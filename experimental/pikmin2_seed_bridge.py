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
# Native parser limit on ENEMY_P2 bindings per seed (pc_randomizer.cpp
# kP2MaxBindings). It was 64 until #948; the constraint-derived target set
# (every campaign generator, holders and arenas) needs more. Runtime cap:
# native refuses a seed above it.
P2_MAX_BINDINGS = 256
PROTOCOL_HEADER = "ENEMY_P2"
PROTOCOL_VERSION = 1

# Density policy for `resolve_placement_layout` (#838). The policy is stored in
# the manifest's ``p2_layout`` so a loaded seed can be rederived/rejected, and it
# keeps legacy manifests (which carry no ``density`` key) unchanged.
DENSITY_POLICY_KEY = "density"
DENSITY_LEGACY = "all-targets-v1"
DENSITY_BOUNDED = "bounded-coverage-v1"
DENSITY_SAMPLED = "sampled-v1"
DENSITY_POLICIES = (DENSITY_LEGACY, DENSITY_BOUNDED, DENSITY_SAMPLED)

# Playable P2 species assigned first under the sampled proxy policy so they
# are always present when selected. Mirrors randomizer.seed.PLAYABLE_P2_SPECIES
# without importing the seed module (which imports this bridge lazily).
# Keep in sync with P2_PLAYABLE_POOL (tests/test_p2_pool_roster_sync.py pins
# the equality); the 2026-09-26 roster wave grew this from the original six;
# admit-frogs5 (#871) appends Wtank 25 + Armor 15; #888 appends MiniHoudai 78;
# #215 appends Demon 32.
# #898 appends PanModoki (Breadbug) 38; #958 appends OoPanModoki (Giant Breadbug) 40.
# #244 appends BombSarai 58.
# #960 appends Kurage 57 and OniKurage 72; #256 Queen 30; #1042 Baby 31.
# #964 appends Catfish 26, Tadpole 27, Hana 84 and BombOtakara 93.
PLAYABLE_IDS = (44, 54, 59, 60, 61, 62, 79,
                2, 33, 35, 43, 53, 67, 76,
                28, 94, 68,
                75,
                63, 69,
                34, 70, 71, 101,
                25, 15, 78, 73, 32, 38, 40, 41, 58, 57, 72, 30, 31,
                26, 27, 84, 93, 66)


class SeedBridgeError(ValueError):
    """Raised when a P2 seed layout or bootstrap line is invalid."""


# P2 boss arenas (#899, owner ruling 2026-09-29): bosses whose placement profile
# is ``is_boss`` are placed only in the document's ``arenas`` (P1 boss spawns),
# never in the ordinary target fill, with their own RNG stream. A layout whose
# pool holds no such boss carries no ``boss_arenas`` key and is byte-identical
# to the pre-arena layout.
BOSS_ARENA_KEY = "boss_arenas"
BOSS_ARENA_VERSION = "p2-boss-arena-v1"


def arena_boss_ids(document, roster: list[RosterEntry] | None = None) -> set[int]:
    """Source ids whose placement profile in ``document`` is an arena boss."""
    roster = roster if roster is not None else load_roster()
    by_enum = {entry.enum_name: entry.source_id for entry in roster}
    return {by_enum[profile.get("identity")]
            for profile in (document or {}).get("profiles", []) or []
            if isinstance(profile, dict) and profile.get("is_boss")
            and profile.get("identity") in by_enum}


def _boss_slot_uids(document) -> set[str]:
    return {str(item.get("uid")) for item in (document or {}).get("slots", []) or []
            if isinstance(item, dict) and item.get("boss_slot")}


# P1 ship-part holder teki slots (#901, randomizer/p2_held_parts.py): a slot
# whose held_part_transfer flag is set is listed in the document's
# ``held_parts`` and accepted for the compatible ordinary identities. It is
# bound by its own RNG stream after the ordinary layout (a seed-stability
# design choice, #951 U18, not a placement rule: the occupant is drawn from
# the same pool). The P2 occupant holds the P1 holder's part natively
# (pc_held_part.cpp).
HELD_PART_KEY = "held_parts"
HELD_PART_VERSION = "p2-held-part-v1"


