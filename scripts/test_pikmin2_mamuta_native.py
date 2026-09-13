"""Private source-arena Mamuta visual observer, not planted-sprout acceptance."""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from experimental.pikmin2_mamuta_arena import prepare
from scripts.test_pikmin2_surface_native import executable_identity

def validate(text):
    if 'PASS P2_MAMUTA_RUNTIME identity control reset' not in text:
        raise ValueError('Missing native control/reset completion')
    rows=re.findall(r'P2_MAMUTA_FIXTURE_BIRTH id=(\d+) type=(\d+) xyz=([-\d.]+),([-\d.]+),([-\d.]+) control=(\d+)',text)
    if len(rows)!=1 or rows[0][:2]!=('221001','24') or rows[0][-1]!='221002':
        raise ValueError('Missing unique source identity')
    if any(abs(float(a)-b)>.02 for a,b in zip(rows[0][2:5],(-150,30,1850))):
        raise ValueError('Full birth XYZ mismatch')
    anchors=re.findall(r'P2_MAMUTA_DRAW generator=221001 anchor=(\w+) static_pose',text)
    if 'wait' not in anchors: raise ValueError('No source wait anchor drawn')
    if '[PC GX] DESYNC' in text: raise ValueError('GX display list desync')
    return dict(birth_xyz=list(map(float,rows[0][2:5])),anchors=sorted(set(anchors)),
                reset=True,control='P1 Chappy',planting_verified=False,
                corpse_verified=False,same_family_control_verified=False)

def run(args):
    args.output.mkdir(parents=True,exist_ok=False)
    identity=executable_identity(args.exe)
    stage=prepare(args.assets,args.profile,args.output)
    (args.output/'launch.json').write_text(json.dumps(dict(executable=identity,stage=str(stage)),indent=2))
    env=dict(os.environ,SDL_AUDIODRIVER='dummy',PATH='C:/msys64/mingw64/bin;'+os.environ['PATH'])
    with (stage/'native.log').open('w') as stream:
        process=subprocess.run([str(args.exe),'--experimental-pikmin2-room'],cwd=stage,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=args.timeout)
    if process.returncode: raise RuntimeError(f'Native exit {process.returncode}: {stage}')
    result=dict(executable=identity,stage=str(stage),evidence=validate((stage/'native.log').read_text(errors='replace')))
    (args.output/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('assets','profile','exe','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--timeout',type=int,default=90)
    args=p.parse_args()
    for key,value in vars(args).items():
        if isinstance(value,Path):setattr(args,key,value.resolve())
    if not 1<=args.timeout<=180:p.error('timeout must be 1..180')
    run(args)
