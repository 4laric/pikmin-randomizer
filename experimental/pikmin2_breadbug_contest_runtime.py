"""Lane 18 small-Breadbug P2 cargo-contest consumer runtime (#220).

Builds the private fixture ``scripts/pikmin2_breadbug_contest_fixture.cpp``
against a completed native build and, in the coordinator's serialized real-GL
slot, runs it in a staged proxy arena, then validates the host log through
``experimental.pikmin2_breadbug_contest`` (the P2CargoContest marker parser and
four-gate validator) plus the run-level gates (live visual delegation and the
centred 960x540 window).

The primary tug is natural: the fixture runs ``probe_carriers(-1)`` so the real
Stickers count drives the P2CargoContest transition table, and the squad actually
out-pulls the Breadbug to reach the Stolen outcome (stolen-outcome release) and
the exactly-once grant. Only the revisit/death phases inject carrier counts via
the labelled ``pc_p2_breadbug_actor_probe_*`` hooks, and each injection is tagged
with a ``P2_BREADBUG_CONTEST_PROBE`` marker so the validator can prove the primary
tug had none. The P1 ``TEKI_Collec`` host still performs the actual pellet
grab/drag.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from experimental import pikmin2_breadbug_contest as contest
from scripts.test_pikmin2_surface_native import executable_identity

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / 'scripts/pikmin2_breadbug_contest_fixture.cpp'
WINDOW_LINE = 'Experimental preview window set to 960x540 windowed and centered'
GENERATOR = 186081

SCOPE = ('P1 TEKI_Collec proxy bound to P2CargoContest; natural Stickers tug '
         'reaches the Stolen outcome (stolen-outcome release) and grants exactly '
         'once; injected revisit/owner-death phases are probe-tagged; natural '
         'squad tug/carry ownership remains lane 04/06')


def validate(text, generator=GENERATOR):
    """Parse a host log through the contest-consumer validator plus run gates."""
    events = contest.parse_contest_consumer(text, generator)
    if not events['pass_marker']:
        raise ValueError('Missing PASS marker for the contest consumer run')
    result = contest.validate_contest_consumer(events)
    report = {
        'events': events,
        'gates': result['checks'],
        'passed': result['passed'],
        'live_visual': 'P2_BREADBUG_ACTOR_DRAW' in text,
        'standard_window': WINDOW_LINE in text,
        'scope': SCOPE,
    }
    if report['passed'] and not report['live_visual']:
        raise ValueError('Missing live Breadbug visual delegation')
    if report['passed'] and not report['standard_window']:
        raise ValueError('Missing 960x540 centred window evidence')
    return report


def build(native, build_dir, output, head):
    """Build the private contest fixture from an existing fresh native build."""
    from scripts import build_pikmin2_fixture as builder
    native, build_dir, output = native.resolve(), build_dir.resolve(), output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / 'fixture.cpp').write_text(FIXTURE.read_text())
    source = (native / 'tools/preview_p2_room.cpp').read_text()
    anchor = 'class RoomApp : public PlugPikiApp {'
    if source.count(anchor) != 1:
        raise ValueError('Room fixture prefix boundary changed')
    (output / 'room-prefix.inc').write_text(source[:source.index(anchor)])
    record = builder.build_fixture(build_dir, native, output / 'fixture.cpp', output / 'baseline', head)
    link = list(record['commands'][-1])
    link[builder.option_index(link, '-o')] = str(output / 'fixture.exe')
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''))
    code, text = builder.run_command(link, build_dir, env, output, 'fixture-link')
    (output / 'fixture-link.log').write_text(text)
    if code:
        raise RuntimeError('contest fixture link failed')
    return output / 'fixture.exe'


def run(stage_dir, exe, output, timeout=180):
    """Run a prebuilt contest fixture in an existing staged proxy arena."""
    stage_dir, output = Path(stage_dir).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, SDL_AUDIODRIVER='dummy', PIKMIN_P2_ROOM_WINDOW='960x540')
    env['PATH'] = 'C:/msys64/mingw64/bin;' + env.get('PATH', '')
    log = stage_dir / 'host.log'
    with log.open('w') as out:
        proc = subprocess.run([str(exe), '--experimental-pikmin2-room'], cwd=stage_dir,
                              env=env, stdout=out, stderr=subprocess.STDOUT, timeout=timeout)
    if proc.returncode:
        raise RuntimeError('Native contest consumer exited %d: %s' % (proc.returncode, stage_dir))
    report = {
        'executable': executable_identity(exe),
        'directory': str(stage_dir),
        'evidence': validate(log.read_text(errors='replace')),
        'scope': SCOPE,
    }
    (output / 'result.json').write_text(json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build', help='build the fixture from a fresh native build')
    for name in ('native', 'build-dir', 'output'):
        b.add_argument('--' + name, type=Path, required=True)
    b.add_argument('--head', required=True)
    r = sub.add_parser('run', help='run a prebuilt fixture in a staged arena')
    for name in ('stage', 'exe', 'output'):
        r.add_argument('--' + name, type=Path, required=True)
    r.add_argument('--timeout', type=int, default=180)
    v = sub.add_parser('validate', help='parse a captured host log')
    v.add_argument('--log', type=Path, required=True)
    args = parser.parse_args()
    for key, value in vars(args).items():
        if isinstance(value, Path):
            setattr(args, key, value.resolve())
    if args.command == 'build':
        if not re.fullmatch(r'[0-9a-f]{40}', args.head):
            parser.error('invalid --head')
        print(json.dumps({'fixture': str(build(args.native, args.build_dir, args.output, args.head))}))
    elif args.command == 'run':
        if not 1 <= args.timeout <= 300:
            parser.error('timeout must be 1..300')
        print(json.dumps(run(args.stage, args.exe, args.output, args.timeout)))
    else:
        print(json.dumps(validate(args.log.read_text(errors='replace'))))


if __name__ == '__main__':
    main()
