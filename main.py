import asyncio
import logging
from collections.abc import AsyncGenerator
from uuid import UUID

import uvicorn
from fastapi import Depends, FastAPI
from fastapi.responses import StreamingResponse

from app import store
from app.auth import validate_api_key
from app.celery_app import celery_app
from app.models import BillingRecord, TaskInput, TaskStatusResponse, User
from app.tasks import run_gpu_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


@app.post("/enqueue-task")
async def enqueue_task(
    task_input: TaskInput, user: User = Depends(validate_api_key)
) -> TaskStatusResponse:
    task = run_gpu_task.apply_async(args=(str(user.id), task_input.data))
    return TaskStatusResponse(task_id=UUID(task.id), status="queued")


@app.get("/task-status/{task_id}")
async def task_status(
    task_id: UUID, user: User = Depends(validate_api_key)
) -> TaskStatusResponse:
    task = celery_app.AsyncResult(str(task_id))
    return TaskStatusResponse(task_id=task_id, status=task.status, result=task.result)


@app.get("/task-status/stream/{task_id}")
async def task_status_stream(
    task_id: UUID, user: User = Depends(validate_api_key)
) -> StreamingResponse:
    async def event_generator() -> AsyncGenerator[str, None]:
        task = celery_app.AsyncResult(str(task_id))
        previous_status = None

        while task.status not in {"SUCCESS", "FAILURE"}:
            task = celery_app.AsyncResult(str(task_id))
            if task.status != previous_status:
                logger.debug("Task %s status: %s", task_id, task.status)
                yield f"data: {task.status}\n\n"
                previous_status = task.status
            await asyncio.sleep(1)

        yield f"data: {task.status}\n\n"
        if task.result:
            logger.debug("Task %s result: %s", task_id, task.result)
            yield f"data: {task.result}\n\n"

    return StreamingResponse(event_generator())


@app.get("/billing-records")
async def fetch_billing_records(
    user: User = Depends(validate_api_key),
) -> list[BillingRecord]:
    return store.billing_records(user.id)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
