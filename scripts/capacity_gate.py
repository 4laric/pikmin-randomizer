"""Admit game sessions and heavy builds by live machine capacity (#953).

Agents call this before launching nectar.exe or a heavy native build instead
of obeying a fixed session count:

    py -3.12 scripts/capacity_gate.py --kind game --wait
    py -3.12 scripts/capacity_gate.py --kind build --jobs 4 --wait
    py -3.12 scripts/capacity_gate.py --status

Admission uses free RAM, CPU load averaged over a short sample, and the
number of running game and compiler processes. Hard ceilings stay as a
backstop: this laptop (Core Ultra 9 275HX, 24 cores, 31 GB) bugchecked twice on
2026-09-29 (0x3B, 0x7E) with ~8 parallel builds plus several game sessions.
A game session measured ~0.4 GB working set. It bugchecked again (0x3B)
on 2026-09-30 at 16 compilers / 6 games with about 9 agents active, so the
limits were halved. Raise the limits in LIMITS only
after sustained stable runs at the current ones, and record why.
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
    # Free RAM that must remain after admitting the job (GB).
    "game_min_free_gb": 6.0,
    "build_min_free_gb": 8.0,
    # Averaged CPU load (%) at or above which nothing new is admitted.
    "game_max_cpu": 85.0,
    "build_max_cpu": 70.0,
    # Backstops regardless of measurements.
    "max_games": 3,
    "max_compilers": 8,  # sum of running compiler processes, roughly total -j
}


@dataclass
class Snapshot:
    free_gb: float
    cpu_percent: float
    games: int
    compilers: int
    logical_cpus: int


def admit(kind: str, snap: Snapshot, jobs: int = 4, limits: dict = LIMITS) -> tuple[bool, str]:
    """Pure admission policy; returns (admitted, reason)."""
    if kind == "game":
        if snap.games >= limits["max_games"]:
            return False, f"games {snap.games} >= max {limits['max_games']}"
        if snap.free_gb < limits["game_min_free_gb"]:
            return False, f"free RAM {snap.free_gb:.1f} GB < {limits['game_min_free_gb']} GB"
        if snap.cpu_percent >= limits["game_max_cpu"]:
            return False, f"CPU {snap.cpu_percent:.0f}% >= {limits['game_max_cpu']:.0f}%"
        return True, "ok"
    if kind == "build":
        if snap.compilers + jobs > limits["max_compilers"]:
            return False, f"compilers {snap.compilers}+{jobs} > max {limits['max_compilers']}"
        if snap.free_gb < limits["build_min_free_gb"]:
            return False, f"free RAM {snap.free_gb:.1f} GB < {limits['build_min_free_gb']} GB"
        if snap.cpu_percent >= limits["build_max_cpu"]:
            return False, f"CPU {snap.cpu_percent:.0f}% >= {limits['build_max_cpu']:.0f}%"
        return True, "ok"
    raise ValueError(f"unknown kind {kind!r}")


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
    return Snapshot(
        free_gb=psutil.virtual_memory().available / 2**30,
        cpu_percent=cpu,
        games=games,
        compilers=compilers,
        logical_cpus=psutil.cpu_count() or 1,
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
              f"free_gb={snap.free_gb:.1f} cpu={snap.cpu_percent:.0f} games={snap.games} compilers={snap.compilers}",
              flush=True)
        if ok:
            return 0
        if not args.wait or time.monotonic() >= deadline:
            return 1
        # Jitter so several waiting agents don't all launch in the same instant.
        time.sleep(30 + random.uniform(0, 30))


if __name__ == "__main__":
    sys.exit(main())