def _held_part_uids(document) -> set[str]:
    return {str(item.get("uid")) for item in (document or {}).get(HELD_PART_KEY, []) or []
            if isinstance(item, dict)}


def _assign_held_parts(seed, slot, document, roster: list[RosterEntry], pool,
                       bound=()) -> tuple[list[dict], dict]:
    """Bind one pool species to each transferable holder slot for this seed.

    A species the ordinary layout left unplaced is preferred, so a holder slot
    never repeats a species while an eligible one is missing from the seed.
    """
    from randomizer.p2_placement import validate_document
    validated = validate_document(document)
    holders = [row for row in validated.get(HELD_PART_KEY, []) if row["held_part_transfer"]]
    accepted = _accepted_placement_targets(document, roster)
    by_source = by_id(roster)
    rng = SeedRandom(f"{seed}/{HELD_PART_VERSION}/{slot}")
    pool = sorted(set(pool))
    bindings, placed = [], []
    for row in sorted(holders, key=lambda item: item["uid"]):
        token = str(row["uid"])
        choices = [source_id for source_id in pool if token in accepted.get(source_id, set())]
        if not choices:
            continue
        taken = set(bound) | {binding["source_id"] for binding in bindings}
        fresh = [source_id for source_id in choices if source_id not in taken]
        source_id = rng.shuffle(fresh or choices)[0]
        bindings.append({"target": token, "source_id": source_id,
                         "enum_name": by_source[source_id].enum_name})
        placed.append({"slot": row["label"], "target": token, "part": row["part"],
                       "source_id": source_id})
    return bindings, {"version": HELD_PART_VERSION, "placed": placed}


def _attach_held_parts(layout: dict, seed, slot, document, roster: list[RosterEntry], pool) -> dict:
    # The bounded policy binds the minimum number of targets; holder slots
    # stay vanilla there like every other spare target.
    if not _held_part_uids(document) or not pool or layout.get(DENSITY_POLICY_KEY) == DENSITY_BOUNDED:
        return layout
    bound = [binding["source_id"] for binding in layout["bindings"]]
    bindings, info = _assign_held_parts(seed, slot, document, roster, pool, bound)
    if not bindings:
        return layout
    combined = list(layout["bindings"]) + bindings
    if len({binding["target"] for binding in combined}) != len(combined):
        raise SeedBridgeError("held-part target collides with an ordinary P2 target")
    layout["bindings"] = _sort_bindings(combined)
    layout[HELD_PART_KEY] = info
    return layout


def _finish_layout(layout: dict, seed, slot, document, roster: list[RosterEntry], pool, boss_pool) -> dict:
    layout = _attach_held_parts(layout, seed, slot, document, roster, pool)
    return _attach_boss_arenas(layout, seed, slot, document, roster, boss_pool)


def _sort_bindings(bindings):
    return sorted(bindings, key=lambda item: (len(item["target"]), item["target"]))


