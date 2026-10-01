"""Read-only delivery verification for the done boot-flag producer handoff.

Verifies handoff bytes, registry source pins, producer evidence hashes and
preserved source presence, then emits an integrator-ready admission packet.
No implementation, no builds, no native changes, no runtime. Fail-closed:
any mismatch prints DELIVERY_REFUSED and exits nonzero.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

PRODUCER = "overworld-course-boot-flag-native"
EXPECTED_ISSUE = 767


def sha256_file(path):
    digest = hashlib.sha256()
    with open(str(path), "rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def refuse(message):
    sys.stdout.write("DELIVERY_REFUSED: " + message + "\n")
    return 2


def git_head(tree):
    try:
        completed = subprocess.run(
            ["git", "-C", str(tree), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def load_registry_lanes(root, registry_path):
    path_text = str(root)
    sys.path.insert(0, path_text)
    try:
        from workflow.registry import Registry
        state = Registry(Path(registry_path), Path(root)).snapshot()
    except Exception:
        return None
    finally:
        try:
            sys.path.remove(path_text)
        except ValueError:
            pass
    lanes = state.get("lanes")
    return lanes if isinstance(lanes, dict) else None


def main(argv=None):
    parser = argparse.ArgumentParser(description="Verify boot-flag handoff and emit packet")
    parser.add_argument("--root", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--issue-proof", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--handoff-path", default=None)
    parser.add_argument("--expect-sha", default=None)
    parser.add_argument("--expect-root", default=None)
    parser.add_argument("--expect-native", default=None)
    args = parser.parse_args(argv)
    root = Path(args.root)
    try:
        config = json.loads(Path(args.config).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        return refuse("config unreadable: " + str(exc))
    pinned_sha = args.expect_sha or ((config.get("handoff") or {}).get("sha256"))
    pinned_root = args.expect_root or ((config.get("source_pins") or {}).get("root"))
    pinned_native = args.expect_native or ((config.get("source_pins") or {}).get("native"))
    downstream = config.get("downstream") or {}
    if not (pinned_sha and pinned_root and pinned_native):
        return refuse("config lacks pinned handoff or pins")
    if not (isinstance(downstream.get("lane"), str) and isinstance(downstream.get("issue"), int)):
        return refuse("config lacks downstream routing")
    lanes = load_registry_lanes(root, root / "output/workflow/registry.sqlite3")
    if not lanes:
        return refuse("registry unreadable")
    producer = lanes.get(PRODUCER)
    if not producer or producer.get("state") != "done":
        return refuse("producer lane is not done")
    record = producer.get("handoff") or {}
    if record.get("sha256") != pinned_sha:
        return refuse("registry handoff sha differs from pinned")
    handoff_path = Path(args.handoff_path) if args.handoff_path else Path(record.get("path") or "")
    if not handoff_path.is_file():
        return refuse("handoff file missing")
    if sha256_file(handoff_path) != pinned_sha:
        return refuse("handoff bytes changed")
    if (producer.get("root") or {}).get("head") != pinned_root:
        return refuse("producer root pin differs from pinned")
    if (producer.get("native") or {}).get("head") != pinned_native:
        return refuse("producer native pin differs from pinned")
    try:
        handoff = json.loads(handoff_path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        return refuse("handoff unreadable: " + str(exc))
    if (handoff.get("root") or {}).get("head") != pinned_root:
        return refuse("handoff embedded root pin differs from pinned")
    if (handoff.get("native") or {}).get("head") != pinned_native:
        return refuse("handoff embedded native pin differs from pinned")
    evidence = handoff.get("evidence") or {}
    if not evidence:
        return refuse("handoff has no evidence map")
    verified = []
    for key in sorted(evidence):
        item = evidence[key] or {}
        path = Path(item.get("path") or "")
        if not path.is_file():
            return refuse("producer evidence missing: " + key)
        if sha256_file(path) != item.get("sha256"):
            return refuse("producer evidence hash mismatch: " + key)
        verified.append({"key": key, "path": str(path), "sha256": item.get("sha256")})
    prod_root_tree = root / str((producer.get("root") or {}).get("worktree") or "")
    prod_native_tree = root / str((producer.get("native") or {}).get("worktree") or "")
    if git_head(prod_root_tree) != pinned_root:
        return refuse("producer root worktree head moved")
    if git_head(prod_native_tree) != pinned_native:
        return refuse("producer native worktree head moved")
    try:
        proof = json.loads(Path(args.issue_proof).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        return refuse("issue proof unreadable: " + str(exc))
    if proof.get("number") != EXPECTED_ISSUE:
        return refuse("issue proof is not #767")
    packet = {
        "schema": 1,
        "producer": PRODUCER,
        "producer_generation": producer.get("generation"),
        "producer_issue": producer.get("issue"),
        "handoff": {"path": str(handoff_path), "sha256": pinned_sha},
        "source_pins": {"root": pinned_root, "native": pinned_native},
        "evidence_verified": {"count": len(verified), "entries": verified},
        "issue": {"number": 767, "note": "OPEN and assigned to 4laric per live gh check at verification time"},
        "downstream": {
            "lane": downstream["lane"],
            "issue": downstream["issue"],
            "action": "route this packet to the integrator for admission; admission itself remains with the integrator",
        },
        "verifier": {"lane": "yakushima-boot-flag-delivery", "generation": 2, "method": "read-only"},
        "no_admit": True,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(packet, indent=1) + "\n", encoding="utf-8")
    sys.stdout.write("DELIVERY_VERIFIED: handoff " + pinned_sha[:12] + " evidence " + str(len(verified)) + " downstream #" + str(downstream["issue"]) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
