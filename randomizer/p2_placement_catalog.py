"""Concrete lane-04 candidate slots and P2 placement profiles.

This is the concrete-placement companion to :mod:`randomizer.p2_placement`. It
turns the real slot tables the game already uses into `p2-placement-v1` slot
records and pairs them with placement profiles for the P2 candidate cohort
(fan-out lanes 13, 14, 16, 19, 22 and 30).

Nothing here admits an identity. Every profile ships with empty
``accepted_gates``, so :func:`randomizer.p2_placement.evaluate` still denies the
pair; :func:`randomizer.p2_placement.compatibility_report` shows which concrete
slots are constraint-compatible and which are rejected outright.

Sources of truth:

- ``randomizer.campaign_data.CAMPAIGN_SLOTS`` / ``CAMPAIGN_SOURCES``: the
  production campaign generators with extracted native XYZ positions, per-day
  schedule and the source ``protected`` flag (personality pellet / Parameter0).
- ``randomizer.spawn_data.ADULT_SLOTS`` / ``GROUP_SLOTS`` / ``GENERATOR_SLOTS``:
  the raw P1 generator inventory (adult, group and the full teki/boss table).
- ``docs/PIKMIN2_ENEMY_ROSTER.json`` (lane 02): the canonical P2 ``source_id``,
  enum name and drop type this module keys candidate profiles on.

Terrain classes are derived from the campaign cohort, not from a native terrain
probe, so slot ``evidence.terrain`` and ``evidence.route`` stay false and the
top-level placement gate stays denied until a family lane or QA supplies them.
"""
import argparse
import json
import sys
from pathlib import Path

from .campaign_data import CAMPAIGN_SLOTS, CAMPAIGN_SOURCES
from .spawn_data import ADULT_SLOTS, GROUP_SLOTS, GENERATOR_SLOTS
from . import p2_placement as _placement

SCHEMA = _placement.SCHEMA
ENCOUNTER_SCHEMA = _placement.ENCOUNTER_SCHEMA
DEFAULT_RADIUS = 100.0

# Campaign cohort -> slot terrain class. `frog` is amphibious shore/water,
# `aquatic` is submerged, `flying` is air; the rest are open ground.
COHORT_TERRAIN = {
    'ground': 'ground',
    'dwarf': 'ground',
    'grub': 'ground',
    'frog': 'mixed',
    'aquatic': 'water',
    'flying': 'air',
}

# terrain class -> slot capability defaults used by the lane-04 adapters.
GROUND_TERRAINS = ('ground', 'mixed')
# Blue Pikmin can carry a corpse back through water, so submerged slots also
# expose a corpse return route; only airborne slots do not.
CORPSE_TERRAINS = ('ground', 'mixed', 'water')

# Lane 02 source_id -> candidate placement profile for the initial cohort.
# `p1_equivalent` is the P1 catalog id whose campaign pool already routes to
# the same behavior; None means no equivalent pool exists yet.
# Fields: source_id, identity, lane, terrains, p1_equivalent.
# P1 catalog id -> production campaign cohort. A candidate that maps to a P1
# equivalent inherits that cohort so it cannot occupy a foreign placement class
# (e.g. a Sheargrub identity may not fill an aquatic slot) even when the terrain
# class would otherwise match.
P1_COHORT = {
    3: 'dwarf', 31: 'dwarf',
    18: 'grub', 19: 'grub', 20: 'grub',
    4: 'ground', 15: 'ground', 17: 'ground', 24: 'ground', 32: 'ground',
    11: 'flying', 16: 'flying',
    25: 'aquatic', 30: 'aquatic',
    0: 'frog', 33: 'frog',
}

