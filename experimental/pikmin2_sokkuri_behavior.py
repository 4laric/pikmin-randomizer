"""Sokkuri (Skitter Leaf, EnemyID 79) source-behavior acceptance (#407/#165).

Builds the batch-2 ground-invertebrate private arena, then overrides Sokkuri's
private arena coordinate so the 20-red fixture squad (x in [-140,-68], z in
[1812,1820]) sits inside the source sight radius (fp12=150) of the actor. That
makes the source Stay -> Appear -> MoveGround -> Wait/Disappear cycle observable
in an unattended run; it is an explicit behavior-fixture override, not production
placement evidence.

The native module (`pc_port/pc_p2_sokkuri.cpp`) drives the FSM and prints
`P2_SOKKURI_*` markers. `validate()` checks only those source-behavior markers;
no disc assets, builds or player saves are touched here.
"""
import argparse
import functools
import json
import os
import re
from pathlib import Path

from experimental.pikmin2_animation_profile import capture_command
from experimental.pikmin2_batch2_core import install, prepare as _prepare, verify_install

try:
    from experimental.pikmin2_batch2_families import FAMILIES
    CFG = dict(FAMILIES['ground'])
except Exception:  # pragma: no cover - import stub used by unit tests
    CFG = {}

IDS = tuple(CFG.get('arena_ids', (346001, 346002, 346003, 346004, 346005, 346006, 346007)))
SOKKURI_ID = 346005
SPECIES = tuple(CFG.get('arena_species', ('Armor', 'ElecBug', 'Imomushi', 'TamagoMushi',
                                          'Sokkuri', 'Hana', 'P1 Chappy')))
SOKKURI_INDEX = SPECIES.index('Sokkuri')
# Evenly spaced engineered row used by the shared batch-2 arena builder.
DEFAULT_POSITIONS = tuple(((-(len(SPECIES) - 2) / 2 + index) * 120.0, 30.0, 1850.0)
                          for index in range(len(SPECIES) - 1)) + ((240.0, 30.0, 1500.0),)
BEHAVIOR_POSITION = (-100.0, 30.0, 1850.0)

