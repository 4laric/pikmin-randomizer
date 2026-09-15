"""Lane 06 ordinary Onion/AP receipt runtime acceptance (#441) / assignment 3.

Stages a real native randomizer session (``randomizer.seed.generate`` +
``NativeRun`` bootstrap and ``state.txt`` refresh; no live AP server), deploys
the real 20-Pikmin squad as a free squad around a real Dwarf Bulborb, lets the
squad kill it, then observes the real corpse being naturally carried into the
real Onion endpoint (``GoalItem::suckMe`` -> ``pc_randomizer_corpse_delivered``
-> ``pc_randomizer_check``). A second fresh process against the same session
proves the ordinary check is granted exactly once across restart.

The fixture source is ``scripts/p2_ordinary_receipt_fixture.cpp`` (replacement
main), built with ``scripts/build_pikmin2_fixture.py``. No enemy health/state is
injected and the carry is not injected: the only stimulus is captain/squad
placement. The run also emits the observed native slot, terrain and carry route
so lane 04 can ingest them as placement evidence. See
``docs/PIKMIN2_REWARD_RECEIPTS.md``.
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
import threading
import uuid
import _winapi
from pathlib import Path

TARGET = 'Bestiary: Deliver Dwarf Bulborb'
VECTOR = r'([-+\d.eE]+),([-+\d.eE]+),([-+\d.eE]+)'


def _vec(match, offset=1):
    return [float(match.group(offset + i)) for i in (0, 1, 2)]


def _finite_vec(value):
    """Coerce a possibly-None/NaN marker triple into a finite triple or None."""
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None
    out = []
    for item in value:
        try:
            item = float(item)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(item):
            return None
        out.append(item)
    return out


def parse_markers(text):
    """Extract the fixture's native placement/route markers."""
    data = {'carry': [], 'blocked_waypoints': []}
    stage = re.search(r'START_STAGE (\d+)', text)
    if stage:
        data['stage'] = int(stage.group(1))
    for line in text.splitlines():
        if line.startswith('P2_ORD_SLOT '):
            m = re.search(r'gen=' + VECTOR + r' actor=' + VECTOR, line)
            if m:
                data['slot'] = {'generator_position': _vec(m, 1), 'actor_spawn': _vec(m, 4)}
        elif line.startswith('P2_ORD_SQUAD '):
            m = re.search(r'free=(\d+) control_others=(\d+)', line)
            if m:
                data['squad'] = {'free': int(m.group(1)), 'control_others': int(m.group(2))}
        elif line.startswith('P2_ORD_DEATH '):
            m = re.search(r'frame=(\d+)', line)
            if m:
                data['death_frame'] = int(m.group(1))
        elif line.startswith('P2_ORD_CORPSE '):
            m = re.search(r'x=' + VECTOR + r' onion=' + VECTOR, line)
            if m:
                data['corpse_start'] = _vec(m, 1)
                data['onion'] = _vec(m, 4)
        elif line.startswith('P2_ORD_WP '):
            m = re.search(r'idx=(\d+) pos=' + VECTOR + r' open=(\d) flags=(\d+) dist=([\d.]+)', line)
            if m:
                data['blocked_waypoints'].append({'index': int(m.group(1)), 'position': _vec(m, 2),
                                                  'open': int(m.group(5)), 'flags': int(m.group(6)),
                                                  'distance_to_corpse': float(m.group(7))})
        elif line.startswith('P2_ORD_CARRY '):
            m = re.search(r'moved=([\d.]+) natural=(\d) transporting=(\d+)', line)
            p = re.search(r'pos=' + VECTOR, line)
            b = re.search(r'blocked=(\d)', line)
            if m:
                row = {'moved': float(m.group(1)), 'natural': int(m.group(2)),
                       'transporting': int(m.group(3))}
                if p:
                    row['pos'] = _vec(p)
                if b:
                    row['blocked'] = int(b.group(1))
                data['carry'].append(row)
        elif line.startswith('P2_ORD_RESULT '):
            m = re.search(r'natural_carry=(\d) route=([\d.]+) frame=(\d+) control_others=(\d+)', line)
            if m:
                data['result'] = {'natural_carry': int(m.group(1)), 'route': float(m.group(2)),
                                  'frame': int(m.group(3)), 'control_others': int(m.group(4))}
        elif line.startswith('P2_ORD_ROUTE '):
            m = re.search(r'origin=' + VECTOR + r' corner=' + VECTOR + r' onion=' + VECTOR, line)
            if m:
                data['route'] = {'origin': _vec(m), 'corner': [float(m.group(i)) for i in (4, 5, 6)],
                                 'onion': [float(m.group(i)) for i in (7, 8, 9)]}
    return data


