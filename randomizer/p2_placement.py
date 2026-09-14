"""Machine-readable P2 placement/encounter compatibility schema and audit tool.

This is the lane-04 (fan-out) placement side of the production randomizer
bridge. It does **not** choose a seed, serialize a layout or implement family
AI. It answers one question for a candidate `(slot, identity)` pair:

    is this P2 identity allowed to occupy this source spawn slot?

The answer defaults to *denied*. A pair is only legal when the slot carries
accepted native placement evidence, the identity has a placement profile with at
least one accepted placement gate, and every terrain/space/route/helper
constraint holds. Bosses additionally require an encounter descriptor; a
universal replacement permission is never granted.

Identity ownership stays with lane 02 (roster) and seed serialization with lane
03. This module consumes their identity keys and defines the constraint record
they must agree on before coding consumers.
"""
import argparse
import json
import sys
from pathlib import Path

SCHEMA = 'p2-placement-v1'
TERRAIN_CLASSES = ('ground', 'water', 'air', 'underground', 'mixed')
EVIDENCE_KEYS = ('xyz', 'terrain', 'route')
SLOT_REQUIRED = ('uid', 'label', 'stage', 'terrain', 'radius')
PROFILE_REQUIRED = ('identity', 'terrains')
DOCUMENT_REQUIRED = ('schema', 'slots', 'profiles')


def _fail(message):
    raise ValueError(message)


def _is_bool(value):
    return isinstance(value, bool)


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_keys(kind, data, required, allowed):
    if not isinstance(data, dict):
        _fail(f'{kind} must be an object')
    missing = [key for key in required if key not in data]
    if missing:
        _fail(f'{kind} missing required field(s): {", ".join(missing)}')
    unknown = [key for key in data if key not in allowed]
    if unknown:
        _fail(f'{kind} has unknown field(s): {", ".join(sorted(unknown))}')


SLOT_ALLOWED = SLOT_REQUIRED + (
    'water_depth', 'flight_space', 'burrow_ground', 'home', 'helper_capacity',
    'projectile_corridor', 'corpse_route', 'protected', 'boss_slot',
    'first_day', 'respawn_days', 'evidence', 'source_identity',
)
PROFILE_ALLOWED = PROFILE_REQUIRED + (
    'family_lane', 'footprint_radius', 'min_water_depth', 'requires_flight_space',
    'requires_burrow_ground', 'requires_home', 'helper_budget',
    'requires_projectile_corridor', 'requires_corpse_route', 'is_boss',
    'encounter_descriptor', 'accepted_gates', 'allow_protected',
    'requires_renewable_slot', 'min_first_day', 'notes',
)


def normalize_slot(data):
    _check_keys('slot', data, SLOT_REQUIRED, SLOT_ALLOWED)
    slot = {
        'uid': data['uid'],
        'label': data['label'],
        'stage': data['stage'],
        'terrain': data['terrain'],
        'radius': data['radius'],
        'water_depth': data.get('water_depth', 0),
        'flight_space': data.get('flight_space', False),
        'burrow_ground': data.get('burrow_ground', False),
        'home': data.get('home', False),
        'helper_capacity': data.get('helper_capacity', 0),
        'projectile_corridor': data.get('projectile_corridor', False),
        'corpse_route': data.get('corpse_route', False),
        'protected': data.get('protected', False),
        'boss_slot': data.get('boss_slot', False),
        'first_day': data.get('first_day', 1),
        'respawn_days': data.get('respawn_days', 0),
        'source_identity': data.get('source_identity'),
        'evidence': {
            key: bool(data.get('evidence', {}).get(key, False)) for key in EVIDENCE_KEYS
        },
    }
    return validate_slot(slot)


def validate_slot(slot):
    if not isinstance(slot['uid'], int) or isinstance(slot['uid'], bool):
        _fail('slot uid must be an integer')
    if not isinstance(slot['label'], str) or not slot['label']:
        _fail('slot label must be a non-empty string')
    if not isinstance(slot['stage'], int) or isinstance(slot['stage'], bool) or slot['stage'] < 0:
        _fail('slot stage must be a non-negative integer')
    if slot['terrain'] not in TERRAIN_CLASSES:
        _fail(f'slot terrain must be one of {TERRAIN_CLASSES}')
    if not _is_number(slot['radius']) or slot['radius'] < 0:
        _fail('slot radius must be a non-negative number')
    if not _is_number(slot['water_depth']) or slot['water_depth'] < 0:
        _fail('slot water_depth must be a non-negative number')
    if not isinstance(slot['helper_capacity'], int) or isinstance(slot['helper_capacity'], bool) or slot['helper_capacity'] < 0:
        _fail('slot helper_capacity must be a non-negative integer')
    if not isinstance(slot['first_day'], int) or isinstance(slot['first_day'], bool) or slot['first_day'] < 1:
        _fail('slot first_day must be a positive integer')
    if not isinstance(slot['respawn_days'], int) or isinstance(slot['respawn_days'], bool) or slot['respawn_days'] < 0:
        _fail('slot respawn_days must be a non-negative integer')
    for key in ('flight_space', 'burrow_ground', 'home', 'projectile_corridor', 'corpse_route', 'protected', 'boss_slot'):
        if not _is_bool(slot[key]):
            _fail(f'slot {key} must be a boolean')
    if slot['source_identity'] is not None and not isinstance(slot['source_identity'], str):
        _fail('slot source_identity must be a string or null')
    if not isinstance(slot['evidence'], dict):
        _fail('slot evidence must be an object')
    for key in EVIDENCE_KEYS:
        if not _is_bool(slot['evidence'][key]):
            _fail(f'slot evidence.{key} must be a boolean')
    return slot