SQUAD_X = tuple(-140.0 + (index % 10) * 8.0 for index in range(20))
SQUAD_Z = tuple(1820.0 - (index // 10) * 8.0 for index in range(20))


def position_override():
    return dict(index=SOKKURI_INDEX, species='Sokkuri', generator=SOKKURI_ID,
                arena_default=list(DEFAULT_POSITIONS[SOKKURI_INDEX]),
                behavior_fixture=list(BEHAVIOR_POSITION),
                reason='place Sokkuri within the source fp12=150 sight radius of the '
                       'starting squad so the Stay/Appear/Move FSM is observable',
                production_placement=False)


def normalize_pose_names(run):
    """Copy misindexed pose files to the contiguous names the native bank loader
    reconstructs.

    The converted ground bank names Sokkuri `appear1`'s single pose `_01` (the
    native loader expects `_00` for pose index 0). This is a private fixture
    normalization only; no shared converter, install receipt or committed asset
    is changed.
    """
    room = run / 'assets/dataDir/courses/pikmin2room'
    bank = (run / 'p2-ground-bank.txt').read_text().splitlines()
    normalized = []
    for line in bank:
        tokens = line.split()
        if not tokens or tokens[0] != 'clip':
            continue
        species, clip, poses = tokens[1], tokens[2], int(tokens[6])
        for index in range(poses):
            expected = room / f'ginv_{species}_{clip}_{index:02d}.mod'
            if expected.exists():
                continue
            candidates = sorted(room.glob(f'ginv_{species}_{clip}_*.mod'))
            if not candidates:
                continue
            expected.write_bytes(candidates[0].read_bytes())
            normalized.append(dict(species=species, clip=clip, index=index,
                                   source=candidates[0].name, target=expected.name))
    return normalized


def prepare(assets, imported, output):
    cfg = dict(CFG)
    positions = list(DEFAULT_POSITIONS)
    positions[SOKKURI_INDEX] = BEHAVIOR_POSITION
    cfg['arena_positions'] = tuple(positions)
    # The shared core's prepare() calls installer(imported, run, actors) while
    # install()/verify_install() take cfg first; bind cfg here (the ground arena
    # module itself currently hits this mismatch).
    run = _prepare(cfg, assets, imported, output,
                   installer=functools.partial(install, cfg),
                   verifier=functools.partial(verify_install, cfg))
    override = position_override()
    override['pose_name_normalization'] = normalize_pose_names(run)
    (run / 'sokkuri-override.json').write_text(json.dumps(override, indent=2) + '\n')
    return run


def run(assets, imported, output, exe, seconds=25):
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    # The private MinGW build needs the toolchain runtime DLLs on PATH.
    os.environ['PATH'] = 'C:\\msys64\\mingw64\\bin;' + os.environ.get('PATH', '')
    run_dir = prepare(Path(assets), Path(imported), Path(output))
    meta = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                           run_dir, run_dir / 'capture', seconds)
    text = (run_dir / 'capture' / 'native.log').read_text(errors='replace')
    result = validate(text, meta['exit_code'])
    result['capture'] = {k: meta[k] for k in ('executable_sha256', 'elapsed_seconds',
                                              'exit_code', 'timed_out')}
    (run_dir / 'sokkuri-validation.json').write_text(
        json.dumps(result, indent=2) + '\n')
    return run_dir, meta, result


def validate(text, code=0):
    """Check the native log against the source FSM contract.

    Confined to `P2_SOKKURI_*` / batch-2 bind markers so it makes no claim about
    unrelated families or about production placement.
    """
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    positions = [(m.group(1), m.group(2), float(m.group(3)), float(m.group(4)), float(m.group(5)))
                 for m in re.finditer(
        r'P2_SOKKURI_POS generator=346005 state=(\w+) clip=(\w+) phase=([\d.]+) '
        r'x=(-?[\d.]+) z=(-?[\d.]+)', text)]
    moving = [p for p in positions if p[0] == 'moveground']
    spread = 0.0
    if len(moving) >= 2:
        x0, z0 = moving[0][3], moving[0][4]
        spread = max(abs(x - x0) + abs(z - z0) for _, _, _, x, z in moving)
    clips_seen = {p[1] for p in positions}
    run_phases = [p[2] for p in positions if p[1] == 'run1']
    phase_spread = (max(run_phases) - min(run_phases)) if len(run_phases) >= 2 else 0.0
    animation = 'run1' in clips_seen and len(clips_seen) >= 2 and phase_spread > 0.05
    checks = dict(
        identity=bool(re.search(r'P2_SOKKURI_BIND generator=346005 source_id=79 visual_only=0', text)),
        ready=bool(re.search(r'P2_ENEMY_READY species=Sokkuri .*generator=346005 .*behavior=native '
                             r'.*source_FSM=implemented', text)),
        window=bool(re.search(r'Experimental preview window set to 960x540 windowed and centered', text)),
        hidden_start=bool(re.search(r'P2_SOKKURI_DISGUISE generator=346005 hidden=1', text)),
        appear=(bool(re.search(r'P2_SOKKURI_DISGUISE generator=346005 hidden=0', text))
                and bool(re.search(r'P2_SOKKURI_STATE generator=346005 state=appear', text))),
        move=bool(re.search(r'P2_SOKKURI_STATE generator=346005 state=moveground', text)),
        autonomous_motion=len(moving) >= 2 and spread > 5.0,
        animation=animation,
        no_extinction=not re.search(r'Extinction', text, re.IGNORECASE),
    )
    return dict(passed=all(checks.values()), checks=checks, motion_spread=spread,
                clips_seen=sorted(clips_seen), sampled_positions=len(positions), exit_code=code,
                unmeasured=['full action animation bank', 'water (MoveWater) branch',
                            'natural controller play', 'corpse carry/delivery receipt'],
                limitations=['Behavior fixture overrides Sokkuri arena coordinate; not production '
                             'placement evidence.', 'View-angle detection is a documented port '
                             'adaptation (fp13 absent from the Sokkuri general block).'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('prepare', 'run'):
        sub = commands.add_parser(name)
        for flag in ('assets', 'imported', 'output'):
            sub.add_argument('--' + flag, type=Path, required=True)
        if name == 'run':
            sub.add_argument('--exe', type=Path, required=True)
            sub.add_argument('--seconds', type=int, default=25)
    args = parser.parse_args()
    if args.command == 'prepare':
        print(prepare(args.assets, args.imported, args.output))
    else:
        run_dir, meta, result = run(args.assets, args.imported, args.output, args.exe, args.seconds)
        print(run_dir)
        print(json.dumps(result, indent=2))
