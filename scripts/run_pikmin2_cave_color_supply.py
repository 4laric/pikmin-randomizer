"""#1125 Red identity correction: ordinary entry and bounded Blue acquisition.

Historical #1086 species2 was Yellow; preserve its immutable evidence.
"""
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
    checks = dict(gamepad=bool(re.search(r'P2_CAVE_COLOR_GAMEPAD instance=\d+ player=1 assigned=1 input=SDL_virtual process_local=1 navi_override=0',log)), bounded=raw.get('timeout_seconds') == 60 and not raw.get('timed_out') and 'FOCUS_HOLD' not in log and 'AUTOPLAY_' not in log and 'P2_AUTOPLAY' not in log)
    state = None
    if mode == 'negative':
        checks.update(expected_exit=raw.get('exit_code') == 86, captain_guard=raw.get('captain_down') is True,
                      no_success='PASS CAVE_COLOR_SUPPLY' not in log and 'P2_CAVE_COLOR_CHECKPOINT' not in log)
    else:
        checks.update(captain_safe=not raw.get('captain_down'),
                      window='P2_CAVE_FINAL_WINDOW width=960 height=540 mode=0' in log,
                      centered=bool(re.search(r'P2_CAVE_GUARDED_WINDOW size=960x540 .*centered=1', log)))
        if mode == 'restore':
            rows = re.findall(r'P2_CAVE_RESTORE species=(\d+) maturity=(\d+)', log)
            checks.update(expected_exit=raw.get('exit_code') == 0,
                          fixture_pass='PASS CAVE_COLOR_SUPPLY_RESTORE red=15 blue=5' in log,
                          mixed_restore=len(rows) == 20 and rows.count(('0','0')) == 5 and rows.count(('1','0')) == 15)
        else:
            accepts=re.findall(r'P2_CAVE_BUD_ACCEPT slot=forest_1:f1:bud:0 colour=blue thrown_colour=1 used=(\d+) budget=5',log)
            sprouts=re.findall(r'P2_CAVE_BUD_SPROUT slot=forest_1:f1:bud:0 colour=blue colour_index=0 plucked=1 natural=1',log)
            checks.update(expected_exit=raw.get('exit_code') == 42,
                original_red='P2_CAVE_COLOR_SETUP starting=20_red_ordinary_entry' in log,
                native_species='P2_CAVE_COLOR_SPECIES red_id=1 yellow_id=2 blue_id=0 red_count=20 yellow_count=0 blue_count=0' in log,
                mapped_throws='P2_CAVE_COLOR_THROW input=mapped_button' in log,
                exactly_five_accepts=accepts==['1','2','3','4','5'], five_sprouts=len(sprouts)==5,
                acquired='P2_CAVE_COLOR_ACQUIRED red=15 blue=5 conversions=5 source=ordinary_controller_throw' in log,
                recalled='P2_CAVE_COLOR_RECALLED following=20 red=15 blue=5' in log,
                mixed_movement='P2_CAVE_COLOR_MIXED_MOVEMENT red=15 blue=5 following=20' in log,
                exit_disclosed='P2_CAVE_COLOR_EXIT captain_only=1 squad_left_west=1 full_squad_traversal=0' in log,
                checkpoint='P2_CAVE_COLOR_CHECKPOINT red=15 blue=5 survivors=20 conversions=5' in log,
                valid_transfer=False)
            if (run/'p2-cave-transfer.txt').exists():
                state=checkpoint((run/'p2-cave-transfer.txt').read_text(),(run/'p2-cave-bud-transfer.txt').read_text(),
                                 (run/'p2-cave-item-receipts.txt').read_text(),manifest,parse_items_text((run/'p2-cave-items.txt').read_text()))
                checks['valid_transfer']=len(state['squad'])==20 and state['squad'].count([0,0])==5 and state['squad'].count([1,0])==15 and receipts(state['receipts'],parse_items_text((run/'p2-cave-items.txt').read_text()))==[]
                lines=state['buds'].splitlines()
                checks['bud_budget']=lines[-2:]==['forest_1:f1:bud:0 5','forest_1:f1:bud:1 0']
    outputs={p.name:sha(p) for p in run.iterdir() if p.is_file() and (p.name in ('native.log','run-result.json','run-inputs.json','fixture-inputs.json','staging-disclosure.json','cave.json','capacity.json') or p.name.startswith('p2-cave-'))}
    return dict(mode=mode,passed=all(checks.values()),checks=checks,native_exit=raw.get('exit_code'),raw_supervisor_passed=raw.get('passed'),outputs=outputs,
                limitations=[('15 Red/5 Blue from actual producer' if mode == 'restore' else 'ordinary fresh stage: 20 Red, entry species 1'),'SDL virtual gamepad scripted','production bud auto-pluck','captain-only exit; mixed squad left west','confirmation bypassed','not Yellow supply or mixed hazard traversal']),state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'fixture', 'production', 'generator', 'assets', 'pod', 'run'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--mode', choices=('supply', 'restore', 'negative'), default='supply')
    parser.add_argument('--previous', type=Path)
    args = parser.parse_args()
    workspace, run = args.workspace.resolve(), args.run.resolve()
    if not run.is_relative_to(workspace / 'output') or run.exists():
        raise ValueError('Use a fresh run under canonical output/')
    provenance = json.loads(args.fixture.with_name('provenance.json').read_text())
    if provenance['status'] != 'built' or provenance['artifacts'][str(args.fixture.resolve())]['sha256'] != sha(args.fixture):
        raise ValueError('Fixture is not the frozen built artifact')
    manifest = create('930')
    prior = None  # Exercise the ordinary stage default; no injected entry squad.
    if args.mode == 'restore':
        if not args.previous:
            raise ValueError('Restore requires an accepted color-supply producer')
        previous = args.previous.resolve()
        report = json.loads((previous / 'assessment.json').read_text())
        if not report['passed'] or report['mode'] != 'supply' or any(sha(previous / n) != h for n, h in report['outputs'].items()):
            raise ValueError('Producer failed or its evidence changed')
        prior = checkpoint((previous / 'p2-cave-transfer.txt').read_text(), (previous / 'p2-cave-bud-transfer.txt').read_text(),
                           (previous / 'p2-cave-item-receipts.txt').read_text(), manifest,
                           parse_items_text((previous / 'p2-cave-items.txt').read_text()))
    stage(manifest, args.assets, args.pod, args.production, args.generator, run, 0, prior)
    if prior is None:
        # The ordinary supervisor initializes the durable ledger before launch.
        # Fresh stage itself deliberately supplies no checkpoint sidecars.
        (run / 'p2-cave-item-receipts.txt').write_text('P2_RECEIPTS_1\n')
    (run / 'staging-disclosure.json').write_text(json.dumps(dict(mode=args.mode, starting_species=('15 Red/5 Blue from actual producer transfer' if args.mode == 'restore' else 'ordinary fresh stage: 20 Red, entry species 1'), starting_squad=(prior['squad'] if prior else [[1, 0]] * 20), entry_override=prior is not None,
        previous=str(args.previous) if args.previous else None, input='SDL virtual gamepad assigned P1 process-locally', position_writes=False,
        velocity_writes=False, species_writes=False, state_writes=False, bud_auto_pluck='existing production behavior', captain_only_exit=True, confirmation_bypassed=True), indent=2))
    env = os.environ.copy()
    for key in list(env):
        if key.startswith(('PIKMIN_CAVE_', 'PIKMIN_P2_', 'P2_CAVE_', 'PIKMIN_RANDOMIZER_AUTOPLAY')):
            del env[key]
    env['PIKMIN_RANDOMIZER_AUTOPLAY'] = '0'
    apply_test_run_env(env, workspace)
    env['SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS'] = '1'
    env['P2_CAVE_TEST_SCENARIO'] = 'restore' if args.mode == 'restore' else 'supply'
    if args.mode == 'negative':
        env['P2_CAVE_GUARDED_BOOT_FORCE_CAPTAIN_DOWN'] = '1'
    measurement = measure()
    allowed, reason = admit('game', measurement)
    (run / 'capacity.json').write_text(json.dumps(dict(admitted=allowed, reason=reason, measurement=asdict(measurement)), indent=2))
    if not allowed:
        print('Capacity denied; no game launched:', reason)
        return 75
    marker = {'supply': 'P2_CAVE_COLOR_CHECKPOINT', 'restore': 'PASS CAVE_COLOR_SUPPLY_RESTORE', 'negative': 'P2_FIXTURE_CAPTAIN_DOWN'}[args.mode]
    command = [sys.executable, str(workspace / 'scripts/run_pikmin2_fixture.py'), '--exe', str(args.fixture.resolve()),
               '--run-dir', str(run), '--arg=--experimental-pikmin2-room', '--pass-marker', marker, '--timeout', '60']
    (run / 'fixture-inputs.json').write_text(json.dumps(dict(command=command, fixture_sha256=sha(args.fixture),
        native_head=provenance['expected_native_head'], runner_sha256=sha(__file__), autoplay_disabled=True,
        sdl_joystick_allow_background_events=env['SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS'],
        inputs={p.name: sha(p) for p in run.iterdir() if p.is_file()}), indent=2))
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
