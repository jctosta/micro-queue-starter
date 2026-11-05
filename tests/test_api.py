from typing import Any
from uuid import UUID

from fastapi.testclient import TestClient

from tests.conftest import USER_A_KEY

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
