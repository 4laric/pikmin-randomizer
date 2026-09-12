"""Deterministic authored cave assembly; not a port of P2's random map generator."""
import argparse
import copy
import json
import math
from pathlib import Path
import struct

from experimental.pikmin2_cave import route_audit
from experimental.pikmin2_collision import attach_collision, ground_height, route_ini
from experimental.pikmin2_convert import decode, texture_layout, u16, u32, unpack, write_model


def transform(point, turn, offset=(0,0,0)):
    if turn not in range(4) or len(point)!=3 or len(offset)!=3:
        raise ValueError('Expected quarter-turn and three-dimensional coordinates')
    if not all(math.isfinite(v) for v in (*point,*offset)):
        raise ValueError('Nonfinite transform')
    x,y,z=point
    for _ in range(turn): x,z=-z,x
    # Preserve signed zeros for identity transforms and byte-stable single units.
    return [v+d if d else v for v,d in zip((x,y,z),offset)]


def merged_model(instances):
    arrays={}; shapes=[]; materials=[]; textures=[]
    for model,turn,offset in instances:
        blocks,attrs,meshes,mats=decode(model,True)
        attr_offsets={k:len(arrays.get(k,[])) for k in attrs}
        for attr,values in attrs.items():
            if attr==9: values=[transform(v,turn,offset) for v in values]
            if attr==10: values=[transform(v,turn) for v in values]
            arrays.setdefault(attr,[]).extend(values)
        shapes.extend([[[{a:i+attr_offsets[a] for a,i in v.items()} for v in tri] for tri in mesh] for mesh in meshes])
        tex_offset=len(textures)
        materials.extend(tex_offset+i if i>=0 else -1 for i in mats)
        tex=blocks['TEX1']
        for i in range(u16(tex,8)):
            at=u32(tex,12)+32*i; header=bytearray(tex[at:at+32])
            _,size=texture_layout(header[0],*unpack(header,'HH',2))
            start=at+u32(header,28)
            if start+size>len(tex): raise ValueError('Truncated scene texture')
            header[24]=1 # base mip only, as in the standalone converter
            textures.append((header,tex[start:start+size]))
    if not instances or len(arrays.get(9,[]))>65535:
        raise ValueError('Empty scene or vertex index limit exceeded')
    # Build the TEX1 fields used by the shared writer; preserve per-texture sampling.
    tex=bytearray(32+32*len(textures)); tex[:4]=b'TEX1'
    struct.pack_into('>H',tex,8,len(textures));struct.pack_into('>I',tex,12,32)
    for i,(header,data) in enumerate(textures):
        at=32+32*i;struct.pack_into('>I',header,28,len(tex)-at)
        tex[at:at+32]=header;tex.extend(data)
    struct.pack_into('>I',tex,4,len(tex))
    return {'TEX1':bytes(tex)},arrays,shapes,materials


