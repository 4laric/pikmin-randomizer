"""Stage a physically fenced engineering entrance fixture; never a player release."""
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import re
import struct
import uuid

from experimental.pikmin2_collision import attach_collision, plane,route_ini
from experimental.pikmin2_surface_physics import surface_mapcode
from experimental.pikmin2_entrance_pocket import CENTER,TRAVEL_RADIUS
from scripts.preview_pikmin2_room import generator,overlay


def boundary_room(original):
    room=deepcopy(original)
    start=len(room['triangles']);verts=len(room['vertices'])
    for i in range(32):
        angle=2*math.pi*i/32
        x,z=CENTER[0]+60*math.cos(angle),CENTER[2]+60*math.sin(angle)
        room['vertices'].extend([[x,-1920.,z],[x,4176.,z]])
    for i in range(32):
        a=verts+2*i;b=verts+2*((i+1)%32)
        for tri in ([a,b+1,b],[a,a+1,b+1]):
            nx,ny,nz,d=plane(room['vertices'],tri)
            if abs(ny)>1e-9 or nx*CENTER[0]+nz*CENTER[2]-d<=0:
                raise ValueError('Boundary wall must face inward, without floor')
            room['triangles'].append(list(tri));room['mapcodes'].append(65)
    room['bounds']={name:[fn(v[k] for v in room['vertices']) for k in range(3)]
                    for name,fn in [('min',min),('max',max)]}
    room['engineering_boundary']=dict(first_triangle=start,count=64,radius=60,sides=32,min_y=-1920,max_y=4176)
    return room


def actors(assets):
    data=generator(assets)
    starts=[m.start() for m in re.finditer(b'    0.0v',data)]+[len(data)]
    entries=[];pikis=0
    for a,b in zip(starts,starts[1:]):
        row=bytearray(data[a:b]);label=bytes(row[16:48]).rstrip(b'\0')
        if label==b'preview red pikmin':
            x,z=CENTER[0]-12+(pikis%5)*6,CENTER[2]-9+(pikis//5)*6;pikis+=1
        elif label==b'preview treasure bolt':x,z=CENTER[0]+20,CENTER[2]+15
        else:continue # No Onion/ship/enemy collision clutter in the tiny fixture.
        struct.pack_into('>3f',row,48,x,80,z);entries.append(row)
    if pikis!=20 or len(entries)!=21:raise ValueError('Unexpected engineering actor templates')
    return b'1.0v'+struct.pack('>4fI',CENTER[0]-20,80,CENTER[2],0,len(entries))+b''.join(entries)


def prepare(assets,source_import,pocket,treasure,output):
    manifest=json.loads((pocket/'entrance-pocket.json').read_text())
    if manifest['source_anchor']!=CENTER or manifest['travel_radius']!=60:raise ValueError('Wrong source pocket')
    water=(pocket/'surface-water.json').read_bytes()
    if len(json.loads(water)['boxes'])!=3:raise ValueError('Missing source water')
    room=boundary_room(json.loads((pocket/'entrance-collision.json').read_text()))
    model=attach_collision((source_import/'surface-render.mod').read_bytes(),room,mapcode_translator=surface_mapcode)
    stage=(assets/'dataDir/stages/chal0.ini').read_bytes()
    stage=re.sub(rb'(?m)^map_file[^\r\n]*',b'map_file courses/pikmin2room/room.mod',stage)
    stage=re.sub(rb'(?m)^navi_start[^\r\n]*',b'navi_start -210.0 1160.0',stage)
    empty=b'1.0v'+struct.pack('>4fI',-210,80,1160,0,0)
    overrides={'dataDir/stages/chal0.ini':stage,'dataDir/stages/chal0/default.gen':actors(assets),
               'dataDir/courses/pikmin2room/room.mod':model,'dataDir/courses/pikmin2room/room.ini':route_ini([]).encode(),
               'dataDir/courses/pikmin2room/treasure.mod':treasure.read_bytes()}
    for p in (assets/'dataDir/stages/chal0').glob('*.gen'):overrides.setdefault('dataDir/stages/chal0/'+p.name,empty)
    run=output/uuid.uuid4().hex;run.mkdir(parents=True)
    overlay(assets,run/'assets',overrides)
    (run/'surface-water.json').write_bytes(water)
    (run/'boundary-collision.json').write_text(json.dumps(room,indent=2))
    (run/'preview.json').write_text(json.dumps(dict(experimental=True,fixture_only=True,player_release=False,
        boundary=room['engineering_boundary'],water_consumer=False,source_water_retained=True,
        limitation='Engineered invisible boundary ring; actual native collision validation required.'),indent=2))
    return run


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('assets','source-import','pocket','treasure','output'):parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args();print(prepare(a.assets.resolve(),a.source_import.resolve(),a.pocket.resolve(),a.treasure.resolve(),a.output.resolve()))
