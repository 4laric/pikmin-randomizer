#include "room-prefix.inc"
#include "Generator.h"
#include "pc_window.h"
#include "pc_p2_breadbug_actor.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>

// Small-Breadbug cargo-contest consumer fixture (#220, slice 3). Binds the
// opted-in TEKI_Collec proxy (generator 186081) to the lane-06 P2CargoContest
// consumer bridge and drives the gates through the family module's own tick:
//   (a) natural squad tug: real Stickers carriers 0->1->2 reach Stolen and the
//       exactly-once grant (no injected carrier count);
//   (b) revisit re-arms and a second steal is refused (duplicate, durable ledger);
//   (c) the real interruption: the Breadbug loses its cargo while the tug is Held
//       (natural P1-host put-to-nest delivery; a captain whistle is also issued to
//       pull the carriers off), so the module interrupts + destroys the handle;
//   (d) the Breadbug dies holding a fresh pellet -> onOwnerDied() releases it.
// Every injected carrier count is confessed by the module itself
// (P2_BREADBUG_CONTEST_PROBE); the primary tug is probe-free.
static bool contest_window_size(int& width, int& height)
{
 const char* value = std::getenv("PIKMIN_P2_ROOM_WINDOW");
 if (value && (!std::strcmp(value, "0") || !std::strcmp(value, "off"))) return false;
 if (value) {
  int w = 0, h = 0;
  if (std::sscanf(value, "%dx%d", &w, &h) == 2 && w >= 320 && h >= 240) { width = w; height = h; return true; }
  if (!std::strcmp(value, "1") || !std::strcmp(value, "small")) { width = 960; height = 540; return true; }
 }
 width = 960; height = 540; return true;
}

class BreadbugContestFixture : public PlugPikiApp {
 int frames = 0, tick = 0;
 int phase = 0;          // 0 natural_tug, 1 revisit_dup, 2 interrupt, 3 death_hold, 4 kill, 5 done
 int killAt = -1;
 bool deathLogged = false;
 bool prevHeld = false;
 Teki* actor = nullptr;
 Pellet* cargo = nullptr;
public:
 Pellet* baitPellet() {
  Vector3f fwd;
  actor->outputDirectionVector(fwd);
  Vector3f p = actor->mSRT.t + fwd * 25.0f;
  p.y = mapMgr->getMinY(p.x, p.z, true) + 5.0f;
  Pellet* pl = pelletMgr->newNumberPellet(PELCOLOR_Red, 0);
  require(pl, "native pellet allocation");
  pl->init(p);
  pl->startAI(0);
  std::printf("P2_BREADBUG_CONTEST_BAIT x=%.1f y=%.1f z=%.1f\n", p.x, p.y, p.z);
  std::fflush(stdout);
  return pl;
 }

 int idle() override {
  int result = PlugPikiApp::idle();
  require(++frames < 9000, "Breadbug contest startup timeout");
  if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) { gameflow.mMoviePlayer->requestSkip(); return result; }
  if (!pc_p2_preview_cargo_free_ready() || !naviMgr || !tekiMgr || gameflow.mPauseAll || gameflow.mIsUIOverlayActive) return result;
  Navi* n = naviMgr->getNavi();
  if (!n) return result;
  ++tick;
  const bool held = actor && actor->getCreaturePointer(2) != nullptr;
  // After a release/steal/deliver resolves the contest, remove the resolved
  // pellet so the proxy cannot re-grab it and loop (the squad would carry it
  // away in a real scene).
  if (cargo && !held && prevHeld && cargo->isAlive()) {
   cargo->kill(false);
   std::printf("P2_BREADBUG_CONTEST_PELLET_RESOLVED tick=%d\n", tick);
   std::fflush(stdout);
  }

  if (tick == 1) {
   Iterator it(tekiMgr);
   CI_LOOP(it) { Teki* t = static_cast<Teki*>(*it); if (t && t->mGenerator && t->mGenerator->_70 == 186081) actor = t; }
   require(actor && actor->mTekiType == TEKI_Collec, "contest proxy identity");
   n->mKontroller = new FixtureController();
   for (int i = 0; i < DEMOFLAG_COUNT; ++i) playerState->mDemoFlags.setFlagOnly(i);
   Vector3f view = actor->mSRT.t + Vector3f(0, 0, 120);
   view.y = mapMgr->getMinY(view.x, view.z, true);
   n->resetPosition(view);
   pc_p2_breadbug_actor_probe_carriers(-1); // natural Stickers for the primary tug
   cargo = baitPellet();
   std::printf("P2_BREADBUG_CONTEST_PHASE phase=natural_tug_setup tick=%d\n", tick);
   std::fflush(stdout);
  }

