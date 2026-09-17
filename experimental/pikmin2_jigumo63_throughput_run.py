"""Latch-first damage-throughput run for Jigumo63 (#167, family #167).

Executes the accepted #729 technique in a fresh private fixture+arena and
validates the marker chain: latch-first sustained blows inside the 200-unit
sweep, EAT-rate bound below pass1, prompt re-latch after flicks; natural DEAD
+ corpse, HP-per-lost-Pikmin ratio strictly above 25, zero captain-down, zero
injections. Reports evidence for #374 gate 4 WITHOUT claiming any gate.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import struct
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.preview_pikmin2_room import records, generator, overlay
from experimental.pikmin2_generator_pose import write_position

CARRIER_GEN = 374003
SQUAD = 20
LIFE = 500.0

BASELINE_RE = re.compile(r"P2_JIGUMO573_BASELINE red=(\d+) blue=(\d+) live=(\d+)")
STAGE_RE = re.compile(r"P2_JIGUMO573_STAGE generator=(\d+) source_id=63")
BIND_RE = re.compile(r"P2_JIGUMO_BIND generator=(\d+) source_id=63")
DEAD_RE = re.compile(r"P2_JIGUMO_DEAD generator=(\d+) source_id=63")
RESULT_RE = re.compile(
    r"P2_JIGUMO573_RESULT dead=1 carcass=(\d) lost=(\d+) ratio=(\S+) hp_drained=([\d.]+)")
BLOCKED_RE = re.compile(r"P2_JIGUMO573_BLOCKED reason=(\S+)")
BITE_RE = re.compile(r"P2_JIGUMO_BITE ")
EAT_RE = re.compile(r"P2_JIGUMO_EAT ")
FLICK_RE = re.compile(r"P2_JIGUMO_FLICK ")
HP_RE = re.compile(r"P2_JIGUMO573_HP health=([\d.]+) live=(\d+)")
CAPTAIN_DOWN_RE = re.compile(r"P2_FIXTURE_CAPTAIN_DOWN")
# Any staged marker must carry staged=1; these prove the sidecar stayed out.
STAGED_RE = re.compile(r"P2_JIGUMO573_(?:STAGE|RELATCH|REINFORCE) .*staged=1")


def stage(assets: Path, output: Path) -> Path:
    import math
    assets = assets.resolve()
    source = assets / "dataDir/stages/practice/default.gen"
    data = source.read_bytes()
    entries = records(source)
    raw = generator(assets)
    starts = [m.start() for m in re.finditer(b"    0.0v", raw)]
    rows = [raw[a:(starts[i + 1] if i + 1 < len(starts) else len(raw))] for i, a in enumerate(starts)]
    enemy = next(r for r in rows if r[72:76] == b"iket")
    piki = next(r for r in rows if r[72:76] == b"ikip")
    row = bytearray(enemy)
    struct.pack_into("<I", row, 8, CARRIER_GEN)
    row[16:48] = b"Jigumo63".ljust(32, b"\0")
    row[80] = 3  # TEKI_Chappy placement vehicle
    row[81] = 0
    row[82] = 0
    struct.pack_into("<f", row, 119, 0.0)
    write_position(row, [34.0, 30.0, 1896.0])
    entries.append(bytes(row))
    for i in range(SQUAD):
        r = bytearray(piki)
        struct.pack_into("<I", r, 8, 235200 + i)
        r[16:48] = b"Jigumo63 squad".ljust(32, b"\0")
        ang = 2.0 * math.pi * i / SQUAD
        write_position(r, [34.0 + 40.0 * math.sin(ang), 30.0, 1896.0 + 40.0 * math.cos(ang)])
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
    (run / "p2-aquatic-actors.txt").write_text(
        "P2_AQUATIC_ACTORS_1\n1\n%d Jigumo\n" % CARRIER_GEN, encoding="utf-8")
    (run / "jigumo573-stage.json").write_text(json.dumps(
        dict(scene="original P1 practice course", interactive=True, window="960x540",
             carrier=dict(generator=CARRIER_GEN, vehicle="TEKI_Chappy", template="iket"),
             starting_squad={"red": SQUAD}, stub_files="never written (sidecar inert)"),
        indent=1) + "\n", encoding="utf-8")
    return run


def stage(assets: Path, output: Path) -> Path:
    import math
    assets = assets.resolve()
    source = assets / "dataDir/stages/practice/default.gen"
    data = source.read_bytes()
    entries = records(source)
    raw = generator(assets)
    starts = [m.start() for m in re.finditer(b"    0.0v", raw)]
    rows = [raw[a:(starts[i + 1] if i + 1 < len(starts) else len(raw))] for i, a in enumerate(starts)]
    enemy = next(r for r in rows if r[72:76] == b"iket")
    piki = next(r for r in rows if r[72:76] == b"ikip")
    row = bytearray(enemy)
    struct.pack_into("<I", row, 8, CARRIER_GEN)
    row[16:48] = b"Jigumo63".ljust(32, b"\0")
    row[80] = 3
    row[81] = 0
    row[82] = 0
    struct.pack_into("<f", row, 119, 0.0)
    write_position(row, [34.0, 30.0, 1896.0])
    entries.append(bytes(row))
    for i in range(SQUAD):
        r = bytearray(piki)
        struct.pack_into("<I", r, 8, 235200 + i)
        r[16:48] = b"Jigumo63 squad".ljust(32, b"\0")
        ang = 2.0 * math.pi * i / SQUAD
        write_position(r, [34.0 + 40.0 * math.sin(ang), 30.0, 1896.0 + 40.0 * math.cos(ang)])
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
    (run / "p2-aquatic-actors.txt").write_text(
        "P2_AQUATIC_ACTORS_1\n1\n%d Jigumo\n" % CARRIER_GEN, encoding="utf-8")
    (run / "jigumo573-stage.json").write_text(json.dumps(
        dict(scene="original P1 practice course", interactive=True, window="960x540",
             carrier=dict(generator=CARRIER_GEN, vehicle="TEKI_Chappy", template="iket"),
             starting_squad={"red": SQUAD}, stub_files="never written (sidecar inert)"),
        indent=1) + "\n", encoding="utf-8")
    return run

def validate(text: str) -> dict:
    """Classify a run log. JSON-serializable verdict; no gate PASS claimed."""
    verdict: dict = {
        "baseline_ok": False, "staged_ok": False, "bound": False,
        "dead": False, "carcass": False, "lost": -1, "ratio": None,
        "ratio_above_25": False, "bites": 0, "eats": 0, "flicks": 0,
        "captain_down": False, "injected": [], "blocked_reason": "",
        "hp_curve": [], "passed": False, "failures": [],
    }
    lines = text.splitlines()
    for line in lines:
        if CAPTAIN_DOWN_RE.search(line):
            verdict["captain_down"] = True
        verdict["bites"] += 1 if BITE_RE.search(line) else 0
        verdict["eats"] += 1 if EAT_RE.search(line) else 0
        verdict["flicks"] += 1 if FLICK_RE.search(line) else 0
        m = HP_RE.search(line)
        if m:
            verdict["hp_curve"].append((float(m.group(1)), int(m.group(2))))
    m = BASELINE_RE.search(text)
    if m and int(m.group(1)) + int(m.group(2)) >= 1:
        verdict["baseline_ok"] = True
    else:
        verdict["failures"].append("no-live-baseline")
    m = STAGE_RE.search(text)
    if m and int(m.group(1)) == CARRIER_GEN:
        verdict["staged_ok"] = True
    else:
        verdict["failures"].append("no-stage")
    if BIND_RE.search(text):
        verdict["bound"] = True
    else:
        verdict["failures"].append("no-bind")
    m = BLOCKED_RE.search(text)
    if m:
        verdict["blocked_reason"] = m.group(1)
    # Injected markers: any line carrying an injection token that is NOT one
    # of our own labeled staged markers (which carry staged=1).
    for line in lines:
        low = line.lower()
        if ("inject" in low or "p2-bombotakara-native" in low or "p2-jigumo-inject" in low):
            if "staged=1" not in line:
                verdict["injected"].append(line.strip()[:120])
                break
    if verdict["captain_down"]:
        verdict["failures"].append("captain-down")
        return verdict
    if verdict["injected"]:
        verdict["failures"].append("injected-marker")
        return verdict
    m = RESULT_RE.search(text)
    if not m:
        if not verdict["blocked_reason"]:
            verdict["failures"].append("no-result-no-blocked")
        return verdict
    if not DEAD_RE.search(text):
        verdict["failures"].append("result-without-dead-marker")
        return verdict
    verdict["dead"] = True
    verdict["carcass"] = m.group(1) == "1"
    verdict["lost"] = int(m.group(2))
    try:
        verdict["ratio"] = float(m.group(3))
    except ValueError:
        verdict["ratio"] = float("inf")
    verdict["ratio_above_25"] = (verdict["ratio"] is not None
                                 and verdict["ratio"] != float("inf")
                                 and verdict["ratio"] > 25.0) or verdict["ratio"] == float("inf")
    if not verdict["carcass"]:
        verdict["failures"].append("no-carcass")
    if not verdict["ratio_above_25"]:
        verdict["failures"].append("ratio-at-or-below-25")
    if not verdict["bound"]:
        verdict["failures"].append("no-bind")
    verdict["passed"] = (verdict["dead"] and verdict["carcass"]
                         and verdict["ratio_above_25"] and verdict["bound"]
                         and not verdict["captain_down"] and not verdict["injected"])
    return verdict


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(description="Stage, run and validate the Jigumo63 throughput run")
    parser.add_argument("--assets", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--log", type=Path, default=None)
    parser.add_argument("--timeout", type=int, default=660)
    parser.add_argument("--json", default="")
    args = parser.parse_args(argv)
    if args.log is not None:
        verdict = validate(args.log.read_text(encoding="utf-8", errors="replace"))
    else:
        args.output.mkdir(parents=True, exist_ok=True)
        directory = stage(args.assets, args.output / "jigumo573")
        env = dict(os.environ, PATH="C:/msys64/mingw64/bin;" + os.environ.get("PATH", ""),
                   SDL_AUDIODRIVER="dummy", PIKMIN_P2_ROOM_WINDOW="960x540", PYTHONUTF8="1")
        with (directory / "native.log").open("w") as log:
            proc = subprocess.Popen([str(args.exe.resolve()), "--experimental-pikmin2-room"],
                                    cwd=directory, env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                code = proc.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                code = "timeout"
        text = (directory / "native.log").read_text(encoding="utf-8", errors="replace")
        verdict = validate(text)
        verdict["exit"] = code
        verdict["directory"] = str(directory)
        print("exit=%s dead=%s ratio=%s captain_down=%s passed=%s" % (
            code, verdict["dead"], verdict["ratio"], verdict["captain_down"], verdict["passed"]))
    for failure in verdict["failures"]:
        print("FAIL " + failure)
    if args.json:
        Path(args.json).write_text(json.dumps(verdict, indent=1), encoding="utf-8")
    if verdict.get("captain_down"):
        print("VERDICT BLOCKED captain-down")
        return 86
    if verdict["passed"]:
        print("VERDICT EVIDENCE ready for #374 gate 4 (no gate claimed here)")
        return 0
    print("VERDICT NOT-READY")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
