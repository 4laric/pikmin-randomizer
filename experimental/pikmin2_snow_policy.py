"""Source-backed optional Snow health policy; source events remain diagnostic only."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

from experimental.pikmin2_assets import archive_files, disc_files

PARAMETER_PATH='yellowkochappy/enemyparm.txt'
ANIMATION_PATH='kochappy/enemyanimmgr.txt'


def parameter_groups(text):
    groups=[];current=None;ended=False
    for raw in text.splitlines():
        line=raw.split('#',1)[0].strip()
        if not line:continue
        if line=='{':
            if current is not None:raise ValueError('Nested parameter group')
            current={};ended=False
        elif line=='}':
            if current is None or not ended:raise ValueError('Missing parameter terminator')
            groups.append(current);current=None
        elif line=='{_eof}':
            if current is None or ended:raise ValueError('Unexpected parameter terminator')
            ended=True
        else:
            match=re.fullmatch(r'\{([a-z0-9]+)\}\s+4\s+([-+\d.eE]+)',line)
            if current is None or ended or not match:raise ValueError('Invalid parameter row')
            key,value=match.groups();value=float(value)
            if key in current or not math.isfinite(value):raise ValueError('Duplicate/nonfinite parameter')
            current[key]=value
    if current is not None or len(groups)!=3:raise ValueError('Expected creature/general/proper parameters')
    return groups


def animation_events(text):
    clean='\n'.join(raw.split('#',1)[0] for raw in text.splitlines())
    count=re.match(r'\s*(\d+)',clean)
    if not count:raise ValueError('Missing animation count')
    blocks=re.findall(r'\{([^{}]*)\}',clean)
    if len(blocks)!=int(count[1]):raise ValueError('Animation count mismatch')
    if re.sub(r'\{[^{}]*\}','',clean[count.end():]).strip():raise ValueError('Trailing animation data')
    result={}
    for block in blocks:
        tokens=block.split()
        if len(tokens)<3 or tokens[-1]!='-1':raise ValueError('Missing animation terminator')
        source,name=tokens[:2]
        if not source.replace('\\','/').endswith('/'+name) or not re.fullmatch(r'[a-z0-9_]+\.bca',name) or name in result:
            raise ValueError('Invalid animation identity')
        values=tokens[2:-1]
        if len(values)%2:raise ValueError('Truncated animation event')
        events=[]
        for frame,event in zip(values[::2],values[1::2]):
            frame,event=int(frame),int(event)
            if frame<0 or event<0 or (events and frame<events[-1]['frame']):raise ValueError('Invalid animation event')
            events.append({'frame':frame,'type':event})
        result[name]=events
    return result


def extract(iso,output):
    files=disc_files(iso);source='enemy/parm/enemyParms.szs'
    with iso.open('rb') as stream:
        offset,size=files[source];stream.seek(offset);data=stream.read(size)
    archive=archive_files(data)
    parameters=parameter_groups(archive[PARAMETER_PATH].decode('shift_jis'))
    health=parameters[1]['fp00']
    if health!=150:raise ValueError('Unsupported source Snow health')
    events=animation_events(archive[ANIMATION_PATH].decode('shift_jis'))
    output.mkdir(parents=True,exist_ok=False)
    result={'schema':1,'species':'YellowKochappy','health':health,'events':events,
            'source_sha256':{source:hashlib.sha256(data).hexdigest(),
                             PARAMETER_PATH:hashlib.sha256(archive[PARAMETER_PATH]).hexdigest(),
                             ANIMATION_PATH:hashlib.sha256(archive[ANIMATION_PATH]).hexdigest()},
            'implemented_delta':'Optional max and initial health only; event timing stays P1.',
            'unmapped_clips':['type1.bca','type5.bca','waitact1.bca','waitact2.bca']}
    (output/'snow-policy.json').write_text(json.dumps(result,indent=2))
    (output/'p2-snow-policy.txt').write_text('P2_SNOW_POLICY_1\nhealth 150\n')
    return result


def validate_policy(text):
    if text.split()!=['P2_SNOW_POLICY_1','health','150']:
        raise ValueError('Expected supported Snow health policy')
    return 150.0


def install(imported,run):
    text=(imported/'p2-snow-policy.txt').read_text()
    validate_policy(text)
    if not (run/'p2-snow.txt').is_file() or not (run/'p2-snow-actors.txt').is_file():
        raise ValueError('Snow policy requires an installed Snow actor bank')
    (run/'p2-snow-policy.txt').write_text(text)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(extract(args.iso,args.output),indent=2))
