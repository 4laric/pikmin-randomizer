"""Production startup and actual mixed adult births; not a physical combat test."""
import argparse, json, os, subprocess, sys, time, _winapi
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from randomizer.seed import generate
from randomizer.session import Session
from randomizer.runner import NativeRun
from randomizer.enemy_slots import verify_source_assets
p=argparse.ArgumentParser()
for name in ('exe','assets','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();verify_source_assets(a.assets)
for area in ('forest','spring'):
    m=generate('slot-production-'+area,'ap',per_spawn_enemies=True,starting_area=area,starting_color='yellow',starting_flarlic=1)
    s=Session(m,a.output.resolve()/area);r=NativeRun(s);r.write_state(True)
    _winapi.CreateJunction(str(a.assets.resolve()),str(r.directory/'assets'))
    env=dict(os.environ,PIKMIN_RANDOMIZER_TEST_BACKGROUND='1',SDL_AUDIODRIVER='dummy')
    env.pop('BBFT_PORT',None);env.pop('PIKMIN_RANDOMIZER_TEST_SCRIPT',None)
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW
    log=r.directory/'native.log'
    with log.open('w',encoding='utf-8') as stream:
        process=subprocess.Popen([str(a.exe.resolve()),'--randomizer-seed',str(r.bootstrap)],cwd=r.directory,env=env,startupinfo=startup,stdout=stream,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+60
            while process.poll() is None and time.monotonic()<deadline:
                r.poll();r.write_state(True)
                text=log.read_text(errors='replace')
                if 'PIKMIN_WORLD_RENDERED' in text and 'color=2 field=10' in text:break
                time.sleep(.1)
            else:raise AssertionError(f'production startup failed: {log}')
            choices={row['uid']:row['actual'] for row in m['spawn_layout']['assignments']}
            adults=[]
            for line in text.splitlines():
                if not line.startswith('ENEMY_SLOT_BIRTH '):continue
                fields=dict(x.split('=',1) for x in line.split()[1:])
                if int(fields['original']) in (4,32):
                    assert choices[int(fields['uid'])]==int(fields['actual'])
                    adults.append(int(fields['actual']))
                else:assert fields['original']==fields['actual']
            assert set(adults)=={4,32} and r.handshaken and 'TEST_ONLY' not in text
            print('PASS production',area,'mixed adult births match seed; yellow cap 10, rendered, handshake',flush=True)
        finally:
            if process.poll() is None:process.terminate();process.wait(timeout=10)
