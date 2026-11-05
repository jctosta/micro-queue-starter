from typing import Any

from scripts.load import summarise


def job(
    worker: str, enqueued: float, started: float, finished: float
) -> dict[str, Any]:
    return {
        "worker": worker,
        "enqueued_at": enqueued,
        "started_at": started,
        "finished_at": finished,
    }


# Two workers over a 10 s window: w1 runs a long job, w2 runs two short ones.
KINDS = ["long", "short", "short"]
RESULTS = [
    job("w1", enqueued=0, started=0, finished=10),
    job("w2", enqueued=0, started=1, finished=3),
    job("w2", enqueued=0, started=3, finished=5),
]


def test_wait_is_measured_from_enqueue_to_start() -> None:
    summary = summarise(KINDS, RESULTS)

    assert summary["queues"]["short"]["p50_wait_s"] == 2


def test_throughput_counts_jobs_over_the_whole_run() -> None:
    summary = summarise(KINDS, RESULTS)

    assert summary["jobs_per_min"] == 18


def test_busy_time_is_summed_per_worker() -> None:
    summary = summarise(KINDS, RESULTS)

    assert {name: w["busy_s"] for name, w in summary["workers"].items()} == {
        "w1": 10,
        "w2": 4,
    }
