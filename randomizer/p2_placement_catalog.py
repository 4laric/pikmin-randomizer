"""Concrete lane-04 candidate slots and P2 placement profiles.

This is the concrete-placement companion to :mod:`randomizer.p2_placement`. It
turns the real slot tables the game already uses into `p2-placement-v1` slot
records and pairs them with placement profiles for the initial P2 candidate
cohort (fan-out lanes 13, 14, 16 and 19).

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
)

# Candidate source_ids that are bosses and therefore require a lane-04 encounter
# descriptor instead of a universal replacement profile. Tracked here so the
# cohort is complete without silently admitting them.
BOSS_COHORT = (
    (71, 'UmiMushi', 16, ['water']),
    (101, 'UmiMushiBlind', 16, ['water']),
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
        profiles.append(_placement.normalize_profile({
            'identity': identity,
            'terrains': list(terrains),
            'family_lane': lane,
            'cohort': cohort,
            'requires_home': requires_home,
            'requires_corpse_route': True,
            'accepted_gates': [],
            'notes': (f"P2 source_id {source_id}; lane-04 constraint seed; "
                      f"p1_equivalent {equivalent}; placement cohort {cohort}; "
                      f"requires_home {requires_home}; native placement gate "
                      f"pending family lane {lane}."),
        }))
    return profiles


def build_document(slots=None, profiles=None):
    """Return a validated `p2-placement-v1` document for the candidate cohort."""
    if slots is None:
        slots = all_slots()
    if profiles is None:
        profiles = candidate_profiles()
    return _placement.validate_document({
        'schema': SCHEMA,
        'slots': list(slots),
        'profiles': list(profiles),
        'notes': 'Lane-04 concrete candidate slots (campaign + adult/group + generator) and P2 candidate profiles; default deny.',
    })


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--document', type=Path, default=None,
                        help='write the built placement document JSON to this path')
    parser.add_argument('--summary', action='store_true', help='print per-identity compatibility counts')
    parser.add_argument('--report', type=Path, default=None,
                        help='write the compatibility report JSON to this path')
    args = parser.parse_args(argv)

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
