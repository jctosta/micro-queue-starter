import functools
import logging
from collections.abc import Callable
from typing import Any

from celery import Task

from app import store
from app.models import BillingRecord

logger = logging.getLogger(__name__)


def track_billing(
    cost: float, description: str
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Bill the task's user once the task succeeds.

    The decorated task must be bound (bind=True) and take the user id as its
    first argument. Failed tasks raise before the record is written, so they
    are not billed.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(
            task: "Task[..., Any]", user_id: str, *args: Any, **kwargs: Any
        ) -> Any:
            result = func(task, user_id, *args, **kwargs)
            record = BillingRecord.model_validate(
                {
                    "user_id": user_id,
                    "task_id": task.request.id,
                    "cost": cost,
                    "description": description,
                }
            )
            if store.add_billing_record(record):
                logger.info("Billed %s", record)
            else:
                logger.warning("Task %s was already billed", record.task_id)
            return result

        return wrapper

    return decorator