def normalize_profile(data):
    _check_keys('profile', data, PROFILE_REQUIRED, PROFILE_ALLOWED)
    profile = {
        'identity': data['identity'],
        'terrains': list(data['terrains']),
        'family_lane': data.get('family_lane', 0),
        'footprint_radius': data.get('footprint_radius', 0),
        'min_water_depth': data.get('min_water_depth', 0),
        'requires_flight_space': data.get('requires_flight_space', False),
        'requires_burrow_ground': data.get('requires_burrow_ground', False),
        'requires_home': data.get('requires_home', False),
        'helper_budget': data.get('helper_budget', 0),
        'requires_projectile_corridor': data.get('requires_projectile_corridor', False),
        'requires_corpse_route': data.get('requires_corpse_route', False),
        'is_boss': data.get('is_boss', False),
        'encounter_descriptor': data.get('encounter_descriptor'),
        'accepted_gates': list(data.get('accepted_gates', [])),
        'allow_protected': data.get('allow_protected', False),
        'requires_renewable_slot': data.get('requires_renewable_slot', False),
        'min_first_day': data.get('min_first_day', 0),
        'notes': data.get('notes', ''),
    }
    return validate_profile(profile)


def validate_profile(profile):
    if not isinstance(profile['identity'], str) or not profile['identity']:
        _fail('profile identity must be a non-empty string')
    if not isinstance(profile['terrains'], list) or not profile['terrains']:
        _fail('profile terrains must be a non-empty list')
    for terrain in profile['terrains']:
        if terrain not in TERRAIN_CLASSES:
            _fail(f'profile terrain must be one of {TERRAIN_CLASSES}')
    if not isinstance(profile['family_lane'], int) or isinstance(profile['family_lane'], bool) or profile['family_lane'] < 0:
        _fail('profile family_lane must be a non-negative integer')
    if not _is_number(profile['footprint_radius']) or profile['footprint_radius'] < 0:
        _fail('profile footprint_radius must be a non-negative number')
    if not _is_number(profile['min_water_depth']) or profile['min_water_depth'] < 0:
        _fail('profile min_water_depth must be a non-negative number')
    if not isinstance(profile['helper_budget'], int) or isinstance(profile['helper_budget'], bool) or profile['helper_budget'] < 0:
        _fail('profile helper_budget must be a non-negative integer')
    for key in ('requires_flight_space', 'requires_burrow_ground', 'requires_home',
                'requires_projectile_corridor', 'requires_corpse_route', 'is_boss',
                'allow_protected', 'requires_renewable_slot'):
        if not _is_bool(profile[key]):
            _fail(f'profile {key} must be a boolean')
    if profile['encounter_descriptor'] is not None and not isinstance(profile['encounter_descriptor'], str):
        _fail('profile encounter_descriptor must be a string or null')
    if not isinstance(profile['accepted_gates'], list) or any(not isinstance(g, str) for g in profile['accepted_gates']):
        _fail('profile accepted_gates must be a list of strings')
    if not isinstance(profile['min_first_day'], int) or isinstance(profile['min_first_day'], bool) or profile['min_first_day'] < 0:
        _fail('profile min_first_day must be a non-negative integer')
    if not isinstance(profile['notes'], str):
        _fail('profile notes must be a string')
    return profile


def validate_document(document):
    _check_keys('document', document, DOCUMENT_REQUIRED, DOCUMENT_REQUIRED + ('notes',))
    if document['schema'] != SCHEMA:
        _fail(f'document schema must be {SCHEMA}')
    if not isinstance(document['slots'], list) or not isinstance(document['profiles'], list):
        _fail('document slots and profiles must be lists')
    slots = [normalize_slot(slot) for slot in document['slots']]
    profiles = [normalize_profile(profile) for profile in document['profiles']]
    uids = [slot['uid'] for slot in slots]
    if len(set(uids)) != len(uids):
        _fail('document has duplicate slot uids')
    identities = [profile['identity'] for profile in profiles]
    if len(set(identities)) != len(identities):
        _fail('document has duplicate profile identities')
    return {'schema': SCHEMA, 'slots': slots, 'profiles': profiles,
            'notes': document.get('notes', '')}


def load_document(path):
    return validate_document(json.loads(Path(path).read_text()))


