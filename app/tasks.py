"""Demo GPU jobs that keep their device busy for `duration_s` seconds.

With the `torch` extra installed and a CUDA device visible, a job runs
matrix multiplications until its time is up. Otherwise it sleeps, so the
queueing behaviour can be shown on any machine.
"""

import logging
import os
import time
from typing import Any

from celery import Task

from app.billing import track_billing
from app.celery_app import celery_app

logger = logging.getLogger(__name__)

MATRIX_SIZE = 4096


def cuda_torch() -> Any:
    """Return the torch module if it can use a CUDA device, else None."""
    try:
        import torch
    except ImportError:
        return None
    return torch if torch.cuda.is_available() else None


def keep_busy(duration_s: float) -> bool:
    """Occupy the GPU for duration_s seconds; return whether a GPU was used."""
    torch = cuda_torch()
    if torch is None:
        time.sleep(duration_s)
        return False
    a = torch.randn(MATRIX_SIZE, MATRIX_SIZE, device="cuda")
    out = torch.empty_like(a)
    deadline = time.monotonic() + duration_s
    while time.monotonic() < deadline:
        torch.mm(a, a, out=out)
        torch.cuda.synchronize()  # kernels are async; wait so the clock is honest
    return True


def run_job(
    task: "Task[..., Any]", duration_s: float, enqueued_at: float
) -> dict[str, Any]:
    started_at = time.time()
    used_gpu = keep_busy(duration_s)
    return {
        "worker": task.request.hostname,
        "gpu_id": os.environ.get("CUDA_VISIBLE_DEVICES") if used_gpu else None,
        "duration_s": duration_s,
        "enqueued_at": enqueued_at,
        "started_at": started_at,
        "finished_at": time.time(),
    }


@celery_app.task(name="gpu_task.short", bind=True)
@track_billing(cost=1.0, description="Short GPU job")
def short_job(
    self: "Task[..., Any]", user_id: str, duration_s: float, enqueued_at: float
) -> dict[str, Any]:
    logger.info("Short job for user %s: %s s", user_id, duration_s)
    return run_job(self, duration_s, enqueued_at)


@celery_app.task(name="gpu_task.long", bind=True)
@track_billing(cost=10.0, description="Long GPU job")
def long_job(
    self: "Task[..., Any]", user_id: str, duration_s: float, enqueued_at: float
) -> dict[str, Any]:
    logger.info("Long job for user %s: %s s", user_id, duration_s)
    return run_job(self, duration_s, enqueued_at)
