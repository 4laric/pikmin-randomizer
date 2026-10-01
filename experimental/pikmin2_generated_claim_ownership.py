"""Ownership/pin validation helpers for the generated-actor claim arm +
BIRTH generator field discovery slice (#644).

Read-only, stdlib-only. Pure functions take injected data (registry status
dicts, document text, git-query callbacks) so every fact is checkable and
every unresolved item is an explicit unknown -- never guessed.
"""

import json
import subprocess


class OwnershipError(ValueError):
    """Malformed or missing input; never a guessed fact."""


# Exact pins established by read-only discovery (see decision record).
CLAIM_ARM_OWNER_LANE = "enemy-waterwraith99-generated"
CLAIM_ARM_OWNER_ISSUE = 572
CLAIM_ARM_FILES = (
    "native/pc_port/pc_p2_waterwraith_actor.cpp",
    "native/pc_port/pc_p2_waterwraith_actor.h",
    "native/pc_port/pc_p2_waterwraith_encounter.cpp",
    "native/pc_port/pc_p2_waterwraith_encounter.h",
)
SELF_ASSIGNMENT_MARKER = "Family generated-claim arm (this lane owns"
ACTOR_BIRTH_SCOPE_EXCLUSION = "excludes family-specific consumer FSMs"
CATALOG_PIN = "7a21ce6a"
PACKAGING_PIN = "04d58d33"
NATIVE_BIND_PIN = "e2aa476e"
DOWNSTREAM_CONSUMERS = ("#572", "f42ecca0", "#608", "#575/#576")


def load_status(path):
    """Load a registry `status` JSON snapshot; reject malformed input."""
    try:
        with open(path, encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as error:
        raise OwnershipError("status snapshot unreadable: %s" % error)
    if not isinstance(data, dict) or not isinstance(data.get("lanes"), dict):
        raise OwnershipError("status snapshot lacks lanes mapping")
    return data


def lane_record(status, key):
    """Fetch one lane record; unknown keys are explicit errors, not guesses."""
    try:
        lanes = status["lanes"]
    except (KeyError, TypeError):
        raise OwnershipError("status has no lanes mapping")
    if not isinstance(lanes, dict) or key not in lanes:
        raise OwnershipError("unknown lane: %r" % (key,))
    record = lanes[key]
    if not isinstance(record, dict):
        raise OwnershipError("malformed lane record: %r" % (key,))
    return record


def git_lines(git_dir, *args):
    """Run a read-only git query; failures are explicit unknowns upstream."""
    proc = subprocess.run(
        ["git", "--git-dir=" + git_dir] + list(args),
        capture_output=True, text=True, timeout=60)
    return proc.returncode, proc.stdout.strip()


def check_claim_arm_owner(status, acceptance_text):
    """Verify #572 self-assigns the claim arm; report file write-state."""
    record = lane_record(status, CLAIM_ARM_OWNER_LANE)
    if record.get("issue") != CLAIM_ARM_OWNER_ISSUE:
        raise OwnershipError("claim-arm lane issue mismatch")
    if SELF_ASSIGNMENT_MARKER not in (acceptance_text or ""):
        return {"owner": CLAIM_ARM_OWNER_LANE, "issue": CLAIM_ARM_OWNER_ISSUE,
                "self_assignment": "UNKNOWN",
                "note": "acceptance doc lacks the self-assignment marker"}
    lineno = next(
        (i + 1 for i, line in enumerate(acceptance_text.splitlines())
         if SELF_ASSIGNMENT_MARKER in line), None)
    return {"owner": CLAIM_ARM_OWNER_LANE, "issue": CLAIM_ARM_OWNER_ISSUE,
            "self_assignment": "docs/PIKMIN2_WATERWRAITH_GENERATED_ACCEPTANCE.md:%d"
                               % lineno,
            "surface": list(CLAIM_ARM_FILES), "state": "unwritten-design-slice"}


def check_birth_field_owner(status):
    """Verify the BIRTH field belongs to the same slice; #608 is excluded."""
    record = lane_record(status, CLAIM_ARM_OWNER_LANE)
    facts = {"owner": CLAIM_ARM_OWNER_LANE, "issue": record.get("issue"),
             "surface": list(CLAIM_ARM_FILES),
             "marker": "P2_WATERWRAITH_BIRTH generator field"}
    lanes = status.get("lanes") if isinstance(status, dict) else None
    key = "planning-shard-provider-actor-birth-projectiles-cycle-13"
    birth = lanes.get(key) if isinstance(lanes, dict) else None
    if birth is None:
        facts["actor_birth_shard"] = "UNKNOWN"
        return facts
    scope = birth.get("scope", "")
    facts["actor_birth_shard"] = "excluded" \
        if ACTOR_BIRTH_SCOPE_EXCLUSION in scope else "UNKNOWN"
    facts["actor_birth_scope"] = scope[:160]
    return facts


def check_catalog_pin(git_dir, native_git_dir):
    """Verify exact carrier pins and their absence from canonical HEADs."""
    pins = {}
    for label, rev in (("catalog", CATALOG_PIN),
                       ("packaging", PACKAGING_PIN)):
        code, _ = git_lines(git_dir, "cat-file", "-t", rev)
        anc, _ = git_lines(git_dir, "merge-base", "--is-ancestor", rev, "HEAD")
        pins[label] = {"pin": rev, "exists": code == 0,
                       "in_canonical_head": anc == 0}
    code, _ = git_lines(native_git_dir, "cat-file", "-t", NATIVE_BIND_PIN)
    anc, _ = git_lines(native_git_dir, "merge-base", "--is-ancestor",
                       NATIVE_BIND_PIN, "HEAD")
    pins["native_bind"] = {"pin": NATIVE_BIND_PIN, "exists": code == 0,
                           "in_canonical_head": anc == 0}
    for label, rev, path in (("wave_root_note", "25af23fc",
                              "randomizer/p2_placement_catalog.py"),
                             ("native_wave_note", "df4135e2",
                              "pc_port/pc_p2_generated_placement.cpp")):
        gd = git_dir if label == "wave_root_note" else native_git_dir
        code, out = git_lines(gd, "show", "--stat", "--oneline", rev)
        pins[label] = {"pin": rev, "carries_bind_file": path in out}
    return pins


def check_packet(consumers):
    """Verify the packet names every exact downstream consumer."""
    if not isinstance(consumers, (list, tuple)):
        raise OwnershipError("consumers must be a list")
    missing = [c for c in DOWNSTREAM_CONSUMERS if c not in consumers]
    if missing:
        raise OwnershipError("packet missing consumers: %s" % missing)
    return {"consumers": list(consumers), "complete": True}
