"""Runnable private small-Breadbug proxy cargo arena (#168/#220).

Wraps the already-committed private fixture
``scripts/pikmin2_breadbug_cargo_fixture.cpp`` into a build/run/validate path on
the maintained line. The fixture stages the small PanModoki (source 38) P1
``TEKI_Collec`` proxy arena (``experimental.pikmin2_breadbug_arena``), drops one
real red level-0 number pellet 100 units ahead of the actor's native facing, and
lets ordinary P1 AI grab, drag and release it. No grab/carry/state/velocity write
is injected; only the fixture captain is moved for camera framing.

The host log is parsed through
``experimental.pikmin2_breadbug_contest_observation``. That module owns the
strength split: ``native_offset_power`` is the P1 host carry power (2.0) that
actually drags the pellet, while ``source_strength`` is the P2 ``PanModokiBase``
contest strength ``(min + max) / 2`` (1.5 for the red 1..2 pellet). This runner
never merges the two and always records ``p2_contest_semantics=False``: the P1
proxy owns no P2 pull channel or carriers.

``build`` reuses ``scripts.build_pikmin2_fixture`` and a prebuilt fresh native
build; it never rebuilds production. ``run`` is for the coordinator's serialized
real-GL slot only. ``validate`` is pure and testable against captured logs.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from experimental import pikmin2_breadbug_contest_observation as observation
from scripts import build_pikmin2_fixture as builder
from scripts.test_pikmin2_surface_native import executable_identity

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / 'scripts/pikmin2_breadbug_cargo_fixture.cpp'
PREFIX = None  # Derive from the pinned native source unless explicitly supplied.
WINDOW_LINE = 'Experimental preview window set to 960x540 windowed and centered'

SCOPE = ('P1 TEKI_Collec proxy cargo observation; the proxy owns no P2 pull '
         'channel or carriers; native carry power and source contest strength '
         'are reported separately; no P2 contest semantics claimed')


def fixture_source():
    """The committed private fixture source this runner builds unchanged."""
    return FIXTURE.read_text()


def validate(text, pellet_min=observation.NUMBER_PELLET_MIN,
             pellet_max=observation.NUMBER_PELLET_MAX):
    """Parse a host log via the contest observation plus the arena gates.

    Delegates the birth/result/strength parsing to
    :func:`experimental.pikmin2_breadbug_contest_observation.observe`, then adds
    the two run-level gates (live visual delegation and the standard centred
    960x540 window). Structural errors (missing/duplicated/mismatched markers)
    propagate from the observation module. A completed process that never
    grabbed or released is reported ``complete=False`` rather than accepted.
    """
    report = observation.observe(text, pellet_min, pellet_max)
    report['live_visual'] = 'P2_BREADBUG_ACTOR_DRAW' in text
    report['standard_window'] = WINDOW_LINE in text
    if not report['live_visual']:
        raise ValueError('Missing live Breadbug visual')
    if not report['standard_window']:
        raise ValueError('Missing 960x540 centred window evidence')
    report['scope'] = SCOPE
    report['complete'] = bool(report['observed'] and report['live_visual']
                              and report['standard_window'])
    return report


def build(native, build_dir, output, head, prefix=PREFIX):
    """Build the private cargo fixture from an existing fresh native build.

    Copies the committed fixture and ``room-prefix.inc`` into ``output`` and
    delegates compilation, provenance and the freshness checks to
    ``scripts.build_pikmin2_fixture``. Returns ``(exe, identity)``.
    """
    native, build_dir, output = native.resolve(), build_dir.resolve(), output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    fixture = output / 'fixture.cpp'
    fixture.write_text(fixture_source())
    if prefix is None:
        source = (native / 'tools/preview_p2_room.cpp').read_text()
        anchor = 'class RoomApp : public PlugPikiApp {'
        if source.count(anchor) != 1:
            raise ValueError('Room fixture prefix boundary changed')
        (output / 'room-prefix.inc').write_text(source[:source.index(anchor)])
    else:
        shutil.copy2(prefix, output / 'room-prefix.inc')
    record = builder.build_fixture(build_dir, native, fixture, output / 'baseline', head)
    link = list(record['commands'][-1])
    link[builder.option_index(link, '-o')] = str(output / 'fixture.exe')
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''))
    code, text = builder.run_command(link, build_dir, env, output, 'fixture-link')
    (output / 'fixture-link.log').write_text(text)
    if code:
        raise RuntimeError('fixture link failed')
    return output / 'fixture.exe', builder.snapshot([output / 'fixture.exe'])


def run(assets, profile, exe, output, timeout=120):
    """Stage the proxy arena, run a prebuilt fixture and write ``result.json``.

    The coordinator serializes real-GL runs; this helper is for that slot only.
    """
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    stage_dir = observation.stage(assets, profile, output)
    env = dict(os.environ, SDL_AUDIODRIVER='dummy', PIKMIN_P2_ROOM_WINDOW='960x540')
    env['PATH'] = 'C:/msys64/mingw64/bin;' + env.get('PATH', '')
    log = stage_dir / 'host.log'
    with log.open('w') as out:
        proc = subprocess.run([str(exe), '--experimental-pikmin2-room'], cwd=stage_dir,
                              env=env, stdout=out, stderr=subprocess.STDOUT, timeout=timeout)
    if proc.returncode:
        raise RuntimeError('Native proxy cargo observation exited %d: %s'
                           % (proc.returncode, stage_dir))
    report = {
        'executable': executable_identity(exe),
        'directory': str(stage_dir),
        'evidence': validate(log.read_text(errors='replace')),
        'native_marker': observation.native_marker(),
        'scope': SCOPE,
    }
    (output / 'result.json').write_text(json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    build_parser = sub.add_parser('build', help='build the fixture from a fresh native build')
    for name in ('native', 'build-dir', 'output'):
        build_parser.add_argument('--' + name, type=Path, required=True)
    build_parser.add_argument('--head', required=True)
    build_parser.add_argument('--prefix', type=Path, default=PREFIX)
    run_parser = sub.add_parser('run', help='stage the arena and run a prebuilt fixture')
    for name in ('assets', 'profile', 'exe', 'output'):
        run_parser.add_argument('--' + name, type=Path, required=True)
    run_parser.add_argument('--timeout', type=int, default=120)
    validate_parser = sub.add_parser('validate', help='parse a captured host log')
    validate_parser.add_argument('--log', type=Path, required=True)
    args = parser.parse_args()
    for key, value in vars(args).items():
        if isinstance(value, Path):
            setattr(args, key, value.resolve())
    if args.command == 'build':
        if not re.fullmatch(r'[0-9a-f]{40}', args.head):
            parser.error('invalid --head')
        exe, identity = build(args.native, args.build_dir, args.output, args.head, args.prefix)
        print(json.dumps({'fixture': str(exe), 'identity': identity}))
    elif args.command == 'run':
        if not 1 <= args.timeout <= 180:
            parser.error('timeout must be 1..180')
        print(json.dumps(run(args.assets, args.profile, args.exe, args.output, args.timeout)))
    else:
        print(json.dumps(validate(args.log.read_text(errors='replace'))))


if __name__ == '__main__':
    main()
