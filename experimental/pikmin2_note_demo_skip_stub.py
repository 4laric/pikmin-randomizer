#!/usr/bin/env python3
"""Evidence verifier for lane audio-note-demo-skip-stub-native (#704).

Fail-closed checker over the lane's compiled artifacts. It never claims what
the evidence does not show: every check must pass, otherwise it reports the
exact problem and exits nonzero. Stdlib only.

Checks:
  1. The latest build-record shows configure exit 0 and default-config
     pikmin_pc exit 0, and every recorded executable hash matches its file.
  2. The stub object exists, its hash matches, and nm proved
     Jac_NoteDemoSkipped defined (symbol_defined true).
  3. The leased build log contains no
     "undefined reference to Jac_NoteDemoSkipped".
  4. The stub-test build log shows compile/link/run exit 0 and the
     PASS P2_NOTE_DEMO_SKIP_STUB marker with no FAIL marker.
"""
import argparse
import glob
import hashlib
import json
import os
import sys

LINK_ERROR = "undefined reference to Jac_NoteDemoSkipped"
TEST_PASS = "PASS P2_NOTE_DEMO_SKIP_STUB"


def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def latest(pattern):
    paths = sorted(glob.glob(pattern))
    if not paths:
        raise ValueError("no file matches %s" % pattern)
    return paths[-1]


def verify_bundle(out_dir):
    problems = []
    report = {"out_dir": out_dir, "checks": {}}

    try:
        record_path = latest(os.path.join(out_dir, "build-record-*.json"))
        record = json.load(open(record_path, encoding="utf-8"))
        report["build_record"] = os.path.basename(record_path)
    except (OSError, ValueError) as exc:
        return False, report, ["unreadable build record: %s" % exc]

    if record.get("config") != "PIKMIN_NATIVE_JAUDIO=OFF":
        problems.append("build record is not the default OFF config")
    steps = record.get("steps", {})
    for name in ("configure", "pikmin_pc"):
        if steps.get(name, {}).get("exit") != 0:
            problems.append("build step %s did not exit 0" % name)
    report["checks"]["build_steps"] = steps.get("pikmin_pc", {}).get("exit") == 0

    exes = record.get("executables") or {}
    if not exes:
        problems.append("no executables recorded")
    for path, pinned in exes.items():
        try:
            actual = sha256_file(path)
        except OSError:
            problems.append("executable missing: %s" % path)
            continue
        if actual != pinned:
            problems.append("executable hash mismatch: %s" % path)
    report["checks"]["executables"] = not any(
        "executable" in p for p in problems)

    stub = record.get("stub_object") or {}
    stub_path = stub.get("path")
    if not stub_path or not os.path.isfile(stub_path):
        problems.append("stub object missing")
    elif stub.get("sha256") != sha256_file(stub_path):
        problems.append("stub object hash mismatch")
    if stub.get("symbol_defined") is not True:
        problems.append("Jac_NoteDemoSkipped not proved defined in stub object")
    report["checks"]["stub_symbol"] = stub.get("symbol_defined") is True

    try:
        build_log = latest(os.path.join(out_dir, "leased-build-*.log"))
        log_text = open(build_log, encoding="utf-8",
                        errors="replace").read()
        report["build_log"] = os.path.basename(build_log)
    except OSError as exc:
        return False, report, problems + ["unreadable build log: %s" % exc]
    if LINK_ERROR in log_text:
        problems.append("link still has the undefined reference")
    report["checks"]["link_clean"] = LINK_ERROR not in log_text

    try:
        test_log = open(os.path.join(out_dir, "stub-test-build.log"),
                        encoding="utf-8", errors="replace").read()
    except OSError as exc:
        return False, report, problems + ["unreadable stub test log: %s" % exc]
    test_ok = ("COMPILE exit=0" in test_log and "LINK exit=0" in test_log
               and "RUN exit=0" in test_log and TEST_PASS in test_log
               and "FAIL P2_NOTE_DEMO_SKIP_STUB" not in test_log
               and "FAIL NOTE_DEMO_SKIP_STUB" not in test_log)
    if not test_ok:
        problems.append("focused stub test did not pass clean")
    report["checks"]["focused_test"] = test_ok

    return (not problems), report, problems


def main(argv=None):
    parser = argparse.ArgumentParser(description="Verify #704 compiled evidence")
    parser.add_argument("--dir", required=True)
    args = parser.parse_args(argv)
    try:
        ok, report, problems = verify_bundle(args.dir)
    except ValueError as exc:
        print("REFUSED %s" % exc)
        return 2
    print(json.dumps(report, indent=1, sort_keys=True))
    for problem in problems:
        print("REFUSED %s" % problem)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
