"""Retail Snow attack-entry geometry; bite/capture timing remains P1."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from experimental.pikmin2_assets import archive_files,disc_files
from experimental.pikmin2_snow_policy import parameter_groups,animation_events,PARAMETER_PATH,ANIMATION_PATH

TEXT='P2_SNOW_ATTACK_1\nrange 30\nhalf_angle 20\n'


def profile(parameters,events):
    general=parameter_groups(parameters)[1]
    clips=animation_events(events)
    if (general.get('fp20'),general.get('fp21'))!=(30,20):
        raise ValueError('Unsupported Snow attack-entry parameters')
    if clips.get('attack.bca')!=[{'frame':8,'type':2},{'frame':88,'type':3}]:
        raise ValueError('Unexpected source capture/swallow events')
    return {'schema':1,'species':'YellowKochappy','range':30,'half_angle_degrees':20,
            'distance':'strict 3D center separation squared < range squared',
            'angle':'absolute wrapped yaw difference <= half_angle_degrees',
            'attack_events':clips['attack.bca'],
            'implemented_delta':'Attack-entry eligibility only; P1 capture and swallow events remain unchanged.'}


def eligible(distance_squared,angle_radians):
    """Source geometry reference; target recognition is supplied by the engine."""
    return (math.isfinite(distance_squared) and math.isfinite(angle_radians) and
            0<=distance_squared<900 and abs(math.remainder(angle_radians,2*math.pi))<=math.radians(20))


def extract(iso,output):
    source='enemy/parm/enemyParms.szs';offset,size=disc_files(iso)[source]
    with iso.open('rb') as stream:stream.seek(offset);data=stream.read(size)
    archive=archive_files(data)
    result=profile(archive[PARAMETER_PATH].decode('shift_jis'),archive[ANIMATION_PATH].decode('shift_jis'))
    result['source_sha256']={source:hashlib.sha256(data).hexdigest(),PARAMETER_PATH:hashlib.sha256(archive[PARAMETER_PATH]).hexdigest(),ANIMATION_PATH:hashlib.sha256(archive[ANIMATION_PATH]).hexdigest()}
    output.mkdir(parents=True,exist_ok=False)
    (output/'snow-attack.json').write_text(json.dumps(result,indent=2))
    (output/'p2-snow-attack.txt').write_text(TEXT)
    return result


def install(imported,run):
    text=(imported/'p2-snow-attack.txt').read_text()
    if text.split()!=TEXT.split():raise ValueError('Unsupported Snow attack policy')
    if not all((run/name).is_file() for name in ('p2-snow.txt','p2-snow-actors.txt')):
        raise ValueError('Snow attack policy requires an installed Snow actor bank')
    (run/'p2-snow-attack.txt').write_text(text)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(extract(args.iso,args.output),indent=2))
