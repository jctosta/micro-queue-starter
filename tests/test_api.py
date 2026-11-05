import json
from typing import Any
from uuid import UUID

import fakeredis
from fastapi.testclient import TestClient

from tests.conftest import USER_A_KEY, USER_B_KEY

USER_A_ID = "11111111-1111-1111-1111-111111111111"

PAYLOAD = {"data": {"image": "test_image_data", "model": "resnet50"}}


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
    assert (body["status"], body["result"]["task_id"]) == ("SUCCESS", task_id)


def test_stream_ends_with_terminal_status(client: TestClient) -> None:
    task_id = enqueue(client)

    with client.stream(
        "GET", f"/task-status/stream/{task_id}", headers={"X-API-Key": USER_A_KEY}
    ) as response:
        events = [line for line in response.iter_lines() if line.startswith("data:")]

    assert events[0] == "data: SUCCESS"


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
