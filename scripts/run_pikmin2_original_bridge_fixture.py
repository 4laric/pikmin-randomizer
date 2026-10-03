"""Bounded private bridge factory/work-hook/cache fixture (no gameplay claim)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from randomizer.seed import generate,validate
from randomizer.session import Session
from randomizer.runner import NativeRun
from scripts.preview_pikmin2_room import overlay


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    for field in ['exe','native','session','assets','resources']:
        cli.add_argument('--'+field,type=Path,required=True)
    cli.add_argument('--expected-native',required=True)
    cli.add_argument('--captain-down',action='store_true')
    args=cli.parse_args()
    exe=args.exe.resolve(strict=True);native=args.native.resolve(strict=True)
    session=args.session.resolve();assets=args.assets.resolve(strict=True);resources=args.resources.resolve(strict=True)
    if session.exists():raise ValueError('Fresh private session required')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=native,text=True).strip()
    if head!=args.expected_native or subprocess.check_output(['git','status','--porcelain'],cwd=native,text=True).strip():
        raise ValueError('Exact clean native pin required')
    roothead=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    manifest=generate('original-bridge-1262','solo',starting_area='impact',starting_color='red',starting_flarlic=2)
    validate(manifest);session.mkdir(parents=True)
    (session/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    state=Session(manifest,session);run=NativeRun(state);run.write_state(True)
    overrides={'p2-original/bridges/type%d.mod'%i:(resources/folder/'bridge.mod').read_bytes() for i,folder in enumerate(['s_bridge','slope_u','l_bridge'])}
    overlay(assets,run.directory/'assets',overrides)
    source=resources/'bridges.txt';(run.directory/'bridges.txt').write_bytes(source.read_bytes())
    home=session/'private-home'
    for part in ['','config','cache','data','state','save']:(home/part).mkdir(parents=True,exist_ok=True)
    env={k:v for k,v in os.environ.items() if not k.casefold().startswith(('pikmin_','p2_','coop_','bbft_','nectar_','sdl_','xdg_')) and k not in ['HOME','DISPLAY']}
    env.update(HOME=str(home),XDG_CONFIG_HOME=str(home/'config'),XDG_CACHE_HOME=str(home/'cache'),XDG_DATA_HOME=str(home/'data'),XDG_STATE_HOME=str(home/'state'),NECTAR_SAVE_DIR=str(home/'save'),NECTAR_EXECUTABLE_PATH=str(exe),PIKMIN_SETTINGS_PATH=str(run.directory/'pikmin_settings.conf'),PIKMIN_RANDOMIZER_TEST_BACKGROUND='1',PIKMIN_RANDOMIZER_AUTOPLAY='0',PIKMIN_P2_ROOM_WINDOW='960x540',SDL_AUDIODRIVER='dummy',LIBGL_ALWAYS_SOFTWARE='1')
    command=[str(exe),'--randomizer-seed',str(run.bootstrap),'--bridge-manifest='+str(run.directory/'bridges.txt')]
    if args.captain_down:command.append('--force-captain-down')
    if os.name!='nt':command=['xvfb-run','-a','-s','-screen 0 1280x720x24 +extension GLX',*command]
    inputs=dict(native=head,root=roothead,exe_sha256=sha(exe),manifest_sha256=sha(source),geometry={key:hashlib.sha256(data).hexdigest() for key,data in overrides.items()},argv=command,timeout=65,baseline='20Pikmin 960x540 centered',full_course_gameplay=False,injected_completion=True)
    (run.directory/'run-inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
    print(json.dumps({'directory':str(run.directory),'inputs':inputs}),flush=True)
    start=time.monotonic();proc=None;timed_out=False
    try:
        with (run.directory/'native.log').open('wb') as log:
            proc=subprocess.Popen(command,cwd=run.directory,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            while proc.poll() is None:
                run.poll();run.write_state(True)
                if time.monotonic()-start>65:
                    timed_out=True
                    if os.name=='nt':proc.kill()
                    else:os.killpg(proc.pid,signal.SIGKILL)
                    break
                time.sleep(.1)
            code=proc.wait(timeout=5)
    finally:
        if proc and proc.poll() is None:
            if os.name=='nt':proc.kill()
            else:os.killpg(proc.pid,signal.SIGKILL)
            proc.wait(timeout=5)
    text=(run.directory/'native.log').read_text(errors='replace')
    marker='PASS ORIGINAL_BRIDGE_NATIVE'
    if args.captain_down:passed=code==86 and 'P2_FIXTURE_CAPTAIN_DOWN' in text and marker not in text
    else:passed=code==0 and marker in text and 'ORIGINAL_BRIDGE_BASELINE pikmin=20 window=960x540' in text and 'P2_FIXTURE_CAPTAIN_DOWN' not in text
    result=dict(passed=passed and not timed_out,exit_code=code,timed_out=timed_out,seconds=time.monotonic()-start,handshake=run.handshaken,log_sha256=sha(run.directory/'native.log'),owned_pid=proc.pid,child_reaped=proc.poll() is not None,full_course_gameplay=False,injected_completion=True)
    (run.directory/'runtime-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
