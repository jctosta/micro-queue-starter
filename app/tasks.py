from typing import Any

from celery import Task
from app.models import User
from app.celery_app import celery_app
from app.billing import track_billing
import time


@celery_app.task(name="gpu_task.run", bind=True)
@track_billing(cost=1.0, description="GPU Task")
def run_gpu_task(
    self: "Task[..., Any]", user: dict[str, Any], data: dict[str, Any]
) -> dict[str, Any]:
    print(user)
    print(data)
    user_model = User(**user)
    task_id = self.request.id
    time.sleep(10)
    return {
        "status": "success",
        "processed_data": data,
        "user": user_model.id,
        "task_id": str(task_id),
    }
