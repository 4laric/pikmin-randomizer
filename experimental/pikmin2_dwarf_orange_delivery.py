"""Original-map P1 corpse delivery for the lane-13 Dwarf Orange Bulborb candidate.

Deliberately no P2 reward/Pod semantics: this closes the lane-13 "carry" leg of
the natural chain (source variant corpse carried to a real goal) while recording
that P2 once-credit/idempotency remains the lane-06 contract.
"""
import json
import os
import re
from pathlib import Path

from experimental.pikmin2_kochappy_arena_delivery import instrument as red_delivery
from experimental.pikmin2_dwarf_orange_runtime import orange, positions


def instrument(source):
    s = orange(red_delivery(source))
    if 'P2_DWARF_ORANGE_P1_DELIVERY' not in s:
        raise ValueError('Delivery transform lost the Dwarf Orange identity')
    return s


def prepare(assets, bank, profile, output):
    """Reuse the combat staging: two actors plus a 20-red free squad."""
    from experimental.pikmin2_dwarf_orange_runtime import prepare as combat_prepare
    return combat_prepare(assets, bank, profile, output)


def build(native, build_dir, output, head):
    from experimental.pikmin2_dwarf_orange_runtime import build_fixture_for
    return build_fixture_for(instrument, native, build_dir, output, head)


def evidence(log, code):
    done = re.search(r'PASS P2_DWARF_ORANGE_P1_DELIVERY distance=([\d.]+) reached=1 '
                     r'p2_receipts=not_applicable', log)
    rows = [dict((k, float(v)) for k, v in re.findall(r'(\w+)=([-+\d.eE]+)', line))
            for line in log.splitlines() if line.startswith('P2_DWARF_ORANGE_P1_HAUL ')]
    checks = {
        'birth_control': log.count('P2_DWARF_ORANGE_ARENA_BIRTH ') == 2,
        'corpse_render': 'P2_DWARF_ORANGE_DRAW corpse=1' in log,
        'transport': any(r.get('transport', 0) > 0 for r in rows),
        'route_goal': bool(done and float(done.group(1)) > 100),
    }
    return dict(passed=code == 0 and all(checks.values()), checks=checks, exit_code=code,
                rows=rows, transport_task_injected='P2_DWARF_ORANGE_P1_TRANSPORT_TASK' in log,
                p2_receipt_gate='not applicable: no Pod; ordinary P1 corpse delivery',
                unmeasured=['P2 once-credit/idempotency', 'actual spawned seed yield',
                            'player-controlled haul'])


def run(stage, exe, output, seconds=150):
    from experimental.pikmin2_animation_profile import capture_command
    stage = Path(stage).resolve()
    positions(stage)
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    meta = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                           stage, output, seconds)
    result = evidence((output / 'native.log').read_text(errors='replace'), meta['exit_code'])
    result['capture'] = meta
    (output / 'evidence.json').write_text(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('stage', 'exe', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    a = parser.parse_args()
    r = run(a.stage.resolve(), a.exe.resolve(), a.output.resolve())
    print(json.dumps({k: v for k, v in r.items() if k != 'rows'}, indent=2))