# `requires_home` is source-backed by the lane-02 roster child reference: a
# non-null `child_name` of PanHouse/JigumoNest means the identity is anchored to
# a nest, not a free spawn. Only Jigumo (Hermit Crawmad) qualifies in this cohort.
# Every cohort entry drops a carryable corpse (BDT_Weak..BDT_Strong), so all of
# them require a corpse return route.
CANDIDATE_SPECS = (
    # Lane 13 - Bulborbs, dwarfs and Sheargrubs.
    (1, 'Kochappy', 13, ['ground'], 3, False),
    (2, 'Chappy', 13, ['ground'], 4, False),
    (12, 'UjiA', 13, ['ground'], 18, False),
    (13, 'UjiB', 13, ['ground'], 19, False),
    (14, 'Tobi', 13, ['ground'], 20, False),
    (33, 'FireChappy', 13, ['ground'], None, False),
    (35, 'KumaChappy', 13, ['ground'], 32, False),
    (42, 'BlueChappy', 13, ['ground'], None, False),
    (43, 'YellowChappy', 13, ['ground'], None, False),
    (44, 'BlueKochappy', 13, ['ground'], None, False),
    (45, 'YellowKochappy', 13, ['ground'], None, False),
    (76, 'KumaKochappy', 13, ['ground'], 31, False),
    # Lane 14 - Ground invertebrates.
    (15, 'Armor', 14, ['ground'], None, False),
    (28, 'ElecBug', 14, ['ground'], None, False),
    (65, 'Imomushi', 14, ['ground'], None, False),
    (68, 'TamagoMushi', 14, ['ground'], None, False),
    (79, 'Sokkuri', 14, ['ground'], None, False),
    (84, 'Hana', 14, ['ground'], None, False),
    # Lane 16 - Frogs and aquatic enemies (bosses excluded; see BOSS_COHORT).
    (17, 'Frog', 16, ['mixed', 'ground'], 0, False),
    (18, 'MaroFrog', 16, ['mixed', 'ground'], 33, False),
    (26, 'Catfish', 16, ['water'], 30, False),
    (27, 'Tadpole', 16, ['water'], 25, False),
    (63, 'Jigumo', 16, ['water'], None, True),
    # Lane 19 - Mamuta.
    (54, 'Miulin', 19, ['ground'], 24, False),
    # Lane 22 - elemental Otakara Dweevils (source ids 59-62). The port binds
    # each to a generated ground slot (lane-22 arena generator=349001).
    (59, 'FireOtakara', 22, ['ground'], None, False),
    (60, 'WaterOtakara', 22, ['ground'], None, False),
    (61, 'GasOtakara', 22, ['ground'], None, False),
    (62, 'ElecOtakara', 22, ['ground'], None, False),
    # Lane 30 - Sarai (Swooping Snitchbug). The port binds it to a generated
    # ground slot (lane-30 arena generator=385875968); no P1 equivalent pool.
    (23, 'Sarai', 30, ['ground'], None, False),
)

# Lane-14 ground-invertebrate source facts (docs/PIKMIN2_GROUND_PLACEMENT_FACTS.md,
# docs/p2_ground_placement_facts.json). These are the terrain/space/water/home/
# helper facts only; lane 04 keeps identity, cohort, family_lane, notes and
# accepted_gates, so no entry here sets a cohort. `footprint_radius` is the
# source root collision sphere and `helper_budget` is the manager group cap
# (TamagoMushi: 10 surface / 30 cave; a 0-capacity slot cannot host the group).
GROUND_INVERT_FACTS = {
    'Armor': {
        'terrains': ['ground'], 'footprint_radius': 40, 'min_water_depth': 0,
        'requires_burrow_ground': True, 'requires_home': False,
        'helper_budget': 0, 'requires_corpse_route': True,
    },
    'ElecBug': {
        'terrains': ['ground'], 'footprint_radius': 32.5, 'min_water_depth': 0,
        'requires_burrow_ground': False, 'requires_home': False,
        'helper_budget': 0, 'requires_corpse_route': True,
    },
    'Imomushi': {
        'terrains': ['ground'], 'footprint_radius': 17.5, 'min_water_depth': 0,
        'requires_burrow_ground': True, 'requires_home': False,
        'helper_budget': 0, 'requires_corpse_route': True,
    },
    'TamagoMushi': {
        'terrains': ['ground', 'underground'], 'footprint_radius': 18, 'min_water_depth': 0,
        'requires_burrow_ground': True, 'requires_home': False,
        'helper_budget': 10, 'requires_corpse_route': True,
    },
    'Sokkuri': {
        'terrains': ['ground', 'mixed', 'water'], 'footprint_radius': 25, 'min_water_depth': 0,
        'requires_burrow_ground': False, 'requires_home': False,
        'helper_budget': 0, 'requires_corpse_route': True,
    },
    'Hana': {
        'terrains': ['ground'], 'footprint_radius': 75, 'min_water_depth': 0,
        'requires_burrow_ground': True, 'requires_home': False,
        'helper_budget': 0, 'requires_corpse_route': True,
    },
}

