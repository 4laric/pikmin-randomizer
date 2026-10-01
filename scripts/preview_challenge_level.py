"""Isolated post-v0.1 layout preview. Never starts an AP seed/session."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experimental.levels import LEVELS, BY_KEY

def audit(assets):
    result=[]
    for level in LEVELS:
        ini=assets/'dataDir'/level.stage_file
        text=ini.read_text(encoding='shift_jis', errors='replace')
        directory=ini.with_suffix('')
        files=sorted(directory.glob('*.gen'))
        if not (directory/'default.gen').is_file(): raise ValueError(f'Missing default generator: {directory}')
        match=re.search(r'^map_file\s+(\S+)',text,re.M)
        if not match: raise ValueError(f'Missing map file: {ini}')
        if not (assets/'dataDir'/match[1]).is_file(): raise ValueError(f'Missing geometry: {match[1]}')
        clock=re.search(r'^day_multiply\s+(\S+)',text,re.M)
        result.append(dict(key=level.key,area_id=level.area_id,stage_file=level.stage_file,
                           geometry=match[1],day_multiplier=float(clock[1]) if clock else None,
                           generators=[dict(name=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]))
    return result

def main():
    p=argparse.ArgumentParser(description='Pikipelago experimental additional-level preview')
    p.add_argument('--assets',type=Path,required=True)
    p.add_argument('--audit',type=Path)
    p.add_argument('--level',choices=[l.key for l in LEVELS if l.layout=='challenge'])
    p.add_argument('--exe',type=Path)
    p.add_argument('--output',type=Path,default=Path('output/challenge-preview'))
    args=p.parse_args(); assets=args.assets.resolve()
    facts=audit(assets)
    if args.audit:
        args.audit.parent.mkdir(parents=True,exist_ok=True)
        args.audit.write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8')
    if not args.level: return
    if not args.exe: p.error('--level requires --exe built from the experimental branch')
    import _winapi
    level=BY_KEY[args.level]
    run=args.output.resolve()/args.level.replace(':','-')/uuid.uuid4().hex
    run.mkdir(parents=True)
    _winapi.CreateJunction(str(assets),str(run/'assets'))
    (run/'preview.json').write_text(json.dumps(dict(level=level.key,experimental=True,ap=False),indent=2))
    print(f'{level.name}: isolated preview at {run}',flush=True)
    with (run/'native.log').open('w',encoding='utf-8') as log:
        result=subprocess.run([str(args.exe.resolve()),'--experimental-challenge-level',str(level.area_id)],cwd=run,stdout=log,stderr=subprocess.STDOUT)
    if result.returncode: raise SystemExit(f'Native exit {result.returncode}; see {run / "native.log"}')

if __name__=='__main__': main()
