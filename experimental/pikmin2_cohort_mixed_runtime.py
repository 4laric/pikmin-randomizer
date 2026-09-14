"""Four-identity cohort scene: Dwarf Orange + Snow + Qurione + ShijimiChou.

Extends the lane-13 mixed run (which already stages Dwarf Orange, Snow Bulborb,
the P1 control, the Pod anchor and a 20-red squad) with the lane-15 Qurione and
ShijimiChou identities. Probe only.

Usage::

    py -3.12 -m experimental.pikmin2_cohort_mixed_runtime prepare \
        --base-run <lane13-mixed-run> --qurione-run <run> --shijimi-run <run> --output <dir>
    py -3.12 -m experimental.pikmin2_cohort_mixed_runtime run \
        --stage <run> --exe <nectar.exe> --output <dir>
"""
import argparse
import json
import os
import shutil
import struct
import uuid
from pathlib import Path

QURIONE_IDS = (203001,)
SHIJIMI_IDS = (204001, 204002)
QURIONE_POSITION = (60.0, 30.0, 1850.0)
SHIJIMI_POSITIONS = {204001: (110.0, 30.0, 1850.0), 204002: (160.0, 30.0, 1850.0)}


def _stage_gen(run):
    return Path(run) / 'assets/dataDir/stages/chal0/default.gen'


def _p2room(run):
    return Path(run) / 'assets/dataDir/courses/pikmin2room'


def _rows(source_run, wanted, positions):
    from scripts.preview_pikmin2_room import records
    from experimental.pikmin2_generator_pose import write_position
    found = {}
    for row in records(_stage_gen(source_run)):
        gen = struct.unpack_from('<I', row, 8)[0]
        if gen in wanted:
            moved = bytearray(row)
            write_position(moved, positions[gen])
            found[gen] = bytes(moved)
    if set(found) != set(wanted):
        raise ValueError('Missing actor rows: ' + str(sorted(set(wanted) - set(found))))
    return [found[g] for g in wanted]


def _install_species(run, source_run, configs, prefix):
    for name in configs:
        shutil.copyfile(Path(source_run) / name, Path(run) / name)
    mods = sorted(_p2room(source_run).glob(prefix + '_*.mod'))
    if not mods:
        raise ValueError('Missing pose bank for ' + prefix)
    for mod in mods:
        shutil.copyfile(mod, _p2room(run) / mod.name)
    return len(mods)


def prepare(base_run, qurione_run, shijimi_run, output):
    base_run, qurione_run, shijimi_run = (Path(p).resolve() for p in (base_run, qurione_run, shijimi_run))
    output = Path(output).resolve()
    run = output / uuid.uuid4().hex
    shutil.copytree(base_run, run)
    qmods = _install_species(run, qurione_run,
                             ('p2-qurione-bank.txt', 'p2-qurione-actors.txt'), 'qurione')
    smods = _install_species(run, shijimi_run,
                             ('p2-shijimi-bank.txt', 'p2-shijimi-actors.txt'), 'shijimi')
    from scripts.preview_pikmin2_room import records
    gen = _stage_gen(run)
    entries = list(records(gen))
    entries += _rows(qurione_run, QURIONE_IDS, {QURIONE_IDS[0]: QURIONE_POSITION})
    entries += _rows(shijimi_run, SHIJIMI_IDS, SHIJIMI_POSITIONS)
    gen.write_bytes(gen.read_bytes()[:20] + struct.pack('>I', len(entries)) + b''.join(entries))
    result = dict(schema=1, scene='cohort-mixed', identities=[211001, 5001, 203001, 204001, 204002],
                  qurione_mods=qmods, shijimi_mods=smods,
                  command=['nectar.exe', '--experimental-pikmin2-room'],
                  note='Private four-identity arena; not a generated-session admission.')
    (run / 'cohort-mixed.json').write_text(json.dumps(result, indent=2))
    return run


def evidence(log, exit_code):
    checks = {
        'window': '960x540' in log,
        'dwarf_orange': 'P2_ENEMY_READY species=BlueKochappy source_id=44' in log,
        'snow': 'P2_ENEMY_READY species=YellowKochappy' in log,
        'qurione': ('P2_QURIONE_BIND generator=203001' in log
                    and 'P2_ENEMY_READY species=Qurione' in log),
        'shijimi': ('P2_SHIJIMI_BIND generator=204001' in log
                    and 'P2_ENEMY_READY species=ShijimiChou' in log),
        'dwarf_orange_draw': 'P2_DWARF_ORANGE_DRAW corpse=0' in log,
        'snow_draw': 'P2_SNOW_DRAW corpse=0' in log,
        'qurione_draw': 'P2_QURIONE_DRAW corpse=0' in log,
        'shijimi_draw': 'P2_SHIJIMI_DRAW corpse=0' in log,
        'no_extinction': 'Extinction' not in log,
    }
    return dict(passed=all(checks.values()), checks=checks, exit_code=exit_code,
                scope='Four native identities staged together; direct run, timer-terminated.',
                unmeasured=['generated-session admission', 'accepted performance budget',
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
    for name in ('base-run', 'qurione-run', 'shijimi-run', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    r = sub.add_parser('run')
    for name in ('stage', 'exe', 'output'):
        r.add_argument('--' + name, type=Path, required=True)
    r.add_argument('--seconds', type=float, default=40)
    a = parser.parse_args()
    if a.command == 'prepare':
        print(prepare(a.base_run, a.qurione_run, a.shijimi_run, a.output))
    else:
        print(json.dumps(run(a.stage, a.exe, a.output, a.seconds), indent=2))
