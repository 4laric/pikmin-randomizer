"""Candidate evidence only: does not enable replacements or change seed catalogs."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

from audit_enemy_slots import audit


FLOAT_FIELDS = {
    'health': 0, 'scale': 1, 'walk_speed': 3, 'run_speed': 4,
    'visible_range': 6, 'attackable_range': 8, 'attack_range': 10,
    'danger_territory': 15, 'safety_territory': 16,
    'corpse_radius': 20, 'corpse_height': 21, 'flight_height': 29,
    'collision_radius': 44, 'lower_range': 45, 'drop_velocity': 50,
    'attack_start_height': 51, 'impassable_period': 56, 'impassable_distance': 57,
}


def parameters(data):
    # TekiParameters v11: version, eight ID32s, then 21 ints and 62 floats.
    # Counts come from TAI/Otimoti.h; ParaMultiParameters reads ints before floats.
    if len(data) != 368 or struct.unpack_from('>i', data)[0] != 11:
        raise ValueError('expected 368-byte version-11 Wollywog parameters')
    ints = struct.unpack_from('>21i', data, 36)
    floats = struct.unpack_from('>62f', data, 120)
    if not all(math.isfinite(value) for value in floats):
        raise ValueError('non-finite Wollywog parameter')
    return dict(ids=[data[i:i+4].hex() for i in range(4, 36, 4)],
                corpse_type=ints[0], culling_type=ints[2],
                jump_ready_loops=ints[20],
                **{name: floats[index] for name, index in FLOAT_FIELDS.items()})


def report(assets):
    catalog = audit(assets)
    species = []
    for type_id, name in ((0, 'frog'), (33, 'frow')):
        relative = f'tekipara/{name}.bin'
        paths = [relative, f'tekikeys/{name}.key',
                 *(f'tekis/{name}/{name}{suffix}' for suffix in ('.mod', 'col.mod', '.anm'))]
        fingerprints = {p: hashlib.sha256((assets / 'dataDir' / p).read_bytes()).hexdigest() for p in paths}
        species.append(dict(type_id=type_id, asset_name=name, asset_sha256=fingerprints,
                            parameters=parameters((assets / 'dataDir' / relative).read_bytes())))
    slots = []
    for row in catalog['slots']:
        if row['kind'] != 'teki' or row['species'] not in (0, 33) or not row['activation_days']:
            continue
        reasons = []
        if row['personality']['pellet_id'] != 'none': reasons.append('named drop')
        if row['personality']['parameter0'] != 0: reasons.append('special personality parameter')
        if row['area'] != 'pint': reasons.append('distributed area')
        if (row['count_min'], row['count_max']) != (1, 1): reasons.append('variable or multiple bodies')
        if row['carry_flags'] != 5: reasons.append('unaudited persistence flags')
        slots.append(dict(id=row['id'], original=row['species'], position=row['position'],
                          schedule=row['schedule'], first_campaign_day=min(row['activation_days']),
                          respawn_days=row['respawn_days'], spawn_type=row['spawn_type'],
                          personality=row['personality'], exclusions=reasons,
                          status='excluded' if reasons else 'candidate-unverified'))
    return dict(version='wollywog-candidate-audit-v1', catalog_hash=catalog['sha256'],
                enabled=False, species=species, slots=slots,
                pending=['Native replacement asset loading and births',
                         'Terrain depth, footprint and jump/landing clearance at each anchor',
                         'Combat, camera culling, death and corpse delivery',
                         'Pellet manager carry requirements and seed yields',
                         'Survivor restore, day-cycle respawn and source guarantees',
                         'Seed protocol and solo/AP reachability integration'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('assets', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = report(args.assets)
    if args.check:
        if json.loads(args.output.read_text(encoding='utf-8')) != result:
            raise ValueError('Wollywog audit differs from assets')
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f"{len(result['slots'])} active slots; "
          f"{sum(not s['exclusions'] for s in result['slots'])} unverified candidates; replacements disabled")


if __name__ == '__main__':
    main()
