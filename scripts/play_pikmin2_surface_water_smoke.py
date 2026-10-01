"""Fresh, bounded user-operated tutorial shoreline check; no manual verdict inferred."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))
from scripts.stage_pikmin2_surface_water import prepare

WORKSPACE = SOURCE_ROOT.parent.parent if SOURCE_ROOT.parent.name == 'output' else SOURCE_ROOT
IDENTITY = 'c8598f04bb884ab396d126b8dfbed6a6ce78d2f6afc92e7b366a5e5c11ccc8d5'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--expected-exe-sha256', required=True)
    parser.add_argument('--assets', type=Path, default=Path(os.environ.get('APPDATA', Path.home()))/'PikminRandomizer/game-data/assets')
    parser.add_argument('--bundle', type=Path, default=WORKSPACE/'output/p2-level-imports/tutorial-09')
    parser.add_argument('--seconds', type=int, default=60)
    args = parser.parse_args()
    if not 15 <= args.seconds <= 60:
        parser.error('--seconds must be 15..60')
    exe = args.exe.resolve(strict=True)
    if hashlib.sha256(exe.read_bytes()).hexdigest() != args.expected_exe_sha256:
        parser.error('Executable differs from the reviewed smoke build')
    output = WORKSPACE/'output/p2-surface-water'/('human-'+uuid.uuid4().hex)
    run = prepare(args.assets.resolve(), args.bundle.resolve(), IDENTITY, output, species_probe=True)
    env = {k:v for k,v in os.environ.items() if not k.startswith(('PIKMIN_RANDOMIZER_', 'P2_SURFACE_WATER_', 'P2_FULL_SURFACE_'))}
    env.update(P2_SURFACE_WATER_HUMAN_SMOKE='1', P2_SURFACE_WATER_SPECIES_PROBE='1',
               PIKMIN_P2_ROOM_WINDOW='960x540', SDL_AUDIODRIVER='dummy')
    env['PATH'] = 'C:/msys64/mingw64/bin'+os.pathsep+env.get('PATH','')
    print('Tutorial shoreline check: WASD/controller stick to walk; Shift/controller B to whistle.')
    print('Whistle the nearby Red and Blue, walk down the slope, then whistle the Red back onto high ground.')
    print('Watch for native water ripples/Red struggle; the Blue should stay safe. Water surface rendering is unfinished.')
    print('The colors and entry are staged; this is not species acquisition or full-level completion.')
    print(f'Fresh reset each launch. Close the game when finished; this run stops after {args.seconds} seconds.')
    print('No human judgment is recorded automatically. Run evidence:', run, flush=True)
    command = [str(exe), '--experimental-pikmin2-surface', 'tutorial']
    started = time.monotonic()
    with (run/'native.log').open('w', encoding='utf-8') as log:
        child = subprocess.Popen(command, cwd=run, env=env, stdout=log, stderr=subprocess.STDOUT)
        timed_out = False
        try:
            code = child.wait(timeout=args.seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            child.terminate()
            try:
                code = child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                code = child.wait(timeout=5)
    record = dict(kind='user-operated-manual-smoke', argv=command, pid=child.pid,
                  exe_sha256=args.expected_exe_sha256, seconds=args.seconds,
                  elapsed_seconds=round(time.monotonic()-started,3), exit_code=code,
                  bounded_stop=timed_out, human_judgment_recorded=False, gameplay_admission=False)
    (run/'manual-run.json').write_text(json.dumps(record, indent=2)+'\n')
    if not timed_out and code != 0:
        print(f'Game exited with code {code}; inspect {run/"native.log"}', flush=True)
        return code if 0 < code < 256 else 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
