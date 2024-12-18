from celery import Celery
from app.settings import Settings

settings = Settings()

celery_app = Celery("gpu_queue", broker=str(settings.redis_url))
celery_app.conf.update(
    result_backend=str(settings.redis_url),
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)

celery_app.autodiscover_tasks(["app.tasks"])
