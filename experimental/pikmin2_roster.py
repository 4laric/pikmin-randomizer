"""Opt-in complete treasure/enemy roster on the standalone engineering rooms."""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct

from experimental.pikmin2_collision import ground_height
from scripts.preview_pikmin2_room import generator, records

POLICY = 'P2_ENGINEERING_ROSTER_2'


def placements(room, actors, kind):
    """Deterministic engineering selections, explicitly not retail RNG positions."""
    slots=[(i,s) for i,s in enumerate(room['spawns']) if s['type']==kind]
    if not slots: raise ValueError('Missing source placement candidates')
    if kind==2:
        if len(actors)>len(slots): raise ValueError('Insufficient treasure slots')
        counts=[1 if i<len(actors) else 0 for i in range(len(slots))]
    else:
        counts=[s['min'] for _,s in slots]
        if sum(counts)>len(actors): raise ValueError('Roster below minimum source groups')
        for i,(_,slot) in enumerate(slots):
            counts[i]+=min(slot['max']-counts[i],len(actors)-sum(counts))
        if sum(counts)!=len(actors): raise ValueError('Roster exceeds source group capacity')
    result=[];cursor=0
    for (index,slot),count in zip(slots,counts):
        for member in range(count):
            x,y,z=slot['position']
            # Nonzero group radius permits a deliberately fixed offset. Single
            # actors stay at the source center; no hidden random reroll on reload.
            distance=slot['radius']*.5 if count>1 else 0
            angle=2*math.pi*member/count
            x+=math.cos(angle)*distance;z+=math.sin(angle)*distance
            ground=ground_height(room['vertices'],room['triangles'],x,z)
            if ground is None: raise ValueError('Roster actor has no collision ground')
            result.append(dict(actors[cursor],source_slot=index,source_position=list(slot['position']),
                               source_radius=slot['radius'],source_angle=slot['angle'],
                               position=[x,ground,z],angle=slot['angle'],
                               ground_projection_delta=ground-y,group_member=member))
            cursor+=1
    return result


def audit(room, actors, floor):
    """Bounded clearance/route probes, not native swept-path proof."""
    fixtures=([(0,-100,60),(-85,0,45),(80,-100,45),(170,170,45)] if floor==1 else
              [(-680,595,60),(-680,500,45),(-550,520,45),(-600,350,35),(-400,400,35),(-800,700,45)])
    points=[]
    routes={p['id']:p for p in room['routes']}
    goal=min(routes,key=lambda i:math.hypot(routes[i]['position'][0]-fixtures[0][0],routes[i]['position'][2]-fixtures[0][1]))
    incoming={goal}
    while True:
        more={i for i,p in routes.items() if any(j in incoming for j in p['links'])}
        if more<=incoming:break
        incoming|=more
    for actor in actors:
        x,y,z=actor['position'];radius=20 if actor['category']=='enemy' else (100 if actor['catalog_id']=='map01' else 35)
        if any(math.hypot(x-a,z-b)<radius+r for a,b,r in fixtures):
            raise ValueError('Roster overlaps captain, destination, marker or flower')
        if any(math.hypot(x-a,z-b)<radius+r for a,b,r in points):raise ValueError('Roster actor overlap')
        points.append((x,z,radius))
        samples=[]
        for dx,dz in ((12,0),(-12,0),(0,12),(0,-12)):
            h=ground_height(room['vertices'],room['triangles'],x+dx,z+dz)
            if h is None or abs(h-y)>40:raise ValueError('Roster ground neighborhood discontinuity')
            samples.append(h)
        route=min(routes,key=lambda i:math.hypot(routes[i]['position'][0]-x,routes[i]['position'][2]-z))
        if route not in incoming:raise ValueError('Actor route cannot reach Pod destination')
        actor['terrain_route_probe']=dict(ground_samples=samples,nearest_route=route,destination_route=goal,
                                         clearance_radius=radius)


def _private(path, run):
    resolved=path.resolve()
    if not resolved.is_relative_to(run.resolve()): raise ValueError('Roster target escapes private run')
    if path.exists() and path.is_file() and path.stat().st_nlink!=1:
        raise ValueError('Roster refuses shared hard-linked file')
    return path


