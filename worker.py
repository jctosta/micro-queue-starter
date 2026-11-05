"""Start a worker that owns one GPU and runs one job at a time.

Pick the GPU with CUDA_VISIBLE_DEVICES, one worker process per card:

    CUDA_VISIBLE_DEVICES=0 uv run worker.py
    CUDA_VISIBLE_DEVICES=1 uv run worker.py

Without CUDA_VISIBLE_DEVICES the worker runs on CPU. By default a worker
consumes both queues; WORKER_QUEUES=short dedicates it to short jobs.
"""

import os

from app.celery_app import QUEUES, celery_app

ALL_QUEUES = ",".join(QUEUES)


def worker_argv(gpu: str, queues: str = ALL_QUEUES) -> list[str]:
    if "," in gpu:
        raise SystemExit(
            f"A worker owns exactly one GPU; got CUDA_VISIBLE_DEVICES={gpu!r}"
        )
    name = f"gpu{gpu}" if gpu else "cpu"
    if queues != ALL_QUEUES:  # e.g. gpu0-short, so dedicated workers stand out
        name += "-" + queues.replace(",", "-")
    # Two jobs on one card slow each other down, so a worker runs one at a time.
    return [
        "worker",
        "--loglevel=INFO",
        "--concurrency=1",
        f"--hostname={name}@%h",
        f"--queues={queues}",
    ]


if __name__ == "__main__":
    celery_app.worker_main(
        argv=worker_argv(
            os.environ.get("CUDA_VISIBLE_DEVICES", ""),
            os.environ.get("WORKER_QUEUES", ALL_QUEUES),
        )
    )
