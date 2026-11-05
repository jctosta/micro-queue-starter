"""Live tests: need the API on :8000, a worker and Redis running."""

import asyncio
from uuid import UUID

import httpx
import pytest

BASE_URL = "http://127.0.0.1:8000"
HEADERS = {"X-API-Key": "default_api_key"}
PAYLOAD = {"data": {"image": "test_image_data", "model": "resnet50"}}

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def enqueue(client: httpx.AsyncClient) -> str:
    response = await client.post("/enqueue-task", json=PAYLOAD, headers=HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued"
    return str(UUID(body["task_id"]))


async def test_task_completes() -> None:
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        task_id = await enqueue(client)
        for _ in range(30):
            response = await client.get(f"/task-status/{task_id}", headers=HEADERS)
            if response.json()["status"] == "SUCCESS":
                return
            await asyncio.sleep(1)
    pytest.fail("Task did not finish within 30 s")


async def test_stream_reaches_terminal_status() -> None:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60) as client:
        task_id = await enqueue(client)
        async with client.stream(
            "GET", f"/task-status/stream/{task_id}", headers=HEADERS
        ) as response:
            async for line in response.aiter_lines():
                if line.removeprefix("data: ") in {"SUCCESS", "FAILURE"}:
                    assert line == "data: SUCCESS"
                    return
    pytest.fail("Stream ended without a terminal status")
