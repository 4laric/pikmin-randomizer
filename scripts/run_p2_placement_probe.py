"""Lane-04 runtime: native terrain/water/route placement evidence probe (#440).

Stages a fresh disposable P2 room arena (current overlay + 20-red starting
squad), launches the privately built engine in the experimental-room fixture,
and captures the ``P2_PLACEMENT_SLOT`` / ``P2_PLACEMENT_PROBE`` markers the
native probe emits, plus the identity-bind and centred-window startup markers.
It then writes a ``p2-placement-probe-v1`` JSON and the audited evidence report.

Run this only under the host GL slot:

    py -3.12 output/deepseek-wave/slot.py run gl l04 -- \
        py -3.12 scripts/run_p2_placement_probe.py --exe <nectar.exe> \
            --converted <room105 dir> --output output/dsw/l04-out

The converted room (``room.mod``/``room.ini``/``treasure.mod``) is a required
input and defaults to the documented ``output/pikmin2-room105`` path; pass
``--converted`` if that directory is absent on this host. The MinGW runtime
(needed for the engine DLLs) is discovered from ``MINGW_BIN`` or ``PATH``, never
hardcoded.

The GL process is time-limited: markers are flushed (unbuffered) at setup, so the
runner terminates the window after a grace period and treats a timeout as a
successful marker capture.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ASSETS = Path(r'C:/Users/alari/bbft/dist/cohesion/pikmin/assets')
DEFAULT_CONVERTED = Path(r'C:/Users/alari/pikmin-randomizer/output/pikmin2-room105')
_CONVERTED_FILES = ('room.mod', 'room.ini', 'treasure.mod')


def _find_mingw():
    env = os.environ.get('MINGW_BIN')
    if env and (Path(env) / 'SDL2.dll').exists():
        return str(Path(env))
    for entry in os.environ.get('PATH', '').split(os.pathsep):
        if entry and (Path(entry) / 'SDL2.dll').exists():
            return entry
    fallback = Path(r'C:/msys64/mingw64/bin')
    return str(fallback) if (fallback / 'SDL2.dll').exists() else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--assets', type=Path, default=ASSETS)
    parser.add_argument('--converted', type=Path, default=DEFAULT_CONVERTED)
    parser.add_argument('--timeout', type=int, default=45)
    args = parser.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts import preview_pikmin2_room  # noqa: E402
    from randomizer import p2_placement_probe  # noqa: E402

    missing = [name for name in _CONVERTED_FILES if not (args.converted / name).exists()]
    if missing:
        raise SystemExit(
            f'Converted room inputs missing from {args.converted}: {", ".join(missing)}. '
            f'Pass --converted to a directory with room.mod/room.ini/treasure.mod.')

    args.output.mkdir(parents=True, exist_ok=True)
    run = preview_pikmin2_room.prepare(args.assets.resolve(), args.converted.resolve(), args.output)
    log = run / 'native.log'
    env = dict(os.environ)
    mingw = _find_mingw()
    if mingw:
        env['PATH'] = mingw + os.pathsep + env.get('PATH', '')
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
    slots, window_marker, summary = p2_placement_probe.capture_markers(text)
    ready = ('P2_ROOM_READY' in text)
    probe = p2_placement_probe.build_probe(text)
    evidence = {
        'run': str(run), 'exit': code, 'window_marker': window_marker,
        'room_ready': ready, 'probe_summary': summary,
        'identity_markers': [l.strip() for l in text.splitlines()
                             if l.startswith('P2_ENEMY_READY') or l.startswith('P2_KOCHAPPY_READY')
                             or 'species=' in l],
        'slot_details': slots,
    }
    (run / 'probe.json').write_text(json.dumps(probe, indent=2) + '\n', encoding='utf-8')
    (run / 'evidence.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
    (args.output / 'latest-run.json').write_text(json.dumps({'run': str(run)}, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'run': str(run), 'exit': code, 'markers_match': bool(slots),
                      'probe': probe, 'evidence': evidence}, indent=2))


if __name__ == '__main__':
    main()
