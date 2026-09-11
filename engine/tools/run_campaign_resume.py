from pathlib import Path
import os, subprocess, threading, uuid, _winapi, sys
root=Path(sys.argv[1]).resolve()
campaign = root / ('campaign-' + uuid.uuid4().hex[:8])
(campaign/'runs').mkdir(parents=True)
identity = uuid.uuid4().hex*2
for phase in ['save', 'resume', 'resume-again']:
    area='foh-day2'
    run=campaign/'runs'/uuid.uuid4().hex;run.mkdir()
    _winapi.CreateJunction('C:/Users/alari/bbft/dist/cohesion/pikmin/assets',str(run/'assets'))
    token=uuid.uuid4().hex*2
    boot=run/'bootstrap.txt'
    boot.write_text(f'PIKMIN_RANDOMIZER 5\nSESSION {token}\nFINGERPRINT {identity}\nPROFILE {area}\nCATALOG gameplay-checks-v5\nPLACEMENT identity-v1\nGOAL 25\nDAYS repeat-day29-v1\nCOLOR red\nSTARTING_FLARLIC 10\nEND\n')
    done=threading.Event()
    def refresh():
        while not done.is_set():
            pending=run/'state.tmp'; pending.write_text(f'PIKMIN_STATE 5 {token} 1 0 127 0 0 END\n')
            os.replace(pending,run/'state.txt');done.wait(.1)
    thread=threading.Thread(target=refresh);thread.start()
    env=dict(os.environ,PIKMIN_RANDOMIZER_TEST_BACKGROUND='1',SDL_AUDIODRIVER='dummy', PIKMIN_CAMPAIGN_TEST='1')
    env.pop('BBFT_PORT',None)
    startup=subprocess.STARTUPINFO(); startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow=0
    try:
        with (run/'native.log').open('w') as log:
            subprocess.run([str(root/'preview_dayend_skip.exe'),'--randomizer-seed',str(boot)],cwd=run,env=env,startupinfo=startup,stdout=log,stderr=subprocess.STDOUT,timeout=180,check=True)
        assert list((campaign/'campaign').glob('*.sav')), 'no committed checkpoint'
        lines = (run/'native.log').read_text(errors='replace').splitlines()
        expected = 'campaign resumed on day 8' if phase != 'save' else 'results/save completed'
        assert any('PASS DAYEND' in line and expected in line for line in lines), lines[-30:]
        assert len(list((campaign/'campaign').glob('*.sav'))) == 1, 'resume unexpectedly saved again'
        print(phase, [line for line in lines if 'DAYEND' in line or 'CAMPAIGN_' in line],flush=True)
    finally: done.set();thread.join()
