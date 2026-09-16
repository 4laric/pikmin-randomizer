"""Correlated natural generated-birth observer for BombSarai 58 (l59, #499).

Muse-bombsarai owns gate1 (identity_spawn) for source ID 58 only. Lane 27
owns the family projectile/FSM seam and its teki-carrier marker contract
(``experimental/pikmin2_bombsarai_teki_log.py``); this module is an ADDITIVE
layer on top of that contract, never a replacement. It answers one question:
do the placement resolve, the source resolve, and the actor binding markers
all name the SAME generated identity?

The three legs that must agree on one generator id:

1. Placement leg (muse-placement #492): a candidate generated-placement
   record resolving ``generator -> source_id 58``.
2. Source leg: the decomp source resolve, ``EnemyID_BombSarai = 58``
   (generator name ``バクダンサライ`` in ``genEnemy.cpp``).
3. Binding leg (lane 27, read-only): ``P2_BOMBSARAI_TEKI_READY`` /
   ``P2_BOMBSARAI_TEKI_SUPPLY`` markers from the generated Napkid vehicle
   carrying the same generator id.

A P1 Napkid birth alone (READY without a matching placement resolve to
source 58) is NOT a generated BombSarai identity and never correlates.
Without a placement record the verdict is ``placement-pending`` (BLOCKED),
never PASS. Dependency-free except for the optional lane-27 import, which
degrades to a local minimal parse when unavailable.

Generation-2 addition (consuming reviewed #492/#493 candidates):
``validate_generated_birth`` derives every leg from one native log using the
real marker contract — ``P2_SEED_RESOLVE source_id=58 target=<uid>`` (seed
bridge), ``P2_GENERATED_PLACEMENT source_id=58 target=<uid> generator=<g>
bound=1`` (muse-placement native bind path, accepted uid 1787125272), and
the lane-27 ``P2_BOMBSARAI_TEKI_READY``/``SUPPLY`` binding markers on the
same generator ``<g>``. It reuses the cherry-picked
``experimental.pikmin2_muse_placement.observe_identity`` (never forked) for
the resolve/bind/accepted-slot leg and adds only the generator cross-check
to the teki vehicle leg.
"""
import math
import re

BOMBSARAI_SOURCE_ID = 58
BOMBSARAI_GENERATOR_NAME = "バクダンサライ"
# P1 vehicle type the generated carrier binds (TEKI_Napkid); recorded so the
# observer can label the vehicle leg honestly instead of passing it off as a
# P2 identity.
NAPKID_VEHICLE_TYPE = 11

_MARKER_GENERATOR_RE = re.compile(
    r"^P2_BOMBSARAI_TEKI_(READY|SUPPLY|THROW|BLAST|DEAD)\b.*\bgenerator=(\d+)"
)
_INT_FIELD_RE = re.compile(r"\b(source_id|generator|slot|type)\s*=\s*(\d+)")
# Real native bind marker for source 58 (muse-placement #492 bind path).
_BIND_58_RE = re.compile(
    r"^P2_GENERATED_PLACEMENT\s+source_id=58\s+target=(\d+)"
    r"(?:\s+generator=(\d+))?\s+bound=(\d)"
)


def parse_placement_record(record):
    """Parse a candidate generated-placement record.

    Accepts a dict with ``source_id``/``generator`` keys or a text record
    such as ``P2_GENERATED_PLACEMENT source_id=58 generator=270001``.
    Returns ``{"source_id": int, "generator": int}`` or ``None`` when the
    record is missing or unparseable. Finite integers only.
    """
    if record is None:
        return None
    if isinstance(record, dict):
        try:
            source_id = int(record.get("source_id"))
            generator = int(record.get("generator"))
        except (TypeError, ValueError):
            return None
        if not (math.isfinite(source_id) and math.isfinite(generator)):
            return None
        return {"source_id": source_id, "generator": generator}
    if isinstance(record, str):
        fields = dict(_INT_FIELD_RE.findall(record))
        if "source_id" not in fields or "generator" not in fields:
            return None
        try:
            return {"source_id": int(fields["source_id"]),
                    "generator": int(fields["generator"])}
        except ValueError:
            return None
    return None


def _binding_generators(log_text):
    """Collect per-marker generator ids for the binding leg.

    Returns ``{"READY": [...], "SUPPLY": [...], "THROW": [...], ...}`` with
    generator ints in log order. Unknown/malformed lines are ignored.
    """
    found = {}
    if not log_text:
        return found
    for line in log_text.splitlines():
        match = _MARKER_GENERATOR_RE.match(line.strip())
        if not match:
            continue
        found.setdefault(match.group(1), []).append(int(match.group(2)))
    return found


def _lane27_gates(log_text):
    """Run the lane-27 marker validator when importable (read-only reuse)."""
    try:
        from experimental.pikmin2_bombsarai_teki_log import (
            validate_teki_markers,
        )
    except ImportError:
        return None
    return validate_teki_markers(log_text)


def _placement_row(log_text):
    """Run the muse-placement observer for source 58 (reused, never forked)."""
    try:
        from experimental.pikmin2_muse_placement import observe_identity
    except ImportError:
        return None
    return observe_identity(log_text, BOMBSARAI_SOURCE_ID)


