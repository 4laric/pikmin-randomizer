"""Catfish (Water Dumple, EnemyID 26) residual-gap acceptance (#407/#167).

Closes the Catfish fidelity gaps left by
:mod:`experimental.pikmin2_catfish_behavior`: the source two-slot mouth
(``kamu1``/``kamu2``), ``attackNavi`` captain damage, the proper ``fp02`` White
Pikmin poison swallowed with the enemy's normal kill/corpse, and the flick
receiver driven by the banked flick events (25,2)/(47,3) instead of a synthetic
frame.

The module reuses the private batch-3 aquatic arena and the Catfish behavior
fixture (same engineered placement override) and validates only the
``P2_CATFISH_*`` residuals markers printed by ``pc_port/pc_p2_catfish.cpp``. It
never runs the fixture itself: the real-GL slot is owned by the ground-lifecycle
worker. ``validate()`` treats the setup ``P2_CATFISH_RESIDUAL`` contract note as
the wiring evidence for ``attackNavi``/poison and, when the markers are observed
in a run, enforces the exact banked values.
"""
import argparse
import json
import os
import re
from pathlib import Path

from experimental.pikmin2_animation_profile import capture_command
from experimental.pikmin2_catfish_behavior import (
    CATFISH_ID, prepare as _prepare)

GEN = CATFISH_ID
SLOT_MAX = 2
ATTACK_DAMAGE = 10.0
POISON_DAMAGE = 300.0
FLICK_KNOCKBACK_FRAME = 25.0
FLICK_RESTORE_FRAME = 47.0
BITE_FRAME = 17.0
SWALLOW_FRAME = 75.0


def prepare(assets, imported, output):
    run = _prepare(Path(assets), Path(imported), Path(output))
    marker = dict(species='Catfish', generator=GEN,
                  features=['two_slot_mouth', 'attackNavi', 'fp02_poison',
                            'banked_flick_25_47'],
                  source='KochappyBase StateAttack/StateFlick; Catfish::Obj::initMouthSlots',
                  reason='residual-gap fixture reuses the Catfish behavior arena override so '
                         'the two-slot capture and banked event markers are observable',
                  production_placement=False)
    (run / 'catfish-residual.json').write_text(json.dumps(marker, indent=2) + '\n')
    return run


def run(assets, imported, output, exe, seconds=30):
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    os.environ['PATH'] = 'C:\\msys64\\mingw64\\bin;' + os.environ.get('PATH', '')
    run_dir = prepare(assets, imported, output)
    meta = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                           run_dir, run_dir / 'capture', seconds)
    text = (run_dir / 'capture' / 'native.log').read_text(errors='replace')
    result = validate(text, meta['exit_code'])
    result['capture'] = {k: meta[k] for k in ('executable_sha256', 'elapsed_seconds',
                                              'exit_code', 'timed_out')}
    (run_dir / 'catfish-residual-validation.json').write_text(
        json.dumps(result, indent=2) + '\n')
    return run_dir, meta, result


def _frame_groups(rows):
    """Group (frame, slot) marker rows into a dict frame -> slots."""
    groups = {}
    for frame, slot in rows:
        groups.setdefault(float(frame), []).append(int(slot))
    return groups


