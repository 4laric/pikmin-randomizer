"""Source Snow chase steering reference; native physics/FSM remain separate."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from experimental.pikmin2_assets import archive_files,disc_files
from experimental.pikmin2_snow_policy import parameter_groups,PARAMETER_PATH
from experimental.pikmin2_snow_turn import step as turn_step

TEXT='P2_SNOW_CHASE_1\nchase_profile source_snow\n'


def profile(text):
    general=parameter_groups(text)[1]
    if tuple(general.get(key) for key in ('fp06','fp08','fp28'))!=(50,0.4,10):
        raise ValueError('Unsupported retail Snow chase profile')
    return {'schema':1,'species':'YellowKochappy','speed':50,'turn_gain':0.4,'turn_cap_degrees_per_update':10,
            'ordering':['source proportional yaw update','heading-aligned XZ target velocity','preserve existing target velocity Y'],
            'scope':'Chase target velocity only; P1 action ordering, acceleration, gravity and animation remain.'}


def steer(facing,target_angle,velocity_y):
    if not math.isfinite(velocity_y):raise ValueError('Nonfinite vertical velocity')
    angle,_=turn_step(facing,target_angle,0)
    return angle,(50*math.sin(angle),velocity_y,50*math.cos(angle))


def extract(iso,output):
    source='enemy/parm/enemyParms.szs';offset,size=disc_files(iso)[source]
    with iso.open('rb') as stream:stream.seek(offset);data=stream.read(size)
    raw=archive_files(data)[PARAMETER_PATH];result=profile(raw.decode('shift_jis'))
    result['source_sha256']={source:hashlib.sha256(data).hexdigest(),PARAMETER_PATH:hashlib.sha256(raw).hexdigest()}
    output.mkdir(parents=True,exist_ok=False);(output/'snow-chase.json').write_text(json.dumps(result,indent=2));(output/'p2-snow-chase.txt').write_text(TEXT)
    return result


def install(imported,run):
    text=(imported/'p2-snow-chase.txt').read_text()
    if text.split()!=TEXT.split():raise ValueError('Unsupported chase profile')
    if not all((run/name).is_file() for name in ('p2-snow.txt','p2-snow-actors.txt')):raise ValueError('Chase profile requires a Snow bank')
    (run/'p2-snow-chase.txt').write_text(text)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--iso',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(extract(args.iso,args.output),indent=2))
