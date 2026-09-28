"""Lane 13/15 three-identity mixed scene: Dwarf Orange + Qurione + ShijimiChou.

Adds the lane-13 Dwarf Orange identity to the lane-15 Qurione + ShijimiChou
mixed arena, all on the combined native candidate. Probe only.

Usage::

    py -3.12 -m experimental.pikmin2_lane1315_mixed_runtime prepare \
        --lane15-run <run> --orange-run <run> --output <dir>
    py -3.12 -m experimental.pikmin2_lane1315_mixed_runtime run \
        --stage <run> --exe <nectar.exe> --output <dir>
"""
import argparse
import json
import os
import re
import shutil
import struct
import uuid
from pathlib import Path

ORANGE_GENERATOR = 211001
ORANGE_POSITION = (-200.0, 30.0, 1650.0)


def _stage_gen(run):
    return Path(run) / 'assets/dataDir/stages/chal0/default.gen'


def _p2room(run):
    return Path(run) / 'assets/dataDir/courses/pikmin2room'


def _orange_row(orange_run):
    from scripts.preview_pikmin2_room import records
    from experimental.pikmin2_generator_pose import write_position
    for row in records(_stage_gen(orange_run)):
        if struct.unpack_from('<I', row, 8)[0] == ORANGE_GENERATOR:
            moved = bytearray(row)
            write_position(moved, ORANGE_POSITION)
            return bytes(moved)
    raise ValueError('Dwarf Orange actor row not found')


def prepare(lane15_run, orange_run, output):
    """Copy a lane-15 mixed run and add the Dwarf Orange identity + assets."""
    from scripts.preview_pikmin2_room import records
    lane15_run, orange_run = Path(lane15_run).resolve(), Path(orange_run).resolve()
    output = Path(output).resolve()
    run = output / uuid.uuid4().hex
    shutil.copytree(lane15_run, run)
    for name in ('p2-dwarf-orange-profile.txt', 'p2-dwarf-orange-bank.txt',
                 'p2-dwarf-orange-actors.txt'):
        shutil.copyfile(orange_run / name, run / name)
    mods = sorted(_p2room(orange_run).glob('dwarf_orange_*.mod'))
    if not mods:
        raise ValueError('Dwarf Orange pose bank missing')
    for mod in mods:
        shutil.copyfile(mod, _p2room(run) / mod.name)
    gen = _stage_gen(run)
    entries = records(gen)
    if any(struct.unpack_from('<I', r, 8)[0] == ORANGE_GENERATOR for r in entries):
        raise ValueError('Dwarf Orange generator already present')
    entries.append(_orange_row(orange_run))
    gen.write_bytes(gen.read_bytes()[:20] + struct.pack('>I', len(entries)) + b''.join(entries))
    result = dict(schema=1, scene='lane13-15-mixed', orange=ORANGE_GENERATOR,
                  qurione=203001, shijimi=[204001, 204002],
                  orange_pose_mods=len(mods),
                  command=['nectar.exe', '--experimental-pikmin2-room'],
                  note='Private three-identity arena; no generated-session admission.')
    (run / 'lane1315-mixed.json').write_text(json.dumps(result, indent=2))
    return run


def evidence(log, exit_code):
    checks = {
        'window': '960x540' in log,
        'orange_bind': 'P2_ENEMY_READY species=BlueKochappy source_id=44' in log,
        'orange_bank': 'P2_DWARF_ORANGE_BANK' in log,
        'orange_draw': 'P2_DWARF_ORANGE_DRAW corpse=0' in log,
        'qurione_bind': ('P2_QURIONE_BIND generator=203001 source_id=16' in log
                         and 'source_FSM=implemented' in log),
        'qurione_draw': 'P2_QURIONE_DRAW corpse=0' in log,
        'shijimi_bind': ('P2_SHIJIMI_BIND generator=204001 source_id=77' in log
                         and 'P2_ENEMY_READY species=ShijimiChou' in log),
        'shijimi_draw': 'P2_SHIJIMI_DRAW corpse=0' in log,
        'no_extinction': 'Extinction' not in log,
    }
    return dict(passed=all(checks.values()), checks=checks, exit_code=exit_code,
                scope='Three lane-13/15 native identities staged together; direct run, timer-terminated.',
                unmeasured=['generated-session admission', 'combined performance budget',
                            'rewards/transport', 'cleanup/re-entry'])


def run(stage, exe, output, seconds=40):
    from experimental.pikmin2_animation_profile import capture_command
    stage = Path(stage).resolve()
    output = Path(output).resolve()
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    meta = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                           stage, output, seconds)
    report = evidence((output / 'native.log').read_text(errors='replace'), meta['exit_code'])
    report['capture'] = meta
    (output / 'evidence.json').write_text(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare')
    for name in ('lane15-run', 'orange-run', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    r = sub.add_parser('run')
    for name in ('stage', 'exe', 'output'):
        r.add_argument('--' + name, type=Path, required=True)
    r.add_argument('--seconds', type=float, default=40)
    a = parser.parse_args()
    if a.command == 'prepare':
        print(prepare(a.lane15_run, a.orange_run, a.output))
    else:
        print(json.dumps(run(a.stage, a.exe, a.output, a.seconds), indent=2))
