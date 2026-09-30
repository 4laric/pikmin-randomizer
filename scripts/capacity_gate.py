"""Admit game sessions and heavy builds by live machine capacity (#953).

Agents call this before launching nectar.exe or a heavy native build instead
of obeying a fixed session count:

    py -3.12 scripts/capacity_gate.py --kind game --wait
    py -3.12 scripts/capacity_gate.py --kind build --jobs 4 --wait
    py -3.12 scripts/capacity_gate.py --status

Admission uses measured headroom only: free RAM left after the job's
expected footprint, CPU load averaged over a short sample, and GPU memory and
load from nvidia-smi. There are no fixed caps on how many games or compilers
run (owner, 2026-09-30: limits must follow real capacity, not counts); the
counts are still reported for diagnosis. This laptop (Core Ultra 9 275HX, 24 cores, 31 GB) bugchecked twice on
2026-09-29 (0x3B, 0x7E) with ~8 parallel builds plus several game sessions.
A game session measured ~0.4 GB working set. It bugchecked again (0x3B)
on 2026-09-30 at 16 compilers / 6 games with about 9 agents active, which
is why the headroom margins below are conservative. Loosen them only after
sustained stable runs, and record why.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from dataclasses import asdict, dataclass

GAME_NAMES = {"nectar.exe", "nectar"}
COMPILER_NAMES = {"cc1plus.exe", "cc1.exe", "lto1.exe", "ld.exe", "cc1plus", "cc1", "lto1", "ld"}

LIMITS = {
    # Free RAM (GB) that must remain after admitting the job.
    "game_min_free_gb": 6.0,
    "build_min_free_gb": 8.0,
    # Expected footprint of a new job (GB): one game session, one compiler job.
    "game_cost_gb": 0.6,
    "build_cost_gb_per_job": 1.0,
    # Averaged CPU load (%) at or above which nothing new is admitted.
    "game_max_cpu": 85.0,
    "build_max_cpu": 70.0,
    # GPU headroom for games (skipped when nvidia-smi is unavailable).
    "game_min_gpu_free_gb": 2.0,
    "game_max_gpu_util": 85.0,
}


@dataclass
class Snapshot:
    free_gb: float
    cpu_percent: float
    games: int
    compilers: int
    logical_cpus: int
    gpu_free_gb: float | None = None
    gpu_util: float | None = None


def admit(kind: str, snap: Snapshot, jobs: int = 4, limits: dict = LIMITS) -> tuple[bool, str]:
    """Pure admission policy; returns (admitted, reason)."""
    if kind == "game":
        after = snap.free_gb - limits["game_cost_gb"]
        if after < limits["game_min_free_gb"]:
            return False, f"free RAM {snap.free_gb:.1f} GB - game {limits['game_cost_gb']} < {limits['game_min_free_gb']} GB"
        if snap.cpu_percent >= limits["game_max_cpu"]:
            return False, f"CPU {snap.cpu_percent:.0f}% >= {limits['game_max_cpu']:.0f}%"
        if snap.gpu_free_gb is not None and snap.gpu_free_gb < limits["game_min_gpu_free_gb"]:
            return False, f"GPU free {snap.gpu_free_gb:.1f} GB < {limits['game_min_gpu_free_gb']} GB"
        if snap.gpu_util is not None and snap.gpu_util >= limits["game_max_gpu_util"]:
            return False, f"GPU {snap.gpu_util:.0f}% >= {limits['game_max_gpu_util']:.0f}%"
        return True, "ok"
    if kind == "build":
        cost = jobs * limits["build_cost_gb_per_job"]
        if snap.free_gb - cost < limits["build_min_free_gb"]:
            return False, f"free RAM {snap.free_gb:.1f} GB - {jobs} jobs x {limits['build_cost_gb_per_job']} < {limits['build_min_free_gb']} GB"
        if snap.cpu_percent >= limits["build_max_cpu"]:
            return False, f"CPU {snap.cpu_percent:.0f}% >= {limits['build_max_cpu']:.0f}%"
        return True, "ok"
    raise ValueError(f"unknown kind {kind!r}")


def measure_gpu() -> tuple[float | None, float | None]:
    """(free GB, utilisation %) of the busiest-memory NVIDIA GPU, or (None, None)."""
    import subprocess

    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total,memory.used,utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10, check=True,
        ).stdout
        rows = [[float(x) for x in line.split(",")] for line in out.strip().splitlines() if line.strip()]
    except (OSError, subprocess.SubprocessError, ValueError):
        return None, None
    if not rows:
        return None, None
    total, used, util = max(rows, key=lambda r: r[1])
    return (total - used) / 1024, util


def measure(sample_seconds: float = 3.0) -> Snapshot:
    import psutil

    cpu = psutil.cpu_percent(interval=sample_seconds)
    games = compilers = 0
    for proc in psutil.process_iter(["name"]):
        name = (proc.info.get("name") or "").lower()
        if name in GAME_NAMES:
            games += 1
        elif name in COMPILER_NAMES:
            compilers += 1
    gpu_free, gpu_util = measure_gpu()
    return Snapshot(
        free_gb=psutil.virtual_memory().available / 2**30,
        cpu_percent=cpu,
        games=games,
        compilers=compilers,
        logical_cpus=psutil.cpu_count() or 1,
        gpu_free_gb=gpu_free,
        gpu_util=gpu_util,
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--kind", choices=("game", "build"))
    parser.add_argument("--jobs", type=int, default=4, help="parallel compile jobs the build will use")
    parser.add_argument("--wait", action="store_true", help="block until admitted")
    parser.add_argument("--timeout", type=float, default=3600.0, help="max seconds to wait")
    parser.add_argument("--status", action="store_true", help="print a capacity snapshot and exit")
    args = parser.parse_args(argv)

    if args.status or not args.kind:
        snap = measure()
        print(json.dumps({**asdict(snap), "game": admit("game", snap), "build": admit("build", snap, args.jobs)}, indent=1))
        return 0

    deadline = time.monotonic() + args.timeout
    while True:
        snap = measure()
        ok, reason = admit(args.kind, snap, args.jobs)
        print(f"CAPACITY_GATE kind={args.kind} admitted={int(ok)} reason={reason} "
              f"free_gb={snap.free_gb:.1f} cpu={snap.cpu_percent:.0f} games={snap.games} compilers={snap.compilers} "
              f"gpu_free_gb={snap.gpu_free_gb} gpu_util={snap.gpu_util}",
              flush=True)
        if ok:
            return 0
        if not args.wait or time.monotonic() >= deadline:
            return 1
        # Jitter so several waiting agents don't all launch in the same instant.
        time.sleep(30 + random.uniform(0, 30))


if __name__ == "__main__":
    sys.exit(main())
