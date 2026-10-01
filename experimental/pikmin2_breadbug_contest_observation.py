"""Lane 18 small-Breadbug proxy contested-cargo observation (#168/#220).

Private runtime validator for the small PanModoki (source 38) P1 ``TEKI_Collec``
proxy arena. It stages the existing private proxy arena, feeds it one real red
number pellet (through the unchanged ``scripts/pikmin2_breadbug_cargo_fixture``)
and parses the native host log into the P1 cargo grab/drag/release timeline. It
then reports the two strength scales **separately**:

* ``native_offset_power`` / ``native_power`` -- the P1 ``TEKI_Collec`` host carry
  power (2, ``taicollec.cpp:509``) that actually drags the pellet.
* ``native_carriers`` -- the read-only Pikmin ``Stickers`` count the family-local
  ``pc_p2_breadbug_actor_tick`` observes on the P1 host's held cargo
  (``getCreaturePointer(2)``). It is reported next to the strength scales and is
  never treated as a P2 pull-channel result.
* ``source_strength`` -- the P2 ``PanModokiBase`` contest strength
  ``(pelletMin + pelletMax) / 2`` that would apply if the same pellet were
  contested through a P2 cargo channel.

The proxy runs **P1** semantics only: it owns no P2 pull channel, and
``getCreaturePointer(2)`` is P1 host state. Every observation sets
``p2_contest_semantics=False``; the P1 carry power is never presented as a P2
contest result. The true P2 contest is blocked on the lane 06/07 shared
cargo/lifetime surface (see ``docs/PIKMIN2_BREADBUG_ACTOR_RUNTIME.md``).

This module never mutates a save, an actor or shared physics state. The native
``pc_p2_breadbug_actor_tick`` hook is read-only introspection: it observes the P1
host's held-cargo pointer and ``Stickers`` carriers and logs a bounded
``P2_BREADBUG_CONTEST`` marker, without changing shared cargo/physics/contest
semantics.
"""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path

from experimental import pikmin2_breadbug_contest as contest

PROXY_CARRY_POWER = 2.0        # P1 TEKI_Collec host carry power (taicollec.cpp:509)
# The private fixture creates one red level-0 number pellet
# (``pelletMgr->newNumberPellet(PELCOLOR_Red, 0)``); its source carry bounds are
# 1..2, so its P2 contest strength is 1.5.
NUMBER_PELLET_MIN = 1
NUMBER_PELLET_MAX = 2

SCOPE = ('P1 Collec proxy observation; read-only native carrier introspection '
         'and native carry power reported separately from the source contest '
         'strength; no P2 pull channel or contest semantics claimed')

_BIRTH = re.compile(r'P2_BREADBUG_CARGO_BIRTH xyz=([-\d.]+),([-\d.]+),([-\d.]+) '
                    r'nest=([-\d.]+),([-\d.]+),([-\d.]+) distance=([\d.]+) min=(\d+)')
_RESULT = re.compile(r'P2_BREADBUG_CARGO_RESULT grabbed=(\d+) held_frames=(\d+) '
                     r'moved=([\d.]+) progress=([-\d.]+) released=(\d+) alive=(\d+)')
_TICK = re.compile(r'P2_BREADBUG_CARGO_TICK tick=(\d+) held=(\d+) state=(\d+) '
                   r'alive=(\d+) distance=([\d.]+) displacement=([\d.]+) held_frames=(\d+)')
# The family-local hook emits ``P2_BREADBUG_CONTEST generator=<id> native_power=2
# carriers=<n>``; the older observation-only marker also carries source_strength.
_CONTEST = re.compile(r'P2_BREADBUG_CONTEST(?: generator=(\d+))? native_power=([\d.]+)'
                      r'(?: carriers=(\d+))?(?: source_strength=([\d.]+))?')


def source_strength(pellet_min=NUMBER_PELLET_MIN, pellet_max=NUMBER_PELLET_MAX):
    """P2 ``PanModokiBase`` contest strength ``(min + max) / 2`` for the pellet."""
    return contest.carry_strength(pellet_min, pellet_max)


def native_marker(generator=0, carriers=0):
    """The bounded ``P2_BREADBUG_CONTEST`` line the family-local hook emits.

    ``pc_p2_breadbug_actor_tick`` logs this same shape when the P1 proxy's held
    state or ``Stickers`` carrier count changes. ``generator=0``/``carriers=0``
    build a neutral marker for tests and ``result.json``.
    """
    return ('P2_BREADBUG_CONTEST generator=%d native_power=%g carriers=%d'
            % (generator, PROXY_CARRY_POWER, carriers))


