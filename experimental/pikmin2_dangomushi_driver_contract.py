"""DangoMushi natural-death/reset driver contract (#664).

Review-only packet for the #376 family owner, unblocking stopped consumer
`dangomushi94-death-cleanup-observer` (gates 4 death_corpse and 6
cleanup_reentry). No family edits, no shared edits, no builds, no runtime,
no ADMIT. All six gates UNTESTED.

Finding (anchored, read-only): the family module already provides every hook
the driver needs - bind, window-gated damage acceptance, death transition,
corpse via die(), reset, forget - so NO family-side change is required. The
driver is entirely fixture-side. This module records that finding with
file:line anchors, the exact (empty) family patch, validation commands, and
the downstream consumers. If the owner prefers an explicit hook, the packet
names the single minimal candidate; nothing is applied here.
"""
import re
from pathlib import Path

ISSUE = 664
FAMILY_ISSUE = 376
SOURCE_ID = 94
FAMILY_FILE = "native/pc_port/pc_p2_dangomushi.cpp"
FAMILY_REF = "claude/p2-deepseek-wave-native"
FILE_SHA256 = "7bfa206c518e49a46d17802778fc0c7c8b7deb9f0db0c499d186431cf28ecb36"

ANCHORS = {
    "reset": (668, "void pc_p2_dangomushi_reset() {"),
    "forget": (675, "void pc_p2_dangomushi_forget(BTeki* actor) { actors.erase(static_cast<PelletView*>(actor)); }"),
    "damage_gate": (706, "bool pc_p2_dangomushi_invulnerable(const BTeki* actor) {"),
    "damage_accepted": (715, "std::printf(\"P2_DANGOMUSHI_DAMAGE_ACCEPTED generator=%u stickable=1 state=%s\\n\","),
    "damage_rejected": (725, "std::printf(\"P2_DANGOMUSHI_DAMAGE_REJECTED generator=%u stickable=0 invulnerable=1 \""),
    "setup": (732, "void pc_p2_dangomushi_setup() {"),
    "bind": (823, "std::printf(\"P2_DANGOMUSHI_BIND generator=%u source_id=94 visual_only=0\\n\","),
    "death_guard": (852, "if (actor->mHealth <= 0.0f && s.state != DANGO_DEAD) {"),
    "death_marker": (854, "std::printf(\"P2_DANGOMUSHI_DEAD generator=%u source_id=94 health=0\\n\", generator);"),
    "death_enter": (858, "setState(actor, s, DANGO_DEAD, \"dead\");"),
    "corpse_die": (1020, "if (s.stateTime >= clipDuration(\"dead\")) actor->die();"),
}

# The driver is fixture-side; no family diff exists. Recorded explicitly so a
# reviewer can distinguish "no change needed" from "change omitted".
FAMILY_PATCH = ""
NO_PATCH_RATIONALE = (
    "bind/death/reset/forget plus window-gated damage acceptance already exist "
    "at the anchors above; the driver observes P2_DANGOMUSHI_DAMAGE_ACCEPTED "
    "windows and drives the documented fixture-side sequence. No family edit."
)

# Acceptance interface: the validated observer contract legs (read-only).
OBSERVER_LEGS = (
    "P2_DANGOMUSHI_BIND generator=<id> source_id=94",
    "P2_DANGOMUSHI_DEAD generator=<id> source_id=94 health=0 (after bind)",
    "P2_BATCH3_DRAW corpse=1 key=DangoMushi clip=<dead> (after death)",
    "second P2_DANGOMUSHI_BIND same id (after corpse) = re-entry",
)

DRIVER_SPEC = (
    "bind: pc_p2_dangomushi_setup() binds the wanted generator; require TEKI vehicle + P2_DANGOMUSHI_BIND",
    "damage: real free-squad Attack orders; proceed only on P2_DANGOMUSHI_DAMAGE_ACCEPTED windows; no health writes",
    "death: await P2_DANGOMUSHI_DEAD health=0; require natural health decreases first",
    "corpse: locate the engine corpse pellet via mPelletView; require P2_BATCH3_DRAW corpse=1 key=DangoMushi",
    "reset: pc_p2_dangomushi_forget + reset; generator re-init; setup; require re-bind with stale/fresh proof",
)

DOWNSTREAM = ("dangomushi94 gates 4/6", "#376 family owner")


class ContractError(ValueError):
    """Malformed contract input or failed anchor verification."""


def contract():
    """Return the review packet data (no I/O, no fabrication)."""
    return dict(
        issue=ISSUE,
        family_issue=FAMILY_ISSUE,
        source_id=SOURCE_ID,
        family_file=FAMILY_FILE,
        family_ref=FAMILY_REF,
        file_sha256=FILE_SHA256,
        anchors={k: {"line": v[0], "text": v[1]} for k, v in ANCHORS.items()},
        family_patch=FAMILY_PATCH,
        no_patch_rationale=NO_PATCH_RATIONALE,
        driver_spec=list(DRIVER_SPEC),
        observer_legs=list(OBSERVER_LEGS),
        downstream=list(DOWNSTREAM),
        gates="all six UNTESTED; no ADMIT",
    )


def verify_anchors(native_file_path):
    """Check every anchor line against the pinned family file (read-only)."""
    path = Path(native_file_path)
    if not path.is_file():
        raise ContractError("missing family file: %s" % native_file_path)
    try:
        lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ContractError("unreadable family file: %s" % exc)
    report = {}
    for name, (line, text) in ANCHORS.items():
        if not isinstance(line, int) or line < 1 or not isinstance(text, str) or not text:
            raise ContractError("malformed anchor record: %s" % name)
        actual = lines[line - 1] if line <= len(lines) else None
        if actual is None or actual.strip() != text.strip():
            raise ContractError("anchor mismatch at %s:%d" % (FAMILY_FILE, line))
        report[name] = {"line": line, "verified": True}
    return report


def validate_packet(packet):
    """Validate a review packet dict (schema + observer-leg alignment)."""
    if not isinstance(packet, dict):
        raise ContractError("packet must be a dict")
    for key in ("issue", "family_issue", "source_id", "family_file", "anchors",
                "family_patch", "driver_spec", "observer_legs", "downstream"):
        if key not in packet:
            raise ContractError("missing packet field: %s" % key)
    if packet["issue"] != ISSUE or packet["family_issue"] != FAMILY_ISSUE:
        raise ContractError("packet issue mismatch")
    if packet["source_id"] != SOURCE_ID:
        raise ContractError("packet source-id mismatch")
    if not isinstance(packet["anchors"], dict) or not packet["anchors"]:
        raise ContractError("packet anchors missing")
    if not isinstance(packet["family_patch"], str):
        raise ContractError("packet patch must be a string")
    if not isinstance(packet["driver_spec"], list) or not packet["driver_spec"]:
        raise ContractError("packet driver spec missing")
    legs = packet["observer_legs"]
    if not isinstance(legs, list) or len(legs) != 4:
        raise ContractError("packet must carry the four observer legs")
    for token in ("P2_DANGOMUSHI_BIND", "P2_DANGOMUSHI_DEAD", "P2_BATCH3_DRAW"):
        if not any(token in leg for leg in legs):
            raise ContractError("observer leg missing token: %s" % token)
    if not isinstance(packet["downstream"], (list, tuple)) or not packet["downstream"]:
        raise ContractError("packet downstream missing")
    return packet