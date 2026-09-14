"""Private native Dwarf Orange Bulborb (BlueKochappy 44) arena runtime.

Builds an instrumented ``preview_p2_room`` against the lane-13 private native
build (module ``pc_p2_dwarf_orange``), stages a two-actor original Impact Site
arena (source Dwarf Orange + ordinary P1 Chappy control) with a 20-red free
squad, and observes identity, source health 250, animation, natural Piki
targeting/damage/death/corpse and draw. The observer is the proven Red-dwarf
combat observer with identity/health substitutions; no enemy state is written
and no attack is injected.

Usage::

    py -3.12 -m experimental.pikmin2_dwarf_orange_runtime build \
        --native <native worktree> --build-dir <build> --output <dir> --head <sha>
    py -3.12 -m experimental.pikmin2_dwarf_orange_runtime run \
        --assets <P1 assets> --bank <bank dir> --profile <profile dir> \
        --output <dir> --exe <fixture.exe>
"""
import argparse
import json
import os
import re
import struct
import subprocess
from pathlib import Path

from experimental.pikmin2_kochappy_arena_combat import instrument as red_combat
from scripts import build_pikmin2_fixture as builder

ID_SOURCE = 211001
ID_CONTROL = 211002
HEALTH = 250
POSITIONS_FILE = 'dwarf-orange-arena-positions.txt'


def instrument(source):
    """Transform the Red-dwarf combat observer into the Dwarf Orange observer."""
    s = red_combat(source)
    s = s.replace('pc_p2_kochappy', 'pc_p2_dwarf_orange')
    s = s.replace('P2_RED', 'P2_DWARF_ORANGE')
    s = s.replace('red-arena', 'dwarf-orange-arena')
    s = s.replace('red-combat', 'dwarf-orange-combat')
    s = s.replace('186001', str(ID_SOURCE)).replace('186002', str(ID_CONTROL))
    s = s.replace('==200', '==250').replace('<200', '<250')
    if '==250' not in s or 'pc_p2_dwarf_orange.h' not in s:
        raise ValueError('Observer transform lost the Dwarf Orange identity')
    return s


def build(native, build_dir, output, head):
    native, build_dir, output = (Path(p).resolve() for p in (native, build_dir, output))
    output.mkdir(parents=True, exist_ok=False)
    room = output / 'room.cpp'
    room.write_text(instrument((native / 'tools/preview_p2_room.cpp').read_text()))
    record = builder.build_fixture(build_dir, native, room, output / 'baseline', head)
    exe = output / 'baseline' / 'fixture.exe'
    print(exe)
    return exe, record