# Muse placement slice (#492): candidate-only legal-slot profiles for
# Fuefuki41, Kurage57, BombSarai58 and MiniHoudai78.
#
# Each entry carries exactly one defensible generated slot (`accepted_slot_uid`)
# plus the P1 placement vehicle the family sidecar binds. Profiles ship with
# empty `accepted_gates`, so `evaluate` still denies every pair until a family
# lane or QA supplies accepted native terrain/route evidence; `compatibility`
# (constraint-only) already resolves the accepted slot. Nothing here admits an
# identity or touches ordinary random pools.
# Fields: source_id, identity, legacy_lane, muse_lane, terrains,
# accepted_slot_uid, vehicle.
MUSE_CANDIDATE_SPECS = (
    # Antenna Beetle: ground follower on the Napkid11 vehicle (lane-28 pattern,
    # cf. Sarai ground profile). Hope ground slot, renewable, corpse route.
    (41, 'Fuefuki', 28, 57, ['ground'], 1254096625, 'Napkid11'),
    # Lesser Spotted Jellyfloat: grounded Frog0 body vehicle (lane-29 sidecar
    # `p2-kurage-teki.txt` grounds the proxy), so frog-cohort mixed slot.
    # Navel mixed slot, renewable, corpse route.
    (57, 'Kurage', 29, 58, ['mixed', 'ground'], 689702860, 'Frog0'),
    # Careening Dirigibug: Napkid11 carrier vehicle (lane-27 sidecar
    # `p2-bombsarai-teki.txt`); the 13-state carrier FSM drives from the
    # vehicle position with hover above a ground slot. Spring ground slot,
    # renewable, corpse route. The two Bomb payloads are family-internal and
    # are not slot helpers (helper_budget stays 0).
    (58, 'BombSarai', 27, 59, ['ground'], 1787125272, 'Napkid11'),
    # Gatling Groink: live generated host actor with carcass sidecar (lane-21
    # `p2-groink-teki.txt`); ground shooter, volley corridor is a family-run
    # gate, not a placement constraint. Navel ground slot, renewable, corpse
    # route.
    (78, 'MiniHoudai', 21, 60, ['ground'], 328297937, 'GroinkHost'),
)

# Native generated-placement bind contract mirror. The dispatcher in
# `native/pc_port/pc_p2_generated_placement.{h,cpp}` carries the same
# (source_id -> accepted slot uid) table as `MUSE_GENERATED_SLOT_UID`
# constants; `tests/test_pikmin2_muse_placement.py` fails if the two drift.
MUSE_GENERATED_SLOTS = {
    source_id: slot_uid for source_id, _, _, _, _, slot_uid, _ in MUSE_CANDIDATE_SPECS
}

MUSE_CANDIDATE_IDS = frozenset(MUSE_GENERATED_SLOTS)

# Candidate source_ids that are bosses and therefore require a lane-04 encounter
# descriptor instead of a universal replacement profile. Tracked here so the
# cohort is complete without silently admitting them.
BOSS_COHORT = (
    (71, 'UmiMushi', 16, ['water']),
    (101, 'UmiMushiBlind', 16, ['water']),
)

# Encounter descriptors for the lane-16 aquatic bosses. A boss may only be
# placed through one of these, and the campaign table contains no boss arena
# slot, so a caller must supply boss slots explicitly. `footprint_radius` is 0
# because no source arena size is extracted yet; `required_gates` are
# requirements, not native proof.
ENCOUNTER_SPECS = (
    {
        'id': 'umi_mushi_arena', 'identity': 'UmiMushi', 'source_id': 71, 'lane': 16,
        'terrains': ['water'], 'helper_budget': 0, 'arena_slots': {'min': 1, 'max': 1},
        'phases': 1, 'protected_drops': [],
        'required_gates': ['arena', 'attack', 'suction', 'death', 'reward'],
        'notes': 'Ranging Bloyster arena; no helper spawns; footprint unmeasured.',
    },
    {
        'id': 'umi_mushi_blind_arena', 'identity': 'UmiMushiBlind', 'source_id': 101, 'lane': 16,
        'terrains': ['water'], 'helper_budget': 0, 'arena_slots': {'min': 1, 'max': 1},
        'phases': 1, 'protected_drops': [],
        'required_gates': ['arena', 'attack', 'suction', 'death', 'reward'],
        'notes': 'Toady Bloyster arena; no helper spawns; footprint unmeasured.',
    },
)


