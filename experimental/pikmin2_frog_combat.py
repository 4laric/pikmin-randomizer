"""Lane 16 natural frog combat observation (#167/#201).

Pins the 20-red starting squad in contact with the registered Frog and observes
P1's ordinary combat exchange with no injected damage: the frog must take natural
Pikmin damage (vulnerability) and the squad must lose members to the frog's
landing press (attack), ending in the frog's natural death with a corpse, a
depleted squad, or the observation window. Unregistered control frogs stay alive.
The `P2_FROG_PRESS` and `P2_FROG_LAND` markers are reported as instrumentation,
not proof of the source landing press: `P2_FROG_LAND` attributes grounded
receivers inside the source head radius but is not made a hard pass condition.
The `P2_FROG_LAND` row now carries the resolved ``bittered``/``pressed``/
``origin``/``host_frozen`` fields and `P2_FROG_BITTER` records the
``pc_p2_frog_set_bittered`` toggle, so a fixture can observe both the
not-bittered and bittered branches. No engine provider writes
``Creature::mIsFrozen``; see ``docs/PIKMIN2_FROG_RUNTIME_ACCEPTANCE.md``.
"""
import re

from experimental.pikmin2_frog_runtime import build as _build
from experimental.pikmin2_frog_runtime import run as _run
from experimental.pikmin2_frog_fsm import parse_states as _parse_states, validate as _validate_fsm

APP = r'''#include <cmath>
#include "Piki.h"
#include "PikiMgr.h"
#include "Pellet.h"
#include "PelletView.h"
class RoomApp : public PlugPikiApp {
 int observed=0,frames=0,zeroFrames=0;Teki* frog=nullptr;float firstHealth=-1.0f,lastHealth=-1.0f;int initialPikis=0;bool died=false,done=false;
 int alivePikis(){int c=0;Iterator it(pikiMgr);CI_LOOP(it){Creature* p=*it;if(p&&p->isAlive())++c;}return c;}
 bool liveTeki(unsigned id){Iterator it(tekiMgr);CI_LOOP(it){Teki* a=static_cast<Teki*>(*it);if(a&&a->mGenerator&&a->mGenerator->_70==id&&a->isAlive())return true;}return false;}
 int frogBodies(){int bodies=0;Iterator p(pelletMgr);CI_LOOP(p){Pellet* b=static_cast<Pellet*>(*p);if(b->isAlive()&&b->mPelletView==static_cast<PelletView*>(frog))++bodies;}return bodies;}
 void finish(const char* why){if(done)return;done=true;
  std::printf("P2_FROG_COMBAT_RESULT reason=%s frog_dead=%d corpse=%d squad=%d controls=%d first=%.1f last=%.1f\n",why,int(died),frogBodies(),pikiMgr?alivePikis():0,int(liveTeki(201003)&&liveTeki(201004)),firstHealth,lastHealth);
  std::puts("PASS P2_FROG_COMBAT natural_combat=1");std::fflush(stdout);std::_Exit(0);}
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<30000,"frog combat timeout");
 if(frames%120==0){std::printf("P2_FROG_COMBAT_GATE frame=%d ready=%d pause=%d ui=%d movie=%d pikis=%d\n",frames,int(pc_p2_preview_cargo_free_ready()),int(gameflow.mPauseAll),int(gameflow.mIsUIOverlayActive),int(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive),pikiMgr?alivePikis():0);std::fflush(stdout);}
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive)gameflow.mMoviePlayer->requestSkip();
 if(frog&&initialPikis>0){
  const int pikis=alivePikis();if(pikis<=0)++zeroFrames;else zeroFrames=0;
  if(zeroFrames>=10)finish("depleted");
  if(!frog->isAlive()&&died&&frogBodies()>=1)finish("death");
  if(frames>=4000)finish("window");
 }
 if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr||!pikiMgr)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
 ++observed;
 if(observed==1){
  for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f);
  Iterator it(tekiMgr);CI_LOOP(it){Teki* a=static_cast<Teki*>(*it);if(a->mGenerator&&a->mGenerator->_70==201001)frog=a;}
  require(frog&&frog->mTekiType==0,"combat frog missing");
  firstHealth=frog->mHealth;initialPikis=alivePikis();
  std::printf("P2_FROG_COMBAT_BEGIN generator=201001 health=%.1f pikis=%d\n",frog->mHealth,initialPikis);std::fflush(stdout);
 }
 if(!frog)return result;
 if(frog->isAlive()){
  int idx=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(!p||!p->isAlive())continue;
   const Vector3f c=frog->getPosition();const float a=6.28318530718f*float(idx)/20.0f;
   p->mSRT.t.set(c.x+14.0f*std::cos(a),c.y,c.z+14.0f*std::sin(a));p->mVelocity.set(0,0,0);p->mTargetVelocity.set(0,0,0);++idx;}
  lastHealth=frog->mHealth;
  if(observed%15==0){std::printf("P2_FROG_COMBAT_TICK health=%.1f pikis=%d\n",frog->mHealth,alivePikis());std::fflush(stdout);}
 } else if(!died){
  died=true;std::printf("P2_FROG_COMBAT_DEATH health=%.1f pikis=%d\n",frog->mHealth,alivePikis());std::fflush(stdout);
 }
 std::fflush(stdout);return result;
 }};
'''