def prepare(assets, bank, profile, output):
    """Stage the arena, then append a 20-red free squad (P1 ``ikip`` template)."""
    from experimental.pikmin2_dwarf_orange_arena import prepare as arena
    from scripts.preview_pikmin2_room import records, generator
    from experimental.pikmin2_generator_pose import write_position
    stage = arena(assets, bank, profile, output)
    path = stage / 'assets/dataDir/stages/chal0/default.gen'
    blob = generator(Path(assets).resolve())
    temporary = stage / 'template.gen'
    temporary.write_bytes(blob)
    template = next(r for r in records(temporary) if r[72:76] == b'ikip')
    entries = records(path)
    used = {struct.unpack_from('<I', r, 8)[0] for r in entries}
    for i in range(20):
        identity = 187000 + i
        if identity in used:
            raise ValueError('Squad ID collision')
        row = bytearray(template)
        struct.pack_into('<I', row, 8, identity)
        struct.pack_into('>I', row, 84, 1)
        write_position(row, (-400. + i % 5 * 8, 30., 1800. + i // 5 * 8))
        entries.append(bytes(row))
    path.write_bytes(path.read_bytes()[:20] + struct.pack('>I', len(entries)) + b''.join(entries))
    (stage / 'combat-stimuli.json').write_text(json.dumps(dict(
        field_pikmin=20, spawn='free at parked position', captain_reposition_ticks=[1, 120],
        free_squad_deployment_tick=240, enemy_state_health_writes=False), indent=2))
    return stage


def positions(stage):
    manifest = json.loads((stage / 'arena.json').read_text())
    if len(manifest['actors']) != 2:
        raise ValueError('Expected two actors')
    (stage / POSITIONS_FILE).write_text(''.join(
        str(a['generator']) + ' ' + ' '.join(map(str, a['expected_xyz'])) + '\n'
        for a in manifest['actors']))


def evidence(log, exit_code):
    rows = [dict((k, float(v)) for k, v in re.findall(r'(\w+)=([-+\d.eE]+)', line))
            for line in log.splitlines() if line.startswith('P2_DWARF_ORANGE_COMBAT ')]
    births = [line for line in log.splitlines() if line.startswith('P2_DWARF_ORANGE_ARENA_BIRTH ')]
    checks = {
        'completion': 'DONE P2_DWARF_ORANGE_COMBAT' in log,
        'identity_ready': 'P2_ENEMY_READY species=BlueKochappy source_id=44' in log,
        'bank_loaded': 'P2_DWARF_ORANGE_BANK' in log,
        'birth_control': len(births) == 2,
        'render': 'P2_DWARF_ORANGE_DRAW corpse=0' in log,
        'window': '960x540' in log,
        'target': any(r.get('target') == 1 for r in rows),
        'damage': any(r.get('health', HEALTH) < HEALTH for r in rows),
        'death_corpse': any(r.get('corpses', 0) > 0 for r in rows),
        'corpse_render': 'P2_DWARF_ORANGE_DRAW corpse=1' in log,
        'chase': any(r.get('state') == 11 and r.get('target') == 1 for r in rows),
        'no_extinction': 'Extinction' not in log,
    }
    metrics = {
        'health_samples': sorted({r.get('health') for r in rows}),
        'first_damage_tick': next((r['tick'] for r in rows if r.get('health', HEALTH) < HEALTH), None),
        'zero_health_tick': next((r['tick'] for r in rows if r.get('health', HEALTH) <= 0), None),
        'corpse_tick': next((r['tick'] for r in rows if r.get('corpses', 0) > 0), None),
    }
    return dict(metrics=metrics, passed=exit_code == 0 and all(checks.values()),
                checks=checks, exit_code=exit_code, rows=rows,
                scope='Captain reposition and20 free Pikmin deployment only; native enemy FSM, health and damage untouched.',
                unmeasured=['player input combat', 'delivery', 'P2 FSM parity'])


def run(stage, exe, output, timeout=180):
    from experimental.pikmin2_animation_profile import capture_command
    import hashlib
    stage = Path(stage).resolve()
    output = Path(output).resolve()
    positions(stage)
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    meta = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                           stage, output, timeout)
    report = evidence((output / 'native.log').read_text(errors='replace'), meta['exit_code'])
    report['capture'] = meta
    report['arena_sha256'] = hashlib.sha256((stage / 'arena.json').read_bytes()).hexdigest()
    (output / 'evidence.json').write_text(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build')
    for name in ('native', 'build-dir', 'output'):
        b.add_argument('--' + name, type=Path, required=True)
    b.add_argument('--head', required=True)
    p = sub.add_parser('prepare')
    for name in ('assets', 'bank', 'profile', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    r = sub.add_parser('run')
    for name in ('stage', 'exe', 'output'):
        r.add_argument('--' + name, type=Path, required=True)
    r.add_argument('--timeout', type=int, default=180)
    args = parser.parse_args()
    if args.command == 'build':
        build(args.native, args.build_dir, args.output, args.head)
    elif args.command == 'prepare':
        print(prepare(args.assets, args.bank, args.profile, args.output))
    else:
        print(json.dumps({k: v for k, v in run(args.stage, args.exe, args.output, args.timeout).items() if k != 'rows'}, indent=2))