def _bind_58_generator(log_text):
    """Last bound=1 ``P2_GENERATED_PLACEMENT`` generator for source 58.

    Returns ``(target_uid, generator)`` or ``(None, None)`` when no bound
    marker exists. A bound=0 marker is a fail-closed refusal, never a bind.
    """
    found = (None, None)
    if not log_text:
        return found
    for line in log_text.splitlines():
        match = _BIND_58_RE.match(line.strip())
        if not match or match.group(3) != "1":
            continue
        target = int(match.group(1))
        generator = int(match.group(2)) if match.group(2) else None
        found = (target, generator)
    return found


def validate_generated_birth(log_text):
    """Validate the generated birth for BombSarai 58 from one native log.

    Every leg is derived from real markers: ``P2_SEED_RESOLVE`` (seed
    bridge), ``P2_GENERATED_PLACEMENT ... bound=1`` on the accepted slot
    (muse-placement bind path), and ``P2_BOMBSARAI_TEKI_READY``/``SUPPLY``
    (lane-27 vehicle binding) on the SAME generator the bind marker names.
    Returns ``{"legs": {...bool...}, "correlated": bool, "reason": str,
    "generators": {...}, "uids": {...}, "placement": row|None,
    "lane27": {...}|None}``. ``reason`` names the exact failing leg:
    ``no-ready`` / ``seed-unresolved`` / ``placement-refused`` /
    ``slot-mismatch`` / ``generator-mismatch`` / ``supply-missing`` /
    ``correlated``. Never correlates without all six legs.
    """
    legs = {"actor_bound": False, "supplied": False,
            "seed_resolved": False, "placement_bound": False,
            "slot_accepted": False, "generator_agree": False}
    text = log_text or ""
    binding = _binding_generators(text)
    ready = binding.get("READY", [])
    bound_generator = ready[0] if ready else None
    if ready:
        legs["actor_bound"] = True
    if bound_generator is not None and bound_generator in binding.get(
            "SUPPLY", []):
        legs["supplied"] = True

    row = _placement_row(text)
    resolved_uid = row["resolved_uid"] if row else None
    row_bound_uid = row["bound_uid"] if row else None
    if resolved_uid is not None:
        legs["seed_resolved"] = True
    if row and row["bound"]:
        legs["placement_bound"] = True
    if row and row["correlated"]:
        legs["slot_accepted"] = True

    bind_target, bind_generator = _bind_58_generator(text)
    if (bound_generator is not None and bind_generator is not None
            and bind_generator == bound_generator):
        legs["generator_agree"] = True

    if not ready:
        reason = "no-ready"
    elif not legs["seed_resolved"]:
        reason = "seed-unresolved"
    elif not legs["placement_bound"]:
        reason = "placement-refused"
    elif not legs["slot_accepted"]:
        reason = "slot-mismatch"
    elif not legs["generator_agree"]:
        reason = "generator-mismatch"
    elif not legs["supplied"]:
        reason = "supply-missing"
    else:
        reason = "correlated"
    return {"legs": legs,
            "correlated": reason == "correlated",
            "reason": reason,
            "generators": {"bound": bound_generator,
                           "placement": bind_generator},
            "uids": {"resolved": resolved_uid,
                     "bound": row_bound_uid,
                     "placement_target": bind_target,
                     "accepted": (row["accepted_uid"] if row else None)},
            "placement": row,
            "lane27": _lane27_gates(text)}


def validate_correlated_birth(log_text, placement=None):
    """Validate the correlated generated-birth chain for BombSarai 58.

    Returns ``{"legs": {...bool...}, "correlated": bool, "reason": str,
    "generators": {...}, "lane27": {...}|None}``. ``correlated`` is True
    only when a READY-bound actor, a SUPPLY from the same generator, a
    placement resolve to source 58, and a placement generator equal to the
    bound generator all hold. Any other outcome reports the exact failing
    leg in ``reason``; a missing/unparseable placement record reports
    ``placement-pending``/``placement-unparseable`` and never correlates.
    """
    legs = {"actor_bound": False, "supplied": False,
            "source_agree": False, "placement_agree": False}
    binding = _binding_generators(log_text or "")
    ready = binding.get("READY", [])
    if ready:
        legs["actor_bound"] = True
    bound_generator = ready[0] if ready else None
    supplied_here = [g for g in binding.get("SUPPLY", [])
                     if g == bound_generator]
    if bound_generator is not None and supplied_here:
        legs["supplied"] = True

    parsed = parse_placement_record(placement)
    if parsed is not None:
        legs["source_agree"] = (parsed["source_id"] == BOMBSARAI_SOURCE_ID)
        legs["placement_agree"] = (parsed["generator"] == bound_generator)

    if not ready:
        reason = "no-ready"
    elif placement is None:
        reason = "placement-pending"
    elif parsed is None:
        reason = "placement-unparseable"
    elif not legs["source_agree"]:
        reason = "source-mismatch"
    elif not legs["placement_agree"]:
        reason = "generator-mismatch"
    elif not legs["supplied"]:
        reason = "supply-missing"
    else:
        reason = "correlated"
    return {"legs": legs,
            "correlated": reason == "correlated",
            "reason": reason,
            "generators": {"bound": bound_generator,
                           "placement": (parsed["generator"]
                                         if parsed else None)},
            "lane27": _lane27_gates(log_text)}
