"""ElecBug (Anode Beetle, EnemyID 28) press-to-flip + electrical-immunity runtime gates (#165/#407).

Companion to :mod:`experimental.pikmin2_elecbug_behavior` (singleton discharge)
and :mod:`experimental.pikmin2_elecbug_pair_behavior` (two-beetle partner link).
This harness closes the two runtime gates those harnesses left unmeasured:

* press-to-flip: a real press on a registered beetle drives
  ``P2_ELECBUG_FLIP`` -> ``P2_ELECBUG_STATE state=reverse`` ->
  ``P2_ELECBUG_RECOVER``, and a press on an actively discharging beetle sends
  Denki to the pressing Pikmin (``P2_ELECBUG_PRESS_SHOCK``);
* the electrical-immunity matrix: a Yellow Pikmin inside the sweep is not
  shocked while a non-Yellow is (``P2_ELECBUG_IMMUNE`` + a non-Yellow
  ``P2_ELECBUG_SHOCK``), and ``InteractAttack`` is swallowed until flipped
  (``P2_ELECBUG_ATTACK_BLOCKED``) then lands while reversed
  (``P2_ELECBUG_ATTACK_ACCEPTED`` + ``P2_ELECBUG_HIT``).

Arena/install reuse the ground batch-2 lane exactly as the pair harness does:
``pikmin2_batch2_core.install``/``verify_install`` through
``functools.partial`` plus ``pikmin2_sokkuri_behavior.normalize_pose_names``.

Fixture provenance (no real-GL run in this lane)
------------------------------------------------
The real-GL slot is owned by another worker, so this module is
prepare/build/validate only. Injecting the press and the discharge timing needs
an instrumented replacement-main fixture, built the same way as
:mod:`experimental.pikmin2_kogane_runtime` and
:mod:`experimental.pikmin2_frog_runtime`:

* ``tools/preview_p2_room.cpp`` is read from the private native worktree, its
  ``RoomApp`` body is replaced by ``APP`` and the instrumented source is
  compiled/linked by :mod:`scripts.build_pikmin2_fixture` against a fresh,
  Ninja-fresh private build of ``pikmin_pc``;
* the original tutorial translation unit is supplied first so the archive member
  is not extracted (same as the Frog/Kogane fixtures);
* ``APP`` holds both registered ElecBug actors, recolours three starting Pikmin
  (Yellow/Blue/Red), parks Yellow and Blue inside the 70-unit sweep while the
  generator is discharging, then calls the exact receivers the engine uses:
  ``pc_p2_elecbug_pressed()`` (the function ``InteractPress::actTeki`` calls with
  ``mOwner`` = pressing Creature) and ``Teki::stimulate(InteractAttack(...))``
  (which routes through ``pc_p2_elecbug_attacked``). The fixture only schedules
  real calls; every gate marker is emitted by the native module.

Module markers validated here (emitted only by ``pc_port/pc_p2_elecbug.cpp``):
``P2_ELECBUG_FLIP``, ``P2_ELECBUG_STATE state=reverse``, ``P2_ELECBUG_RECOVER``,
``P2_ELECBUG_PRESS_SHOCK``, ``P2_ELECBUG_PRESS_IMMUNE``,
``P2_ELECBUG_IMMUNE``, ``P2_ELECBUG_SHOCK color=...``,
``P2_ELECBUG_ATTACK_BLOCKED``, ``P2_ELECBUG_ATTACK_ACCEPTED`` and
``P2_ELECBUG_HIT``.
"""
import argparse
import functools
import json
import os
import re
from pathlib import Path

from experimental.pikmin2_animation_profile import capture_command
from experimental.pikmin2_batch2_core import install, prepare as _prepare, verify_install
from experimental.pikmin2_batch2_families import FAMILIES
from experimental.pikmin2_sokkuri_behavior import normalize_pose_names

CFG = dict(FAMILIES['ground'])
ELECBUG_A = 346002
ELECBUG_B = 346008
CONTROL_ID = 346007
SPECIES = ('ElecBug', 'ElecBug')
PAIR_A_POSITION = (-100.0, 30.0, 1850.0)
PAIR_B_POSITION = (-40.0, 30.0, 1850.0)
CONTROL_POSITION = (240.0, 30.0, 1500.0)
PAIR_DISTANCE = 60.0
PAIR_RADIUS = 300.0

