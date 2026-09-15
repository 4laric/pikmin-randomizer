"""Lane-22 natural elemental dweevil runtime gate (#170, child #447).

Runs the real actor-bound Fiery Dweevil (FireOtakara, EnemyID 59) FSM
(``pc_port/pc_p2_otakara.cpp``) on the batch-2 Chappy placement vehicle and
observes the natural elemental emitter -> receiver chain plus the natural death
path:

* identity/spawn: ``P2_OTAKARA_BIND generator=349001 source_id=59
  stimulus=InteractFire visual_only=0`` and ``P2_ENEMY_READY
  species=FireOtakara ... source_FSM=implemented attack=elemental_discharge``;
* movement/animation: the FSM drives the shared OtakaraBase ``wait1``/``attack1``
  clips and flicks when a Pikmin is inside the 60-unit source hit radius;
* natural elemental discharge: event type 3 of the ``attack1`` clip emits the
  real ``InteractFire`` receiver. The emitter honours the lane-11 capability
  matrix and simply does not deliver to a fire-immune Pikmin
  (``P2_OTAKARA_DISCHARGE_IMMUNE ... colour=red``, emitter-side); a Blue Pikmin
  reaches the real receiver and transits the fire panic
  (``P2_OTAKARA_DISCHARGE_HIT ... stimulus=InteractFire accepted=1``, later
  ``PIKISTATE_Fired``);
* damage/death: every mHealth drop is logged (``P2_OTAKARA_HIT``) including the
  natural pre-injection combat; one labeled ``InteractAttack`` injection then
  drives the queue-then-apply path to 0 and the module logs ``P2_OTAKARA_DEAD
  health=0``. Host die()/dieSoon()/becomePellet() teardown and the corpse pellet
  are NOT observed (the fixture exits at health<=0).

The fixture recolours two starting Pikmin (Red/Blue) and parks them inside the
fire discharge radius; the FSM, the emitter, the receiver and the death-health
drop are all native. The ``InteractAttack`` death trigger is a labeled injection
of the damage value, not a forced death.
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
import experimental.pikmin2_elecbug_immunity_behavior as immunity

FIRE_ID = 349001
CONTROL_ID = 349006
SPECIES = ('FireOtakara',)
FIRE_POSITION = (0.0, 30.0, 1850.0)
CONTROL_POSITION = (240.0, 30.0, 1500.0)

APP = r'''class RoomApp : public PlugPikiApp {
 int frames=0,observed=0;Teki* fire=nullptr;
 Piki* red=nullptr;Piki* blue=nullptr;
 bool blueHit=false,injected=false,deadSeen=false,violation=false;
 int hitFrame=0;
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<120000,"otakara runtime startup timeout");
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!pikiMgr||!tekiMgr)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
 ++observed;
 if(observed==1){
  Iterator e(tekiMgr);CI_LOOP(e){Teki* t=static_cast<Teki*>(*e);if(!t->mGenerator)continue;
   if(t->mGenerator->_70==349001)fire=t;}
  require(fire,"FireOtakara registered");
  require(pc_p2_otakara_registered(fire),"FireOtakara FSM registered");
  int index=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* v=static_cast<Piki*>(*p);if(!v->isAlive())continue;
   if(index==0){red=v;v->setColor(Red);}else if(index==1){blue=v;v->setColor(Blue);}++index;}
  require(red&&blue,"two starting Pikmin available");
  int reds=0,blues=0;Iterator q(pikiMgr);CI_LOOP(q){Piki* v=static_cast<Piki*>(*q);if(v->isAlive()){if(v->mColor==Red)++reds;else if(v->mColor==Blue)++blues;}}
  std::printf("P2_OTAKARA_SQUAD red=%d blue=%d registered=%lu\n",reds,blues,pc_p2_otakara_count());
  std::fflush(stdout);
 }
 // Park the two Pikmin inside the 60-unit fire discharge radius so the natural
 // Flick discharge reaches them. (Positioning is a labeled fixture intervention;
 // the FSM/emitter/receiver are native.)
 const Vector3f fp=fire->getPosition();
 if(red->isAlive()&&red->getState()!=PIKISTATE_Fired)red->mSRT.t=Vector3f(fp.x+14.0f,fp.y,fp.z);
 if(blue->isAlive()&&blue->getState()!=PIKISTATE_Fired)blue->mSRT.t=Vector3f(fp.x+32.0f,fp.y,fp.z);
 // Natural hit evidence: Blue (fire-vulnerable) transits the fire panic state.
 if(!blueHit&&blue->getState()==PIKISTATE_Fired){blueHit=true;hitFrame=observed;}
 // A Red Pikmin (fire-immune) must never enter the fire panic state.
 if(red->getState()==PIKISTATE_Fired)violation=true;
 // Inject the fatal attack once the natural discharge is observed, so the source
 // queue-then-apply death path can run. Labeled injection of the damage value.
 if(!injected&&blueHit&&observed>hitFrame+10){injected=true;
  float before=fire->mHealth;
  fire->stimulate(InteractAttack(n,nullptr,100000,false));
  std::printf("P2_OTAKARA_DEATH_INJECT before=%.1f\n",before);
  std::fflush(stdout);
 }
  // A real queue-then-apply death drives health<=0 -> the module's Dead state.
  // The fixture exits here: host die()/dieSoon()/becomePellet() teardown and the
  // corpse pellet are NOT observed (relabelled UNTESTED, see handoff).
  if(injected&&!deadSeen&&fire->mHealth<=0.0f){deadSeen=true;
   std::printf("P2_OTAKARA_DEATH_OBSERVE health=%.1f\n",fire->mHealth);
   std::fflush(stdout);}
 if(deadSeen){
  std::puts("PASS P2_OTAKARA_RUNTIME");
  std::fflush(stdout);std::_Exit(0);
 }
 if(violation){std::puts("FAIL P2_OTAKARA_RUNTIME immune_violation=1");std::fflush(stdout);std::_Exit(1);}
 if(observed>30000){std::puts("FAIL P2_OTAKARA_RUNTIME timeout");std::fflush(stdout);std::_Exit(1);}
 std::fflush(stdout);return result;
}};
'''


def instrument(source, app=APP):
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    return ('#include <cstring>\n#include <cstdlib>\n#include "Generator.h"\n'
            '#include "TekiPersonality.h"\n#include "Interactions.h"\n'
            '#include "Piki.h"\n#include "PikiState.h"\n#include "PikiMgr.h"\n'
            '#include "GlobalGameOptions.h"\n#include "pc_p2_otakara.h"\n'
            + source[:start] + app + source[end:])


def prepare(assets, imported, output):
    cfg = dict(FAMILIES['dweevil'])
    cfg['arena_species'] = SPECIES + ('P1 Chappy',)
    cfg['arena_ids'] = (FIRE_ID, CONTROL_ID)
    cfg['arena_positions'] = (FIRE_POSITION, CONTROL_POSITION)
    run = _prepare(cfg, assets, imported, output,
                   installer=functools.partial(install, cfg),
                   verifier=functools.partial(verify_install, cfg))
    override = dict(
        species=list(SPECIES), generators=[FIRE_ID],
        arena_default=[FIRE_POSITION], behavior_fixture=[FIRE_POSITION],
        reason='stage one FireOtakara generator near the starting squad so the '
               'natural Flick fire discharge and the queue-then-apply death path are '
               'observable without production placement claims',
        production_placement=False)
    (run / 'otakara-override.json').write_text(json.dumps(override, indent=2) + '\n')
    return run


def build(native, build_dir, output, head, resume=False, app=None):
    original = immunity.instrument
    immunity.instrument = lambda source, _app=None: instrument(source, app or APP)
    try:
        return immunity.build(native, build_dir, output, head, resume)
    finally:
        immunity.instrument = original


def validate(text, code=0):
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    identity = bool(re.search(
        rf'P2_OTAKARA_BIND generator={FIRE_ID} source_id=59 stimulus=InteractFire visual_only=0', text))
    ready = bool(re.search(
        rf'P2_ENEMY_READY species=FireOtakara .*generator={FIRE_ID} .*behavior=native '
        r'.*source_FSM=implemented attack=elemental_discharge', text))
    flick = bool(re.search(rf'P2_OTAKARA_STATE generator={FIRE_ID} state=flick', text))
    discharge = bool(re.search(
        rf'P2_OTAKARA_DISCHARGE generator={FIRE_ID} source_id=59 stimulus=InteractFire', text))
    immune_red = bool(re.search(
        rf'P2_OTAKARA_DISCHARGE_IMMUNE generator={FIRE_ID} source_id=59 pikmin=\d+ colour=red '
        r'stimulus=InteractFire', text))
    hit_blue = bool(re.search(
        rf'P2_OTAKARA_DISCHARGE_HIT generator={FIRE_ID} source_id=59 pikmin=\d+ colour=blue '
        r'stimulus=InteractFire accepted=1', text))
    death_inject = bool(re.search(rf'P2_OTAKARA_DEATH_INJECT before=\d+', text))
    dead = bool(re.search(rf'P2_OTAKARA_DEAD generator={FIRE_ID} source_id=59 health=0', text))
    natural_damage = bool(re.search(rf'P2_OTAKARA_HIT generator={FIRE_ID} source_id=59 health=150\.0->', text))
    squad = re.search(r'P2_OTAKARA_SQUAD red=(\d+) blue=(\d+) registered=(\d+)', text)
    checks = dict(
        completion=code == 0 and 'PASS P2_OTAKARA_RUNTIME' in text,
        window=bool(re.search(r'Experimental preview window set to 960x540 windowed and centered', text)),
        squad=bool(squad) and int(squad.group(3)) >= 1,
        identity=identity,
        ready=ready,
        flick=flick,
        discharge=discharge,
        immune_red=immune_red,
        hit_blue=hit_blue,
        natural_damage=natural_damage,
        death_inject=death_inject,
        dead=dead,
        no_extinction=not re.search(r'Extinction', text, re.IGNORECASE),
    )
    return dict(passed=all(checks.values()), checks=checks, exit_code=code,
                injected=['InteractAttack death trigger (damage value 100000)',
                           'starting Pikmin recoloured Red/Blue and parked in the '
                           'discharge radius'],
                unmeasured=['host die()/dieSoon()/becomePellet() corpse teardown after '
                            'health<=0 (fixture exits at the health drop)',
                            'corpse pellet/transport/reward after death',
                            'scene re-entry and recycled-address rebind'],
                limitations=['Behavior fixture overrides the FireOtakara arena coordinate; '
                             'not production placement evidence.',
                             'The discharge immunity is emitter-side (the lane-11 matrix '
                             'suppresses delivery to fire-immune Pikmin); the Blue hit proves '
                             'the real InteractFire receiver runs. BombOtakara (93) and the '
                             'item-carry states are out of scope.'])


def run(assets, imported, output, exe, seconds=120):
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    os.environ['PATH'] = 'C:\\msys64\\mingw64\\bin;' + os.environ.get('PATH', '')
    run_dir = prepare(Path(assets), Path(imported), Path(output))
    meta = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                           run_dir, run_dir / 'capture', seconds)
    text = (run_dir / 'capture' / 'native.log').read_text(errors='replace')
    result = validate(text, meta['exit_code'])
    result['capture'] = {k: meta[k] for k in ('executable_sha256', 'elapsed_seconds',
                                              'exit_code', 'timed_out')}
    (run_dir / 'otakara-validation.json').write_text(json.dumps(result, indent=2) + '\n')
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
            sub.add_argument('--seconds', type=int, default=120)
    b = commands.add_parser('build')
    for flag in ('native', 'build-dir', 'output'):
        b.add_argument('--' + flag, type=Path, required=True)
    b.add_argument('--head', required=True)
    b.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if args.command == 'prepare':
        print(prepare(args.assets, args.imported, args.output))
    elif args.command == 'build':
        build(args.native, args.build_dir, args.output, args.head, args.resume)
    else:
        run_dir, meta, result = run(args.assets, args.imported, args.output, args.exe, args.seconds)
        print(run_dir)
        print(json.dumps(result, indent=2))
