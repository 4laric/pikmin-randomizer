"""Terminate an owned Python host at durable native entry boundaries."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch

from scripts import play_pikmin2_surface_loop as loop
from scripts.test_pikmin2_terminal_native import FaultProcess, fork_boundary
from scripts.test_pikmin2_surface_native import executable_identity


def pause_boundary(args):
    marker=args.output/'kill-ready.json'
    marker.write_text(json.dumps(dict(pid=os.getpid(),boundary=args.boundary)))
    # Parent owns this process and keeps stdin open until it terminates us.
    sys.stdin.buffer.read(1)
    raise RuntimeError('Parent released boundary without terminating host')


def child(config,resume):
    data=json.loads(config.read_text())
    args=SimpleNamespace(**{k:Path(v) if k not in ('timeout','boundary') and v is not None else v for k,v in data.items()})
    args.surface_exe=args.repeat_exe;args.cave_exe=args.repeat_exe
    process=FaultProcess(args,'healthy')
    if resume:
        process.runs=json.loads((args.output/'native-runs.json').read_text())
        process.surfaces=sum(r['kind']=='surface' for r in process.runs)
        process.caves=sum(r['kind']=='cave' for r in process.runs)
    def native(*a,**kw):
        result=process(*a,**kw)
        if not resume and args.boundary=='handoff':pause_boundary(args)
        return result
    unlink=Path.unlink
    def cleanup(path,*a,**kw):
        if not resume and path==args.output/'pending-surface-entry.json':pause_boundary(args)
        return unlink(path,*a,**kw)
    with patch.object(Path,'unlink',cleanup):
        result=loop.play(args,native)
    (args.output/'child-result.json').write_text(json.dumps(result,indent=2))


def kill_at_marker(process,marker,boundary,timeout):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if process.poll() is not None:raise RuntimeError('Host exited before requested boundary')
        if marker.exists():
            try:data=json.loads(marker.read_text())
            except json.JSONDecodeError:continue
            if data!={'pid':process.pid,'boundary':boundary}:raise RuntimeError('Boundary marker does not identify owned host')
            process.kill();process.wait(timeout=10)
            return dict(pid=process.pid,exit=process.returncode,boundary=boundary)
        time.sleep(.05)
    raise TimeoutError('Owned host did not reach kill boundary')


def run(args):
    args.output.mkdir(parents=True,exist_ok=False)
    report=dict(executable=executable_identity(args.repeat_exe),
                baseline=str(args.baseline),
                baseline_sha256=hashlib.sha256((args.baseline/'session/surface-ledger.json').read_bytes()).hexdigest(),cases={})
    for boundary in ('handoff','commit'):
        destination=args.output/boundary
        before=fork_boundary(args.baseline,destination)
        config={k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()}
        config.update(output=str(destination),boundary=boundary)
        path=destination/'host-config.json';path.write_text(json.dumps(config))
        command=[sys.executable,'-m','scripts.test_pikmin2_host_kill_native','--child',str(path)]
        with (destination/'host-before.log').open('w') as log:
            process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT)
            try:killed=kill_at_marker(process,destination/'kill-ready.json',boundary,args.timeout)
            finally:
                if process.poll() is None:process.kill();process.wait(timeout=10)
                process.stdin.close()
        state=json.loads((destination/'session/surface-ledger.json').read_text())
        assert state['revision']==before['revision']+(boundary=='commit')
        pending=json.loads((destination/'pending-surface-entry.json').read_text())
        (destination/'preserved-command.json').write_text(json.dumps(pending,indent=2))
        with (destination/'host-resume.log').open('w') as log:
            result=subprocess.run(command+['--resume'],stdout=log,stderr=subprocess.STDOUT,timeout=args.timeout*4)
        assert result.returncode==0,'Relaunched host failed; inspect host-resume.log'
        after=json.loads((destination/'child-result.json').read_text())
        runs=json.loads((destination/'native-runs.json').read_text())
        assert after['phase']=='surface' and after['revision']==before['revision']+4
        assert all(after['surface'][f]==before['surface'][f] for f in ('squad','health','receipts'))
        assert f"enter:{pending['token']}" in after['events']
        assert [r['exit'] for r in runs]==[42,42,42,0]
        report['cases'][boundary]=dict(killed=killed,interrupted_revision=state['revision'],token=pending['token'],final=after,runs=runs)
        (args.output/'result.json').write_text(json.dumps(report,indent=2))
        print('PASS actual host termination '+boundary,flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--child',type=Path);p.add_argument('--resume',action='store_true')
    for name in ('assets','source-import','pocket','treasure','pod1','pod2','purple','imported','repeat-exe','baseline','output','transitions','snow','roster','transition-assets'):
        p.add_argument('--'+name,type=Path)
    p.add_argument('--timeout',type=int,default=60)
    args=p.parse_args()
    if args.child:child(args.child,args.resume)
    else:
        del args.child;del args.resume
        if not 1<=args.timeout<=300:p.error('timeout must be 1..300 seconds')
        for name in ('assets','source_import','pocket','treasure','pod1','pod2','purple','imported','repeat_exe','baseline','output'):
            if getattr(args,name) is None:p.error('--'+name.replace('_','-')+' is required')
        for k,v in vars(args).items():
            if isinstance(v,Path):setattr(args,k,v.resolve())
        run(args)
