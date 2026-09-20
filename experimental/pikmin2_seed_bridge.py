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
    admitted_ids,
    by_id,
    load_roster,
)
from randomizer.seed import SeedRandom

LAYOUT_VERSION = "p2-enemy-layout-v1"
PROTOCOL_HEADER = "ENEMY_P2"
PROTOCOL_VERSION = 1

# Density policy for `resolve_placement_layout` (#838). The policy is stored in
# the manifest's ``p2_layout`` so a loaded seed can be rederived/rejected, and it
# keeps legacy manifests (which carry no ``density`` key) unchanged.
DENSITY_POLICY_KEY = "density"
DENSITY_LEGACY = "all-targets-v1"
DENSITY_BOUNDED = "bounded-coverage-v1"
DENSITY_POLICIES = (DENSITY_LEGACY, DENSITY_BOUNDED)


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


def validate_density(density) -> str:
    """Return a recognised density policy token.

    ``None`` is the product default and means the unchanged all-target fill; a
    caller that wants bounded coverage must ask for it explicitly by token.
    """
    if density is None:
        return DENSITY_LEGACY
    if density not in DENSITY_POLICIES:
        raise SeedBridgeError(
            f"unknown P2 density policy {density!r}; expected one of {list(DENSITY_POLICIES)}")
    return density


def _layout_density(layout) -> str:
    """Density policy stored on a layout; absent/None means the legacy default."""
    if not isinstance(layout, dict):
        raise SeedBridgeError("P2 layout must be a mapping")
    density = layout.get(DENSITY_POLICY_KEY)
    if density is None:
        return DENSITY_LEGACY
    if density not in DENSITY_POLICIES:
        raise SeedBridgeError(f"unsupported P2 layout density policy: {density!r}")
    return density


def resolve_admitted_layout(seed, slot, targets, roster: list[RosterEntry] | None = None) -> dict:
    """Bind the lane 02 admitted cohort; fail closed when nothing is admitted.

    This is the product entry point. It never accepts an explicit cohort, so a
    caller cannot seed an identity that lane 02 has not admitted.
    """
    roster = roster if roster is not None else load_roster()
    cohort = admitted_ids(roster)
    if not cohort:
        raise SeedBridgeError(
            "no admitted P2 identities; refusing to seed an unadmitted pool (lane 02 admission set is empty)"
        )
    return resolve_layout(seed, slot, targets, cohort, roster, admitted=cohort)


def _accepted_placement_targets(document, roster: list[RosterEntry]) -> dict[int, set[str]]:
    """Map each admitted source ID to the target tokens lane 04 *accepts* for it.

    This is the evidence gate (``randomizer.p2_placement.audit`` -> ``evaluate``,
    which requires accepted placement gates and slot XYZ/terrain/route evidence),
    kept separate from lane 04's constraint-only catalog below.
    """
    from randomizer.p2_placement import audit
    by_enum = {entry.enum_name: entry for entry in roster}
    accepted: dict[int, set[str]] = {}
    for identity, uids in audit(document).get("admitted", {}).items():
        entry = by_enum.get(identity)
        if entry is not None:
            accepted.setdefault(entry.source_id, set()).update(str(uid) for uid in uids)
    return accepted


def binding_targets_from_placement(document, roster: list[RosterEntry] | None = None) -> list[str]:
    """Ordered lane 04 constraint-compatible targets for the admitted cohort.

    Delegates to ``randomizer.p2_placement_catalog.binding_targets_for_sources``,
    which is lane 04's flat binding-target contract (constraint compatibility
    only; acceptance is enforced separately by :func:`resolve_placement_layout`).
    """
    from randomizer import p2_placement_catalog as catalog
    from randomizer.p2_placement import validate_document
    roster = roster if roster is not None else load_roster()
    admitted = admitted_ids(roster)
    if not admitted:
        raise SeedBridgeError(
            "no admitted P2 identities; refusing to seed an unadmitted pool (lane 02 admission set is empty)"
        )
    document = validate_document(document)
    try:
        targets = catalog.binding_targets_for_sources(admitted, document=document)
    except ValueError as exc:
        raise SeedBridgeError(f"placement catalog rejected the admitted cohort: {exc}") from exc
    if not targets:
        raise SeedBridgeError("placement document has no constraint-compatible admitted target")
    return targets


