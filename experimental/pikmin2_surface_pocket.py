"""Local Valley of Repose source preparation, not a playable surface or cropped map."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_cave import tree
from experimental.pikmin2_collision import decode_room, ground_height
from experimental.pikmin2_convert import convert

GEN = 'user/Abe/map/tutorial/'
MAP = 'user/Kando/map/tutorial/'


def vector(values):
    result = list(map(float, values))
    if len(result) != 3 or not all(math.isfinite(x) for x in result):
        raise ValueError('Invalid source generator position')
    return result


def generators(text):
    """Read common source headers; retain actor-specific data without translating it."""
    values = tree(text)
    if len(values) < 6 or values[0] != ['v0.1'] or int(values[5]) != len(values)-6:
        raise ValueError('Unexpected generator manager header/count')
    result = []
    for index, row in enumerate(values[6:]):
        if not isinstance(row, list) or len(row) < 43 or row[0] not in (['v0.1'], ['v0.2'], ['v0.3']):
            raise ValueError('Unsupported generator record')
        label_bytes = bytes(map(int, row[3:35])).split(b'\0')[0]
        position, offset = vector(row[35:38]), vector(row[38:41])
        if not isinstance(row[41], list) or len(row[41]) != 1:
            raise ValueError('Invalid generator kind')
        actor = dict(index=index, label=label_bytes.decode('cp932'), kind=row[41][0],
                     reserved=int(row[1]), respawn_days=int(row[2]), position=position, offset=offset,
                     effective_position=[a+b for a,b in zip(position,offset)])
        if actor['kind'] == 'item':
            body = row[43]
            actor['item'] = body[0][0]
            actor['rotation'] = vector(body[1:4])
            if actor['item'] == 'cave':
                actor.update(cave_file=body[5], units_file=body[6], cave_id=body[7][0])
            if actor['item'] == 'onyn':
                actor.update(onion_index=int(body[5]), after_boot=int(body[6]))
        result.append(actor)
    return dict(header_start=vector(values[1:4]), header_direction=float(values[4]), actors=result)


def prepare_surface(iso, output):
    output.mkdir(parents=True, exist_ok=False)
    catalog = disc_files(iso)
    sources = {}
    with iso.open('rb') as stream:
        def read(name):
            offset, length = catalog[name]
            stream.seek(offset)
            data = stream.read(length)
            sources[name] = hashlib.sha256(data).hexdigest()
            return data
        for archive in ('arc','texts'):
            for name, data in archive_files(read(MAP+archive+'.szs')).items():
                target = output/archive/name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        definitions, errors = {}, []
        for name in sorted(catalog):
            if name.startswith(GEN) and name.endswith('.txt') and not name.endswith('route.txt'):
                data = read(name)
                target = output/'generators'/name[len(GEN):]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                try: definitions[name[len(GEN):]] = generators(data.decode('cp932'))
                except (ValueError, IndexError, TypeError) as error:
                    errors.append(dict(source=name, error=str(error)))
        route = read(GEN+'route.txt')
        (output/'texts/route.txt').write_text(route.decode('cp932'), encoding='utf-8')
    defaults = definitions['defaultgen.txt']['actors']
    entrances = [a for a in defaults if a.get('cave_file') == 'tutorial_1.txt']
    if len(entrances) != 1: raise ValueError('Expected exactly one Emergence entrance')
    entrance = entrances[0]
    blockers = ['Native surface map bootstrap/renderer and entry interaction are not wired.',
                'Surface generator scheduling, obstacles, actors, storage and two-captain state are not restored.',
                'Return anchor is the source cave actor origin; safe party offsets and native return placement remain unvalidated.',
                'Terrain render is the whole source surface, not a bounded or physically sealed pocket.',
                'Static materials approximate TEV; texture animation texanm_1.btk is not implemented.']
    water = tree((output/'texts/waterbox.txt').read_text())
    if water != ['0',['0']]: blockers.append('Source water volumes are retained but not converted; do not treat the whole map as dry.')
    render = {}
    try: render = convert(output/'arc/model.bmd', output/'surface-render.mod', approximate_materials=True)
    except (ValueError, IndexError, KeyError) as error: blockers.append('Static render conversion blocked: '+str(error))
    codes = (output/'texts/mapcode.bin').read_bytes()
    mapcode_inventory = dict(triangles=int.from_bytes(codes[:4], 'big'),
                             material_counts=dict(sorted(Counter(code & 15 for code in codes[4:]).items())))
    if len(codes) != 4 + mapcode_inventory['triangles']:
        raise ValueError('Surface mapcode inventory count mismatch')
    collision = {}
    try:
        room = decode_room(output/'texts')
        (output/'surface-collision.json').write_text(json.dumps(room,indent=2))
        x,y,z = entrance['effective_position']
        collision = dict(triangles=len(room['triangles']), vertices=len(room['vertices']),
                         mapcodes=sorted(set(room['mapcodes'])), bounds=room['bounds'],
                         entrance_ground=ground_height(room['vertices'], room['triangles'],x,z,ceiling=y+10))
    except (ValueError, IndexError, KeyError) as error: blockers.append('Existing dry-room collision decoder blocked: '+str(error))
    result = dict(schema=1, region='valley_of_repose', source_region='tutorial', cave='tutorial_1',
                  source_sha256=sources, definitions=definitions, generator_errors=errors,
                  entrance=entrance, return_anchor=entrance['effective_position'],
                  landing_actors=[a for a in defaults if a.get('item') == 'onyn'],
                  snapshot_contract=dict(region='valley_of_repose', position='capture actual captain position before entering',
                                         fields=['day','time','position','squad','health','receipts']),
                  render=render, collision=collision, mapcode_inventory=mapcode_inventory, water_source=water, blockers=blockers,
                  playable=False, native_validated=False)
    (output/'surface-pocket.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=prepare_surface(args.iso,args.output)
    print(json.dumps(dict(render=bool(result['render']),collision=bool(result['collision']),entrance=result['return_anchor'],blockers=result['blockers'])))