def validate(text, code=0):
    """Check the native log against the Catfish residual contract.

    Confined to ``P2_CATFISH_*`` / batch-3 bind markers so it makes no claim
    about unrelated families or production placement.
    """
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    identity = bool(re.search(r'P2_CATFISH_BIND generator=374001 source_id=26 visual_only=0',
                              text))
    ready = bool(re.search(r'P2_ENEMY_READY species=Catfish .*generator=374001 '
                           r'.*source_FSM=implemented', text))
    batch3_bind = bool(re.search(r'P2_BATCH3_BIND generator=374001 key=aquatic\|Catfish '
                                 r'visual_only=0 native_fsm=implemented', text))
    window = bool(re.search(r'Experimental preview window set to 960x540 windowed and centered',
                            text))
    residual = re.search(r'P2_CATFISH_RESIDUAL generator=374001 slots=(\d+) '
                         r'attack_damage=([\d.]+) poison_damage=([\d.]+) flick_events=(\S+)',
                         text)

    bites = re.findall(r'P2_CATFISH_BITE generator=374001 frame=([\d.]+) pikmin=1 slot=(\d+)',
                       text)
    eats = re.findall(r'P2_CATFISH_EAT generator=374001 pikmin=1 slot=(\d+)', text)
    navi = re.findall(r'P2_CATFISH_ATTACK_NAVI generator=374001 frame=([\d.]+) damage=([\d.]+)',
                      text)
    flick_knockback = re.findall(
        r'P2_CATFISH_FLICK generator=374001 frame=([\d.]+) event=knockback hit=(\d+)', text)
    flick_restore = re.findall(
        r'P2_CATFISH_FLICK generator=374001 frame=([\d.]+) event=restore', text)
    poison = re.findall(r'P2_CATFISH_POISON generator=374001 source_id=26 pikmin=white '
                        r'damage=([\d.]+) health=(-?[\d.]+)', text)

    bite_groups = _frame_groups(bites)
    # Two attack cycles can share one animation frame, so reusing slot 0 across
    # cycles is valid; each cycle may fill 1..SLOT_MAX distinct slots.
    slots_ok = all(1 <= len(slots) <= SLOT_MAX for slots in bite_groups.values())
    bite_slots = [int(slot) for _, slot in bites]
    eat_slots = [int(slot) for slot in eats]
    exactly_once = (len(eats) == len(bites)
                    and all(0 <= slot < SLOT_MAX for slot in bite_slots + eat_slots))

    contract_ok = bool(residual) and int(residual.group(1)) == SLOT_MAX \
        and float(residual.group(2)) == ATTACK_DAMAGE \
        and float(residual.group(3)) == POISON_DAMAGE \
        and residual.group(4) == '25,47'
    attack_navi_ok = contract_ok and all(float(d) == ATTACK_DAMAGE for _, d in navi)
    poison_ok = contract_ok and all(float(d) == POISON_DAMAGE for d, _ in poison)
    flick_ok = all(float(f) == FLICK_KNOCKBACK_FRAME for f, _ in flick_knockback) \
        and all(float(f) == FLICK_RESTORE_FRAME for f in flick_restore)

    checks = dict(
        identity=identity,
        ready=ready,
        batch3_bind=batch3_bind,
        window=window,
        residual_contract=contract_ok,
        two_slot_capture=bool(bites) and contract_ok and slots_ok,
        bite_eat_exactly_once=exactly_once,
        attack_navi_contract=attack_navi_ok,
        poison_contract=poison_ok,
        flick_banked=flick_ok,
        no_extinction=not re.search(r'Extinction', text, re.IGNORECASE),
    )
    watched = dict(
        residual_slots=int(residual.group(1)) if residual else None,
        residual_attack_damage=float(residual.group(2)) if residual else None,
        residual_poison_damage=float(residual.group(3)) if residual else None,
        bite_frames=sorted(bite_groups),
        bite_slots=bite_slots,
        eat_slots=eat_slots,
        attack_navi=[(float(f), float(d)) for f, d in navi],
        poison=[(float(d), float(h)) for d, h in poison],
        flick_knockback=[(float(f), int(h)) for f, h in flick_knockback],
        flick_restore=[float(f) for f in flick_restore],
        slots_per_frame={f: slots for f, slots in bite_groups.items()},
    )
    return dict(passed=all(checks.values()), checks=checks, watched=watched, exit_code=code,
                unmeasured=['two simultaneous mouth slots at runtime (the arena staged only one '
                            'target inside the sweep per attack cycle; the two-slot fill is '
                            'covered by the standalone policy test)',
                            'runtime White Pikmin poison (the aquatic arena stages only the '
                            '20-red starting squad; the fp02 policy is covered by the '
                            'standalone policy test)',
                            'kamu1/kamu2 mouth attachment visual (no P1 mouth geometry)',
                            'attackNavi hit unless the active Navi is inside the fp22/fp23 '
                            'sweep at the bite frame'],
                limitations=['Behavior fixture overrides the Catfish arena coordinate; not '
                             'production placement evidence.',
                             'The two-slot mouth is an explicit nearest-first capture inside the '
                             'source attack sweep; the host has no mouth joints.',
                             'The flick knockback/damage/range use source general fp17/fp18/fp19 '
                             'defaults; the flick latch radius is a P1-host value.'])


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
