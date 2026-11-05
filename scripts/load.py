"""Fire a mix of short and long jobs at the API and report how they queued.

Start the stack first (docker compose --profile cpu up), then:

    uv run scripts/load.py
    uv run scripts/load.py --jobs 50 --long-fraction 0.2

Every number comes from the timestamps the jobs return: queue wait is
started_at - enqueued_at, busy time is finished_at - started_at.
"""

import argparse
import asyncio
import random
import statistics
from collections import defaultdict
from typing import Any

import httpx


def percentile(values: list[float], p: int) -> float:
    if len(values) == 1:
        return values[0]
    return statistics.quantiles(values, n=100, method="inclusive")[p - 1]


def summarise(kinds: list[str], results: list[dict[str, Any]]) -> dict[str, Any]:
    start = min(r["enqueued_at"] for r in results)
    wall_s = max(r["finished_at"] for r in results) - start

    waits: dict[str, list[float]] = defaultdict(list)
    for kind, r in zip(kinds, results, strict=True):
        waits[kind].append(r["started_at"] - r["enqueued_at"])

    busy: dict[str, list[float]] = defaultdict(list)
    for r in results:
        busy[r["worker"]].append(r["finished_at"] - r["started_at"])

    return {
        "jobs": len(results),
        "wall_s": wall_s,
        "jobs_per_min": len(results) / wall_s * 60,
        "queues": {
            kind: {
                "jobs": len(w),
                "p50_wait_s": percentile(w, 50),
                "p95_wait_s": percentile(w, 95),
            }
            for kind, w in sorted(waits.items(), reverse=True)  # short, then long
        },
        "workers": {
            name: {
                "jobs": len(b),
                "busy_s": sum(b),
                "busy_pct": sum(b) / wall_s * 100,
            }
            for name, b in sorted(busy.items())
        },
    }


def render(summary: dict[str, Any]) -> str:
    lines = [
        f"{summary['jobs']} jobs in {summary['wall_s']:.1f} s, "
        f"throughput {summary['jobs_per_min']:.2f} jobs/min",
        "",
        f"{'queue':<8}{'jobs':>6}{'wait p50 (s)':>15}{'wait p95 (s)':>15}",
    ]
    for kind, q in summary["queues"].items():
        lines.append(
            f"{kind:<8}{q['jobs']:>6}{q['p50_wait_s']:>15.1f}{q['p95_wait_s']:>15.1f}"
        )
    lines += ["", f"{'worker':<28}{'jobs':>6}{'busy (s)':>11}{'busy %':>9}"]
    for name, w in summary["workers"].items():
        lines.append(
            f"{name:<28}{w['jobs']:>6}{w['busy_s']:>11.1f}{w['busy_pct']:>9.1f}"
        )
    return "\n".join(lines)


async def wait_for(client: httpx.AsyncClient, task_id: str, poll_s: float) -> Any:
    while True:
        body = (await client.get(f"/task-status/{task_id}")).raise_for_status().json()
        if body["status"] == "SUCCESS":
            return body["result"]
        if body["status"] in {"FAILURE", "REVOKED"}:
            raise RuntimeError(
                f"Job {task_id} ended {body['status']}: {body['result']}"
            )
        await asyncio.sleep(poll_s)


async def run(args: argparse.Namespace) -> None:
    n_long = round(args.jobs * args.long_fraction)
    kinds = ["long"] * n_long + ["short"] * (args.jobs - n_long)
    random.Random(args.seed).shuffle(kinds)
    duration = {"short": args.short_s, "long": args.long_s}

    async with httpx.AsyncClient(
        base_url=args.url, headers={"X-API-Key": args.api_key}, timeout=30
    ) as client:
        task_ids = []
        for kind in kinds:
            response = await client.post(
                "/enqueue-task", json={"kind": kind, "duration_s": duration[kind]}
            )
            task_ids.append(response.raise_for_status().json()["task_id"])
        print(
            f"Submitted {args.jobs - n_long} short ({args.short_s} s) and "
            f"{n_long} long ({args.long_s} s) jobs; waiting for them to finish..."
        )
        results = await asyncio.gather(
            *(wait_for(client, task_id, args.poll_s) for task_id in task_ids)
        )

    print(render(summarise(kinds, list(results))))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--api-key", default="default_api_key")
    parser.add_argument("--jobs", type=int, default=20)
    parser.add_argument("--long-fraction", type=float, default=0.1)
    parser.add_argument("--short-s", type=float, default=5)
    parser.add_argument("--long-s", type=float, default=90)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--poll-s", type=float, default=2)
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
