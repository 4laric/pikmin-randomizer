"""Lane-22 elemental dweevil runtime gate (#170, child #447): host seams.

Slice 3 moves the death/forget/reward evidence off the fixture and onto the host
seams. The primary run (`scenario='natural'`) stages the concrete P2 Pod room
(red Onion goal + treasure + `p2-pod.txt`) with a FireOtakara Chappy actor placed
inside carry range of the goal, then:

* deploys the 20-Pikmin free squad so ordinary ``InteractAttack`` receivers bring
  the actor down (every drop named `interaction=… attacker=…`);
* lets the module's ``BTeki::die()`` hook log the real death seam
  (``P2_OTAKARA_DEAD … mDeadState=1``) distinct from the module's own
  mHealth<=0 observation (``P2_OTAKARA_MODULE_DEAD``);
* observes the host dieSoon()/becomePellet() corpse pellet
  (``P2_OTAKARA_CORPSE``);
* lets the Pikmin haul the corpse pellet to the Onion, where
  ``pc_p2_preview_deliver`` routes the corpse into the shared Pod economy
  (``P2_POD_RECEIPT id=corpse:…otakara:349001``) from the additive
  ``pc_p2_otakara_receipt`` lookup branch (no separate ledger);
* waits for the lane-07 seam ``pc_p2_forget_teki`` in ``BTeki::doKill`` to clear
  the registration after the pellet is consumed, and proves the registry dropped
  to zero without invoking ``pc_p2_otakara_forget`` itself; the module's own
  ``P2_OTAKARA_FORGET`` marker reports a computed ``stale=0``.

The prior ``scenario='inject'`` (one-shot ``InteractAttack`` death trigger) is
retained as a recorder-side cross-check; it is not the primary run.
"""
import argparse
import functools
import json
import os
import re
import struct
from pathlib import Path

from experimental.pikmin2_animation_profile import capture_command
from experimental.pikmin2_batch2_core import install, prepare as _prepare, verify_install
from experimental.pikmin2_batch2_families import FAMILIES
from experimental.pikmin2_generator_pose import write_position
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
 Pellet* corpse=nullptr;
  bool blueHit=false,deadSeen=false,corpseSeen=false,assisted=false,violation=false,freeCarryLogged=false;
 public:int idle() override {
  int result=PlugPikiApp::idle();require(++frames<120000,"otakara runtime startup timeout");
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!(pc_p2_preview_cargo_free_ready()||pc_p2_preview_ready())||!naviMgr||!pikiMgr||!tekiMgr||!pelletMgr)return result;
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
  if(deadSeen&&!corpseSeen){
   // Pointer identity only (never deref fire once the host owns teardown).
   Iterator pi(pelletMgr);CI_LOOP(pi){Pellet* pp=static_cast<Pellet*>(*pi);if(pp->mPelletView==static_cast<PelletView*>(fire)){corpse=pp;break;}}
   if(corpse){corpseSeen=true;std::printf("P2_OTAKARA_CORPSE generator=349001 pellet=1 state=%d\n",corpse->getState());std::fflush(stdout);}
   else if(observed-deadAt>1200){std::puts("FAIL P2_OTAKARA_RUNTIME corpse_timeout");std::fflush(stdout);std::_Exit(1);}
  }
  if(corpseSeen){
   // Lane-07 seam: wait for pc_p2_forget_teki (BTeki::doKill) after the pellet is
   // consumed. No direct pc_p2_otakara_forget call here.
   if(!pc_p2_otakara_registered(fire)&&pc_p2_otakara_count()==0){
    std::printf("P2_OTAKARA_SEAM_OBSERVED generator=349001 registered=0 count=0\n");std::fflush(stdout);
    std::puts("PASS P2_OTAKARA_RUNTIME natural_death=1 corpse=1 receipt=1 forget=1");
    std::fflush(stdout);std::_Exit(0);
   }
   // Only assist while the corpse pellet is still present in the pellet manager;
   // delivery consumes it, so never dereference `corpse` after the receipt fires.
   bool present=false;Iterator pi(pelletMgr);CI_LOOP(pi){Pellet* pp=static_cast<Pellet*>(*pi);if(pp==corpse){present=true;break;}}
   if(present){
    // Ordinary carry assist only if native free recruitment has not latched a
    // carrier after a grace period; the Transport action is the native haul.
    int carry=0;Iterator ck(pikiMgr);CI_LOOP(ck){Piki* p=static_cast<Piki*>(*ck);if(p&&p->isAlive()&&p->getStickObject()==static_cast<Creature*>(corpse))++carry;}
    if(!freeCarryLogged&&carry>0){freeCarryLogged=true;
     std::printf("P2_OTAKARA_CARRY_FREE carry=%d\n",carry);std::fflush(stdout);}
    if(!assisted&&carry==0&&observed-deadAt>600){assisted=true;
     int assigned=0;Iterator pk(pikiMgr);CI_LOOP(pk){Piki* p=static_cast<Piki*>(*pk);if(!p->isAlive()||!p->mActiveAction)continue;
      p->mActiveAction->abandon(nullptr);p->mActiveAction->mCurrActionIdx=PikiAction::Transport;
      p->mActiveAction->mChildActions[PikiAction::Transport].initialise(corpse);p->mMode=PikiMode::TransportMode;++assigned;}
     std::printf("P2_OTAKARA_ASSIST assigned=%d\n",assigned);std::fflush(stdout);}
   }
  }
  if(violation){std::puts("FAIL P2_OTAKARA_RUNTIME immune_violation=1");std::fflush(stdout);std::_Exit(1);}
  if(observed>60000){std::puts("FAIL P2_OTAKARA_RUNTIME timeout forget_wait");std::fflush(stdout);std::_Exit(1);}
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
            '#include "Piki.h"\n#include "PikiState.h"\n#include "PikiMgr.h"\n#include "PikiAI.h"\n'
            '#include "Pellet.h"\n#include "PelletView.h"\n'
            '#include "GlobalGameOptions.h"\n#include "pc_p2_otakara.h"\n#include "pc_p2_preview.h"\n'
            + source[:start] + app + source[end:])


