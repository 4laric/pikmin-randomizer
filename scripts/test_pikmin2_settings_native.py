"""Real settings F1/F6 regression and separate fixed-frame drift measurements."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import subprocess

from experimental import pikmin2_campaign as cave
from experimental.pikmin2_surface_runner import NativeContent
from scripts.play_pikmin2_surface import initial_snapshot,launch_surface
from scripts.test_pikmin2_surface_native import executable_identity
from scripts.test_pikmin2_surface_roundtrip import native_position


def settings_evidence(text):
    markers=('P2_SETTINGS_REAL_MENU_OPEN','P2_SETTINGS_F6_SUPPRESSED dialogs=0 transfer=0',
             'P2_SETTINGS_REAL_MENU_CLOSED','P2_SETTINGS_CLOSED_CONFIRM','P2_MANUAL_ENTRANCE_HANDOFF')
    positions=[text.find(m) for m in markers]
    if any(p<0 for p in positions) or positions!=sorted(positions) or text.count('P2_SETTINGS_CLOSED_CONFIRM')!=1:
        raise ValueError('Missing/out-of-order real settings guard evidence')
    return dict(real_menu_open=True,open_f6_dialogs=0,open_f6_transfers=0,closed_f6_transferred=True)


def drift_evidence(text,origin):
    rows=[]
    for line in text.splitlines():
        match=re.fullmatch(r'P2_DRIFT frame=(\d+) position=([^ ]+) velocity=([^ ]+) ground=([^ ]+)',line)
        if not match:continue
        frame=int(match[1]);position=list(map(float,match[2].split(',')));velocity=list(map(float,match[3].split(',')))
        if len(position)!=3 or len(velocity)!=3 or not all(math.isfinite(v) for v in position+velocity+[float(match[4])]):
            raise ValueError('Invalid drift sample')
        rows.append(dict(frame=frame,position=position,velocity=velocity,ground=float(match[4]),
                         distance_from_snapshot=math.dist(position,origin)))
    if [r['frame'] for r in rows]!=[1,30,60,90]:raise ValueError('Drift observation windows changed/missing')
    return rows


def run_test(args):
    args.output.mkdir(parents=True,exist_ok=False)
    provenance=executable_identity(args.exe)
    (args.output/'provenance.json').write_text(json.dumps(provenance,indent=2))
    content=NativeContent(args.assets,args.imported,[args.pod1,args.pod2],args.purple,args.treasure,
                         args.transitions,args.snow,args.roster,args.transition_assets,
                         source_import=args.source_import,pocket=args.pocket)
    snapshot=json.loads(args.drift_snapshot.read_text())['final']['surface']
    reports={};env=dict(os.environ,SDL_AUDIODRIVER='dummy');env['PATH']='C:/msys64/mingw64/bin;'+env['PATH']
    for mode,state_snapshot in [('settings',initial_snapshot()),('drift',snapshot)]:
        run,state,token=launch_surface(args,content,state_snapshot,'enter',None)
        (run/'settings-fixture.txt').write_text(mode+'\n')
        with (run/'native.log').open('w') as log:
            result=subprocess.run([str(args.exe),'--experimental-pikmin2-room'],cwd=run,env=env,
                                  stdout=log,stderr=subprocess.STDOUT,timeout=args.timeout)
        text=(run/'native.log').read_text(errors='replace')
        if result.returncode!=(42 if mode=='settings' else 0):raise RuntimeError(f'{mode} fixture exit{result.returncode}; {run}')
        if mode=='settings':
            evidence=settings_evidence(text)
            handed=cave.transition(state,token,(run/'p2-cave-transfer.txt').read_text(),cave.read_ledger(run/'p2-economy.txt'),{})
            assert handed['squad']==state_snapshot['squad'] and handed['health']==state_snapshot['health']
            evidence['actual_position']=native_position(run,token)
        else:
            if (run/'p2-cave-transfer.txt').exists():raise ValueError('Drift observation wrote a transfer')
            evidence=dict(snapshot_position=state_snapshot['position'],samples=drift_evidence(text,state_snapshot['position']),
                          input='keyboard/buttons/axes zeroed; no actor repositioning',threshold_changed=False)
        reports[mode]=dict(run=str(run),exit=result.returncode,evidence=evidence)
        (args.output/'result.json').write_text(json.dumps(dict(provenance=provenance,runs=reports,physical_input_tested=False),indent=2))
    print('PASS real settings open blocks F6; close allows native handoff. Fixed-frame drift measurements recorded separately.')
    return reports


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('assets','source-import','pocket','treasure','pod1','pod2','purple','imported','exe','drift-snapshot','output'):
        p.add_argument('--'+name,type=Path,required=True)
    for name in ('transitions','snow','roster','transition-assets'):p.add_argument('--'+name,type=Path)
    p.add_argument('--timeout',type=int,default=60);args=p.parse_args()
    if not 1<=args.timeout<=300:p.error('timeout must be1..300 seconds')
    for name,value in vars(args).items():
        if isinstance(value,Path):setattr(args,name,value.resolve())
    run_test(args)
