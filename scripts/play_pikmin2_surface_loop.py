"""Repeated bounded surface visits using one authoritative SurfaceLedger."""
import argparse
import json
from pathlib import Path
import subprocess
import uuid

from experimental import pikmin2_campaign as cave
from experimental.pikmin2_surface_ledger import SurfaceLedger
from experimental.pikmin2_surface_runner import NativeContent, SurfaceRunner
from randomizer.session import SessionLock, atomic_write
from scripts.play_pikmin2_surface import initial_snapshot, launch_surface
from scripts.test_pikmin2_surface_native import executable_identity
from scripts.test_pikmin2_surface_roundtrip import native_position

WARNING = ('BOUNDED REPEAT-VISIT PROTOTYPE: radius60 invisible fence; outside terrain is visual only. '
           'F6 at orange marker enters/re-enters Emergence Cave. F6 at cave hole/geyser saves a boundary. '
           'No mid-floor/world/day-clock save or native surface water support. Entrance cargo pickup '
           'disabled. Maximum20 returned survivors; larger parties remain durable but cannot be staged. '
           'Repeated treasure deliveries retain their original receipt IDs and do not add duplicate Pokos.')


def capture_entry(command):
    run=Path(command['run'])
    return dict(text=(run/'p2-cave-transfer.txt').read_text(),
                position=native_position(run,command['token']) if (run/'surface-position.txt').exists() else None,
                receipts=cave.read_ledger(run/'p2-economy.txt'))


def consume_command(path, ledger):
    """Persist a replayable command before committing the sole authoritative ledger."""
    command=json.loads(path.read_text())
    if command['campaign']!=ledger.campaign or command['content']!=ledger.content:
        raise ValueError('Surface command belongs to another campaign/content')
    if 'native_entry' not in command:
        command['native_entry']=capture_entry(command)
        atomic_write(path,json.dumps(command,indent=2))
    state=ledger.enter_cave(command['revision'],command['token'],native_entry=command['native_entry'])
    path.unlink()
    return state


def play(args, process=subprocess.run):
    print(WARNING,flush=True)
    args.output.mkdir(parents=True,exist_ok=True)
    content=NativeContent(args.assets,args.imported,[args.pod1,args.pod2],args.purple,args.treasure,
                          args.transitions,args.snow,args.roster,args.transition_assets,
                          source_import=args.source_import,pocket=args.pocket)
    with SessionLock(args.output/'manual-host-lease'):
        if (args.output/'entry-command.json').exists():
            raise ValueError('One-trip output belongs to the previous launcher; use a new repeat-visit output')
        identity_path=args.output/'loop-identity.json'
        if identity_path.exists():
            identity=json.loads(identity_path.read_text())
            if identity['content']!=content.identity:raise ValueError('Content changed or legacy surface identity; retain original bundle and launcher; session preserved')
        else:
            if (args.output/'session').exists():raise ValueError('Missing loop identity; refusing to reset existing session')
            identity=dict(content=content.identity,campaign=uuid.uuid4().hex)
            atomic_write(identity_path,json.dumps(identity,indent=2))
        ledger=SurfaceLedger(args.output/'session',content.identity,identity['campaign'])
        ledger.create(initial_snapshot())
        provenance=dict(surface=executable_identity(args.surface_exe),cave=executable_identity(args.cave_exe))
        atomic_write(args.output/f'launch-{uuid.uuid4().hex}.json',json.dumps(provenance,indent=2))
        command_path=args.output/'pending-surface-entry.json'
        while True:
            state=ledger.read()
            if command_path.exists():
                command=json.loads(command_path.read_text())
                if command['campaign']!=ledger.campaign or command['content']!=ledger.content:
                    raise ValueError('Surface command belongs to another campaign/content')
                if 'native_entry' in command or (Path(command['run'])/'p2-cave-transfer.txt').exists():
                    state=consume_command(command_path,ledger)
                elif state['phase']!='surface' or state['revision']!=command['revision']:
                    raise ValueError('Stale pending surface launch')
            if state['phase']!='surface':
                state=SurfaceRunner(ledger,content,args.cave_exe,process).resume()
                if state['phase']!='surface':return state
            if not command_path.exists():
                run,_,token=launch_surface(args,content,state['surface'],'enter',process)
                # New opt-in App mode. Older single-trip binaries reject this file.
                (run/'manual-entrance.txt').write_text('repeat\n')
                command=dict(campaign=ledger.campaign,content=ledger.content,revision=state['revision'],
                             token=token,run=str(run))
                atomic_write(command_path,json.dumps(command,indent=2))
            else:
                command=json.loads(command_path.read_text());run=Path(command['run'])
            with (run/'native.log').open('w') as log:
                result=process([str(args.surface_exe),'--experimental-pikmin2-room'],cwd=run,
                               stdout=log,stderr=subprocess.STDOUT)
            if result.returncode==0:return ledger.read()
            if result.returncode!=42:raise RuntimeError(f'Entrance exit {result.returncode}; preserve {run}')
            consume_command(command_path,ledger)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('assets','source-import','pocket','treasure','pod1','pod2','purple','imported','surface-exe','cave-exe','output'):
        p.add_argument('--'+name,type=Path,required=True)
    for name in ('transitions','snow','roster','transition-assets'):p.add_argument('--'+name,type=Path)
    args=p.parse_args()
    for name,value in vars(args).items():
        if isinstance(value,Path):setattr(args,name,value.resolve())
    play(args)
