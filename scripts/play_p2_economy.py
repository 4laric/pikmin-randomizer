"""Launch the ordinary seed/session runner with its private verified catalog.

Use the existing explicit White/Purple/diamond banks and native day SAVE flow.
This wrapper changes no session/card or assets; only the catalog input path.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experimental.pikmin2_treasure_catalog import verify_native_catalog


def launch_command(catalog, runner_args):
    catalog = verify_native_catalog(catalog)
    if not runner_args:
        raise ValueError('Ordinary randomizer run arguments required')
    env = os.environ.copy()
    env['PIKMIN_P2_TREASURE_CATALOG'] = str(catalog)
    env['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    return [sys.executable, '-m', 'randomizer', 'run', *runner_args], env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('runner_args', nargs=argparse.REMAINDER,
                        help='After --: existing randomizer run manifest/session/exe/bank options')
    args = parser.parse_args()
    runner_args = args.runner_args[1:] if args.runner_args[:1] == ['--'] else args.runner_args
    command, env = launch_command(args.catalog, runner_args)
    return subprocess.call(command, env=env, cwd=ROOT)


if __name__ == '__main__': raise SystemExit(main())
