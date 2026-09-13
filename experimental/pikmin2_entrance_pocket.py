"""Original-geometry Emergence entrance subset; no native travel/water enforcement."""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path

from experimental.pikmin2_collision import adjacency, attach_collision, ground_height
from experimental.pikmin2_surface_physics import in_water, surface_mapcode

CENTER = [-190., 80., 1160.]
TRAVEL_RADIUS = 60.
SELECTION_HALF_WIDTH = 100.


def subset(room, center=CENTER, half_width=SELECTION_HALF_WIDTH):
    if len(center)!=3 or not all(math.isfinite(v) for v in center) or not math.isfinite(half_width) or half_width<=0:
        raise ValueError('Invalid subset bounds')
    vertices, triangles = room['vertices'],room['triangles']
    selected=[]
    for i,tri in enumerate(triangles):
        points=[vertices[v] for v in tri]
        # Conservative complete-triangle selection, no cutting or replacement faces.
        if all(max(p[axis] for p in points)>=center[axis]-half_width and
               min(p[axis] for p in points)<=center[axis]+half_width for axis in (0,2)):
            selected.append(i)
    if not selected: raise ValueError('Empty entrance subset')
    edges=defaultdict(list)
    for i,tri in enumerate(triangles):
        for j in range(3):edges[tuple(sorted((tri[j],tri[(j+1)%3])))].append(i)
    ambiguous={i for ids in edges.values() if len(ids)>2 for i in ids}
    if ambiguous.intersection(selected):
        raise ValueError('Subset touches source nonmanifold topology')
    source_vertices=sorted({v for i in selected for v in triangles[i]})
    remap={v:i for i,v in enumerate(source_vertices)}
    result=dict(vertices=[vertices[i][:] for i in source_vertices],
                triangles=[[remap[v] for v in triangles[i]] for i in selected],
                mapcodes=[room['mapcodes'][i] for i in selected],routes=[],
                source_triangle_ids=selected,source_vertex_ids=source_vertices,
                bounds={label:[fn(vertices[v][axis] for v in source_vertices) for axis in range(3)]
                        for label,fn in [('min',min),('max',max)]})
    adjacency(result['triangles'])
    return result


def validate_probes(source, pocket, boxes):
    samples={(0.,0.)}
    for x in range(-60,61,10):
        for z in range(-60,61,10):
            if x*x+z*z<=TRAVEL_RADIUS**2:samples.add((float(x),float(z)))
    for i in range(72):
        angle=i*math.pi/36
        samples.add((TRAVEL_RADIUS*math.cos(angle),TRAVEL_RADIUS*math.sin(angle)))
    result=[]
    for dx,dz in sorted(samples):
        x,z=CENTER[0]+dx,CENTER[2]+dz
        original=ground_height(source['vertices'],source['triangles'],x,z,ceiling=90)
        converted=ground_height(pocket['vertices'],pocket['triangles'],x,z,ceiling=90)
        if original is None or converted is None or abs(original-converted)>1e-6:
            raise ValueError('Source/subset ground mismatch or missing floor')
        if any(in_water(b,[x,original,z],10.) for b in boxes):
            raise ValueError('Declared travel probe overlaps source water')
        result.append(dict(position=[x,original,z],source_height=original,subset_height=converted,water=False))
    return result


def prepare(source_import, physics, output):
    source=json.loads((physics/'surface-collision.json').read_text())
    water_bytes=(physics/'surface-water.json').read_bytes()
    water=json.loads(water_bytes)
    if water.get('schema')!=1 or len(water.get('boxes',[]))!=3:
        raise ValueError('Expected all three source water boxes')
    origin=json.loads((source_import/'surface-pocket.json').read_text(encoding='utf-8'))
    if origin.get('source_region')!='tutorial' or origin.get('return_anchor')!=CENTER:
        raise ValueError('Expected source Emergence entrance anchor')
    pocket=subset(source)
    probes=validate_probes(source,pocket,water['boxes'])
    render=(source_import/'surface-render.mod').read_bytes()
    mod=attach_collision(render,pocket,mapcode_translator=surface_mapcode)
    output.mkdir(parents=True,exist_ok=False)
    (output/'entrance-pocket.mod').write_bytes(mod)
    (output/'entrance-collision.json').write_text(json.dumps(pocket,indent=2))
    (output/'surface-water.json').write_bytes(water_bytes)
    report=dict(schema=1,region='valley_of_repose',source_anchor=CENTER,travel_radius=TRAVEL_RADIUS,
                selection_half_width=SELECTION_HALF_WIDTH,selection_policy='whole-triangle XZ AABB overlap',
                source_triangle_ids=pocket['source_triangle_ids'],source_vertex_ids=pocket['source_vertex_ids'],
                triangles=len(pocket['triangles']),vertices=len(pocket['vertices']),probes=probes,
                native_mod_written=True,playable=False,terrain_usable_alone=False,
                mandatory_water_sidecar='surface-water.json',native_boundary_implemented=False,
                crop_boundary_sealed=False,render_policy='unaltered whole source surface; outside terrain visible but unsupported',
                requires=['Native physical travel-radius boundary and independent water consumer.',
                          'Native surface captain/party bootstrap, entry/return interaction and playtesting.',
                          'Carry routes are omitted; this is a local walking/entry pocket only.'],
                source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                               (source_import/'surface-render.mod',physics/'surface-collision.json',physics/'surface-water.json')})
    (output/'entrance-pocket.json').write_text(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-import',type=Path,required=True)
    parser.add_argument('--physics',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report=prepare(args.source_import,args.physics,args.output)
    print(json.dumps(dict(triangles=report['triangles'],vertices=report['vertices'],probes=len(report['probes']),playable=False)))
