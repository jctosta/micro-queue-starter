import pytest

from app.celery_app import celery_app
from worker import worker_argv


def test_worker_reserves_only_the_job_it_runs() -> None:
    assert celery_app.conf.worker_prefetch_multiplier == 1


def test_job_is_acked_only_after_it_finishes() -> None:
    assert celery_app.conf.task_acks_late is True


def test_job_returns_to_queue_when_its_worker_dies() -> None:
    assert celery_app.conf.task_reject_on_worker_lost is True


def test_worker_runs_one_job_at_a_time() -> None:
    assert "--concurrency=1" in worker_argv("0")


def test_worker_is_named_after_its_gpu() -> None:
    assert "--hostname=gpu1@%h" in worker_argv("1")


def test_worker_without_gpu_is_named_cpu() -> None:
    assert "--hostname=cpu@%h" in worker_argv("")


def test_worker_refuses_more_than_one_gpu() -> None:
    with pytest.raises(SystemExit, match="exactly one GPU"):
        worker_argv("0,1")