def resolve_placement_layout(seed, slot, document, roster: list[RosterEntry] | None = None, *,
                             species=None, density=None) -> dict:
    """Bind lane 04 targets to admitted identities that the document *accepts*.

    Targets come from lane 04's constraint catalog; each is then bound only to an
    identity with accepted placement evidence for it. Every admitted identity
    must have an accepted target, and each is guaranteed at least one binding.
    Fails closed while the admission set is empty or no pair is accepted.

    ``species`` optionally narrows the pool to a subset of the admitted ids;
    targets only those excluded species could fill stay vanilla (unbound).

    ``density`` selects the versioned fill policy recorded as
    ``layout["density"]``. The default ``None`` is the legacy all-target fill
    (:data:`DENSITY_LEGACY`): every accepted target is bound, so a one-species
    request still replaces every compatible target. :data:`DENSITY_BOUNDED`
    binds the minimum number of targets that gives every selected species at
    least one binding and leaves the remaining compatible targets vanilla. Both
    policies share the same RNG stream prefix, so bounded role assignment is a
    stable function of the same roll. Insufficient unique accepted targets still
    fail closed under either policy; there is no species special case.
    """
    policy = validate_density(density)
    roster = roster if roster is not None else load_roster()
    admitted = list(admitted_ids(roster))
    if species is not None:
        wanted = set(species)
        if not wanted or not wanted <= set(admitted):
            raise SeedBridgeError(f"P2 species subset must be a nonempty subset of the admitted ids {sorted(admitted)}: {sorted(wanted)}")
        admitted = [source_id for source_id in admitted if source_id in wanted]
    if not admitted:
        raise SeedBridgeError(
            "no admitted P2 identities; refusing to seed an unadmitted pool (lane 02 admission set is empty)"
        )
    targets = binding_targets_from_placement(document, roster)
    accepted = _accepted_placement_targets(document, roster)
    admitted_set = set(admitted)
    eligible: dict[str, list[int]] = {}
    for target in targets:
        ids = sorted(source_id for source_id, tokens in accepted.items()
                     if source_id in admitted_set and target in tokens)
        if ids:
            eligible[target] = ids
    if not eligible:
        raise SeedBridgeError("no admitted identity has accepted placement evidence in the document")
    uncovered = [source_id for source_id in admitted
                 if not any(source_id in ids for ids in eligible.values())]
    if uncovered:
        raise SeedBridgeError(f"admitted identities have no accepted placement target: {uncovered}")

    revision = roster_revision(roster)
    by_source = by_id(roster)
    rng = SeedRandom(f"{seed}/p2-placement-layout-v1/{slot}")
    # Shared with the legacy fill below: the identity order and the target sort
    # are pinned so bounded mode reuses the same deterministic roll.
    identity_order = rng.shuffle(admitted)
    remaining = sorted(eligible, key=lambda item: (len(item), item))
    # Assign the first unique target to each identity in turn. The legacy
    # all-target fill continues the same roll, so both policies share coverage
    # and remain stable functions of ``(seed, slot, document, species)``.
    assigned: dict[str, int] = {}
    for source_id in identity_order:
        choices = [target for target in remaining if source_id in eligible[target]]
        if not choices:
            continue
        target = rng.shuffle(choices)[0]
        assigned[target] = source_id
        remaining.remove(target)
    if policy == DENSITY_LEGACY:
        for target in remaining:
            assigned[target] = rng.shuffle(eligible[target])[0]
    # Fail closed: every admitted identity must end up bound to at least one
    # target. A target is assigned to exactly one identity, so when two admitted
    # identities share only one accepted slot (e.g. Snow 45 and Dwarf Orange 44
    # reuse the same P1 Dwarf-Bulborb host slot) the second identity is silently
    # dropped unless we reject here. This keeps the slot contract default-deny.
    covered = set(assigned.values())
    uncovered = [source_id for source_id in admitted if source_id not in covered]
    if uncovered:
        raise SeedBridgeError(
            f"admitted identities have no unique accepted placement target: {uncovered}")
    bindings = [{"target": target, "source_id": source_id,
                 "enum_name": by_source[source_id].enum_name}
                for target, source_id in sorted(assigned.items(), key=lambda item: (len(item[0]), item[0]))]
    return {"version": LAYOUT_VERSION, "roster_schema": ROSTER_SCHEMA,
            "roster_revision": revision, DENSITY_POLICY_KEY: policy,
            "bindings": bindings}