def run_once(session, exe, assets, label):
    from randomizer.runner import NativeRun
    native_run = NativeRun(session)
    run = native_run.directory
    _winapi.CreateJunction(str(assets.resolve()), str((run / 'assets').resolve()))
    done = threading.Event()

    def refresh():
        while not done.is_set():
            native_run.write_state(True)
            done.wait(0.1)

    threading.Thread(target=refresh, daemon=True).start()
    env = dict(os.environ, SDL_AUDIODRIVER='dummy', PIKMIN_RANDOMIZER_TEST_BACKGROUND='1')
    env.pop('BBFT_PORT', None)
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    log = run / 'native.log'
    try:
        with log.open('w') as stream:
            try:
                code = subprocess.run([str(exe), '--randomizer-seed', str(native_run.bootstrap.resolve())],
                                      cwd=run, env=env, startupinfo=startup, stdout=stream,
                                      stderr=subprocess.STDOUT, timeout=720).returncode
            except subprocess.TimeoutExpired:
                code = 'timeout'
    finally:
        done.set()
    text = log.read_text(errors='replace')
    checks = run / 'checks.txt'
    names = [session.names[int(x)] for x in checks.read_text().split()] if checks.exists() else []
    target_lines = [line for line in text.splitlines() if 'CHECK' in line and TARGET in line]
    markers = parse_markers(text)
    print(f'[{label}] exit={code} target_check_lines={len(target_lines)} checks={names}')
    return code, names, target_lines, run, markers


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--assets', type=Path,
                        default=Path(os.environ.get('APPDATA', '')) / 'PikminRandomizer' / 'game-data' / 'assets')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', default='lane06-ordinary-restart')
    args = parser.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from randomizer.seed import generate
    from randomizer.session import Session
    from randomizer.catalog import ITEM_IDS

    args.output.mkdir(parents=True, exist_ok=True)
    manifest = generate(args.seed, 'ap', expanded=True, all_areas=True,
                        collection_checks=True, starting_flarlic=10)
    session = Session(manifest, args.output / ('session-' + uuid.uuid4().hex[:8]))
    session.bind_ap('lane06-fixture', 0, 1)
    wanted = [uid for name, uid in ITEM_IDS.items()
              if uid in session.allowed_items and (name.endswith('Onion') or name.endswith('Access'))]
    session.receive(0, wanted)
    print('schema', manifest['schema'], 'catalog', manifest['catalog'])

    code1, names1, lines1, run1, markers1 = run_once(session, args.exe, args.assets, 'run1')
    for name in names1:
        if name not in session.data['checked']:
            session.collect(name)
    code2, names2, lines2, run2, markers2 = run_once(session, args.exe, args.assets, 'run2')

    natural = markers1.get('result', {}).get('natural_carry') == 1
    transported = any(row['transporting'] > 0 for row in markers1.get('carry', []))
    route = markers1.get('result', {}).get('route', 0.0)
    blocked = any(row.get('blocked') == 1 for row in markers1.get('carry', [])) or bool(markers1.get('blocked_waypoints'))
    checks = {
        'run1_exit_ok': code1 == 0,
        'run1_one_target_check': len(lines1) == 1,
        'target_checked': TARGET in session.data['checked'],
        'natural_carry': natural,
        'free_squad_deployed': markers1.get('squad', {}).get('free', 0) > 0,
        'real_transport': transported,
        'route_length': route > 100.0,
        'run2_exit_ok': code2 == 0,
        'run2_no_duplicate': len(lines2) == 0,
    }
    ok = all(checks.values())
    evidence = {
        'target': TARGET,
        'checks': checks,
        'block_finding': {
            'route_blocked': bool(blocked),
            'stall_moved': max((r['moved'] for r in markers1.get('carry', [])), default=0.0),
            'blocked_waypoints': markers1.get('blocked_waypoints', []),
            'note': 'carry route to the target Onion passes blocked/Pebble waypoints (STATE_Guru spin)' if blocked else None,
        },
        'run1': {'exit': code1, 'run': str(run1), 'markers': markers1},
        'run2': {'exit': code2, 'run': str(run2), 'markers': markers2},
        'placement_evidence': {
            'generator_position': markers1.get('slot', {}).get('generator_position'),
            'actor_spawn': markers1.get('slot', {}).get('actor_spawn'),
            'corpse_start': markers1.get('corpse_start'),
            'corpse_end': markers1.get('route', {}).get('corner'),
            'onion': markers1.get('route', {}).get('onion'),
            'route_length': route,
        },
        'ordinary_ledger': True,
        'pod_ledger': False,
    }
    (args.output / 'ordinary-receipt-evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    # Trustworthy placement evidence is emitted only when the run actually
    # reached a natural terminal delivery through the real Onion endpoint.
    # A run that merely carried the corpse partway and then stalled
    # (no_natural_delivery, run6) must not raise a slot.
    delivered = bool(code1 == 0 and natural and TARGET in session.data['checked'])
    placement = {
        'schema': 'p2-placement-evidence-v1',
        'stage': markers1.get('stage'),
        'actor_spawn': _finite_vec(markers1.get('slot', {}).get('actor_spawn')),
        'generator_position': _finite_vec(markers1.get('slot', {}).get('generator_position')),
        'onion': _finite_vec((markers1.get('route', {}) or {}).get('onion') or markers1.get('onion')),
        'route_length': route if math.isfinite(route) else None,
        'control_others': markers1.get('result', {}).get('control_others'),
        'delivered': delivered,
        'injected': False,
        'source': {'seed': args.seed, 'run': str(run1), 'target': TARGET},
        'ordinary_ledger': True,
        'pod_ledger': False,
    }
    from randomizer.p2_placement_evidence import publish_evidence
    if publish_evidence(args.output / 'placement-evidence.json', placement):
        print('PLACEMENT_EVIDENCE_TRUSTED:', placement['stage'])
    else:
        print('PLACEMENT_EVIDENCE_UNTRUSTED: missing or invalid natural delivery evidence')
    print('EXACTLY_ONCE_ACROSS_RESTART:', ok)
    print('run1', run1)
    print('run2', run2)
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