def _assign_boss_arenas(seed, slot, document, roster: list[RosterEntry], boss_pool) -> tuple[list[dict], dict]:
    """Sample one arena per boss (at most one boss per arena) for this seed.

    An arena is eligible for a boss when lane 04 *accepts* the boss on the
    arena's primary slot (``evaluate``: accepted gates, slot evidence, not
    protected, encounter footprint within the measured clearance). Every
    spawn uid of a chosen arena is bound to the boss; suppressed arena mates
    are emptied natively. Bosses without a free eligible arena are recorded
    as unplaced; unchosen arenas keep their P1 boss.
    """
    from randomizer.p2_placement import validate_document
    validated = validate_document(document)
    arenas = {str(arena["primary_uid"]): arena for arena in validated.get("arenas", [])}
    accepted = _accepted_placement_targets(document, roster)
    by_source = by_id(roster)
    rng = SeedRandom(f"{seed}/{BOSS_ARENA_VERSION}/{slot}")
    free = sorted(arenas, key=int)
    chosen: dict[str, int] = {}
    # Most-constrained boss first (#246): the Titan Dweevil fits only the
    # Impact Goolix arena while the Crawbster fits two, so a Crawbster drawn
    # first must not take the Titan's only arena. The shuffle still breaks
    # ties (and a one-boss pool draws exactly as before, so its layouts are
    # unchanged).
    order = rng.shuffle(sorted(boss_pool))
    eligible = {source_id: sum(1 for token in free if token in accepted.get(source_id, set()))
                for source_id in order}
    for source_id in sorted(order, key=lambda sid: eligible[sid]):
        choices = [token for token in free if token in accepted.get(source_id, set())]
        if not choices:
            continue
        token = rng.shuffle(choices)[0]
        chosen[token] = source_id
        free.remove(token)
    bindings = []
    placed = []
    for token, source_id in sorted(chosen.items(), key=lambda item: int(item[0])):
        arena = arenas[token]
        # One binding per arena: the primary spawn uid. The arena's other
        # spawn generators (the Impact Goolix's other day files) are re-keyed
        # to the primary natively (pc_p2_boss_arena_policy.h kAlias), so the
        # boss keeps one generator token across days.
        targets = [str(arena["primary_uid"])]
        bindings += [{"target": target, "source_id": source_id,
                      "enum_name": by_source[source_id].enum_name} for target in targets]
        placed.append({"arena": arena["id"], "source_id": source_id, "targets": targets})
    info = {"version": BOSS_ARENA_VERSION, "placed": placed}
    unplaced = sorted(set(boss_pool) - set(chosen.values()))
    if unplaced:
        info["unplaced"] = unplaced
    return bindings, info


def _attach_boss_arenas(layout: dict, seed, slot, document, roster: list[RosterEntry], boss_pool) -> dict:
    if not boss_pool:
        return layout
    bindings, info = _assign_boss_arenas(seed, slot, document, roster, boss_pool)
    combined = list(layout["bindings"]) + bindings
    if len({binding["target"] for binding in combined}) != len(combined):
        raise SeedBridgeError("boss arena target collides with an ordinary P2 target")
    if len(combined) > P2_MAX_BINDINGS:
        raise SeedBridgeError(
            f"P2 layout exceeds the native {P2_MAX_BINDINGS}-binding cap "
            "(pc_randomizer.cpp kP2MaxBindings)")
    layout["bindings"] = _sort_bindings(combined)
    layout[BOSS_ARENA_KEY] = info
    return layout


