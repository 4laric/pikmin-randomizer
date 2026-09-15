"""Seeded hazard-leaf alcove catalog and attachment planner (lane 36, #468/#475).

A *leaf* is a single-door dead-end cave unit with exactly one treasure spawn
point inside, attached to a hazard-free segment. Water is intrinsic to the unit
(its `waterbox.txt` volume); electric/poison/fire are door or in-room hazard
actors assigned later by lane 37. This module authors and validates the unit
config and plans attachment to segment doors. It does not assign tagged
treasures or gates.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
import tempfile

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_cave import BASE, safe_name, tree
from experimental.pikmin2_collision import decode_room

LEAF_HAZARDS = ('water', 'elec', 'poison', 'fire')
# Hard hazards stop carrying until the ability is owned; soft geysers are timing based.
HAZARD_HARDNESS = {'water': 'hard', 'elec': 'hard', 'poison': 'soft', 'fire': 'soft'}
# CaveGenType::CGT_TreasureItem — the single item spawn a leaf may carry.
TREASURE_SPAWN = 2
UNITKIND_CAP, UNITKIND_ROOM, UNITKIND_CORRIDOR = 0, 1, 2
UNITKIND_NAMES = {UNITKIND_CAP: 'cap', UNITKIND_ROOM: 'room', UNITKIND_CORRIDOR: 'corridor'}
# A leaf slot table is seeded by lane 34/35; this is the consumer contract.
LEAF_TABLE_SCHEMA = 'p2-cave-leaf-table-v1'


def authored_hazards(name):
    """Hazards baked into a retail unit name (e.g. `*_hiba_*` authors fire geysers)."""
    tokens = safe_name(name).lower().split('_')
    found = []
    if 'hiba' in tokens:
        found.append('fire')
    return found


def classify_leaf_unit(definition, spawns, water_empty):
    """Validate one retail unit as a leaf alcove and normalize it.

    Rules (all build-time, not observations):
      * exactly one door — a single-door dead end;
      * placement kind is a cap or a room, never a corridor;
      * exactly one CGT_TreasureItem (=2) spawn point inside;
      * water is only claimed when `waterbox.txt` is non-empty.
    Raises ValueError on any violation; returns the leaf record.
    """
    name = safe_name(definition['name'])
    doors = definition['doors']
    if len(doors) != 1:
        raise ValueError('Leaf unit must have exactly one door: ' + name)
    kind = definition['kind']
    if kind not in (UNITKIND_CAP, UNITKIND_ROOM):
        raise ValueError('Leaf unit must be a cap or room: ' + name)
    treasures = [i for i, spawn in enumerate(spawns) if spawn['type'] == TREASURE_SPAWN]
    if len(treasures) != 1:
        raise ValueError('Leaf unit must have exactly one treasure spawn: ' + name)
    if not isinstance(water_empty, bool):
        raise ValueError('Leaf unit water state must be known: ' + name)
    water = not water_empty
    authored = authored_hazards(name)
    supports = list(LEAF_HAZARDS) if water else ['elec', 'poison', 'fire']
    return dict(name=name, kind=kind, kind_name=UNITKIND_NAMES[kind], cells=list(definition['cells']),
                door=int(doors[0]['id']), treasure_slots=treasures, water=water,
                authored_hazards=authored, supports=supports,
                spawn_types=dict(sorted(Counter(s['type'] for s in spawns).items())))


def validate_leaf_catalog(catalog):
    """Fail closed unless the catalog covers every hazard with a validated leaf."""
    if catalog.get('schema') != 1:
        raise ValueError('Unsupported leaf catalog schema')
    units = catalog.get('units')
    if not isinstance(units, list) or not units:
        raise ValueError('Leaf catalog has no units')
    seen = set()
    for unit in units:
        name = safe_name(unit['name'])
        if name in seen:
            raise ValueError('Duplicate leaf unit: ' + name)
        seen.add(name)
        if unit['kind'] not in (UNITKIND_CAP, UNITKIND_ROOM) or len(str(unit['door'])) == 0:
            raise ValueError('Malformed leaf unit: ' + name)
        if unit['water'] and 'water' not in unit['supports']:
            raise ValueError('Water unit must support water: ' + name)
        if not unit['water'] and 'water' in unit['supports']:
            raise ValueError('Dry unit must not claim water: ' + name)
        if not set(unit['supports']) <= set(LEAF_HAZARDS):
            raise ValueError('Unknown supported hazard: ' + name)
        if len(unit['treasure_slots']) != 1:
            raise ValueError('Leaf unit must have one treasure slot: ' + name)
    for hazard in LEAF_HAZARDS:
        if hazard not in catalog.get('capacity', {}):
            raise ValueError('Leaf catalog missing hazard class: ' + hazard)
    return catalog


def leaf_capacity(units):
    """Per-hazard counts of distinct units that can host each class."""
    return {hazard: sum(1 for unit in units if hazard in unit['supports']) for hazard in LEAF_HAZARDS}


def pick_leaf(units, hazard):
    """Deterministically choose a validated unit for a hazard slot.

    Water prefers intrinsic water units. Actor hazards prefer a unit with the
    matching authored hazard, then any dry unit. Ties break on unit name.
    """
    if hazard not in LEAF_HAZARDS:
        raise ValueError('Unknown leaf hazard: ' + str(hazard))
    candidates = sorted((u for u in units if hazard in u['supports']), key=lambda u: u['name'])
    if not candidates:
        raise ValueError('No leaf unit supports hazard: ' + hazard)
    if hazard == 'water':
        return candidates[0]
    # Actor hazards go in a dry alcove; only fall back to a flooded room if no dry unit exists.
    dry = [u for u in candidates if not u['water']]
    authored = [u for u in dry if hazard in u['authored_hazards']]
    return (authored or dry or candidates)[0]


def validate_leaf_table(table):
    if table.get('schema') != LEAF_TABLE_SCHEMA:
        raise ValueError('Unsupported leaf table schema')
    segments = table.get('segments')
    if not isinstance(segments, list) or not segments:
        raise ValueError('Leaf table needs segments')
    seen = set()
    for segment in segments:
        if not isinstance(segment.get('segment'), int) or segment['segment'] in seen:
            raise ValueError('Duplicate or malformed segment')
        seen.add(segment['segment'])
        if not isinstance(segment.get('doors'), list) or any(not isinstance(d, int) for d in segment['doors']):
            raise ValueError('Malformed segment doors')
    leaves = table.get('leaves')
    if not isinstance(leaves, list) or not leaves:
        raise ValueError('Leaf table needs leaves')
    for slot in leaves:
        if slot.get('segment') not in seen:
            raise ValueError('Leaf slot references a missing segment')
        if slot.get('hazard') not in LEAF_HAZARDS:
            raise ValueError('Leaf slot has an unknown hazard')
    return table


def attach_leaves(units, table):
    """Place one leaf per seeded slot onto a free door of its target segment.

    Generation-side contract: segments and their free doors come from lane 35's
    phased trunk growth; the ordered leaf list is the lane-34 seeded table. Each
    slot consumes one door. Returns a deterministic plan; no tagged item or gate
    assignment happens here (lane 37).
    """
    validate_leaf_table(table)
    free = {}
    order = []
    for segment in table['segments']:
        free[segment['segment']] = list(segment['doors'])
        order.append(segment['segment'])
    assignments = []
    used = set()
    for slot in table['leaves']:
        segment = slot['segment']
        if not free[segment]:
            raise ValueError('No free door for leaf slot: ' + str(slot.get('slot')))
        door = free[segment].pop(0)
        if (segment, door) in used:
            raise ValueError('Leaf door reused: ' + str((segment, door)))
        used.add((segment, door))
        unit = pick_leaf(units, slot['hazard'])
        assignments.append(dict(slot=slot.get('slot'), segment=segment, door=door,
                                hazard=slot['hazard'], hardness=HAZARD_HARDNESS[slot['hazard']],
                                unit=unit['name'], treasure_slots=list(unit['treasure_slots']),
                                water=unit['water']))
    plan = dict(schema='p2-cave-leaf-plan-v1', floor=table.get('floor'), table_schema=table['schema'],
                assignments=assignments, unused_doors={str(s): free[s] for s in order if free[s]})
    return plan


def build_leaf_catalog(iso, catalog, output, cave_ids=None):
    """Scan real single-door retail units and emit a validated leaf catalog."""
    if catalog.get('schema') != 1:
        raise ValueError('Unsupported cave catalog schema')
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    files = disc_files(iso)
    hashes = {}
    caves = cave_ids if cave_ids is not None else [c['cave_id'] for c in catalog['caves']]
    selected = [c for c in catalog['caves'] if c['cave_id'] in caves]
    if len(selected) != len(caves):
        raise ValueError('Unknown cave in leaf scan')
    units = {}
    with iso.open('rb') as disc:
        def read(path):
            if path not in files:
                raise ValueError('Missing disc asset: ' + path)
            offset, size = files[path]
            disc.seek(offset)
            data = disc.read(size)
            if len(data) != size:
                raise ValueError('Truncated disc asset')
            hashes[path] = hashlib.sha256(data).hexdigest()
            return data
        for cave in selected:
            for floor in cave['floors']:
                pool = floor['parameters']['f008']
                for definition in catalog['unit_pools'][pool]['units']:
                    if len(definition['doors']) != 1:
                        continue
                    name = safe_name(definition['name'])
                    if name in units:
                        unit = units[name]
                    else:
                        with tempfile.TemporaryDirectory() as tmp:
                            texts = Path(tmp) / 'texts'
                            for member, data in archive_files(read(f'{BASE}/arc/{name}/texts.szs')).items():
                                target = texts / member
                                target.parent.mkdir(parents=True, exist_ok=True)
                                target.write_bytes(data)
                            water_file = texts / 'waterbox.txt'
                            if not water_file.exists():
                                raise ValueError('Leaf candidate has no waterbox: ' + name)
                            water_empty = tree(water_file.read_text()) == ['0', ['0']]
                            try:
                                spawns = decode_room(texts)['spawns']
                            except ValueError:
                                # Material/route decode failures are not leaf evidence.
                                spawns = None
                        if spawns is None:
                            continue
                        try:
                            unit = classify_leaf_unit(definition, spawns, water_empty)
                        except ValueError:
                            continue
                        unit.update(caves=[], pools=[], source=[])
                        units[name] = unit
                    if cave['cave_id'] not in unit['caves']:
                        unit['caves'].append(cave['cave_id'])
                    if pool not in unit['pools']:
                        unit['pools'].append(pool)
    ordered = sorted(units.values(), key=lambda u: u['name'])
    result = dict(schema=1, disc=catalog.get('disc'), generated=True, leaf_hazards=list(LEAF_HAZARDS),
                  capacity=leaf_capacity(ordered), units=ordered, source_sha256=hashes,
                  limitations=['Catalog is a validated unit selection, not a generated floor layout.',
                               'Authoring tags intrinsic water only; electric/poison/fire actors are placed by lane 37.',
                               'A single unit template may be reused across distinct leaf slots on a floor.'])
    validate_leaf_catalog(result)
    (output / 'leaf_catalog.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cave', action='append', dest='caves')
    parser.add_argument('--table', type=Path)
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text())
    result = build_leaf_catalog(args.iso, catalog, args.output, tuple(args.caves) if args.caves else None)
    summary = dict(units=len(result['units']), capacity=result['capacity'], output=str(args.output / 'leaf_catalog.json'))
    if args.table is not None:
        table = json.loads(args.table.read_text())
        plan = attach_leaves(result['units'], table)
        (args.output / 'leaf_plan.json').write_text(json.dumps(plan, indent=2) + '\n', encoding='utf-8')
        summary['assignments'] = len(plan['assignments'])
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
