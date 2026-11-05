"""Start a worker that owns one GPU and runs one job at a time.

Pick the GPU with CUDA_VISIBLE_DEVICES, one worker process per card:

    CUDA_VISIBLE_DEVICES=0 uv run worker.py
    CUDA_VISIBLE_DEVICES=1 uv run worker.py

Without CUDA_VISIBLE_DEVICES the worker runs on CPU.
"""

import os

from app.celery_app import celery_app


def worker_argv(gpu: str) -> list[str]:
    if "," in gpu:
        raise SystemExit(
            f"A worker owns exactly one GPU; got CUDA_VISIBLE_DEVICES={gpu!r}"
        )
    name = f"gpu{gpu}" if gpu else "cpu"
    # Two jobs on one card slow each other down, so a worker runs one at a time.
    return ["worker", "--loglevel=INFO", "--concurrency=1", f"--hostname={name}@%h"]


if __name__ == "__main__":
    celery_app.worker_main(argv=worker_argv(os.environ.get("CUDA_VISIBLE_DEVICES", "")))
