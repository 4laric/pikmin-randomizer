"""Dwarf Orange Pod corpse-receipt witness (gate 5 transport/reward, lane 13 #120).

Natural combat (few-Pikmin FSM) kills the source actor, ordinary Pikmin carry the
corpse to the Research Pod, and the Pod corpse-receipt branch in
``pc_p2_preview_deliver`` logs ``P2_POD_RECEIPT``. Exactly-once is the
``P2Economy`` generator-keyed receipt dedupe (``new=1`` first, ``new=0`` on a
revisit), already unit-proven by ``tools/test_p2_economy.cpp``.

No enemy state, health, target or animation is written: the death is the real
Pikmin damage path and the carry is a TransportMode order, not an injected
``pc_p2_preview_deliver`` call.
"""
import argparse
import json
import os
import re
from pathlib import Path

from experimental.pikmin2_kochappy_arena_combat import instrument as combat
from experimental.pikmin2_dwarf_orange_runtime import orange, positions
from experimental.pikmin2_dwarf_orange_cleanup import CLEANUP, COMBAT_COMPLETION
from experimental.pikmin2_mamuta_rules import stage_cargo, find_pod_package


def instrument(source):
    result = combat(source)
    if result.count(COMBAT_COMPLETION) != 1:
        raise ValueError('Unexpected combat completion anchor')
    pod_cleanup = CLEANUP.replace(
        'require(pc_p2_preview_goal()==nullptr && pc_p2_preview_pokos()==-1,'
        '"unexpected P2 reward binding");',
        'require(pc_p2_preview_pokos()>=0,"corpse did not reach the Pod");')
    pod_cleanup = pod_cleanup.replace(
        'PASS P2_RED_P1_CLEANUP', 'PASS P2_DWARF_ORANGE_P1_POD')
    transformed = '#include <algorithm>\n' + result.replace(COMBAT_COMPLETION, pod_cleanup)
    transformed = orange(transformed)
    if 'P2_DWARF_ORANGE_P1_POD' not in transformed or 'pc_p2_dwarf_orange' not in transformed:
        raise ValueError('Pod transform lost the Dwarf Orange identity')
    return transformed


def prepare(assets, bank, profile, pod_package, output):
    """Dwarf Orange arena + Research Pod (stage_cargo). Returns the run dir."""
    from experimental.pikmin2_dwarf_orange_runtime import prepare as combat_prepare
    stage = combat_prepare(Path(assets).resolve(), Path(bank).resolve(),
                           Path(profile).resolve(), Path(output).resolve())
    package = find_pod_package([Path(pod_package).resolve()])
    stage_cargo(stage, Path(assets).resolve(), package)
    return stage


def build(native, build_dir, output, head):
    from experimental.pikmin2_dwarf_orange_runtime import build_fixture_for
    return build_fixture_for(instrument, native, build_dir, output, head)


def evidence(log, code):
    receipts = re.findall(r'P2_POD_RECEIPT id=(\S+) value=(\d+) new=(\d) pokos=(\d+)', log)
    corpse = [r for r in receipts if r[0].startswith('corpse:')]
    rows = [dict((k, float(v)) for k, v in re.findall(r'(\w+)=([-+\d.eE]+)', line))
            for line in log.splitlines() if line.startswith('P2_DWARF_ORANGE_P1_HAUL ')]
    checks = {
        'birth_control': log.count('P2_DWARF_ORANGE_ARENA_BIRTH ') == 2,
        'fsm_death': 'P2_KOCHAPPY_DEAD generator=211001 source_id=44' in log,
        'pod_ready': 'P2_POD_READY' in log,
        'transport': any(r.get('transport', 0) > 0 for r in rows),
        'carried_distance': any(r.get('distance', 0) > 100 for r in rows),
        'receipt': bool(corpse) and '211001' in corpse[0][0],
        'receipt_new': bool(corpse) and corpse[0][2] == '1',
        'completion': 'PASS P2_DWARF_ORANGE_P1_POD' in log,
    }
    return dict(passed=code == 0 and all(checks.values()), checks=checks, exit_code=code,
                receipts=receipts, rows=rows,
                scope='natural few-Pikmin FSM combat (no injected enemy state) + real TransportMode carry '
                      'to the Research Pod; receipt logged by the Pod corpse-receipt branch',
                unmeasured=['exactly-once revisit (P2Economy dedupe is unit-proven; see tools/test_p2_economy.cpp)',
                            'P2 once-credit idempotency across process restart'])


def run(stage, exe, output, timeout=240):
    from experimental.pikmin2_animation_profile import capture_command
    stage = Path(stage).resolve()
    output = Path(output).resolve()
    positions(stage)
    os.environ.setdefault('PIKMIN_P2_ROOM_WINDOW', '960x540')
    meta = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                           stage, output, timeout)
    report = evidence((output / 'native.log').read_text(errors='replace'), meta['exit_code'])
    report['capture'] = meta
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
    for name in ('assets', 'bank', 'profile', 'pod-package', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    r = sub.add_parser('run')
    for name in ('stage', 'exe', 'output'):
        r.add_argument('--' + name, type=Path, required=True)
    r.add_argument('--timeout', type=int, default=240)
    args = parser.parse_args()
    if args.command == 'build':
        print(build(args.native, args.build_dir, args.output, args.head))
    elif args.command == 'prepare':
        print(prepare(args.assets, args.bank, args.profile, args.pod_package, args.output))
    else:
        print(json.dumps({k: v for k, v in run(args.stage, args.exe, args.output, args.timeout).items()
                          if k != 'rows'}, indent=2))
