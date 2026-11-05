from celery import Celery

from app.settings import settings

celery_app = Celery("gpu_queue", broker=str(settings.redis_url))
celery_app.conf.update(
    result_backend=str(settings.redis_url),
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # A worker reserves only the job it is running, so a long job never holds
    # short jobs hostage in the worker's local buffer.
    worker_prefetch_multiplier=1,
    # Ack after the job finishes, not when it starts: if the worker dies
    # mid-job, the broker hands the job to another worker.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Short (seconds) and long (minutes) jobs wait in separate queues. A worker
    # that consumes both takes from each in turn, so a burst of long jobs
    # cannot push every short job to the back of one shared line.
    task_routes={
        "gpu_task.short": {"queue": "short"},
        "gpu_task.long": {"queue": "long"},
    },
    task_default_queue="short",
)

celery_app.autodiscover_tasks(["app.tasks"])
