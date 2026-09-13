"""Fresh, private stages for Snow crossfade renderer and lifecycle acceptance."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
from scripts.preview_pikmin2_room import overlay

def stage(source, output):
    source, output = source.resolve(), output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    overlay(source/'assets', output/'assets', {})
    for name in ('p2-pod.txt', 'p2-snow.txt', 'p2-snow-actors.txt',
                 'p2-snow-interpolation.txt', 'p2-snow-skeletal.txt',
                 'p2-snow-skin.txt', 'p2-snow-joints.txt'):
        shutil.copyfile(source/name, output/name)
    (output/'p2-snow-crossfade.txt').write_text('P2_SNOW_CROSSFADE_1\n')
    return output

def run(exe, directory):
    exe=exe.resolve()
    provenance=json.loads((exe.parent/'provenance.json').read_text())
    expected=provenance.get('artifacts',{}).get(str(exe),{}).get('sha256')
    digest=hashlib.sha256(exe.read_bytes()).hexdigest()
    if provenance.get('status')!='built' or digest!=expected:
        raise ValueError('Require completed, unchanged isolated fixture build')
    env=dict(os.environ, PATH='C:/msys64/mingw64/bin;'+os.environ.get('PATH',''),
             SDL_AUDIODRIVER='dummy', PIKMIN_RANDOMIZER_TEST_BACKGROUND='1')
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    with (directory/'native.log').open('x') as log:
        result=subprocess.run([str(exe),'--experimental-pikmin2-room'],cwd=directory,
                              env=env,stdout=log,stderr=subprocess.STDOUT,
                              startupinfo=startup,timeout=180)
    text=(directory/'native.log').read_text(errors='replace')
    unchanged=hashlib.sha256(exe.read_bytes()).hexdigest()==digest
    report=dict(exit=result.returncode,exe_sha256=digest,exe_unchanged=unchanged,
                passed=result.returncode==0 and 'PASS CROSSFADE_RENDER' in text and unchanged)
    (directory/'result.json').write_text(json.dumps(report,indent=2))
    return report

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','output','exe'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();report=run(a.exe,stage(a.source,a.output));print(json.dumps(report,indent=2))
    raise SystemExit(0 if report['passed'] else 1)
