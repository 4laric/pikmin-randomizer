"""One manual bounded entrance -> production cave -> entrance trip per session."""
import argparse
import json
from pathlib import Path
import subprocess
import uuid

from experimental import pikmin2_campaign as cave
from experimental.pikmin2_surface_ledger import SurfaceLedger
from experimental.pikmin2_surface_runner import NativeContent, SurfaceRunner
from randomizer.session import SessionLock, atomic_write
from scripts.test_pikmin2_surface_native import executable_identity
from scripts.test_pikmin2_surface_roundtrip import stage_surface, native_position

WARNING = ('BOUNDED MANUAL PROTOTYPE: one cave trip per session; radius-60 invisible fence. '
           'Terrain outside the fence is visual only; water gameplay is unavailable. '
           'Entrance cargo pickup is disabled. F6 at the orange entrance marker '
           'opens confirmation. Cave uses normal gameplay and F6 at hole/geyser. '
           'Saves occur at cave boundaries, not mid-floor; surface clock/world state is not saved. '
           'Return supports at most20 survivors; larger parties are preserved in the ledger but cannot '
           'be staged here. Returned entrance is interactive with re-entry disabled.')


def initial_snapshot():
    return dict(region='valley_of_repose',day=2,time=8.5,position=[-210.,80.,1160.],
                squad=[dict(species='red',maturity=0) for _ in range(20)],health=1.,receipts={})


def consume_entry(directory, command, content):
    """Replay a completed native command; never infer success from process exit alone."""
    run=Path(command['run']);state=command['checkpoint'];token=command['token']
    handed=cave.transition(state,token,(run/'p2-cave-transfer.txt').read_text(),
                           cave.read_ledger(run/'p2-economy.txt'),{})
    if handed['status']=='failed':
        atomic_write(directory/'failed-entry.json',json.dumps(dict(run=str(run),token=token,
                     reason='Native surface extinction/knockout; no automatic revival')))
        raise RuntimeError('Entrance party failed; session retained and cannot restart with fresh Pikmin')
    snapshot=dict(initial_snapshot(),position=native_position(run,token))
    snapshot.update({k:handed[k] for k in ('squad','health','receipts')})
    ledger=SurfaceLedger(directory/'session',content.identity,command['campaign'])
    ledger.create(snapshot)
    ledger.enter_cave(0,command['trip'])
    return ledger


def launch_surface(args, content, snapshot, mode, process):
    if len(snapshot['squad'])>20:
        raise ValueError('Returned party exceeds20; ledger preserved, no Pikmin truncated. Larger entrance roster is not implemented.')
    run,state,token=stage_surface(args,snapshot,content.identity,mode)
    # Only the new manual App consumes this. Never stage test-driver control flags.
    (run/'surface-fixture.txt').unlink()
    (run/'manual-entrance.txt').write_text(mode+'\n')
    return run,state,token


def play(args, process=subprocess.run):
    print(WARNING,flush=True)
    args.output.mkdir(parents=True,exist_ok=True)
    content=NativeContent(args.assets,args.imported,[args.pod1,args.pod2],args.purple,args.treasure,
                          args.transitions,args.snow,args.roster,args.transition_assets)
    with SessionLock(args.output/'manual-host-lease'):
        if any((args.output/name).exists() for name in ('failed-entry.json','failed-return.json')):
            raise RuntimeError('This entrance session failed; retained without revival. Use a new output for a new test.')
        provenance=dict(surface=executable_identity(args.surface_exe),cave=executable_identity(args.cave_exe))
        atomic_write(args.output/f'launch-{uuid.uuid4().hex}.json',json.dumps(provenance,indent=2))
        command_path=args.output/'entry-command.json'
        if command_path.exists():
            command=json.loads(command_path.read_text())
            if command['content']!=content.identity:raise ValueError('Content changed; retain original bundle')
        else:
            run,state,token=launch_surface(args,content,initial_snapshot(),'enter',process)
            command=dict(content=content.identity,campaign=uuid.uuid4().hex,trip=uuid.uuid4().hex,
                         run=str(run),checkpoint=state,token=token)
            atomic_write(command_path,json.dumps(command,indent=2))
        ledger=SurfaceLedger(args.output/'session',content.identity,command['campaign'])
        if not ledger.path.exists():
            run=Path(command['run'])
            if not (run/'p2-cave-transfer.txt').exists():
                with (run/'native.log').open('w') as log:
                    result=process([str(args.surface_exe),'--experimental-pikmin2-room'],cwd=run,
                                   stdout=log,stderr=subprocess.STDOUT)
                if result.returncode==0:return None
                if result.returncode!=42:raise RuntimeError(f'Entrance exit {result.returncode}; inspect {run / "native.log"}')
            ledger=consume_entry(args.output,command,content)
        else:
            current=ledger.read()
            # Recovery after creating the authoritative ledger but before suspending it.
            if current['revision']==0:ledger.enter_cave(0,command['trip'])
        final=SurfaceRunner(ledger,content,args.cave_exe,process).resume()
        if final['phase']!='surface':
            print(f'Campaign phase: {final["phase"]}; boundary state retained.',flush=True)
            return final
        run,returned_state,token=launch_surface(args,content,final['surface'],'returned',process)
        with (run/'native.log').open('w') as log:
            result=process([str(args.surface_exe),'--experimental-pikmin2-room'],cwd=run,
                           stdout=log,stderr=subprocess.STDOUT)
        if result.returncode==42:
            handed=cave.transition(returned_state,token,(run/'p2-cave-transfer.txt').read_text(),
                                   cave.read_ledger(run/'p2-economy.txt'),{})
            if handed['status']=='failed':
                atomic_write(args.output/'failed-return.json',json.dumps(dict(run=str(run),token=token,
                             reason='Native returned-surface extinction/knockout; no automatic revival')))
        if result.returncode:raise RuntimeError(f'Returned entrance exit {result.returncode}; cave result retained; {run / "native.log"}')
        return final


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('assets','source-import','pocket','treasure','pod1','pod2','purple','imported','surface-exe','cave-exe','output'):
        p.add_argument('--'+name,type=Path,required=True)
    for name in ('transitions','snow','roster','transition-assets'):p.add_argument('--'+name,type=Path)
    args=p.parse_args()
    for name,value in vars(args).items():
        if isinstance(value,Path):setattr(args,name,value.resolve())
    play(args)