def evaluate(slot, profile):
    """Return {'status': 'legal'|'denied', 'reasons': [...]} with deny default."""
    reasons = []
    if not profile['accepted_gates']:
        reasons.append('no accepted placement evidence')
    if not all(slot['evidence'].get(key, False) for key in EVIDENCE_KEYS):
        reasons.append('slot lacks accepted native placement evidence')
    if slot['protected'] and not profile['allow_protected']:
        reasons.append('slot drop is protected')
    if profile['is_boss'] and not profile['encounter_descriptor']:
        reasons.append('boss requires an encounter descriptor')
    if slot['boss_slot'] and not profile['encounter_descriptor']:
        reasons.append('boss slot requires an encounter descriptor')
    if slot['terrain'] not in profile['terrains']:
        reasons.append(f"terrain {slot['terrain']} not in {profile['terrains']}")
    if slot['water_depth'] < profile['min_water_depth']:
        reasons.append(f"water depth {slot['water_depth']} below required {profile['min_water_depth']}")
    if profile['requires_flight_space'] and not slot['flight_space']:
        reasons.append('slot lacks flight space')
    if profile['requires_burrow_ground'] and not slot['burrow_ground']:
        reasons.append('slot lacks burrow ground')
    if profile['requires_home'] and not slot['home']:
        reasons.append('slot lacks a home/nest anchor')
    if profile['requires_projectile_corridor'] and not slot['projectile_corridor']:
        reasons.append('slot lacks a projectile corridor')
    if profile['requires_corpse_route'] and not slot['corpse_route']:
        reasons.append('slot lacks a corpse return route')
    if profile['helper_budget'] > slot['helper_capacity']:
        reasons.append(f"helper budget {profile['helper_budget']} exceeds slot capacity {slot['helper_capacity']}")
    if profile['footprint_radius'] > slot['radius']:
        reasons.append(f"footprint {profile['footprint_radius']} exceeds slot radius {slot['radius']}")
    if profile['requires_renewable_slot'] and slot['respawn_days'] <= 0:
        reasons.append('slot is one-shot, not renewable')
    if slot['first_day'] < profile['min_first_day']:
        reasons.append(f"slot first day {slot['first_day']} before required {profile['min_first_day']}")
    return {'status': 'denied' if reasons else 'legal', 'reasons': sorted(reasons)}


def audit(document, slot_uids=None, identities=None):
    """Evaluate candidate pairs and return a deterministic machine-readable report."""
    document = validate_document(document)
    slots = [s for s in document['slots'] if slot_uids is None or s['uid'] in slot_uids]
    profiles = [p for p in document['profiles'] if identities is None or p['identity'] in identities]
    decisions = []
    admitted = {p['identity']: [] for p in profiles}
    denied = {p['identity']: [] for p in profiles}
    reasons = {}
    for slot in sorted(slots, key=lambda s: s['uid']):
        for profile in sorted(profiles, key=lambda p: p['identity']):
            result = evaluate(slot, profile)
            row = {'slot_uid': slot['uid'], 'slot_label': slot['label'], 'identity': profile['identity'], **result}
            decisions.append(row)
            if result['status'] == 'legal':
                admitted[profile['identity']].append(slot['uid'])
            else:
                denied[profile['identity']].append(slot['uid'])
                for reason in result['reasons']:
                    reasons[reason] = reasons.get(reason, 0) + 1
    return {
        'schema': SCHEMA,
        'slots_evaluated': len(slots),
        'identities_evaluated': len(profiles),
        'decisions': decisions,
        'admitted': {k: v for k, v in admitted.items() if v},
        'denied': {k: v for k, v in denied.items() if v},
        'denied_reasons': dict(sorted(reasons.items())),
        'unplaced_identities': sorted(p['identity'] for p in profiles if not admitted[p['identity']]),
        'boss_slots': sorted(s['uid'] for s in slots if s['boss_slot']),
    }


def slot_from_spawn_row(row, terrain='ground', evidence=None):
    """Adapt a P1 spawn row (spawn_data shape) into a default-deny slot record."""
    return normalize_slot({
        'uid': row['uid'],
        'label': row.get('label', str(row['uid'])),
        'stage': row.get('stage', 0),
        'terrain': terrain,
        'radius': row.get('radius', 0),
        'first_day': row.get('first_day', 1),
        'respawn_days': row.get('respawn_days', 0),
        'protected': row.get('protected', False),
        'source_identity': row.get('source', row.get('original')),
        'evidence': evidence or {},
    })


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--document', type=Path, required=True, help='placement/encounter JSON document')
    parser.add_argument('--summary', action='store_true', help='print counts only, not every decision')
    args = parser.parse_args(argv)
    report = audit(load_document(args.document))
    if args.summary:
        print(json.dumps({key: report[key] for key in
                          ('slots_evaluated', 'identities_evaluated', 'admitted', 'denied_reasons',
                           'unplaced_identities', 'boss_slots')}, indent=2))
    else:
        print(json.dumps(report, indent=2))
    return 1 if report['unplaced_identities'] and not report['admitted'] else 0


if __name__ == '__main__':
    sys.exit(main())
