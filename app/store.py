"""State shared by the API and the workers.

They run as separate processes, often on separate machines, so anything both
sides need lives in Redis. Every Redis key the app uses is defined here.
"""

from collections.abc import Iterable
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
    get_redis().set(f"task_owner:{task_id}", str(user_id), ex=settings.task_ttl_s)


def task_owner(task_id: UUID) -> str | None:
    return cast(str | None, get_redis().get(f"task_owner:{task_id}"))


def queue_depths(queues: Iterable[str]) -> dict[str, int]:
    """Jobs waiting per queue. Kombu keeps each Redis queue in a list of that name."""
    redis_client = get_redis()
    return {queue: cast(int, redis_client.llen(queue)) for queue in queues}


def add_billing_record(record: BillingRecord) -> bool:
    """Append the record unless this task was already billed.

    Workers ack late, so a task runs again if its worker dies after billing
    but before the ack. The billed:{task_id} marker and the record are written
    in one WATCH/MULTI transaction, so a task is billed exactly once.
    """
    marker = f"billed:{record.task_id}"
    # redis-py leaves watch() and execute() unannotated.
    with get_redis().pipeline() as pipe:
        try:
            pipe.watch(marker)  # type: ignore[no-untyped-call]
            if pipe.exists(marker):
                return False
            pipe.multi()
            pipe.set(marker, 1, ex=settings.task_ttl_s)
            pipe.rpush(f"billing:{record.user_id}", record.model_dump_json())
            pipe.execute()  # type: ignore[no-untyped-call]
        except redis.WatchError:  # a concurrent run of the same task billed it
            return False
    return True


def billing_records(user_id: UUID) -> list[BillingRecord]:
    raw = cast(list[str], get_redis().lrange(f"billing:{user_id}", 0, -1))
    return [BillingRecord.model_validate_json(item) for item in raw]
