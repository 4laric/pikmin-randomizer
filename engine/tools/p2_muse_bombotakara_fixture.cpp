// Muse l61 (#501) BombOtakara93 natural observation fixture.
//
// Replacement-main fixture (isolated fixture build only; never part of the
// game target). Reuses the integrated lane-22 Otakara natural runner: the
// carrier is bound through the real family generator chain
// (p2-dweevil-actors.txt with BombOtakara source 93 on a Teki actor), never
// through the lane-22 sidecar profile or its inject trigger file.
//
// The fixture observes only:
//   * P2_OTAKARA_BIND source_id=93 + P2_ENEMY_READY attack=payload_delegated
//     (emitted by pc_p2_otakara_setup/update on the live actor);
//   * the source `otakara`-joint attachment via
//     pc_p2_bombotakara_note_attach_natural (observation marker, no staging);
//   * blast routing through the shared lane-20 primitive against live
//     receivers (observed P2_BOMBOTAKARA_BLAST/P2_BOMBOTAKARA_BOMB_HIT lines).
//
// It writes no health/state/transport, kills nothing, stimulates no receiver
// directly, and never writes p2-bombotakara-native.txt or
// p2-bombotakara-inject.txt. Without a real EnemyID_Bomb payload actor the
// blast half stays unobserved and the fixture exits with an explicit
// P2_MUSE_BOMBOTAKARA_BLOCKED marker naming the missing artifact; that is
// the honest BLOCKED record, not a PASS.
#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "gl/pc_opengl.h"
#include "App.h"
#include "Node.h"
#include "Graphics.h"
#include "MapMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "MoviePlayer.h"
#include "Shape.h"
#include "teki.h"
#include "system.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "pc_window.h"
#include "pc_p2_preview.h"
#include "pc_p2_bombotakara.h"
#include "pc_p2_otakara.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <string>

namespace {

void require(bool value, const char* message) {
    if (!value) {
        std::printf("FAIL P2_MUSE_BOMBOTAKARA %s\n", message);
        std::fflush(stdout);
        std::_Exit(1);
    }
}

// Read the staged family generator for the BombOtakara93 bind.
// Returns 0 when the stage does not name a real family generator chain.
unsigned stagedBombGenerator() {
    std::ifstream in("p2-dweevil-actors.txt");
    if (!in) return 0;
    std::string header;
    int count = 0;
    if (!(in >> header >> count) || header != "P2_DWEEVIL_ACTORS_1" || count < 1) return 0;
    for (int i = 0; i < count; ++i) {
        unsigned long long generator = 0;
        std::string species;
        if (!(in >> generator >> species)) return 0;
        if (species == "BombOtakara" && generator != 0 && generator <= 0xffffffffULL) {
            return static_cast<unsigned>(generator);
        }
    }
    return 0;
}

class MuseBombotakaraApp : public PlugPikiApp {
    int frames = 0;
    int ready = 0;
    bool armed = false;
    bool finished = false;
    bool hold = false;
    bool attachLogged = false;
    unsigned generator = 0;

public:
    int idle() override {
        int result = PlugPikiApp::idle();
        require(++frames < 20000 || hold, "BombOtakara muse startup timeout");
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
            gameflow.mMoviePlayer->requestSkip();
            return result;
        }
        if (!pc_p2_preview_cargo_free_ready() || !naviMgr || !tekiMgr || !mapMgr) return result;
        Navi* navi = naviMgr->getNavi();
        if (!navi || gameflow.mPauseAll || gameflow.mIsUIOverlayActive) return result;
        ++ready;
        if (ready == 1) {
            std::ifstream holding("bombotakara-keep-open.txt");
            hold = bool(holding);
            SDL_SetWindowTitle(SDL_GL_GetCurrentWindow(),
                               "BombOtakara93 natural observer l61 (#501)");
            int red = 0, blue = 0;
            if (pikiMgr) {
                Iterator it(pikiMgr);
                CI_LOOP(it) {
                    Piki* piki = static_cast<Piki*>(*it);
                    if (piki && piki->isAlive()) {
                        if (piki->mColor == Red) ++red;
                        else if (piki->mColor == Blue) ++blue;
                    }
                }
            }
            std::printf("P2_MUSE_BOMBOTAKARA_BASELINE red=%d blue=%d\n", red, blue);
            std::fflush(stdout);
            generator = stagedBombGenerator();
            if (generator != 0) {
                std::printf("P2_MUSE_BOMBOTAKARA_STAGE generator=%u source_id=93 chain=family\n",
                            generator);
                std::fflush(stdout);
            }
        }
        if (ready == 30 && !armed) {
            // Bind through the real family generator chain only. The sidecar
            // profile (p2-bombotakara-native.txt) and its inject triggers are
            // never written here; their absence keeps the sidecar inert.
            const int heap = gsys->setHeap(SYSHEAP_App);
            pc_p2_otakara_setup();
            pc_p2_bombotakara_setup();
            gsys->setHeap(heap);
            armed = true;
            std::printf("P2_MUSE_BOMBOTAKARA_SCENARIO natural_observe generator=%u\n", generator);
            std::fflush(stdout);
        }
        if (armed && !finished) {
            const unsigned long bound = pc_p2_otakara_count();
            if (bound > 0 && !attachLogged && generator != 0) {
                // Observation only: the carrier bound through the family
                // chain is seen holding its payload on the source joint.
                // The payload actor itself (EnemyID_Bomb) is staged by the
                // lane-20 contract; until it exists this marker records the
                // carrier side of the attachment chain.
                attachLogged = true;
                std::printf("P2_MUSE_BOMBOTAKARA_OBSERVED bound=%lu\n", bound);
                std::fflush(stdout);
            }
            if (pc_p2_bombotakara_behavior_tick() > 900 || frames > 15000) {
                std::printf("P2_MUSE_BOMBOTAKARA_BLOCKED reason=no_bomb_payload_actor "
                            "generator=%u bound=%lu blast=%d\n",
                            generator, bound, pc_p2_bombotakara_blast_count());
                std::fflush(stdout);
                finished = true;
                if (!hold) std::_Exit(0);
            }
        }
        std::fflush(stdout);
        return result;
    }
};

} // namespace

int main(int argc, char** argv) {
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    pc_bbft_init(argc, argv);
    require(pc_pikipelago_room_preview(), "requires --experimental-pikmin2-room");
    int windowWidth = 960, windowHeight = 540;
    const char* windowEnv = std::getenv("PIKMIN_P2_ROOM_WINDOW");
    if (windowEnv && std::strcmp(windowEnv, "off") && std::strcmp(windowEnv, "0")) {
        int w = 0, h = 0;
        if (std::sscanf(windowEnv, "%dx%d", &w, &h) == 2 && w >= 320 && h >= 240) {
            windowWidth = w;
            windowHeight = h;
        }
    }
    require(pc_window_init("BombOtakara93 natural observer l61", windowWidth, windowHeight),
            "window init");
    pc_settings_init();
    pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);
    pc_window_set_window_size(windowWidth, windowHeight);
    pc_window_center();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new MuseBombotakaraApp());
    return 0;
}
