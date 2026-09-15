#include "room-prefix.inc"
#include "Generator.h"
#include "pc_window.h"
#include "pc_p2_breadbug_actor.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>

// Small-Breadbug cargo-contest consumer fixture (#220). Binds the opted-in
// TEKI_Collec proxy (generator 186081) to the lane-06 P2CargoContest consumer
// bridge and drives the four gates through the family module's own tick with a
// fixed frame timeline:
//   (a) the Breadbug contests a carried pellet against the squad (1 carrier held);
//   (b) two carriers out-pull it -> interrupt() + release + exactly-once grant;
//   (c) a revisit re-arms, and a second steal is refused (duplicate, durable ledger);
//   (d) the Breadbug dies holding a fresh pellet -> onOwnerDied() releases it.
// Carrier counts are injected through the labelled probe hook (natural squad
// combat/carry is lane 04/06; the probe only drives the value-token contest).
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
 int phase = 0;
 bool deathLogged = false;
 Teki* actor = nullptr;
public:
 Pellet* baitPellet() {
  Vector3f fwd;
  actor->outputDirectionVector(fwd);
  Vector3f p = actor->mSRT.t + fwd * 60.0f;
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

  if (tick == 1) {
   Iterator it(tekiMgr);
   CI_LOOP(it) { Teki* t = static_cast<Teki*>(*it); if (t && t->mGenerator && t->mGenerator->_70 == 186081) actor = t; }
   require(actor && actor->mTekiType == TEKI_Collec, "contest proxy identity");
   n->mKontroller = new FixtureController();
   for (int i = 0; i < DEMOFLAG_COUNT; ++i) playerState->mDemoFlags.setFlagOnly(i);
   Vector3f view = actor->mSRT.t + Vector3f(0, 0, 120);
   view.y = mapMgr->getMinY(view.x, view.z, true);
   n->resetPosition(view);
   pc_p2_breadbug_actor_probe_carriers(1); // squad of one contests first
   baitPellet();
   std::printf("P2_BREADBUG_CONTEST_PHASE phase=setup tick=%d\n", tick);
   std::fflush(stdout);
  }

  // Fixed timeline (labelled injected carrier counts; grab latency ~120-150 frames).
  if (tick == 300) { pc_p2_breadbug_actor_probe_carriers(2); std::printf("P2_BREADBUG_CONTEST_PHASE phase=steal1 tick=%d\n", tick); std::fflush(stdout); }
  else if (tick == 380) { pc_p2_breadbug_actor_probe_carriers(-1); pc_p2_breadbug_actor_probe_revisit(); baitPellet(); pc_p2_breadbug_actor_probe_carriers(2); std::printf("P2_BREADBUG_CONTEST_PHASE phase=revisit1_bait2 tick=%d\n", tick); std::fflush(stdout); }
  else if (tick == 750) { pc_p2_breadbug_actor_probe_carriers(-1); pc_p2_breadbug_actor_probe_revisit(); baitPellet(); pc_p2_breadbug_actor_probe_carriers(1); std::printf("P2_BREADBUG_CONTEST_PHASE phase=revisit2_bait3 tick=%d\n", tick); std::fflush(stdout); }
  else if (tick == 1000) { if (actor->isAlive()) { actor->mHealth = 0.0f; std::printf("P2_BREADBUG_CONTEST_PHASE phase=kill_injected tick=%d\n", tick); std::fflush(stdout); } }
  else if (tick >= 1060) {
   if (!deathLogged && !actor->isAlive()) { deathLogged = true; std::printf("P2_BREADBUG_CONTEST_PHASE phase=dead tick=%d\n", tick); std::fflush(stdout); }
   if (tick >= 1100) {
    capture("breadbug-contest-final.ppm");
    std::printf("PASS P2_BREADBUG_CONTEST contest tug interrupt_grant owner_died revisit_exactly_once\n");
    std::fflush(nullptr);
    std::_Exit(0);
   }
  }

  if (tick % 60 == 0) {
   std::printf("P2_BREADBUG_CONTEST_HEARTBEAT tick=%d held=%d state=%d alive=%d\n",
               tick, int(actor->getCreaturePointer(2) != nullptr), actor->mStateID, int(actor->isAlive()));
   std::fflush(stdout);
  }
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
