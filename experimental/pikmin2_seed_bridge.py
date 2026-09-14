"""Versioned P2 enemy seed choices and deterministic native manifest binding.

Lane 03 (#439), consuming the lane 02 roster (#438).

Contract
--------
* A P2 layout is a pure function of ``(seed, slot, roster revision, targets,
  admitted cohort)``. The same seed/revisit/restart therefore resolves to the
  same identity; no runtime order or address participates in the roll.
* The layout stores the roster schema and revision. A later roster change makes
  the saved revision mismatch and the seed is rejected instead of silently
  re-rolled. Legacy (non-P2) seeds carry no ``p2_layout`` and are unchanged.
* Only ``enemy``/``boss`` classifications may be bound. ``manager_base``,
  ``non_spawnable``, plants, hazards and projectiles are rejected, never
  substituted with a P1 analogue.
* Placement (lane 04) supplies the ordered binding targets; this module never
  invents positions. Content staging (lane 05) supplies the assets keyed by
  ``source_id``/``enum_name``.
"""
from __future__ import annotations

import hashlib
import json
import re

from experimental.pikmin2_enemy_roster import (
    SCHEMA as ROSTER_SCHEMA,
    RosterEntry,
    by_id,
    load_roster,
)
from randomizer.seed import SeedRandom

LAYOUT_VERSION = "p2-enemy-layout-v1"
PROTOCOL_HEADER = "ENEMY_P2"
PROTOCOL_VERSION = 1


class SeedBridgeError(ValueError):
    """Raised when a P2 seed layout or bootstrap line is invalid."""


def roster_revision(roster: list[RosterEntry] | None = None) -> str:
    """Stable hash of the roster's identity set; changes if any ID/name changes."""
    roster = roster if roster is not None else load_roster()
    payload = [
        [entry.source_id, entry.enum_name, entry.classification]
        for entry in sorted(roster, key=lambda item: item.source_id)
    ]
    return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()


def eligible_identity(roster: list[RosterEntry], source_id: int) -> RosterEntry:
    entry = by_id(roster).get(source_id)
    if entry is None:
        raise SeedBridgeError(f"unknown P2 source id {source_id}")
    if entry.classification not in ("enemy", "boss"):
        raise SeedBridgeError(
            f"source id {source_id} ({entry.enum_name}) is {entry.classification}; not bindable"
        )
    return entry


def validate_cohort(roster: list[RosterEntry], cohort) -> list[int]:
    ids = list(cohort)
    if any(type(source_id) is not int for source_id in ids):
        raise SeedBridgeError("source ids must be integers")
    if not ids:
        raise SeedBridgeError("admitted cohort is empty; lane 03 cannot seed an unadmitted pool")
    if len(ids) != len(set(ids)):
        raise SeedBridgeError("admitted cohort contains duplicate source ids")
    for source_id in ids:
        eligible_identity(roster, source_id)
    return ids


def validate_targets(targets) -> list[str]:
    values = list(targets)
    if any(not isinstance(target, str) or not re.fullmatch(r"[A-Za-z0-9_.:/-]+", target) for target in values):
        raise SeedBridgeError("binding targets must be nonempty protocol tokens")
    if not values:
        raise SeedBridgeError("binding targets are empty")
    if len(values) != len(set(values)):
        raise SeedBridgeError("binding targets contain duplicates")
    return values


def resolve_layout(seed, slot, targets, cohort, roster: list[RosterEntry] | None = None) -> dict:
    """Deterministically bind each target to an admitted identity."""
    roster = roster if roster is not None else load_roster()
    revision = roster_revision(roster)
    target_ids = validate_targets(targets)
    cohort_ids = validate_cohort(roster, cohort)

    if len(target_ids) < len(cohort_ids):
        raise SeedBridgeError("not enough binding targets to cover the admitted cohort")

    rng = SeedRandom(f"{seed}/p2-enemy-layout-v1/{slot}")
    values = list(cohort_ids)
    while len(values) < len(target_ids):
        values.append(rng.shuffle(list(cohort_ids))[0])
    values = rng.shuffle(values)
    by_source = by_id(roster)
    return {
        "version": LAYOUT_VERSION,
        "roster_schema": ROSTER_SCHEMA,
        "roster_revision": revision,
        "bindings": [
            {"target": target, "source_id": source_id, "enum_name": by_source[source_id].enum_name}
            for target, source_id in zip(target_ids, values)
        ],
    }