def _campaign_index(campaign_sources):
    index = {}
    for row in campaign_sources:
        index[row['uid']] = row
    return index


def slots_from_campaign(campaign_slots=CAMPAIGN_SLOTS, campaign_sources=CAMPAIGN_SOURCES):
    """Adapt production campaign generators into default-deny slot records."""
    sources = _campaign_index(campaign_sources)
    slots = []
    for row in campaign_slots:
        cohort = row['cohort']
        terrain = COHORT_TERRAIN[cohort]
        source = sources.get(row['uid'], {})
        position = row.get('position')
        slots.append({
            'uid': row['uid'],
            'label': row['label'],
            'stage': row['stage'],
            'terrain': terrain,
            'radius': DEFAULT_RADIUS,
            'flight_space': terrain == 'air',
            'burrow_ground': terrain in GROUND_TERRAINS,
            'corpse_route': terrain in CORPSE_TERRAINS,
            'protected': bool(source.get('protected', False)),
            'first_day': row.get('first_day', 1),
            'respawn_days': row.get('respawn_days', 0),
            'source_identity': f"campaign:{cohort}:{row.get('original')}",
            'cohort': cohort,
            'evidence': {'xyz': bool(position), 'terrain': False, 'route': False},
        })
    return slots


def _merge_unique(primary, secondary):
    merged = {}
    for record in primary:
        merged[record['uid']] = record
    for record in secondary:
        merged.setdefault(record['uid'], record)
    return [merged[uid] for uid in sorted(merged)]


def _slot_from_legacy_row(row, terrain, source_identity, evidence):
    radius = DEFAULT_RADIUS
    return {
        'uid': row['uid'],
        'label': row.get('label', str(row['uid'])),
        'stage': row.get('stage', 0),
        'terrain': terrain,
        'radius': radius,
        'flight_space': terrain == 'air',
        'burrow_ground': terrain in GROUND_TERRAINS,
        'corpse_route': terrain in CORPSE_TERRAINS,
        'first_day': row.get('first_day', 1),
        'respawn_days': row.get('respawn_days', 0),
        'source_identity': source_identity,
        'evidence': dict(evidence),
    }


def _hex_to_float(value):
    import struct
    try:
        return struct.unpack('>f', bytes.fromhex(value))[0]
    except (ValueError, TypeError):
        return DEFAULT_RADIUS


def slots_from_adult_group(adult_slots=ADULT_SLOTS, group_slots=GROUP_SLOTS):
    """Adapt the raw adult/group generator rows into default-deny slots."""
    slots = []
    for row in adult_slots:
        slots.append(_slot_from_legacy_row(
            row, 'ground', f"adult:{row.get('original')}",
            {'xyz': bool(row.get('position')), 'terrain': False, 'route': False}))
    for row in group_slots:
        record = _slot_from_legacy_row(
            row, 'ground', f"group:{row.get('original')}",
            {'xyz': bool(row.get('position')), 'terrain': False, 'route': False})
        record['radius'] = _hex_to_float(row.get('radius_hex'))
        slots.append(record)
    return slots


def slots_from_generators(generator_slots=GENERATOR_SLOTS):
    """Adapt generator-only rows; these carry a file offset but no XYZ yet."""
    slots = []
    for uid, stage, name, offset, kind, original in generator_slots:
        slots.append({
            'uid': uid,
            'label': f"generator_{name}_{offset}",
            'stage': stage,
            'terrain': 'mixed',
            'radius': DEFAULT_RADIUS,
            'flight_space': False,
            'burrow_ground': False,
            'corpse_route': False,
            'boss_slot': kind == 'boss',
            'first_day': 1,
            'respawn_days': 0,
            'source_identity': f"generator:{kind}:{original}",
            'evidence': {'xyz': False, 'terrain': False, 'route': False},
        })
    return slots


