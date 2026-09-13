"""Private native Breadbug display captures, reset and no-config fallback."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from scripts.preview_pikmin2_room import prepare
from experimental.pikmin2_breadbug_visual import install
from scripts.test_pikmin2_surface_native import executable_identity


def validate_log(text,enabled):
    if 'PASS P2_BREADBUG_VISUAL_FIXTURE' not in text:raise ValueError('Native visual fixture did not finish')
    if enabled:
        if text.count('P2_BREADBUG_VISUAL_READY')!=1 or 'P2_BREADBUG_VISUAL_DRAW' not in text or text.count('P2_BREADBUG_FIXTURE_GROUND')!=1:raise ValueError('Missing visual setup/draw/ground evidence')
    elif 'P2_BREADBUG_VISUAL_READY' in text or 'P2_BREADBUG_VISUAL_DRAW' in text:raise ValueError('Disabled visual profile rendered')


def run(args):
    args.output.mkdir(parents=True,exist_ok=False);report=dict(executable=executable_identity(args.exe),runs={})
    env=dict(os.environ,SDL_AUDIODRIVER='dummy');env['PATH']='C:/msys64/mingw64/bin;'+env['PATH']
    for mode in ('wait','move','nest','disabled'):
        directory=prepare(args.assets,args.converted,args.output/mode)
        # Keep original P1 practice map/collision/routes; only private actor scaffold.
        stage=args.assets/'dataDir/stages/chal0.ini'
        (directory/'assets/dataDir/stages/chal0.ini').write_bytes(stage.read_bytes())
        install(args.profile,directory)
        (directory/'p2-breadbug-visual.txt').rename(directory/'breadbug-fixture-profile.txt')
        (directory/'breadbug-runtime-mode.txt').write_text(mode)
        with (directory/'host.log').open('w') as out:
            process=subprocess.run([str(args.exe),'--experimental-pikmin2-room'],cwd=directory,env=env,stdout=out,stderr=subprocess.STDOUT,timeout=args.timeout)
        if process.returncode!=0:raise RuntimeError(f'Native visual fixture exit{process.returncode}: {directory}')
        text=(directory/'host.log').read_text(errors='replace');validate_log(text,mode!='disabled')
        images={}
        for name in ('breadbug-pose-a.ppm','breadbug-pose-b.ppm','breadbug-reset.ppm'):
            data=(directory/name).read_bytes()
            if not data.startswith(b'P6\n') or len(data)<10000:raise ValueError('Missing capture')
            images[name]=hashlib.sha256(data).hexdigest()
        report['runs'][mode]=dict(directory=str(directory),exit=process.returncode,captures=images,
            original_stage_sha256=hashlib.sha256(stage.read_bytes()).hexdigest(),
            actual_config=(directory/'p2-breadbug-visual.txt').read_text() if mode!='disabled' else None)
        (args.output/'result.json').write_text(json.dumps(report,indent=2));print('PASS Breadbug visual '+mode,flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('assets','converted','profile','exe','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--timeout',type=int,default=60);a=p.parse_args()
    if not 1<=a.timeout<=300:p.error('timeout must be1..300')
    for k,v in vars(a).items():
        if isinstance(v,Path):setattr(a,k,v.resolve())
    run(a)
