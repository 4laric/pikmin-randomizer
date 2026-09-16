"""Muse l64 Breadbug38 natural death/corpse + cleanup/re-entry observer (#504).

Scope: PanModoki source 38 only (P1 TEKI_Collec proxy 186081, control 186082
untouched). This module stages a private proxy arena WITHOUT a bait pellet,
builds/runs ``native/tools/p2_muse_breadbug_fixture.cpp`` and validates the
host log for:

- autonomous P1-proxy movement sampling (displacement + native-velocity
  frames; P2 FSM motion is absent and is never claimed),
- a natural squad kill: free-mode reds ringed around the actor, health falls
  through the real receiver path with zero fixture health writes and no
  ``die()`` call (any ``P2_MUSE_BREADBUG_INJECTED`` marker fails the gate),
- death-funnel cleanup: the family ``P2_BREADBUG_ACTOR_FORGET`` marker with
  ``dead_state>=1`` (BTeki::doKill -> pc_p2_forget_teki, not slot reuse),
- corpse: live pellet(s) bound to the dead actor (``mPellet`` at
  ``mDeadState==2`` plus the pelletMgr ``mPelletView`` scan),
- re-entry: a ``P2_BREADBUG_ACTOR_REBIRTH`` registration from the per-tick
  rebirth scan with exactly one ``READY`` in the whole log (no manager
  recreation, no forced release, no second setup).

Accepted lane-18 ownership/cargo-contest behavior is preserved and
re-cited, never re-implemented here.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = Path('native/tools/p2_muse_breadbug_fixture.cpp')
WINDOW_LINE = 'Experimental preview window set to 960x540 windowed and centered'
GENERATOR = 186081
CONTROL = 186082

SCOPE = ('Breadbug38 natural lifecycle: P1-proxy movement sample, natural '
         'free-mode squad kill, death-funnel forget, corpse pellet, generator '
         'rebirth re-registration without manager recreation; P2 FSM motion, '
         'cargo contest and transport reward are lane-18 accepted behavior '
         'preserved by reference, not re-claimed here')

# Movement acceptance mirrors the retired proxy fixture: >15 units horizontal
# displacement and >=15 frames of native horizontal velocity.
MOVE_DISPLACEMENT_MIN = 15.0
MOVE_FRAMES_MIN = 15

_PATTERNS = {
    'ready': re.compile(r'^P2_BREADBUG_ACTOR_READY generator=(\d+) native_type=(\d+) xyz=([-\d.,]+)'),
    'forget': re.compile(r'^P2_BREADBUG_ACTOR_FORGET generator=(\d+) had_handle=(\d+) dead_state=(\d+)'),
    'death': re.compile(r'^P2_BREADBUG_ACTOR_DEATH generator=(\d+) corpse=(\d+) held=(\d+)'),
    'rebirth': re.compile(r'^P2_BREADBUG_ACTOR_REBIRTH generator=(\d+) native_type=(\d+) replaced_stale=(\d+)'),
    'move': re.compile(r'^P2_MUSE_BREADBUG_MOVE frame=(\d+) displacement=([-\d.eE+]+) moving=(\d+)'),
    'ring': re.compile(r'^P2_MUSE_BREADBUG_RING tick=(\d+) reds=(\d+) health=([-\d.eE+]+)'),
    'kill': re.compile(r'^P2_MUSE_BREADBUG_KILL_NATURAL tick=(\d+)'),
    'corpse': re.compile(r'^P2_MUSE_BREADBUG_CORPSE bodies=(\d+) via_mpellet=(\d+)'),
    'rebirth_begin': re.compile(r'^P2_MUSE_BREADBUG_REBIRTH_BEGIN generator=(\d+)'),
    'rebirth_new': re.compile(r'^P2_MUSE_BREADBUG_REBIRTH_NEW recycled=(\d+)'),
    'injected': re.compile(r'^P2_MUSE_BREADBUG_INJECTED (\S.*)$'),
    'draw': re.compile(r'^P2_BREADBUG_ACTOR_DRAW generator=(\d+)'),
    'pass': re.compile(r'^PASS P2_MUSE_BREADBUG\b'),
}


def parse_muse_breadbug(text, generator=GENERATOR):
    """Parse a host log into lifecycle events for one generator id."""
    events = {
        'ready': [], 'forget': [], 'death': [], 'rebirth': [],
        'moves': [], 'rings': [], 'kill': None, 'corpse': None,
        'rebirth_begin': None, 'rebirth_new': None, 'injected': [],
        'draw': False, 'window': WINDOW_LINE in text, 'pass_marker': False,
    }
    for lineno, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        m = _PATTERNS['ready'].match(line)
        if m and int(m.group(1)) == generator:
            events['ready'].append({'line': lineno, 'native_type': int(m.group(2)), 'xyz': m.group(3)})
            continue
        m = _PATTERNS['forget'].match(line)
        if m and int(m.group(1)) == generator:
            events['forget'].append({'line': lineno, 'had_handle': int(m.group(2)), 'dead_state': int(m.group(3))})
            continue
        m = _PATTERNS['death'].match(line)
        if m and int(m.group(1)) == generator:
            events['death'].append({'line': lineno, 'corpse': int(m.group(2)), 'held': int(m.group(3))})
            continue
        m = _PATTERNS['rebirth'].match(line)
        if m and int(m.group(1)) == generator:
            events['rebirth'].append({'line': lineno, 'native_type': int(m.group(2)),
                                      'replaced_stale': int(m.group(3))})
            continue
        m = _PATTERNS['move'].match(line)
        if m:
            events['moves'].append({'line': lineno, 'frame': int(m.group(1)),
                                    'displacement': float(m.group(2)), 'moving': int(m.group(3))})
            continue
        m = _PATTERNS['ring'].match(line)
        if m:
            events['rings'].append({'line': lineno, 'tick': int(m.group(1)),
                                    'reds': int(m.group(2)), 'health': float(m.group(3))})
            continue
        m = _PATTERNS['kill'].match(line)
        if m and events['kill'] is None:
            events['kill'] = {'line': lineno, 'tick': int(m.group(1))}
            continue
        m = _PATTERNS['corpse'].match(line)
        if m and events['corpse'] is None:
            events['corpse'] = {'line': lineno, 'bodies': int(m.group(1)), 'via_mpellet': int(m.group(2))}
            continue
        m = _PATTERNS['rebirth_begin'].match(line)
        if m and int(m.group(1)) == generator and events['rebirth_begin'] is None:
            events['rebirth_begin'] = {'line': lineno}
            continue
        m = _PATTERNS['rebirth_new'].match(line)
        if m and events['rebirth_new'] is None:
            events['rebirth_new'] = {'line': lineno, 'recycled': int(m.group(1))}
            continue
        m = _PATTERNS['injected'].match(line)
        if m:
            events['injected'].append({'line': lineno, 'detail': m.group(1)})
            continue
        if _PATTERNS['draw'].match(line):
            events['draw'] = True
            continue
        if _PATTERNS['pass'].match(line):
            events['pass_marker'] = True
    return events


def validate_muse_breadbug(events):
    """Check the six lifecycle gates. Every failure names its exact cause."""
    checks = {}
    reasons = []

    moves = events['moves']
    best = max([m['displacement'] for m in moves], default=0.0)
    moving = max([m['moving'] for m in moves], default=0)
    checks['movement_sample'] = bool(moves) and best > MOVE_DISPLACEMENT_MIN and moving >= MOVE_FRAMES_MIN
    if not checks['movement_sample']:
        reasons.append('movement: displacement=%.2f moving=%d, need >%.0f and >=%d (P1 proxy only)' % (
            best, moving, MOVE_DISPLACEMENT_MIN, MOVE_FRAMES_MIN))

    rings = events['rings']
    health_fell = any(b['health'] < a['health'] for a, b in zip(rings, rings[1:]))
    checks['natural_kill'] = (events['kill'] is not None and not events['injected']
                              and len(rings) >= 2 and health_fell
                              and all(r['reds'] > 0 for r in rings))
    if not checks['natural_kill']:
        reasons.append('natural_kill: kill=%s injected=%d rings=%d health_fell=%s' % (
            events['kill'] is not None, len(events['injected']), len(rings), health_fell))

    funnel = [f for f in events['forget'] if f['dead_state'] >= 1]
    checks['death_funnel'] = bool(funnel)
    if not checks['death_funnel']:
        reasons.append('death_funnel: no FORGET with dead_state>=1 (forget=%d)' % len(events['forget']))

    corpse = events['corpse']
    checks['corpse'] = corpse is not None and corpse['bodies'] >= 1 and corpse['via_mpellet'] == 1
    if not checks['corpse']:
        reasons.append('corpse: %s (need bodies>=1 via mPellet at mDeadState==2)' % (corpse,))

    rebirths = events['rebirth']
    checks['rebirth'] = (len(rebirths) == 1 and rebirths[0]['replaced_stale'] == 0
                         and len(events['ready']) == 1 and events['rebirth_begin'] is not None
                         and events['rebirth_new'] is not None)
    if not checks['rebirth']:
        reasons.append('rebirth: rebirths=%d ready=%d begin=%s new=%s (need exactly one '
                       'REBIRTH with replaced_stale=0 and a single READY: no manager recreation)' % (
                           len(rebirths), len(events['ready']),
                           events['rebirth_begin'] is not None, events['rebirth_new'] is not None))

    checks['single_death'] = events['kill'] is not None and len(events['death']) <= 1
    if not checks['single_death']:
        reasons.append('single_death: kill=%s death_markers=%d' % (
            events['kill'] is not None, len(events['death'])))

    passed = all(checks.values())
    return {'checks': checks, 'passed': passed, 'reasons': reasons}


def validate(text, generator=GENERATOR):
    """Parse a host log plus run-level gates (window, live visual, PASS)."""
    events = parse_muse_breadbug(text, generator)
    if not events['pass_marker']:
        raise ValueError('Missing PASS marker for the muse breadbug run')
    result = validate_muse_breadbug(events)
    report = {
        'events': events,
        'gates': result['checks'],
        'reasons': result['reasons'],
        'passed': result['passed'],
        'live_visual': events['draw'],
        'standard_window': events['window'],
        'scope': SCOPE,
    }
    if result['passed'] and not events['draw']:
        raise ValueError('Missing live Breadbug visual delegation')
    if result['passed'] and not events['window']:
        raise ValueError('Missing 960x540 centred window evidence')
    return report


def stage(assets, profile, output):
    """Stage a fresh proxy arena (no bait pellet) into a new directory."""
    from experimental import pikmin2_breadbug_arena as arena
    from experimental.pikmin2_breadbug_actor import install
    assets, profile, output = Path(assets).resolve(), Path(profile).resolve(), Path(output).resolve()
    run = arena.prepare(assets, profile, output)
    install(profile, run, [GENERATOR])
    return run


def build(native, build_dir, output, head):
    """Build the private muse breadbug fixture from a fresh native build."""
    import re as _re
    from scripts import build_pikmin2_fixture as builder
    from scripts.test_pikmin2_surface_native import executable_identity  # noqa: F401 (re-exported for run())
    native, build_dir, output = Path(native).resolve(), Path(build_dir).resolve(), Path(output).resolve()
    if not _re.fullmatch(r'[0-9a-f]{40}', head):
        raise ValueError('invalid --head')
    fixture_src = (ROOT / FIXTURE)
    if not fixture_src.is_file():
        raise ValueError('missing fixture source: %s' % FIXTURE)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'fixture.cpp').write_text(fixture_src.read_text())
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
        raise RuntimeError('muse breadbug fixture link failed')
    return output / 'fixture.exe'


def run(stage_dir, exe, output, timeout=300):
    """Run a prebuilt muse breadbug fixture in a staged arena."""
    from scripts.test_pikmin2_surface_native import executable_identity
    stage_dir, output = Path(stage_dir).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, SDL_AUDIODRIVER='dummy', PIKMIN_P2_ROOM_WINDOW='960x540')
    env['PATH'] = 'C:/msys64/mingw64/bin;' + env.get('PATH', '')
    log = stage_dir / 'host.log'
    with log.open('w') as out:
        proc = subprocess.run([str(exe), '--experimental-pikmin2-room'], cwd=stage_dir,
                              env=env, stdout=out, stderr=subprocess.STDOUT, timeout=timeout)
    shutil.copy2(log, output / 'host.log')
    if proc.returncode:
        raise RuntimeError('Native muse breadbug fixture exited %d: %s' % (proc.returncode, stage_dir))
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
    s = sub.add_parser('stage', help='stage a fresh proxy arena')
    for name in ('assets', 'profile', 'output'):
        s.add_argument('--' + name, type=Path, required=True)
    b = sub.add_parser('build', help='build the fixture from a fresh native build')
    for name in ('native', 'build-dir', 'output'):
        b.add_argument('--' + name, type=Path, required=True)
    b.add_argument('--head', required=True)
    r = sub.add_parser('run', help='run a prebuilt fixture in a staged arena')
    for name in ('stage', 'exe', 'output'):
        r.add_argument('--' + name, type=Path, required=True)
    r.add_argument('--timeout', type=int, default=300)
    v = sub.add_parser('validate', help='parse a captured host log')
    v.add_argument('--log', type=Path, required=True)
    args = parser.parse_args()
    for key, value in vars(args).items():
        if isinstance(value, Path):
            setattr(args, key, value.resolve())
    if args.command == 'stage':
        print(json.dumps({'stage': str(stage(args.assets, args.profile, args.output))}))
    elif args.command == 'build':
        print(json.dumps({'fixture': str(build(args.native, args.build_dir, args.output, args.head))}))
    elif args.command == 'run':
        if not 1 <= args.timeout <= 300:
            parser.error('timeout must be 1..300')
        print(json.dumps(run(args.stage, args.exe, args.output, args.timeout)))
    else:
        print(json.dumps(validate(args.log.read_text(errors='replace'))))


if __name__ == '__main__':
    main()