def all_slots(campaign_slots=CAMPAIGN_SLOTS, campaign_sources=CAMPAIGN_SOURCES,
              adult_slots=ADULT_SLOTS, group_slots=GROUP_SLOTS, generator_slots=GENERATOR_SLOTS,
              include_generators=False):
    """Return the merged concrete slot inventory across every real table.

    Generator-only rows are excluded by default: they carry a file offset but no
    extracted XYZ or terrain, so their terrain cannot be classified and they
    would spuriously match every open-terrain profile. Pass
    ``include_generators=True`` to inspect the raw inventory, but keep it out of
    admission decisions until terrain evidence exists.
    """
    campaign = slots_from_campaign(campaign_slots, campaign_sources)
    legacy = slots_from_adult_group(adult_slots, group_slots)
    merged = _merge_unique(campaign, legacy)
    if include_generators:
        merged = _merge_unique(merged, slots_from_generators(generator_slots))
    return merged


def candidate_profiles():
    """Return default-deny placement profiles for the non-boss candidate cohort."""
    profiles = []
    for source_id, identity, lane, terrains, p1_equivalent, requires_home in CANDIDATE_SPECS:
        equivalent = 'none' if p1_equivalent is None else str(p1_equivalent)
        cohort = P1_COHORT.get(p1_equivalent)
        facts = GROUND_INVERT_FACTS.get(identity, {})
        record = {
            'identity': identity,
            'terrains': list(facts.get('terrains', terrains)),
            'family_lane': lane,
            'cohort': cohort,
            'requires_home': facts.get('requires_home', requires_home),
            'requires_corpse_route': facts.get('requires_corpse_route', True),
            'accepted_gates': [],
            'notes': (f"P2 source_id {source_id}; lane-04 constraint seed; "
                      f"p1_equivalent {equivalent}; placement cohort {cohort}; "
                      f"requires_home {facts.get('requires_home', requires_home)}; "
                      f"native placement gate pending family lane {lane}."),
        }
        for key in ('footprint_radius', 'min_water_depth', 'requires_burrow_ground', 'helper_budget'):
            if key in facts:
                record[key] = facts[key]
        profiles.append(_placement.normalize_profile(record))
    return profiles


def boss_encounters():
    """Return validated encounter descriptors for the lane-16 aquatic bosses."""
    return [_placement.normalize_encounter_descriptor({
        'id': spec['id'],
        'identity': spec['identity'],
        'terrains': list(spec['terrains']),
        'footprint_radius': 0,
        'helper_budget': spec['helper_budget'],
        'arena_slots': dict(spec['arena_slots']),
        'phases': spec['phases'],
        'protected_drops': list(spec['protected_drops']),
        'required_gates': list(spec['required_gates']),
        'notes': spec['notes'],
    }) for spec in ENCOUNTER_SPECS]


def boss_profiles():
    """Return default-deny boss profiles bound to the encounter descriptors.

    These are only meaningful against caller-supplied boss arena slots; the
    campaign table exposes none, so `build_document()` excludes them by default.
    """
    profiles = []
    for spec in ENCOUNTER_SPECS:
        profiles.append(_placement.normalize_profile({
            'identity': spec['identity'],
            'terrains': list(spec['terrains']),
            'family_lane': spec['lane'],
            'is_boss': True,
            'encounter_descriptor': spec['id'],
            'accepted_gates': [],
            'notes': (f"P2 source_id {spec['source_id']}; lane-04 boss constraint; "
                      f"requires encounter descriptor {spec['id']}; arena slot "
                      f"not present in the campaign table."),
        }))
    return profiles


def candidate_source_ids():
    """Map lane-04 candidate identities to their lane-02 source ids."""
    mapping = {identity: source_id for source_id, identity, *_ in CANDIDATE_SPECS}
    mapping.update({identity: source_id for source_id, identity, *_ in BOSS_COHORT})
    return mapping


