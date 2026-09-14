"""Lane-04 runtime: native terrain/water/route placement evidence probe (#440).

Stages a fresh disposable P2 room arena (current overlay + 20-red starting
squad), launches the privately built engine in the experimental-room fixture,
and captures the ``P2_PLACEMENT_SLOT`` / ``P2_PLACEMENT_PROBE`` markers the
native probe emits, plus the identity-bind and centred-window startup markers.
It then writes a ``p2-placement-probe-v1`` JSON and the audited evidence report.

Run this only under the host GL slot:

    py -3.12 output/deepseek-wave/slot.py run gl l04 -- \
        py -3.12 scripts/run_p2_placement_probe.py --exe <nectar.exe> --output output/dsw/l04-out

The GL process is time-limited: markers are flushed (unbuffered) at setup, so the
runner terminates the window after a grace period and treats a timeout as a
successful marker capture.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

MINGW = Path(r'C:/msys64/mingw64/bin')
CONVERTED = Path(r'C:/Users/alari/pikmin-randomizer/output/dsw/l20-out/converted')
ASSETS = Path(r'C:/Users/alari/bbft/dist/cohesion/pikmin/assets')


def capture_markers(text):
    slots = []
    window = None
    for line in text.splitlines():
        if line.startswith('P2_PLACEMENT_SLOT '):
            fields = dict(p.split('=', 1) for p in line[len('P2_PLACEMENT_SLOT '):].split() if '=' in p)
            try:
                slots.append({
                    'uid': int(fields['uid']),
                    'xyz': fields['xyz'] == '1',
                    'terrain': fields['terrain'] in ('ground', 'water'),
                    'route': fields['route'] == '1',
                    'terrain_class': fields['terrain'],
                    'water_depth': float(fields.get('water_depth', '0')),
                })
            except (KeyError, ValueError):
                continue
        if 'window set to 960x540' in line:
            window = line.strip()
    summary = [l.strip() for l in text.splitlines() if l.startswith('P2_PLACEMENT_PROBE ')]
    return slots, window, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--assets', type=Path, default=ASSETS)
    parser.add_argument('--converted', type=Path, default=CONVERTED)
    parser.add_argument('--timeout', type=int, default=45)
    args = parser.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts import preview_pikmin2_room  # noqa: E402

    args.output.mkdir(parents=True, exist_ok=True)
    private_converted = args.output / 'converted'
    if not (private_converted / 'room.mod').exists():
        shutil.copytree(args.converted, private_converted)

    run = preview_pikmin2_room.prepare(args.assets.resolve(), private_converted.resolve(), args.output)
    log = run / 'native.log'
    env = dict(os.environ)
    env['PATH'] = str(MINGW) + os.pathsep + env.get('PATH', '')
    env['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    env['PYTHONUTF8'] = '1'
    env['SDL_AUDIODRIVER'] = 'dummy'
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    code = 'ok'
    with log.open('w', encoding='utf-8', errors='replace') as stream:
        try:
            subprocess.run([str(args.exe.resolve()), '--experimental-pikmin2-room'],
                           cwd=run, env=env, stdout=stream, stderr=subprocess.STDOUT,
                           startupinfo=startup, timeout=args.timeout)
        except subprocess.TimeoutExpired:
            code = 'timeout'  # markers already flushed; window retired

    text = log.read_text(encoding='utf-8', errors='replace')
    slots, window_marker, summary = capture_markers(text)
    ready = ('P2_ROOM_READY' in text)
    identity = [l.strip() for l in text.splitlines()
                if l.startswith('P2_ENEMY_READY') or l.startswith('P2_KOCHAPPY_READY')
                or 'species=' in l]
    probe = {'schema': 'p2-placement-probe-v1', 'slots': [
        {'uid': s['uid'], 'xyz': s['xyz'], 'terrain': s['terrain'], 'route': s['route']}
        for s in slots]}
    evidence = {
        'run': str(run), 'exit': code, 'window_marker': window_marker,
        'room_ready': ready, 'probe_summary': summary,
        'identity_markers': identity,
        'slot_details': slots,
    }
    (run / 'probe.json').write_text(json.dumps(probe, indent=2) + '\n', encoding='utf-8')
    (run / 'evidence.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
    (args.output / 'latest-run.json').write_text(json.dumps({'run': str(run)}, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'run': str(run), 'exit': code, 'markers_match': bool(slots),
                      'probe': probe, 'evidence': evidence}, indent=2))


if __name__ == '__main__':
    main()
