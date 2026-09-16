"""Isolated Emergence entrance-room engineering preview, not a complete floor."""
import argparse
import json
from pathlib import Path
import re
import struct
import subprocess
import uuid

from experimental.pikmin2_collision import attach_collision, ground_height, route_ini
from experimental.pikmin2_purple_motion import CLIPS, validate_profile
from scripts.preview_pikmin2_room import generator, overlay, records

UNIT = 'room_north_tutorial_1_snow'


def _purple_motion_files(directory):
    profile=validate_profile((directory/'p2-purple-motion.txt').read_text())
    expected={f'purple_{name}_{index:02}.mod' for name,count in CLIPS for index in range(count)}
    actual={path.name for path in directory.glob('purple_*.mod') if path.name.startswith(('purple_rolljmp_','purple_fall_'))}
    if actual!=expected:raise ValueError('Purple motion bank must contain exactly 34 source poses')
    return profile,{name:(directory/name).read_bytes() for name in sorted(expected)}

def prepare(assets, imported, treasure, output, assembled=None, floor=1, pod=None, purple=None, violet=True, squad=None, white=None, purple_motion=None):
    if (purple or white) and not pod:raise ValueError('Sequel Pikmin preview requires Research Pod')
    if purple_motion and (not purple or not pod):raise ValueError('Purple motion preview requires Purple bank and Research Pod')
    if purple and white:raise ValueError('Use separate bounded Purple and White preview runs')
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
    if purple and violet:
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
    if white:
        template=next(r for r in records(assets/'dataDir/stages/chal0/default.gen') if r[72:76]==b'ssob' and r[76:80]==b'\x02\x00\x00\x00')
        count=struct.unpack_from('>I',actors,20)[0];generator_id=count+1
        configured=(white/'p2-white.txt').read_text().splitlines()
        binding=next((line for line in configured if line.startswith('ivory_generators ')),None)
        if binding != f'ivory_generators 1 {generator_id}':raise ValueError('White bank is not bound to this preview Ivory generator')
        x,z=(-140,60) if floor==1 else (-600,350);y=ground_height(room['vertices'],room['triangles'],x,z)
        if y is None:raise ValueError('Ivory flower has no ground')
        # Generator::readID consumes the on-disk ID in big-endian order.
        flower=bytearray(template);struct.pack_into('>I',flower,8,generator_id);flower[16:48]=b'preview ivory'.ljust(32,b'\0')
        struct.pack_into('>6f',flower,48,x,y,z,0,0,0);struct.pack_into('>I',flower,80,5|(1<<6));actors.extend(flower)
        struct.pack_into('>I',actors,20,count+1)
    if squad is not None:
        if not 1 <= len(squad) <= 100: raise ValueError('Cave entry requires 1-100 survivors')
        starts=[match.start() for match in re.finditer(b'    0.0v',actors)]+[len(actors)]
        entries=[bytearray(actors[a:b]) for a,b in zip(starts,starts[1:])]
        pikis=[e for e in entries if bytes(e[16:48]).rstrip(b'\0')==b'preview red pikmin']
        if len(pikis)!=20: raise ValueError('Expected twenty scaffold spawn templates')
        entries=[e for e in entries if bytes(e[16:48]).rstrip(b'\0')!=b'preview red pikmin']
        for i in range(len(squad)):
            p=bytearray(pikis[i%len(pikis)]);struct.pack_into('>I',p,8,1000+i)
            entries.append(p)
        actors=actors[:24]+b''.join(entries);struct.pack_into('>I',actors,20,len(entries))
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
    motion_profile=None
    if purple_motion:
        motion_profile,motion_files=_purple_motion_files(purple_motion)
        for motion_name,data in motion_files.items():overrides['dataDir/courses/pikmin2room/'+motion_name]=data
    if white:
        for path in white.glob('*.mod'):overrides['dataDir/courses/pikmin2room/'+path.name]=path.read_bytes()
    for path in (assets/'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/'+path.name,empty)
    run=output.resolve()/uuid.uuid4().hex
    run.mkdir(parents=True)
    if pod: (run/'p2-pod.txt').write_bytes((pod/'p2-pod.txt').read_bytes())
    if purple:
        purple_config=(purple/'p2-purple.txt').read_text()
        if purple_motion and 'impact red_earthquake_v1' not in purple_config.splitlines():purple_config=purple_config.rstrip()+'\nimpact red_earthquake_v1\n'
        (run/'p2-purple.txt').write_text(purple_config)
    if purple_motion:
        (run/'p2-purple-motion.txt').write_text(motion_profile)
        (run/'p2-purple-flight.txt').write_text('P2_PURPLE_FLIGHT_1\n')
    if white: (run/'p2-white.txt').write_bytes((white/'p2-white.txt').read_bytes())
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
    (run/'preview.json').write_text(json.dumps(dict(unit=name,floor=floor,experimental=True,ap=False,save_resume=squad is not None,
        assembled_geometry=bool(assembled),pod=bool(pod),purple=bool(purple),purple_motion=bool(purple_motion),white=bool(white),complete_floor=False,
        actors=(f'{len(squad)} transferred survivors; source-configured treasure' if squad is not None else
                '20 Reds and source-configured treasure; Dwarf corpse on floor 1' if pod else '20 Reds, bolt and temporary Onion; Dwarf on floor 1'),
        limitations=('Floor boundaries are saved by the campaign runner; no mid-floor save, surface map or full cave roster.' if squad is not None else
                     'Engineering layout; no actual cave roster, descent or campaign persistence. Purple support is experimental and opt-in.')),indent=2))
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
    parser.add_argument('--purple-motion',type=Path,help='Opt-in retail Purple throw/fall motion bank and flight presentation')
    parser.add_argument('--white',type=Path,help='Experimental White pose bank and one explicitly bound Ivory conversion flower')
    args=parser.parse_args()
    run=prepare(args.assets.resolve(),args.imported.resolve(),args.treasure.resolve(),args.output,args.assembled.resolve() if args.assembled else None,args.floor,args.pod.resolve() if args.pod else None,args.purple.resolve() if args.purple else None,white=args.white.resolve() if args.white else None,purple_motion=args.purple_motion.resolve() if args.purple_motion else None)
    print(run,flush=True)
    if args.exe:
        with (run/'native.log').open('w',encoding='utf-8') as log:
            result=subprocess.run([str(args.exe.resolve()),'--experimental-pikmin2-room'],cwd=run,stdout=log,stderr=subprocess.STDOUT)
        if result.returncode:
            raise SystemExit(f'Native exit {result.returncode}: {run / "native.log"}')
