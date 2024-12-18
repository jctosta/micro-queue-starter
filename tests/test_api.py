from typing import Any
import pytest
import httpx
import asyncio
from uuid import UUID

BASE_URL = "http://127.0.0.1:8000"
API_KEY = "default_api_key"

pytestmark = pytest.mark.asyncio


async def test_enqueue_task() -> Any:
    async with httpx.AsyncClient() as client:
        payload = {"data": {"image": "test_image_data", "model": "resnet50"}}
        headers = {"X-API-Key": API_KEY}

        response = await client.post(
            f"{BASE_URL}/enqueue-task", json=payload, headers=headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "task_id" in data, "Response must include 'task_id'"
        assert "status" in data, "Response must include 'status'"
        assert UUID(data["task_id"]), "task_id must be a valid UUID"
        assert data["status"] == "queued", "Status must be 'queued'"

        print(f"Enqueue Task Response: {data}")
        return data["task_id"]


async def test_task_status() -> None:
    task_id = await test_enqueue_task()

    async with httpx.AsyncClient() as client:
        headers = {"X-API-Key": API_KEY}
        for _ in range(10):
            response = await client.get(
                f"{BASE_URL}/task-status/{task_id}", headers=headers
            )
            assert response.status_code == 200
            data = response.json()

            assert "status" in data, "Response must include 'status'"
            print(f"Task Status: {data['status']}")

            if data["status"] == "SUCCESS":
                assert "result" in data, "Task result must be present when finished"
                print(f"Final Result: {data['result']}")
                break
            await asyncio.sleep(2)
        else:
            pytest.fail("Task did not complete within 10 retries")


async def test_see_task_stream() -> None:
    task_id = await test_enqueue_task()

    async with httpx.AsyncClient(timeout=360) as client:
        headers = {"X-API-Key": API_KEY}
        async with client.stream(
            "GET", f"{BASE_URL}/task-status/stream/{task_id}", headers=headers
        ) as response:
            assert response.status_code == 200

            async for line in response.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue

                status = line[len("data:") :].strip()
                print(f"Stream Update: {status}")

                if status in {"SUCCESS", "FAILURE"}:
                    assert status == "SUCCESS", f"Task failed with status: {status}"
                    return

    pytest.fail("Stream ended without receiving terminal status.")