def validate_layout(layout: dict, roster: list[RosterEntry] | None = None) -> None:
    roster = roster if roster is not None else load_roster()
    if layout.get("version") != LAYOUT_VERSION:
        raise SeedBridgeError(f"unsupported P2 layout version: {layout.get('version')!r}")
    if layout.get("roster_schema") != ROSTER_SCHEMA:
        raise SeedBridgeError(f"unsupported roster schema: {layout.get('roster_schema')!r}")
    if layout.get("roster_revision") != roster_revision(roster):
        raise SeedBridgeError("P2 layout roster revision does not match the current roster; regenerate the seed")
    bindings = layout.get("bindings")
    if not isinstance(bindings, list) or not bindings:
        raise SeedBridgeError("P2 layout has no bindings")
    seen: set[str] = set()
    for binding in bindings:
        target = binding.get("target")
        source_id = binding.get("source_id")
        if not isinstance(target, str) or not re.fullmatch(r"[A-Za-z0-9_.:/-]+", target) or target in seen:
            raise SeedBridgeError(f"invalid or duplicate P2 binding target: {target!r}")
        seen.add(target)
        if not isinstance(source_id, int) or isinstance(source_id, bool):
            raise SeedBridgeError(f"invalid P2 source id: {source_id!r}")
        entry = eligible_identity(roster, source_id)
        if binding.get("enum_name") != entry.enum_name:
            raise SeedBridgeError(f"binding {target} enum mismatch: {binding.get('enum_name')!r} != {entry.enum_name!r}")


def build_bootstrap(layout: dict, roster: list[RosterEntry] | None = None) -> str:
    """Emit the native bootstrap line, or empty string when no P2 layout is present."""
    if not layout:
        return ""
    validate_layout(layout, roster)
    parts = [PROTOCOL_HEADER, str(PROTOCOL_VERSION), layout["roster_revision"], str(len(layout["bindings"]))]
    for binding in layout["bindings"]:
        parts += [binding["target"], str(binding["source_id"])]
    return " ".join(parts) + "\n"


def parse_bootstrap(text: str, roster: list[RosterEntry] | None = None) -> dict:
    """Parse a native ``ENEMY_P2`` line back into a layout; rejects malformed input."""
    tokens = text.split()
    if not tokens or tokens[0] != PROTOCOL_HEADER:
        raise SeedBridgeError(f"missing {PROTOCOL_HEADER} header")
    if len(tokens) < 4:
        raise SeedBridgeError("truncated ENEMY_P2 line")
    if tokens[1] != str(PROTOCOL_VERSION):
        raise SeedBridgeError(f"unsupported ENEMY_P2 protocol version: {tokens[1]}")
    revision = tokens[2]
    try:
        count = int(tokens[3])
    except ValueError as error:
        raise SeedBridgeError(f"invalid ENEMY_P2 binding count: {tokens[3]!r}") from error
    body = tokens[4:]
    if count <= 0 or len(body) != count * 2:
        raise SeedBridgeError(f"ENEMY_P2 count {count} does not match {len(body)} tokens")
    bindings = []
    for index in range(count):
        target, source_text = body[index * 2], body[index * 2 + 1]
        try:
            source_id = int(source_text)
        except ValueError as error:
            raise SeedBridgeError(f"invalid ENEMY_P2 source id: {source_text!r}") from error
        bindings.append({"target": target, "source_id": source_id})
    roster = roster if roster is not None else load_roster()
    layout = {
        "version": LAYOUT_VERSION,
        "roster_schema": ROSTER_SCHEMA,
        "roster_revision": revision,
        "bindings": [
            {"target": b["target"], "source_id": b["source_id"],
             "enum_name": eligible_identity(roster, b["source_id"]).enum_name}
            for b in bindings
        ],
    }
    validate_layout(layout, roster)
    return layout


def bootstrap_for_manifest(manifest: dict, roster: list[RosterEntry] | None = None) -> str:
    """Return the ENEMY_P2 line for a manifest, or '' for legacy seeds."""
    return build_bootstrap(manifest.get("p2_layout"), roster)
