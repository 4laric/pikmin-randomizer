"""ch_MUKI_redblue P1 runtime runner + observer (#744, P2 Challenge 19).

Stages a fresh practice-overlay arena (chal0 slot) with a live red squad and
the #743 staged boot-request for ch_MUKI_redblue, then classifies the
fixture native.log. Pure stage + log classifier: launching uses canonical
scripts/run_pikmin2_fixture.py. Six gates stay UNTESTED unless observed;
this turn expects the fail-closed row-pending refusal until #748 lands.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import struct
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.preview_pikmin2_room import records, generator, overlay
from experimental.pikmin2_generator_pose import write_position
from experimental.pikmin2_challenge_gap_stages_select import (
    select_stage_extended, render_boot_request_extended, GapStagesError)

STAGE_ID = "ch_MUKI_redblue"
SQUAD = 8
LIFE = 500.0

BASELINE_RE = re.compile(r"P2_MUKI_REDBLUE_P1_BASELINE red=(\d+) blue=(\d+)")
WINDOW_RE = re.compile(r"P2_MUKI_REDBLUE_P1_WINDOW width=(\d+) height=(\d+) centered_call=1")
CONTROL_RE = re.compile(r"P2_MUKI_REDBLUE_P1_CONTROL_OK control=chal0")
SELECT_RE = re.compile(r"P2_MUKI_REDBLUE_P1_SELECT_RESOLVED cave=ch_MUKI_redblue")
ROW_RESOLVED_RE = re.compile(r"P2_MUKI_REDBLUE_P1_ROW_RESOLVED stage=ch_MUKI_redblue")
ROW_PENDING_RE = re.compile(r"BLOCKED P2_MUKI_REDBLUE_P1_BOOT engine-table-row-pending stage=ch_MUKI_redblue")
BOOT_PASS_RE = re.compile(r"PASS P2_MUKI_REDBLUE_P1_BOOT stage=ch_MUKI_redblue")
REFUSED_RE = re.compile(r"P2_MUKI_REDBLUE_P1_REFUSED reason=(\S+)")
NO_REQUEST_RE = re.compile(r"BLOCKED P2_MUKI_REDBLUE_P1_BOOT reason=no-valid-boot-request")
CAPTAIN_DOWN_RE = re.compile(r"P2_FIXTURE_CAPTAIN_DOWN")


def select_redblue():
    """Resolve ch_MUKI_redblue through the adopted #743 selector."""
    record, provenance = select_stage_extended(STAGE_ID)
    return record, provenance, render_boot_request_extended(record)


def boot_request_text() -> str:
    """Render the staged #743 boot-request for redblue (raises on refusal)."""
    return select_redblue()[2]


def stage(assets: Path, output: Path) -> Path:
    import math
    assets = assets.resolve()
    record, provenance, boot_text = select_redblue()
    source = assets / "dataDir/stages/practice/default.gen"
    data = source.read_bytes()
    entries = records(source)
    raw = generator(assets)
    starts = [m.start() for m in re.finditer(b"    0.0v", raw)]
    rows = [raw[a:(starts[i + 1] if i + 1 < len(starts) else len(raw))] for i, a in enumerate(starts)]
    piki = next(r for r in rows if r[72:76] == b"ikip")
    for i in range(SQUAD):
        r = bytearray(piki)
        struct.pack_into("<I", r, 8, 235200 + i)
        r[16:48] = b"RedblueP1 squad".ljust(32, b"\0")
        ang = 2.0 * math.pi * i / SQUAD
        write_position(r, [60.0 + 40.0 * math.sin(ang), 30.0, 1850.0 + 40.0 * math.cos(ang)])
        struct.pack_into(">I", r, 92, 1)
        entries.append(bytes(r))
    data = data[:20] + struct.pack(">I", len(entries)) + b"".join(entries)
    run = Path(output).resolve() / uuid.uuid4().hex
    run.mkdir(parents=True)
    empty = data[:20] + struct.pack(">I", 0)
    overrides = {"dataDir/stages/chal0.ini": (assets / "dataDir/stages/practice.ini").read_bytes(),
                 "dataDir/stages/chal0/default.gen": data}
    for p in (assets / "dataDir/stages/chal0").glob("*.gen"):
        overrides.setdefault("dataDir/stages/chal0/" + p.name, empty)
    overlay(assets, run / "assets", overrides)
    (run / "p2-cargo-free.txt").write_bytes(b"P2_CARGO_FREE_1\n")
    (run / "p2-challenge-boot-request.txt").write_text(boot_text, encoding="utf-8")
    (run / "p2-session.json").write_text(json.dumps(
        {"schema": 1, "stage_id": STAGE_ID, "selector_provenance": provenance,
         "note": "preview-room boot probe; native row pending #748"}, indent=1) + "\n",
        encoding="utf-8")
    return run