def merge_rooms(instances, seams):
    """Transform collision/placements and join only explicitly matched door nodes."""
    out=dict(vertices=[],triangles=[],mapcodes=[],routes=[],spawns=[])
    doors={}; maps=[]
    for index,(room,definition,turn,offset) in enumerate(instances):
        first=len(out['vertices'])
        out['vertices'].extend(transform(p,turn,offset) for p in room['vertices'])
        out['triangles'].extend([v+first for v in tri] for tri in room['triangles'])
        out['mapcodes'].extend(room['mapcodes'])
        mapping={p['id']:len(out['routes'])+i for i,p in enumerate(room['routes'])}; maps.append(mapping)
        for p in room['routes']:
            out['routes'].append(dict(id=mapping[p['id']],position=transform(p['position'],turn,offset),
                                      radius=p['radius'],links=[mapping[i] for i in p['links']]))
        for spawn in room['spawns']:
            p=copy.deepcopy(spawn);p['position']=transform(p['position'],turn,offset)
            p['angle']=(p['angle']-90*turn)%360;p['instance']=index
            out['spawns'].append(p)
        for door in definition['doors']:
            doors[index,door['id']]=dict(route=mapping[door['waypoint']],direction=(door['direction']+turn)%4)
    parent=list(range(len(out['routes'])));used=set()
    def root(i):
        while i!=parent[i]: i=parent[i]
        return i
    for left,right in seams:
        left,right=tuple(left),tuple(right)
        if left==right or left in used or right in used or left not in doors or right not in doors:
            raise ValueError('Missing or reused seam door')
        a,b=doors[left],doors[right];p,q=out['routes'][a['route']],out['routes'][b['route']]
        if (a['direction']-b['direction'])%4!=2 or math.dist(p['position'],q['position'])>0.01:
            raise ValueError('Seam doors do not coincide and face each other')
        parent[root(b['route'])]=root(a['route']);used.update((left,right))
    if set(doors)!=used: raise ValueError('Assembly has unsealed doors')
    groups={}
    for p in out['routes']: groups.setdefault(root(p['id']),[]).append(p)
    ids={old:i for i,group in enumerate(groups.values()) for old in [p['id'] for p in group]}
    routes=[]
    for i,group in enumerate(groups.values()):
        links={ids[other] for p in group for other in p['links']}-{i}
        routes.append(dict(id=i,position=group[0]['position'],radius=min(p['radius'] for p in group),links=sorted(links)))
    out['routes']=routes
    out['bounds']={label:[fn(v[i] for v in out['vertices']) for i in range(3)] for label,fn in [('min',min),('max',max)]}
    route_ini(routes)
    return out


def build(imported, output):
    manifest=json.loads((imported/'manifest.json').read_text())
    if manifest['schema']!=1 or manifest['cave']!='tutorial_1': raise ValueError('Expected Emergence import')
    # Two 5x5 rooms (850 units), joined by one 170-unit straight connector.
    # Rotation is around each source unit's center. This layout is authored.
    layout=[('room_north_tutorial_1_snow',0,[0,0,0]),
            ('way2_snow',0,[0,0,510]),
            ('room_north_tutorial_1_snow',2,[0,0,1020])]
    collision=[]; models=[]
    for name,turn,offset in layout:
        if name not in manifest['floors'][0]['unit_candidates']: raise ValueError('Unit not in floor pool')
        directory=imported/'units'/name
        room=json.loads((directory/'collision.json').read_text())
        collision.append((room,manifest['units'][name]['definition'],turn,offset))
        models.append(((directory/'arc/view.bmd').read_bytes(),turn,offset))
    seams=[((0,0),(1,0)),((1,1),(2,0))]
    room=merge_rooms(collision,seams)
    audit=route_audit(room)
    if any(r['unreachable_sources'] for r in audit): raise ValueError('Disconnected assembled routes')
    # Sample a carry-width strip through both seams, including each side.
    probes=[]
    for z in range(350,671,5):
        for x in (-30,0,30):
            y=ground_height(room['vertices'],room['triangles'],x,z)
            if y is None or abs(y)>0.05: raise ValueError(f'Broken seam ground at {x},{z}: {y}')
            probes.append([x,y,z])
    output.mkdir(parents=True,exist_ok=False)
    report=write_model(merged_model(models),output/'render.mod','authored Emergence floor 1')
    (output/'room.mod').write_bytes(attach_collision((output/'render.mod').read_bytes(),room))
    (output/'room.ini').write_text(route_ini(room['routes']))
    (output/'collision.json').write_text(json.dumps(room,indent=2))
    result=dict(schema=1,cave='tutorial_1',floor=1,layout=layout,seams=seams,assembled=True,native_validated=False,
                source_sha256=manifest['source_sha256'],
                layout_policy='authored deterministic engineering layout; not original P2 generation',
                geometry=report,route_audit=audit,seam_probes=probes,
                limitations=manifest['limitations'][1:])
    (output/'assembly.json').write_text(json.dumps(result,indent=2))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--imported',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=build(args.imported,args.output)
    print(json.dumps(dict(triangles=result['geometry']['triangles'],seam_samples=len(result['seam_probes']))))
