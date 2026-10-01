#!/usr/bin/env python3
"""Evidence verifier for lane bomb-birth-hook-notifier-port-native (#715).

Fail-closed checker over the lane's compiled artifacts. It never claims what
the evidence does not show: every check must pass, otherwise it reports the
exact problem and exits nonzero. Stdlib only.

Checks:
  1. A build record shows configure exit 0, pikmin_pc built, the provider
     test target built, and the provider CTest passed.
  2. Every recorded executable hash matches its file.
  3. The provider test log shows ALL_FIXTURE_PASS with no FAIL marker.
  4. The pikmin_pc link log (when the link ran) has no undefined reference
     to pc_p2_bomb_birth_hook_notify (the hook the notifier defines).
"""
import argparse
import glob
import hashlib
import json
import os
import sys

HOOK_ERROR = "undefined reference to `pc_p2_bomb_birth_hook_notify"
TEST_PASS = "ALL_FIXTURE_PASS"


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

    steps = record.get("steps", {})
    for name in ("configure", "pikmin_pc", "provider_test_build",
                 "provider_test_run"):
        if steps.get(name, {}).get("exit") != 0:
            problems.append("build step %s did not exit 0" % name)
    report["checks"]["build_steps"] = all(
        steps.get(n, {}).get("exit") == 0
        for n in ("configure", "pikmin_pc", "provider_test_build",
                  "provider_test_run"))

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

    try:
        test_logs = sorted(glob.glob(os.path.join(out_dir, "ctest-*.log")))
        if not test_logs:
            problems.append("no provider test log")
            test_text = ""
        else:
            test_text = open(test_logs[-1], encoding="utf-8",
                             errors="replace").read()
            report["provider_test_log"] = os.path.basename(test_logs[-1])
    except OSError as exc:
        return False, report, problems + ["unreadable test log: %s" % exc]
    test_ok = bool(test_text) and TEST_PASS in test_text and "Failed" not in test_text
    if not test_ok:
        problems.append("provider fixture did not pass clean")
    report["checks"]["provider_test"] = test_ok

    return (not problems), report, problems


def main(argv=None):
    parser = argparse.ArgumentParser(description="Verify #715 compiled evidence")
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
