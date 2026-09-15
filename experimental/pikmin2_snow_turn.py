"""Snow angular response profile; source turn-state completion is not applied."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from experimental.pikmin2_assets import archive_files,disc_files
from experimental.pikmin2_snow_policy import parameter_groups,PARAMETER_PATH

TEXT='P2_SNOW_TURN_1\nturn_profile source_snow\n'


def profile(text):
    groups=parameter_groups(text);general,proper=groups[1:]
    values=(general.get('fp06'),general.get('fp08'),general.get('fp28'),proper.get('fp03'))
    if values!=(50,0.4,10,180):raise ValueError('Unsupported retail Snow turning profile')
    return {'schema':1,'species':'YellowKochappy','gain':0.4,'cap_degrees_per_update':10,
            'source_move_speed':50,'source_rotation_end_degrees':180,
            'arrival':'P1 turnSpeed*dt threshold and snap retained; source180 completion not applied',
            'scope':'Angular response only, per receiver update; no full locomotion/state parity.'}


def step(facing,target,arrival_step):
    if not all(math.isfinite(v) for v in (facing,target,arrival_step)) or arrival_step<0:
        raise ValueError('Nonfinite direction or invalid arrival step')
    facing%=2*math.pi;target%=2*math.pi
    error=(target-facing)%(2*math.pi)
    if error>=math.pi:error-=2*math.pi
    arrived=abs(error)<arrival_step
    delta=error if arrived else max(-math.radians(10),min(math.radians(10),error*0.4))
    return (facing+delta)%(2*math.pi),arrived


def extract(iso,output):
    source='enemy/parm/enemyParms.szs';offset,size=disc_files(iso)[source]
    with iso.open('rb') as stream:stream.seek(offset);data=stream.read(size)
    raw=archive_files(data)[PARAMETER_PATH];result=profile(raw.decode('shift_jis'))
    result['source_sha256']={source:hashlib.sha256(data).hexdigest(),PARAMETER_PATH:hashlib.sha256(raw).hexdigest()}
    output.mkdir(parents=True,exist_ok=False);(output/'snow-turn.json').write_text(json.dumps(result,indent=2));(output/'p2-snow-turn.txt').write_text(TEXT)
    return result


def install(imported,run):
    text=(imported/'p2-snow-turn.txt').read_text()
    if text.split()!=TEXT.split():raise ValueError('Unsupported Snow turning policy')
    if not all((run/name).is_file() for name in ('p2-snow.txt','p2-snow-actors.txt')):raise ValueError('Snow turn profile requires a Snow bank')
    (run/'p2-snow-turn.txt').write_text(text)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--iso',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(extract(args.iso,args.output),indent=2))