def prepare(assets, imported, output, scenario='natural', converted=None, pod_dir=None):
    if scenario == 'deliver' or scenario == 'natural':
        return _prepare_pod(assets, imported, output, converted, pod_dir)
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


def _prepare_pod(assets, imported, output, converted, pod_dir):
    """Concrete P2 Pod room (red Onion goal + treasure + p2-pod.txt) with one
    FireOtakara Chappy actor placed inside carry range of the goal, plus the
    dweevil profile/bank/actor sidecars and the lane-06 receipt host."""
    from scripts.preview_pikmin2_room import prepare as room_prepare
    if converted is None or pod_dir is None:
        raise ValueError('deliver/natural scenario requires --converted and --pod-dir')
    run = room_prepare(Path(assets).resolve(), Path(converted).resolve(), Path(output).resolve())
    cfg = dict(FAMILIES['dweevil'])
    gen = run / 'assets/dataDir/stages/chal0/default.gen'
    blob = bytearray(gen.read_bytes())
    starts = [m.start() for m in re.finditer(rb'    0.0v', blob)]
    dwarf = next((s for s in starts if blob[s + 72:s + 76] == b'iket'), None)
    if dwarf is None:
        raise ValueError('Concrete room has no Chappy enemy record to bind FireOtakara')
    struct.pack_into('<I', blob, dwarf + 8, FIRE_ID)
    blob[dwarf + 16:dwarf + 48] = b'preview fireotakara'.ljust(32, b'\0')
    # ~120 units from the room's red goal/Onion so the corpse carry route is bounded.
    onion = None
    for s in starts:
        if b'preview red onion' in bytes(blob[s + 16:s + 48]):
            onion = struct.unpack_from('>3f', blob, s + 48)
            break
    if onion is None:
        onion = (-220.0, 0.0, -180.0)
    struct.pack_into('>3f', blob, dwarf + 48, onion[0], 30.0, onion[2] + 115.0)
    gen.write_bytes(blob)
    install(cfg, Path(imported).resolve(), run, [(FIRE_ID, 'FireOtakara')])
    (run / 'p2-pod.txt').write_text('P2_POD_1 dia_a_red 180 15 25 Kochappy 2\n')
    (run / 'assets/dataDir/courses/pikmin2room/pod.mod').write_bytes(
        (Path(pod_dir) / 'pod.mod').read_bytes())
    (run / 'otakara-override.json').write_text(json.dumps(dict(
        species=list(SPECIES), generators=[FIRE_ID], scenario='natural',
        pod=True, onion=list(onion),
        reason='FireOtakara staged ~120 units from the concrete-room red Onion so the '
               'corpse pellet can be naturally hauled to the Pod goal and the lane-06 '
               'receipt logged from pc_p2_preview_deliver',
        production_placement=False), indent=2) + '\n')
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
    module_dead = bool(re.search(
        rf'P2_OTAKARA_MODULE_DEAD generator={FIRE_ID} source_id=59 health=0', text))
    dead = bool(re.search(
        rf'P2_OTAKARA_DEAD generator={FIRE_ID} source_id=59 mDeadState=1', text))
    corpse = bool(re.search(rf'P2_OTAKARA_CORPSE generator={FIRE_ID} pellet=1', text))
    receipt = bool(re.search(rf'P2_POD_RECEIPT id=corpse:\S*otakara:{FIRE_ID}\b', text))
    forget = bool(re.search(
        rf'P2_OTAKARA_FORGET generator={FIRE_ID} registered=1 count=0\b', text))
    assisted = 'P2_OTAKARA_ASSIST assigned=' in text
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
        module_dead=module_dead,
        natural_death=dead and not injected,
        corpse=corpse,
        receipt=receipt,
        forget=forget,
        no_extinction=not re.search(r'Extinction', text, re.IGNORECASE),
    )
    required = ('completion', 'window', 'squad', 'identity', 'ready', 'flick', 'discharge',
                'immune_red', 'hit_blue', 'natural_hit', 'module_dead', 'natural_death',
                'corpse', 'receipt', 'forget', 'no_extinction')
    gates = dict(
        identity_spawn='pass' if (identity and ready) else 'fail',
        movement_animation='pass' if flick else 'fail',
        attacks_receivers='pass' if (discharge and immune_red and hit_blue) else 'fail',
        death_corpse='pass' if (dead and not injected and corpse) else 'fail',
        transport_reward='pass_assisted' if (receipt and assisted) else ('pass' if receipt else 'fail'),
        cleanup_reentry='pass' if forget else 'fail',
    )
    return dict(passed=code == 0 and all(checks[name] for name in required),
                checks=checks, gates=gates, squad=int(squad.group(1)) if squad else 0,
                exit_code=code,
                injected=['InteractAttack death trigger (damage value 100000)'] if injected else [],
                assisted=assisted,
                unmeasured=['scene re-entry and recycled-address rebind',
                            'Water/Gas/Elec discharge (only Fire was exercised)'],
                limitations=['The 20-Pikmin FreeMode deployment is a player-equivalent stimulus, '
                             'not a recorded player-input run.',
                             'Corpse haul uses the native Transport action; a fixture assist '
                             'is labelled if natural free recruitment leaves the corpse uncarried.',
                             'Elemental discharge uses the P1 InteractFire receiver; '
                             'BombOtakara (93) and the item-carry states are out of scope.'])


