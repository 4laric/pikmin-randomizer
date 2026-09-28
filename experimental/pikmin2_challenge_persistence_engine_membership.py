"""Challenge persistence engine membership contract (issue #725).

Lane challenge-persistence-engine-membership-native. Verifies, without a
build, that the #713 persistence module is a member of the pikmin_pc target
and that a fixture run proves the production engine emits the exact 7 probe
markers. Stdlib only.

Owned files only; #713/#718/#710 and pc_p2_challenge_persistence.{h,cpp} are
read-only inputs.
"""

import re

SCHEMA = "p2-challenge-persistence-engine-membership-v1"
ISSUE = 725
CONSUMER = {"lane": "p2-challenge-ch_mat_route_rover-p1", "issue": 561}
STAGE = "ch_MAT_route_rover"
STAGE_UI_INDEX = 27
STAGE_FLOORS = 1
MODULE_SOURCE = "pc_port/pc_p2_challenge_persistence.cpp"
TARGET = "pikmin_pc"
PROBE_STEMS = ("SAVE_KEY", "LOAD_KEY", "CLEAR", "HIGHSCORE", "UNLOCK",
               "RECEIPT_DEDUP", "REENTRY")
PASS_MARKER = "PASS P2_CHALLENGE_PERSISTENCE_MEMBERSHIP_RUN"
CAPTAIN_DOWN = "P2_FIXTURE_CAPTAIN_DOWN"
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"
FIXTURE_LOCAL_INCLUDE = '#include "../pc_port/pc_p2_challenge_persistence.cpp"'


def probe_marker(stem, stage=STAGE):
    return "P2_CHALLENGE_%s stage=%s" % (stem, stage)


def cmake_membership_ok(cmake_text):
    """True when MODULE_SOURCE is inside the PC_PORT_SOURCES list (not a comment)."""
    if MODULE_SOURCE not in cmake_text:
        return False
    lines = cmake_text.splitlines()
    try:
        start = next(i for i, l in enumerate(lines) if l.strip().startswith("set(PC_PORT_SOURCES"))
    except StopIteration:
        return False
    for line in lines[start + 1:]:
        stripped = line.strip()
        if stripped == ")" or stripped.startswith(")"):
            return False
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == MODULE_SOURCE:
            return True
    return False


def fixture_is_not_local_copy(fixture_text):
    """The membership fixture must not compile the module in itself."""
    return FIXTURE_LOCAL_INCLUDE not in fixture_text


def check_marker_log(text, stage=STAGE):
    """Return (ok, detail) for a membership run log; fail-closed."""
    if not isinstance(text, str):
        raise TypeError("marker log must be text")
    if CAPTAIN_DOWN in text:
        return False, "captain-down interruption present"
    if PASS_MARKER not in text:
        return False, "run PASS marker absent"
    missing = [s for s in PROBE_STEMS if probe_marker(s, stage) not in text]
    if missing:
        return False, "missing probe markers: %s" % ",".join(missing)
    for stem in PROBE_STEMS:
        if text.count(probe_marker(stem, stage)) != 1:
            return False, "probe marker not emitted exactly once: " + stem
    if "P2_CHALLENGE_PERSISTENCE_REFUSED" in text:
        return False, "persistence refusal present"
    return True, "run PASS with exact 7/7 probe markers"


def source_requirement_checklist():
    """Machine-readable statement of the two independent membership proofs."""
    return {
        "schema": SCHEMA,
        "issue": ISSUE,
        "consumer": CONSUMER,
        "target": TARGET,
        "module_source": MODULE_SOURCE,
        "stage": {"cave_id": STAGE, "ui_index": STAGE_UI_INDEX, "floors": STAGE_FLOORS},
        "probe_stems": list(PROBE_STEMS),
        "pass_marker": PASS_MARKER,
        "guard": {"path": "scripts/p2_fixture_captain_guard.h", "sha256": GUARD_SHA256},
        "proofs": [
            "link-time: the fixture references the recorders strongly and does not compile the module, so a successful link requires the CMake membership",
            "run-time: the production pc_bbft_update() callsite emits the exact 7 probe markers for the selected stage",
        ],
        "shared_review": "#186 owner review required before any shared-line landing of the CMake change",
    }
