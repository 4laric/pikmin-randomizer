"""Authored, source-door-matched Beasts floor-three engineering assembly."""
import argparse
import hashlib
import json
from pathlib import Path

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_assembly import transform, merge_rooms, merged_model
from experimental.pikmin2_beasts_assembly import cell_audit, seam_audit
from experimental.pikmin2_beasts_floor3 import POOL, ROOMS, source_floor
from experimental.pikmin2_beasts_navigation import interpret
from experimental.pikmin2_cave import route_audit
from experimental.pikmin2_collision import attach_collision, route_ini
from experimental.pikmin2_convert import write_model

BLOCK, NORTH = ROOMS
WAY, CAP = 'way2_tsuchi', 'cap_tsuchi'
NAMES = (BLOCK, WAY, NORTH, CAP)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def layout(units, rooms, *, block=BLOCK, north=NORTH, way=WAY, cap=CAP):
    instances = [(block, 0, [0,0,0])]
    seams = []

    def attach(parent, door_id, name, child_id):
        parent_name, turn, offset = instances[parent]
        door = next(d for d in units[parent_name]['doors'] if d['id'] == door_id)
        child = next(d for d in units[name]['doors'] if d['id'] == child_id)
        rotation = (door['direction']+turn+2-child['direction']) % 4
        target = next(p for p in rooms[parent_name]['routes'] if p['id'] == door['waypoint'])
        local = next(p for p in rooms[name]['routes'] if p['id'] == child['waypoint'])
        target = transform(target['position'], turn, offset)
        local = transform(local['position'], rotation)
        position = [a-b for a,b in zip(target, local)]
        index = len(instances)
        seams.append(((parent,door_id),(index,child_id)))
        instances.append((name,rotation,position))
        return index

    corridor = attach(0, 0, way, 1)
    attach(corridor, 0, north, 0)
    for door in units[block]['doors']:
        if door['id'] != 0:
            attach(0, door['id'], cap, 0)
    return instances, seams


def return_audit(room, target):
    matches = [p['id'] for p in room['routes'] if p['position'] == target]
    if len(matches) != 1:
        raise ValueError('Ambiguous engineering return waypoint')
    rows = route_audit(room)
    selected = next(p for p in rows if p['destination'] == matches[0])
    if selected['unreachable_sources']:
        raise ValueError('Source waypoint cannot reach engineering return target')
    return dict(target=matches[0], position=target, all_sources_reach_target=True,
                source_route_audit=rows, all_pairs_connected=not any(r['unreachable_sources'] for r in rows))


