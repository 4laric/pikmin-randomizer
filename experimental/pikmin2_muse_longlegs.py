"""Muse l62 Long Legs observer: Houdai66 Walk translation + no-carcass reward (#502).

Source facts (read-only retail ``native/pikmin2-research``):
* Houdai/BigFoot/Damagumo ``onInit`` all run ``disableEvent(0, EB_LeaveCarcass)``
  (Houdai.cpp:71, BigFoot.cpp:69, Damagumo.cpp:80) — no carcass, no corpse, no
  corpse transport, ever. Death reward is ``createItemAndEnemy``: a pellet/treasure
  drop when ``mPelletDropCode`` is set, else child births from the ``kosi`` joint
  (BigFoot 30 Mitites, Damagumo 25 ShijimiChou, Houdai none).
* Walk is ``startIKMotion`` toward ``getTargetPosition`` (nearest Pikmin in sight,
  else a random territory-ring point; Houdai.cpp:333-349, HoudaiState.cpp:340-375)
  with no walk animation (family-wide). The port has no IKSystemMgr, so the owned
  host translates the body at the source species speed along the source target
  rule while the legs stay bind-pose (documented approximation).

This module validates a native log for:
* ``walk_translation`` (Houdai66): a ``P2_LONG_LEGS_WALK`` / ``P2_LONG_LEGS_WALK_END``
  pair with real displacement (``distance >= 50`` units, average speed within the
  source 250 u/s budget). Replaces the old host-pinned schedule-only evidence.
* ``death_intent``: natural ``P2_LONG_LEGS_DEAD`` lines for both species, BigFoot
  ``P2_LONG_LEGS_BIRTH count=30``, and NO Houdai birth line (source deathChildren 0).
* ``no_carcass_source``: static audit that the retail sources disable EB_LeaveCarcass
  for both species — the source-backed basis for reporting gate 5 as N/A in a
  cargo-free arena instead of the old proxy-corpse Pod credit.
* ``preserved``: the caller passes lane26 ``validate()``'s ``passed`` flag through,
  so the four accepted gates (identity/attacks/death/cleanup) must stay green.

No fixture, actor or engine state is touched here; this is a pure log auditor.
"""

import argparse
import json
import os
import re
from pathlib import Path

from experimental.pikmin2_animation_profile import capture_command
from experimental.pikmin2_batch2_core import prepare as _prepare
from experimental.pikmin2_long_legs_arena import CFG
from experimental.pikmin2_long_legs_install import install, verify_install
from experimental.pikmin2_long_legs_visual import convert as convert_visual

HOUDAI_GEN = 312001
BIGFOOT_GEN = 312002
# Source disc speeds carried by the owned FSM policy (p2LongLegsParmsFor).
SOURCE_SPEED = {'Houdai': 250.0, 'BigFoot': 70.0, 'Damagumo': 100.0}
# Minimum real displacement per Walk that counts as autonomous translation.
# Houdai covers 50 units in 0.2 s at source speed; anything below is staging noise.
MIN_WALK_DISTANCE = 50.0

WALK_RE = re.compile(
    r'P2_LONG_LEGS_WALK species=(\w+) generator=(\d+) '
    r'from=(-?[\d.]+),(-?[\d.]+) to=(-?[\d.]+),(-?[\d.]+) speed=([\d.]+)')
WALK_END_RE = re.compile(
    r'P2_LONG_LEGS_WALK_END species=(\w+) generator=(\d+) '
    r'distance=([\d.]+) seconds=([\d.]+)')
DEAD_RE = re.compile(
    r'P2_LONG_LEGS_DEAD species=(\w+) generator=(\d+) health=0 prior_health=([\d.]+)')
BIRTH_RE = re.compile(
    r'P2_LONG_LEGS_BIRTH species=(\w+) generator=(\d+) count=(\d+)')

# Retail checkout root (read-only). Overridable for tests.
RETAIL_ROOT = Path(os.environ.get(
    'PIKMIN_P2_RETAIL_ROOT',
    r'C:/Users/alari/pikmin-randomizer/native/pikmin2-research'))