def resolve_layout(seed, slot, targets, cohort, roster: list[RosterEntry] | None = None, *,
                   admitted=None, density=None) -> dict:
    """Deterministically bind each target to an identity from ``cohort``.

    ``admitted`` is an optional allowlist; when supplied every cohort id must be
    in it. The product path supplies lane 02's admission set through
    :func:`resolve_admitted_layout`; tests and lane 04 placement may pass an
    explicit cohort.

    ``density`` is stored on the layout and honoured when rederived. The legacy
    default (:data:`DENSITY_LEGACY`) fills every ordered target; the bounded
    policy binds the minimum number of leading targets that gives every cohort
    identity at least one binding and leaves the rest vanilla. Insufficient
    targets still fail closed.
    """
    policy = validate_density(density)
    roster = roster if roster is not None else load_roster()
    revision = roster_revision(roster)
    target_ids = validate_targets(targets)
    cohort_ids = validate_cohort(roster, cohort)

    if admitted is not None:
        allowed = set(admitted)
        unadmitted = sorted({source_id for source_id in cohort_ids if source_id not in allowed})
        if unadmitted:
            raise SeedBridgeError(f"cohort contains unadmitted source ids: {unadmitted}")

    if len(target_ids) < len(cohort_ids):
        raise SeedBridgeError("not enough binding targets to cover the admitted cohort")

    rng = SeedRandom(f"{seed}/p2-enemy-layout-v1/{slot}")
    values = list(rng.shuffle(cohort_ids))
    used_targets = target_ids
    if policy == DENSITY_BOUNDED:
        used_targets = target_ids[:len(cohort_ids)]
    else:
        while len(values) < len(target_ids):
            values.append(rng.shuffle(list(cohort_ids))[0])
        values = rng.shuffle(values)
    by_source = by_id(roster)
    return {
        "version": LAYOUT_VERSION,
        "roster_schema": ROSTER_SCHEMA,
        "roster_revision": revision,
        DENSITY_POLICY_KEY: policy,
        "bindings": [
            {"target": target, "source_id": source_id, "enum_name": by_source[source_id].enum_name}
            for target, source_id in zip(used_targets, values)
        ],
    }


def validate_layout(layout: dict, roster: list[RosterEntry] | None = None, *, admitted=None) -> None:
    """Validate a layout structurally, and optionally against the current admission set.

    ``admitted`` is supplied by the product manifest path so a loaded seed whose
    bound identity is no longer admitted is rejected; diagnostic callers omit it.
    """
    roster = roster if roster is not None else load_roster()
    if layout.get("version") != LAYOUT_VERSION:
        raise SeedBridgeError(f"unsupported P2 layout version: {layout.get('version')!r}")
    # Absent/None means the legacy all-target fill; any other value must be a
    # recognised token so a tampered manifest is rejected rather than re-rolled.
    _layout_density(layout)
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
    if admitted is not None:
        allowed = set(admitted)
        unadmitted = sorted({binding["source_id"] for binding in bindings if binding["source_id"] not in allowed})
        if unadmitted:
            raise SeedBridgeError(f"P2 layout binds unadmitted source ids: {unadmitted}")


def build_bootstrap(layout: dict, roster: list[RosterEntry] | None = None) -> str:
    """Emit the native bootstrap line, or empty string when no P2 layout is present."""
    if not layout:
        return ""
    validate_layout(layout, roster)
    parts = [PROTOCOL_HEADER, str(PROTOCOL_VERSION), layout["roster_revision"], str(len(layout["bindings"]))]
    for binding in layout["bindings"]:
        parts += [binding["target"], str(binding["source_id"])]
    return " ".join(parts) + "\n"


def parse_bootstrap(text: str, roster: list[RosterEntry] | None = None, *,
                    density=None) -> dict:
    """Parse a native ``ENEMY_P2`` line back into a layout; rejects malformed input.

    The wire format carries only the bindings, so the density policy is not on
    the line. ``density`` lets a caller reconstruct the policy the manifest
    stored; it defaults to the legacy all-target fill.
    """
    policy = validate_density(density)
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
        DENSITY_POLICY_KEY: policy,
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