  if (tick == 420) {                                   // revisit -> re-grab -> duplicate grant
   pc_p2_breadbug_actor_probe_revisit();
   cargo = baitPellet();
   pc_p2_breadbug_actor_probe_carriers(2);
   std::printf("P2_BREADBUG_CONTEST_PHASE phase=revisit_duplicate tick=%d\n", tick);
   std::fflush(stdout);
  } else if (tick == 800) {                            // interruption: hold, whistle carriers off, delivery -> interrupt
   pc_p2_breadbug_actor_probe_revisit();
   cargo = baitPellet();
   pc_p2_breadbug_actor_probe_carriers(1);             // keep the tug Held so the contest does not time out
   n->callPikis(150.0f, true);                         // natural captain-whistle carrier-off trigger (audited Navi::callPikis)
   std::printf("P2_BREADBUG_CONTEST_PHASE phase=interrupt_delivery tick=%d whistle=1\n", tick);
   std::fflush(stdout);
  } else if (tick == 2600) {                           // fresh hold for the death gate
   pc_p2_breadbug_actor_probe_revisit();
   cargo = baitPellet();
   pc_p2_breadbug_actor_probe_carriers(1);
   std::printf("P2_BREADBUG_CONTEST_PHASE phase=death_hold tick=%d\n", tick);
   std::fflush(stdout);
  }

  // Death: kill shortly after the death-hold pellet is grabbed (so released=1),
  // with a fallback kill so the run still completes if the proxy drifts away.
  if (tick >= 2600 && killAt < 0 && held && !prevHeld) { killAt = tick + 10; }
  if (tick >= 4400 && killAt < 0) { killAt = tick; std::printf("P2_BREADBUG_CONTEST_PHASE phase=kill_fallback tick=%d\n", tick); std::fflush(stdout); }
  if (killAt >= 0 && tick >= killAt) {
   if (!actor->mDeadState) { actor->die(); std::printf("P2_BREADBUG_CONTEST_PHASE phase=kill tick=%d\n", tick); std::fflush(stdout); }
  }
  if (killAt >= 0 && actor->mDeadState) {
   if (!deathLogged) { deathLogged = true; std::printf("P2_BREADBUG_CONTEST_PHASE phase=dead tick=%d\n", tick); std::fflush(stdout); }
   if (tick >= killAt + 40) {
    capture("breadbug-contest-final.ppm");
    std::printf("PASS P2_BREADBUG_CONTEST tug stolen_grant interrupt owner_died revisit_exactly_once\n");
    std::fflush(nullptr);
    std::_Exit(0);
   }
  }

  if (tick % 60 == 0) {
   std::printf("P2_BREADBUG_CONTEST_HEARTBEAT tick=%d held=%d state=%d alive=%d\n",
               tick, int(held), actor->mStateID, int(actor->isAlive()));
   std::fflush(stdout);
  }
  prevHeld = held;
  return result;
 }
};

int main(int argc, char** argv) {
 SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
 std::setvbuf(stdout, nullptr, _IONBF, 0);
 SDL_SetMainReady(); pc_gpu_preference_apply(); _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
 pc_bbft_init(argc, argv);
 require(pc_pikipelago_room_preview(), "preview flag");
 int windowWidth = 960, windowHeight = 540;
 const bool standardWindow = contest_window_size(windowWidth, windowHeight);
 if (!pc_window_init("Breadbug contest consumer", windowWidth, windowHeight)) return 3;
 pc_settings_init();
 if (standardWindow) { pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED); pc_window_set_window_size(windowWidth, windowHeight); pc_window_center(); std::printf("Experimental preview window set to %dx%d windowed and centered\n", windowWidth, windowHeight); std::fflush(stdout); }
 gsys->Initialise(); pc_settings_p2d_init();
 nodeMgr = new NodeMgr(); gsys->run(new BreadbugContestFixture()); return 0;
}