def _boss_only_layout(seed, slot, document, roster: list[RosterEntry], boss_pool, policy) -> dict:
    layout = {"version": LAYOUT_VERSION, "roster_schema": ROSTER_SCHEMA,
              "roster_revision": roster_revision(roster), DENSITY_POLICY_KEY: policy,
              "bindings": []}
    layout = _attach_boss_arenas(layout, seed, slot, document, roster, boss_pool)
    if not layout["bindings"]:
        raise SeedBridgeError(f"P2 bosses have no eligible boss arena: {sorted(boss_pool)}")
    return layout


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

    The ordinary target set is the *union* of every admitted identity's
    constraint-compatible slots (#948): a water slot that only the Skitter
    Leaf can take is still a target, paired below with the identities the
    document accepts there. (Before #948 this was the intersection across the
    cohort, which silently dropped every slot any one species could not use.)
    Acceptance is enforced separately by :func:`resolve_placement_layout`.
    """
    from randomizer import p2_placement_catalog as catalog
    from randomizer.p2_placement import validate_document
    roster = roster if roster is not None else load_roster()
    admitted = admitted_ids(roster)
    if not admitted:
        raise SeedBridgeError(
            "no admitted P2 identities; refusing to seed an unadmitted pool (lane 02 admission set is empty)"
        )
    # Arena bosses (#899) never join the flat ordinary target contract.
    bosses = arena_boss_ids(document, roster) & set(admitted)
    admitted = [source_id for source_id in admitted if source_id not in bosses]
    if not admitted:
        return []
    document = validate_document(document)
    try:
        targets = catalog.binding_targets_union_for_sources(admitted, document)
    except ValueError as exc:
        raise SeedBridgeError(f"placement catalog rejected the admitted cohort: {exc}") from exc
    if not targets:
        raise SeedBridgeError("placement document has no constraint-compatible admitted target")
    return targets


def _proxy_accepted_targets(document, proxy_rows, roster: list[RosterEntry], proxy_document=None) -> dict[int, set[str]]:
    """Map each proxy source id to its accepted target tokens.

    A proxy row is accepted on every target that is accepted for at least one
    roster-admitted identity AND whose slot terrain is in the row's
    ``terrains``. Slots and terrains come from the validated placement
    document; today all committed slots are ``ground``.

    ``proxy_document`` is an optional validated stage-A sibling
    (``p2-proxy-placement-v1``): when supplied, its slot uids extend the
    audit union for proxy rows only (filtered by row terrains, minus
    ``reserved_vanilla``). Pack slots (``pack: true``) additionally require
    the row's ``host_teki`` to be in the document's ``pack_hosts`` small-host
    set, so a 2-5 member pack never multiplies a large/dangerous host.
    Six-gate identities keep exactly today's targets
    because their ``accepted`` mapping never sees the sibling. When ``None``
    (diagnostic callers) the behaviour is exactly the pre-stage-A union.
    """
    from randomizer.p2_placement import validate_document
    accepted = _accepted_placement_targets(document, roster)
    union: set[str] = set()
    for tokens in accepted.values():
        union.update(tokens)
    # A boss arena (#899) hosts only its P2 boss, never a proxy.
    union -= _boss_slot_uids(document)
    # A held-part slot (#901) is filled by its own layer, never by a proxy.
    union -= _held_part_uids(document)
    validated = validate_document(document)
    terrain_by_uid = {str(item["uid"]): item["terrain"] for item in validated["slots"]}
    reserved: set[str] = set()
    pack_uids: set[str] = set()
    pack_hosts: set[int] | None = None
    if proxy_document is not None:
        from randomizer.p2_placement import validate_proxy_document
        validated_proxy = validate_proxy_document(proxy_document)
        for item in validated_proxy["slots"]:
            terrain_by_uid.setdefault(str(item["uid"]), item["terrain"])
        union = set(union) | {str(item["uid"]) for item in validated_proxy["slots"]}
        reserved = {str(uid) for uid in validated_proxy["reserved_vanilla"]}
        pack_hosts = set(validated_proxy["pack_hosts"])
        pack_uids = {str(item["uid"]) for item in validated_proxy["slots"] if item.get("pack")}
    result: dict[int, set[str]] = {}
    for row in proxy_rows or []:
        source_id = row.get("source_id")
        terrains = row.get("terrains") or ["ground"]
        host = row.get("host_teki")
        tokens = {uid for uid in union if terrain_by_uid.get(uid) in set(terrains)} - reserved
        if pack_uids and pack_hosts is not None and host not in pack_hosts:
            tokens -= pack_uids
        result[source_id] = tokens
    return result


def _least_contended(remaining, eligible, source_id):
    """Targets ``source_id`` may take, narrowed to the ones fewest species want.

    The first pass gives every species one target. With a terrain-mixed
    target set (#948: ground, water, air and shore slots) a flexible species
    that took a ground slot could starve a ground-only species even though a
    water or air slot was free for it, so a species is steered to its least
    contended targets first (deterministic; the seed still shuffles ties).
    """
    choices = [target for target in remaining if source_id in eligible[target]]
    if not choices:
        return choices
    contention = {target: len(eligible[target]) for target in choices}
    lowest = min(contention.values())
    return [target for target in choices if contention[target] == lowest]


def resolve_placement_layout(seed, slot, document, roster: list[RosterEntry] | None = None, *,
                             species=None, density=None, proxy_rows=None, proxy_document=None) -> dict:
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

    ``proxy_rows`` (keyword-only, a list of proxy row dicts for the tier ids in
    play) switches to the :data:`DENSITY_SAMPLED` policy automatically: the
    species subset check allows roster-admitted ids plus those proxy ids, a
    proxy row is accepted on every target accepted for at least one
    roster-admitted identity whose slot terrain is in the row's ``terrains``,
    and the sampled fill below never raises. With ``proxy_rows`` empty/None
    this function is unchanged (``proxy_document`` is ignored).

    ``proxy_document`` (keyword-only, a ``p2-proxy-placement-v1`` sibling) adds
    the stage-A proxy-only slots to the proxy union and to the sampled target
    list. Six-gate identities never see it: their ``accepted`` mapping is
    untouched, so they keep byte-identical targets and layouts.
    """
    roster = roster if roster is not None else load_roster()
    roster_admitted = list(admitted_ids(roster))
    proxy_ids: list[int] = []
    if proxy_rows:
        seen_proxy: set[int] = set()
        for row in proxy_rows:
            source_id = row.get("source_id")
            if type(source_id) is not int or isinstance(source_id, bool):
                raise SeedBridgeError(f"proxy row has an invalid source id: {source_id!r}")
            if source_id in seen_proxy:
                raise SeedBridgeError(f"proxy rows contain a duplicate source id: {source_id}")
            seen_proxy.add(source_id)
            proxy_ids.append(source_id)
        if density is not None and density != DENSITY_SAMPLED:
            raise SeedBridgeError(
                f"proxy rows force the {DENSITY_SAMPLED} policy, not {density!r}")
        policy = DENSITY_SAMPLED
    else:
        policy = validate_density(density)
    if proxy_rows:
        allowed = set(roster_admitted) | set(proxy_ids)
        if species is not None:
            wanted = set(species)
            if not wanted or not wanted <= allowed:
                raise SeedBridgeError(
                    f"P2 species subset must be a nonempty subset of the admitted ids {sorted(allowed)}: {sorted(wanted)}")
            pool = ([source_id for source_id in roster_admitted if source_id in wanted]
                    + sorted(source_id for source_id in proxy_ids
                             if source_id in wanted and source_id not in set(roster_admitted)))
        else:
            pool = list(roster_admitted) + sorted(
                source_id for source_id in proxy_ids if source_id not in set(roster_admitted))
        if not pool:
            raise SeedBridgeError(
                "no admitted P2 identities; refusing to seed an unadmitted pool (lane 02 admission set is empty)"
            )
        # Only roster-admitted bosses move to the arenas; a proxy-tier stand-in
        # keeps its proxy placement.
        bosses = arena_boss_ids(document, roster) & set(roster_admitted)
        boss_pool = [source_id for source_id in pool if source_id in bosses]
        pool = [source_id for source_id in pool if source_id not in bosses]
        if not pool:
            return _boss_only_layout(seed, slot, document, roster, boss_pool, policy)
        held = _held_part_uids(document)
        targets = [target for target in binding_targets_from_placement(document, roster)
                   if target not in held]
        accepted = _accepted_placement_targets(document, roster)
        proxy_accepted = _proxy_accepted_targets(document, proxy_rows, roster,
                                                 proxy_document=proxy_document)
        if proxy_document is not None:
            from randomizer.p2_placement import validate_proxy_document
            sibling = validate_proxy_document(proxy_document)
            extra = sorted({str(item["uid"]) for item in sibling["slots"]} - set(targets),
                           key=int)
            targets = sorted(set(targets) | set(extra), key=int)
        pool_set = set(pool)
        eligible: dict[str, list[int]] = {}
        for target in targets:
            ids = sorted(source_id for source_id, tokens in accepted.items()
                         if source_id in pool_set and target in tokens)
            ids += sorted(source_id for source_id, tokens in proxy_accepted.items()
                          if source_id in pool_set and target in tokens
                          and source_id not in set(ids))
            if ids:
                eligible[target] = ids
        if not eligible:
            raise SeedBridgeError("no admitted identity has accepted placement evidence in the document")
        revision = roster_revision(roster)
        by_source = by_id(roster)
        rng = SeedRandom(f"{seed}/p2-placement-layout-v1/{slot}")
        shuffled = rng.shuffle(pool)
        playable = set(PLAYABLE_IDS)
        play_first = [source_id for source_id in shuffled if source_id in playable]
        rest = [source_id for source_id in shuffled if source_id not in playable]
        # Most-constrained species first (stable: ties keep shuffled order) so
        # host-restricted species claim the committed/singleton slots before
        # flexible small-host species take them: a stranded large species can
        # never land on a pack target, while a small one can land anywhere.
        width = {source_id: sum(1 for target in eligible if source_id in eligible[target])
                 for source_id in rest}
        rest.sort(key=lambda source_id: width[source_id])
        identity_order = play_first + rest
        remaining = sorted(eligible, key=lambda item: (len(item), item))
        assigned: dict[str, int] = {}
        for source_id in identity_order:
            choices = _least_contended(remaining, eligible, source_id)
            if not choices:
                continue
            target = rng.shuffle(choices)[0]
            assigned[target] = source_id
            remaining.remove(target)
            if not remaining:
                break
        for target in list(remaining):
            # Never waste a slot on a repeat while an eligible unplaced species
            # exists: prefer pool ids not yet covered on this target; only when
            # every eligible id is already placed (e.g. a pack target whose
            # small-host pool is exhausted) fall back to any eligible id.
            covered_so_far = set(assigned.values())
            fresh = [source_id for source_id in eligible[target]
                     if source_id not in covered_so_far]
            assigned[target] = rng.shuffle(fresh or eligible[target])[0]
        if len(assigned) > P2_MAX_BINDINGS:
            raise SeedBridgeError(
                f"P2 layout exceeds the native {P2_MAX_BINDINGS}-binding cap "
                "(pc_randomizer.cpp kP2MaxBindings)")
        covered = set(assigned.values())
        unplaced = sorted(set(pool) - covered)
        bindings = [{"target": target, "source_id": source_id,
                     "enum_name": by_source[source_id].enum_name}
                    for target, source_id in sorted(assigned.items(), key=lambda item: (len(item[0]), item[0]))]
        layout = {"version": LAYOUT_VERSION, "roster_schema": ROSTER_SCHEMA,
                  "roster_revision": revision, DENSITY_POLICY_KEY: policy,
                  "bindings": bindings}
        if unplaced:
            layout["unplaced"] = unplaced
        held_pool = [source_id for source_id in pool if source_id in set(roster_admitted)]
        return _finish_layout(layout, seed, slot, document, roster, held_pool, boss_pool)
    admitted = list(roster_admitted)
    if species is not None:
        wanted = set(species)
        if not wanted or not wanted <= set(admitted):
            raise SeedBridgeError(f"P2 species subset must be a nonempty subset of the admitted ids {sorted(admitted)}: {sorted(wanted)}")
        admitted = [source_id for source_id in admitted if source_id in wanted]
    if not admitted:
        raise SeedBridgeError(
            "no admitted P2 identities; refusing to seed an unadmitted pool (lane 02 admission set is empty)"
        )
    bosses = arena_boss_ids(document, roster)
    boss_pool = [source_id for source_id in admitted if source_id in bosses]
    admitted = [source_id for source_id in admitted if source_id not in bosses]
    if not admitted:
        return _boss_only_layout(seed, slot, document, roster, boss_pool, policy)
    held = _held_part_uids(document)
    targets = [target for target in binding_targets_from_placement(document, roster) if target not in held]
    accepted = _accepted_placement_targets(document, roster)
    admitted_set = set(admitted)
    eligible = {}
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
    # #893 (owner decision 2026-09-28): a pool with more species than eligible
    # targets cannot give every species a unique target. Under the default
    # density the seed then samples the pool (sampled-v1): each target gets a
    # distinct species and the species that did not fit are recorded as
    # ``unplaced``. A pool that fits keeps the legacy fill byte-for-byte, and
    # Explicit sampling uses the same path; explicit all-target/bounded policies
    # retain their complete-coverage requirement below.
    sampled = policy == DENSITY_SAMPLED or (density is None and len(admitted) > len(eligible))
    if sampled:
        policy = DENSITY_SAMPLED

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
    assigned = {}
    for source_id in identity_order:
        choices = _least_contended(remaining, eligible, source_id)
        if not choices:
            continue
        target = rng.shuffle(choices)[0]
        assigned[target] = source_id
        remaining.remove(target)
    if policy == DENSITY_LEGACY:
        for target in remaining:
            assigned[target] = rng.shuffle(eligible[target])[0]
    if sampled:
        # A target is left over only when every species it accepts already
        # holds another target (the loop above gives each species with a free
        # choice one), so it repeats an eligible species as the legacy fill does.
        for target in remaining:
            assigned[target] = rng.shuffle(eligible[target])[0]
        bindings = [{"target": target, "source_id": source_id,
                     "enum_name": by_source[source_id].enum_name}
                    for target, source_id in sorted(assigned.items(), key=lambda item: (len(item[0]), item[0]))]
        layout = {"version": LAYOUT_VERSION, "roster_schema": ROSTER_SCHEMA,
                  "roster_revision": revision, DENSITY_POLICY_KEY: policy,
                  "bindings": bindings}
        unplaced = sorted(set(admitted) - set(assigned.values()))
        if unplaced:
            layout["unplaced"] = unplaced
        return _finish_layout(layout, seed, slot, document, roster, admitted, boss_pool)
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
    layout = {"version": LAYOUT_VERSION, "roster_schema": ROSTER_SCHEMA,
              "roster_revision": revision, DENSITY_POLICY_KEY: policy,
              "bindings": bindings}
    return _finish_layout(layout, seed, slot, document, roster, admitted, boss_pool)


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
    policy = _layout_density(layout)
    unplaced = layout.get("unplaced")
    if unplaced is not None:
        if policy != DENSITY_SAMPLED:
            raise SeedBridgeError("P2 layout unplaced list requires the sampled-v1 density policy")
        if (not isinstance(unplaced, list)
                or any(type(source_id) is not int or isinstance(source_id, bool)
                       for source_id in unplaced)
                or len(set(unplaced)) != len(unplaced)
                or unplaced != sorted(unplaced)):
            raise SeedBridgeError(f"invalid P2 layout unplaced list: {unplaced!r}")
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
    if unplaced is not None:
        # A holder slot (#901) prefers a species the ordinary fill left unplaced
        # (#893); that binding does not un-sample the species from the fill.
        held_targets = {row.get("target") for row in
                        (layout.get(HELD_PART_KEY) or {}).get("placed", []) if isinstance(row, dict)}
        overlap = sorted(set(unplaced) & {binding["source_id"] for binding in bindings
                                          if binding.get("target") not in held_targets})
        if overlap:
            raise SeedBridgeError(f"P2 layout unplaced ids overlap bound ids: {overlap}")
    arena_block = layout.get(BOSS_ARENA_KEY)
    if arena_block is not None:
        by_target = {binding["target"]: binding["source_id"] for binding in bindings}
        if not isinstance(arena_block, dict) or arena_block.get("version") != BOSS_ARENA_VERSION:
            raise SeedBridgeError(f"unsupported P2 boss arena block: {arena_block!r}")
        placed = arena_block.get("placed")
        if not isinstance(placed, list):
            raise SeedBridgeError("P2 boss arena block has no placed list")
        for row in placed:
            targets = row.get("targets") if isinstance(row, dict) else None
            if (not isinstance(targets, list) or not targets
                    or any(by_target.get(target) != row.get("source_id") for target in targets)):
                raise SeedBridgeError(f"P2 boss arena row does not match the bindings: {row!r}")
        arena_unplaced = arena_block.get("unplaced", [])
        if (not isinstance(arena_unplaced, list)
                or set(arena_unplaced) & {row["source_id"] for row in placed}):
            raise SeedBridgeError(f"invalid P2 boss arena unplaced list: {arena_unplaced!r}")
    held_block = layout.get(HELD_PART_KEY)
    if held_block is not None:
        by_target = {binding["target"]: binding["source_id"] for binding in bindings}
        if not isinstance(held_block, dict) or held_block.get("version") != HELD_PART_VERSION:
            raise SeedBridgeError(f"unsupported P2 held-part block: {held_block!r}")
        held_placed = held_block.get("placed")
        if not isinstance(held_placed, list) or not held_placed:
            raise SeedBridgeError("P2 held-part block has no placed list")
        for row in held_placed:
            if not isinstance(row, dict) or by_target.get(row.get("target")) != row.get("source_id"):
                raise SeedBridgeError(f"P2 held-part row does not match the bindings: {row!r}")
    if admitted is not None:
        allowed = set(admitted)
        unadmitted = sorted({binding["source_id"] for binding in bindings if binding["source_id"] not in allowed})
        if unadmitted:
            raise SeedBridgeError(f"P2 layout binds unadmitted source ids: {unadmitted}")


def build_bootstrap(layout: dict, roster: list[RosterEntry] | None = None, *,
                    proxy_tier=None) -> str:
    """Emit the native bootstrap line, or empty string when no P2 layout is present.

    When the seed manifest carries ``p2_proxy_tier`` (``proxy_tier`` not None,
    or the layout itself carries a truthy ``p2_proxy_tier`` key from a prior
    :func:`parse_bootstrap`), a second ``P2_PROXY_TIER 1`` line follows the
    ``ENEMY_P2`` line so the native adapter can echo ``p2-proxy-tier-v1`` in
    the hello. The wire version is always 1; the tier name lives in the
    manifest, not on the wire. Legacy layouts (no tier) emit byte-for-byte
    what they always did.
    """
    if not layout:
        return ""
    validate_layout(layout, roster)
    parts = [PROTOCOL_HEADER, str(PROTOCOL_VERSION), layout["roster_revision"], str(len(layout["bindings"]))]
    for binding in layout["bindings"]:
        parts += [binding["target"], str(binding["source_id"])]
    text = " ".join(parts) + "\n"
    tier = proxy_tier if proxy_tier is not None else layout.get("p2_proxy_tier")
    if tier is not None:
        text += "P2_PROXY_TIER 1\n"
    return text


def parse_bootstrap(text: str, roster: list[RosterEntry] | None = None, *,
                    density=None) -> dict:
    """Parse a native ``ENEMY_P2`` line back into a layout; rejects malformed input.

    The wire format carries only the bindings, so the density policy is not on
    the line. ``density`` lets a caller reconstruct the policy the manifest
    stored; it defaults to the legacy all-target fill.

    An optional trailing ``P2_PROXY_TIER 1`` pair (same line or next line) is
    accepted and round-trips as a truthy ``layout["p2_proxy_tier"]`` key; any
    other value fails closed. Layouts without the pair carry no such key, so
    legacy ``parse(build(layout)) == layout`` is unchanged.
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
    proxy_tier = None
    if "P2_PROXY_TIER" in body:
        if len(body) != count * 2 + 2 or body[-2] != "P2_PROXY_TIER" or body[-1] != "1":
            raise SeedBridgeError(f"invalid P2 proxy tier pair: {body[count * 2:]!r}")
        proxy_tier = True
        body = body[:-2]
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
    if proxy_tier is not None:
        layout["p2_proxy_tier"] = True
    validate_layout(layout, roster)
    return layout


def bootstrap_for_manifest(manifest: dict, roster: list[RosterEntry] | None = None) -> str:
    """Return the ENEMY_P2 block for a manifest, or '' for legacy seeds.

    Manifests carrying ``p2_proxy_tier`` gain a trailing ``P2_PROXY_TIER 1``
    line after the ``ENEMY_P2`` line (before the runner's ``END``) so the
    native hello can echo ``p2-proxy-tier-v1`` in manifest capability order;
    an old binary that never emits the token then fails the exact hello
    comparison instead of silently showing plain Pikmin 1 hosts.
    """
    if not isinstance(manifest, dict) or not manifest.get("p2_layout"):
        return build_bootstrap(manifest.get("p2_layout") if isinstance(manifest, dict) else None, roster)
    return build_bootstrap(manifest.get("p2_layout"), roster,
                           proxy_tier=manifest.get("p2_proxy_tier"))
