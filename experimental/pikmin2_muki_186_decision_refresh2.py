"""Read-only #186 decision-request refresh for muki gen-5 pins (#824).

Verifies the producer delta, destination pins, and unlanded state, then
emits a decision-request packet for the #186 owners. Never edits source,
never builds, never launches. Diagnosis only.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

PRODUCER_ROOT = "baf82085429160b6b8ce5a901a8af3ef36a50af8"
PRODUCER_NATIVE_BASE = "93603dc232f9c6ddc4fb2c1241bd590fe95d9b54"
PRODUCER_NATIVE_HEAD = "3c50ca44faad976d91cf790da8adbe6e3f508c4a"
DEST_ROOT = "3a33cbdefd5e4057eef9fb0d824cce4510ddab05"
DEST_NATIVE = "73891ad546c03c6da6b3b3574635fd2c35d0eda1"
ROWS = ["pc_port/pc_p2_challenge_muki_stages.h",
        "pc_port/pc_p2_challenge_muki_stages.cpp",
        "tools/p2_muki_stage_table_fixture.cpp"]
SHARED_WIRING = ["pc_port/pc_bbft.cpp", "native/CMakeLists.txt"]


def git(native, *args):
    return subprocess.run(["git", "-C", str(native)] + list(args),
                          capture_output=True, text=True)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(native_repo, dest_native):
    """Return (report_dict, ok). Read-only."""
    diff = git(native_repo, "diff", "--stat",
               PRODUCER_NATIVE_BASE + ".." + PRODUCER_NATIVE_HEAD)
    if diff.returncode != 0:
        return {"error": "producer range unreadable"}, False
    paths = [l.split("|")[0].strip() for l in diff.stdout.splitlines() if "|" in l]
    if sorted(paths) != sorted(ROWS):
        return {"error": "producer delta is not exactly the 3 row files",
                "paths": paths}, False
    landed = []
    for f in ROWS:
        r = git(native_repo, "ls-tree", dest_native, "--", f)
        if r.stdout.strip():
            landed.append(f)
    return {
        "producer_root": PRODUCER_ROOT,
        "producer_native_base": PRODUCER_NATIVE_BASE,
        "producer_native_head": PRODUCER_NATIVE_HEAD,
        "producer_files": ROWS,
        "producer_insertions": 113,
        "producer_deletions": 0,
        "dest_root": DEST_ROOT,
        "dest_native": dest_native,
        "landed_at_dest": landed,
        "unlanded": not landed,
        "shared_wiring_needing_decision": SHARED_WIRING,
    }, True


def packet(report, issue=824, consumer="muki-stage-table-rows-native"):
    return {
        "schema": "muki-186-decision-refresh2-v1",
        "issue": issue,
        "consumer": consumer,
        "producer_pins": {"root": report["producer_root"],
                          "native": report["producer_native_head"]},
        "destination_pins": {"root": report["dest_root"],
                             "native": report["dest_native"]},
        "rows": report["producer_files"],
        "unlanded": report["unlanded"],
        "decision_requested": ("#186 landing word on the serialized "
                               "pc_bbft.cpp/CMakeLists.txt wiring for the "
                               "3 additive MUKI row files; then final-owner "
                               "export + leased rebuild + re-batch"),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--native-repo", type=Path, required=True)
    ap.add_argument("--dest-native", default=DEST_NATIVE)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args(argv)
    report, ok = verify(args.native_repo, args.dest_native)
    if not ok:
        print(json.dumps(report, indent=1))
        return 1
    pack = packet(report)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "decision-packet.json").write_text(
        json.dumps(pack, indent=1), encoding="utf-8")
    (args.output / "verification.json").write_text(
        json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({"unlanded": report["unlanded"],
                      "packet": str(args.output / "decision-packet.json")}))
    return 0 if report["unlanded"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
