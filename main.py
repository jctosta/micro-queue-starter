import asyncio
from typing import Any, AsyncGenerator
from uuid import UUID
from fastapi import FastAPI, Depends
from fastapi.responses import StreamingResponse
from app.auth import validate_api_key
from app.tasks import run_gpu_task
from app.celery_app import celery_app
from app.models import BillingRecord, TaskInput, TaskStatusResponse, User
from app.billing import billing_records
import uvicorn

app = FastAPI()


@app.post("/enqueue-task")
async def enqueue_task(
    task_input: TaskInput, user: User = Depends(validate_api_key)
) -> TaskStatusResponse:
    task_args: tuple[Any, ...] = (user.model_dump(), task_input.data)
    task = run_gpu_task.apply_async(args=task_args)
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
                print(f"Sending status update: {task.status}")
                yield f"data: {task.status}\n\n"
                previous_status = task.status
            await asyncio.sleep(1)

        yield f"data: {task.status}\n\n"
        if task.result:
            print(f"Sending final result: {task.result}")
            yield f"data: {task.result}\n\n"

    return StreamingResponse(event_generator())


@app.get("/billing-records")
async def fetch_billing_records(
    user: User = Depends(validate_api_key),
) -> list[BillingRecord]:
    user_billing = [record for record in billing_records if record.user_id == user.id]
    return user_billing


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
