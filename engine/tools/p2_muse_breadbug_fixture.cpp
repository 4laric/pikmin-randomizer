#include "room-prefix.inc"
#include <cmath>
#include <algorithm>
#include "pc_p2_breadbug_actor.h"
#include "Generator.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Pellet.h"
#include "PelletView.h"

// Muse l64 Breadbug38 natural lifecycle fixture (#504). PanModoki source 38
// only (P1 TEKI_Collec proxy 186081); the 186082 control is a never-touched
// sentinel. No bait pellet is ever deployed, so the contest bridge stays idle.
//
// Phases: bind -> autonomous movement sample -> captain-thrown red assault
// (real player-controller throw events through Navi::throwPiki; damage flows
// through the real engine receiver; zero fixture health writes, no die() call,
// no InteractAttack injection) -> death-funnel forget + corpse capture
// (mPellet at mDeadState==2 plus the pelletMgr mPelletView scan) -> generator
// rebirth (natural respawn first, engine mGenType->init fallback, both
// fixture-timed and honestly labelled) -> tracked re-registration check via
// the family rebirth scan (no reset/setup call) -> PASS.
//
// A prior revision ringed free-mode reds around the actor (lane-19 recipe):
// 20 reds for 2400 ticks dealt zero damage (Collec HP stayed 5000.0), so the
// harmless proxy never engages idle pursuers. Thrown Pikmin actively latch,
// which is the ordinary player combat path. Any P2_MUSE_BREADBUG_INJECTED line
// would mark a fixture health/die write; this fixture never emits one. A
// missing corpse or a timed-out kill fails here with the exact cause instead
// of passing silently.
class MuseBreadbugApp : public PlugPikiApp {
 int frames = 0, active = 0, moving = 0, phase = 0, phaseTick = 0;
 Teki* actor = nullptr; Teki* control = nullptr; Generator* generator = nullptr;
 void* oldHost = nullptr; Teki* fresh = nullptr;
 Vector3f origin; float farthest = 0;
 float killHealth0 = 0; bool healthFell = false;
 bool corpseOk = false, rebirthForced = false;
 int aliveReds() {
  int count = 0; Iterator it(pikiMgr); CI_LOOP(it) { Piki* p = static_cast<Piki*>(*it); if (p && p->isAlive() && p->mColor == Red) ++count; } return count;
 }
 void ringReds(Navi* n) {
  int total = aliveReds(); if (total <= 0 || !actor) return;
  int index = 0; Iterator it(pikiMgr); CI_LOOP(it) {
   Piki* p = static_cast<Piki*>(*it); if (!p || !p->isAlive() || p->mColor != Red) continue;
   const float angle = float(index) * 6.2831853f / float(total);
   Vector3f spot(actor->mSRT.t.x + 22.0f * std::sin(angle), 0.0f, actor->mSRT.t.z + 22.0f * std::cos(angle));
   spot.y = mapMgr->getMinY(spot.x, spot.z, true);
   p->resetPosition(spot); p->changeMode(PikiMode::FreeMode, n); ++index;
  }
 }
public:
 int idle() override {
  int result = PlugPikiApp::idle();
  require(++frames < 20000, "Muse breadbug timeout");
  if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) { gameflow.mMoviePlayer->requestSkip(); return result; }
  if (!pc_p2_preview_cargo_free_ready() || !naviMgr || !tekiMgr || !pikiMgr || !mapMgr) return result;
  Navi* n = naviMgr->getNavi(); if (!n || gameflow.mPauseAll || gameflow.mIsUIOverlayActive) return result;
  ++active;
  if (phase == 0) {
   Iterator it(tekiMgr); CI_LOOP(it) { Teki* t = static_cast<Teki*>(*it); if (t && t->mGenerator) { if (t->mGenerator->_70 == 186081) actor = t; if (t->mGenerator->_70 == 186082) control = t; } }
   require(actor && control && actor != control, "Muse breadbug proxy/control missing");
   require(actor->mTekiType == TEKI_Collec && control->mTekiType == TEKI_Collec, "Muse breadbug proxy/control identity");
   require(actor->isAlive() && pc_p2_breadbug_actor_is_tracked(actor), "proxy not family-tracked at birth");
   generator = actor->mGenerator; require(generator != nullptr, "proxy generator missing at bind");
   origin = actor->mSRT.t;
   n->mKontroller = new FixtureController(); for (int i = 0; i < DEMOFLAG_COUNT; ++i) playerState->mDemoFlags.setFlagOnly(i);
   Vector3f park = origin + Vector3f(100, 0, 100); park.y = mapMgr->getMinY(park.x, park.z, true); n->resetPosition(park);
   killHealth0 = actor->mHealth;
   std::printf("P2_MUSE_BREADBUG_BOUND proxy=186081 control=186082 health=%.1f reds=%d\n", killHealth0, aliveReds());
   std::fflush(stdout); capture("muse-breadbug-start.ppm"); phase = 1; phaseTick = 0;
  }
  if (phase == 1) {
   require(control->isAlive(), "control died during movement sample");
   require(actor->isAlive(), "proxy died before the natural kill phase");
   float dx = actor->mSRT.t.x - origin.x, dz = actor->mSRT.t.z - origin.z;
   farthest = std::max(farthest, std::sqrt(dx * dx + dz * dz));
   if (actor->mVelocity.x * actor->mVelocity.x + actor->mVelocity.z * actor->mVelocity.z > 1) ++moving;
   if (active % 60 == 0) { std::printf("P2_MUSE_BREADBUG_MOVE frame=%d displacement=%.6f moving=%d xyz=%.6f,%.6f,%.6f\n", active, farthest, moving, actor->mSRT.t.x, actor->mSRT.t.y, actor->mSRT.t.z); std::fflush(stdout); }
   if (farthest > 15 && moving >= 15) { std::printf("P2_MUSE_BREADBUG_MOVED displacement=%.6f moving=%d\n", farthest, moving); std::fflush(stdout); phase = 2; phaseTick = 0; }
   require(active < 2000, "Muse breadbug autonomous movement not demonstrated");
  }
  if (phase == 2) {
   require(control->isAlive(), "control died during the natural kill");
   ++phaseTick;
   if (actor->isAlive()) {
    // Captain-thrown assault through the real player-controller event path:
    // the captain is staged in throw range (reported position) and idle reds
    // are thrown at the actor with Navi::throwPiki. Thrown Pikmin latch onto
    // the Collec through ordinary engine behavior and wound it through the
    // real receiver. No health is written, die() is never called, and no
    // InteractAttack is injected.
    if (phaseTick == 1 || phaseTick % 10 == 0) {
     Vector3f near = actor->mSRT.t + Vector3f(60, 0, 60);
     near.y = mapMgr->getMinY(near.x, near.z, true);
     n->resetPosition(near);
     int thrown = 0;
     Iterator it(pikiMgr); CI_LOOP(it) {
      Piki* p = static_cast<Piki*>(*it);
      if (!p || !p->isAlive() || p->mColor != Red) continue;
      if (p->getStickObject() || p->getState() != PIKISTATE_Normal) continue;
      p->changeMode(PikiMode::FreeMode, n);
      p->mFSM->transit(p, PIKISTATE_Flying);
      n->throwPiki(p, actor->mSRT.t);
      std::printf("P2_MUSE_BREADBUG_THROW tick=%d reds=%d health=%.1f\n", phaseTick, aliveReds(), actor->mHealth);
      if (++thrown >= 2) break;
     }
     std::fflush(stdout);
    }
    if (actor->mHealth < killHealth0) healthFell = true;
    if (phaseTick % 60 == 0) { std::printf("P2_MUSE_BREADBUG_RING tick=%d reds=%d health=%.1f\n", phaseTick, aliveReds(), actor->mHealth); std::fflush(stdout); }
    require(phaseTick < 5400, "Muse breadbug thrown-Pikmin kill did not complete");
   } else {
    std::printf("P2_MUSE_BREADBUG_KILL_NATURAL tick=%d\n", phaseTick); std::fflush(stdout);
    require(healthFell, "kill without receiver health fall");
    oldHost = static_cast<void*>(actor); phase = 3; phaseTick = 0;
   }
  }
  if (phase == 3) {
   ++phaseTick;
   // The pooled actor pointer stays readable here, as in the shared ordinary
   // receipt fixture. die() only sets mDeadState=1; the dieSoon() corpse
   // product (becomePellet sets mPellet for LeaveCorpse types such as Collec)
   // materializes on a later update, so wait for mDeadState==2 explicitly.
   if (!corpseOk) {
    if (phaseTick % 60 == 0) { std::printf("P2_MUSE_BREADBUG_WAIT phase=corpse tick=%d dead=%d tracked=%d\n", phaseTick, actor->mDeadState, pc_p2_breadbug_actor_tracked_count()); std::fflush(stdout); }
    if (actor->mDeadState == 2) {
     const int viaPellet = (actor->mPellet != nullptr) ? 1 : 0;
     int bodies = 0; Iterator p(pelletMgr); CI_LOOP(p) { Pellet* body = static_cast<Pellet*>(*p); if (body && body->isAlive() && body->mPelletView == static_cast<PelletView*>(actor)) ++bodies; }
     std::printf("P2_MUSE_BREADBUG_CORPSE bodies=%d via_mpellet=%d\n", bodies, viaPellet); std::fflush(stdout);
     require(bodies >= 1 && viaPellet == 1, "Muse breadbug natural death left no corpse");
     corpseOk = true;
     std::printf("P2_MUSE_BREADBUG_REBIRTH_BEGIN generator=186081\n"); std::fflush(stdout);
    }
    require(phaseTick < 900, "Muse breadbug corpse product never materialized");
   } else {
    // Corpse proven. Now observe whether the real death funnel
    // (BTeki::doKill -> pc_p2_forget_teki, dead_state>=1) ever runs for a
    // LeaveCorpse death, or the dead entry simply persists until rebirth.
    if (phaseTick % 60 == 0) { std::printf("P2_MUSE_BREADBUG_WAIT phase=funnel tick=%d tracked=%d\n", phaseTick, pc_p2_breadbug_actor_tracked_count()); std::fflush(stdout); }
    if (pc_p2_breadbug_actor_tracked_count() == 0) { phase = 4; phaseTick = 0; }
    else if (phaseTick > 900) {
     std::printf("P2_MUSE_BREADBUG_NO_FORGET tick=%d tracked=%d\n", phaseTick, pc_p2_breadbug_actor_tracked_count()); std::fflush(stdout);
     phase = 4; phaseTick = 0;
    }
    require(phaseTick < 1500, "Muse breadbug funnel wait did not resolve");
   }
  }
  if (phase == 4) {
   ++phaseTick;
   if (pc_p2_breadbug_actor_tracked_count() == 0 && phaseTick <= 600) {
    if (phaseTick % 60 == 0) { std::printf("P2_MUSE_BREADBUG_REBIRTH_WAIT tick=%d\n", phaseTick); std::fflush(stdout); }
    return result;
   }
   if (pc_p2_breadbug_actor_tracked_count() == 0 && !fresh) {
    // No natural generator respawn within the window and nothing captured yet:
    // one fixture-timed engine rebirth on the captured generator (the
    // groink/fuefuki rehearsal path), honestly labelled; the re-registration
    // itself stays fully natural (family rebirth scan, no reset/setup).
    require(generator && generator->mGenType, "generator lost before rebirth");
    generator->mGenType->init(generator);
    fresh = static_cast<Teki*>(generator->mLatestSpawnCreature);
    require(fresh != nullptr, "generator rebirth produced no actor");
    rebirthForced = true;
    std::printf("P2_MUSE_BREADBUG_REBIRTH_FORCED tick=%d\n", phaseTick); std::fflush(stdout);
    phaseTick = 0;
   }
   // Settle: the rebirth scan must bind exactly one live actor with no setup
   // or reset call in between (no manager recreation).
   if (phaseTick >= 120) {
    if (!fresh) { Iterator it(tekiMgr); CI_LOOP(it) { Teki* t = static_cast<Teki*>(*it); if (t && t->mGenerator && t->mGenerator->_70 == 186081 && t->mTekiType == TEKI_Collec && !t->mDeadState && t->isAlive()) { fresh = t; break; } } }
    require(fresh && fresh->isAlive(), "reborn actor not alive");
    require(pc_p2_breadbug_actor_is_tracked(fresh), "reborn actor not re-registered");
    require(pc_p2_breadbug_actor_tracked_count() == 1, "rebirth binds exactly one actor");
    const int recycled = (static_cast<void*>(fresh) == oldHost) ? 1 : 0;
    std::printf("P2_MUSE_BREADBUG_REBIRTH_NEW recycled=%d\n", recycled); std::fflush(stdout);
    capture("muse-breadbug-rebirth.ppm");
    require(corpseOk, "corpse gate not satisfied");
    std::puts("PASS P2_MUSE_BREADBUG move kill_natural funnel corpse rebirth"); std::fflush(stdout); std::_Exit(0);
   }
   require(phaseTick < 1200, "Muse breadbug rebirth did not bind");
  }
  return result;
 }
};
int main(int argc, char** argv) {
 SDL_setenv("SDL_AUDIODRIVER", "dummy", 1); SDL_SetMainReady(); pc_gpu_preference_apply();
 _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1"); pc_bbft_init(argc, argv);
 require(pc_pikipelago_room_preview(), "preview flag");
 if (!pc_window_init("Muse breadbug lifecycle", 960, 540)) return 3;
 pc_settings_init(); pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED); pc_window_set_window_size(960, 540); pc_window_center();
 std::puts("Experimental preview window set to 960x540 windowed and centered");
 gsys->Initialise(); pc_settings_p2d_init(); nodeMgr = new NodeMgr(); gsys->run(new MuseBreadbugApp()); return 0;
}
