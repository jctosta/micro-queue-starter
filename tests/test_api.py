import json
from typing import Any
from uuid import UUID, uuid4

import fakeredis
import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app import store
from app.celery_app import celery_app
from app.settings import settings
from tests.conftest import USER_A_KEY, USER_B_KEY

USER_A_ID = "11111111-1111-1111-1111-111111111111"

PAYLOAD = {"kind": "short", "duration_s": 0}


def enqueue(client: TestClient, api_key: str = USER_A_KEY) -> str:
    response = client.post(
        "/enqueue-task", json=PAYLOAD, headers={"X-API-Key": api_key}
    )
    assert response.status_code == 200
    task_id: str = response.json()["task_id"]
    return task_id


def test_enqueue_returns_queued_task(client: TestClient) -> None:
    response = client.post(
        "/enqueue-task", json=PAYLOAD, headers={"X-API-Key": USER_A_KEY}
    )

    body = response.json()
    UUID(body["task_id"])  # raises if the id is not a UUID
    assert body["status"] == "queued"


def test_unknown_api_key_is_rejected(client: TestClient) -> None:
    response = client.post("/enqueue-task", json=PAYLOAD, headers={"X-API-Key": "nope"})

    assert response.status_code == 403


def test_task_status_reports_result(client: TestClient) -> None:
    task_id = enqueue(client)

    response = client.get(f"/task-status/{task_id}", headers={"X-API-Key": USER_A_KEY})

    body: dict[str, Any] = response.json()
    assert (body["status"], body["result"]["duration_s"]) == ("SUCCESS", 0)


def test_long_job_is_billed_as_long(client: TestClient) -> None:
    client.post(
        "/enqueue-task",
        json={"kind": "long", "duration_s": 0},
        headers={"X-API-Key": USER_A_KEY},
    )

    records = client.get("/billing-records", headers={"X-API-Key": USER_A_KEY}).json()

    assert [record["description"] for record in records] == ["Long GPU job"]


@pytest.mark.parametrize(
    "payload",
    [
        {"kind": "huge", "duration_s": 1},
        {"kind": "short", "duration_s": -1},
        {"kind": "long", "duration_s": 7200},
        {"kind": "short", "duration_s": 600},
    ],
)
def test_invalid_job_is_rejected(client: TestClient, payload: dict[str, Any]) -> None:
    response = client.post(
        "/enqueue-task", json=payload, headers={"X-API-Key": USER_A_KEY}
    )

    assert response.status_code == 422


def stream(client: TestClient, task_id: str) -> tuple[str, list[dict[str, Any]]]:
    """Read a status stream to its end; return content type and parsed events."""
    with client.stream(
        "GET", f"/task-status/stream/{task_id}", headers={"X-API-Key": USER_A_KEY}
    ) as response:
        events = [
            json.loads(line.removeprefix("data: "))
            for line in response.iter_lines()
            if line.startswith("data: ")
        ]
    return response.headers["content-type"], events


def test_stream_ends_with_terminal_status(client: TestClient) -> None:
    _, events = stream(client, enqueue(client))

    assert events[-1]["status"] == "SUCCESS"


def test_stream_is_server_sent_events(client: TestClient) -> None:
    content_type, _ = stream(client, enqueue(client))

    assert content_type.startswith("text/event-stream")


def test_stream_stops_at_timeout(
    client: TestClient, fake_redis: fakeredis.FakeRedis, monkeypatch: MonkeyPatch
) -> None:
    never_runs = str(uuid4())
    fake_redis.set(f"task_owner:{never_runs}", USER_A_ID)
    monkeypatch.setattr(settings, "stream_timeout_s", 0)

    _, events = stream(client, never_runs)

    assert [event["status"] for event in events] == ["PENDING"]


def test_failed_task_reports_error_message(
    client: TestClient, fake_redis: fakeredis.FakeRedis
) -> None:
    task_id = str(uuid4())
    fake_redis.set(f"task_owner:{task_id}", USER_A_ID)
    celery_app.backend.mark_as_failure(task_id, ValueError("out of memory"))

    response = client.get(f"/task-status/{task_id}", headers={"X-API-Key": USER_A_KEY})

    assert response.json()["result"] == "out of memory"


def test_billing_record_is_visible_to_its_owner(client: TestClient) -> None:
    task_id = enqueue(client, USER_A_KEY)

    records = client.get("/billing-records", headers={"X-API-Key": USER_A_KEY}).json()

    assert [record["task_id"] for record in records] == [task_id]


def test_billing_record_is_hidden_from_other_users(client: TestClient) -> None:
    enqueue(client, USER_A_KEY)

    records = client.get("/billing-records", headers={"X-API-Key": USER_B_KEY}).json()

    assert records == []


def test_billing_record_is_stored_in_redis(
    client: TestClient, fake_redis: fakeredis.FakeRedis
) -> None:
    task_id = enqueue(client, USER_A_KEY)

    stored = fake_redis.lrange(f"billing:{USER_A_ID}", 0, -1)

    assert [json.loads(raw)["task_id"] for raw in stored] == [task_id]


def test_owner_can_read_task_status(client: TestClient) -> None:
    task_id = enqueue(client, USER_A_KEY)

    response = client.get(f"/task-status/{task_id}", headers={"X-API-Key": USER_A_KEY})

    assert response.status_code == 200


def test_other_user_gets_404_for_task_status(client: TestClient) -> None:
    task_id = enqueue(client, USER_A_KEY)

    response = client.get(f"/task-status/{task_id}", headers={"X-API-Key": USER_B_KEY})

    assert response.status_code == 404


def test_owner_can_stream_task_status(client: TestClient) -> None:
    task_id = enqueue(client, USER_A_KEY)

    response = client.get(
        f"/task-status/stream/{task_id}", headers={"X-API-Key": USER_A_KEY}
    )

    assert response.status_code == 200


def test_other_user_gets_404_for_task_stream(client: TestClient) -> None:
    task_id = enqueue(client, USER_A_KEY)

    response = client.get(
        f"/task-status/stream/{task_id}", headers={"X-API-Key": USER_B_KEY}
    )

    assert response.status_code == 404


def test_task_ownership_expires(
    client: TestClient, fake_redis: fakeredis.FakeRedis
) -> None:
    task_id = enqueue(client, USER_A_KEY)

    assert fake_redis.ttl(f"task_owner:{task_id}") > 0


def test_health_reports_queue_depths(
    client: TestClient, fake_redis: fakeredis.FakeRedis
) -> None:
    fake_redis.rpush("short", "job-1", "job-2")
    fake_redis.rpush("long", "job-3")

    body = client.get("/health").json()

    assert body == {"redis": "ok", "queues": {"short": 2, "long": 1}}


def test_health_is_503_when_redis_is_down(
    client: TestClient, monkeypatch: MonkeyPatch
) -> None:
    down = fakeredis.FakeServer()
    down.connected = False
    monkeypatch.setattr(store, "get_redis", lambda: fakeredis.FakeRedis(server=down))

    assert client.get("/health").status_code == 503
