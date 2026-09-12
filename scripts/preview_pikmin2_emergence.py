"""Isolated Emergence entrance-room engineering preview, not a complete floor."""
import argparse
import json
from pathlib import Path
import re
import struct
import subprocess
import uuid

from experimental.pikmin2_collision import attach_collision, ground_height, route_ini
from scripts.preview_pikmin2_room import generator, overlay, records

UNIT = 'room_north_tutorial_1_snow'


def prepare(assets, imported, treasure, output, assembled=None, floor=1, pod=None, purple=None):
    if purple and not pod:raise ValueError('Purple preview requires Research Pod')
    if floor not in (1,2) or (floor==2 and assembled):
        raise ValueError('Choose floor 1 assembly or standalone floor 2')
    manifest=json.loads((imported/'manifest.json').read_text())
    if manifest['schema']!=1 or manifest['cave']!='tutorial_1':
        raise ValueError('Expected Emergence import manifest')
    name=UNIT if floor==1 else 'room_purple14x14_snow'
    unit=manifest['units'][name]
    if any(row['unreachable_sources'] for row in unit['start_destination_audit']):
        raise ValueError('Room has unreachable start destination')
    directory=assembled if assembled else imported/'units'/name
    if assembled:
        assembly=json.loads((assembled/'assembly.json').read_text())
        if assembly['cave']!='tutorial_1' or assembly['floor']!=1 or not assembly['assembled']:
            raise ValueError('Expected assembled Emergence floor 1')
    room=json.loads((directory/'collision.json').read_text())
    # Preserve source routes; unlike room105 these destinations already connect.
    routes=route_ini(room['routes']).encode('utf-8')
    model=attach_collision((directory/'render.mod').read_bytes(),room,cap_exits=floor==1 and not bool(assembled))
    stage=(assets/'dataDir/stages/chal0.ini').read_bytes()
    stage=re.sub(rb'(?m)^map_file[^\r\n]*',b'map_file courses/pikmin2room/room.mod',stage)
    stage=re.sub(rb'(?m)^navi_start[^\r\n]*',b'navi_start -85.0 0.0',stage)
    empty=b'1.0v'+struct.pack('>4fI',-85,0,0,45,0)
    actors=bytearray(generator(assets))
    # The old concrete-room Onion position is inside this room's raised bank.
    # Put the temporary receiver on audited flat ground near source waypoint 1.
    if actors[40:57] != b'preview red onion':
        raise ValueError('Unexpected preview receiver framing')
    struct.pack_into('>3f',actors,72,0,0,-100)
    if assembled:
        # Same test actors, now in the distant room to exercise both joins.
        starts=[match.start() for match in re.finditer(b'    0.0v',actors)]
        placements={b'preview treasure bolt':(0,0,1020),b'preview dwarf bulborb':(0,0,1190)}
        found=set()
        for start in starts:
            label=bytes(actors[start+16:start+48]).rstrip(b'\0')
            if label in placements:
                struct.pack_into('>3f',actors,start+48,*placements[label]);found.add(label)
        if found!=set(placements): raise ValueError('Missing distant test actor')
    walk=[]
    if floor==2:
        def grounded(x,z):
            y=ground_height(room['vertices'],room['triangles'],x,z)
            if y is None: raise ValueError('Missing floor beneath second-floor actor')
            return (x,y,z)
        starts=[match.start() for match in re.finditer(b'    0.0v',actors)]+[len(actors)]
        entries=[];piki=0
        for start,end in zip(starts,starts[1:]):
            entry=bytearray(actors[start:end]);label=bytes(entry[16:48]).rstrip(b'\0')
            if label==b'preview dwarf bulborb': continue # terrain/carry fixture, no combat roster yet
            if label==b'preview red onion': position=grounded(-680,595)
            elif label==b'preview ship': position=grounded(-800,700)
            elif label==b'preview treasure bolt': position=grounded(475,-425)
            elif label==b'preview red pikmin':
                position=grounded(-750+(piki%5)*12,520+(piki//5)*12);piki+=1
            else: raise ValueError('Unknown second-floor scaffold actor')
            struct.pack_into('>3f',entry,48,*position);entries.append(entry)
        actors=bytearray(b'1.0v'+struct.pack('>4fI',*grounded(-680,500),45,len(entries))+b''.join(entries))
        stage=re.sub(rb'(?m)^navi_start[^\r\n]*',b'navi_start -680.0 500.0',stage)
        # Walk out along the source return route in reverse, without reversing its links.
        walk=[(-340,510),(-85,595),(170,560),(425,425),(595,255),(660,0),(660,-170),(600,-325),(475,-425)]
    if purple:
        template=next(r for r in records(assets/'dataDir/stages/chal0/default.gen') if r[72:76]==b'ssob' and r[76:80]==b'\x02\x00\x00\x00')
        count=struct.unpack_from('>I',actors,20)[0]
        positions=[(-140,60),(140,60)] if floor==1 else [(-600,350),(-400,400)]
        for i,(x,z) in enumerate(positions):
            y=ground_height(room['vertices'],room['triangles'],x,z)
            if y is None:raise ValueError('Violet flower has no ground')
            flower=bytearray(template);struct.pack_into('>I',flower,8,count+i+1)
            flower[16:48]=f'preview violet {i}'.encode().ljust(32,b'\0')
            struct.pack_into('>6f',flower,48,x,y,z,0,0,0)
            struct.pack_into('>I',flower,80,5|(1<<6)) # Pom, Red legacy storage color; explicit P2 Violet metadata.
            actors.extend(flower)
        struct.pack_into('>I',actors,20,count+len(positions))
    overrides={'dataDir/stages/chal0.ini':stage,
               'dataDir/stages/chal0/default.gen':bytes(actors),
               'dataDir/courses/pikmin2room/room.mod':model,
               'dataDir/courses/pikmin2room/room.ini':routes,
               'dataDir/courses/pikmin2room/treasure.mod':treasure.read_bytes()}
    if pod:
        overrides['dataDir/courses/pikmin2room/pod.mod']=(pod/'pod.mod').read_bytes()
        overrides['dataDir/courses/pikmin2room/treasure.mod']=(pod/'treasure.mod').read_bytes()
    if purple:
        for path in purple.glob('*.mod'):overrides['dataDir/courses/pikmin2room/'+path.name]=path.read_bytes()
    for path in (assets/'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/'+path.name,empty)
    run=output.resolve()/uuid.uuid4().hex
    run.mkdir(parents=True)
    if pod: (run/'p2-pod.txt').write_bytes((pod/'p2-pod.txt').read_bytes())
    if purple: (run/'p2-purple.txt').write_bytes((purple/'p2-purple.txt').read_bytes())
    probes=[(-680,500),(-680,595),(475,-425),(660,0)] if floor==2 else [(-85,0),(-175,-100),(185,-180),(-220,-180)]
    heights=[ground_height(room['vertices'],room['triangles'],x,z) for x,z in probes]
    if any(y is None for y in heights):
        raise ValueError('Missing ground beneath preview actor fixture')
    (run/'p2-ground.txt').write_text(' '.join(str(y) for y in heights))
    (run/'p2-probe-positions.txt').write_text('\n'.join(f'{x} {z}' for x,z in probes))
    if assembled: (run/'p2-assembled.txt').write_text('1\n')
    if floor==2:
        (run/'p2-second-floor.txt').write_text(str(len(walk))+'\n'+'\n'.join(f'{x} {z}' for x,z in walk))
    overlay(assets,run/'assets',overrides)
    (run/'preview.json').write_text(json.dumps(dict(unit=name,floor=floor,experimental=True,ap=False,save_resume=False,
        assembled_geometry=bool(assembled),pod=bool(pod),purple=bool(purple),complete_floor=False,
        actors=('20 Reds and source-configured treasure; Dwarf corpse on floor 1' if pod else '20 Reds, bolt and temporary Onion; Dwarf on floor 1'),
        limitations='Engineering layout; no actual cave roster, descent or campaign persistence. Purple support is experimental and opt-in.'),indent=2))
    return run


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets',type=Path,required=True)
    parser.add_argument('--imported',type=Path,required=True)
    parser.add_argument('--treasure',type=Path,required=True,help='Existing local room105 treasure.mod scaffold')
    parser.add_argument('--output',type=Path,default=Path('output/pikmin2-emergence-preview'))
    parser.add_argument('--exe',type=Path)
    parser.add_argument('--assembled',type=Path,help='Optional authored floor assembly directory')
    parser.add_argument('--floor',type=int,choices=(1,2),default=1)
    parser.add_argument('--pod',type=Path,help='Opt-in Research Pod assets and source economy config')
    parser.add_argument('--purple',type=Path,help='Experimental Purple pose bank and two Violet conversion flowers')
    args=parser.parse_args()
    run=prepare(args.assets.resolve(),args.imported.resolve(),args.treasure.resolve(),args.output,args.assembled.resolve() if args.assembled else None,args.floor,args.pod.resolve() if args.pod else None,args.purple.resolve() if args.purple else None)
    print(run,flush=True)
    if args.exe:
        with (run/'native.log').open('w',encoding='utf-8') as log:
            result=subprocess.run([str(args.exe.resolve()),'--experimental-pikmin2-room'],cwd=run,stdout=log,stderr=subprocess.STDOUT)
        if result.returncode:
            raise SystemExit(f'Native exit {result.returncode}: {run / "native.log"}')