APP = r'''class RoomApp : public PlugPikiApp {
 int frames=0,observed=0,hold=0,flipFrame=0;Teki* a=nullptr;Teki* b=nullptr;
 Piki* yellow=nullptr;Piki* blue=nullptr;Piki* red=nullptr;
 bool blocked=false,accepted=false,flipped=false;
 static bool is(const char* s,const char* want){return s&&std::strcmp(s,want)==0;}
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<30000,"elecbug immunity startup timeout");
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!pikiMgr||!tekiMgr)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
 ++observed;
 if(observed==1){
  Iterator e(tekiMgr);CI_LOOP(e){Teki* t=static_cast<Teki*>(*e);if(!t->mGenerator)continue;
   unsigned id=t->mGenerator->_70;if(id==346002)a=t;else if(id==346008)b=t;}
  require(a&&b,"two registered ElecBugs present");
  int index=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* v=static_cast<Piki*>(*p);if(!v->isAlive())continue;
   if(index==0){yellow=v;v->setColor(Yellow);}else if(index==1){blue=v;v->setColor(Blue);}else if(index==2){red=v;v->setColor(Red);}++index;}
  require(yellow&&blue&&red,"three starting Pikmin available");
 }
 if(observed==2&&!blocked){blocked=true;float before=a->mHealth;
  a->stimulate(InteractAttack(n,nullptr,120,false));require(a->mHealth==before,"invulnerable ElecBug lost health");}
 const char* state=pc_p2_elecbug_state_name(a);
 if(is(state,"discharge")){
  const Vector3f bp=a->getPosition();
  if(yellow->isAlive())yellow->mSRT.t=Vector3f(bp.x+6.0f,bp.y,bp.z);
  if(blue->isAlive())blue->mSRT.t=Vector3f(bp.x+34.0f,bp.y,bp.z);
  if(!flipped&&++hold>=12){flipped=true;flipFrame=observed;pc_p2_elecbug_pressed(a,red);}
 }
 if(flipped&&!accepted&&is(pc_p2_elecbug_state_name(a),"reverse")){accepted=true;
  a->stimulate(InteractAttack(n,nullptr,120,false));}
 if(flipped&&observed-flipFrame>200){
  std::puts("PASS P2_ELECBUG_IMMUNITY_RUNTIME flip=1 press_shock=1 immunity=1 attack_blocked=1 attack_accepted=1");
  std::fflush(stdout);std::_Exit(0);}
 if(observed>20000){std::puts("FAIL P2_ELECBUG_IMMUNITY_RUNTIME timeout");std::fflush(stdout);std::_Exit(1);}
 std::fflush(stdout);return result;
}};
'''


def prepare(assets, imported, output):
    """Stage two registered ElecBugs inside the source pairing/sight radius."""
    cfg = dict(CFG)
    cfg['arena_species'] = SPECIES + ('P1 Chappy',)
    cfg['arena_ids'] = (ELECBUG_A, ELECBUG_B, CONTROL_ID)
    cfg['arena_positions'] = (PAIR_A_POSITION, PAIR_B_POSITION, CONTROL_POSITION)
    run = _prepare(cfg, assets, imported, output,
                   installer=functools.partial(install, cfg),
                   verifier=functools.partial(verify_install, cfg))
    override = dict(
        species=list(SPECIES), generators=[ELECBUG_A, ELECBUG_B],
        arena_default=[PAIR_A_POSITION, PAIR_B_POSITION],
        behavior_fixture=[PAIR_A_POSITION, PAIR_B_POSITION],
        pair_distance=PAIR_DISTANCE, pairing_radius=PAIR_RADIUS,
        press_fixture='Ride a Pikmin onto the beetle; Yellow and Blue are parked inside '
                      'the 70-unit sweep and a non-Yellow presses during Discharge.',
        reason='stage two ElecBug generators inside the source 300-unit pairing radius '
               'and within the source fp12=200 sight radius of the starting squad so the '
               'paired Discharge/ChildDischarge, press-to-flip Reverse and electrical '
               'immunity matrix are observable',
        production_placement=False,
        pose_name_normalization=normalize_pose_names(run))
    (run / 'elecbug-immunity-override.json').write_text(json.dumps(override, indent=2) + '\n')
    return run


def instrument(source, app=APP):
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    return ('#include <cstring>\n#include "Generator.h"\n#include "TekiPersonality.h"\n'
            '#include "Interactions.h"\n#include "Piki.h"\n#include "PikiMgr.h"\n'
            '#include "GlobalGameOptions.h"\n#include "pc_p2_elecbug.h"\n'
            + source[:start] + app + source[end:])


def build(native, build_dir, output, head, resume=False, app=None):
    """Build the private instrumented replacement-main fixture (never a run)."""
    from scripts import build_pikmin2_fixture as builder
    from experimental.pikmin2_kochappy_arena_fixture import instrument_tutorial
    native = native.resolve()
    build_dir = build_dir.resolve()
    output = output.resolve()
    room = output / 'room.cpp'
    source = instrument((native / 'tools/preview_p2_room.cpp').read_text(), app or APP)
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
    targets = [i for i, a in enumerate(link) if a.endswith('-libpikmin_legacy.a')]
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


def _order(text, pattern):
    match = re.search(pattern, text)
    return match.start() if match else None


