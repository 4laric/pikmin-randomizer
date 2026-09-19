#!/usr/bin/env python3
"""Tutorial P1 native runtime runner (lane p2-overworld-tutorial-p1-native-runtime).

Stages a private run layout from the P1 tutorial manifest + session seed,
validates it, and verifies headed run logs. The runner never claims what the
log does not show: a PASS is reported only when every required marker is
present AND no failure/interruption marker appears. Stdlib only.

Consumes the integrated p2-surface-session-1 contract read-only (schema and
course are checked against it when importable) and hash-pins the contract and
overworld source locator alongside the run metadata.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

SCHEMA = "p2-tutorial-p1-run-1"
COURSE = "tutorial"
CONTRACT_SCHEMA = "p2-surface-session-1"

CONTRACT_PATH = "experimental/pikmin2_surface_session_contract.py"
LOCATOR_PATH = "experimental/pikmin2_overworld_source_locator.py"

REQUIRED_ENGINE_MARKERS = [
    "P2_TUTORIAL_P1_WINDOW",
    "P2_TUTORIAL_P1_ENGINE_FACT",
]

# Boundary PASS markers. Absence (or a FAIL/BLOCKED marker) means the boundary
# was not observed; the verifier reports it unobserved, never passing.
BOUNDARY_PASS_MARKERS = {
    "boot_tutorial_surface": "P2_TUTORIAL_P1_BOOT_PASS",
    "day_transition": "P2_TUTORIAL_P1_DAY_PASS",
    "save_reload": "P2_TUTORIAL_P1_SAVE_PASS",
    "receipt_replay": "P2_TUTORIAL_P1_RECEIPT_PASS",
    "exit_reentry": "P2_TUTORIAL_P1_REENTRY_PASS",
}

FAILURE_MARKERS = (
    "FAIL TUTORIAL_P1_RUNTIME",
    "P2_FIXTURE_CAPTAIN_DOWN",
    "P2_TUTORIAL_P1_UNSUPPORTED",
)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def contract_schema(repo_root=None):
    """Return the integrated contract schema, or the literal fallback."""
    root = repo_root or os.path.join(os.path.dirname(__file__), "..")
    root = os.path.abspath(root)
    if root not in sys.path:
        sys.path.insert(0, root)
    try:
        from experimental.pikmin2_surface_session_contract import SCHEMA as value
    except Exception:
        return CONTRACT_SCHEMA
    return value


def pin_hashes(repo_root):
    """Hash-pin the integrated contract and source locator (read-only)."""
    pins = {}
    for key, rel in (("contract", CONTRACT_PATH), ("source_locator", LOCATOR_PATH)):
        path = os.path.join(repo_root, rel)
        pins[key] = {"path": rel, "sha256": sha256_file(path)} if os.path.isfile(path) else None
    return pins


def stage_run_layout(manifest_path, seed_path, run_dir, pins, repo_root=None):
    """Copy the P1 manifest + session seed into a private run layout."""
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    with open(seed_path, encoding="utf-8") as f:
        seed = json.load(f)
    if seed.get("schema") != contract_schema(repo_root):
        raise ValueError("session seed schema is not %s" % CONTRACT_SCHEMA)
    if seed.get("course") != COURSE:
        raise ValueError("session seed course is not %s" % COURSE)
    layout = os.path.join(run_dir, "tutorial-p1")
    os.makedirs(layout, exist_ok=True)
    manifest_text = json.dumps(manifest, indent=1, sort_keys=True)
    seed_text = json.dumps(seed, indent=1, sort_keys=True)
    with open(os.path.join(layout, "manifest.json"), "w", encoding="utf-8", newline="") as f:
        f.write(manifest_text)
    with open(os.path.join(layout, "session-seed.json"), "w", encoding="utf-8", newline="") as f:
        f.write(seed_text)
    record = {
        "schema": SCHEMA,
        "course": COURSE,
        "manifest_sha256": hashlib.sha256(manifest_text.encode()).hexdigest(),
        "seed_sha256": hashlib.sha256(seed_text.encode()).hexdigest(),
        "source_pins": pins,
        "integrated_pins": pin_hashes(repo_root or os.path.join(os.path.dirname(__file__), "..")),
        "staged_files": ["tutorial-p1/manifest.json", "tutorial-p1/session-seed.json"],
    }
    with open(os.path.join(layout, "run-metadata.json"), "w", encoding="utf-8", newline="") as f:
        json.dump(record, f, indent=2)
        f.write("\n")
    return record


def validate_run_layout(run_dir):
    """Refuse a run layout whose files do not match its metadata pins."""
    problems = []
    layout = os.path.join(run_dir, "tutorial-p1")
    meta_path = os.path.join(layout, "run-metadata.json")
    try:
        record = json.load(open(meta_path, encoding="utf-8"))
    except (OSError, ValueError):
        return ["missing-or-bad-run-metadata"]
    if record.get("schema") != SCHEMA:
        problems.append("bad-run-schema")
    for name, key in (("manifest.json", "manifest_sha256"),
                      ("session-seed.json", "seed_sha256")):
        path = os.path.join(layout, name)
        try:
            actual = sha256_file(path)
        except OSError:
            problems.append("missing-" + name)
            continue
        if actual != record.get(key):
            problems.append("hash-mismatch-" + name)
    try:
        seed = json.load(open(os.path.join(layout, "session-seed.json"), encoding="utf-8"))
    except (OSError, ValueError):
        problems.append("bad-session-seed")
    else:
        if seed.get("schema") != CONTRACT_SCHEMA or seed.get("course") != COURSE:
            problems.append("bad-session-seed-content")
    return problems


def verify_run_log(log_text):
    """Map the headed run log to boundary verdicts. Never invents a PASS."""
    verdicts = {}
    for boundary, marker in BOUNDARY_PASS_MARKERS.items():
        if marker in log_text:
            verdicts[boundary] = "observed"
        elif "P2_TUTORIAL_P1_UNSUPPORTED boundary=%s" % boundary in log_text:
            verdicts[boundary] = "unsupported"
        else:
            verdicts[boundary] = "unobserved"
    failures = [m for m in FAILURE_MARKERS if m in log_text]
    engine_boot = all(m in log_text for m in REQUIRED_ENGINE_MARKERS)
    overall_pass = (
        engine_boot
        and all(v == "observed" for v in verdicts.values())
        and not failures
        and "PASS TUTORIAL_P1_RUNTIME" in log_text
    )
    return {
        "engine_boot": engine_boot,
        "boundaries": verdicts,
        "failure_markers": failures,
        "overall_pass": overall_pass,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Tutorial P1 native runtime runner")
    sub = parser.add_subparsers(dest="command", required=True)
    stage = sub.add_parser("stage")
    stage.add_argument("--manifest", required=True)
    stage.add_argument("--seed", required=True)
    stage.add_argument("--out", required=True)
    stage.add_argument("--pins", default="{}")
    stage.add_argument("--repo-root", default=None)
    validate = sub.add_parser("validate")
    validate.add_argument("--dir", required=True)
    verify = sub.add_parser("verify-log")
    verify.add_argument("--log", required=True)
    args = parser.parse_args(argv)
    if args.command == "stage":
        try:
            pins = json.loads(args.pins)
        except ValueError as exc:
            print("bad --pins JSON: %s" % exc)
            return 2
        try:
            record = stage_run_layout(args.manifest, args.seed, args.out, pins,
                                      repo_root=args.repo_root)
        except (ValueError, OSError) as exc:
            print("refused: %s" % exc)
            return 2
        print("staged manifest=%s seed=%s" % (
            record["manifest_sha256"][:16], record["seed_sha256"][:16]))
        return 0
    if args.command == "validate":
        problems = validate_run_layout(args.dir)
        if problems:
            for problem in problems:
                print("REFUSED reason=%s" % problem)
            return 1
        print("RUN_LAYOUT_PASS dir=%s" % args.dir)
        return 0
    with open(args.log, encoding="utf-8", errors="replace") as f:
        result = verify_run_log(f.read())
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0 if result["overall_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
