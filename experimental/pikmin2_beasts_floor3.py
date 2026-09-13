"""Source-bound Beasts floor 3 assets and isolated engineering room packages."""
import argparse
import hashlib
import json
from pathlib import Path

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_collision import attach_collision, ground_height, route_ini
from experimental.pikmin2_convert import convert
from experimental.pikmin2_pod import pellet_catalog

POOL = '2_ABE_norhiba_blkhiba_tsuchi.txt'
ROOMS = ('room_block1_3_hiba_tsuchi', 'room_north_1_hiba_tsuchi')
TREASURES = ('donutswhite', 'dia_c_green')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_floor(catalog):
    caves = [c for c in catalog['caves'] if c['cave_id'] == 'forest_1']
    if len(caves) != 1:
        raise ValueError('Expected one forest_1 cave')
    floors = [f for f in caves[0]['floors'] if f['first_floor'] <= 3 <= f['last_floor']]
    if len(floors) != 1:
        raise ValueError('Ambiguous floor three')
    floor = floors[0]
    rows = [(e['enemy_id'], e.get('minimum_count', e.get('target_count')), e['placement_type']) for e in floor['enemies']]
    if rows != [('Hiba', 7, 1), ('Hiba', 7, 8), ('HikariKinoko', 8, 6)]:
        raise ValueError('Unexpected floor-three actor roster')
    if any(e.get('selection_weight', 0) or e.get('carried_treasure') for e in floor['enemies']):
        raise ValueError('Unsupported weighted or carrying actor')
    expected = [dict(treasure_id=t, source_weight=10, minimum_count=1, selection_weight=0) for t in TREASURES]
    p = floor['parameters']
    if floor['treasures'] != expected or floor['gates'] or floor['caps']:
        raise ValueError('Unexpected floor-three cargo, gate or cap roster')
    if floor['definition_index'] != 2 or p['f008'] != POOL or p['f007'] != '0' or p['f010'] != '0':
        raise ValueError('Unexpected floor-three unit or exit definition')
    names = [u['name'] for u in catalog['unit_pools'][POOL]['units'] if u['kind'] == 1]
    if sorted(names) != sorted(ROOMS):
        raise ValueError('Unexpected floor-three room candidates')
    return floor


def economy(row):
    values = [int(row[k]) for k in ('money', 'min', 'max')]
    if not 0 < values[0] <= 10000 or not 1 <= values[1] <= values[2] <= 100:
        raise ValueError('Invalid treasure economy')
    return dict(value=values[0], weight=values[1], slots=values[2])


def checked_rooms(units, catalog_raw, *, source_navigation=False):
    metadata = json.loads((units/'units.json').read_bytes())
    if metadata['cave_id'] != 'forest_1' or metadata['catalog_sha256'] != sha(catalog_raw):
        raise ValueError('Unit/catalog provenance mismatch')
    catalog = json.loads(catalog_raw)
    definitions = {u['name']: u for u in catalog['unit_pools'][POOL]['units']}
    result = {}
    for name in ROOMS:
        record = metadata['units'][name]
        if record['definition'] != definitions[name] or not record['assembly_ready']:
            raise ValueError('Unsupported room definition or routes: '+name)
        files = {}
        for filename in ('render.mod', 'room.mod', 'room.ini', 'collision.json'):
            raw = (units/'units'/name/filename).read_bytes()
            if sha(raw) != record['output_sha256'][filename]:
                raise ValueError('Unit hash mismatch: '+name+'/'+filename)
            files[filename] = raw
        room = json.loads(files['collision.json'])
        probes = []
        for i, spawn in enumerate(room['spawns']):
            x, y, z = spawn['position']
            ground = ground_height(room['vertices'], room['triangles'], x, z)
            probes.append(dict(source_slot=i, source=spawn, ground=ground,
                               grounded=ground is not None and abs(ground-y) <= .1,
                               placement_selected=False))
        navigation = None
        if source_navigation:
            from experimental.pikmin2_beasts_navigation import interpret
            room, navigation = interpret(room, record['definition'])
        result[name] = dict(record=record, probes=probes, navigation=navigation, files={
            'room.mod': attach_collision(files['render.mod'], room, cap_exits=True),
            'room.ini': route_ini(room['routes']).encode('ascii'),
            'collision.json': (json.dumps(room, indent=2)+'\n').encode() if source_navigation else files['collision.json']})
        if source_navigation:
            result[name]['files']['source-collision.json'] = files['collision.json']
    return metadata, result


