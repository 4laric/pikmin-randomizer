"""Smoke-test five isolated native story-layout boots; no AP or user saves."""
import argparse, os, subprocess, time, uuid, _winapi
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--exe',type=Path,required=True);p.add_argument('--assets',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
for area in range(5):
    run=a.output.resolve()/str(area)/uuid.uuid4().hex;run.mkdir(parents=True)
    _winapi.CreateJunction(str(a.assets.resolve()),str(run/'assets'))
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW
    with (run/'native.log').open('w',encoding='utf-8') as log:
        proc=subprocess.Popen([str(a.exe.resolve()),'--experimental-challenge-level',str(area)],cwd=run,stdout=log,stderr=subprocess.STDOUT,startupinfo=startup,env=dict(os.environ,SDL_AUDIODRIVER='dummy'))
        try:
            deadline=time.monotonic()+45
            while proc.poll() is None and time.monotonic()<deadline:
                text=(run/'native.log').read_text(encoding='utf-8',errors='replace')
                if f'CHALLENGE_LAYOUT_READY id=challenge-{area}' in text and f'stages/chal{area}/default.gen' in text and text.count('[PC Port] FPS:')>=4: break
                time.sleep(.2)
            assert proc.poll() is None,text[-3000:]
            assert f'file=stages/chal{area}.ini story=1' in text and f'stages/chal{area}/default.gen' in text,text[-3000:]
            assert text.count('[PC Port] FPS:')>=4, text[-3000:]
            print(f'PASS challenge-{area}: native stage selected, layout generator loaded, process alive; {run}',flush=True)
        finally:
            if proc.poll() is None: proc.terminate();proc.wait(timeout=10)
