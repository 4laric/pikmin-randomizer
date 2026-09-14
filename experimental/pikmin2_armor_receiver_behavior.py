"""Armor (Cloaking Burrow-nit, EnemyID 15) damage-receiver + stone-flick acceptance.

Issue #407 / #165. Reuses the private batch-2 ground arena and the Armor
behavior fixture from :mod:`experimental.pikmin2_armor_behavior`, plus the
shared ``install``/``verify_install`` partial workaround and
:func:`experimental.pikmin2_sokkuri_behavior.normalize_pose_names`.

The native module ``pc_port/pc_p2_armor.cpp`` implements the source
``damageCallBack`` rule (accept only on ``dmg1`` or ``EB_Bittered``) and the
``doStartStoneState`` mouth flick, printing ``P2_ARMOR_RECEIVER*`` /
``P2_ARMOR_STONE*`` markers. ``validate()`` checks only those markers; it makes
no claim about production placement and never runs the fixture itself.
"""
import argparse
import functools
import json
import os
import re
from pathlib import Path

from experimental.pikmin2_animation_profile import capture_command
from experimental.pikmin2_batch2_core import install, prepare as _prepare, verify_install
from experimental.pikmin2_armor_behavior import (
    ARMOR_ID, ARMOR_INDEX, BEHAVIOR_POSITION, CFG, DEFAULT_POSITIONS, SPECIES)
from experimental.pikmin2_sokkuri_behavior import normalize_pose_names

RECEIVER_MODES = ('source_dmg1', 'port_bounding_sphere', 'reject_all')


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
                    reason='place Armor within the source fp12=200 sight radius so the '
                           'dmg1/bittered receiver and the stone mouth-flick are exercisable',
                    production_placement=False,
                    pose_name_normalization=normalize_pose_names(run))
    (run / 'armor-receiver-override.json').write_text(json.dumps(override, indent=2) + '\n')
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
    (run_dir / 'armor-receiver-validation.json').write_text(
        json.dumps(result, indent=2) + '\n')
    return run_dir, meta, result


def validate(text, code=0):
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    bind = re.search(r'P2_ARMOR_BIND generator=346001 source_id=15 visual_only=0', text)
    ready = re.search(r'P2_ENEMY_READY species=Armor .*generator=346001 .*source_FSM=implemented',
                      text)
    window = bool(re.search(r'Experimental preview window set to 960x540 windowed and centered',
                            text))
    part = re.search(r'P2_ARMOR_RECEIVER_PART generator=346001 dmg1=(present|absent) '
                     r'weakpoint=(\S+) mode=(\w+)', text)
    dmg1_present = bool(part) and part.group(1) == 'present'
    mode = part.group(3) if part else None
    decisions = re.findall(r'P2_ARMOR_RECEIVER generator=346001 decision=(accept|reject) '
                           r'reason=(\w+)', text)
    accepts = [reason for decision, reason in decisions if decision == 'accept']
    rejects = [reason for decision, reason in decisions if decision == 'reject']
    stone_note = bool(re.search(r'P2_ARMOR_STONE_NOTE generator=346001 host_lifecycle=absent '
                                r'port_analogue=pressed', text))
    stone_enter = re.search(r'P2_ARMOR_STONE generator=346001 event=enter stuck=(\d+) '
                            r'flicked=(\d+)', text)
    stone_exit = bool(re.search(r'P2_ARMOR_STONE generator=346001 event=exit', text))
    checks = dict(
        identity=bool(bind),
        ready=bool(ready),
        window=window,
        receiver_part=bool(part) and mode in RECEIVER_MODES,
        # The P1 host has no petrified lifecycle, so the flick is validated via
        # its wired analogue note, or a real enter marker when pressed.
        stone_contract=stone_note or bool(stone_enter),
        no_extinction=not re.search(r'Extinction', text, re.IGNORECASE),
    )
    watched = dict(dmg1_available=dmg1_present, mode=mode,
                   receiver_decisions=decisions, accepts=accepts, rejects=rejects,
                   stone_enter=bool(stone_enter), stone_exit=stone_exit)
    return dict(passed=all(checks.values()), checks=checks, watched=watched, exit_code=code,
                unmeasured=['retail dmg1 part-id fidelity (host collision is the P1 Chappy model)',
                            'hipdropCallBack purple-press leg (InteractPress carries no part)',
                            'real petrification lifecycle (P1 host has none)'],
                limitations=['Behavior fixture overrides Armor arena coordinate; not production '
                             'placement evidence.',
                             'The receiver weakpoint substitutes the host bounding-sphere part for '
                             'the source dmg1 part when dmg1 is absent (port approximation).',
                             'The stone flick is wired to TEKIOPT_Pressed, the host port analogue, '
                             'not a retail petrified state.'])


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
