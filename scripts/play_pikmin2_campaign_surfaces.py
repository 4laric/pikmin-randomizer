"""Launch a fresh four-course terrain/travel candidate, preserving existing saves."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from scripts.stage_pikmin2_campaign_surfaces import COURSES


def launch(run, exe, course='tutorial', process=subprocess.run):
    run,exe=Path(run).resolve(),Path(exe).resolve()
    if course not in COURSES:
        raise ValueError('Unsupported campaign course')
    record=json.loads((run/'campaign-surface-inputs.json').read_text())
    if record.get('schema')!=1 or set(record.get('courses',{}))!=set(COURSES):
        raise ValueError('Four-course staging record required')
    for name, expected in record['files'].items():
        path=run/'assets'/name
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise ValueError('Staged campaign content changed: '+name)
    if (run/'save/p2-campaign').exists():
        raise ValueError('Native saves exist; preserve them. Fresh-process resume is pending; stage a new output for a fresh test.')
    if not exe.is_file():
        raise ValueError('Native production executable missing')
    print('Terrain travel candidate; native P1 landing adapters, fixture squads, no retail actor or story progression acceptance.',flush=True)
    return process([str(exe),'--experimental-pikmin2-campaign',course],cwd=run).returncode


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--exe',type=Path,required=True)
    p.add_argument('--course',choices=COURSES,default='tutorial')
    a=p.parse_args()
    raise SystemExit(launch(a.run,a.exe,a.course))
