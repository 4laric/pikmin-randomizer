"""Bounded #1072 controller fixture, explicit Blue staging and exact exit contracts."""
import argparse
from dataclasses import asdict
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.cave_floor import create, fingerprint, NAMES
from randomizer.test_run import apply_test_run_env
from experimental.pikmin2_cave_lane41_generator import _seed_uint64
from experimental.pikmin2_cave_items import parse_items_text
from scripts.stage_pikmin2_playable_cave import stage
from scripts.play_pikmin2_cave import checkpoint, receipts
from scripts.capacity_gate import admit, measure


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def assess(run, mode, manifest):
    raw = json.loads((run / 'run-result.json').read_text())
    log = (run / 'native.log').read_text(errors='replace')
    safe = not raw.get('timed_out') and 'FOCUS_HOLD' not in log and 'AUTOPLAY_' not in log and 'P2_AUTOPLAY' not in log
    checks = dict(bounded=safe)
    state = None
    if mode == 'negative':
        checks.update(expected_exit=raw.get('exit_code') == 86,
                      captain_guard=raw.get('captain_down') is True,
                      no_success='PASS CAVE_FULL_SQUAD' not in log and
                      'P2_CAVE_FULL_SQUAD_CHECKPOINT' not in log)
    else:
        checks['captain_safe'] = not raw.get('captain_down')
        checks['window'] = 'P2_CAVE_FINAL_WINDOW width=960 height=540 mode=0' in log
        checks['centered'] = bool(re.search(r'P2_CAVE_GUARDED_WINDOW size=960x540 .*centered=1', log))
        if mode == 'restore':
            checks.update(expected_exit=raw.get('exit_code') == 0,
                          fixture_pass='PASS CAVE_FULL_SQUAD_RESTORE' in log,
                          blue_rows=re.findall(r'P2_CAVE_RESTORE species=(\d+) maturity=(\d+)', log) == [('0', '0')] * 20,
                          water_suppressed='P2_CAVE_ITEM_RESTORE item=treasure_water collected=1 spawn=0' in log,
                          electric_present=bool(re.search(r'P2_CAVE_ITEM_ACTOR .*item=treasure_elec ', log)))
        else:
            checks.update(expected_exit=raw.get('exit_code') == 42,
                          pickup='P2_CAVE_ROUTE_PICKUP item=treasure_water attachment=ordinary' in log,
                          checkpoint='P2_CAVE_FULL_SQUAD_CHECKPOINT survivors=20 following=20 crossed=20' in log)
            crosses = re.findall(r'P2_CAVE_FULL_SQUAD_CROSSED actor=(\d+)', log)
            checks['every_actor_crossed'] = len(crosses) == 20 and set(map(int, crosses)) == set(range(20))
            arrival = re.search(r'P2_CAVE_FULL_SQUAD_ARRIVED alive=20 following=20 crossed=20 farthest=([\d.]+) captain_x=([\d.-]+) captain_y=([\d.-]+) captain_z=([\d.-]+)', log)
            actors = re.findall(r'P2_CAVE_FULL_SQUAD_AT_EXIT actor=(\d+) species=(\d+) x=([\d.-]+) y=([\d.-]+) z=([\d.-]+) mode=(\d+)', log)
            checks['physical_arrival'] = bool(arrival) and len(actors) == 20 and {int(a[0]) for a in actors} == set(range(20))
            if arrival:
                far, x, y, z = map(float, arrival.groups())
                checks['physical_arrival'] &= far <= 120.01 and abs(y) <= 30 and math.hypot(x - 800, z - 100) <= 40
                checks['physical_arrival'] &= all(s == '0' and mode == '1' and abs(float(py)) <= 30 and math.dist((float(px),float(py),float(pz)),(x,y,z)) <= 120.01
                                                  for _, s, px, py, pz, mode in actors)
            placement = parse_items_text((run / 'p2-cave-items.txt').read_text())
            entry = next(e for e in placement['items'] if e['item'] == 'treasure_water')
            expected = (f"P2_CAVE_ITEM_RECEIPT id=treasure:forest_1:f1:{entry['slot_id']} item=treasure_water "
                        f"host={entry['host']} tagged={int(entry['tagged'])} new=1 tag=cave_treasure seed={placement['seed']} result=1")
            checks['native_receipt'] = expected in log
            checks['valid_transfer'] = False
            if (run / 'p2-cave-transfer.txt').exists():
                state = checkpoint((run / 'p2-cave-transfer.txt').read_text(), (run / 'p2-cave-bud-transfer.txt').read_text(),
                                   (run / 'p2-cave-item-receipts.txt').read_text(), manifest, placement)
                checks['valid_transfer'] = len(state['squad']) == 20 and all(s == 0 for s, _ in state['squad']) and receipts(state['receipts'], placement) == [NAMES[0]]
    outputs = {p.name: sha(p) for p in run.iterdir() if p.is_file() and
               (p.name in ('native.log', 'run-result.json', 'run-inputs.json', 'fixture-inputs.json', 'staging-disclosure.json', 'cave.json', 'capacity.json') or p.name.startswith('p2-cave-'))}
    report = dict(mode=mode, passed=all(checks.values()), checks=checks, native_exit=raw.get('exit_code'),
                  raw_supervisor_passed=raw.get('passed'), outputs=outputs,
                  limitations=['20 Blue staged', 'native controller scripted', 'checkpoint confirmation bypassed', 'not natural color supply or full campaign'])
    return report, state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'fixture', 'production', 'generator', 'assets', 'pod', 'run'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--mode', choices=('full_squad', 'restore', 'negative'), default='full_squad')
    parser.add_argument('--previous', type=Path)
    args = parser.parse_args()
    workspace, run = args.workspace.resolve(), args.run.resolve()
    if not run.is_relative_to(workspace / 'output') or run.exists():
        raise ValueError('Use a fresh run under canonical output/')
    provenance = json.loads(args.fixture.with_name('provenance.json').read_text())
    if provenance['status'] != 'built' or provenance['artifacts'][str(args.fixture.resolve())]['sha256'] != sha(args.fixture):
        raise ValueError('Fixture is not the frozen built artifact')
    manifest = create('930')
    seed = _seed_uint64(manifest['table']['seed'])
    buds = f'P2_CAVE_BUD_STATE_1\n{seed} forest_1 1 2\nforest_1:f1:bud:0 0\nforest_1:f1:bud:1 0\n'
    prior = dict(schema=1, fingerprint=fingerprint(manifest), health=1, squad=[[0, 0] for _ in range(20)], buds=buds, receipts='P2_RECEIPTS_1\n')
    if args.mode == 'restore':
        if not args.previous:
            raise ValueError('Restore requires an accepted full-squad producer')
        previous = args.previous.resolve()
        report = json.loads((previous / 'assessment.json').read_text())
        if not report['passed'] or report['mode'] != 'full_squad' or any(sha(previous / n) != h for n, h in report['outputs'].items()):
            raise ValueError('Producer failed or its evidence changed')
        prior = checkpoint((previous / 'p2-cave-transfer.txt').read_text(), (previous / 'p2-cave-bud-transfer.txt').read_text(),
                           (previous / 'p2-cave-item-receipts.txt').read_text(), manifest,
                           parse_items_text((previous / 'p2-cave-items.txt').read_text()))
    stage(manifest, args.assets, args.pod, args.production, args.generator, run, 0, prior)
    (run / 'staging-disclosure.json').write_text(json.dumps(dict(mode=args.mode, starting_species='20 Blue staged',
        previous=str(args.previous) if args.previous else None, input='native scripted controller', position_writes=False,
        velocity_writes=False, confirmation_bypassed=True), indent=2))
    env = os.environ.copy()
    for key in list(env):
        if key.startswith(('PIKMIN_CAVE_', 'PIKMIN_P2_', 'P2_CAVE_', 'PIKMIN_RANDOMIZER_AUTOPLAY')):
            del env[key]
    env['PIKMIN_RANDOMIZER_AUTOPLAY'] = '0'
    apply_test_run_env(env, workspace)
    env['P2_CAVE_TEST_SCENARIO'] = 'restore' if args.mode == 'restore' else 'full_squad'
    if args.mode == 'negative':
        env['P2_CAVE_GUARDED_BOOT_FORCE_CAPTAIN_DOWN'] = '1'
    measurement = measure()
    allowed, reason = admit('game', measurement)
    (run / 'capacity.json').write_text(json.dumps(dict(admitted=allowed, reason=reason, measurement=asdict(measurement)), indent=2))
    if not allowed:
        print('Capacity denied; no game launched:', reason)
        return 75
    marker = {'full_squad': 'P2_CAVE_FULL_SQUAD_CHECKPOINT', 'restore': 'PASS CAVE_FULL_SQUAD_RESTORE', 'negative': 'P2_FIXTURE_CAPTAIN_DOWN'}[args.mode]
    command = [sys.executable, str(workspace / 'scripts/run_pikmin2_fixture.py'), '--exe', str(args.fixture.resolve()),
               '--run-dir', str(run), '--arg=--experimental-pikmin2-room', '--pass-marker', marker, '--timeout', '180']
    (run / 'fixture-inputs.json').write_text(json.dumps(dict(command=command, fixture_sha256=sha(args.fixture),
        native_head=provenance['expected_native_head'], autoplay_disabled=True, inputs={p.name: sha(p) for p in run.iterdir() if p.is_file()}), indent=2))
    subprocess.run(command, cwd=workspace, env=env, check=False)
    report, state = assess(run, args.mode, manifest)
    if args.mode == 'restore':
        report['checks']['bud_state_continuity'] = (run / 'p2-cave-bud-entry.txt').read_text() == prior['buds']
        report['checks']['receipt_continuity'] = (run / 'p2-cave-item-receipts.txt').read_text() == prior['receipts']
        report['passed'] = all(report['checks'].values())
    (run / 'assessment.json').write_text(json.dumps(report, indent=2))
    if state:
        (run / 'observed-checkpoint.json').write_text(json.dumps(state, indent=2))
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
