"""Live native benefit fixture, with delayed receipts; requires TEST_HOOKS build."""
import argparse, os, subprocess, sys, time, _winapi
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.seed import generate
from randomizer.session import Session
from randomizer.runner import NativeRun
from randomizer.catalog import ITEM_IDS
from randomizer.benefits import BENEFIT_ITEMS, WHISTLE, PLUCK
p=argparse.ArgumentParser()
for name in ('exe','assets','output'): p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args()
for color in ('red','yellow','blue'):
    m=generate('benefits-native-'+color,'ap',collection_checks=True,starting_color=color,starting_flarlic=1)
    s=Session(m,a.output.resolve()/color);s.bind_ap('benefit-fixture',0,1)
    r=NativeRun(s);r.write_state(True)
    _winapi.CreateJunction(str(a.assets.resolve()),str(r.directory/'assets'))
    env=dict(os.environ,PIKMIN_RANDOMIZER_TEST_BACKGROUND='1',SDL_AUDIODRIVER='dummy',PIKMIN_RANDOMIZER_TEST_SCRIPT='benefits')
    env.pop('BBFT_PORT',None)
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW
    log=r.directory/'native.log'
    with log.open('w',encoding='utf-8') as stream:
        process=subprocess.Popen([str(a.exe.resolve()),'--randomizer-seed',str(r.bootstrap)],cwd=r.directory,env=env,startupinfo=startup,stdout=stream,stderr=subprocess.STDOUT)
        try:
            sent=False;deadline=time.monotonic()+90
            while process.poll() is None and time.monotonic()<deadline:
                r.poll()
                if not sent and 'TEST_ONLY benefits_ready' in log.read_text(errors='replace'):
                    ids=[ITEM_IDS[n] for n in BENEFIT_ITEMS]+[ITEM_IDS[WHISTLE],ITEM_IDS[PLUCK]]
                    s.receive(0,ids);s.receive(0,ids);sent=True
                r.write_state(True);time.sleep(.1)
            assert process.poll()==0 and 'TEST_ONLY benefits_pass' in log.read_text(errors='replace'), f'exit {process.poll()}; {log}'
        finally:
            if process.poll() is None:process.terminate();process.wait(timeout=10)
    print('PASS',color,log)
