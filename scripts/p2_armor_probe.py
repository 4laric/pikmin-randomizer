"""Headless evidence run for the Cloaking Burrow-nit (Armor 15) skewer and shell rules (#1014).

Launches a smoke package (``scripts/p2_smoke_seed.py`` output) headless with the TEST-ONLY native probe
``PIKMIN_P2_ARMOR_PROBE=1`` (bait and decoy Pikmin around the body, eight Pikmin thrown through the real
``Navi::throwPiki`` at the shell and the head, a bomb and two punches) and ``PIKMIN_P2_PROXY_SHOT=<dir>``
(one BMP per key), then keeps native.log and the screenshots (converted to PNG when Pillow is available).

Capacity-gated; kills only the process tree it started (by PID); removes the asset links of its own
finished run. Never use this output as owner evidence of normal play: the probe moves Pikmin and the
captain. The owner package carries no probe.

Usage:
  py -3.12 scripts/p2_armor_probe.py --package output/smoke-armored-maw --exe <nectar.exe> --out <dir> --seconds 120
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
DONE_MARKERS = ('P2_ARMOR_PROBE kind=done',)
GATE = os.environ.get('PIKMIN_CAPACITY_GATE', str(ROOT / 'scripts' / 'capacity_gate.py'))


def remove_links(root: Path):
    """Delete directory links/junctions under this run's own session dir (never their targets)."""
    removed = []
    for path in root.rglob('*'):
        try:
            if path.is_symlink() or (os.name == 'nt' and path.is_dir() and os.path.isjunction(path)):
                os.rmdir(path) if path.is_dir() else os.unlink(path)
                removed.append(str(path))
        except OSError:
            pass
    return removed


def run(package, exe, out, seconds, assets, probe, extra_env):
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
        env['PIKMIN_P2_ARMOR_PROBE'] = '1'
    cmd = [sys.executable, '-m', 'randomizer', 'run', str(smoke), '--session-dir', str(session), '--exe', str(exe),
           '--assets', str(assets), '--p2-content', str(content), '--p2-actors', str(actors)]
    gate = subprocess.run([sys.executable, GATE, '--kind', 'game', '--jobs', '2', '--wait', '--timeout', '7200'])
    if gate.returncode != 0:
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
    lines = [l for l in text.splitlines() if 'P2_ARMOR' in l]
    (out / 'armor.log').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    links = remove_links(session)
    summary = dict(package=str(package), exe=str(exe), seconds=seconds, probe=probe, log_lines=len(text.splitlines()),
                   armor_lines=len(lines), shots=converted, links_removed=links)
    (out / 'run.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--package', required=True)
    parser.add_argument('--exe', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--seconds', type=float, default=120.0)
    parser.add_argument('--assets', default=DEFAULT_ASSETS)
    parser.add_argument('--no-probe', dest='probe', action='store_false', default=True)
    parser.add_argument('--env', action='append', default=[], metavar='NAME=VALUE')
    args = parser.parse_args(argv)
    extra = dict(item.split('=', 1) for item in args.env)
    print(json.dumps(run(args.package, args.exe, args.out, args.seconds, args.assets, args.probe, extra), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
