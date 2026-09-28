"""Landing decision packet for the #730 ext table + #755 follow-on (recovery 8c2b7615).

Root-only tooling: records exact producer pins, computes merge-base/conflict
pre-analysis against a destination tip, and emits a decision packet the
coordinator/integrator can execute without rediscovery. It performs NO merge,
touches NO shared/native files, runs NO builds and claims NO runtime.
Downstream: #537 P1 boot (blocked on the engine table row) + recovery
request 8c2b7615 (+ #575/#576 placement providers, unaffected).
"""
import hashlib
import json
import subprocess
from pathlib import Path

SCHEMA = "p2-challenge-ext-landing-decision-v1"

EXT_COMMIT = "5e871f88b0493d79d0ed800d923fec84367fe056"
EXT_BRANCH = "codex/autofill-challenge-stage-table-extension-native"
EXT_FILES = {
    "pc_port/pc_p2_challenge_stages_ext.h": "6d47f50987be",
    "pc_port/pc_p2_challenge_stages_ext.cpp": "ca117202380e",
    "tools/p2_challenge_stage_table_ext_fixture.cpp": "9b8aaebbd4d6",
}
FOLLOWON_FILES = ("native/pc_port/pc_bbft.cpp", "native/CMakeLists.txt")
FOLLOWON_ISSUE = 755
EXT_ISSUE = 730
DOWNSTREAM = ["#537", "recovery 8c2b7615", "#575/#576"]


class DecisionError(ValueError):
    """Refusal: missing input, pin drift, or unreadable baseline."""


def _git(native_repo, *args):
    proc = subprocess.run(["git", "-C", str(native_repo)] + list(args),
                          capture_output=True, timeout=120)
    if proc.returncode != 0:
        raise DecisionError("git failed: " + " ".join(args) + " :: " + proc.stderr.decode()[:200])
    return proc.stdout


def blob_prefix(native_repo, rev, path, length=12):
    """Short blob hash of one committed file; fail closed on missing objects."""
    digest = _git(native_repo, "rev-parse", "%s:%s" % (rev, path)).decode().strip()
    if len(digest) < length:
        raise DecisionError("bad blob hash for " + path)
    return digest[:length]


def record_producer_pins(native_repo):
    """Verify the ext commit and return its exact file/blob record."""
    native_repo = str(native_repo)
    head = _git(native_repo, "rev-parse", EXT_COMMIT).decode().strip()
    if head != EXT_COMMIT:
        raise DecisionError("ext commit identity drift")
    files = {}
    for path, prefix in EXT_FILES.items():
        blob = blob_prefix(native_repo, EXT_COMMIT, path)
        if not blob.startswith(prefix):
            raise DecisionError("ext file drift: " + path)
        files[path] = blob
    return {"commit": EXT_COMMIT, "branch": EXT_BRANCH, "files": files}


def conflict_matrix(native_repo, dest_rev, live_owned_files=()):
    """For each producer file: presence at destination tip + live-owner overlap."""
    native_repo = str(native_repo)
    rows = []
    live = set(live_owned_files)
    for path in EXT_FILES:
        proc = subprocess.run(["git", "-C", native_repo, "cat-file", "-e",
                               "%s:%s" % (dest_rev, path)],
                              capture_output=True, timeout=60)
        present = proc.returncode == 0
        overlap = [f for f in live if f.endswith(path.split("/")[-1])]
        rows.append({"path": path, "present_at_destination": present,
                     "live_owner_overlap": overlap,
                     "landing": "skip-present" if present else ("blocked-overlap" if overlap else "clean-add")})
    rows.append({"path": "native/pc_port/pc_bbft.cpp + native/CMakeLists.txt",
                 "present_at_destination": None,
                 "live_owner_overlap": ["challenge-pc-bbft-followon (#755, blocked)"],
                 "landing": "owner-blocked: #755 holds these files; coordinator rebase + #186 review pending"})
    return rows


def ancestry(native_repo, dest_rev):
    """Is the ext commit already an ancestor of the destination tip?"""
    proc = subprocess.run(["git", "-C", str(native_repo), "merge-base", "--is-ancestor",
                           EXT_COMMIT, dest_rev],
                          capture_output=True, timeout=60)
    return proc.returncode == 0


def decision_packet(native_repo, dest_rev, live_owned_files=()):
    """Assemble the integrator decision packet (no merge performed)."""
    pins = record_producer_pins(native_repo)
    matrix = conflict_matrix(native_repo, dest_rev, live_owned_files)
    landed = ancestry(native_repo, dest_rev)
    steps = []
    if not landed:
        steps.append("cherry-pick -x %s onto the destination line (3 pure-add files, no deletions)" % EXT_COMMIT)
    steps.append("resolve #755 follow-on (pc_bbft.cpp fallthrough + CMakeLists membership) via its owner: needs coordinator rebase + #186 review")
    steps.append("re-run the #711 record fixture: 02tile must resolve TABLE (not ENGINE_ROW_PENDING) and boot READY")
    return {"schema": SCHEMA, "producer": pins, "destination_rev": dest_rev,
            "already_landed": landed, "conflict_matrix": matrix,
            "ordered_steps": steps, "downstream": list(DOWNSTREAM),
            "limitations": ["Packet is scope validation, not a merge and not runtime acceptance.",
                            "No shared/native files were touched to produce it."]}


def packet_json(native_repo, dest_rev, live_owned_files=()):
    return json.dumps(decision_packet(native_repo, dest_rev, live_owned_files),
                      indent=2, sort_keys=True) + "\n"