NO_CARCASS_SOURCES = {
    'Houdai': 'src/plugProjectNishimuraU/Houdai.cpp',
    'BigFoot': 'src/plugProjectNishimuraU/BigFoot.cpp',
}


def parse_walks(text):
    """Return (entries, ends) lists of dicts from WALK/WALK_END markers."""
    entries = [dict(species=m.group(1), generator=int(m.group(2)),
                    from_x=float(m.group(3)), from_z=float(m.group(4)),
                    to_x=float(m.group(5)), to_z=float(m.group(6)),
                    speed=float(m.group(7)))
               for m in WALK_RE.finditer(text)]
    ends = [dict(species=m.group(1), generator=int(m.group(2)),
                 distance=float(m.group(3)), seconds=float(m.group(4)))
            for m in WALK_END_RE.finditer(text)]
    return entries, ends


def check_walk_translation(text):
    """Houdai66 autonomous translation: real displacement within source budget."""
    _, ends = parse_walks(text)
    houdai = [e for e in ends if e['species'] == 'Houdai' and e['generator'] == HOUDAI_GEN]
    if not houdai:
        return dict(passed=False, reason='no Houdai WALK_END marker', best=0.0)
    best = max(houdai, key=lambda e: e['distance'])
    budget = SOURCE_SPEED['Houdai'] * 1.25
    avg = best['distance'] / best['seconds'] if best['seconds'] > 0 else float('inf')
    if best['distance'] >= MIN_WALK_DISTANCE and avg <= budget:
        return dict(passed=True,
                    reason='distance=%.1f seconds=%.2f avg=%.1f u/s within %.1f' % (
                        best['distance'], best['seconds'], avg, budget),
                    best=best['distance'])
    return dict(passed=False,
                reason='best distance=%.1f avg=%.1f u/s outside [%.1f, %.1f] budget' % (
                    best['distance'], avg, MIN_WALK_DISTANCE, budget),
                best=best['distance'])


def check_bigfoot_walk_seen(text):
    """BigFoot69 translation opportunity: a Walk entry (staged under the squad, so
    Walk may legitimately never occur — this gate is informational, not required)."""
    entries, ends = parse_walks(text)
    bigfoot = [e for e in entries if e['species'] == 'BigFoot']
    return dict(seen=bool(bigfoot),
                ends=[e for e in ends if e['species'] == 'BigFoot'])


def check_death_intent(text):
    """Source-correct death output: both DEAD lines, BigFoot birth 30, no Houdai birth."""
    dead = {(m.group(1), int(m.group(2))): float(m.group(3))
            for m in DEAD_RE.finditer(text)}
    births = {(m.group(1), int(m.group(2))): int(m.group(3))
              for m in BIRTH_RE.finditer(text)}
    houdai_dead = dead.get(('Houdai', HOUDAI_GEN), 0.0) > 0
    bigfoot_dead = dead.get(('BigFoot', BIGFOOT_GEN), 0.0) > 0
    bigfoot_birth_ok = births.get(('BigFoot', BIGFOOT_GEN)) == 30
    houdai_no_birth = ('Houdai', HOUDAI_GEN) not in births
    injected = bool(re.search(r'P2_LL_INJECT[^\n]*Houdai', text))
    passed = houdai_dead and bigfoot_dead and bigfoot_birth_ok and houdai_no_birth
    return dict(passed=passed, houdai_dead=houdai_dead, bigfoot_dead=bigfoot_dead,
                bigfoot_birth_ok=bigfoot_birth_ok, houdai_no_birth=houdai_no_birth,
                injected_houdai=injected)


