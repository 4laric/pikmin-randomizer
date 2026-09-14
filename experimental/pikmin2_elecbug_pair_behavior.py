"""ElecBug (Anode Beetle, EnemyID 28) two-beetle partner-link acceptance (#165/#407).

Private batch-2 ground arena staging TWO ElecBug generators close to each other
and to the 20-red fixture squad. The native `pc_p2_elecbug.cpp` links a
registered Charge beetle with the nearest registered beetle inside the source
300-unit pairing radius, runs the pair through Charge/ChildCharge ->
Discharge/ChildDischarge, sends the electrical receiver around the pair, and
breaks the link on discharge completion, partner death or press/Reverse.

`validate()` checks only the `P2_ELECBUG_*` markers emitted by the native module;
no disc assets, builds or player saves are touched here. The real-GL runtime
fixture is owned by another lane, so this module is prepare/validate only.
"""
import argparse
import functools
import json
import os
import re
from pathlib import Path

from experimental.pikmin2_animation_profile import capture_command
from experimental.pikmin2_batch2_core import install, prepare as _prepare, verify_install
from experimental.pikmin2_batch2_families import FAMILIES
from experimental.pikmin2_sokkuri_behavior import normalize_pose_names

CFG = dict(FAMILIES['ground'])
ELECBUG_A = 346002
ELECBUG_B = 346008
CONTROL_ID = 346007
SPECIES = ('ElecBug', 'ElecBug')
PAIR_A_POSITION = (-100.0, 30.0, 1850.0)
PAIR_B_POSITION = (-40.0, 30.0, 1850.0)
CONTROL_POSITION = (240.0, 30.0, 1500.0)
PAIR_DISTANCE = 60.0
PAIR_RADIUS = 300.0
SQUAD_X = tuple(-140.0 + (index % 10) * 8.0 for index in range(20))
SQUAD_Z = tuple(1820.0 - (index // 10) * 8.0 for index in range(20))


def prepare(assets, imported, output):
    cfg = dict(CFG)
    cfg['arena_species'] = SPECIES + ('P1 Chappy',)
    cfg['arena_ids'] = (ELECBUG_A, ELECBUG_B, CONTROL_ID)
    cfg['arena_positions'] = (PAIR_A_POSITION, PAIR_B_POSITION, CONTROL_POSITION)
    run = _prepare(cfg, assets, imported, output,
                   installer=functools.partial(install, cfg),
                   verifier=functools.partial(verify_install, cfg))
    override = dict(
        species=list(SPECIES), generators=[ELECBUG_A, ELECBUG_B],
        arena_default=[pair for pair in (PAIR_A_POSITION, PAIR_B_POSITION)],
        behavior_fixture=[PAIR_A_POSITION, PAIR_B_POSITION],
        pair_distance=PAIR_DISTANCE, pairing_radius=PAIR_RADIUS,
        reason='stage two ElecBug generators inside the source 300-unit pairing '
               'radius and within the source fp12=200 sight radius of the starting '
               'squad so Charge/ChildCharge -> Discharge/ChildDischarge and the '
               'press-to-flip Reverse path are observable',
        production_placement=False,
        pose_name_normalization=normalize_pose_names(run))
    (run / 'elecbug-pair-override.json').write_text(json.dumps(override, indent=2) + '\n')
    return run


def run(assets, imported, output, exe, seconds=40):
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    os.environ['PATH'] = 'C:\\msys64\\mingw64\\bin;' + os.environ.get('PATH', '')
    run_dir = prepare(Path(assets), Path(imported), Path(output))
    meta = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                           run_dir, run_dir / 'capture', seconds)
    text = (run_dir / 'capture' / 'native.log').read_text(errors='replace')
    result = validate(text, meta['exit_code'])
    result['capture'] = {k: meta[k] for k in ('executable_sha256', 'elapsed_seconds',
                                              'exit_code', 'timed_out')}
    (run_dir / 'elecbug-pair-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    return run_dir, meta, result


def validate(text, code=0):
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    pair = {ELECBUG_A, ELECBUG_B}
    states = {}
    for match in re.finditer(r'P2_ELECBUG_STATE generator=(\d+) state=(\w+)', text):
        states.setdefault(int(match.group(1)), []).append(match.group(2))
    links = [(int(m.group(1)), int(m.group(2)))
             for m in re.finditer(r'P2_ELECBUG_LINK generator=(\d+) partner=(\d+)', text)]
    unlinks = [int(m.group(1))
               for m in re.finditer(r'P2_ELECBUG_UNLINK generator=(\d+)', text)]
    shocks = [int(m.group(1))
              for m in re.finditer(r'P2_ELECBUG_SHOCK generator=(\d+) pikmin=1', text)]
    discharges = [int(m.group(1)) for m in
                  re.finditer(r'P2_ELECBUG_DISCHARGE generator=(\d+) source_id=28 ', text)]
    flips = [m.start() for m in re.finditer(r'P2_ELECBUG_FLIP generator=\d+ source_id=28', text)]
    recovers = [m.start() for m in
                re.finditer(r'P2_ELECBUG_RECOVER generator=\d+ source_id=28', text)]
    all_states = [name for names in states.values() for name in names]
    pair_link = [(g, p) for g, p in links if g != p and {g, p} == pair]
    flip_before_recover = bool(flips) and bool(recovers) and min(flips) < max(recovers)
    checks = dict(
        identity=(bool(re.search(rf'P2_ELECBUG_BIND generator={ELECBUG_A} source_id=28 visual_only=0', text))
                  and bool(re.search(rf'P2_ELECBUG_BIND generator={ELECBUG_B} source_id=28 visual_only=0', text))),
        ready=(bool(re.search(rf'P2_ENEMY_READY species=ElecBug .*generator={ELECBUG_A} '
                              r'.*behavior=native .*source_FSM=implemented', text))
               and bool(re.search(rf'P2_ENEMY_READY species=ElecBug .*generator={ELECBUG_B} '
                                  r'.*behavior=native .*source_FSM=implemented', text))),
        window=bool(re.search(r'Experimental preview window set to 960x540 windowed and centered', text)),
        pair_link=bool(pair_link),
        no_self_link=all(g != p for g, p in links),
        charge_state='charge' in all_states,
        child_charge_state='childcharge' in all_states,
        discharge_state='discharge' in all_states,
        child_discharge_state='childdischarge' in all_states,
        discharge_pair=len(discharges) >= 2 and set(discharges) <= pair,
        shock_receiver=bool(shocks) and set(shocks) <= pair,
        unlink=bool(unlinks) and set(unlinks) <= pair,
        flip_path=flip_before_recover,
        no_extinction=not re.search(r'Extinction', text, re.IGNORECASE),
    )
    return dict(passed=all(v for k, v in checks.items() if k != 'flip_path'), checks=checks, links=pair_link,
                unlinks=len(unlinks), shocks=len(shocks), exit_code=code,
                unmeasured=['retail uniform-random partner selection (port picks nearest)',
                            'InteractDenki electrical-immunity exclusions beyond Yellow',
                            'press-to-flip runtime path (no Pikmin lands on the host unattended)',
                            'corpse/transport/cleanup after death'],
                limitations=['Behavior fixture overrides both ElecBug arena coordinates; '
                             'not production placement evidence.',
                             'Pair discharge + single-target receiver resolution is a P1-host '
                             'adaptation of the source two-beetle Denki sweep.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('prepare', 'run'):
        sub = commands.add_parser(name)
        for flag in ('assets', 'imported', 'output'):
            sub.add_argument('--' + flag, type=Path, required=True)
        if name == 'run':
            sub.add_argument('--exe', type=Path, required=True)
            sub.add_argument('--seconds', type=int, default=40)
    args = parser.parse_args()
    if args.command == 'prepare':
        print(prepare(args.assets, args.imported, args.output))
    else:
        run_dir, meta, result = run(args.assets, args.imported, args.output, args.exe, args.seconds)
        print(run_dir)
        print(json.dumps(result, indent=2))