def muse_candidate_profiles():
    """Return default-deny placement profiles for the #492 muse cohort.

    One profile per identity, each naming its single defensible generated
    slot via `accepted_slot_uids`. `accepted_gates` stays empty so `evaluate`
    denies every pair (fail closed) until accepted native evidence lands;
    `compatibility` already accepts the named slot on constraints alone.
    """
    profiles = []
    for (source_id, identity, legacy_lane, muse_lane, terrains, slot_uid,
            vehicle) in MUSE_CANDIDATE_SPECS:
        profiles.append(_placement.normalize_profile({
            'identity': identity,
            'terrains': list(terrains),
            'family_lane': legacy_lane,
            'requires_corpse_route': True,
            'accepted_gates': [],
            'accepted_slot_uids': [slot_uid],
            'notes': (f"P2 source_id {source_id}; muse placement slice #492; "
                      f"legacy lane {legacy_lane} / muse observer lane {muse_lane}; "
                      f"vehicle {vehicle}; accepted generated slot {slot_uid}; "
                      f"native placement gate pending family lane {legacy_lane}."),
        }))
    return profiles


def muse_candidate_source_ids():
    """Map muse-cohort identities to their lane-02 source ids."""
    return {identity: source_id
            for source_id, identity, *_ in MUSE_CANDIDATE_SPECS}


def build_muse_document(slots=None, include_bosses=False):
    """Return a validated document with base + muse-cohort profiles.

    The default `build_document()` is unchanged (pinned lane-04 contract);
    this parallel document is what packaging (#493) and the four gate
    observers (#497-#500) consume for the 41/57/58/78 cohort.
    """
    if slots is None:
        slots = all_slots()
    profiles = candidate_profiles() + muse_candidate_profiles()
    document = {
        'schema': SCHEMA,
        'slots': list(slots),
        'profiles': profiles,
        'notes': ('Lane-04 concrete candidate slots plus muse #492 candidate-only '
                  'profiles for 41/57/58/78; default deny.'),
    }
    if include_bosses:
        document['profiles'] = profiles + boss_profiles()
        document['encounters'] = boss_encounters()
    return _placement.validate_document(document)


def binding_targets_for_muse_sources(source_ids, document=None):
    """Return constraint-compatible uid targets for a muse-cohort source list."""
    if document is None:
        document = build_muse_document()
    by_source = {source_id: identity
                 for identity, source_id in muse_candidate_source_ids().items()}
    identities = []
    for source_id in source_ids:
        identity = by_source.get(source_id)
        if identity is None:
            raise ValueError(f'source id {source_id} is not a muse #492 candidate')
        identities.append(identity)
    return binding_targets(identities, document=document)


def targets_by_identity(document=None):
    """Return constraint-compatible slot targets per identity as uid tokens.

    A target token is the slot's integer `uid` rendered as a string, matching the
    existing native `ENEMY_CAMPAIGN` generator keying. Lane 03 consumes these
    tokens as its flat binding-target list.
    """
    document = document if document is not None else build_document()
    encounters = {encounter['id']: encounter for encounter in document['encounters']}
    result = {}
    for profile in document['profiles']:
        targets = [str(slot['uid']) for slot in document['slots']
                   if not _placement.compatibility(slot, profile, encounters)]
        result[profile['identity']] = sorted(targets, key=int)
    return result


def binding_targets(identities, document=None, targets=None):
    """Return constraint-compatible uid targets for *every* identity in `identities`.

    This does not enforce accepted placement evidence.
    Because lane 03 binds a flat target list to a cohort, a target is compatible
    when every cohort member accepts it: this is the intersection of the members'
    compatible targets. An empty result means the cohort is not homogeneous enough
    for the flat contract and needs per-identity targets instead.
    """
    by_identity = targets if targets is not None else targets_by_identity(document)
    names = list(identities)
    if not names:
        raise ValueError('cohort is empty')
    unknown = [name for name in names if name not in by_identity]
    if unknown:
        raise ValueError(f'unknown candidate identities: {", ".join(unknown)}')
    common = set.intersection(*(set(by_identity[name]) for name in names))
    return sorted(common, key=int)