def install(content_import, run, floor, assets, imported):
    """Replace scaffold cargo/enemies; preserve squad, Pod and conversion flowers."""
    if floor not in (1,2): raise ValueError('Expected floor one or two')
    if (run/'p2-cargo.txt').exists(): raise ValueError('Roster already installed')
    content=json.loads((content_import/'content.json').read_text())
    if content.get('schema')!=1 or content.get('cave')!='tutorial_1':raise ValueError('Expected Emergence content')
    source=next(f for f in content['floors'] if f['number']==floor)
    unit='room_north_tutorial_1_snow' if floor==1 else 'room_purple14x14_snow'
    room=json.loads((imported/'units'/unit/'collision.json').read_text())
    targets=[a for a in source['actors'] if a['category']=='treasure']
    enemies=[a for a in source['actors'] if a['category']=='enemy']
    if len(targets)!=(2 if floor==1 else 1) or len(enemies)!=(4 if floor==1 else 7):
        raise ValueError('Unexpected Emergence roster count')
    if any(a['catalog_id']!='YellowKochappy' for a in enemies):raise ValueError('Unsupported enemy species')
    items=placements(room,targets,2);mobs=placements(room,enemies,0)
    if floor==2:
        for item in items:
            if item['catalog_id']=='map01':
                item['source_projected_position']=item['position']
                x,z=-470,670
                y=ground_height(room['vertices'],room['triangles'],x,z)
                if y is None:raise ValueError('Atlas engineering placement lacks ground')
                item['position']=[x,y,z]
                item['placement_override']='Flat landing-side approach; native haul from source slot drops at slope near (-250,555).'
                item['ground_projection_delta']=y-item['source_position'][1]
    audit(room,items+mobs,floor)
    # Legacy fixture accessors retain the Pod-selected item as their first cargo.
    selected=(run/'p2-pod.txt').read_text().split()[1]
    items.sort(key=lambda a:a['catalog_id']!=selected)
    if items[0]['catalog_id']!=selected:raise ValueError('Selected Pod treasure absent from floor')
    gen=_private(run/'assets/dataDir/stages/chal0/default.gen',run)
    old=records(gen);kept=[];treasure=None
    for row in old:
        label=row[16:48].rstrip(b'\0')
        if label==b'preview treasure bolt':treasure=row
        elif label!=b'preview dwarf bulborb':kept.append(row)
    if treasure is None or treasure[80:84]!=b'50rp':raise ValueError('Missing pr05 treasure template')
    # Base generator returns the same validated one-actor dwarf template even
    # when the prepared second floor contains no enemy yet.
    base=generator(assets)
    starts=[m.start() for m in re.finditer(b'    0.0v',base)]+[len(base)]
    dwarf=next(base[a:b] for a,b in zip(starts,starts[1:]) if base[a+16:a+48].rstrip(b'\0')==b'preview dwarf bulborb')
    used={struct.unpack_from('<I',r,8)[0] for r in kept};rows=[];models=[]
    ids=set();models_seen=set()
    for ordinal,actor in enumerate(items+mobs):
        gid=5000+ordinal
        if gid in used:raise ValueError('Reserved generator ID collision')
        ident=actor['instance_id']
        if not re.fullmatch(r'[A-Za-z0-9_:/-]{1,90}',ident) or ident in ids:raise ValueError('Invalid instance identity')
        ids.add(ident);actor['native_generator_id']=gid
        cargo=ordinal<len(items)
        row=bytearray(treasure if cargo else dwarf)
        struct.pack_into('<I',row,8,gid)
        row[16:48]=(b'preview treasure bolt' if cargo else b'preview dwarf bulborb').ljust(32,b'\0')
        struct.pack_into('>6f',row,48,*actor['position'],0,actor['angle'],0)
        rows.append(bytes(row))
        if cargo:
            cid=actor['catalog_id'];entry=content['treasures'][cid]
            if not re.fullmatch(r'[A-Za-z0-9_-]+',cid):raise ValueError('Unsafe catalog ID')
            model='p2cargo_'+cid
            if len(model)>64 or model in models_seen:raise ValueError('Duplicate/invalid model identity')
            models_seen.add(model)
            data=(content_import/'treasures'/cid/'treasure.mod').read_bytes()
            if hashlib.sha256(data).hexdigest()!=entry['model_sha256']:raise ValueError('Content model hash differs')
            value,weight,slots=(entry[k] for k in ('value','required_strength','carrier_slots'))
            if any(type(v)!=int for v in (value,weight,slots)) or not(0<=value<=1000000 and 1<=weight<=1000 and 1<=slots<=128):
                raise ValueError('Invalid cargo economy')
            actor.update(model=model,value=value,weight=weight,slots=slots)
            models.append((_private(run/'assets/dataDir/courses/pikmin2room'/(model+'.mod'),run),data))
    config='P2_CARGO_1\n'+str(len(items))+'\n'+''.join(
        f'{a["native_generator_id"]} {a["instance_id"]} {a["model"]} {a["value"]} {a["weight"]} {a["slots"]}\n' for a in items)
    header=bytearray(gen.read_bytes()[:24]);struct.pack_into('>I',header,20,len(kept)+len(rows))
    # All content and path validation precedes mutations in this disposable run.
    for path,data in models:path.write_bytes(data)
    temporary=gen.with_suffix('.roster.tmp');_private(temporary,run).write_bytes(header+b''.join(kept+rows));os.replace(temporary,gen)
    (run/'p2-cargo.txt').write_text(config,encoding='ascii')
    result=dict(schema=1,engineered_runtime=True,policy=POLICY,floor=floor,unit=unit,
                actors=items+mobs,enemy_generator_ids=[a['native_generator_id'] for a in mobs],
                allowed_receipts={**{f'treasure:{a["instance_id"]}':a['value'] for a in items},
                                  **{f'corpse:floor{floor}:{a["native_generator_id"]}':int((run/'p2-pod.txt').read_text().split()[6]) for a in mobs}},
                limitations=['Standalone engineering room, not retail generated layout.',
                             'Source-slot deterministic offsets; ground projection does not prove full footprint/carry clearance.',
                             'Native P1 combat remains; plants and existing Violet flower placements are unchanged.'])
    (run/'p2-roster.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