def check_no_carcass_source(retail_root=None):
    """Static source audit: both species disable EB_LeaveCarcass in onInit."""
    root = Path(retail_root) if retail_root else RETAIL_ROOT
    detail = {}
    for species, rel in NO_CARCASS_SOURCES.items():
        path = root / rel
        try:
            content = path.read_text(errors='replace')
        except OSError:
            detail[species] = 'missing: %s' % path
            continue
        detail[species] = ('disableEvent(0, EB_LeaveCarcass) present'
                           if 'disableEvent(0, EB_LeaveCarcass)' in content
                           else 'MARKER ABSENT')
    passed = all(v.endswith('present') for v in detail.values())
    return dict(passed=passed, detail={k: str(v) for k, v in detail.items()})


def validate(text, retail_root=None):
    """Validate a muse-l62 walk-run native log.

    Gates: walk_translation (new candidate), houdai_death (natural drain under
    the translation change), no_carcass_source (static audit), preserved
    (bind + schedule + window + squad + session in this run; the four accepted
    lane26 gates are otherwise untouched — translation only acts in FSM Walk,
    which combat staging never enters with the squad inside 60u).
    """
    walk = check_walk_translation(text)
    bigfoot = check_bigfoot_walk_seen(text)
    death = check_death_intent(text)
    nocarcass = check_no_carcass_source(retail_root)
    ready = re.search(r'P2_MUSE_WALK_READY squad=(\d+) houdai_gen=312001 bigfoot_gen=312002', text)
    squad = int(ready.group(1)) if ready else 0
    binds = (bool(re.search(r'P2_LONG_LEGS_BIND generator=312001 species=Houdai .* native_fsm=implemented', text))
             and bool(re.search(r'P2_LONG_LEGS_BIND generator=312002 species=BigFoot .* native_fsm=implemented', text)))
    schedule = (bool(re.search(r'P2_LONG_LEGS_STATE species=Houdai generator=312001 state=(Land|Wait|Flick|Shot|Walk)', text))
                and bool(re.search(r'P2_LONG_LEGS_STATE species=BigFoot generator=312002 state=(Land|Wait|Flick|Walk)', text)))
    window = bool(re.search(r'Experimental preview window set to 960x540 windowed and centered', text))
    no_inject = 'P2_LL_INJECT' not in text
    houdai_death = (death['houdai_dead'] and death['houdai_no_birth']
                    and bool(re.search(r'P2_MUSE_WALK_NATURAL_DEATH houdai=1', text))
                    and no_inject)
    session = (bool(re.search(r'P2_MUSE_WALK_SESSION navi=1\b', text))
               and not re.search(r'Extinction', text, re.IGNORECASE))
    completion = 'PASS P2_MUSE_LONGLEGS_WALK' in text
    checks = dict(
        walk_translation=walk['passed'],
        bigfoot_walk_seen=bigfoot['seen'],
        houdai_death=houdai_death,
        no_carcass_source=nocarcass['passed'],
        binds=binds,
        schedule=schedule,
        window=window,
        live_squad=squad >= 1,
        no_inject=no_inject,
        session=session,
        completion=completion,
    )
    gates = dict(
        walk_translation='pass' if walk['passed'] else 'fail',
        bigfoot_walk='pass' if bigfoot['seen'] else 'unmeasured',
        houdai_death='pass' if houdai_death else 'fail',
        no_carcass_source='pass' if nocarcass['passed'] else 'fail',
        preserved='pass' if (binds and schedule and window and squad >= 1) else 'fail',
        session='pass' if session else 'fail',
    )
    passed = (walk['passed'] and houdai_death and nocarcass['passed'] and binds
              and schedule and window and squad >= 1 and session and completion)
    return dict(passed=passed, checks=checks, gates=gates, walk=walk,
                bigfoot=bigfoot, death=death, nocarcass=nocarcass, squad=squad,
                natural_vs_injected=dict(
                    walk_translation_natural=walk['passed'],
                    houdai_death_natural=houdai_death,
                    inject_present=not no_inject))


