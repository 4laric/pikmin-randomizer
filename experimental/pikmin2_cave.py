"""Local-only Emergence Cave asset inventory and static unit conversion.

This reads definitions, not a final spawn list or the P2 random map algorithm.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_collision import attach_collision, decode_room, ground_height, route_ini
from experimental.pikmin2_convert import convert, decode

BASE = 'user/Mukki/mapunits'
CAVE = BASE + '/caveinfo/tutorial_1.txt'


def tree(text):
    """Parse the comment-bearing brace stream without relying on translated comments."""
    tokens = iter(re.findall(r'[{}]|[^\s{}]+', '\n'.join(line.split('#')[0] for line in text.splitlines())))
    def block(nested=False):
        result = []
        for token in tokens:
            if token == '}':
                if not nested:
                    raise ValueError('Unexpected closing brace')
                return result
            result.append(block(True) if token == '{' else token)
        if nested:
            raise ValueError('Unclosed definition block')
        return result
    return block()


def parameters(values):
    result = {}
    while values:
        key, *values = values
        if not isinstance(key, list) or len(key) != 1:
            raise ValueError('Expected parameter identifier')
        if key == ['_eof']:
            if values:
                raise ValueError('Trailing parameter data')
            return result
        if len(values) < 2 or key[0] in result:
            raise ValueError('Incomplete or duplicate parameter')
        size, value, *values = values
        if size not in ('4', '-1'):
            raise ValueError('Unsupported parameter type')
        result[key[0]] = value
    raise ValueError('Missing parameter terminator')


def weighted(values, width):
    count = int(values[0])
    if count < 0 or len(values) != 1 + count * width:
        raise ValueError('Invalid weighted roster count')
    return [values[1+i*width:1+(i+1)*width] for i in range(count)]


def cave_definition(text):
    nodes = tree(text)
    if len(nodes) < 2:
        raise ValueError('Missing cave header')
    header = parameters(nodes[0]); count = int(nodes[1])
    if count != int(header['c000']) or count <= 0 or len(nodes) != 2+5*count:
        raise ValueError('Inconsistent floor count')
    floors = []
    for i in range(count):
        params, enemies, items, gates, caps = nodes[2+5*i:7+5*i]
        params = parameters(params)
        if int(params['f000']) != i or int(params['f001']) != i:
            raise ValueError('Only individual authored floor definitions supported')
        if gates != ['0'] or caps != ['0']:
            raise ValueError('Gate/cap rosters not yet supported')
        floors.append(dict(number=i+1, parameters=params,
                           enemies=[dict(id=a, packed_weight=int(b), placement_type=int(c)) for a,b,c in weighted(enemies,3)],
                           treasures=[dict(id=a, packed_weight=int(b)) for a,b in weighted(items,2)]))
    return floors


def safe_name(name):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', name) or name in ('.', '..'):
        raise ValueError('Unsafe asset name')
    return name


def unit_definition(text):
    nodes = tree(text)
    if not nodes or int(nodes[0]) != len(nodes)-1:
        raise ValueError('Invalid unit count')
    result = []
    for row in nodes[1:]:
        if len(row) < 8 or row[0] != '1':
            raise ValueError('Unsupported unit definition')
        name = safe_name(row[1]); width, depth, kind, flag0, flag1, count = map(int,row[2:8])
        if min(width,depth) <= 0 or count < 0:
            raise ValueError('Invalid unit dimensions or doors')
        doors=[]; cursor=8
        for _ in range(count):
            if cursor+5 > len(row):
                raise ValueError('Truncated door')
            index,direction,offset,waypoint,links = map(int,row[cursor:cursor+5]); cursor+=5
            if direction not in range(4) or links < 0 or cursor+3*links > len(row):
                raise ValueError('Invalid door links')
            peers=[]
            for _ in range(links):
                distance,other,teki = row[cursor:cursor+3]; cursor+=3
                distance=float(distance)
                if not math.isfinite(distance) or distance < 0:
                    raise ValueError('Invalid door distance')
                peers.append(dict(distance=distance,door=int(other),enemy_flag=int(teki)))
            doors.append(dict(id=index,direction=direction,offset=offset,waypoint=waypoint,links=peers))
        if cursor != len(row) or sorted(d['id'] for d in doors) != list(range(count)):
            raise ValueError('Invalid door framing')
        if any(link['door'] not in range(count) for d in doors for link in d['links']):
            raise ValueError('Missing linked door')
        result.append(dict(name=name,cells=[width,depth],kind=kind,flags=[flag0,flag1],doors=doors))
    if len({u['name'] for u in result}) != len(result):
        raise ValueError('Duplicate unit')
    return result


def route_audit(room):
    routes = {p['id']:p for p in room['routes']}
    result = []
    for destination in routes:
        reachable={destination}
        while True:
            more={i for i,p in routes.items() if any(j in reachable for j in p['links'])}
            if more <= reachable:
                break
            reachable |= more
        result.append(dict(destination=destination,unreachable_sources=sorted(set(routes)-reachable)))
    return result


def import_emergence(iso, output):
    """Refuse reuse so failed imports cannot masquerade as a previous successful run."""
    output = output.resolve()
    output.mkdir(parents=True,exist_ok=False)
    catalog=disc_files(iso); hashes={}
    with iso.open('rb') as disc:
        def read(name):
            offset,size=catalog[name]; disc.seek(offset); data=disc.read(size)
            if len(data)!=size:
                raise ValueError('Truncated disc asset')
            hashes[name]=hashlib.sha256(data).hexdigest()
            return data
        floors=cave_definition(read(CAVE).decode('shift_jis')); units={}
        for floor in floors:
            filename=safe_name(floor['parameters']['f008'])
            definitions=unit_definition(read(BASE+'/units/'+filename).decode('shift_jis'))
            floor['unit_candidates']=[u['name'] for u in definitions]
            for definition in definitions:
                name=definition['name']
                if name in units:
                    if units[name]['definition']!=definition:
                        raise ValueError('Inconsistent shared unit definition')
                    continue
                directory=output/'units'/name
                for archive in ('arc','texts'):
                    for filename,data in archive_files(read(f'{BASE}/arc/{name}/{archive}.szs')).items():
                        target=directory/archive/filename
                        target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data)
                # Water is a separate volume system. Lane 49 parses the volume
                # and stores it; it no longer refuses wet rooms. Imported lazily to
                # avoid the pikmin2_cave <-> pikmin2_surface_physics import cycle.
                from experimental.pikmin2_cave_water import water_unit_sidecar
                water=water_unit_sidecar((directory/'texts/waterbox.txt').read_text())
                (directory/'water.json').write_text(json.dumps(water,indent=2)+'\n',encoding='utf-8')
                room=decode_room(directory/'texts')
                if any(d['waypoint'] not in {p['id'] for p in room['routes']} for d in definition['doors']):
                    raise ValueError('Door references a missing route waypoint')
                report=convert(directory/'arc/view.bmd',directory/'render.mod',approximate_materials=True)
                (directory/'room.mod').write_bytes(attach_collision((directory/'render.mod').read_bytes(),room))
                (directory/'room.ini').write_text(route_ini(room['routes']),encoding='utf-8')
                (directory/'collision.json').write_text(json.dumps(room,indent=2),encoding='utf-8')
                _,arrays,shapes,_=decode((directory/'arc/view.bmd').read_bytes(),True)
                render_triangles=[[v[9] for v in tri] for shape in shapes for tri in shape]
                probes=[]
                for spawn in room['spawns']:
                    x,y,z=spawn['position']; ground=ground_height(room['vertices'],room['triangles'],x,z)
                    # Ignore overhead scenery when comparing the local floor.
                    visual=ground_height(arrays[9],render_triangles,x,z,ceiling=ground+10) if ground is not None else None
                    probes.append(dict(type=spawn['type'],position=spawn['position'],ground=ground,
                                       delta=None if ground is None else y-ground,render_ground=visual,
                                       render_collision_delta=None if visual is None or ground is None else visual-ground))
                audit=route_audit(room)
                starts=[p for p in room['spawns'] if p['type']==7]
                start_routes=[min(room['routes'],key=lambda p:sum((p['position'][i]-s['position'][i])**2 for i in (0,2)))['id'] for s in starts]
                units[name]=dict(definition=definition,water=water,render={k:v for k,v in report.items() if k not in ('source','output')},
                                 collision_triangles=len(room['triangles']),source_mapcodes=sorted(set(room['mapcodes'])),
                                 route_audit=audit,start_destination_audit=[row for row in audit if row['destination'] in start_routes],
                                 spawn_candidates=room['spawns'],ground_probes=probes,
                                 deferred_animations=[p.name for p in (directory/'arc').glob('*.btk')])
        manifest=dict(schema=1,cave='tutorial_1',disc='GPVE01 revision 0',floors=floors,units=units,
                      source_sha256=hashes,assembled=False,native_validated=False,
                      limitations=['Unit candidates are not an assembled floor or final actor placements.',
                                   'Static first-texture materials; extra UV/color channels and texture animation omitted.',
                                   'Base texture mip only; P2 footstep/impact materials approximated as solid.',
                                   'No Research Pod, floor transitions, Purple Pikmin or campaign saves yet.'])
        (output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); manifest=import_emergence(args.iso,args.output)
    print(json.dumps(dict(floors=len(manifest['floors']),units=len(manifest['units']),manifest=str(args.output/'manifest.json'))))
