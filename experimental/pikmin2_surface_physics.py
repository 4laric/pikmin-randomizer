"""Valley-only static terrain and source water sidecar; requires native water support."""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path

from experimental.pikmin2_cave import tree
from experimental.pikmin2_collision import attach_collision, decode_room, ground_height


VALLEY_ATTRIBUTES = frozenset((0, 1, 3, 5, 6, 7, 9))


def surface_mapcode(code):
    # P2 navi.cpp consumes this nibble as a walk sound, overridden by inWater().
    # P2 water comes from SeaMgr, never from material3/9. Preserve slope/bald bits.
    if type(code) is not int or not 0 <= code < 128 or code & 15 not in VALLEY_ATTRIBUTES:
        raise ValueError('Unaudited Valley material/flags')
    return (((code >> 4) & 3) << 27) | ((not (code & 64)) << 25)


def water_boxes(text):
    nodes = tree(text)
    if len(nodes) != 2 or nodes[0] != '0' or not isinstance(nodes[1], list) or not nodes[1]:
        raise ValueError('Unsupported water structure/version')
    count = int(nodes[1][0])
    values = nodes[1][1:]
    if not 0 <= count <= 128 or len(values) != count*6:
        raise ValueError('Invalid water box count')
    boxes = []
    for i in range(count):
        row = list(map(float, values[i*6:i*6+6]))
        if not all(math.isfinite(v) for v in row) or any(row[j] >= row[j+3] for j in range(3)):
            raise ValueError('Invalid water box bounds')
        boxes.append(dict(id=i, min=row[:3], max=row[3:], surface=row[4],
                          runtime_min_y=row[1]-1000., lowered_amount=0.))
    return boxes


def in_water(box, position, radius=0.):
    """Source AABBWaterBox::inWater: XZ sphere overlap, centre Y <= top-3.

    Deliberately no lower-Y cutoff: the source predicate does not test one.
    """
    if (len(position) != 3 or not all(math.isfinite(v) for v in position)
            or not math.isfinite(radius) or radius < 0):
        raise ValueError('Invalid water probe')
    x,y,z = position
    return (y <= box['surface']-3 and x+radius >= box['min'][0] and x-radius <= box['max'][0]
            and z+radius >= box['min'][2] and z-radius <= box['max'][2])


def probe(room, boxes, position):
    x,y,z = position
    floor = ground_height(room['vertices'],room['triangles'],x,z,ceiling=y+10)
    return dict(position=position, ground=floor,
                at_anchor=[b['id'] for b in boxes if in_water(b,position)],
                at_ground=None if floor is None else [b['id'] for b in boxes if in_water(b,[x,floor,z])])


def convert_surface(imported, output):
    manifest = json.loads((imported/'surface-pocket.json').read_text(encoding='utf-8'))
    if manifest.get('schema') != 1 or manifest.get('source_region') != 'tutorial':
        raise ValueError('Expected Valley source inventory')
    boxes = water_boxes((imported/'texts/waterbox.txt').read_text())
    if len(boxes) != 3: raise ValueError('Expected three Valley source water volumes')
    # Optional translation policy never changes the dry-room default.
    room = decode_room(imported/'texts', mapcode_translator=surface_mapcode)
    edges = defaultdict(list)
    for index, triangle in enumerate(room['triangles']):
        for edge in range(3):
            edges[tuple(sorted((triangle[edge],triangle[(edge+1)%3])))].append(index)
    nonmanifold = [dict(vertices=list(edge), triangles=ids) for edge,ids in edges.items() if len(ids)>2]
    output.mkdir(parents=True,exist_ok=False)
    mod_written = False
    if not nonmanifold:
        mod = attach_collision((imported/'surface-render.mod').read_bytes(), room,
                               mapcode_translator=surface_mapcode)
        (output/'surface-terrain.mod').write_bytes(mod)
        mod_written = True
    (output/'surface-collision.json').write_text(json.dumps(room,indent=2))
    water = dict(schema=1, source='Game::SeaMgr/AABBWaterBox', boxes=boxes,
                 query='xz_sphere_overlap_and_center_y_le_surface_minus_3_no_bottom_test',
                 dynamic_lowering_supported=False, native_consumer_implemented=False)
    (output/'surface-water.json').write_text(json.dumps(water,indent=2))
    anchors = {'emergence':manifest['return_anchor']}
    for actor in manifest['landing_actors']:
        anchors[f'onion_{actor["index"]}'] = actor['effective_position']
    probes = {name:probe(room,boxes,pos) for name,pos in anchors.items()}
    for box in boxes:
        center=[(box['min'][0]+box['max'][0])/2,box['surface'],(box['min'][2]+box['max'][2])/2]
        probes[f'water_{box["id"]}_center']=probe(room,boxes,center)
        for side in (-1,1):
            pos=[box['min'][0]+side,box['surface']-4,center[2]]
            probes[f'water_{box["id"]}_shore_{side}']=probe(room,boxes,pos)
    sources = {str(path.relative_to(imported)):hashlib.sha256(path.read_bytes()).hexdigest()
               for path in [imported/'surface-render.mod',imported/'texts/grid.bin',imported/'texts/mapcode.bin',
                            imported/'texts/route.txt',imported/'texts/waterbox.txt']}
    report=dict(schema=1,source_sha256=sources,triangles=len(room['triangles']),vertices=len(room['vertices']),
                water_volumes=len(boxes),probes=probes,playable=False,
                native_mod_written=mod_written,nonmanifold_edges=nonmanifold,
                mandatory_water_sidecar='surface-water.json',terrain_usable_alone=False,
                requires=['Source nonmanifold-edge adjacency policy is required before native MOD output.' if nonmanifold else 'Native geometry validation.',
                          'Native independent water query, drowning/effects and water render integration.',
                          'Source water lowering from drain actor remains unsupported.',
                          'Surface actor/entry/return bootstrap and performance validation.'],
                warning='Terrain MOD alone has no water semantics; never launch it as a complete dry surface.')
    (output/'surface-physics.json').write_text(json.dumps(report,indent=2))
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--imported',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report=convert_surface(args.imported,args.output)
    print(json.dumps({k:report[k] for k in ('triangles','vertices','water_volumes','playable')}))
