"""Run the lifecycle fixture through the real launcher and repeated native loads.

The fixture deliberately supplies a casualty, maturity and Purple conversion.
It tests persistence and native hooks, not controller gameplay or transport AI.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import uuid
from unittest.mock import patch

from experimental.pikmin2_campaign import run_campaign, load, entry_text, ledger_text
from scripts.preview_pikmin2_emergence import prepare


def test(args):
    args.output.mkdir(parents=True, exist_ok=False)
    session = args.output/'session'
    end = run_campaign(args.assets, args.imported, [args.pod1, args.pod2], args.purple, args.treasure, args.exe, session)
    assert end['status'] == 'exited' and len(end['squad']) == 19 and end['health'] == .625
    assert Counter(p['species'] for p in end['squad']) == {'red':9, 'purple':10}
    assert sum(p['maturity'] == 2 for p in end['squad']) == 1
    assert sum(p['maturity'] == 1 for p in end['squad']) == 1
    assert end['receipts'] == {'treasure:dia_a_red':180, 'treasure:map01':200}
    assert load(session/'checkpoint.json', end['content']) == end
    # Relaunch of an exited cave must preserve the result and create no new run.
    existing = list((session/'runs').iterdir())
    assert run_campaign(args.assets, args.imported, [args.pod1,args.pod2], args.purple,args.treasure,args.exe,session) == end
    assert list((session/'runs').iterdir()) == existing
    # Explicit synthetic floor-entry checkpoint verifies Purple restoration,
    # including two process restarts without changing the saved checkpoint.
    state = dict(end, status='active', floor=2, revision=1, receipts={'treasure:dia_a_red':180})
    for _ in range(2):
        run = prepare(args.assets,args.imported,args.treasure,args.output/'reloads',floor=2,pod=args.pod2,
                      purple=args.purple,squad=state['squad'])
        (run/'p2-cave-entry.txt').write_text(entry_text(state,uuid.uuid4().hex))
        (run/'p2-economy.txt').write_text(ledger_text(state['receipts']))
        (run/'p2-cave-restore-only.txt').touch()
        with (run/'native.log').open('w') as log:
            result = subprocess.run([str(args.exe),'--experimental-pikmin2-room'],cwd=run,stdout=log,stderr=subprocess.STDOUT)
        assert result.returncode == 0, run
        text = (run/'native.log').read_text(errors='replace')
        assert 'P2_CAVE_RESTORE_PASS' in text and 'PASS cave repeated restore' in text, run
        assert not (run/'p2-cave-transfer.txt').exists()
    (args.output/'result.json').write_text(json.dumps(end,indent=2))
    def extinction_room(*a, **kw):
        run=prepare(*a,**kw);(run/'p2-cave-extinction.txt').touch();return run
    with patch('experimental.pikmin2_campaign.prepare',side_effect=extinction_room):
        failed=run_campaign(args.assets,args.imported,[args.pod1,args.pod2],args.purple,args.treasure,args.exe,args.output/'extinction')
    assert failed['status']=='failed' and not failed['squad'] and not failed['receipts']
    assert load(args.output/'extinction/checkpoint.json',end['content'])==failed
    print('PASS: two native floor processes, atomic 380-Poko result, 19 survivors, maturity/health, ten Purples, repeated native restoration.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets','imported','pod1','pod2','purple','treasure','exe','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args()
    for name,value in vars(args).items():setattr(args,name,value.resolve())
    test(args)
