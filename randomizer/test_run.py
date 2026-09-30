"""Environment policy for agent-driven native test runs.

Agent runs must always set PIKMIN_RANDOMIZER_TEST_BACKGROUND=1 so the game never
pauses when it loses focus. The owner may opt in to *watching* those runs by
creating ``output/workflow/WATCH_RUNS`` (or exporting PIKMIN_WATCH_RUNS=1); runs
then also get PIKMIN_RANDOMIZER_TEST_VISIBLE=1, which shows the window without
stealing focus. Owner hand-play launchers must not use this module.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

BACKGROUND = "PIKMIN_RANDOMIZER_TEST_BACKGROUND"
VISIBLE = "PIKMIN_RANDOMIZER_TEST_VISIBLE"
WATCH_ENV = "PIKMIN_WATCH_RUNS"
WATCH_FILE = "WATCH_RUNS"


def workflow_dir(start: Path | None = None) -> Path | None:
    """Nearest ancestor's ``output/workflow`` directory (shared across worktrees)."""
    override = os.environ.get("PIKMIN_WORKFLOW_DIR")
    if override:
        return Path(override)
    here = Path(start or __file__).resolve()
    for parent in here.parents:
        candidate = parent / "output" / "workflow"
        if candidate.is_dir():
            return candidate
    return None


def watch_enabled(env=None, start: Path | None = None) -> bool:
    env = os.environ if env is None else env
    if env.get(WATCH_ENV) == "1":
        return True
    directory = workflow_dir(start)
    return bool(directory and (directory / WATCH_FILE).exists())


def apply_test_run_env(env: dict, start: Path | None = None) -> dict:
    """Force background mode (never hold for focus); add visible when watching."""
    env[BACKGROUND] = "1"
    if watch_enabled(env, start):
        env[VISIBLE] = "1"
    else:
        env.pop(VISIBLE, None)
    return env


def hidden_startupinfo(env=None, start: Path | None = None):
    """STARTUPINFO hiding the game window, or None when the owner is watching runs.

    A hidden STARTUPINFO forces the first ShowWindow to SW_HIDE, which would defeat
    TEST_VISIBLE, so watched runs must not pass it.
    """
    if watch_enabled(env, start) or not hasattr(subprocess, "STARTUPINFO"):
        return None
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    return startup


def show_window_flag(env=None, start: Path | None = None) -> int:
    """Value to OR into STARTUPINFO.dwFlags: STARTF_USESHOWWINDOW (hide) unless watching."""
    if watch_enabled(env, start) or not hasattr(subprocess, "STARTF_USESHOWWINDOW"):
        return 0
    return subprocess.STARTF_USESHOWWINDOW
