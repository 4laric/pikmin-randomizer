// Private real-GL slice-3 runtime fixture for the BigTreasure ordinary loop
// (#246), built by scripts/build_pikmin2_fixture.py only. This fixture does NOT
// call pc_p2_bigtreasure_stimulate_piki / the receiver probe: it pins a live
// Navi and a few live Pikmin inside the boss's attack box and lets the ORDINARY
// loop (pc_p2_hardlanes_update) reach a real weapon Attack, emit the element, and
// apply it through the real receiver (the loop's own queryHit + handled set +
// stimulate path). It then posts ONE flagged injected max-health hit against the
// chosen (elec) weapon to observe the FSM's weapon-loss re-pick.
//
// The 960x540 centred window and the live starting squad are asserted at boot.
// Teleporting the Navi/Pikmin near the boss is a fixture intervention (labelled).

#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "gl/pc_opengl.h"
#include "App.h"
#include "Node.h"
#include "Graphics.h"
#include "MapMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "MoviePlayer.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "system.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "pc_window.h"
#include "pc_p2_preview.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "pc_p2_hardlanes.h"
#include "pc_p2_bigtreasure.h"
#include "pc_p2_species.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace {

void require(bool value, const char* message)
{
    if (!value) {
        std::printf("FAIL BIGTREASURE_SLICE3 %s\n", message);
        std::fflush(stdout);
        std::_Exit(1);
    }
}

class Slice3App final : public PlugPikiApp {
    int frames = 0;
    int squad = 0;
    bool setup = false;
    bool sentKnock = false;
    bool sawRepick = false;
    bool injectedBlue = false;
    int phase = -1;
    int lastPhase = -1;
    int framesInAttack = 0;
    int repickFrames = 0;
    Piki* bluePiki = nullptr;
    float ground = 0.0f;

public:
    int idle() override
    {
        int result = PlugPikiApp::idle();
        require(++frames < 3600, "timeout");
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
            gameflow.mMoviePlayer->requestSkip();
            return result;
        }
        if (!pc_p2_preview_ready() || !naviMgr || !naviMgr->getNavi() || gameflow.mPauseAll
            || gameflow.mIsUIOverlayActive) {
            return result;
        }
        if (!setup) {
            SDL_Window* window = SDL_GL_GetCurrentWindow();
            require(window != nullptr, "window");
            int w = 0, h = 0, x = 0, y = 0;
            SDL_GetWindowSize(window, &w, &h);
            SDL_GetWindowPosition(window, &x, &y);
            require(w == 960 && h == 540, "window size 960x540");
            std::printf("P2_BIGTREASURE_WINDOW size=%dx%d pos=%d,%d\n", w, h, x, y);
            ground = mapMgr->getMinY(0, 0, false);
            require(std::isfinite(ground), "center ground unavailable");
            squad = countSquad();
            require(squad >= 20, "live starting squad (>=20)");
            std::printf("P2_BIGTREASURE_SLICE3_SQUAD alive=%d\n", squad);
            require(pc_p2_hardlanes_bigtreasure_ready(), "ordinary seam active");
            // Inject one Blue Pikmin (flagged: the squad is all Red) so a
            // non-immune target is available for the fire receiver.
            if (pikiMgr) {
                Iterator it(pikiMgr);
                CI_LOOP(it) {
                    Piki* piki = static_cast<Piki*>(*it);
                    if (piki && piki->isAlive()) {
                        pc_p2_set_species(piki, P2SpeciesBlue);
                        bluePiki = piki;
                        injectedBlue = true;
                        std::printf("P2_BIGTREASURE_SLICE3_BLUE species=%d injected=1\n",
                                    pc_p2_species(piki));
                        break;
                    }
                }
            }
            require(injectedBlue, "inject blue species");
            setup = true;
        }

        // Pin the Navi and a few red Pikmin inside/at the boss attack box so the
        // ordinary attack has live targets. Teleport each frame (fixture
        // intervention, labelled).
        pinTargets();

        // Observe the ordinary FSM phase via the read hook.
        phase = pc_p2_hardlanes_bigtreasure_phase();
        if (phase != lastPhase) {
            lastPhase = phase;
            std::printf("P2_BIGTREASURE_SLICE3_PHASE phase=%s weapons=%d\n",
                        phaseName(phase),
                        pc_p2_hardlanes_bigtreasure_weapon_count());
        }