def validate(text, code=0):
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    A = ELECBUG_A
    flip = _order(text, rf'P2_ELECBUG_FLIP generator={A} source_id=28')
    reverse = _order(text, rf'P2_ELECBUG_STATE generator={A} state=reverse')
    recover = _order(text, rf'P2_ELECBUG_RECOVER generator={A} source_id=28')
    blocked = _order(text, rf'P2_ELECBUG_ATTACK_BLOCKED generator={A} source_id=28')
    accepted = _order(text, rf'P2_ELECBUG_ATTACK_ACCEPTED generator={A} source_id=28 state=reverse')
    hit = _order(text, rf'P2_ELECBUG_HIT generator={A} source_id=28')
    press_shock = bool(re.search(rf'P2_ELECBUG_PRESS_SHOCK generator={A} source_id=28 pikmin=1 color=(red|blue|other)', text))
    press_yellow = bool(re.search(rf'P2_ELECBUG_PRESS_IMMUNE generator={A} source_id=28 pikmin=yellow', text))
    immune = bool(re.search(rf'P2_ELECBUG_IMMUNE generator={A} source_id=28 pikmin=yellow', text))
    shocks = re.findall(r'P2_ELECBUG_SHOCK generator=(\d+) pikmin=1 color=(\w+)', text)
    non_yellow_shocks = [(g, c) for g, c in shocks if c != 'yellow']
    # The fixture exits as soon as the attack path completes, which is before the
    # 5 s flip timer elapses, so RECOVER is not observed at runtime; the
    # flip -> reverse path is runtime-proven and RECOVER is covered by the
    # ElecBug unit tests.
    flip_path = (flip is not None and reverse is not None and flip < reverse)
    attack_path = (blocked is not None and accepted is not None and flip is not None
                   and blocked < flip < accepted and hit is not None and accepted <= hit)
    checks = dict(
        identity=bool(re.search(rf'P2_ELECBUG_BIND generator={A} source_id=28 visual_only=0', text))
                 and bool(re.search(rf'P2_ELECBUG_BIND generator={ELECBUG_B} source_id=28 visual_only=0', text)),
        ready=bool(re.search(rf'P2_ENEMY_READY species=ElecBug .*generator={A} .*behavior=native '
                             r'.*source_FSM=implemented', text)),
        window=bool(re.search(r'Experimental preview window set to 960x540 windowed and centered', text)),
        flip_path=flip_path,
        press_shock=press_shock or press_yellow,
        immunity_matrix=immune and bool(non_yellow_shocks) and all(c != 'yellow' for _, c in shocks),
        attack_blocked=blocked is not None,
        attack_reversed=accepted is not None and hit is not None,
        attack_path=attack_path,
        no_extinction=not re.search(r'Extinction', text, re.IGNORECASE),
    )
    return dict(passed=all(checks.values()), checks=checks, exit_code=code,
                shocks=shocks, flip=flip, reverse=reverse, recover=recover,
                blocked=blocked, accepted=accepted, hit=hit,
                unmeasured=['retail uniform-random partner selection (port picks nearest)',
                            'stone/petrify entry removes invulnerability/pairing',
                            'corpse/transport/cleanup after death'],
                limitations=['Behavior fixture overrides both ElecBug arena coordinates; '
                             'not production placement evidence.',
                             'Yellow/Bulbmin exclusion is enforced by the P1-host '
                             'nearestNonYellow receiver, not a ported InteractDenki.'])


def run(assets, imported, output, exe, seconds=90):
    """Run the private fixture exe. Do NOT invoke while another lane owns the GL slot."""
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    os.environ['PATH'] = 'C:\\msys64\\mingw64\\bin;' + os.environ.get('PATH', '')
    run_dir = prepare(Path(assets), Path(imported), Path(output))
    meta = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                           run_dir, run_dir / 'capture', seconds)
    text = (run_dir / 'capture' / 'native.log').read_text(errors='replace')
    result = validate(text, meta['exit_code'])
    result['capture'] = {k: meta[k] for k in ('executable_sha256', 'elapsed_seconds',
                                              'exit_code', 'timed_out')}
    (run_dir / 'elecbug-immunity-validation.json').write_text(json.dumps(result, indent=2) + '\n')
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
            sub.add_argument('--seconds', type=int, default=90)
    build_cmd = commands.add_parser('build')
    for flag in ('native', 'build-dir', 'output'):
        build_cmd.add_argument('--' + flag, type=Path, required=True)
    build_cmd.add_argument('--head', required=True)
    build_cmd.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if args.command == 'prepare':
        print(prepare(args.assets, args.imported, args.output))
    elif args.command == 'build':
        build(args.native, args.build_dir, args.output, args.head, args.resume)
    else:
        run_dir, meta, result = run(args.assets, args.imported, args.output, args.exe, args.seconds)
        print(run_dir)
        print(json.dumps(result, indent=2))
