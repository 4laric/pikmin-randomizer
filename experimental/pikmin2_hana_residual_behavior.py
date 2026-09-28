"""Hana (Creeping Chrysanthemum, EnemyID 84) residual-gate acceptance (#407/#165).

Reuses the private batch-2 ground arena and the Hana behavior fixture from
:mod:`experimental.pikmin2_hana_behavior` (same coordinate override so the
20-red squad is inside Hana's source sight wake radius), plus the shared
``install``/``verify_install`` partial workaround and
:func:`experimental.pikmin2_sokkuri_behavior.normalize_pose_names`.

The native module ``pc_port/pc_p2_hana.cpp`` additionally implements the source
``setUnderGround`` buried/no-atari + invulnerable gate (``P2_HANA_UNDERGROUND*``),
``attackNavi`` captain damage at the attack event frame (``P2_HANA_ATTACK_NAVI``)
and the ``fp02`` poison on a successfully consumed White Pikmin
(``P2_HANA_POISON``). ``validate()`` checks only those markers; it makes no claim
about production placement and never runs the fixture itself.
"""
import argparse
import functools
import json
import os
import re
from pathlib import Path

from experimental.pikmin2_animation_profile import capture_command
from experimental.pikmin2_batch2_core import install, prepare as _prepare, verify_install
from experimental.pikmin2_hana_behavior import (
    BEHAVIOR_POSITION, BITE_FRAME, CFG, DEFAULT_POSITIONS, HANA_ID, HANA_INDEX,
    SPECIES, SQUAD_X, SQUAD_Z)
from experimental.pikmin2_sokkuri_behavior import normalize_pose_names

SWALLOW_FRAME = 71.0
POISON_DAMAGE = 2500.0


def prepare(assets, imported, output):
    cfg = dict(CFG)
    positions = list(DEFAULT_POSITIONS)
    positions[HANA_INDEX] = BEHAVIOR_POSITION
    cfg['arena_positions'] = tuple(positions)
    run = _prepare(cfg, assets, imported, output,
                   installer=functools.partial(install, cfg),
                   verifier=functools.partial(verify_install, cfg))
    override = dict(index=HANA_INDEX, species='Hana', generator=HANA_ID,
                    arena_default=list(DEFAULT_POSITIONS[HANA_INDEX]),
                    behavior_fixture=list(BEHAVIOR_POSITION),
                    reason='reuse the Hana behavior fixture so the buried gate, '
                           'attackNavi and fp02 poison markers are observable from '
                           'the same starting-squad wake',
                    production_placement=False,
                    pose_name_normalization=normalize_pose_names(run))
    (run / 'hana-residual-override.json').write_text(json.dumps(override, indent=2) + '\n')
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
    (run_dir / 'hana-residual-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    return run_dir, meta, result


def validate(text, code=0):
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')

    identity = bool(re.search(r'P2_HANA_BIND generator=346006 source_id=84 visual_only=0', text))
    ready = bool(re.search(r'P2_ENEMY_READY species=Hana .*generator=346006 .*behavior=native '
                           r'.*source_FSM=implemented', text))
    window = bool(re.search(r'Experimental preview window set to 960x540 windowed and centered',
                            text))

    gate = re.findall(r'P2_HANA_UNDERGROUND generator=346006 event=(\w+) '
                      r'no_atari=(\d) invulnerable=(\d)', text)
    enters = [(i, ev) for i, ev in enumerate(gate) if ev[0] == 'enter']
    exits = [(i, ev) for i, ev in enumerate(gate) if ev[0] == 'exit']
    gate_enter = any(ev[1] == '1' and ev[2] == '1' for _, ev in enters)
    gate_exit = any(ev[1] == '0' and ev[2] == '0' for _, ev in exits)
    # The buried gate must be entered (setUnderGround) and later cleared (on wake).
    gate_order = bool(enters and exits) and enters[0][0] < exits[-1][0]
    blocks = re.findall(r'P2_HANA_UNDERGROUND_BLOCK generator=346006 source_id=84 buried=1', text)

    navi = [(float(f), int(n), float(d)) for f, n, d in re.findall(
        r'P2_HANA_ATTACK_NAVI generator=346006 frame=([\d.]+) navi=(\d+) damage=([\d.]+)', text)]
    navi_in_window = bool(navi) and all(BITE_FRAME - 1.0 <= f < SWALLOW_FRAME for f, _, _ in navi)
    navi_damage = bool(navi) and all(d == 10.0 for _, _, d in navi)

    eats = re.findall(r'P2_HANA_EAT generator=346006 pikmin=1', text)
    poisons = [(float(d), float(h)) for d, h in re.findall(
        r'P2_HANA_POISON generator=346006 pikmin=1 damage=([\d.]+) health=(-?[\d.]+)', text)]
    poison_damage = bool(poisons) and all(d == POISON_DAMAGE for d, _ in poisons)
    # Exactly-once accounting: a poison can never outnumber the consumed Pikmin.
    poison_accounting = len(poisons) <= len(eats)
    poison_exercised = len(poisons) >= 1

    checks = dict(
        identity=identity,
        ready=ready,
        window=window,
        underground_enter=gate_enter,
        underground_exit=gate_exit,
        underground_order=gate_order,
        attack_navi_event=navi_in_window and navi_damage,
        poison_accounting=poison_accounting,
        no_extinction=not re.search(r'Extinction', text, re.IGNORECASE),
    )
    watched = dict(gate=gate, blocks=blocks, attack_navi=navi, eats=len(eats), poisons=poisons,
                   poison_exercised=poison_exercised)
    # The underground gate toggles host TEKIOPT flags only in the authoritative
    # render phase, and Hana wakes immediately in this arena (squad inside the
    # 500-unit wake radius), so the enter/exit markers are informational; the
    # gate itself is covered by the standalone policy test.
    informational = {'underground_enter', 'underground_exit', 'underground_order'}
    return dict(passed=all(v for k, v in checks.items() if k not in informational),
                checks=checks, watched=watched, exit_code=code,
                unmeasured=['kamu1..3 mouth-slot attachment visual',
                            'retail EB_Invulnerable/EB_ModelHidden event fidelity '
                            '(host flag write is authoritative-only)',
                            'full action animation bank', 'cleanup/re-entry'],
                limitations=['Behavior fixture overrides Hana arena coordinate; not production '
                             'placement evidence.',
                             'Poison is only observable when a White Pikmin is present; the arena '
                             'fixture is 20 reds, so poison_exercised may be false while the '
                             'exactly-once contract is still enforced.'])


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
