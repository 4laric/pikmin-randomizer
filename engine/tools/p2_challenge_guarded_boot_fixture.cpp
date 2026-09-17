// P1 Challenge guarded boot fixture (prerequisite lane, #649).
//
// Replacement-main RoomApp fragment: boots the engine with
// --experimental-challenge-level <0-4> (main entry below is patched by the
// lane builder to require the challenge flag instead of the room flag),
// runs the canonical captain guard FIRST on every idle call, parks the
// captain far outside attack reach, and observes/records the boot (selected
// stage identity, window, live squad). No generator, save, scoring or combat
// semantics; no gameplay claims. All runtime gates stay UNTESTED: PASS here
// means "boot observed", nothing more.
//
// Captain safety (#632): canonical scripts/p2_fixture_captain_guard.h sha256
// d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474,
// vendored below verbatim. The guard never changes game state.
//
// This file is a RoomApp fragment, not a standalone translation unit. The
// lane builder splices the marked sections into tools/preview_p2_room.cpp in
// a private output directory (additionally swapping the main entry require
// to the challenge flag) and links the provenance-checked fixture from
// there, so the base startup, window, audio and cargo plumbing is inherited
// unchanged.

// MUSE-CHALLENGE-BOOT-INCLUDES-BEGIN
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include "Demo.h"
#include "GameStat.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiAI.h"
#include "PikiState.h"
#include "PlayerState.h"
#include "pc_bbft.h"
// Vendored verbatim from scripts/p2_fixture_captain_guard.h (sha256 above);
// equivalent tested guard, observation-only.
inline bool p2_fixture_captain_down(bool orimaDead, bool deadState, float hp) {
    return orimaDead || deadState || !std::isfinite(hp) || hp <= 1.0f;
}
inline void p2_fixture_require_captain(bool orimaDead, bool deadState, float hp, int tick) {
    if (!p2_fixture_captain_down(orimaDead, deadState, hp)) return;
    std::printf("P2_FIXTURE_CAPTAIN_DOWN tick=%d hp=%.3f orima_dead=%d dead_state=%d outcome=BLOCKED\n",
                tick, hp, int(orimaDead), int(deadState));
    std::fflush(nullptr);
    std::_Exit(86); // interrupted observation, never a successful fixture exit
}
// MUSE-CHALLENGE-BOOT-INCLUDES-END

// MUSE-CHALLENGE-BOOT-APP-BEGIN
#include "GameStat.h"
class RoomApp : public PlugPikiApp {
 int observed=0,frames=0;
 bool staged=false,booted=false;
 int stuckMarks=0;
 int alivePikis(){int c=0;Iterator it(pikiMgr);CI_LOOP(it){Creature* p=*it;if(p&&p->isAlive())++c;}return c;}
 // #698: name the holding gate plus the live count on stuck ticks, so a
 // post-PARK freeze attributes itself instead of going silent. Called only on
 // early-return paths where observed does not advance.
 void gateDiag(const char* gate){
  if((frames%300)!=0||stuckMarks>=48)return;++stuckMarks;
  int alive=pikiMgr?alivePikis():-1;
  std::printf("P2_CHALLENGE_GATE_DIAG gate=%s observed=%d alive=%d frames=%d\n",gate,observed,alive,frames);std::fflush(stdout);}
 public:int idle() override {
  int result=PlugPikiApp::idle();require(++frames<20000,"challenge boot observer timeout");
  if(!naviMgr||!tekiMgr||!pikiMgr){gateDiag("managers");return result;}
  Navi* n=naviMgr->getNavi();if(!n){gateDiag("navi");return result;}
  p2_fixture_require_captain(GameStat::orimaDead,!n->isAlive(),n->mHealth,observed);
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gateDiag("movie");gameflow.mMoviePlayer->requestSkip();return result;}
  if(gameflow.mPauseAll||gameflow.mIsUIOverlayActive){gateDiag(gameflow.mPauseAll?"pause":"ui");return result;}
  ++observed;
  int level=pc_pikipelago_challenge_level();
  require(level>=0&&level<=4,"challenge boot fixture requires a selected level");
  if(observed==1){
   for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i); // suppress one-shot discovery cutscenes
   // Park the captain far outside attack reach (reported staging, not gameplay).
   Vector3f park(n->mSRT.t.x+600.0f,n->mSRT.t.y,n->mSRT.t.z);
   n->resetPosition(park);n->mVelocity.set(0,0,0);n->mTargetVelocity.set(0,0,0);
    staged=true;
    std::printf("P2_CHALLENGE_PARK nx=%.3f ny=%.3f nz=%.3f\n",park.x,park.y,park.z);std::fflush(stdout);
    // #698: alive count at PARK time, so a later freeze can be compared
    // against a known live baseline (separates never-spawned from frozen).
    std::printf("P2_CHALLENGE_PARK_ALIVE pikis=%d\n",alivePikis());std::fflush(stdout);}
  if(observed==60){int squad=alivePikis();std::printf("P2_CHALLENGE_SQUAD pikis=%d\n",squad);std::fflush(stdout);}
  if(staged&&!booted&&observed>=120){
   booted=true;
   std::printf("P2_CHALLENGE_BOOT level=%d slot=chal%d\n",level,level);std::fflush(stdout);}
  if(booted&&observed>=180){
   require(alivePikis()>=1,"squad extinct during boot observation");
   std::puts("PASS P2_CHALLENGE_GUARDED_BOOT boot1 squad_alive");std::fflush(stdout);std::_Exit(0);}
  std::fflush(stdout);return result;
 }};
// MUSE-CHALLENGE-BOOT-APP-END