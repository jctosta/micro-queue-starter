import asyncio
import logging
import time
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse

from app import store
from app.auth import validate_api_key
from app.celery_app import celery_app
from app.models import BillingRecord, TaskInput, TaskStatusResponse, User
from app.settings import settings
from app.tasks import long_job, short_job

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STREAM_POLL_S = 1.0
TASKS = {"short": short_job, "long": long_job}

app = FastAPI()

# Endpoints that call Redis or Celery are plain `def`: both clients block, and
# FastAPI runs sync endpoints in a thread pool instead of on the event loop.


@app.post("/enqueue-task")
def enqueue_task(
    task_input: TaskInput, user: User = Depends(validate_api_key)
) -> TaskStatusResponse:
    # Record the owner before the task exists, so no status request can see an
    # unowned task.
    task_id = uuid4()
    store.set_task_owner(task_id, user.id)
    # Stamp the enqueue time on the server, so queue wait uses server clocks.
    TASKS[task_input.kind].apply_async(
        args=(str(user.id), task_input.duration_s, time.time()), task_id=str(task_id)
    )
    return TaskStatusResponse(task_id=task_id, status="queued")


def owned_task_id(task_id: UUID, user: User = Depends(validate_api_key)) -> UUID:
    """Resolve the task id, or 404 if the caller does not own it.

    404 rather than 403, so callers cannot probe which task ids exist.
    """
    if store.task_owner(task_id) != str(user.id):
        raise HTTPException(status_code=404, detail="Task not found")
    return task_id


def read_status(task_id: UUID) -> TaskStatusResponse:
    task = celery_app.AsyncResult(str(task_id))
    # A failed task's result is the exception; send its message instead.
    result = str(task.result) if task.failed() else task.result
    return TaskStatusResponse(task_id=task_id, status=task.status, result=result)


@app.get("/task-status/{task_id}")
def task_status(task_id: UUID = Depends(owned_task_id)) -> TaskStatusResponse:
    return read_status(task_id)


@app.get("/task-status/stream/{task_id}")
async def task_status_stream(
    request: Request, task_id: UUID = Depends(owned_task_id)
) -> StreamingResponse:
    """Send an event on every status change until the task finishes.

    The stream also ends when the client disconnects or after stream_timeout_s.
    """

    async def events() -> AsyncIterator[str]:
        deadline = time.monotonic() + settings.stream_timeout_s
        last = None
        while not await request.is_disconnected():
            status = await asyncio.to_thread(read_status, task_id)
            if status != last:
                yield f"data: {status.model_dump_json()}\n\n"
                last = status
            remaining = deadline - time.monotonic()
            if status.status in {"SUCCESS", "FAILURE", "REVOKED"} or remaining <= 0:
                return
            await asyncio.sleep(min(STREAM_POLL_S, remaining))

    return StreamingResponse(events(), media_type="text/event-stream")


@app.get("/billing-records")
def fetch_billing_records(
    user: User = Depends(validate_api_key),
) -> list[BillingRecord]:
    return store.billing_records(user.id)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
