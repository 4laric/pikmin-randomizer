"""Pre-flight for new reduced-mode lanes: is each lane's issue or any owned file held by an unfinished lane?

  py -3.12 check_lanes.py --root <workspace> rd-a rd-b ...   (read-only; setup-lanes.ps1 enforces the same rule)
"""
import argparse
import json
from pathlib import Path

import reduced_setup as rs

p = argparse.ArgumentParser()
p.add_argument('--root', type=Path, required=True)
p.add_argument('lanes', nargs='+')
a = p.parse_args()
rs.release(rs.RELEASE)
from workflow.registry import Registry
state = Registry(a.root / 'output/workflow/registry.sqlite3', a.root).snapshot()
m = json.loads((a.root / 'output/reduced/lanes.json').read_text(encoding='utf-8'))
for lane in a.lanes:
    s = m['lanes'][lane]
    probs = []
    for o in state['lanes'].values():
        if o['state'] == 'done' or o['lane'] == lane:
            continue
        if o['issue'] == s['issue']:
            probs.append(f"issue #{s['issue']} held by {o['lane']} ({o['state']})")
        c = {f.casefold() for f in o['owned_files']} & {f.casefold() for f in s['owned_files']}
        if c:
            probs.append(f"{sorted(c)} held by {o['lane']} ({o['state']})")
    print(lane, 'OK' if not probs else probs)
