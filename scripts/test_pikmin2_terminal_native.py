"""Native repeated-entry terminal failures and interrupted-command recovery."""
import argparse
from copy import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from unittest.mock import patch

from experimental import pikmin2_campaign as cave
from scripts import play_pikmin2_surface_loop as loop
from scripts.test_pikmin2_surface_native import executable_identity


def fork_boundary(source,destination):
    state=json.loads((source/'session/surface-ledger.json').read_text())
    if state['phase']!='surface' or state['trip'] is not None:
        raise ValueError('Fixture baseline must be a completed native surface boundary')
    destination.mkdir(parents=True,exist_ok=False);(destination/'session').mkdir()
    for relative in ('loop-identity.json','session/surface-ledger.json'):
        shutil.copy2(source/relative,destination/relative)
    return state


def assert_terminal_preserved(before,after):
    if after['phase']!='failed' or after['trip']['checkpoint']['squad'] or after['trip']['token'] is not None:
        raise AssertionError('Native failure did not remain terminal')
    if (after['surface']['receipts']!=before['surface']['receipts']
            or after['trip']['checkpoint']['receipts']!=before['surface']['receipts']):
        raise AssertionError('Failure changed committed receipts')


class FaultProcess:
    def __init__(self,args,case):
        self.args,self.case=args,case;self.surfaces=0;self.caves=0;self.runs=[]
        self.interrupted=False

    def __call__(self,argv,*,cwd,**kwargs):
        cwd=Path(cwd);surface=(cwd/'manual-entrance.txt').exists()
        if surface:self.surfaces+=1
        else:self.caves+=1
        target='surface' if surface else 'cave'
        terminal=self.case.startswith(target+'_')
        pokos=sum(cave.read_ledger(cwd/'p2-economy.txt').values())
        if terminal:
            fault=self.case.split('_',1)[1]
            (cwd/'terminal-fixture.txt').write_text(f'{fault} {pokos}\n');exe=self.args.fault_exe
        else:
            visit=3 if surface and self.surfaces>1 else 2
            state=json.loads((self.args.output/'session/surface-ledger.json').read_text())
            position=state['surface']['position'] if surface else [0,0,0]
            (cwd/'repeat-fixture.txt').write_text(f'{target} {visit} {pokos} '+ ' '.join(map(str,position))+'\n')
            exe=self.args.repeat_exe
        env=dict(os.environ,SDL_AUDIODRIVER='dummy');env['PATH']='C:/msys64/mingw64/bin;'+env['PATH']
        result=subprocess.run([str(exe),'--experimental-pikmin2-room'],cwd=cwd,env=env,timeout=self.args.timeout,**kwargs)
        self.runs.append(dict(kind=target,terminal=terminal,exe=str(exe),run=str(cwd),exit=result.returncode))
        (self.args.output/'native-runs.json').write_text(json.dumps(self.runs,indent=2))
        text=(cwd/'native.log').read_text(errors='replace')
        if result.returncode not in (0,42):raise RuntimeError(f'Native fault/recovery fixture failed: {cwd}')
        if terminal and (result.returncode!=42 or 'P2_TERMINAL_INJECTED' not in text or 'failed=1' not in text):
            raise RuntimeError('Failure did not use production terminal checkpoint')
        if self.case=='handoff_interrupt' and surface and not self.interrupted:
            self.interrupted=True
            raise InterruptedError('fixture host interruption after native handoff')
        return result


def run_case(args,case):
    local=copy(args);local.output=args.output/case
    before=fork_boundary(args.baseline,local.output)
    local.surface_exe=args.repeat_exe;local.cave_exe=args.repeat_exe
    process=FaultProcess(local,case)
    interrupted=False
    if case=='commit_interrupt':
        unlink=Path.unlink;pending=local.output/'pending-surface-entry.json'
        def fail_cleanup(path,*a,**kw):
            nonlocal interrupted
            if path==pending and not interrupted:
                interrupted=True;raise InterruptedError('fixture host interruption after ledger commit')
            return unlink(path,*a,**kw)
        with patch.object(Path,'unlink',fail_cleanup):
            try:loop.play(local,process)
            except InterruptedError:pass
    elif case=='handoff_interrupt':
        try:loop.play(local,process)
        except InterruptedError:interrupted=True
    else:
        after=loop.play(local,process)
        assert_terminal_preserved(before,after)
        count=len(process.runs)
        def forbidden(*a,**kw):raise AssertionError('Terminal relaunch attempted native revival')
        assert loop.play(local,forbidden)==after and len(process.runs)==count
        expected=before['revision']+(1 if case.startswith('surface_') else 2)
        assert after['revision']==expected
        return dict(final=after,runs=process.runs,relaunch_native_calls=0)
    if not interrupted:raise AssertionError('Host interruption was not exercised')
    pending=local.output/'pending-surface-entry.json'
    if not pending.exists():raise AssertionError('Interrupted entry command was lost')
    command=json.loads(pending.read_text());token=command['token']
    interrupted_state=json.loads((local.output/'session/surface-ledger.json').read_text())
    expected=before['revision']+(1 if case=='commit_interrupt' else 0)
    assert interrupted_state['revision']==expected
    (local.output/'interrupted-command.json').write_text(json.dumps(command,indent=2))
    after=loop.play(local,process)
    assert after['phase']=='surface' and after['revision']==before['revision']+4
    assert after['surface']['receipts']==before['surface']['receipts']
    assert after['surface']['squad']==before['surface']['squad']
    assert after['surface']['health']==before['surface']['health']
    assert len(process.runs)==4 and [r['exit'] for r in process.runs]==[42,42,42,0]
    assert f'enter:{token}' in after['events']
    return dict(final=after,runs=process.runs,interrupted_revision=interrupted_state['revision'],
                preserved_entry_token=token,replayed_surface_process=False)


def run_test(args):
    args.output.mkdir(parents=True,exist_ok=False)
    report=dict(provenance=dict(fault=executable_identity(args.fault_exe),repeat=executable_identity(args.repeat_exe),
                baseline=str(args.baseline),baseline_sha256=hashlib.sha256((args.baseline/'session/surface-ledger.json').read_bytes()).hexdigest()),cases={})
    (args.output/'result.json').write_text(json.dumps(report,indent=2))
    for case in ('surface_extinction','surface_knockout','cave_extinction','cave_knockout','handoff_interrupt','commit_interrupt'):
        report['cases'][case]=run_case(args,case)
        (args.output/'result.json').write_text(json.dumps(report,indent=2))
        print('PASS '+case,flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('assets','source-import','pocket','treasure','pod1','pod2','purple','imported','fault-exe','repeat-exe','baseline','output'):
        p.add_argument('--'+name,type=Path,required=True)
    for name in ('transitions','snow','roster','transition-assets'):p.add_argument('--'+name,type=Path)
    p.add_argument('--timeout',type=int,default=60);args=p.parse_args()
    if not 1<=args.timeout<=300:p.error('timeout must be1..300 seconds')
    for name,value in vars(args).items():
        if isinstance(value,Path):setattr(args,name,value.resolve())
    run_test(args)
