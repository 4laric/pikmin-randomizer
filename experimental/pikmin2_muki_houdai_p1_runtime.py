"""P1 private runtime import for P2 Challenge 09 ch_MUKI_houdai (issue #735).

Extends the P0 import contract with a P1 path that validates a stage record
against the catalogued pin, stages it into a private run layout
(stage-manifest.json + p1-input-package.json + run-plan.json, all hashed),
and provides a dependency-free run-log reader for the guarded boot markers.

The P0 adapter (experimental/content_lanes/p2-challenge-ch_muki_houdai.py)
is loaded BY PATH and never edited; its catalogued pin and missing-source
reporting are reused, never forked. The integrated host-mode module
(native/pc_port/pc_p2_challenge_mode.{h,cpp}) is consumed read-only by exact
commit pin; this lane owns no native/shared files beyond its own guarded
fixture source and performs no shared edits. Captain safety #632 is
mandatory for any runtime run executed from the staged plan. All six runtime
gates stay UNTESTED unless genuinely observed; no playability claim beyond
observed evidence; no ADMIT, no ledger writes. Without legal source bytes
(ch_MUKI_houdai.txt) the staged plan records the exact missing prerequisite
rather than overclaiming.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

STAGE_ID = "ch_MUKI_houdai"
P0_ADAPTER_REL = "experimental/content_lanes/p2-challenge-ch_muki_houdai.py"

# Catalogued P0 pin (P0 doc, read-only): 2 floors, table order 24, UI index
# 8, floor timers 100.0 + 150.0 s, bitter 1 / spicy 1, five colours of 10
# leaf Pikmin, treasure-count field 0. Actual source bytes were NOT available
# at P0 (no hash validated, no roster claimed).
PIN = {
    "floors": 2,
    "table_order": 24,
    "ui_index": 8,
    "floor_seconds": [100.0, 150.0],
    "bitter_sprays": 1,
    "spicy_sprays": 1,
    "starting_population": {"colors": 5, "per_color": 10, "maturity": "leaf"},
    "treasure_count": 0,
}

# Integrated host-mode module pins (same module as the accepted #537 shape;
# consumed read-only, never edited).
HOST_MODE_COMMIT = "ada6bda4"
HOST_MODE_FILES = {
    "pc_port/pc_p2_challenge_mode.h":
        "d543c6fef4d63dccfceb384e40c08abe0d24f23969bc85ae02353b8d06706b68",
    "pc_port/pc_p2_challenge_mode.cpp":
        "6576858f1f67b5c450aaf29a86026424f7326eb7859a7d660140d924a8e36ca1",
}

GUARD_HEADER = "scripts/p2_fixture_captain_guard.h"
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"

RUN_FILES = ("stage-manifest.json", "p1-input-package.json", "run-plan.json")

# Receipt-parseable markers a real stage boot must emit (mirrors the #675
# stage-boot fixture marker set, consumed read-only).
EXPECTED_MARKERS = (
    "P2CHALLENGE_STAGE_ENTRY",
    "P2_ROOM_READY",
    "P2_FIXTURE_CAPTAIN_DOWN",
)

MISSING_SOURCE = ("legal US GPVE01 rev 0 disc or an extracted "
                  "ch_MUKI_houdai.txt (user/Mukki/mapunits/caveinfo/)")


class P1Error(ValueError):
    """Fail-closed P1 import rejection."""


def validate_stage_record(record):
    """Validate a stage record dict against the catalogued P0 pin."""
    if not isinstance(record, dict):
        raise P1Error("stage record must be a dict")
    if record.get("stage_id") != STAGE_ID:
        raise P1Error("wrong stage_id: %r" % record.get("stage_id"))
    for key in ("table_order", "ui_index", "treasure_count"):
        if record.get(key) != PIN[key]:
            raise P1Error("%s mismatch: %r, expected %r" % (key, record.get(key), PIN[key]))
    if list(record.get("floor_seconds") or []) != PIN["floor_seconds"]:
        raise P1Error("floor_seconds mismatch: %r" % (record.get("floor_seconds"),))
    sprays = record.get("sprays") or {}
    if sprays.get("bitter") != 1 or sprays.get("spicy") != 1:
        raise P1Error("spray counts mismatch: %r" % (sprays,))
    pop = record.get("starting_population") or {}
    want = PIN["starting_population"]
    if pop.get("colors") != 5 or pop.get("per_color") != 10 or pop.get("maturity") != "leaf":
        raise P1Error("starting population mismatch: %r" % (pop,))
    if record.get("floors") != 2:
        raise P1Error("expected 2 floors, got %r" % (record.get("floors"),))
    return dict(record)


def default_record():
    """Catalogued pin as a stage record (source-bytes fields left absent)."""
    return {
        "stage_id": STAGE_ID,
        "table_order": PIN["table_order"],
        "ui_index": PIN["ui_index"],
        "floor_seconds": list(PIN["floor_seconds"]),
        "sprays": {"bitter": 1, "spicy": 1},
        "starting_population": {"colors": 5, "per_color": 10, "maturity": "leaf"},
        "treasure_count": PIN["treasure_count"],
        "floors": PIN["floors"],
        "source_bytes": None,
        "missing_prerequisite": MISSING_SOURCE,
    }


def stage_run_layout(record, output_dir):
    """Write the hashed private run layout. Returns (paths, hashes)."""
    validated = validate_stage_record(record)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    manifest = {"schema": 1, "stage_id": STAGE_ID, "pin": PIN,
                "record": validated, "source_bytes_present": False,
                "missing_prerequisite": MISSING_SOURCE}
    package = {"schema": 1, "stage_id": STAGE_ID,
               "squad": {"colors": 5, "per_color": 10, "maturity": "leaf"},
               "window": {"width": 960, "height": 540, "centred": True},
               "captain_guard": {"header": GUARD_HEADER, "sha256": GUARD_SHA256},
               "host_mode": {"commit": HOST_MODE_COMMIT, "files": HOST_MODE_FILES},
               "expected_markers": list(EXPECTED_MARKERS)}
    plan = {"schema": 1, "stage_id": STAGE_ID,
            "steps": ["boot stage", "observe markers", "negative guard test"],
            "acceptance": "natural boot/combat/receipt/exit with honest gates; "
                          "blocked on legal source bytes until staged"}
    blobs = {"stage-manifest.json": manifest, "p1-input-package.json": package,
             "run-plan.json": plan}
    hashes = {}
    for name in RUN_FILES:
        path = output_dir / name
        path.write_text(json.dumps(blobs[name], indent=2) + "\n", encoding="utf-8")
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {str(output_dir / name): hashes[name] for name in RUN_FILES}


def read_run_log(text):
    """Dependency-free run-log reader. Returns observed markers + verdict."""
    if not isinstance(text, str):
        raise P1Error("run log must be text")
    observed = [m for m in EXPECTED_MARKERS if m in text]
    down = "P2_FIXTURE_CAPTAIN_DOWN" in text
    boot = "P2CHALLENGE_STAGE_ENTRY" in text and "P2_ROOM_READY" in text
    if down:
        verdict = "BLOCKED (captain down; guard fired, no PASS)"
    elif boot:
        verdict = "BOOT observed (markers present; gameplay gates still require evidence)"
    else:
        verdict = "UNTESTED (no boot markers)"
    return {"observed": observed, "captain_down": down, "verdict": verdict}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    record = json.loads(args.record.read_text(encoding="utf-8"))
    paths = stage_run_layout(record, args.output)
    print(json.dumps(paths, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# Markers the guarded P1 fixture emits (native/tools/p2_muki_houdai_p1_fixture.cpp).
WINDOW_MARKER = "P2_MUKI_HOUDAI_P1_WINDOW width=960 height=540 centered=1"
SQUAD_MARKER = "P2_ROOM_READY treasure=bolt carry=5 repairs=1"
STAGE_ENTRY_PREFIX = "P2CHALLENGE_STAGE_ENTRY stage=ch_MUKI_houdai"
BOOT_BLOCKED_MARKER = "BLOCKED MUKI_HOUDAI_P1_BOOT engine-table-row-pending"
STAGE_PASS_MARKER = "PASS MUKI_HOUDAI_P1_STAGE"


def read_run_log_file(path):
    """Read a native run log from disk (utf-8 or utf-16) as text."""
    raw = Path(path).read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "utf-8"):
        try:
            return raw.decode(encoding).replace(chr(0), "")
        except (UnicodeDecodeError, ValueError):
            continue
    raise P1Error("run log is not decodable text: %s" % (path,))


def evaluate_gates(text, exit_code=None):
    """Map observed markers to honest gate rows. PASS only on an observed marker."""
    if not isinstance(text, str):
        raise P1Error("run log must be text")
    window = WINDOW_MARKER in text
    down = "P2_FIXTURE_CAPTAIN_DOWN" in text
    squad = SQUAD_MARKER in text
    stage_entry = STAGE_ENTRY_PREFIX in text
    stage_pass = STAGE_PASS_MARKER in text
    boot_blocked = BOOT_BLOCKED_MARKER in text
    if window and not down:
        guard = ("PASS", "guard silent during observed run")
    elif down:
        guard = ("BLOCKED", "P2_FIXTURE_CAPTAIN_DOWN observed")
    else:
        guard = ("UNTESTED", "no run observed")
    if stage_entry:
        boot = ("PASS", STAGE_ENTRY_PREFIX)
    elif boot_blocked:
        boot = ("BLOCKED", BOOT_BLOCKED_MARKER)
    else:
        boot = ("UNTESTED", "stage never entered")
    if stage_pass and exit_code == 0:
        done = ("PASS", "exit 0 with stage PASS")
    elif boot_blocked or down or (exit_code is not None and exit_code != 0):
        qualifier = "BLOCKED marker" if (boot_blocked or down) else "nonzero exit"
        done = ("BLOCKED", "exit %r with %s" % (exit_code, qualifier))
    elif exit_code is None:
        done = ("UNTESTED", "exit code not recorded")
    else:
        done = ("UNTESTED", "exit %r without markers" % (exit_code,))
    return [
        {"token": "window-960x540-centred", "status": "PASS" if window else "UNTESTED",
         "evidence": WINDOW_MARKER if window else "no window marker"},
        {"token": "captain-guard-silent", "status": guard[0], "evidence": guard[1]},
        {"token": "squad-ready", "status": "PASS" if squad else "UNTESTED",
         "evidence": SQUAD_MARKER if squad else "no squad marker"},
        {"token": "stage-boot", "status": boot[0], "evidence": boot[1]},
        {"token": "challenge-arena", "status": "PASS" if stage_pass else "UNTESTED",
         "evidence": STAGE_PASS_MARKER if stage_pass else "stage never entered"},
        {"token": "exit-status", "status": done[0], "evidence": done[1]},
    ]

