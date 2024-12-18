import functools
import logging
from typing import Any, Callable, TypedDict, Unpack
from uuid import uuid4, UUID
from app.models import BillingRecord

logger = logging.getLogger(__name__)

billing_records: list[BillingRecord] = []


class RequestParams(TypedDict, total=False):
    id: UUID


def track_billing(cost: float, description: str = "GPU Task") -> Callable[..., Any]:
    """
    Decorator to track billing information and associate it with a user.

    Args:
        cost (float): The cost of the task.
        description (str): The description of the task.

    Returns:
        function: The decorated function.
    """

    def decorator(func: Any) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(
            *args: Unpack[tuple[Any, Any]], **kwargs: Unpack[RequestParams]
        ) -> Any:
            # Handle `bind=True` for Celery tasks
            remaining_args: list[Any]
            if hasattr(func, "__self__") or "self" in func.__code__.co_varnames:
                self, user, *remaining_args = args
                logger.debug(f"Task {self.name} is bound. Processing billing.")
                task_id = self.request.id  # Get task ID from Celery's request object
                result = func(self, user, *remaining_args, **kwargs)
            else:
                user, *remaining_args = args
                logger.debug(f"Task {func.__name__} is unbound. Processing billing.")
                task_id = kwargs.get(
                    "task_id", uuid4()
                )  # Generate a UUID if not present
                result = func(user, *remaining_args, **kwargs)

            # Add a billing record
            billing_record = BillingRecord(
                user_id=user["id"] if isinstance(user, dict) else user.id,
                task_id=UUID(task_id) if not isinstance(task_id, UUID) else task_id,
                cost=cost,
                description=description,
            )
            billing_records.append(billing_record)
            logger.info(f"Billing tracked: {billing_record}")
            return result

        return wrapper

    return decorator