        if (phase == P2BT_Attack && !sentKnock) {
            ++framesInAttack;
            // Let the elec element run to emit, then knock elec off to observe
            // the re-pick. This single knock-off is the flagged injected trigger;
            // the FSM re-pick and the next (fire) attack are natural.
            if (framesInAttack >= 90) {
                const bool posted = pc_p2_hardlanes_bigtreasure_hit(
                    P2BTWEAPON_Elec, P2BigTreasureOwnership::kWeaponMaxHealth, false);
                std::printf("P2_BIGTREASURE_SLICE3_KNOCKOFF posted=%d weapon=elec injected=1\n",
                            posted ? 1 : 0);
                sentKnock = true;
            }
        }
        if (sentKnock && !sawRepick && phase == P2BT_PreAttack) {
            sawRepick = true;
            repickFrames = 0;
            std::printf("P2_BIGTREASURE_SLICE3_REPICK phase=PreAttack weapons=%d\n",
                        pc_p2_hardlanes_bigtreasure_weapon_count());
        }
        if (sawRepick) {
            // Let the follow-on (fire) attack run so the pinned fire-column
            // Pikmin are hit by the loop's real receiver before we exit.
            ++repickFrames;
            if (repickFrames >= 700) {
                std::printf("P2_BIGTREASURE_SLICE3_ATTACKED\n");
                std::puts("PASS BIGTREASURE_SLICE3_RUNTIME");
                std::fflush(stdout);
                std::_Exit(0);
            }
        }
        return result;
    }

    void draw(Graphics& gfx) override { PlugPikiApp::draw(gfx); }

private:
    static const char* phaseName(int p)
    {
        switch (p) {
        case P2BT_Dead: return "Dead";
        case P2BT_Stay: return "Stay";
        case P2BT_Land: return "Land";
        case P2BT_Wait: return "Wait";
        case P2BT_ItemWait: return "ItemWait";
        case P2BT_Flick: return "Flick";
        case P2BT_PreAttack: return "PreAttack";
        case P2BT_Attack: return "Attack";
        case P2BT_PutItem: return "PutItem";
        case P2BT_DropItem: return "DropItem";
        case P2BT_Walk: return "Walk";
        case P2BT_ItemWalk: return "ItemWalk";
        default: return "?";
        }
    }

    int countSquad()
    {
        int alive = 0;
        if (!pikiMgr) return 0;
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* piki = static_cast<Piki*>(*it);
            if (piki && piki->isAlive()) ++alive;
        }
        return alive;
    }

    // Pins the Navi in the boss box and a few Pikmin: the injected Blue plus a
    // Red in the fire column (so the follow-on fire attack reaches them through
    // the loop), and two Red near the boss footprint for the elec scatter.
    void pinTargets()
    {
        Navi* navi = naviMgr ? naviMgr->getNavi() : nullptr;
        if (navi) {
            navi->mSRT.t.set(0.0f, ground, 60.0f);
        }
        static const float fireColumn[2][3] = {
            { 0.0f, 50.0f, 120.0f },   // red, fire-immune -> accepted=0
            { 0.0f, 50.0f, 130.0f },   // blue (injected), non-immune -> accepted=1
        };
        static const float nearBoss[2][3] = {
            { 25.0f, 0.0f, 0.0f }, { -25.0f, 0.0f, 0.0f },
        };
        if (!pikiMgr) return;
        int columnIndex = 0, bossIndex = 0;
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* piki = static_cast<Piki*>(*it);
            if (!piki || !piki->isAlive()) continue;
            if (piki == bluePiki) {
                piki->mSRT.t.set(fireColumn[1][0], ground + fireColumn[1][1], fireColumn[1][2]);
                continue;
            }
            if (columnIndex < 1) {
                piki->mSRT.t.set(fireColumn[0][0], ground + fireColumn[0][1], fireColumn[0][2]);
                ++columnIndex;
                continue;
            }
            if (bossIndex < 2) {
                piki->mSRT.t.set(nearBoss[bossIndex][0], ground, nearBoss[bossIndex][2]);
                ++bossIndex;
                continue;
            }
        }
    }
};
} // namespace

int main(int argc, char** argv)
{
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    pc_bbft_init(argc, argv);
    require(pc_pikipelago_room_preview(), "requires --experimental-pikmin2-room");
    require(pc_window_init("BigTreasure slice-3 ordinary-loop fixture", 960, 540), "window init");
    pc_settings_init();
    pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);
    pc_window_set_window_size(960, 540);
    pc_window_center();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new Slice3App());
    return 0;
}
