"""PC-BBFT follow-on anchor/ownership audit for recovery 2a21d6ed (issue #775).

Read-only diagnosis: verifies whether a pinned native base contains the
`pc_p2_challenge_stage_lookup` anchor and the #730 extension files required
by blocked `challenge-pc-bbft-followon` (#755), and records ownership for the
downstream `p2-challenge-ch-nari-03toy-p1` (#746) resume decision.

No engine edits, no builds, no launches, no ADMIT. Git is invoked
read-only (`git show`, `git rev-parse`); set `git_available=False` to run
purely off supplied text. Anything unverifiable is recorded ABSENT, never
invented.
"""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path

LANE = "pc-bbft-followon-anchor-diagnosis"
ISSUE = 775
DOWNSTREAM_LANE = "p2-challenge-ch-nari-03toy-p1"
DOWNSTREAM_ISSUE = 746

LOOKUP_SYMBOL = "pc_p2_challenge_stage_lookup"
LOOKUP_FILE = "pc_port/pc_bbft.cpp"
EXT_FILES = [
    "pc_port/pc_p2_challenge_stages_ext.h",
    "pc_port/pc_p2_challenge_stages_ext.cpp",
]


class AnchorError(ValueError):
    """An anchor input violates the audit contract."""


def _run_git(repo, *args):
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, timeout=60)
    return completed


def blob_present(repo, rev, path, git_available=True):
    """True when `path` exists at `rev`; fail-closed on bad rev/path."""
    if not rev or not path:
        raise AnchorError("rev and path are required")
    if not git_available:
        raise AnchorError("git unavailable; presence unverifiable")
    completed = _run_git(repo, "cat-file", "-e", "%s:%s" % (rev, path))
    return completed.returncode == 0


def symbol_in_blob(repo, rev, path, symbol, git_available=True):
    """True when `symbol` occurs in `path` at `rev`; fail-closed."""
    if not symbol:
        raise AnchorError("symbol is required")
    if not git_available:
        raise AnchorError("git unavailable; symbol unverifiable")
    completed = _run_git(repo, "show", "%s:%s" % (rev, path))
    if completed.returncode != 0:
        return False
    try:
        text = completed.stdout.decode("utf-8", errors="replace")
    except Exception as exc:
        raise AnchorError("undecodable blob: %s" % exc)
    return symbol in text


def anchor_status(lookup_present, ext_present):
    """Map presence facts to a resume disposition (pure logic)."""
    if not isinstance(lookup_present, bool) or not isinstance(ext_present, bool):
        raise AnchorError("presence facts must be booleans")
    if lookup_present and ext_present:
        return {"verdict": "anchor-complete",
                "resume": "rebase the blocked lane onto a line carrying both, "
                          "then controller-recover with a fresh worker; do "
                          "not create a duplicate lane"}
    if lookup_present and not ext_present:
        return {"verdict": "anchor-split",
                "resume": "coordinator/integrator rebase decision: land the "
                          "#730 ext files (unintegrated worktree branch) onto "
                          "the lookup-carrying line per the approved #186 "
                          "follow-on, then resume the blocked lane"}
    if not lookup_present and ext_present:
        return {"verdict": "anchor-split",
                "resume": "coordinator/integrator rebase decision: rebase "
                          "onto a lookup-carrying wave tip first"}
    return {"verdict": "anchor-absent",
            "resume": "no live resumable producer; coordinator must provision "
                      "both the lookup anchor and the ext files before any "
                      "resume"}


def ownership_record(lane_key, lane_state, worker_alive):
    """Record one lane's liveness for the resume decision (fail-closed)."""
    if lane_state not in ("blocked", "running", "ready", "done",
                          "handoff_ready", "waiting_resource", "integrating"):
        raise AnchorError("unknown lane state: %r" % (lane_state,))
    if not isinstance(worker_alive, bool):
        raise AnchorError("worker_alive must be a boolean")
    resumable = lane_state in ("blocked", "waiting_resource") and worker_alive
    return {"lane": lane_key, "state": lane_state,
            "worker_alive": worker_alive, "resumable_in_place": resumable,
            "note": "resume in place" if resumable else
                    "controller recovery with a fresh worker required"}


def packet(anchor, owners, downstream):
    """Build the hashed anchor/ownership packet."""
    if not isinstance(anchor, dict) or "verdict" not in anchor:
        raise AnchorError("anchor disposition required")
    if not isinstance(owners, list) or not owners:
        raise AnchorError("owner records required")
    result = {"schema": 1, "lane": LANE, "issue": ISSUE,
              "anchor": copy.deepcopy(anchor),
              "owners": copy.deepcopy(owners),
              "downstream": copy.deepcopy(downstream),
              "gates": "all six UNTESTED; flora gates unclaimed",
              "admit": False}
    result["packet_sha256"] = hashlib.sha256(
        json.dumps(result, sort_keys=True).encode("utf-8")).hexdigest()
    return result


def main(argv=None):
    """Audit one native rev and print the packet as JSON."""
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--rev", required=True)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    lookup = symbol_in_blob(args.repo, args.rev, LOOKUP_FILE, LOOKUP_SYMBOL)
    ext = {path: blob_present(args.repo, args.rev, path)
           for path in EXT_FILES}
    data = packet(
        anchor_status(lookup, all(ext.values())),
        [{"scope": "cli-audit", "lookup_present": lookup,
          "ext_present": ext}],
        {"lane": DOWNSTREAM_LANE, "issue": DOWNSTREAM_ISSUE})
    text = json.dumps(data, indent=2) + "\n"
    if args.output is not None:
        if args.output.suffix != ".json":
            raise AnchorError("Packet output must be JSON")
        args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
