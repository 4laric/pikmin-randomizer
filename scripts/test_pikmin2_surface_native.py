"""Exercise SurfaceRunner with actual cave fixture processes in fresh private output.

This tests host snapshots and native cave boundaries, not a native surface renderer.
Run with the lifecycle fixture executable, never the player's game executable.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import subprocess
import uuid

from experimental.pikmin2_surface_ledger import SurfaceLedger
from experimental.pikmin2_surface_runner import NativeContent, SurfaceRunner


def expected_receipts(roster):
    if roster is None:
        return {'treasure:dia_a_red': 180, 'treasure:map01': 200}
    content = json.loads((roster/'content.json').read_text())
    return {f'treasure:{a["instance_id"]}': content['treasures'][a['catalog_id']]['value']
            for floor in content['floors'] for a in floor['actors'] if a['category'] == 'treasure'}


class FixtureProcess:
    """Inject fixture flags only into freshly staged runs and retain real exit codes."""
    def __init__(self, timeout, mode='normal'):
        if not 1 <= timeout <= 300:
            raise ValueError('Fixture timeout must be 1..300 seconds')
        if mode not in ('normal', 'restore_floor2', 'extinction'):
            raise ValueError('Unknown fixture mode')
        self.timeout, self.mode, self.runs = timeout, mode, []

    def __call__(self, argv, *, cwd, **kwargs):
        cwd = Path(cwd)
        floor = int((cwd/'p2-cave-entry.txt').read_text().splitlines()[2].split()[0])
        restore = self.mode == 'restore_floor2' and floor == 2
        if restore:
            (cwd/'p2-cave-restore-only.txt').touch()
        if self.mode == 'extinction':
            (cwd/'p2-cave-extinction.txt').touch()
        env = dict(os.environ, SDL_AUDIODRIVER='dummy')
        result = subprocess.run(argv, cwd=cwd, timeout=self.timeout, env=env, **kwargs)
        self.runs.append(dict(path=str(cwd), floor=floor, exit=result.returncode, restore=restore))
        if restore:
            log = (cwd/'native.log').read_text(errors='replace')
            if result.returncode != 0 or 'P2_CAVE_RESTORE_PASS' not in log or 'PASS cave repeated restore' not in log:
                raise AssertionError(f'Native restore fixture failed: {cwd}')
            if (cwd/'p2-cave-transfer.txt').exists():
                raise AssertionError(f'Restore-only fixture unexpectedly transferred: {cwd}')
        return result


def run_test(args):
    args.output.mkdir(parents=True, exist_ok=False)
    content = NativeContent(args.assets, args.imported, [args.pod1, args.pod2], args.purple,
                            args.treasure, args.transitions, args.snow, args.roster, args.transition_assets)
    campaign = uuid.uuid4().hex
    directory = args.output/'session'
    ledger = SurfaceLedger(directory, content.identity, campaign)
    snapshot = dict(region='valley_of_repose', day=2, time=8.5, position=[1., 2., 3.],
                    squad=[dict(species='red', maturity=0) for _ in range(20)], health=1., receipts={})
    ledger.create(snapshot)
    ledger.enter_cave(0, uuid.uuid4().hex)
    # Floor 1 commits through the real process; floor 2 pauses after native restore.
    paused_process = FixtureProcess(args.timeout, 'restore_floor2')
    paused = SurfaceRunner(ledger, content, args.exe, paused_process).resume()
    assert paused['phase'] == 'cave' and paused['trip']['checkpoint']['floor'] == 2
    assert paused['revision'] == 2 and len(paused['trip']['checkpoint']['squad']) == 19
    assert [r['exit'] for r in paused_process.runs] == [42, 0]
    # A newly constructed host restores the identical authoritative floor entry.
    reloaded = SurfaceLedger(directory, content.identity, campaign)
    restore_process = FixtureProcess(args.timeout, 'restore_floor2')
    assert SurfaceRunner(reloaded, content, args.exe, restore_process).resume() == paused
    assert reloaded.read() == paused
    finish_process = FixtureProcess(args.timeout)
    final = SurfaceRunner(reloaded, content, args.exe, finish_process).resume()
    returned = final['surface']
    assert final['phase'] == 'surface' and final['trip'] is None and final['revision'] == 4
    assert len(returned['squad']) == 19 and returned['health'] == .625
    assert Counter(p['species'] for p in returned['squad']) == {'red':9, 'purple':10}
    assert sum(p['maturity'] == 2 for p in returned['squad']) == 1
    assert sum(p['maturity'] == 1 for p in returned['squad']) == 1
    assert returned['receipts'] == expected_receipts(args.roster)
    assert all(returned[k] == snapshot[k] for k in ('region','day','time','position'))
    assert reloaded.read() == final
    count = len(finish_process.runs)
    assert SurfaceRunner(reloaded, content, args.exe, finish_process).resume() == final
    assert len(finish_process.runs) == count
    assert not (directory/'checkpoint.json').exists() and not (directory/'pending-handoff.json').exists()
    # Extinction is a separate real native fixture and cannot revive suspended party.
    failed_ledger = SurfaceLedger(args.output/'extinction', content.identity, uuid.uuid4().hex)
    failed_ledger.create(snapshot)
    failed_ledger.enter_cave(0, uuid.uuid4().hex)
    death_process = FixtureProcess(args.timeout, 'extinction')
    failed = SurfaceRunner(failed_ledger, content, args.exe, death_process).resume()
    assert failed['phase'] == 'failed' and not failed['trip']['checkpoint']['squad']
    assert not failed['trip']['checkpoint']['receipts']
    assert SurfaceRunner(failed_ledger, content, args.exe, death_process).resume() == failed
    assert len(death_process.runs) == 1
    report = dict(surface_renderer=False, final=final, failed=failed,
                  processes=paused_process.runs+restore_process.runs+finish_process.runs+death_process.runs)
    (args.output/'result.json').write_text(json.dumps(report, indent=2))
    print(f'PASS: actual native two-floor handoffs, repeated entry restore, {sum(returned["receipts"].values())} Pokos returned once, extinction preserved. Host surface snapshot only.')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets','imported','pod1','pod2','purple','treasure','exe','output'):
        parser.add_argument('--'+name, type=Path, required=True)
    for name in ('transitions','snow','roster','transition-assets'):
        parser.add_argument('--'+name, type=Path)
    parser.add_argument('--timeout', type=int, default=120)
    args = parser.parse_args()
    for name, value in vars(args).items():
        if isinstance(value, Path): setattr(args, name, value.resolve())
    run_test(args)


if __name__ == '__main__': main()
