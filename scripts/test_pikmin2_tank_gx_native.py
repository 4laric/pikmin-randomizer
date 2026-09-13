"""Paired Tank attack/GX diagnosis using the preserved attack-trigger fixture."""
import argparse,json,os,re,subprocess
from pathlib import Path
from experimental.pikmin2_tank_arena import prepare
from scripts.test_pikmin2_surface_native import executable_identity

def analyze(text):
    lines=text.splitlines()
    attacks=[i for i,l in enumerate(lines) if re.search(r'P2_TANK_COUNTER state=7 motion=8 counter=',l)]
    warnings=[i for i,l in enumerate(lines) if '[PC GX] DESYNC #' in l or '[PC GX] Malformed vertex' in l or '[PC GX] Unsupported display-list' in l]
    movies=[i for i,l in enumerate(lines) if 'MoviePlayer: clearing top heap!' in l]
    demo56=[i for i,l in enumerate(lines) if 'dataDir/cinemas/demo56.cin' in l]
    if not attacks:raise ValueError('No observed native Tank attack; comparison invalid')
    return dict(attack_samples=len(attacks),first_attack_line=attacks[0]+1,warning_lines=[i+1 for i in warnings],first_warning_line=warnings[0]+1 if warnings else None,post_attack_movie_clear_lines=[i+1 for i in movies if i>attacks[0]],demo56_lines=[i+1 for i in demo56],warnings_before_demo56=sum(1 for i in warnings if not demo56 or i<demo56[0]),imported_draw='P2_TANK_PROXY_DRAW' in text,water_draw='P2_WTANK_DISPLAY_DRAW' in text)

def run(args):
    args.output.mkdir(parents=True,exist_ok=False)
    exe=executable_identity(args.exe);directory=prepare(args.assets,args.profile,args.output)
    config=directory/'p2-tank-visual.txt'
    original=config.read_bytes();(directory/'p2-tank-visual.original').write_bytes(original)
    if args.mode=='absent':config.unlink()
    elif args.mode=='fire':
        lines=original.decode().splitlines();assert lines[-2]=='1';config.write_bytes(('\n'.join(lines[:-2]+['0'])+'\n').encode())
    import hashlib
    launch=dict(executable=exe,directory=str(directory),mode=args.mode,profile_sha256=hashlib.sha256(config.read_bytes()).hexdigest() if config.exists() else None)
    (args.output/'launch.json').write_text(json.dumps(launch,indent=2))
    env=dict(os.environ,SDL_AUDIODRIVER='dummy');env['PATH']='C:/msys64/mingw64/bin;'+env['PATH']
    timed_out=False
    with (directory/'host.log').open('w') as log:
        try:result=subprocess.run([str(args.exe),'--experimental-pikmin2-room'],cwd=directory,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=args.timeout);code=result.returncode
        except subprocess.TimeoutExpired:timed_out=True;code=None
    report=dict(**launch,exit_code=code,timed_out=timed_out,evidence=analyze((directory/'host.log').read_text(errors='replace')),acceptance='diagnostic only; original movement fixture failure/timeout expected for stationary attacking actor')
    (args.output/'result.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('assets','profile','exe','output'):p.add_argument('--'+key,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--mode',choices=('absent','fire','full'),required=True);p.add_argument('--timeout',type=int,default=100);a=p.parse_args()
    if not 1<=a.timeout<=120:p.error('timeout must be 1..120')
    run(a)
