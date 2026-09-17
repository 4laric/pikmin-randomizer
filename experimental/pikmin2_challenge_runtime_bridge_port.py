#!/usr/bin/env python3
"""Evidence verifier for lane challenge-runtime-bridge-port-native (#722).

Fail-closed checker over the compiled + marker evidence. It never claims what
the evidence does not show: the build must be clean, the fixture must pass its
guard checks, and the headed marker log must show BOOT before the tick stream
with no captain-down. Stdlib only.
"""
import argparse
import hashlib
import json
import os
import sys

BOOT = "P2_CHALLENGE_MODE_BOOT"
TICKS = ("P2CHALLENGE_WIRING_TICK", "P2_CHALLENGE_MODE_TICK")
DOWN = "P2_FIXTURE_CAPTAIN_DOWN"


def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def verify_bundle(out_dir):
    problems = []
    report = {"out_dir": out_dir, "checks": {}}
    try:
        records = sorted(f for f in os.listdir(out_dir)
                         if f.startswith("build-record-") and f.endswith(".json"))
        record = json.load(open(os.path.join(out_dir, records[-1]),
                                encoding="utf-8"))
        report["build_record"] = records[-1]
    except (OSError, ValueError, IndexError) as exc:
        return False, report, ["unreadable build record: %s" % exc]

    steps = record.get("steps", {})
    build_ok = all(steps.get(n, {}).get("exit") == 0
                   for n in ("configure", "pikmin_pc", "dry_run",
                             "fixture_compile", "fixture_link", "self_test"))
    build_ok = build_ok and steps.get("negative_test", {}).get("exit") == 86
    if not build_ok:
        problems.append("build record does not show a clean build + guard checks")
    report["checks"]["build"] = build_ok

    marker_path = os.path.join(out_dir, "marker-run.log")
    try:
        text = open(marker_path, encoding="utf-8", errors="replace").read()
    except OSError as exc:
        return False, report, problems + ["unreadable marker log: %s" % exc]
    report["marker_log"] = {"path": "marker-run.log",
                            "sha256": sha256_file(marker_path)}
    boot = BOOT in text
    ticks = sum(text.count(t) for t in TICKS)
    down = DOWN in text
    boot_first = boot and ticks > 0 and text.index(BOOT) < min(
        text.index(t) for t in TICKS if t in text)
    run_ok = boot_first and ticks > 0 and not down
    if not run_ok:
        problems.append("marker log does not show BOOT before a clean tick stream")
    report["checks"]["marker_run"] = {
        "boot_marker": boot, "tick_markers": ticks, "captain_down": down,
        "boot_before_ticks": bool(boot_first), "pass": bool(run_ok)}
    exe_ok = bool(record.get("exe_sha256"))
    if not exe_ok:
        problems.append("executable hash missing")
    report["checks"]["executable"] = exe_ok
    return (not problems), report, problems


def main(argv=None):
    parser = argparse.ArgumentParser(description="Verify #722 bridge evidence")
    parser.add_argument("--dir", required=True)
    args = parser.parse_args(argv)
    ok, report, problems = verify_bundle(args.dir)
    print(json.dumps(report, indent=1, sort_keys=True))
    for problem in problems:
        print("REFUSED %s" % problem)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
