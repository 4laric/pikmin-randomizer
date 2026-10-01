"""Read-only reconciliation ledger for P2 integration candidates (lane 01, #437).

For each candidate commit, report whether it is an ancestor of the maintained
base, which files it changes, and how many of those files already match the base
tree. This is evidence for the reviewer; it does not merge or build anything.

    py -3.12 scripts/audit_p2_candidates.py --base origin/codex/p2-main-review --output docs/PIKMIN2_RECONCILE_LEDGER.json
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# name, candidate revision, tracked issue, expected native/root modules to check.
CANDIDATES = (
    ("hard-lanes", "87204df", "#244/#245/#246", ("engine/pc_port/pc_p2_hardlanes.cpp", "engine/pc_port/pc_p2_bombsarai.cpp")),
    ("species-ground-six", "86aa159", "#407 #165", ("engine/pc_port/pc_p2_sokkuri.cpp", "experimental/pikmin2_sokkuri_behavior.py")),
    ("cannon", "656c556", "#406 #424 #425", ("engine/pc_port/pc_p2_cannon.cpp", "experimental/pikmin2_cannon_projectile.py")),
    ("lifecycle-forget", "6b71b14", "#397", ("engine/pc_port/pc_p2_batch2.cpp",)),
    ("lifecycle-reward", "9280a2f", "#397", ("engine/pc_port/pc_p2_economy.cpp",)),
    ("lifecycle-native", "fb6389ce", "#397", ("engine/pc_port/pc_p2_batch2.cpp",)),
    ("hikari-48", "33c5cac", "#429", ("experimental/pikmin2_convert.py",)),
    ("anim-clock", "cb253f5", "#431", ("engine/pc_port/pc_p2_animation.h", "experimental/pikmin2_animation_clock.py")),
)


def git(*args: str) -> tuple[int, str]:
    result = subprocess.run(["git", "-C", str(ROOT), *args],
                            capture_output=True, text=True)
    return result.returncode, result.stdout.strip()


def commit_exists(rev: str) -> bool:
    return git("cat-file", "-t", rev)[1] == "commit"


def is_ancestor(rev: str, base: str) -> bool:
    return git("merge-base", "--is-ancestor", rev, base)[0] == 0


def changed_files(rev: str) -> list[str]:
    code, out = git("diff-tree", "--no-commit-id", "--name-only", "-r", rev)
    if code != 0 or not out:
        code, out = git("diff", "--name-only", f"{rev}^1", rev)
    if code != 0:
        return []
    return [line for line in out.splitlines() if line]


def blob(rev: str, path: str) -> str | None:
    code, out = git("rev-parse", "--verify", "-q", f"{rev}:{path}")
    return out if code == 0 and out else None


def reconcile(candidate: tuple, base: str) -> dict:
    name, rev, issue, expected = candidate
    record = {"name": name, "revision": rev, "issues": issue, "expected_modules": {}}
    if not commit_exists(rev):
        record.update(exists=False, note="commit not in this repository (likely native-only)")
        record["expected_modules"] = {path: "unknown" for path in expected}
        return record
    record["exists"] = True
    _, subject = git("log", "-1", "--format=%h %ad %s", "--date=short", rev)
    record["subject"] = subject
    record["ancestor_of_base"] = is_ancestor(rev, base)
    files = changed_files(rev)
    present = absent = differ = 0
    absent_examples: list[str] = []
    for path in files:
        base_blob, rev_blob = blob(base, path), blob(rev, path)
        if base_blob is None:
            absent += 1
            absent_examples.append(path)
        elif base_blob == rev_blob:
            present += 1
        else:
            differ += 1
    record.update(changed_file_count=len(files), files_present_identical=present,
                  files_absent_from_base=absent, files_differ=differ,
                  absent_examples=sorted(absent_examples)[:15])
    for path in expected:
        base_blob, rev_blob = blob(base, path), blob(rev, path)
        if rev_blob is None:
            record["expected_modules"][path] = "not-in-candidate"
        elif base_blob is None:
            record["expected_modules"][path] = "absent-from-base"
        elif base_blob == rev_blob:
            record["expected_modules"][path] = "identical-in-base"
        else:
            record["expected_modules"][path] = "differs-in-base"
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/codex/p2-main-review")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    base = args.base
    _, base_subject = git("log", "-1", "--format=%h %s", base)
    records = [reconcile(candidate, base) for candidate in CANDIDATES]
    missing = [r for r in records if r.get("exists") and not r.get("ancestor_of_base")]
    absent_modules = [
        f"{r['name']}:{path}"
        for r in records
        for path, state in r.get("expected_modules", {}).items()
        if state == "absent-from-base"
    ]
    ledger = {
        "schema": "p2-candidate-reconcile-1",
        "base": base,
        "base_subject": base_subject,
        "candidate_count": len(records),
        "not_ancestor_of_base": [r["name"] for r in missing],
        "expected_modules_absent_from_base": absent_modules,
        "candidates": records,
        "note": "Read-only audit. Confirms candidate presence/ancestry; does not merge, build or export.",
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")

    print(f"base {base_subject}")
    for record in records:
        if not record.get("exists"):
            print(f"  {record['name']:<20} {record['revision']:<10} MISSING")
            continue
        print(f"  {record['name']:<20} {record['revision']:<10} ancestor={record['ancestor_of_base']!s:<5} "
              f"files={record['changed_file_count']} absent={record['files_absent_from_base']}")
    print(f"\nnot ancestor of base: {[r['name'] for r in missing]}")
    print(f"expected modules absent from base: {absent_modules}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
