"""Run the private original P1 Tank proxy arena; no combat/carry claim."""
import argparse,json,os,re,subprocess
from pathlib import Path
from experimental.pikmin2_tank_arena import prepare,POSITIONS,IDS
from scripts.test_pikmin2_surface_native import executable_identity

def validate(text):
    rows=re.findall(r'P2_TANK_PROXY_READY generator=(\d+) native_type=(\d+) xyz=([-\d.]+),([-\d.]+),([-\d.]+)',text)
    if len(rows)!=1:raise ValueError('Expected one opted-in Tank')
    identity,kind,*xyz=rows[0]
    if int(identity)!=IDS[0] or int(kind)!=15 or any(abs(float(a)-b)>.1 for a,b in zip(xyz,POSITIONS[0])):raise ValueError('Full native birth identity/XYZ mismatch')
    if 'P2_TANK_PROXY_DRAW' not in text or 'PASS P2_TANK_ACTOR_ARENA' not in text:raise ValueError('Missing live visual/movement/reset evidence')
    movement=re.findall(r'P2_TANK_ARENA_MOVE frame=(\d+) displacement=([\d.]+) moving=(\d+)',text)
    if not movement or max(float(r[1]) for r in movement)<=15 or max(int(r[2]) for r in movement)<15:raise ValueError('Insufficient natural movement')
    if 'P2_WTANK_DISPLAY_READY display=186153' not in text or 'P2_WTANK_DISPLAY_DRAW noninteractive_static_no_actor_no_collision_no_receiver' not in text:raise ValueError('Missing noninteractive water display evidence')
    if 'P2_TANK_CONTROL generator=186152' not in text:raise ValueError('Missing ordinary control')
    counters=re.findall(r'P2_TANK_COUNTER state=(\d+) motion=(\d+) counter=([\d.]+) frames=(\d+)',text)
    if not any(a[1]==b[1] and a[2]!=b[2] for a,b in zip(counters,counters[1:])):raise ValueError('Animation counter did not advance within a motion')
    return dict(counter_samples=counters,water_noninteractive=True,identity=int(identity),birth_xyz=list(map(float,xyz)),max_displacement=max(float(r[1]) for r in movement),moving_frames=max(int(r[2]) for r in movement))

def run(args):
    args.output.mkdir(parents=True,exist_ok=False);exe=executable_identity(args.exe)
    directory=prepare(args.assets,args.profile,args.output)
    (args.output/'launch.json').write_text(json.dumps(dict(executable=exe,directory=str(directory)),indent=2))
    env=dict(os.environ,SDL_AUDIODRIVER='dummy');env['PATH']='C:/msys64/mingw64/bin;'+env['PATH']
    with (directory/'host.log').open('w') as out:
        result=subprocess.run([str(args.exe),'--experimental-pikmin2-room'],cwd=directory,env=env,stdout=out,stderr=subprocess.STDOUT,timeout=args.timeout)
    if result.returncode:raise RuntimeError(f'Native arena exit{result.returncode}: {directory}')
    evidence=validate((directory/'host.log').read_text(errors='replace'))
    report=dict(executable=exe,directory=str(directory),evidence=evidence,behavior='P1 fire proxy; water noninteractive static display; no P2 combat acceptance')
    (args.output/'result.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('assets','profile','exe','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--timeout',type=int,default=60);a=p.parse_args()
    for k,v in vars(a).items():
        if isinstance(v,Path):setattr(a,k,v.resolve())
    if not 1<=a.timeout<=180:p.error('timeout must be1..180')
    run(a)