def build(iso, catalog_path, imported, output, *, floor=3, room_names=ROOMS, pool=POOL, cap=CAP):
    catalog_raw = catalog_path.read_bytes()
    catalog = json.loads(catalog_raw)
    if floor==3:
        if tuple(room_names)!=ROOMS or pool!=POOL or cap!=CAP:raise ValueError('Unexpected floor3 assembly selection')
        source_floor(catalog)
    elif floor!=4:raise ValueError('Unsupported engineering assembly floor')
    elif tuple(room_names)!=('room_mid1_6_tsuchi','room_north3_1_tsuchi') or pool!='2_ABE_mid1_nor3_tsuchi.txt' or cap!='item_cap_tsuchi':
        raise ValueError('Unexpected floor4 assembly selection')
    block,north=room_names
    names=(block,WAY,north,cap)
    manifest_raw = (imported/'units.json').read_bytes()
    manifest = json.loads(manifest_raw)
    if manifest['cave_id'] != 'forest_1' or manifest['catalog_sha256'] != sha(catalog_raw):
        raise ValueError('Catalog/unit provenance mismatch')
    definitions = {u['name']:u for u in catalog['unit_pools'][pool]['units']}
    if not set(names) <= set(definitions):
        raise ValueError('Assembly candidate absent from floor-three source pool')
    units, rooms, sources, navigation, source_hashes = {}, {}, {}, {}, {}
    index = disc_files(iso)
    with iso.open('rb') as disc:
        def read(name, expected):
            offset,size = index[name]
            disc.seek(offset)
            raw = disc.read(size)
            if len(raw) != size or sha(raw) != expected:
                raise ValueError('Disc source mismatch: '+name)
            source_hashes[name] = sha(raw)
            return raw
        for name, expected in catalog['source_sha256'].items():
            read(name, expected)
        for name in names:
            record = manifest['units'][name]
            if record['definition'] != definitions[name] or not record['assembly_ready']:
                raise ValueError('Unsupported source room: '+name)
            directory = imported/'units'/name
            for filename in ('render.mod','room.mod','room.ini','collision.json'):
                if sha((directory/filename).read_bytes()) != record['output_sha256'][filename]:
                    raise ValueError('Converted unit changed: '+name+'/'+filename)
            units[name] = record['definition']
            original = json.loads((directory/'collision.json').read_bytes())
            rooms[name], navigation[name] = interpret(original, units[name])
            archive = f'user/Mukki/mapunits/arc/{name}/arc.szs'
            members = archive_files(read(archive, manifest['source_sha256'][archive]))
            if 'view.bmd' not in members:
                raise ValueError('Missing source room model')
            sources[name] = members['view.bmd']
    instances, seams = layout(units, rooms,block=block,north=north,cap=cap)
    footprints = cell_audit(instances, units)
    merged = merge_rooms([(rooms[n],units[n],turn,offset) for n,turn,offset in instances], seams)
    # The block north door is the engineering return target. No actor is spawned.
    target_door = next(d for d in units[block]['doors'] if d['id'] == 0)
    target = next(p['position'] for p in rooms[block]['routes'] if p['id'] == target_door['waypoint'])
    navigation_audit = return_audit(merged, target)
    ground = seam_audit(merged, instances, seams, units, rooms)
    output.mkdir(parents=True, exist_ok=False)
    report = write_model(merged_model([(sources[n],turn,offset) for n,turn,offset in instances]),
                         output/'render.mod', f'Beasts floor {floor} engineering assembly')
    (output/'room.mod').write_bytes(attach_collision((output/'render.mod').read_bytes(), merged))
    (output/'room.ini').write_text(route_ini(merged['routes']))
    (output/'collision.json').write_text(json.dumps(merged, indent=2)+'\n')
    report = {k:v for k,v in report.items() if k not in ('source','output')}
    (output/'render.json').write_text(json.dumps(report, indent=2)+'\n')
    result = dict(schema=1, policy=f'P2_BEASTS_FLOOR{floor}_ASSEMBLY_1', cave='forest_1', floor=floor,
        layout=instances, seams=seams, footprints=footprints, seam_audit=ground,
        navigation=navigation_audit, unit_navigation=navigation, render=report,
        source_sha256=source_hashes, catalog_sha256=sha(catalog_raw), import_sha256=sha(manifest_raw),
        output_sha256={name:sha((output/name).read_bytes()) for name in ('render.mod','room.mod','room.ini','collision.json')},
        assembled=True, native_validated=False, native_ready=False, retail_generation=False,
        limitations=[f'Authored two source rooms, one straight corridor and {"two" if len(instances)==5 else "five"} caps; not retail map generation.',
                     'Directed source links preserved; only coincident seam waypoints are merged.',
                     'Engineering return waypoint is not a selected Pod, captain spawn or cave exit.',
                     'Seam-width offline probes and graph paths do not certify native carrying, scenery footprint or camera.',
                     'No actors, treasures, receipts, native launch, floor-four descent or campaign integration.'])
    (output/'assembly.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('iso','catalog','imported','output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    report = build(args.iso, args.catalog, args.imported, args.output)
    print(json.dumps(dict(instances=len(report['layout']), seams=len(report['seams']),
                         samples=sum(len(s['samples']) for s in report['seam_audit']))))
