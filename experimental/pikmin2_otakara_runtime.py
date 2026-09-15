"""Lane-22 natural elemental dweevil runtime gate (#170, child #447).

Runs the real actor-bound Fiery Dweevil (FireOtakara, EnemyID 59) FSM
(``pc_port/pc_p2_otakara.cpp``) on the batch-2 Chappy placement vehicle and
observes the natural elemental emitter -> receiver chain plus the natural
combat -> death -> corpse -> cleanup path:

* identity/spawn: ``P2_OTAKARA_BIND generator=349001 source_id=59
  stimulus=InteractFire visual_only=0`` and ``P2_ENEMY_READY
  species=FireOtakara ... source_FSM=implemented attack=elemental_discharge``;
* movement/animation: the FSM drives the shared OtakaraBase ``wait1``/``attack1``
  clips and flicks when a Pikmin is inside the 60-unit source hit radius;
* natural elemental discharge: event type 3 of the ``attack1`` clip emits the
  real ``InteractFire`` receiver. A Red Pikmin is rejected (``P2_OTAKARA_
  DISCHARGE_IMMUNE ... colour=red``), a Blue Pikmin transits the fire panic
  (``P2_OTAKARA_DISCHARGE_HIT ... stimulus=InteractFire accepted=1``);
* natural combat death: the starting squad is deployed in a circle around the
  actor and switched to ``FreeMode`` (player-equivalent stimulus, no fixture
  damage). Ordinary Pikmin ``InteractAttack`` receivers reduce health; every drop
  is logged with its interaction and attacker colour (``P2_OTAKARA_HIT ...
  interaction=InteractAttack attacker=red``). The real death seam is
  ``P2_OTAKARA_DEAD ... health=0``;
* host corpse: the fixture keeps running past mHealth<=0 so the host
  die()/dieSoon()/becomePellet() path runs; it observes the corpse pellet whose
  ``mPelletView`` is the dead actor (``P2_OTAKARA_CORPSE ... pellet=1``);
* cleanup: the lane-07 lifecycle seam ``pc_p2_otakara_forget`` clears the dead
  binding and the registry returns to zero (``P2_OTAKARA_FORGET ... count=0
  registered=0 stale=0``); no stale fire/red/blue pointers remain.

The leading ``InteractAttack`` death inject of the previous slice is retained as
the ``scenario='inject'`` variant for cross-checking the recorder-side death path;
the primary run is natural combat.
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

APP_NATURAL = r'''class RoomApp : public PlugPikiApp {
 int frames=0,observed=0,stage=0,deadAt=0,deployed=0;
 Teki* fire=nullptr;
 Piki* red=nullptr;Piki* blue=nullptr;
 bool blueHit=false,deadSeen=false,violation=false;
 Pellet* corpse=nullptr;
 public:int idle() override {
  int result=PlugPikiApp::idle();require(++frames<120000,"otakara natural runtime startup timeout");
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!pikiMgr||!tekiMgr)return result;
  Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
  ++observed;
  if(stage==0){
   Iterator e(tekiMgr);CI_LOOP(e){Teki* t=static_cast<Teki*>(*e);if(!t->mGenerator)continue;
    if(t->mGenerator->_70==349001)fire=t;}
   require(fire,"FireOtakara registered");
   require(pc_p2_otakara_registered(fire),"FireOtakara FSM registered");
   int index=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* v=static_cast<Piki*>(*p);if(!v->isAlive())continue;
    if(index==0){red=v;v->setColor(Red);}else if(index==1){blue=v;v->setColor(Blue);}++index;}
   require(red&&blue,"two starting Pikmin available");
   int reds=0,blues=0;Iterator q(pikiMgr);CI_LOOP(q){Piki* v=static_cast<Piki*>(*q);if(v->isAlive()){if(v->mColor==Red)++reds;else if(v->mColor==Blue)++blues;}}
   std::printf("P2_OTAKARA_SQUAD red=%d blue=%d registered=%lu\n",reds,blues,pc_p2_otakara_count());
   std::fflush(stdout);stage=1;
  }
  if(stage<2){
   // Park the fire-immune Red and fire-vulnerable Blue inside the 60-unit
   // discharge radius so the native Flick discharge reaches them (labelled
   // fixture intervention; the FSM/emitter/receiver are native).
   const Vector3f fp=fire->getPosition();
   if(red->isAlive()&&red->getState()!=PIKISTATE_Fired)red->mSRT.t=Vector3f(fp.x+14.0f,fp.y,fp.z);
   if(blue->isAlive()&&blue->getState()!=PIKISTATE_Fired)blue->mSRT.t=Vector3f(fp.x+32.0f,fp.y,fp.z);
   if(!blueHit&&blue->getState()==PIKISTATE_Fired)blueHit=true;
   if(red->getState()==PIKISTATE_Fired)violation=true;
   if(stage==1&&blueHit&&observed>40){
    if(deployed==0){
     int count=0;Iterator squad(pikiMgr);CI_LOOP(squad){Piki* p=static_cast<Piki*>(*squad);if(!p->isAlive())continue;
      float angle=float(count)*6.2831853f/20.f;
      Vector3f point=Vector3f(fp.x+22*std::sin(angle),fp.y,fp.z+22*std::cos(angle));
      point.y=mapMgr->getMinY(point.x,point.z,true);
      p->resetPosition(point);p->changeMode(PikiMode::FreeMode,n);++count;}
     deployed=count;
     std::printf("P2_OTAKARA_DEPLOY free_squad=%d\n",deployed);std::fflush(stdout);
    }
    stage=2;
   }
   if(stage==1&&observed>900){std::puts("FAIL P2_OTAKARA_RUNTIME discharge_timeout");std::fflush(stdout);std::_Exit(1);}
  }
  if(stage>=2&&!deadSeen&&fire->mHealth<=0.0f){deadSeen=true;deadAt=observed;}
  if(deadSeen&&!corpse){
   // The host die()/dieSoon()/becomePellet() path leaves a corpse pellet whose
   // mPelletView is the dead actor; pointer identity only, no deref of fire.
   Iterator pi(pelletMgr);CI_LOOP(pi){Pellet* pp=static_cast<Pellet*>(*pi);if(pp->mPelletView==static_cast<PelletView*>(fire)){corpse=pp;break;}}
   if(corpse){std::printf("P2_OTAKARA_CORPSE generator=349001 pellet=1 state=%d\n",corpse->getState());std::fflush(stdout);}
   else if(observed-deadAt>1200){std::puts("FAIL P2_OTAKARA_RUNTIME corpse_timeout");std::fflush(stdout);std::_Exit(1);}
  }
  if(corpse){
   // Lane-07 lifecycle seam: forget the dead binding and prove the registry is
   // empty (no stale module key; the fire/red/blue C++ pointers are never
   // dereferenced again after this point).
   pc_p2_otakara_forget(fire);
   require(pc_p2_otakara_count()==0&&!pc_p2_otakara_registered(fire),"otakara registry not cleared by forget");
   std::printf("P2_OTAKARA_FORGET generator=349001 count=0 registered=0 stale=0\n");std::fflush(stdout);
   std::puts("PASS P2_OTAKARA_RUNTIME natural_death=1 corpse=1 forget=1");
   std::fflush(stdout);std::_Exit(0);
  }
  if(violation){std::puts("FAIL P2_OTAKARA_RUNTIME immune_violation=1");std::fflush(stdout);std::_Exit(1);}
  if(observed>30000){std::puts("FAIL P2_OTAKARA_RUNTIME timeout");std::fflush(stdout);std::_Exit(1);}
  std::fflush(stdout);return result;
 }};
'''

APP_INJECT = r'''class RoomApp : public PlugPikiApp {
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
  const Vector3f fp=fire->getPosition();
  if(red->isAlive()&&red->getState()!=PIKISTATE_Fired)red->mSRT.t=Vector3f(fp.x+14.0f,fp.y,fp.z);
  if(blue->isAlive()&&blue->getState()!=PIKISTATE_Fired)blue->mSRT.t=Vector3f(fp.x+32.0f,fp.y,fp.z);
  if(!blueHit&&blue->getState()==PIKISTATE_Fired){blueHit=true;hitFrame=observed;}
  if(red->getState()==PIKISTATE_Fired)violation=true;
  if(!injected&&blueHit&&observed>hitFrame+10){injected=true;
   float before=fire->mHealth;
   fire->stimulate(InteractAttack(n,nullptr,100000,false));
   std::printf("P2_OTAKARA_DEATH_INJECT before=%.1f\n",before);
   std::fflush(stdout);
  }
  if(injected&&!deadSeen&&fire->mHealth<=0.0f){deadSeen=true;
   std::printf("P2_OTAKARA_DEATH_OBSERVE health=%.1f\n",fire->mHealth);
   std::fflush(stdout);}
  if(deadSeen){
   std::puts("PASS P2_OTAKARA_RUNTIME injected=1 deadline=1");
   std::fflush(stdout);std::_Exit(0);
  }
  if(violation){std::puts("FAIL P2_OTAKARA_RUNTIME immune_violation=1");std::fflush(stdout);std::_Exit(1);}
  if(observed>30000){std::puts("FAIL P2_OTAKARA_RUNTIME timeout");std::fflush(stdout);std::_Exit(1);}
  std::fflush(stdout);return result;
 }};
'''


def instrument(source, app=APP_NATURAL):
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    return ('#include <cstring>\n#include <cstdlib>\n#include <cmath>\n#include "Generator.h"\n'
            '#include "TekiPersonality.h"\n#include "Interactions.h"\n'
            '#include "Piki.h"\n#include "PikiState.h"\n#include "PikiMgr.h"\n'
            '#include "GlobalGameOptions.h"\n#include "pc_p2_otakara.h"\n'
            + source[:start] + app + source[end:])


def prepare(assets, imported, output, scenario='natural'):
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
        scenario=scenario,
        reason='stage one FireOtakara generator near the starting squad so the '
               'natural Flick fire discharge and the queue-then-apply death path are '
               'observable without production placement claims',
        production_placement=False)
    (run / 'otakara-override.json').write_text(json.dumps(override, indent=2) + '\n')
    return run


def build(native, build_dir, output, head, resume=False, app=None, scenario='natural'):
    chosen = app or (APP_INJECT if scenario == 'inject' else APP_NATURAL)
    original = immunity.instrument
    immunity.instrument = lambda source, _app=None: instrument(source, chosen)
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
    natural_hit = bool(re.search(
        rf'P2_OTAKARA_HIT generator={FIRE_ID} source_id=59 .*interaction=InteractAttack '
        r'attacker=\w+', text))
    injected = bool(re.search(r'P2_OTAKARA_DEATH_INJECT before=\d+', text))
    dead = bool(re.search(rf'P2_OTAKARA_DEAD generator={FIRE_ID} source_id=59 health=0', text))
    corpse = bool(re.search(rf'P2_OTAKARA_CORPSE generator={FIRE_ID} pellet=1', text))
    forget = bool(re.search(
        rf'P2_OTAKARA_FORGET generator={FIRE_ID} count=0 registered=0 stale=0', text))
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
        natural_hit=natural_hit,
        natural_death=dead and not injected,
        corpse=corpse,
        forget=forget,
        no_extinction=not re.search(r'Extinction', text, re.IGNORECASE),
    )
    required = ('completion', 'window', 'squad', 'identity', 'ready', 'flick', 'discharge',
                'immune_red', 'hit_blue', 'natural_hit', 'natural_death', 'corpse', 'forget',
                'no_extinction')
    gates = dict(
        identity_spawn='pass' if (identity and ready) else 'fail',
        movement_animation='pass' if flick else 'fail',
        attacks_receivers='pass' if (discharge and immune_red and hit_blue) else 'fail',
        death_corpse='pass' if ((dead and not injected) and corpse) else 'fail',
        transport_reward='untested',
        cleanup_reentry='pass' if forget else 'fail',
    )
    return dict(passed=code == 0 and all(checks[name] for name in required),
                checks=checks, gates=gates, squad=int(squad.group(1)) if squad else 0,
                exit_code=code,
                injected=['InteractAttack death trigger (damage value 100000)'] if injected else [],
                unmeasured=['corpse pellet transport to Onion / reward (cargo-free arena has no '
                            'Pod or Onion ledger)',
                            'scene re-entry and recycled-address rebind',
                            'Water/Gas/Elec discharge (only Fire was exercised)'],
                limitations=['The 20-Pikmin FreeMode deployment is a player-equivalent stimulus, '
                             'not a recorded player-input run.',
                             'Behavior fixture overrides the FireOtakara arena coordinate; '
                             'not production placement evidence.',
                             'Elemental discharge uses the P1 InteractFire receiver; '
                             'BombOtakara (93) and the item-carry states are out of scope.'])


def run(assets, imported, output, exe, seconds=120, scenario='natural'):
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    os.environ['PATH'] = 'C:\\msys64\\mingw64\\bin;' + os.environ.get('PATH', '')
    run_dir = prepare(Path(assets), Path(imported), Path(output), scenario=scenario)
    meta = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                           run_dir, run_dir / 'capture', seconds)
    text = (run_dir / 'capture' / 'native.log').read_text(errors='replace')
    result = validate(text, meta['exit_code'])
    result['scenario'] = scenario
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
            sub.add_argument('--scenario', choices=('natural', 'inject'), default='natural')
    b = commands.add_parser('build')
    for flag in ('native', 'build-dir', 'output'):
        b.add_argument('--' + flag, type=Path, required=True)
    b.add_argument('--head', required=True)
    b.add_argument('--resume', action='store_true')
    b.add_argument('--scenario', choices=('natural', 'inject'), default='natural')
    args = parser.parse_args()
    if args.command == 'prepare':
        print(prepare(args.assets, args.imported, args.output,
                      getattr(args, 'scenario', 'natural')))
    elif args.command == 'build':
        build(args.native, args.build_dir, args.output, args.head, args.resume,
              scenario=args.scenario)
    else:
        run_dir, meta, result = run(args.assets, args.imported, args.output, args.exe,
                                    args.seconds, args.scenario)
        print(run_dir)
        print(json.dumps(result, indent=2))
