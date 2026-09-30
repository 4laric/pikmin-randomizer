"""Headless evidence run for the Bloyster (UmiMushi 71 / 101) skewer hold and tail latch (#995).

Launches a smoke package (``scripts/p2_smoke_seed.py`` output) headless with the TEST-ONLY native
probe ``PIKMIN_P2_UMIMUSHI_PROBE=1`` (bait Pikmin ahead, eight Pikmin thrown through the real
``Navi::throwPiki`` at the tail bulb, captain moved into view) and ``PIKMIN_P2_PROXY_SHOT=<dir>``
(one BMP per key, taken 30 presented frames after the native notify), then keeps native.log and the
screenshots (converted to PNG when Pillow is available).

Capacity-gated; kills only the process tree it started (by PID). Never use this output as owner
evidence of normal play: the probe moves Pikmin and the captain. The owner package carries no probe.

Usage:
  py -3.12 scripts/p2_umimushi_probe.py --package output/smoke-bloyster/071-ranging-bloyster \
      --exe output/native-bloyster-build/bin/nectar.exe --out output/bloyster-evidence/run71 --seconds 150
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import p2_smoke_verify  # noqa: E402

DEFAULT_ASSETS = r'C:\Users\alari\bbft\dist\cohesion\pikmin\assets'
DONE_MARKERS = ('P2_UMIMUSHI_DEAD',)


def run(package, exe, out, seconds, assets, probe, autoplay, extra_env):
    package = Path(package).resolve()
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    shots = out / 'shots'
    shots.mkdir(exist_ok=True)
    session = out / 'session'
    smoke = next(package.glob('smoke-*.json'))
    actors = package / 'actors.json'
    content = package / 'content'
    env = dict(os.environ, PYTHONUTF8='1', PIKMIN_RANDOMIZER_TEST_BACKGROUND='1',
               PIKMIN_P2_SMOKE_ANY_SLOT='1', PIKMIN_P2_PROXY_SHOT=str(shots), **extra_env)
    if probe:
        env['PIKMIN_P2_UMIMUSHI_PROBE'] = '1'
    if autoplay:
        env['PIKMIN_RANDOMIZER_AUTOPLAY'] = '1'
    cmd = [sys.executable, '-m', 'randomizer', 'run', str(smoke), '--session-dir', str(session), '--exe', str(exe),
           '--assets', str(assets), '--p2-content', str(content), '--p2-actors', str(actors)]
    if not p2_smoke_verify.capacity_gate():
        raise SystemExit('capacity gate did not admit a game session')
    proc = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    text = ''
    deadline = time.time() + seconds
    try:
        while time.time() < deadline and proc.poll() is None:
            logs = glob.glob(str(session / 'runs' / '*' / 'native.log'))
            if logs:
                text = Path(logs[0]).read_text(encoding='utf-8', errors='replace')
                if any(m in text for m in DONE_MARKERS):
                    time.sleep(6.0)
                    text = Path(logs[0]).read_text(encoding='utf-8', errors='replace')
                    break
            time.sleep(2.0)
    finally:
        if proc.poll() is None:  # only the tree this call started
            subprocess.run(['taskkill', '/T', '/F', '/PID', str(proc.pid)], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
    (out / 'native.log').write_text(text, encoding='utf-8')
    converted = []
    try:
        from PIL import Image
        for bmp in sorted(shots.glob('*.bmp')):
            png = bmp.with_suffix('.png')
            Image.open(bmp).save(png)
            converted.append(png.name)
    except Exception as error:  # Pillow missing: keep the BMPs
        converted.append(f'png conversion skipped: {error}')
    lines = [l for l in text.splitlines() if 'P2_UMIMUSHI' in l]
    (out / 'umimushi.log').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    summary = dict(package=str(package), exe=str(exe), seconds=seconds, probe=probe, autoplay=autoplay,
                   log_lines=len(text.splitlines()), umimushi_lines=len(lines), shots=converted)
    (out / 'run.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--package', required=True)
    parser.add_argument('--exe', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--seconds', type=float, default=150.0)
    parser.add_argument('--assets', default=DEFAULT_ASSETS)
    parser.add_argument('--no-probe', dest='probe', action='store_false', default=True)
    parser.add_argument('--autoplay', action='store_true', help='also run the headless bot (off by default)')
    parser.add_argument('--env', action='append', default=[], metavar='NAME=VALUE')
    args = parser.parse_args(argv)
    extra = dict(item.split('=', 1) for item in args.env)
    print(json.dumps(run(args.package, args.exe, args.out, args.seconds, args.assets, args.probe, args.autoplay,
                         extra), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
