"""Forest P1 input-injection staging + run-log reading (issue #660).

Lane p2-overworld-forest-runtime-input-injection. Reuses the done P1
staged-rerun adapter read-only (run-root staging with JAudio pins; never
edited, never re-owned) and the accepted #660 fixture/runner read-only.
This module only: stages a fresh injection run dir, parses a runtime marker
log with a strict advance verdict, and records the #632 guard hash.
No engine/family/shared edits, no ADMIT, no ledger writes, no invented
values. Every injected press the fixture emits is labelled INJECTED and must
never be presented as natural input.
"""
import hashlib
import importlib.util
import json
import re
from pathlib import Path

CAVE_ID = "forest-p1"
ISSUE = 660
GUARD_PATH = "scripts/p2_fixture_captain_guard.h"
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"

INJECTED_PREFIX = "P2_FOREST_INPUT_INJECTED"
CLEARED_PREFIX = "P2_FOREST_INPUT_CLEARED"
SUMMARY_PREFIX = "P2_FOREST_INPUT_SUMMARY"
WINDOW_PREFIX = "P2_FOREST_P1_INPUT_WINDOW"
ENGINE_FACT_PREFIX = "P2_FOREST_P1_INPUT_ENGINE_FACT"

# Advance evidence: engine log lines proving the UI moved past the wait.
# The save manager announces itself when input starts it; any later UI
# screen load after injection began also counts (compared against the
# pre-injection baseline, never assumed).
SAVE_START_RE = re.compile(r"SAVE Mgr START", re.IGNORECASE)
UI_LOAD_RE = re.compile(r"ui[_ ]screen.*load|loading screen|Screen.*Load|"
                        r"ogScr\w+\s+load|map.?select", re.IGNORECASE)

INJECTED_TOKENS = ("P2_FOREST_P1_INJECT", "forest-p1-inject", "injection=1")
FAIL_TOKENS = ("P2_FIXTURE_CAPTAIN_DOWN", "duplicate treasure",
               "P2 preview: duplicate")


class InjectionError(ValueError):
    """Malformed input, missing prerequisite, or illegal run configuration."""


def workspace_root():
    return Path(__file__).resolve().parents[2]


def sha256_file(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


STAGED_RERUN_ADAPTER = ("output/workflow/autofill/planning-shards/overworld-forest/"
                        "prepared/forest-p1-staged-rerun-root/experimental/"
                        "pikmin2_forest_p1_staged_rerun.py")


def load_staged_rerun_adapter(adapter_path=None):
    """Import the done #660 staged-rerun adapter by path (reuse, never fork).

    The adapter lives in its own completed lane worktree, so the default is
    the canonical workspace location; callers may pass an explicit path.
    """
    canonical = Path("C:/Users/alari/pikmin-randomizer")
    path = Path(adapter_path) if adapter_path is not None else canonical / STAGED_RERUN_ADAPTER
    if not path.is_file():
        raise InjectionError("staged-rerun adapter missing: %s" % path)
    spec = importlib.util.spec_from_file_location("forest_p1_staged_rerun_ro", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage_injection_run(adapter, manifest_path, seed_path, source_snddata,
                        run_root, pins=None):
    """Stage a fresh injection run dir through the done adapter (read-only).

    Returns the adapter record plus this lane's run-config hash. The run dir
    must not exist; the arena bytes come from the accepted baseline.
    """
    run_root = Path(run_root)
    if run_root.exists():
        raise InjectionError("run dir must be fresh")
    record = adapter.stage_run_root(str(manifest_path), str(seed_path),
                                    str(source_snddata), str(run_root),
                                    dict(pins or {}))
    config = {"cave_id": CAVE_ID, "issue": ISSUE, "window": "960x540",
              "captain_guard": GUARD_PATH, "guard_sha256": GUARD_SHA256,
              "injection": "START/A pulses via pc_p2_input_script_set/clear, "
                           "alternating press/release windows; all presses labelled"}
    config_path = run_root / "forest-p1-input-injection.json"
    config_path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    record["injection_config_sha256"] = sha256_file(config_path)
    return record


def guard_record(root=None):
    """Hash the canonical #632 guard header read-only; fail closed on drift."""
    base = Path(root) if root is not None else workspace_root()
    path = base / Path(*GUARD_PATH.split("/"))
    if not path.is_file():
        raise InjectionError("guard header missing: %s" % GUARD_PATH)
    digest = sha256_file(path)
    if digest != GUARD_SHA256:
        raise InjectionError("guard header drifted: %s" % digest)
    return {"path": GUARD_PATH, "sha256": digest}


def split_injection_phases(text):
    """Split log lines into pre-injection and post-injection segments."""
    if not isinstance(text, str) or not text.strip():
        raise InjectionError("empty marker log")
    lines = text.splitlines()
    first = next((i for i, line in enumerate(lines)
                  if INJECTED_PREFIX in line), None)
    if first is None:
        return lines, []
    return lines[:first], lines[first:]


def read_run_log(text):
    """Parse a runtime marker log into observations with a strict verdict.

    Advance requires post-injection evidence the UI moved: the save-manager
    start announcement or a NEW UI screen load not present pre-injection.
    Returns (observations, passed). Injection markers alone never pass.
    """
    before, after = split_injection_phases(text)
    if any(token in text for token in INJECTED_TOKENS):
        return {"injected": True}, False
    injected = sum(1 for line in after if INJECTED_PREFIX in line)
    cleared = sum(1 for line in after if CLEARED_PREFIX in line)
    save_started = any(SAVE_START_RE.search(line) for line in after)
    before_screens = {line.strip() for line in before if UI_LOAD_RE.search(line)}
    new_screens = sorted({line.strip() for line in after
                          if UI_LOAD_RE.search(line)
                          and line.strip() not in before_screens})
    window = "960x540" in text
    squad = None
    match = re.search(r"squad_alive=(\d+)", text)
    if match:
        squad = int(match.group(1))
    failed = any(token in text for token in FAIL_TOKENS)
    failed = failed or re.search(r"(?:^|\s)FAIL(?:\s|$)", text) is not None
    observations = {"injected_presses": injected, "clears": cleared,
                    "save_started": save_started,
                    "new_ui_screens": new_screens,
                    "window_960": window, "squad_alive": squad,
                    "failed_tokens": failed}
    passed = (injected > 0 and (save_started or bool(new_screens))
              and not failed)
    return observations, passed