def build(native, build_dir, output, head, resume=False):
    return _build(native, build_dir, output, head, resume, app=APP)


def run(assets, bank, output, exe):
    return _run(assets, bank, output, exe, validator=validate)


def validate(text, code):
    begin = re.search(r'P2_FROG_COMBAT_BEGIN generator=201001 health=([\d.]+) pikis=(\d+)', text)
    ticks = [float(h) for h in re.findall(r'P2_FROG_COMBAT_TICK health=([\d.]+)', text)]
    squad = [int(p) for p in re.findall(r'P2_FROG_COMBAT_TICK health=[\d.]+ pikis=(\d+)', text)]
    result = re.search(r'P2_FROG_COMBAT_RESULT reason=(\w+) frog_dead=(\d+) corpse=(\d+) squad=(\d+) controls=(\d+)', text)
    start = float(begin[1]) if begin else None
    initial = int(begin[2]) if begin else 0
    checks = dict(
        completion=code == 0 and 'PASS P2_FROG_COMBAT ' in text,
        begin=start == 800.0 and initial == 20,
        vulnerability=bool(ticks) and start is not None and min(ticks) < start,
        frog_attack=bool(squad) and min(squad) < initial,
        controls_alive=bool(result) and result[5] == '1',
        outcome=bool(result) and (result[2] == '0' or int(result[3]) >= 1))
    try:
        fsm_result = _validate_fsm(_parse_states(text))
        checks['fsm'] = fsm_result['passed']
        fsm_errors = list(fsm_result['errors'])
    except ValueError as exc:
        checks['fsm'] = False
        fsm_errors = [str(exc)]
    land = re.findall(r'P2_FROG_LAND species=(\w+) radius=([\d.]+) bittered=(\d) '
                      r'pikmin=(\d+) navi=(\d+) behavior=(P1_proxy|source)'
                      r'(?: pressed=(\d) origin=(\w+) host_frozen=(\d+))?', text)
    bitter = re.findall(r'P2_FROG_BITTER species=(\w+) override=(\d) host_frozen=(\d+) '
                        r'effective=(\d) origin=(\w+)', text)
    return dict(passed=all(checks.values()), checks=checks, ticks=ticks, squad=squad,
                reason=result[1] if result else None, frog_dead=result[2] if result else None,
                corpse=result[3] if result else None,
                fsm_errors=fsm_errors,
                press_markers={'Frog': len(re.findall(r'P2_FROG_PRESS species=Frog ', text)),
                               'MaroFrog': len(re.findall(r'P2_FROG_PRESS species=MaroFrog ', text))},
                land_markers={'Frog': len(re.findall(r'P2_FROG_LAND species=Frog ', text)),
                              'MaroFrog': len(re.findall(r'P2_FROG_LAND species=MaroFrog ', text))},
                land_attribution=[{'species': s, 'radius': float(r), 'bittered': b == '1',
                                   'pikmin': int(p), 'navi': int(n),
                                   'pressed': int(pr) if pr != '' else int(b == '0'),
                                   'origin': o or 'unknown', 'host_frozen': int(hf) if hf != '' else 0}
                                   for s, r, b, p, n, _beh, pr, o, hf in land],
                bitter_markers=[{'species': s, 'override': o == '1', 'host_frozen': int(hf),
                                 'effective': e == '1', 'origin': og}
                                for s, o, hf, e, og in bitter],
                unmeasured=['transport/rewards', 'full scene/day reload',
                            'native engine-level bitter/stone provider (Creature::mIsFrozen is '
                            'read by the frog rule but no provider writes it; the family override '
                            'pc_p2_frog_set_bittered covers fixture testing)'])


if __name__ == '__main__':
    import argparse
    from pathlib import Path
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build'); r = sub.add_parser('run')
    for n in ('native', 'build-dir', 'output'):
        b.add_argument('--' + n, type=Path, required=True)
    b.add_argument('--head', required=True); b.add_argument('--resume', action='store_true')
    for n in ('assets', 'bank', 'output', 'exe'):
        r.add_argument('--' + n, type=Path, required=True)
    a = p.parse_args()
    if a.command == 'build':
        build(a.native, a.build_dir, a.output, a.head, a.resume)
    else:
        run(a.assets, a.bank, a.output, a.exe)
