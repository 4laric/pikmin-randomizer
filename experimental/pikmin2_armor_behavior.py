"""Armor (Cloaking Burrow-nit, EnemyID 15) source-behavior acceptance (#165/#407).

Same private batch-2 ground arena as the Sokkuri runner, but overrides Armor's
coordinate so the 20-red fixture squad is inside its source sight radius (fp12=200).
The native `pc_p2_armor.cpp` drives Stay -> Appear -> Move -> Attack2 -> Eat and
prints `P2_ARMOR_*` markers; `validate()` checks only those markers.
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
IDS = tuple(CFG['arena_ids'])
ARMOR_ID = 346001
SPECIES = tuple(CFG['arena_species'])
ARMOR_INDEX = SPECIES.index('Armor')
DEFAULT_POSITIONS = tuple(((-(len(SPECIES) - 2) / 2 + index) * 120.0, 30.0, 1850.0)
                          for index in range(len(SPECIES) - 1)) + ((240.0, 30.0, 1500.0),)
BEHAVIOR_POSITION = (-100.0, 30.0, 1850.0)
SQUAD_X = tuple(-140.0 + (index % 10) * 8.0 for index in range(20))
SQUAD_Z = tuple(1820.0 - (index // 10) * 8.0 for index in range(20))


def prepare(assets, imported, output):
    cfg = dict(CFG)
    positions = list(DEFAULT_POSITIONS)
    positions[ARMOR_INDEX] = BEHAVIOR_POSITION
    cfg['arena_positions'] = tuple(positions)
    run = _prepare(cfg, assets, imported, output,
                   installer=functools.partial(install, cfg),
                   verifier=functools.partial(verify_install, cfg))
    override = dict(index=ARMOR_INDEX, species='Armor', generator=ARMOR_ID,
                    arena_default=list(DEFAULT_POSITIONS[ARMOR_INDEX]),
                    behavior_fixture=list(BEHAVIOR_POSITION),
                    reason='place Armor within the source fp12=200 sight radius of the '
                           'starting squad so the Appear/Move/Attack2/Eat FSM is observable',
                    production_placement=False,
                    pose_name_normalization=normalize_pose_names(run))
    (run / 'armor-override.json').write_text(json.dumps(override, indent=2) + '\n')
    return run


def run(assets, imported, output, exe, seconds=30):
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    os.environ['PATH'] = 'C:\\msys64\\mingw64\\bin;' + os.environ.get('PATH', '')
    run_dir = prepare(Path(assets), Path(imported), Path(output))
    meta = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                           run_dir, run_dir / 'capture', seconds)
    text = (run_dir / 'capture' / 'native.log').read_text(errors='replace')
    result = validate(text, meta['exit_code'])
    result['capture'] = {k: meta[k] for k in ('executable_sha256', 'elapsed_seconds',
                                              'exit_code', 'timed_out')}
    (run_dir / 'armor-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    return run_dir, meta, result


def validate(text, code=0):
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    states = re.findall(r'P2_ARMOR_STATE generator=346001 state=(\w+)', text)
    bites = re.findall(r'P2_ARMOR_BITE generator=346001 frame=([\d.]+) pikmin=1', text)
    eats = re.findall(r'P2_ARMOR_EAT generator=346001 pikmin=1', text)
    frames = [float(f) for f in bites]
    bite_in_window = bool(frames) and all(17.0 < f < 27.0 for f in frames)
    checks = dict(
        identity=bool(re.search(r'P2_ARMOR_BIND generator=346001 source_id=15 visual_only=0', text)),
        ready=bool(re.search(r'P2_ENEMY_READY species=Armor .*generator=346001 .*behavior=native '
                             r'.*source_FSM=implemented', text)),
        window=bool(re.search(r'Experimental preview window set to 960x540 windowed and centered', text)),
        appear='appear' in states,
        move='move' in states,
        attack2='attack2' in states,
        animation_event_bite=bite_in_window,
        bite_frames=frames,
        eat_state='eat' in states,
        bite_eat_accounting=len(eats) >= 1 and len(eats) <= len(frames),
        no_extinction=not re.search(r'Extinction', text, re.IGNORECASE),
    )
    return dict(passed=all(v for k, v in checks.items() if k != 'bite_frames'),
                checks=checks, exit_code=code,
                unmeasured=['dmg1 part-id damage rule on the P1 host', 'ItemBridge Attack1/MoveSide/Centre/Top',
                            'mouth-slot attachment visual', 'full action animation bank', 'cleanup/re-entry'],
                limitations=['Behavior fixture overrides Armor arena coordinate; not production placement evidence.',
                             'P2 mouth swallow is resolved as an explicit P1-host capture + single eat kill.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('prepare', 'run'):
        sub = commands.add_parser(name)
        for flag in ('assets', 'imported', 'output'):
            sub.add_argument('--' + flag, type=Path, required=True)
        if name == 'run':
            sub.add_argument('--exe', type=Path, required=True)
            sub.add_argument('--seconds', type=int, default=30)
    args = parser.parse_args()
    if args.command == 'prepare':
        print(prepare(args.assets, args.imported, args.output))
    else:
        run_dir, meta, result = run(args.assets, args.imported, args.output, args.exe, args.seconds)
        print(run_dir)
        print(json.dumps(result, indent=2))
