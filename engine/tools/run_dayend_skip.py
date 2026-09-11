from pathlib import Path
import os, subprocess, threading, uuid, _winapi, sys
root=Path(sys.argv[1]).resolve()
for area in ['foh-day2']:
    run=root/(area+'-'+uuid.uuid4().hex[:8]);run.mkdir()
    _winapi.CreateJunction('C:/Users/alari/bbft/dist/cohesion/pikmin/assets',str(run/'assets'))
    token=uuid.uuid4().hex*2
    boot=run/'bootstrap.txt'
    boot.write_text(f'PIKMIN_RANDOMIZER 5\nSESSION {token}\nFINGERPRINT {token}\nPROFILE {area}\nCATALOG gameplay-checks-v5\nPLACEMENT identity-v1\nGOAL 25\nDAYS repeat-day29-v1\nCOLOR red\nSTARTING_FLARLIC 10\nEND\n')
    done=threading.Event()
    def refresh():
        while not done.is_set():
            pending=run/'state.tmp'; pending.write_text(f'PIKMIN_STATE 5 {token} 1 0 127 0 0 END\n')
            os.replace(pending,run/'state.txt');done.wait(.1)
    thread=threading.Thread(target=refresh);thread.start()
    env=dict(os.environ,PIKMIN_RANDOMIZER_TEST_BACKGROUND='1',SDL_AUDIODRIVER='dummy')
    env.pop('BBFT_PORT',None)
    startup=subprocess.STARTUPINFO(); startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow=0
    try:
        with (run/'native.log').open('w') as log:
            subprocess.run([str(root/'preview_dayend_skip.exe'),'--randomizer-seed',str(boot)],cwd=run,env=env,startupinfo=startup,stdout=log,stderr=subprocess.STDOUT,timeout=180,check=True)
        print(area, [line for line in (run/'native.log').read_text(errors='replace').splitlines() if 'DAYEND' in line],flush=True)
    finally: done.set();thread.join()
