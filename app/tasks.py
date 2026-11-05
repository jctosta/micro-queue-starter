import logging
import time
from typing import Any

from celery import Task

from app.billing import track_billing
from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="gpu_task.run", bind=True)
@track_billing(cost=1.0, description="GPU Task")
def run_gpu_task(
    self: "Task[..., Any]", user_id: str, data: dict[str, Any]
) -> dict[str, Any]:
    logger.info("Running GPU task for user %s", user_id)
    time.sleep(10)
    return {"status": "success", "processed_data": data, "task_id": self.request.id}