def observe(text, pellet_min=NUMBER_PELLET_MIN, pellet_max=NUMBER_PELLET_MAX):
    """Parse one native host log into the P1 cargo observation and strength split.

    Raises ``ValueError`` when the birth marker is missing/mismatched or the log
    does not contain exactly one completed P1 cargo result, so a successful
    process exit can never be mistaken for a completed observation. The returned
    mapping records ``native_offset_power`` (aliased ``native_power``),
    ``native_carriers`` and ``source_strength`` side by side with
    ``p2_contest_semantics=False``.
    """
    births = _BIRTH.findall(text)
    results = _RESULT.findall(text)
    if not births:
        raise ValueError('Missing native cargo birth marker')
    if len(results) != 1:
        raise ValueError('Expected one completed P1 cargo observation')
    observed_min = int(births[0][7])
    if observed_min != pellet_min:
        raise ValueError('Pellet min mismatch: native %d != expected %d'
                         % (observed_min, pellet_min))
    grabbed, held_frames, moved, progress, released, alive = results[0]
    grabbed, held_frames = bool(int(grabbed)), int(held_frames)
    moved, progress = float(moved), float(progress)
    released, alive = bool(int(released)), bool(int(alive))
    markers = _CONTEST.findall(text)
    if markers:
        generator, marked_power, marked_carriers, _marked_strength = markers[-1]
        native_power = float(marked_power)
        native_carriers = int(marked_carriers) if marked_carriers else None
        native_generator = int(generator) if generator else None
    else:
        native_power = PROXY_CARRY_POWER
        native_carriers = native_generator = None
    strength = source_strength(pellet_min, pellet_max)
    return {
        'pellet_bounds': {'min': pellet_min, 'max': pellet_max},
        'native_offset_power': native_power,
        'native_power': native_power,
        'native_carriers': native_carriers,
        'native_generator': native_generator,
        'source_strength': strength,
        'native_hook': bool(markers),
        'p2_contest_semantics': False,
        'grab_observed': grabbed,
        'drag_observed': grabbed and held_frames > 15 and moved > 10 and progress > 10,
        'release_observed': grabbed and released,
        'held_frames': held_frames,
        'displacement': moved,
        'nest_progress': progress,
        'pellet_alive': alive,
        'tick_samples': len(_TICK.findall(text)),
        'observed': grabbed and released,
    }


def stage(assets, profile, output):
    """Stage the private P1 proxy arena (one proxy + one control) into ``output``."""
    from experimental.pikmin2_breadbug_arena import prepare
    return prepare(assets, profile, output)


def run(assets, profile, exe, output, timeout=100):
    """Stage the arena, run a prebuilt fixture and write the observation report.

    The coordinator serializes real-GL runs; this helper is for that slot only.
    It parses the host log through :func:`observe` and writes ``result.json``.
    """
    from scripts.test_pikmin2_surface_native import executable_identity
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    stage_dir = stage(assets, profile, output)
    env = dict(os.environ, SDL_AUDIODRIVER='dummy', PIKMIN_P2_ROOM_WINDOW='960x540')
    env['PATH'] = 'C:/msys64/mingw64/bin;' + env.get('PATH', '')
    log = stage_dir / 'host.log'
    with log.open('w') as out:
        proc = subprocess.run([str(exe), '--experimental-pikmin2-room'], cwd=stage_dir,
                              env=env, stdout=out, stderr=subprocess.STDOUT, timeout=timeout)
    if proc.returncode:
        raise RuntimeError('Native observation exited %d: %s' % (proc.returncode, stage_dir))
    report = {
        'executable': executable_identity(exe),
        'directory': str(stage_dir),
        'evidence': observe(log.read_text(errors='replace')),
        'native_marker': native_marker(),
        'scope': SCOPE,
    }
    (output / 'result.json').write_text(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'profile', 'exe', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--timeout', type=int, default=100)
    args = parser.parse_args()
    for key, value in vars(args).items():
        if isinstance(value, Path):
            setattr(args, key, value.resolve())
    if not 1 <= args.timeout <= 180:
        parser.error('timeout must be 1..180')
    print(json.dumps(run(args.assets, args.profile, args.exe, args.output,
                         timeout=args.timeout)))
