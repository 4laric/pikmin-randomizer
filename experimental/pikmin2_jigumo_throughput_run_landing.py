"""Landing checker for the #167 jigumo63 throughput-run PASS evidence (#759).

Re-verifies the run artifacts hash-identical (read-only, no re-derivation)
and validates the recorded verdict: natural DEAD + carcass, HP-per-lost
ratio strictly above 25, zero captain-down, zero injections. Submits nothing
itself; the handoff + packet carry the evidence to the integrator for
downstream consumer shard-enemies-4-jigumo63-observer (#374) gate 4.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

RUN_DIR = Path(
    "C:/Users/alari/pikmin-randomizer/output/workflow/autofill/"
    "planning-shards/enemies-4/prepared/shard-enemies-4-jigumo63-throughput-run")
LOG = RUN_DIR / "out/jigumo573/fd633e8807f44d88abc8491428631483/native.log"
RESULT = RUN_DIR / "out/result.json"
FIXTURE_EXE = RUN_DIR / "fixture-build/fixture.exe"

EXPECTED = {
    "native.log": "88ee97daeecaf66a87ce9800b4f321e46ae30a09798c5da6b4aface0728b67ec",
    "result.json": "8c678156cb49f0625028e3945d8a448e481caa6c7381c2df735083d8398c8099",
    "fixture.exe": "64c13089758fe8ce669fccd877ebf987efdae8952cabc8db2439ee02b514bb48",
}

RUN_PINS = {
    "native_head": "859fe9bf9eb8dff029c5ecc1024f164e5fb4db6a",
    "native_exe_sha256": "66ea163d03f3c4d8627ec6831783e5701692011550463c2fb1dba237d27a9f12",
    "root_commits": [
        "975a971394b35608e0a03ee25d4fdb5085745b42",
        "3b9d467d4f30c3b163f81eccf790aca325581def",
        "accd844720442aa0136a222c27910f291177e304",
        "b1aa9c363f8608529cc0567482ffa0c62f96ff32",
        "75797053af7c84520c02c7c0382f9a5262a0fdc8",
    ],
    "observer_tests": 14,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reverify() -> dict:
    """Hash-check each artifact against the pinned evidence."""
    report = {}
    for name, path, expected in (("native.log", LOG, EXPECTED["native.log"]),
                                 ("result.json", RESULT, EXPECTED["result.json"]),
                                 ("fixture.exe", FIXTURE_EXE, EXPECTED["fixture.exe"])):
        if not path.is_file():
            report[name] = {"present": False, "match": False, "sha256": None}
            continue
        digest = sha256(path)
        report[name] = {"present": True, "match": digest == expected, "sha256": digest}
    report["all_match"] = all(v["match"] for v in report.values() if isinstance(v, dict))
    return report


def validate_run() -> dict:
    """Validate the recorded supervisor verdict (read-only)."""
    record = json.loads(RESULT.read_text(encoding="utf-8"))
    verdict = {
        "exit": record.get("exit"),
        "dead": record.get("dead") is True,
        "carcass": record.get("carcass") is True,
        "lost": record.get("lost"),
        "ratio": record.get("ratio"),
        "ratio_above_25": isinstance(record.get("ratio"), (int, float)) and record["ratio"] > 25.0,
        "captain_down": record.get("captain_down") is True,
        "injected": record.get("injected") or [],
        "bites": record.get("bites"),
        "eats": record.get("eats"),
        "flicks": record.get("flicks"),
        "passed": record.get("passed") is True,
    }
    verdict["evidence_intact"] = bool(
        verdict["dead"] and verdict["carcass"] and verdict["ratio_above_25"]
        and not verdict["captain_down"] and not verdict["injected"] and verdict["passed"])
    return verdict


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(description="Re-verify #167 run evidence for landing")
    parser.add_argument("--json", default="")
    args = parser.parse_args(argv)
    hashes = reverify()
    verdict = validate_run()
    for name, item in hashes.items():
        if name == "all_match":
            continue
        print("%s present=%s match=%s" % (name, item["present"], item["match"]))
    print("dead=%s carcass=%s ratio=%s captain_down=%s passed=%s evidence_intact=%s" % (
        verdict["dead"], verdict["carcass"], verdict["ratio"],
        verdict["captain_down"], verdict["passed"], verdict["evidence_intact"]))
    if args.json:
        Path(args.json).write_text(json.dumps(
            {"hashes": hashes, "verdict": verdict, "pins": RUN_PINS}, indent=1), encoding="utf-8")
    if not hashes["all_match"]:
        print("LANDING BLOCKED hash-mismatch")
        return 2
    if not verdict["evidence_intact"]:
        print("LANDING BLOCKED verdict-changed")
        return 1
    print("LANDING READY evidence intact for #374 gate 4 (no gate claimed here)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
