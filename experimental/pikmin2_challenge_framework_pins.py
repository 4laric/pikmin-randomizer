"""Pin-discovery + verification helpers for the P2 challenge framework
contract consumer pins (issue #136).

The framework lane committed schema + validator + tests on
`codex/prereq-p2-challenge-framework-contract` (commit `b9bb55f0`), but that
commit is not an ancestor of any canonical checkout. Investigation showed the
contract content itself WAS integrated onto the content line at `fc5cbdeb`
(byte-identical files), so the coherent consumer pair is published from
verified integration-line pins ? never invented.

All helpers are pure/read-only except where explicitly marked; no git
mutation, no builds, no ADMIT.
"""
from __future__ import annotations

import hashlib
import subprocess

SCHEMA = "p2-challenge-framework-pins-v1"

# Framework contract commit (root repo) and its branch.
CONTRACT_COMMIT = "b9bb55f0c52d1722a6c8cada958f2b1452a5ae99"
CONTRACT_BRANCH = "codex/prereq-p2-challenge-framework-contract"

# Contract files with byte hashes at the consumer root pin.
CONTRACT_FILES = {
    "docs/PIKMIN2_CHALLENGE_FRAMEWORK_CONTRACT.md":
        "55ef70425c665c8a6e1e523707f40d1f61d5d58bc3d7329b64ccf6b41179f545",
    "experimental/pikmin2_challenge_framework_contract.py":
        "7236c25309287e822c67cd619c8fe652281c21aa2ab03f98f7a9b2e6efc93517",
    "tests/test_pikmin2_challenge_framework_contract.py":
        "714b4d5c1462ae6776176472e89e4b396e2fd7ffc56d7514561fbcc808499e62",
}

# Coherent consumer pins (verified this turn, see the pin-table doc).
ROOT_CONSUMER_PIN = "b08e3bdc2dfb758c0d48e4dab074081a0ee34246"
ROOT_CONSUMER_BRANCH = "codex/content-lanes-531"
NATIVE_CONSUMER_PIN = "ab81cf5d0fa1856f46cc80b527b7e184afec97eb"
NATIVE_CONSUMER_BRANCH = "claude/p2-deepseek-wave-native"
ROOT_FORK_POINT = "b5309fb6c402c067afc7f1817ef06365bcb822d6"

# Downstream consumers of the pin pair.
DOWNSTREAM_P1_SCOPES = (
    "ch_NARI_01kusachi",
    "ch_MUKI_king",
    "ch_MAT_t_hunter_enemy",
    "ch_MUKI_enemyzero",
    "ch_MIYA_oopan",
    "ch_MUKI_bombing",
    "ch_MAT_t_hunter_otakara",
    "ch_NARI_09suikomi",
    "ch_MAT_route_rover",
    "ch_MAT_crawler",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(repo, *args):
    """Run a read-only git command; return (returncode, stdout)."""
    proc = subprocess.run(["git", "-C", str(repo)] + list(args),
                          capture_output=True, text=True, timeout=120)
    return proc.returncode, proc.stdout.strip()


def commit_exists(repo, commit):
    """True when the object exists and is a commit."""
    code, out = git(repo, "cat-file", "-t", commit)
    return code == 0 and out == "commit"


def branches_containing(repo, commit):
    """Branches containing the commit (empty when unknown)."""
    code, out = git(repo, "branch", "-a", "--contains", commit)
    if code != 0:
        return []
    return [line.strip().lstrip("*+ ") for line in out.splitlines() if line.strip()]


def is_ancestor(repo, ancestor, descendant):
    """True when ancestor is reachable from descendant."""
    code, _ = git(repo, "merge-base", "--is-ancestor", ancestor, descendant)
    return code == 0


def merge_base(repo, left, right):
    """Merge-base hash or empty string."""
    code, out = git(repo, "merge-base", left, right)
    return out if code == 0 else ""


def file_hash_at(repo, commit, path):
    """Byte hash of a file at a commit, or empty string when absent."""
    proc = subprocess.run(["git", "-C", str(repo), "show", commit + ":" + path],
                          capture_output=True, timeout=120)
    if proc.returncode != 0:
        return ""
    return sha256(proc.stdout)


def verify_contract_files(repo, commit, expected=CONTRACT_FILES):
    """Check every contract file hash at a pin; return a gap list (empty = clean)."""
    gaps = []
    for path, want in expected.items():
        got = file_hash_at(repo, commit, path)
        if not got:
            gaps.append("missing: " + path)
        elif got != want:
            gaps.append("hash-mismatch: " + path)
    return gaps


def check_coherent_pair(root_repo, root_pin, native_repo, native_pin):
    """Grade a candidate consumer pair without inventing anything.

    Returns (ok, findings): ok only when the contract commit exists, both
    pins exist, and the contract files verify byte-identical at the root pin.
    Native coherence for this root-only contract means the native pin exists
    on the maintained integration line (no native component required).
    """
    findings = []
    if not commit_exists(root_repo, CONTRACT_COMMIT):
        return False, ["contract-commit-absent"]
    if not commit_exists(root_repo, root_pin):
        findings.append("root-pin-absent")
    if not commit_exists(native_repo, native_pin):
        findings.append("native-pin-absent")
    gaps = verify_contract_files(root_repo, root_pin)
    findings.extend(gaps)
    return len(findings) == 0, findings


def no_coherent_pair_finding(root_repo, root_pin):
    """Exact no-pair statement data: where the contract is/isn't reachable."""
    return {
        "contract_commit": CONTRACT_COMMIT,
        "contract_branches": branches_containing(root_repo, CONTRACT_COMMIT),
        "consumer_root_pin": root_pin,
        "contract_ancestral_to_pin": is_ancestor(root_repo, CONTRACT_COMMIT, root_pin),
        "content_verified_at_pin": verify_contract_files(root_repo, root_pin) == [],
    }
