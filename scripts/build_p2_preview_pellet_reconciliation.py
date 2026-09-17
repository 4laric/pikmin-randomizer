"""Build the preview pellet-reconciliation fixture against a private build (#679).

Thin wrapper over scripts/build_pikmin2_fixture.py: links
native/tools/p2_preview_pellet_reconciliation_fixture.cpp against the private
pikmin_pc graph without editing shared build files, then runs the
engine-independent guard self-test and negative test.

Never rebuilds production. Private output must stay outside the native source
and the production build directory.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import build_pikmin2_fixture as base


FIXTURE_REL = Path('tools/p2_preview_pellet_reconciliation_fixture.cpp')


def fixture_env(build):
    env = dict(os.environ)
    path = env.get('Path', env.get('PATH', ''))
    extra = os.pathsep.join((r'C:\msys64\mingw64\bin', str(Path(build) / 'bin')))
    env['Path'] = extra + os.pathsep + path if path else extra
    return env


def run_guard_checks(exe, build):
    exe = Path(exe)
    env = fixture_env(build)
    selftest = subprocess.run([str(exe), '--guard-self-test'], capture_output=True,
                              text=True, timeout=60, env=env)
    if selftest.returncode != 0 or 'P2_PELLET_RECONCILIATION_SELFTEST_PASS' not in selftest.stdout:
        raise SystemExit('guard self-test failed:\n' + selftest.stdout + selftest.stderr)
    negative = subprocess.run([str(exe), '--guard-negative-test'], capture_output=True,
                              text=True, timeout=60, env=env)
    if negative.returncode != 86 or 'P2_FIXTURE_CAPTAIN_DOWN' not in negative.stdout:
        raise SystemExit('guard negative test failed:\n' + negative.stdout + negative.stderr)
    if 'PASS' in negative.stdout.split('P2_FIXTURE_CAPTAIN_DOWN', 1)[0]:
        raise SystemExit('guard negative test emitted PASS before interruption')
    return {'selftest': selftest.stdout.strip().splitlines()[-1],
            'negative_exit': negative.returncode}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-native-head', required=True)
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--skip-guard-checks', action='store_true')
    args = parser.parse_args()
    fixture = (args.source / FIXTURE_REL)
    result = base.build_fixture(args.build, args.source, fixture, args.output,
                                args.expected_native_head, args.check_only)
    checks = {}
    if result.get('status') == 'built' and not args.check_only and not args.skip_guard_checks:
        checks = run_guard_checks(Path(args.output).resolve() / 'fixture.exe', args.build)
    print(json.dumps(dict(status=result['status'],
                          output=str(args.output.resolve()), **checks)))


if __name__ == '__main__':
    main()