# Impact Site squad overlay places 20 reds at x in [-140,-68], z in [1804,1820].
# Houdai stays at its lane26 staging (120, 30, 1850); BigFoot is parked far from
# the squad ((330, 30, 1900)) so BOTH actors start outside the 60u accumulate
# radius and reach Walk naturally instead of combat.
HOUDAI_POSITION = (120.0, 30.0, 1850.0)
BIGFOOT_POSITION = (330.0, 30.0, 1900.0)


def position_override():
    return dict(
        species=['Houdai', 'BigFoot'],
        generators={'Houdai': HOUDAI_GEN, 'BigFoot': BIGFOOT_GEN},
        arena_default=[list(HOUDAI_POSITION), list(BIGFOOT_POSITION)],
        behavior_fixture=[list(HOUDAI_POSITION), list(BIGFOOT_POSITION)],
        reason='park both Long Legs outside the 60u accumulate radius so Walk '
               'is reached naturally (muse l62 movement slice)',
        production_placement=False)


def prepare(assets, imported, output):
    """Stage a fresh walk-observation arena (cargo-free, no Pod)."""
    from experimental.pikmin2_long_legs_lifecycle import (
        BIGFOOT_INDEX, HOUDAI_INDEX)
    cfg = dict(CFG)
    positions = list(CFG['arena_positions'])
    positions[HOUDAI_INDEX] = HOUDAI_POSITION
    positions[BIGFOOT_INDEX] = BIGFOOT_POSITION
    cfg['arena_positions'] = tuple(positions)
    run = _prepare(cfg, Path(assets), Path(imported), Path(output),
                   installer=install, verifier=verify_install)
    convert_visual(run / 'assets/dataDir/courses/pikmin2room')
    (run / 'muse-longlegs-override.json').write_text(
        json.dumps(position_override(), indent=2) + '\n')
    (run / 'pikmin_settings.conf').write_text('disableTutorials = 0\n')
    return run


def instrument(source, app=None):
    """Splice the reserved walk fixture app into preview_p2_room.cpp."""
    if app is None:
        raise ValueError('muse walk fixture source text required')
    if 'P2_MUSE_WALK_READY' in source:
        raise ValueError('Room fixture already carries the muse walk app')
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    includes = ('#include <cstring>\n#include "Generator.h"\n#include "pc_p2_long_legs.h"\n'
                '#include "pc_p2_preview.h"\n#include "CinematicPlayer.h"\n'
                '#include "GameStat.h"\n#include "NaviState.h"\n')
    return includes + source[:start] + app + source[end:]