def run(assets, imported, output, exe, seconds=120, scenario='natural',
        converted=None, pod_dir=None):
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    os.environ['PATH'] = 'C:\\msys64\\mingw64\\bin;' + os.environ.get('PATH', '')
    run_dir = prepare(Path(assets), Path(imported), Path(output), scenario=scenario,
                      converted=converted, pod_dir=pod_dir)
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
            sub.add_argument('--scenario', choices=('natural', 'deliver', 'inject'), default='natural')
        sub.add_argument('--converted', type=Path)
        sub.add_argument('--pod-dir', type=Path)
    b = commands.add_parser('build')
    for flag in ('native', 'build-dir', 'output'):
        b.add_argument('--' + flag, type=Path, required=True)
    b.add_argument('--head', required=True)
    b.add_argument('--resume', action='store_true')
    b.add_argument('--scenario', choices=('natural', 'deliver', 'inject'), default='natural')
    args = parser.parse_args()
    if args.command == 'prepare':
        print(prepare(args.assets, args.imported, args.output,
                      getattr(args, 'scenario', 'natural'),
                      getattr(args, 'converted', None), getattr(args, 'pod_dir', None)))
    elif args.command == 'build':
        build(args.native, args.build_dir, args.output, args.head, args.resume,
              scenario=args.scenario)
    else:
        run_dir, meta, result = run(args.assets, args.imported, args.output, args.exe,
                                    args.seconds, args.scenario,
                                    getattr(args, 'converted', None), getattr(args, 'pod_dir', None))
        print(run_dir)
        print(json.dumps(result, indent=2))
