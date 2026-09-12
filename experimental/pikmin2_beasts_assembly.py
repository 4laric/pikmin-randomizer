"""Two-room Hole of Beasts engineering assembly, not retail seeded generation."""
import argparse
import hashlib
import json
import math
from pathlib import Path

from experimental.pikmin2_assembly import transform,merge_rooms,merged_model
from experimental.pikmin2_cave import route_audit
from experimental.pikmin2_collision import attach_collision,ground_height,route_ini
from experimental.pikmin2_convert import write_model

ROOM='room_cent3_4_tsuchi'
WAY='way2_tsuchi'
CAP='item_cap_tsuchi'


def layout(units,rooms):
    instances=[(ROOM,0,[0,0,0]),(WAY,1,[510,0,0]),(ROOM,0,[1020,0,0])]
    seams=[((0,1),(1,1)),((1,0),(2,3))]
    used={(0,1),(2,3)}
    for room_index in (0,2):
        _,turn,offset=instances[room_index]
        routes={p['id']:p for p in rooms[ROOM]['routes']}
        cap_routes={p['id']:p for p in rooms[CAP]['routes']}
        capdoor=units[CAP]['doors'][0]
        for door in units[ROOM]['doors']:
            if (room_index,door['id']) in used:continue
            capturn=(door['direction']+turn+2-capdoor['direction'])%4
            target=transform(routes[door['waypoint']]['position'],turn,offset)
            local=transform(cap_routes[capdoor['waypoint']]['position'],capturn)
            capoffset=[a-b for a,b in zip(target,local)]
            seams.append(((room_index,door['id']),(len(instances),capdoor['id'])))
            instances.append((CAP,capturn,capoffset))
    return instances,seams


def cell_audit(instances,units):
    rectangles=[]
    for name,turn,offset in instances:
        width,depth=units[name]['cells']
        if turn%2:width,depth=depth,width
        x,_,z=offset
        box=(x-width*85,x+width*85,z-depth*85,z+depth*85)
        if any(min(box[1],b[1])-max(box[0],b[0])>.01 and min(box[3],b[3])-max(box[2],b[2])>.01 for b in rectangles):
            raise ValueError('Unit grid footprints overlap')
        rectangles.append(box)
    return rectangles


def seam_audit(room,instances,seams,units,rooms):
    reports=[]
    for left,right in seams:
        i,d=left;name,turn,offset=instances[i]
        door=next(x for x in units[name]['doors'] if x['id']==d)
        route=next(p for p in rooms[name]['routes'] if p['id']==door['waypoint'])
        center=transform(route['position'],turn,offset)
        direction=(door['direction']+turn)%4
        axis=(0,-1) if direction==0 else (1,0) if direction==1 else (0,1) if direction==2 else (-1,0)
        samples=[]
        for distance in range(-30,31,5):
            for side in (-25,0,25):
                x=center[0]+axis[0]*distance-axis[1]*side
                z=center[2]+axis[1]*distance+axis[0]*side
                y=ground_height(room['vertices'],room['triangles'],x,z)
                if y is None or abs(y-center[1])>.1:raise ValueError('Missing or discontinuous seam ground')
                samples.append([x,y,z])
        reports.append(dict(left=left,right=right,center=center,samples=samples))
    return reports


def build(imported,output):
    manifest_bytes=(imported/'units.json').read_bytes();manifest=json.loads(manifest_bytes)
    if manifest.get('schema')!=1 or manifest.get('cave_id')!='forest_1':raise ValueError('Expected Hole of Beasts selected units')
    floor=next((f for f in manifest['floors'] if f['first_floor']==f['last_floor']==1),None)
    if floor is None or not {ROOM,WAY,CAP}<=set(floor['unit_candidates']):raise ValueError('Assembly units absent from source floor1 pool')
    units={};rooms={};sources={}
    for name in (ROOM,WAY,CAP):
        metadata=manifest['units'][name]
        if metadata['status']!='converted' or not metadata['assembly_ready']:raise ValueError('Unit is not converted')
        directory=imported/'units'/name
        for file,expected in metadata['output_sha256'].items():
            if hashlib.sha256((directory/file).read_bytes()).hexdigest()!=expected:raise ValueError('Converted unit hash differs')
        units[name]=metadata['definition'];rooms[name]=json.loads((directory/'collision.json').read_text())
        sources[name]=(directory/'arc/view.bmd').read_bytes()
    instances,seams=layout(units,rooms)
    footprints=cell_audit(instances,units)
    room=merge_rooms([(rooms[name],units[name],turn,offset) for name,turn,offset in instances],seams)
    navigation=route_audit(room)
    if any(row['unreachable_sources'] for row in navigation):raise ValueError('Assembly route graph disconnected')
    ground=seam_audit(room,instances,seams,units,rooms)
    output.mkdir(parents=True,exist_ok=False)
    report=write_model(merged_model([(sources[name],turn,offset) for name,turn,offset in instances]),output/'render.mod','Hole of Beasts engineering assembly')
    (output/'room.mod').write_bytes(attach_collision((output/'render.mod').read_bytes(),room))
    (output/'room.ini').write_text(route_ini(room['routes']))
    (output/'collision.json').write_text(json.dumps(room,indent=2)+'\n')
    result=dict(schema=1,cave='forest_1',floor=1,layout=instances,seams=seams,footprints=footprints,
                assembled=True,native_validated=False,generated_retail=False,render=report,route_audit=navigation,seam_audit=ground,
                import_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
                source_model_sha256={k:hashlib.sha256(v).hexdigest() for k,v in sorted(sources.items())},
                output_sha256={name:hashlib.sha256((output/name).read_bytes()).hexdigest() for name in ('render.mod','room.mod','room.ini','collision.json')},
                limitations=['Authored two-room arrangement plus connector and six caps; no retail generation.',
                             'No actor/treasure/start selection, native camera test or physical hauling validation.',
                             'Cell and seam probes do not prove full scenery/carry footprint clearance.'])
    result['render']={k:v for k,v in report.items() if k not in ('source','output')}
    (output/'assembly.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--imported',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=build(a.imported,a.output)
    print(json.dumps(dict(instances=len(r['layout']),seams=len(r['seams']),routes=len(r['route_audit']),ground_samples=sum(len(s['samples']) for s in r['seam_audit']))))
