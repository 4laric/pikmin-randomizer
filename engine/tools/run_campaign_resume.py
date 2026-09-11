"""Save through results, then restore twice in separate native processes."""
from pathlib import Path
import argparse, os, subprocess, threading, uuid, _winapi, sys
p=argparse.ArgumentParser()
p.add_argument('output',type=Path)
p.add_argument('--assets',type=Path,default=Path('C:/Users/alari/bbft/dist/cohesion/pikmin/assets'))
p.add_argument('--campaign-enemies',action='store_true')
a=p.parse_args();root=a.output.resolve()
campaign=root/('campaign-'+uuid.uuid4().hex[:8]);(campaign/'runs').mkdir(parents=True)
identity=uuid.uuid4().hex*2
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
if a.campaign_enemies:
    from randomizer.seed import generate
    from randomizer.session import Session
    from randomizer.runner import NativeRun
    from randomizer.catalog import ITEM_IDS
    manifest=generate('campaign-save-test','ap',campaign_enemies=True,starting_area='navel',starting_flarlic=10)
for phase in ('save','resume','resume-again'):
    if a.campaign_enemies:
        session=Session(manifest,campaign)
        session.bind_ap("campaign-save-fixture",0,1)
        if not session.data['received']:
            session.receive(0,[uid for name,uid in ITEM_IDS.items() if uid in session.allowed_items and (name.endswith('Onion') or name.endswith('Access'))])
        native_run=NativeRun(session);run=native_run.directory;boot=native_run.bootstrap
    else:
        token=uuid.uuid4().hex*2;run=campaign/'runs'/token;run.mkdir();boot=run/'bootstrap.txt'
        boot.write_text(f'PIKMIN_RANDOMIZER 5\nSESSION {token}\nFINGERPRINT {identity}\nPROFILE foh-day2\nCATALOG gameplay-checks-v5\nPLACEMENT identity-v1\nGOAL 25\nDAYS repeat-day29-v1\nCOLOR red\nSTARTING_FLARLIC 10\nEND\n')
    _winapi.CreateJunction(str(a.assets.resolve()),str(run/'assets'))
    done=threading.Event()
    def refresh():
        while not done.is_set():
            if a.campaign_enemies:native_run.write_state(True)
            else:
                pending=run/'state.tmp';pending.write_text(f'PIKMIN_STATE 5 {token} 1 0 127 0 0 END\n');os.replace(pending,run/'state.txt')
            done.wait(.1)
    thread=threading.Thread(target=refresh);thread.start()
    env=dict(os.environ,PIKMIN_RANDOMIZER_TEST_BACKGROUND='1',SDL_AUDIODRIVER='dummy',PIKMIN_CAMPAIGN_TEST='1')
    env.pop('BBFT_PORT',None)
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    try:
        with (run/'native.log').open('w') as log:
            subprocess.run([str(root/'preview_dayend_skip.exe'),'--randomizer-seed',str(boot)],cwd=run,env=env,startupinfo=startup,stdout=log,stderr=subprocess.STDOUT,timeout=180,check=True)
        lines=(run/'native.log').read_text(errors='replace').splitlines()
        expected='campaign resumed on day 8' if phase!='save' else 'results/save completed'
        assert any('PASS DAYEND' in line and expected in line for line in lines),lines[-30:]
        assert len(list((campaign/'campaign').glob('*.sav')))==1,'unexpected checkpoint count'
        print(phase,[line for line in lines if 'DAYEND' in line or 'CAMPAIGN_' in line],flush=True)
    finally:done.set();thread.join()
