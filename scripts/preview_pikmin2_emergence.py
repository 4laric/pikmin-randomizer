"""Isolated Emergence entrance-room engineering preview, not a complete floor."""
import argparse
import json
from pathlib import Path
import re
import struct
import subprocess
import uuid

from experimental.pikmin2_collision import attach_collision, ground_height, route_ini
from scripts.preview_pikmin2_room import generator, overlay

UNIT = 'room_north_tutorial_1_snow'


def prepare(assets, imported, treasure, output):
    manifest=json.loads((imported/'manifest.json').read_text())
    if manifest['schema']!=1 or manifest['cave']!='tutorial_1':
        raise ValueError('Expected Emergence import manifest')
    unit=manifest['units'][UNIT]
    if any(row['unreachable_sources'] for row in unit['route_audit']):
        raise ValueError('Entrance room has unreachable route destinations')
    directory=imported/'units'/UNIT
    room=json.loads((directory/'collision.json').read_text())
    # Preserve source routes; unlike room105 these destinations already connect.
    routes=route_ini(room['routes']).encode('utf-8')
    model=attach_collision((directory/'render.mod').read_bytes(),room,cap_exits=True)
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
    overrides={'dataDir/stages/chal0.ini':stage,
               'dataDir/stages/chal0/default.gen':bytes(actors),
               'dataDir/courses/pikmin2room/room.mod':model,
               'dataDir/courses/pikmin2room/room.ini':routes,
               'dataDir/courses/pikmin2room/treasure.mod':treasure.read_bytes()}
    for path in (assets/'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/'+path.name,empty)
    run=output.resolve()/uuid.uuid4().hex
    run.mkdir(parents=True)
    heights=[ground_height(room['vertices'],room['triangles'],x,z)
             for x,z in [(-85,0),(-175,-100),(185,-180),(-220,-180)]]
    if any(y is None for y in heights):
        raise ValueError('Missing ground beneath preview actor fixture')
    (run/'p2-ground.txt').write_text(' '.join(str(y) for y in heights))
    overlay(assets,run/'assets',overrides)
    (run/'preview.json').write_text(json.dumps(dict(unit=UNIT,experimental=True,ap=False,save_resume=False,
        complete_floor=False,actors='20 Reds, P1 Dwarf Bulborb, Onion and bolt from room105 fixture',
        limitations='Door capped; no Pod, actual cave roster, descent, Purples or campaign persistence.'),indent=2))
    return run


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets',type=Path,required=True)
    parser.add_argument('--imported',type=Path,required=True)
    parser.add_argument('--treasure',type=Path,required=True,help='Existing local room105 treasure.mod scaffold')
    parser.add_argument('--output',type=Path,default=Path('output/pikmin2-emergence-preview'))
    parser.add_argument('--exe',type=Path)
    args=parser.parse_args()
    run=prepare(args.assets.resolve(),args.imported.resolve(),args.treasure.resolve(),args.output)
    print(run,flush=True)
    if args.exe:
        with (run/'native.log').open('w',encoding='utf-8') as log:
            result=subprocess.run([str(args.exe.resolve()),'--experimental-pikmin2-room'],cwd=run,stdout=log,stderr=subprocess.STDOUT)
        if result.returncode:
            raise SystemExit(f'Native exit {result.returncode}: {run / "native.log"}')
