"""Observe a P1 Breadbug proxy's native pellet interaction in a private arena."""
import argparse,json,os,re,subprocess
from pathlib import Path
from experimental.pikmin2_breadbug_arena import prepare
from scripts.test_pikmin2_surface_native import executable_identity

def evidence(text):
    rows=re.findall(r'P2_BREADBUG_CARGO_RESULT grabbed=(\d+) held_frames=(\d+) moved=([\d.]+) progress=([-\d.]+) released=(\d+) alive=(\d+)',text)
    if len(rows)!=1:raise ValueError('Expected one completed cargo observation')
    grabbed,frames,moved,progress,released,alive=rows[0]
    result=dict(grabbed=bool(int(grabbed)),held_frames=int(frames),displacement=float(moved),nest_progress=float(progress),released=bool(int(released)),pellet_alive=bool(int(alive)))
    result['live_visual']='P2_BREADBUG_ACTOR_DRAW' in text
    result['drag_observed']=result['grabbed'] and result['held_frames']>15 and result['displacement']>10 and result['nest_progress']>10
    result['complete']=result['drag_observed'] and result['released'] and result['live_visual']
    return result

def run(args):
    args.output.mkdir(parents=True,exist_ok=False)
    exe=executable_identity(args.exe);stage=prepare(args.assets,args.profile,args.output)
    env=dict(os.environ,SDL_AUDIODRIVER='dummy');env['PATH']='C:/msys64/mingw64/bin;'+env['PATH']
    with (stage/'host.log').open('w') as out:
        native=subprocess.run([str(args.exe),'--experimental-pikmin2-room'],cwd=stage,env=env,stdout=out,stderr=subprocess.STDOUT,timeout=args.timeout)
    if native.returncode:raise RuntimeError(f'Native observation exited {native.returncode}: {stage}')
    result=dict(executable=exe,directory=str(stage),evidence=evidence((stage/'host.log').read_text(errors='replace')),scope='P1 proxy observation; no forced enemy action or P2 AI parity')
    (args.output/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('assets','profile','exe','output'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--timeout',type=int,default=100);a=p.parse_args()
    for k,v in vars(a).items():
        if isinstance(v,Path):setattr(a,k,v.resolve())
    if not 1<=a.timeout<=180:p.error('timeout must be 1..180')
    run(a)
