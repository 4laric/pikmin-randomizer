"""Selected authored Emergence content on existing source-unit geometry.

This is an explicit deterministic authoring policy, not original P2 map RNG.
No P1 generator, proxy actor, treasury receipt or gameplay authority is produced.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_assembly import merge_rooms, transform
from experimental.pikmin2_cave import BASE
from experimental.pikmin2_collision import decode_room, ground_height
from experimental.pikmin2_retail_context import authenticate

POLICY = 'authored-emergence-source-slots/1'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def prepare(catalog, iso, source, imported, assembled, floor, output):
    if floor not in (1, 2):
        raise ValueError('Emergence has two floors')
    context = authenticate(catalog, iso, source)
    cave = context['caves'][0]
    definition = cave['floors'][floor-1]
    inventory = json.loads((imported/'manifest.json').read_bytes())
    if inventory['cave'] != cave['cave_id']:
        raise ValueError('Imported cave identity differs')
    layout = [('room_north_tutorial_1_snow',0,[0,0,0]),('way2_snow',0,[0,0,510]),
              ('room_north_tutorial_1_snow',2,[0,0,1020])] if floor == 1 else [
                  ('room_purple14x14_snow',0,[0,0,0])]
    files = disc_files(iso)
    instances = []
    with iso.open('rb') as stream:
        for name, turn, offset in layout:
            if name not in inventory['floors'][floor-1]['unit_candidates']:
                raise ValueError('Unit outside source floor pool')
            for kind in ('arc', 'texts'):
                member = f'{BASE}/arc/{name}/{kind}.szs'
                at, size = files[member]
                stream.seek(at)
                raw = stream.read(size)
                if len(raw) != size or hashlib.sha256(raw).hexdigest() != inventory['source_sha256'][member]:
                    raise ValueError('Source unit archive differs')
                for relative, data in archive_files(raw).items():
                    if (imported/'units'/name/kind/relative).read_bytes() != data:
                        raise ValueError('Extracted source unit member differs')
            room = decode_room(imported/'units'/name/'texts')
            instances.append((room, inventory['units'][name]['definition'], turn, offset))
    room = merge_rooms(instances, [((0,0),(1,0)),((1,1),(2,0))] if floor == 1 else [])
    geometry = assembled if floor == 1 else imported/'units'/layout[0][0]
    expected = json.loads((geometry/'collision.json').read_bytes())
    # merge_rooms annotates source spawns and computes bounds; compare actual
    # terrain/routes, not optional provenance fields of the imported JSON.
    for key in ('vertices','triangles','mapcodes','routes'):
        if room[key] != expected[key]:
            raise ValueError('Selected geometry differs: '+key)
    slots = []
    for unit, (original, _, turn, offset) in enumerate(instances):
        for index, slot in enumerate(original['spawns']):
            slots.append(dict(unit=unit, index=index, source=copy.deepcopy(slot),
                              position=transform(slot['position'],turn,offset),
                              yaw=(slot['angle']-90*turn)%360))
    def selected(kind):
        # Keep first-floor combat/cargo in the second room using its actual
        # transformed slots, preserving the source entrance room for the squad.
        return [s for s in slots if s['source']['type']==kind and (floor==2 or s['unit']==2)]
    allocations = {}
    for row_index, row in enumerate(definition['rows']):
        count = row['source_weight'] if row['placement_type']==6 else row['source_weight']//10
        if row['placement_type']!=6 and row['source_weight']%10:
            raise ValueError('Weighted selection unsupported')
        allocations.setdefault(row['placement_type'], []).extend((row_index, ordinal) for ordinal in range(count))
    actors = []
    for kind, identities in allocations.items():
        candidates = selected(kind)
        if not candidates:
            raise ValueError('Missing source placement kind')
        counts = [0]*len(candidates)
        remaining = len(identities)
        for i, candidate in enumerate(candidates):
            count = min(candidate['source']['min'], remaining)
            counts[i] = count
            remaining -= count
        for i, candidate in enumerate(candidates):
            extra = min(candidate['source']['max']-counts[i], remaining)
            counts[i] += extra
            remaining -= extra
        if remaining:
            raise ValueError('Source slots cannot hold complete roster')
        cursor = 0
        for candidate, count in zip(candidates, counts):
            for member in range(count):
                row_index, ordinal = identities[cursor]
                row = definition['rows'][row_index]
                position = list(candidate['position'])
                radius = candidate['source']['radius']*.5 if count>1 else 0
                angle = 2*math.pi*member/count
                position[0] += math.cos(angle)*radius
                position[2] += math.sin(angle)*radius
                ground = ground_height(room['vertices'], room['triangles'],position[0],position[2])
                if ground is None:
                    raise ValueError('Selected source actor lacks collision ground')
                instance = f'tutorial_1:floor{floor}:{row["kind"]}:{row["index"]}:{ordinal}'
                actors.append(dict(row=row_index,ordinal=ordinal,instance=instance,source_id=row['source_id'],
                                   catalog_id=row['catalog_id'],unit=candidate['unit'],slot=candidate['index'],
                                   source_position=candidate['position'],position=position,yaw=candidate['yaw'],
                                   group_member=member,group_count=count,ground_probe=ground,
                                   ground_projection='native factory owns actual map query; authored height retained'))
                cursor += 1
    start = next(s for s in slots if s['source']['type']==7 and s['unit']==0)
    exit_slot = selected(4)[0]
    result = dict(schema=1,policy=POLICY,cave='tutorial_1',floor=floor,max_floor=2,
                  source=cave['source'],source_sha256=cave['source_sha256'],catalog_sha256=context['catalog_sha256'],
                  layout=layout,geometry_sha256=hashlib.sha256((geometry/'room.mod').read_bytes()).hexdigest(),
                  routes_sha256=hashlib.sha256((geometry/'room.ini').read_bytes()).hexdigest(),
                  actors=actors,pod=start,exit=dict(exit_slot,kind='hole' if floor==1 else 'geyser'),
                  native_ready=False,retail_rng=False,
                  limitations=['Authored selection from original slots; not original random-map generation.',
                               'Static converted materials do not reproduce original animated TEV.',
                               'Ground probes do not establish native movement, combat, carrying or SAVE acceptance.'])
    result['audit_sha256'] = hashlib.sha256(canonical(result)).hexdigest()
    words = ['P2_RETAIL_FLOOR_1', result['cave'], str(floor), result['source_sha256'],
             result['catalog_sha256'], result['geometry_sha256'], result['routes_sha256'],
             'actors', str(len(actors))]
    native = ' '.join(words)+'\n'
    for actor in actors:
        native += 'actor '+str(actor['row'])+' '+str(actor['ordinal'])+' '+actor['instance']+' '+\
                  str(actor['unit'])+' '+str(actor['slot'])+' '+\
                  ' '.join(format(v,'.9g') for v in (*actor['position'],actor['yaw']))+'\n'
    for name, anchor in (('pod', start), ('exit', exit_slot)):
        native += name+' '+str(anchor['unit'])+' '+str(anchor['index'])+' '+\
                  ' '.join(format(v,'.9g') for v in (*anchor['position'],anchor['yaw']))+'\n'
    native += 'transition '+('hole' if floor==1 else 'geyser')+'\n'
    result['layout_sha256'] = hashlib.sha256(native.encode('ascii')).hexdigest()
    output.mkdir(parents=True,exist_ok=False)
    (output/'floor.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    (output/'p2-retail-floor.txt').write_bytes(native.encode('ascii'))
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('catalog','iso','source','imported','assembled','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--floor',type=int,choices=(1,2),required=True)
    a=p.parse_args()
    result=prepare(a.catalog,a.iso,a.source,a.imported,a.assembled,a.floor,a.output)
    print(json.dumps(dict(floor=a.floor,actors=len(result['actors']),layout_sha256=result['layout_sha256'],native_ready=False)))
