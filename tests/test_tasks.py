from uuid import uuid4

import fakeredis

from app.tasks import run_gpu_task

USER_A_ID = "11111111-1111-1111-1111-111111111111"


def test_redelivered_task_is_billed_once(fake_redis: fakeredis.FakeRedis) -> None:
    task_id = str(uuid4())

    for _ in range(2):  # a late-acked task runs again if its worker dies
        run_gpu_task.apply(args=(USER_A_ID, {}), task_id=task_id)

    assert fake_redis.llen(f"billing:{USER_A_ID}") == 1