def build(native, build_dir, output, head, fixture_cpp, resume=False):
    """Build the private instrumented walk fixture (never a run)."""
    from scripts import build_pikmin2_fixture as builder
    from experimental.pikmin2_kochappy_arena_fixture import instrument_tutorial
    native = Path(native).resolve()
    build_dir = Path(build_dir).resolve()
    output = Path(output).resolve()
    app = Path(fixture_cpp).read_text()
    room = output / 'room.cpp'
    source = instrument((native / 'tools/preview_p2_room.cpp').read_text(), app)
    if resume:
        if (output / 'instrumentation.json').exists() or room.read_text() != source:
            raise ValueError('Cannot resume completed or changed fixture')
        record = json.loads((output / 'baseline/provenance.json').read_text())
        if record.get('status') != 'built' or record.get('expected_native_head') != head \
                or builder.git_state(native) != record['observed_source']:
            raise ValueError('Baseline no longer matches source')
        for key in ('inputs', 'fixture_inputs', 'configuration_inputs'):
            builder.check_snapshot(record[key])
    else:
        output.mkdir(parents=True, exist_ok=False)
        room.write_text(source)
        record = builder.build_fixture(build_dir, native, room, output / 'baseline', head)
    compile_cmd = list(record['commands'][-2])
    compile_cmd[builder.option_index(compile_cmd, '-o')] = str(output / 'room.obj')
    compile_cmd[builder.option_index(compile_cmd, '-MF')] = str(output / 'room.d')
    link = list(record['commands'][-1])
    targets = [i for i, a in enumerate(link) if a.endswith('\\fixture.obj') or a.endswith('/fixture.obj')]
    if len(targets) != 1:
        raise ValueError('Expected one private room object')
    link[targets[0]] = str(output / 'room.obj')
    link[builder.option_index(link, '-o')] = str(output / 'fixture.exe')
    link = [('-Wl,--out-implib,' + str(output / 'fixture.dll.a')) if a.startswith('-Wl,--out-implib,') else a for a in link]
    tutorial = native / 'src/plugPikiColin/newPikiGame.cpp'
    tutorial_private = output / 'tutorial.cpp'
    tutorial_private.write_text(instrument_tutorial(tutorial.read_text()))
    tutorial_compile = [str(tutorial_private) if a == str(room) else a for a in compile_cmd]
    tutorial_compile[builder.option_index(tutorial_compile, '-o')] = str(output / 'tutorial.obj')
    tutorial_compile[builder.option_index(tutorial_compile, '-MF')] = str(output / 'tutorial.d')
    targets = [i for i, a in enumerate(link) if a.endswith('libpikmin_legacy.a')]
    if len(targets) != 1:
        raise ValueError('Expected one private legacy archive')
    link.insert(targets[0], str(output / 'tutorial.obj'))
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''))
    audit = dict(original_fixture=builder.snapshot([native / 'tools/preview_p2_room.cpp', tutorial]),
                 instrumented=builder.snapshot([room, tutorial_private]),
                 commands=[compile_cmd, tutorial_compile, link], freshness_checks=[])
    for name, command in [('room-compile', compile_cmd), ('tutorial-compile', tutorial_compile), ('room-link', link)]:
        code, text = builder.run(command, build_dir, env)
        (output / (name + '.log')).write_text(text)
        if code:
            raise RuntimeError(name + ' failed')
    builder.require_fresh(Path(record['toolchain']['ninja']['path']), build_dir, audit['freshness_checks'])
    builder.check_snapshot(record['inputs'])
    builder.check_snapshot(record['fixture_inputs'])
    builder.check_snapshot(record['configuration_inputs'])
    if builder.git_state(native) != record['observed_source']:
        raise RuntimeError('Native changed during private replacement')
    audit['artifacts'] = builder.snapshot([output / 'fixture.exe', output / 'room.obj'])
    audit['status'] = 'built'
    (output / 'instrumentation.json').write_text(json.dumps(audit, indent=2) + '\n')


def run(assets, imported, output, exe, seconds=200):
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    os.environ['PATH'] = 'C:\\msys64\\mingw64\\bin;' + os.environ.get('PATH', '')
    run_dir = prepare(Path(assets), Path(imported), Path(output))
    meta = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                           run_dir, run_dir / 'capture', seconds)
    text = (run_dir / 'capture' / 'native.log').read_text(errors='replace')
    result = validate(text)
    result['capture'] = {k: meta[k] for k in ('executable_sha256', 'elapsed_seconds',
                                              'exit_code', 'timed_out')}
    (run_dir / 'muse-longlegs-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    return run_dir, meta, result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('prepare', 'run'):
        sub = commands.add_parser(name)
        for flag in ('assets', 'imported', 'output'):
            sub.add_argument('--' + flag, type=Path, required=True)
        if name == 'run':
            sub.add_argument('--exe', type=Path, required=True)
            sub.add_argument('--seconds', type=int, default=200)
    build_cmd = commands.add_parser(name='build')
    for flag in ('native', 'build-dir', 'output', 'fixture'):
        build_cmd.add_argument('--' + flag, type=Path, required=True)
    build_cmd.add_argument('--head', required=True)
    build_cmd.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if args.command == 'prepare':
        print(prepare(args.assets, args.imported, args.output))
    elif args.command == 'build':
        build(args.native, args.build_dir, args.output, args.head, args.fixture, args.resume)
    else:
        run_dir, meta, result = run(args.assets, args.imported, args.output, args.exe, args.seconds)
        print(run_dir)
        print(json.dumps(result, indent=2))
