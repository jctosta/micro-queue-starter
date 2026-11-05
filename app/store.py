"""State shared by the API and the workers.

They run as separate processes, often on separate machines, so anything both
sides need lives in Redis. Every Redis key the app uses is defined here.
"""

from functools import cache
from typing import cast
from uuid import UUID

import redis

from app.models import BillingRecord
from app.settings import settings


@cache
def get_redis() -> redis.Redis:
    return redis.Redis.from_url(str(settings.redis_url), decode_responses=True)


def set_task_owner(task_id: UUID, user_id: UUID) -> None:
    get_redis().set(f"task_owner:{task_id}", str(user_id), ex=settings.task_owner_ttl_s)


def task_owner(task_id: UUID) -> str | None:
    return cast(str | None, get_redis().get(f"task_owner:{task_id}"))


def add_billing_record(record: BillingRecord) -> None:
    get_redis().rpush(f"billing:{record.user_id}", record.model_dump_json())


def billing_records(user_id: UUID) -> list[BillingRecord]:
    raw = cast(list[str], get_redis().lrange(f"billing:{user_id}", 0, -1))
    return [BillingRecord.model_validate_json(item) for item in raw]
