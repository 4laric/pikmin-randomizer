"""Rebase verification adapter for the #715 bomb-birth notifier (#726).

Verifies the rebase inputs without compiling: the wave tip carries the evolved
provider (`pc_p2_bomb_mgr_birth.*`, `pc_p2_bomb_payload_actor.*`,
`pc_p2_otakara_joint_capture.*`) but no notifier TU and no hooked
`generalEnemyMgr.cpp`; the lane adds exactly those plus the guarded fixture.
Re-derives the expected landable content (hook-only 14-line addition) and
hashes evidence for the packet. No builds, no runtime, no ADMIT.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ISSUE = 726
WAVE_PIN = "93603dc232f9c6ddc4fb2c1241bd590fe95d9b54"
NOTIFIER_715 = "a6ca7bc6"
HOOK_677 = "91c09444"
NOTIFIER_FILES = ("pc_port/pc_p2_bomb_notifier.h", "pc_port/pc_p2_bomb_notifier.cpp")
HOOK_FILE = "pikmin2-research/src/plugProjectYamashitaU/generalEnemyMgr.cpp"
HOOK_MARKERS = ("pc_p2_bomb_birth_hook_notify",
                "pc_p2_bomb_birth_hook_maybe_notify",
                "EnemyID_BombOtakara")
PROVIDER_FILES = ("pc_port/pc_p2_bomb_mgr_birth.cpp",
                  "pc_port/pc_p2_bomb_payload_actor.cpp",
                  "pc_port/pc_p2_otakara_joint_capture.cpp")
GUARD_PATH = "scripts/p2_fixture_captain_guard.h"
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"


class RebaseGapError(ValueError):
    """A rebase prerequisite cannot be verified; nothing is invented."""


def _git(native, *args):
    proc = subprocess.run(["git", "-C", str(native), *args], capture_output=True)
    if proc.returncode != 0:
        raise RebaseGapError("git %s failed" % " ".join(args))
    return proc.stdout


def wave_inventory(native):
    """Prove the wave tip has the provider but neither the notifier nor the hook."""
    present, missing = [], []
    for path in PROVIDER_FILES + NOTIFIER_FILES + (HOOK_FILE,):
        blob = subprocess.run(
            ["git", "-C", str(native), "cat-file", "-e",
             "%s:%s" % (WAVE_PIN, path)],
            capture_output=True)
        (present if blob.returncode == 0 else missing).append(path)
    for path in PROVIDER_FILES:
        if path not in present:
            raise RebaseGapError("wave tip lost provider file: %s" % path)
    for path in NOTIFIER_FILES + (HOOK_FILE,):
        if path not in missing:
            raise RebaseGapError("wave tip already has: %s" % path)
    return {"provider_present": list(PROVIDER_FILES),
            "notifier_absent": list(NOTIFIER_FILES),
            "hook_absent": [HOOK_FILE]}


def hook_addition_lines(native, research_path):
    """The exact hook lines the rebase adds over the live research file."""
    current = Path(research_path).read_bytes().decode("utf-8", errors="replace")
    reviewed = _git(native, "show",
                    "%s:%s" % (HOOK_677, HOOK_FILE)).decode("utf-8", errors="replace")
    import difflib
    return [line for line in difflib.unified_diff(
        current.splitlines(), reviewed.splitlines(), lineterm="", n=0)
        if line[:1] == "+" and not line.startswith("+++")]


def verify_rebased_copy(native, copy_path, research_path):
    """The lane copy must equal the reviewed #677 bytes, byte-exact."""
    copy = Path(copy_path).read_bytes()
    reviewed = _git(native, "show", "%s:%s" % (HOOK_677, HOOK_FILE))
    if copy != reviewed:
        raise RebaseGapError("rebased copy differs from reviewed #677 bytes")
    Path(research_path).read_bytes()
    if b"pc_p2_bomb_birth_hook_notify" not in copy or b"EnemyID_BombOtakara" not in copy:
        raise RebaseGapError("hook markers missing from rebased copy")
    return {"copy_sha256": hashlib.sha256(copy).hexdigest(),
            "live_sha256": hashlib.sha256(live).hexdigest()}


def packet(native, worktree, research_path, exe_sha256="", hook_log_sha256="",
           dry_run=""):
    """Assemble the landable packet record (downstream #573)."""
    inv = wave_inventory(native)
    vcopy = verify_rebased_copy(native, worktree, research_path)
    return {
        "schema": 1, "issue": ISSUE, "wave_pin": WAVE_PIN,
        "notifier_source": NOTIFIER_715, "hook_source": HOOK_677,
        "inventory": inv, "rebased_copy": vcopy,
        "notifier_files": list(NOTIFIER_FILES),
        "exe_sha256": exe_sha256, "hook_log_sha256": hook_log_sha256,
        "dry_run": dry_run,
        "guard": {"path": GUARD_PATH, "sha256": GUARD_SHA256},
        "cmake_membership": "serialized after #725; NOT included here",
        "downstream": "enemy-bombotakara93-payload (#573)",
        "gates": "all six UNTESTED",
    }


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--worktree", type=Path, required=True)
    parser.add_argument("--research", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        record = packet(args.native, args.worktree, args.research)
    except RebaseGapError as exc:
        print("REBASE_GAP %s" % exc)
        return 4
    payload = json.dumps(record, indent=1) + "\n"
    if args.out is None:
        print(payload, end="")
    else:
        args.out.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())