def binding_targets_for_sources(source_ids, document=None):
    """Return binding targets for a lane-02 source-id cohort (non-boss).

    Accepts both lane-04 candidates and the muse #492 candidate cohort
    (41/57/58/78). A cohort that contains any muse candidate is evaluated
    against the base+muse document, because the default lane-04 document does
    not carry the muse profiles; a lane-04-only cohort keeps the caller's
    document (or the default lane-04 document) unchanged.
    """
    lane04 = {source_id: identity for identity, source_id in candidate_source_ids().items()}
    muse = {source_id: identity for identity, source_id in muse_candidate_source_ids().items()}
    uses_muse = any(source_id in MUSE_CANDIDATE_IDS for source_id in source_ids)
    if uses_muse:
        # Constraint targets only; the caller's document still supplies the
        # accepted placement evidence checked later by resolve_placement_layout.
        document = build_muse_document()
    elif document is None:
        document = build_document()
    identities = []
    for source_id in source_ids:
        identity = lane04.get(source_id) or muse.get(source_id)
        if identity is None or (identity not in {name for _, name, *_ in CANDIDATE_SPECS}
                                and source_id not in MUSE_CANDIDATE_IDS):
            raise ValueError(
                f'source id {source_id} is not a non-boss lane-04 or muse #492 candidate')
        identities.append(identity)
    return binding_targets(identities, document=document)


def binding_target_groups(document=None):
    """Group candidate identities by placement cohort and intersect their targets."""
    document = document if document is not None else build_document()
    by_identity = targets_by_identity(document)
    groups = {}
    for profile in document['profiles']:
        groups.setdefault(profile['cohort'] or 'open', []).append(profile['identity'])
    report = {}
    for key, identities in groups.items():
        report[key] = {
            'identities': sorted(identities),
            'targets': binding_targets(identities, targets=by_identity),
        }
    return {'by_identity': by_identity, 'groups': report, 'source_ids': candidate_source_ids()}


def build_document(slots=None, profiles=None, include_bosses=False):
    """Return a validated `p2-placement-v1` document for the candidate cohort.

    ``include_bosses`` adds the lane-16 boss profiles and their encounter
    descriptors. Only pass it with caller-supplied boss arena slots; the default
    campaign slots are not boss arenas.
    """
    if slots is None:
        slots = all_slots()
    if profiles is None:
        profiles = candidate_profiles()
    document = {
        'schema': SCHEMA,
        'slots': list(slots),
        'profiles': list(profiles),
        'notes': 'Lane-04 concrete candidate slots (campaign + adult/group) and P2 candidate profiles; default deny.',
    }
    if include_bosses:
        document['profiles'] = list(profiles) + boss_profiles()
        document['encounters'] = boss_encounters()
    return _placement.validate_document(document)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--document', type=Path, default=None,
                        help='write the built placement document JSON to this path')
    parser.add_argument('--summary', action='store_true', help='print per-identity compatibility counts')
    parser.add_argument('--report', type=Path, default=None,
                        help='write the compatibility report JSON to this path')
    parser.add_argument('--boss-descriptors', action='store_true',
                        help='print the lane-16 boss encounter descriptors and exit')
    parser.add_argument('--targets', action='store_true',
                        help='print lane-03 binding targets per identity and placement cohort')
    args = parser.parse_args(argv)

    if args.boss_descriptors:
        print(json.dumps(boss_encounters(), indent=2))
        return 0
    if args.targets:
        print(json.dumps(binding_target_groups(), indent=2))
        return 0

    document = build_document()
    report = _placement.compatibility_report(document)
    if args.document:
        args.document.write_text(json.dumps(document, indent=2))
    if args.report:
        args.report.write_text(json.dumps(report, indent=2))
    if args.summary:
        summary = {
            'schema': report['schema'],
            'encounter_schema': ENCOUNTER_SCHEMA,
            'slots': report['slots_evaluated'],
            'identities': report['identities_evaluated'],
            'compatible': {
                identity: row['compatible_slots']
                for identity, row in report['identity_compatibility'].items()
            },
            'unplaceable_identities': report['unplaceable_identities'],
            'boss_cohort': [{'source_id': sid, 'identity': name, 'lane': lane, 'terrains': terrains}
                            for sid, name, lane, terrains in BOSS_COHORT],
        }
        print(json.dumps(summary, indent=2))
    elif not args.document and not args.report:
        print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