def validate(text: str) -> dict:
    """Classify a run log. JSON-serializable verdict; gates UNTESTED unless observed."""
    verdict: dict = {
        "baseline_ok": False, "window_ok": False, "control_ok": False,
        "select_resolved": False, "row_resolved": False, "row_pending": False,
        "boot_pass": False, "refused_reason": "", "no_request": False,
        "baseline_red": 0, "captain_down": False, "injected": [],
        "gates": {"boot": "UNTESTED", "arena": "UNTESTED", "gameplay": "UNTESTED",
                  "exit": "UNTESTED", "guard": "UNTESTED", "squad": "UNTESTED"},
        "gate_identity_spawn": False, "gate_attacks_receivers": False,
        "gate_other": "untested",
        "passed": False, "failures": [],
    }
    lines = text.splitlines()
    if CAPTAIN_DOWN_RE.search(text):
        verdict["captain_down"] = True
    m = BASELINE_RE.search(text)
    if m and int(m.group(1)) >= 1:
        verdict["baseline_ok"] = True
        verdict["baseline_red"] = int(m.group(1))
        verdict["gates"]["squad"] = "PASS"
    else:
        verdict["failures"].append("no-live-baseline")
    m = WINDOW_RE.search(text)
    if m and (int(m.group(1)), int(m.group(2))) == (960, 540):
        verdict["window_ok"] = True
    else:
        verdict["failures"].append("window-not-960x540")
    if CONTROL_RE.search(text):
        verdict["control_ok"] = True
    else:
        verdict["failures"].append("control-chal0-unresolved")
    if SELECT_RE.search(text):
        verdict["select_resolved"] = True
    else:
        verdict["failures"].append("no-select-resolved")
    if ROW_RESOLVED_RE.search(text):
        verdict["row_resolved"] = True
    if ROW_PENDING_RE.search(text):
        verdict["row_pending"] = True
    if BOOT_PASS_RE.search(text):
        verdict["boot_pass"] = True
        verdict["gates"]["boot"] = "PASS"
    m = REFUSED_RE.search(text)
    if m:
        verdict["refused_reason"] = m.group(1)
    if NO_REQUEST_RE.search(text):
        verdict["no_request"] = True
        verdict["failures"].append("no-valid-boot-request")
    for line in lines:
        low = line.lower()
        if ("inject" in low or "p2-muki-redblue-inject" in low) and "staged=1" not in line:
            verdict["injected"].append(line.strip()[:120])
            break
    if verdict["captain_down"]:
        verdict["failures"].append("captain-down")
        verdict["gates"]["guard"] = "BLOCKED"
        return verdict
    verdict["gates"]["guard"] = "PASS"
    if verdict["injected"]:
        verdict["failures"].append("injected-marker")
        return verdict
    if verdict["row_pending"]:
        verdict["gates"]["boot"] = "BLOCKED"
        verdict["gates"]["exit"] = "BLOCKED"
    if verdict["boot_pass"] and verdict["row_resolved"]:
        verdict["gate_identity_spawn"] = True
        verdict["passed"] = True
    elif not verdict["row_pending"]:
        verdict["failures"].append("no-boot-no-row-pending")
    return verdict


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(description="Stage redblue arena / validate run log")
    parser.add_argument("--log", type=Path, default=None)
    parser.add_argument("--json", default="")
    parser.add_argument("--stage", nargs=2, metavar=("ASSETS", "OUTPUT"), default=None)
    args = parser.parse_args(argv)
    if args.stage is not None:
        directory = stage(Path(args.stage[0]), Path(args.stage[1]))
        print("STAGED_DIR=%s" % directory)
        return 0
    if args.log is None:
        parser.error("--log or --stage required")
    verdict = validate(args.log.read_text(encoding="utf-8", errors="replace"))
    print("baseline=%s window=%s control=%s select=%s row_resolved=%s row_pending=%s boot=%s passed=%s" % (
        verdict["baseline_ok"], verdict["window_ok"], verdict["control_ok"],
        verdict["select_resolved"], verdict["row_resolved"], verdict["row_pending"],
        verdict["boot_pass"], verdict["passed"]))
    for failure in verdict["failures"]:
        print("FAIL " + failure)
    if args.json:
        Path(args.json).write_text(json.dumps(verdict, indent=1), encoding="utf-8")
    if verdict.get("captain_down"):
        print("VERDICT BLOCKED captain-down")
        return 86
    if verdict["passed"]:
        print("VERDICT PASS redblue boot observed")
        return 0
    if verdict["row_pending"]:
        print("VERDICT BLOCKED engine-table-row-pending (#748)")
        return 3
    print("VERDICT NOT-READY")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
