#!/usr/bin/env python3
"""Evidence verifier for lane yakushima-p1-boot-stall-diagnosis (#717).

Fail-closed checker over the two contrasting diagnosis runs. It never claims
what the logs do not show:
  * the missing-asset run must reach `before-gsys-initialise`, never
    `after-gsys-initialise`, name the failed SndData members, and time out
    (the stall);
  * the staged-asset run must reach `P2_YAKUSHIMA_P1_DIAG_IDLE_RUNNING` with
    no timeout and no captain-down (the stall is data-dependent).
Stdlib only.
"""
import argparse
import hashlib
import json
import os
import sys

STALL_LOG = "diagnosis-run-jaudioon.log"
IDLE_LOG = "diagnosis-run-staged-assets.log"
FAILED_MEMBERS = ("dataDir/SndData/Seqs/pikiseq.arc",
                  "dataDir/SndData/Banks/pikibank.bx")


def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def verify_bundle(out_dir):
    problems = []
    report = {"out_dir": out_dir, "checks": {}}
    stall_path = os.path.join(out_dir, STALL_LOG)
    idle_path = os.path.join(out_dir, IDLE_LOG)
    for path in (stall_path, idle_path):
        if not os.path.isfile(path):
            return False, report, ["missing log: %s" % os.path.basename(path)]
    stall = open(stall_path, encoding="utf-8", errors="replace").read()
    idle = open(idle_path, encoding="utf-8", errors="replace").read()
    report["stall_log"] = {"path": STALL_LOG, "sha256": sha256_file(stall_path)}
    report["idle_log"] = {"path": IDLE_LOG, "sha256": sha256_file(idle_path)}

    stall_ok = (
        "phase=before-gsys-initialise" in stall
        and "phase=after-gsys-initialise" not in stall
        and all(m in stall for m in FAILED_MEMBERS)
        and "P2_YAKUSHIMA_P1_DIAG_TIMEOUT" in stall
        and "P2_YAKUSHIMA_P1_DIAG_IDLE_RUNNING" not in stall
    )
    if not stall_ok:
        problems.append("missing-asset run does not show the expected stall shape")
    report["checks"]["missing_asset_stall"] = stall_ok

    idle_ok = (
        "P2_YAKUSHIMA_P1_DIAG_IDLE_RUNNING" in idle
        and "P2_YAKUSHIMA_P1_DIAG_TIMEOUT" not in idle
        and "P2_FIXTURE_CAPTAIN_DOWN" not in idle
        and "phase=after-gsys-initialise" in idle
    )
    if not idle_ok:
        problems.append("staged-asset run does not show a clean idle-running boot")
    report["checks"]["staged_asset_idle"] = idle_ok

    try:
        records = sorted(f for f in os.listdir(out_dir)
                         if f.startswith("build-record-") and f.endswith(".json"))
        record = json.load(open(os.path.join(out_dir, records[-1]),
                                encoding="utf-8"))
        steps = record.get("steps", {})
        build_ok = all(steps.get(n, {}).get("exit") == 0
                       for n in ("configure", "pikmin_pc", "diagnosis_compile",
                                 "diagnosis_link", "self_test"))
        build_ok = build_ok and steps.get("negative_test", {}).get("exit") == 86
        report["build_record"] = records[-1]
    except (OSError, ValueError, IndexError) as exc:
        return False, report, problems + ["unreadable build record: %s" % exc]
    if not build_ok:
        problems.append("build record does not show a clean build + guard checks")
    report["checks"]["build"] = build_ok

    return (not problems), report, problems


def main(argv=None):
    parser = argparse.ArgumentParser(description="Verify #717 diagnosis evidence")
    parser.add_argument("--dir", required=True)
    args = parser.parse_args(argv)
    ok, report, problems = verify_bundle(args.dir)
    print(json.dumps(report, indent=1, sort_keys=True))
    for problem in problems:
        print("REFUSED %s" % problem)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
