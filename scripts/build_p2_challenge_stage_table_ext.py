"""Stage + build + run + validate the challenge stage extension table (#730).

Stages a fresh chal0 practice arena through the current overlay (live
starting squad), builds the guarded replacement-main fixture through the
canonical fixture builder, runs it once per stage key under the 960x540
baseline, and validates the marker chain with the owned observer. Prints
evidence paths and hashes. Launches nothing else.
"""
from __future__ import annotations

import argparse
import hashlib
import math
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
from experimental.pikmin2_challenge_stage_table_extension import validate


def sha256(path: Path) -> str:
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def stage(assets: Path, output: Path) -> Path:
    assets = assets.resolve()
    source = assets / "dataDir/stages/practice/default.gen"
    data = source.read_bytes()
    entries = records(source)
    raw = generator(assets)
    starts = [m.start() for m in re.finditer(b"    0.0v", raw)]
    rows = [raw[a:(starts[i + 1] if i + 1 < len(starts) else len(raw))] for i, a in enumerate(starts)]
    piki = next(r for r in rows if r[72:76] == b"ikip")
    for i in range(8):
        row = bytearray(piki)
        struct.pack_into("<I", row, 8, 236100 + i)
        row[16:48] = b"Stage table ext squad".ljust(32, b"\0")
        ang = 2.0 * math.pi * i / 8
        write_position(row, [60 + 40.0 * math.sin(ang), 30.0,
                             1850 + 40.0 * math.cos(ang)])
        struct.pack_into(">I", row, 92, 1)
        entries.append(bytes(row))
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
    (run / "stage-table-ext-stage.json").write_text(json.dumps(
        dict(scene="original P1 practice course", window="960x540",
             starting_squad={"red": 8}, stub_files="none"), indent=1) + "\n",
        encoding="utf-8")
    return run


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(description="Stage, build, run and validate the ext table")
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)
    results = {}
    for cave in ("ch_ABEM_LeafChappy", "ch_NARI_02tile"):
        directory = stage(args.assets, args.output / "ext")
        env = dict(os.environ, PATH="C:/msys64/mingw64/bin;" + os.environ.get("PATH", ""),
                   SDL_AUDIODRIVER="dummy", PIKMIN_P2_ROOM_WINDOW="960x540", PYTHONUTF8="1")
        with (directory / "native.log").open("w") as log:
            proc = subprocess.Popen(
                [str(args.exe.resolve()), "--experimental-pikmin2-room", "--ext-stage", cave],
                cwd=directory, env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                code = proc.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                code = "timeout"
        text = (directory / "native.log").read_text(encoding="utf-8", errors="replace")
        verdict = validate(text, cave)
        (args.output / ("result-%s.json" % cave)).write_text(
            json.dumps(verdict, indent=1), encoding="utf-8")
        print("%s exit=%s passed=%s dir=%s" % (cave, code, verdict["passed"], directory), flush=True)
        results[cave] = {"exit": code, "passed": verdict["passed"],
                         "directory": str(directory), "log_sha256": sha256(directory / "native.log")}
    print(json.dumps({"results": results,
                      "exe_sha256": sha256(args.exe.resolve())}, indent=1))
    return 0 if all(r["passed"] and r["exit"] == 0 for r in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

