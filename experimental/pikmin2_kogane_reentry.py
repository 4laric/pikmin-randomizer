"""Lane 17 in-process re-entry acceptance for the restored-flip escape (#168/#219).

Private fixture built on the parameterized
``experimental.pikmin2_kogane_runtime.build/run`` arena (the same staging path as
the accepted batch-4 behavior fixture). It drives two flips on Kogane (219001),
one on Wealthy (219002) and leaves Doodlebug (219003) untouched, then calls
``pc_p2_kogane_reset()`` + ``pc_p2_kogane_setup()`` a second time in the same
process. The reset snapshots every live actor's flip count by generator id and
setup must reconstruct the spent state instead of re-spawning a beetle that can
never drop again:

  - Kogane, already at the source flip cap, is restored escaped
    (``P2_KOGANE_RESTORED_ESCAPE``) and burrows away,
  - Wealthy resumes at its restored flip count (``P2_KOGANE_FLIPS_RESTORED``),
  - the untouched Doodlebug emits no restore line.

The third Kogane press and the reset+setup happen in the same tick, before the
pending damage-clip escape finalizes, so every actor is still present at setup.
This module never runs the desktop/GL slot; ``validate`` checks the captured log.
See ``docs/PIKMIN2_KOGANE_REWARDS.md``.
"""
import argparse
import re
from pathlib import Path

from experimental.pikmin2_kogane_assets import MAX_FLIPS
from experimental.pikmin2_kogane_behavior import native_sidecar
from experimental.pikmin2_kogane_runtime import build as build_fixture_base
from experimental.pikmin2_kogane_runtime import instrument as instrument_base
from experimental.pikmin2_kogane_runtime import run as run_fixture_base

IDS = (219001, 219002, 219003)
SPENT = 219001     # reaches the flip cap in the first pass; restored escaped
SURVIVOR = 219002  # partial flips; restored at its count
UNTOUCHED = 219003 # never flipped; must not emit a restore line

APP = r'''class RoomApp : public PlugPikiApp {
 int observed=0,frames=0;
 Teki* beetles[3]={nullptr,nullptr,nullptr};
 void press(Teki* actor,Navi* n){if(!actor)return;InteractPress p(n,0.0f);actor->stimulate(p);}
 bool aliveTeki(unsigned id){Iterator it(tekiMgr);CI_LOOP(it){Teki* a=static_cast<Teki*>(*it);if(a&&a->mGenerator&&a->mGenerator->_70==id&&a->isAlive())return true;}return false;}
 void reenter(){pc_p2_kogane_reset();pc_p2_kogane_setup();std::printf("P2_KOGANE_REENTRY reset_setup=2\n");std::fflush(stdout);}
 public:int idle() override {
  int result=PlugPikiApp::idle();require(++frames<20000,"beetle reentry timeout");
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr)return result;
  Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
  ++observed;
  if(observed==1){
   for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i); // suppress one-shot discovery cutscenes
   std::ifstream input("kogane-positions.txt");unsigned id;float x,y,z;int count=0;
   while(input>>id>>x>>y>>z){
    Teki* actor=nullptr;int matches=0;Iterator iter(tekiMgr);CI_LOOP(iter){Teki* a=static_cast<Teki*>(*iter);if(a->mGenerator&&a->mGenerator->_70==id){actor=a;++matches;}}
    require(matches==1,"beetle roster identity");
    std::printf("P2_KOGANE_BIRTH id=%u type=%d x=%.3f y=%.3f z=%.3f\n",id,actor->mTekiType,x,y,z);
    if(id>=219001&&id<=219003)beetles[id-219001]=actor;
    ++count;}
   require(count==4,"beetle roster missing");}
  // Two flips on Kogane and one on Wealthy; the third Kogane press and the
  // reset+setup happen together, before the pending escape can finalize.
  if(observed==90||observed==180)press(beetles[0],n);
  if(observed==90)press(beetles[1],n);
  if(observed==270){press(beetles[0],n);reenter();}
  if(observed==280){
   require(!aliveTeki(219001),"restored spent beetle still present");
   require(aliveTeki(219002),"restored surviving beetle missing");
   require(aliveTeki(219003),"untouched beetle missing");
   std::puts("PASS P2_KOGANE_REENTRY restored2 escaped1");std::fflush(stdout);std::_Exit(0);}
  std::fflush(stdout);return result;
 }};
'''

INCLUDES = ('#include <map>\n#include "Demo.h"\n#include "Interactions.h"\n'
            '#include "PelletView.h"\n#include "PlayerState.h"\n'
            '#include "pc_p2_kogane.h"\n')


def validate(text, code):
    """Validate a re-entry run log against the restored-flip contract.

    Accepts only a clean completion where exactly Kogane at the cap is reported
    escaped, Wealthy resumes at one flip and the untouched Doodlebug emits no
    restore line.
    """
    births = [int(b) for b in re.findall(r'P2_KOGANE_BIRTH id=(\d+)', text)]
    restored = sorted((int(g), int(n)) for g, n in re.findall(
        r'P2_KOGANE_FLIPS_RESTORED generator=(\d+) flips=(\d+)', text))
    escaped = sorted((int(g), int(n)) for g, n in re.findall(
        r'P2_KOGANE_RESTORED_ESCAPE generator=(\d+) flips=(\d+)', text))
    checks = dict(
        completion=code == 0 and 'PASS P2_KOGANE_REENTRY restored2 escaped1' in text,
        births=births == list(IDS) + [219004],
        reset_setup='P2_KOGANE_REENTRY reset_setup=2' in text,
        restored=restored == [(SPENT, MAX_FLIPS), (SURVIVOR, 1)],
        restored_escape=escaped == [(SPENT, MAX_FLIPS)],
        untouched=UNTOUCHED not in {g for g, _ in restored})
    return dict(passed=all(checks.values()), checks=checks,
                restored={str(g): n for g, n in restored},
                restored_escape=[list(row) for row in escaped],
                unmeasured=['full scene/day reload (in-process reset/re-entry only)',
                            'native treasure override / cave relocation (disabled: P1 host)',
                            'cross-process save bridge (lane 01/06)'])


def build(native, build_dir, output, head, resume=False):
    return build_fixture_base(native, build_dir, output, head, resume, app=INCLUDES + APP)


def run(assets, bank, output, exe):
    return run_fixture_base(assets, bank, output, exe,
                            sidecar=native_sidecar(bank), validator=validate)


def instrument(source):
    return instrument_base(source, INCLUDES + APP)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build')
    r = sub.add_parser('run')
    for n in ('native', 'build-dir', 'output'):
        b.add_argument('--' + n, type=Path, required=True)
    b.add_argument('--head', required=True)
    b.add_argument('--resume', action='store_true')
    for n in ('assets', 'bank', 'output', 'exe'):
        r.add_argument('--' + n, type=Path, required=True)
    a = p.parse_args()
    if a.command == 'build':
        build(a.native, a.build_dir, a.output, a.head, a.resume)
    else:
        run(a.assets, a.bank, a.output, a.exe)
