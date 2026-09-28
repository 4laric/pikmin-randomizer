"""Lane-15 two-identity mixed scene: Qurione (16) + ShijimiChou (77).

Combines two independently implemented lane-15 native identities on one build
(the combined `pc_p2_qurione` + `pc_p2_shijimi` candidate) and one stage. This
is a probe, not a generated-session admission.

The arena is the already-staged Shijimi run (Shijimi + control + 20-red squad)
with the audited Qurione configs and a Qurione actor row (host TEKI_Qurione)
added from the audited Qurione arena. No enemy state is injected.

Usage::

    py -3.12 -m experimental.pikmin2_lane15_mixed_runtime prepare \
        --shijimi-run <run> --qurione-run <run> --output <dir>
    py -3.12 -m experimental.pikmin2_lane15_mixed_runtime run \
        --stage <run> --exe <nectar.exe> --output <dir>
"""
import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import uuid
from pathlib import Path

QURIONE_GENERATOR = 203001
SHIJIMI_GENERATOR = 204001
CONTROL_GENERATOR = 204002
QURIONE_POSITION = (-50.0, 30.0, 1750.0)


def _stage_gen(run):
    return Path(run) / 'assets/dataDir/stages/chal0/default.gen'


def _p2room(run):
    return Path(run) / 'assets/dataDir/courses/pikmin2room'


def _qurione_row(qurione_run):
    from scripts.preview_pikmin2_room import records
    from experimental.pikmin2_generator_pose import write_position
    for row in records(_stage_gen(qurione_run)):
        if struct.unpack_from('<I', row, 8)[0] == QURIONE_GENERATOR:
            moved = bytearray(row)
            write_position(moved, QURIONE_POSITION)
            return bytes(moved)
    raise ValueError('Qurione actor row not found')


def prepare(shijimi_run, qurione_run, output):
    """Copy the Shijimi run and add the Qurione identity + assets."""
    from scripts.preview_pikmin2_room import records
    shijimi_run, qurione_run = Path(shijimi_run).resolve(), Path(qurione_run).resolve()
    output = Path(output).resolve()
    run = output / uuid.uuid4().hex
    shutil.copytree(shijimi_run, run)
    for name in ('p2-qurione-bank.txt', 'p2-qurione-actors.txt'):
        shutil.copyfile(qurione_run / name, run / name)
    mods = sorted(_p2room(qurione_run).glob('qurione_*.mod'))
    if not mods:
        raise ValueError('Qurione pose bank missing')
    for mod in mods:
        shutil.copyfile(mod, _p2room(run) / mod.name)
    gen = _stage_gen(run)
    entries = records(gen)
    if any(struct.unpack_from('<I', r, 8)[0] == QURIONE_GENERATOR for r in entries):
        raise ValueError('Qurione generator already present')
    entries.append(_qurione_row(qurione_run))
    gen.write_bytes(gen.read_bytes()[:20] + struct.pack('>I', len(entries)) + b''.join(entries))
    result = dict(schema=1, scene='lane15-mixed', qurione=QURIONE_GENERATOR,
                  shijimi=[SHIJIMI_GENERATOR, CONTROL_GENERATOR],
                  qurione_position=list(QURIONE_POSITION),
                  qurione_pose_mods=len(mods),
                  command=['nectar.exe', '--experimental-pikmin2-room'],
                  note='Private mixed arena; no generated-session admission.')
    (run / 'lane15-mixed.json').write_text(json.dumps(result, indent=2))
    return run


def evidence(log, exit_code):
    checks = {
        'window': '960x540' in log,
        'qurione_bind': 'P2_QURIONE_BIND generator=203001 source_id=16' in log,
        'qurione_ready': ('P2_ENEMY_READY species=Qurione' in log
                          and 'source_FSM=implemented' in log),
        'qurione_bank': 'P2_QURIONE_BANK' in log,
        'shijimi_bind': 'P2_SHIJIMI_BIND generator=204001 source_id=77' in log,
        'shijimi_ready': 'P2_ENEMY_READY species=ShijimiChou' in log,
        'shijimi_bank': 'P2_SHIJIMI_BANK' in log,
        'qurione_draw': 'P2_QURIONE_DRAW corpse=0' in log,
        'shijimi_draw': 'P2_SHIJIMI_DRAW corpse=0' in log,
        'no_extinction': 'Extinction' not in log,
    }
    states = {m for m in re.findall(r'P2_QURIONE_STATE \S+ state=(\w+)', log)}
    return dict(passed=all(checks.values()), checks=checks, exit_code=exit_code,
                qurione_states=sorted(states),
                scope='Two lane-15 native identities staged together; direct run, timer-terminated.',
                unmeasured=['generated-session admission', 'combined performance budget',
                            'reward/transport', 'cleanup/re-entry'])


def run(stage, exe, output, seconds=40):
    from experimental.pikmin2_animation_profile import capture_command
    stage = Path(stage).resolve()
    output = Path(output).resolve()
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    meta = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                           stage, output, seconds)
    log = (output / 'native.log').read_text(errors='replace')
    report = evidence(log, meta['exit_code'])
    report['capture'] = meta
    (output / 'evidence.json').write_text(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare')
    for name in ('shijimi-run', 'qurione-run', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    r = sub.add_parser('run')
    for name in ('stage', 'exe', 'output'):
        r.add_argument('--' + name, type=Path, required=True)
    r.add_argument('--seconds', type=float, default=40)
    a = parser.parse_args()
    if a.command == 'prepare':
        print(prepare(a.shijimi_run, a.qurione_run, a.output))
    else:
        print(json.dumps(run(a.stage, a.exe, a.output, a.seconds), indent=2))
