import time
from typing import Any
from uuid import uuid4

import fakeredis
import pytest
from celery import Task

from app.tasks import long_job, short_job

USER_A_ID = "11111111-1111-1111-1111-111111111111"


def run(task: "Task[..., Any]", duration_s: float = 0) -> dict[str, Any]:
    result: dict[str, Any] = task.apply(args=(USER_A_ID, duration_s, time.time())).get()
    return result


@pytest.mark.parametrize("task", [short_job, long_job])
def test_job_reports_when_it_waited_and_ran(task: "Task[..., Any]") -> None:
    result = run(task)

    assert result["enqueued_at"] <= result["started_at"] <= result["finished_at"]


def test_job_runs_for_its_duration() -> None:
    result = run(short_job, duration_s=0.05)

    assert result["finished_at"] - result["started_at"] >= 0.05


def test_job_without_gpu_reports_no_gpu_id() -> None:
    assert run(short_job)["gpu_id"] is None


def test_redelivered_task_is_billed_once(fake_redis: fakeredis.FakeRedis) -> None:
    task_id = str(uuid4())

    for _ in range(2):  # a late-acked task runs again if its worker dies
        short_job.apply(args=(USER_A_ID, 0, time.time()), task_id=task_id)

    assert fake_redis.llen(f"billing:{USER_A_ID}") == 1