def prepare(iso, catalog_path, units, output, *, source_navigation=False):
    catalog_raw = catalog_path.read_bytes()
    catalog = json.loads(catalog_raw)
    floor = source_floor(catalog)
    imported, rooms = checked_rooms(units, catalog_raw, source_navigation=source_navigation)
    index = disc_files(iso)
    hashes = {}
    cargo = {}
    with iso.open('rb') as disc:
        def read(name):
            offset, size = index[name]
            disc.seek(offset)
            raw = disc.read(size)
            if len(raw) != size:
                raise ValueError('Truncated disc asset')
            hashes[name] = sha(raw)
            return raw
        # Bind both source catalog and converted unit archives to this disc.
        for name in catalog['source_sha256'].keys() & imported['source_sha256'].keys():
            if catalog['source_sha256'][name] != imported['source_sha256'][name]:
                raise ValueError('Conflicting catalog/unit provenance: '+name)
        for name, digest in {**catalog['source_sha256'], **imported['source_sha256']}.items():
            if sha(read(name)) != digest:
                raise ValueError('Disc provenance mismatch: '+name)
        config = pellet_catalog(read('user/Abe/Pellet/us/otakara_config.txt').decode('shift_jis'))
        models = {}
        for name in TREASURES:
            row = config[name]
            cargo[name] = dict(catalog_id=name, instance_id=f'forest_1:floor3:treasure:{name}:0',
                               **economy(row), source_config=row, placement=None)
            members = archive_files(read('user/Abe/Pellet/us/'+row['archive']))
            matches = [v for k, v in members.items() if k.lower() == row['bmd'].lower()]
            if len(matches) != 1:
                raise ValueError('Missing or ambiguous source treasure model')
            models[name] = matches[0]
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in models.items():
        directory = output/'treasures'/name
        directory.mkdir(parents=True)
        source, target = directory/'source.bmd', directory/'treasure.mod'
        source.write_bytes(raw)
        first = convert(source, target, True, bake_rigid=True)
        report = convert(source, target, True, y_offset=-first['bounds'][1], bake_rigid=True)
        report['source'], report['output'] = 'source.bmd', 'treasure.mod'
        target.with_suffix('.json').write_text(json.dumps(report, indent=2)+'\n')
        cargo[name].update(source_model_sha256=sha(raw), model_sha256=sha(target.read_bytes()), conversion=report)
    staged = {}
    for name, room in rooms.items():
        directory = output/'rooms'/name
        directory.mkdir(parents=True)
        for filename, raw in room['files'].items():
            (directory/filename).write_bytes(raw)
        staged[name] = dict(source=room['record'], spawn_ground_audit=room['probes'], exits_capped=True,
                           routes_connected=not any(r['unreachable_sources'] for r in room['record']['route_audit']),
                           output_sha256={f: sha(raw) for f, raw in room['files'].items()})
        if source_navigation:
            staged[name]['navigation'] = room['navigation']
    result = dict(schema=1, policy='P2_BEASTS_FLOOR3_PACKAGE_1', cave='forest_1', floor=3,
        catalog_sha256=sha(catalog_raw), source_sha256=hashes, source_definition=floor,
        treasures=cargo, rooms=staged, native_ready=False, retail_generation=False, complete_roster=False,
        actors=[dict(definition_id=f'forest_1:definition2:enemy:{i}', source=row,
                     runtime_status='not_installed', placement=None) for i, row in enumerate(floor['enemies'])],
        exit=dict(destination_floor=4, has_geyser=False, clogged_hole=False, placement=None, native_supported=False),
        limitations=['Two isolated capped source room candidates; no assembled or seeded floor.',
                     'Source route graphs contain unreachable waypoints; no route repair or carry certification.',
                     'Hiba and HikariKinoko are omitted; no P1 actor substitutions.',
                     'Treasure models/economy are imported but not spawned or receipted.',
                     'Source spawn probes are candidates, not selected placements or carry-route validation.',
                     'Approximate materials inherit converter policy; source texture animation is deferred.',
                     'No native launch, gameplay acceptance, session binding or floor-four descent.'])
    if source_navigation:
        result['policy'] = 'P2_BEASTS_FLOOR3_NAVIGATION_PACKAGE_1'
        result['limitations'].append('Opt-in local waypoint Y grounding only; source X/Z, edges and spawn centers preserved.')
    (output/'floor3.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('iso', 'catalog', 'units', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--source-navigation', action='store_true', help='Opt in to source-backed local waypoint grounding and navigation audit')
    args = parser.parse_args()
    prepare(args.iso, args.catalog, args.units, args.output, source_navigation=args.source_navigation)
    print(args.output/'floor3.json')


if __name__ == '__main__':
    main()
