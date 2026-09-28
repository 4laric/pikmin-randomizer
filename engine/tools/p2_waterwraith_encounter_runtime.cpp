// Private real-GL Waterwraith ENCOUNTER runtime fixture (#443 / parent #175).
// Compiled by the isolated fixture build only (root repo
// scripts/build_pikmin2_fixture.py); it is not part of the game target.
//
// Boots the frozen host with --experimental-pikmin2-room and lets the real
// engine preview setup install the lane-31 registration seam, which now also
// drives the combat consumer (pc_p2_waterwraith_encounter). The fixture does
// NOT call the combat API directly: it only arranges live squad Pikmin near the
// registered actor (repositioning real Piki objects and converting some to
// Purple) and observes the encounter markers/stats.
//
// Coverage:
//   * Stage A (reds only adjacent): the roller crushes them (InteractFlick),
//     but non-Purple never damages the actor (`damageDealt == 0`).
//   * Stage B (Purple adjacent): Purple stuns the riding roller, accepted hits
//     deplete the Tyre health, the roller death script dismounts and removes the
//     child, and the exposed body is finished through its own death (body zero
//     -> Dead key5 stand-in corpse drop -> Dead end teardown).
//   * Cleanup/re-entry: after natural death, reset then re-setup the seam and
//     require it is ready again with restored health and no stale state.

#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "gl/pc_opengl.h"
#include "App.h"
#include "Graphics.h"
#include "MapMgr.h"
#include "Matrix4f.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Node.h"
#include "MoviePlayer.h"
#include "Piki.h"
#include "PikiAI.h"
#include "PikiMgr.h"
#include "Pellet.h"
#include "Kontroller.h"
#include "system.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "pc_window.h"
#include "pc_p2_preview.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "pc_p2_purple.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <vector>

#include "pc_p2_waterwraith_encounter.h"
#include "pc_p2_waterwraith_register.h"

namespace {
constexpr int kStageA_Frames = 45;
constexpr int kMaxFrames = 9000;
constexpr int kCarryDeadlineFrames = 2400;
// The labelled transport assist fires only near the end of the observation
// window, so a natural multi-carrier haul has time to complete first (a natural
// carrier that grabs early reaches the Pod long before this).
constexpr int kAssistGraceFrames = 1800;
constexpr float kPurpleOffsetX[3] = { 30.0f, 0.0f, -30.0f };
constexpr float kPurpleOffsetZ[3] = { 0.0f, 30.0f, 0.0f };
constexpr float kRedOffsetX[2] = { 50.0f, -50.0f };
constexpr float kRedOffsetZ[2] = { 0.0f, 0.0f };

// A navi controller that never whistles or moves, so the Captain cannot recall
// a squad the fixture freed into FreeMode (the same trick preview_p2_room's
// FixtureController uses: the navi polls this controller each update).
class NullNaviController : public Kontroller {
public:
    NullNaviController() : Kontroller(1) {}
    void update() override
    {
        updateCont(0);
        mMainStickX = 0;
        mMainStickY = 0;
        mSubStickX = 0;
        mSubStickY = 0;
    }
};

void require(bool value, const char* message)
{
    if (!value) {
        std::printf("FAIL WATERWRAITH_ENCOUNTER_RUNTIME %s\n", message);
        std::fflush(stdout);
        std::_Exit(1);
    }
}

void capture(const char* path)
{
    auto bind = reinterpret_cast<PFNGLBINDFRAMEBUFFERPROC>(SDL_GL_GetProcAddress("glBindFramebuffer"));
    GLint previous = 0;
    glGetIntegerv(GL_FRAMEBUFFER_BINDING, &previous);
    bind(GL_FRAMEBUFFER, 0);
    int w = 0, h = 0;
    SDL_GL_GetDrawableSize(SDL_GL_GetCurrentWindow(), &w, &h);
    std::vector<unsigned char> pixels(size_t(w) * size_t(h) * 3);
    glPixelStorei(GL_PACK_ALIGNMENT, 1);
    glReadBuffer(GL_BACK);
    glReadPixels(0, 0, w, h, GL_RGB, GL_UNSIGNED_BYTE, pixels.data());
    bind(GL_FRAMEBUFFER, previous);
    require(glGetError() == GL_NO_ERROR, "capture GL error");
    bool nonblack = false;
    for (unsigned char value : pixels) {
        nonblack |= value > 8;
    }
    require(nonblack, "empty capture");
    FILE* file = std::fopen(path, "wb");
    require(file != nullptr, "capture file");
    std::fprintf(file, "P6\n%d %d\n255\n", w, h);
    for (int y = h - 1; y >= 0; --y) {
        std::fwrite(pixels.data() + size_t(y) * w * 3, 1, size_t(w) * 3, file);
    }
    std::fclose(file);
}

class WaterwraithEncounterApp final : public PlugPikiApp {
    int frames = 0;
    bool windowPrinted = false;
    bool readyPrinted = false;
    bool stagedReds = false;
    bool convertedPurple = false;
    int stageAFrames = 0;
    bool stageAOk = false;
    bool captured = false;
    bool reentryChecked = false;
    bool corpseGrabStaged = false;
    bool carryResolved = false;
    bool carrySetupLogged = false;
    bool assistAssigned = false;
    int carryFrames = 0;
    int maxCarriers = 0;

public:
    int idle() override
    {
        int result = PlugPikiApp::idle();
        require(++frames < kMaxFrames, "timeout");
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
            gameflow.mMoviePlayer->requestSkip();
            return result;
        }
        if (!pc_p2_preview_ready() || !naviMgr || !naviMgr->getNavi() || gameflow.mPauseAll
            || gameflow.mIsUIOverlayActive) {
            return result;
        }
        require(pc_p2_waterwraith_register_ready(),
                "register seam not installed (missing p2-waterwraith-actor.txt?)");

        if (!windowPrinted) {
            SDL_Window* window = SDL_GL_GetCurrentWindow();
            require(window != nullptr, "window");
            int windowWidth = 0, windowHeight = 0;
            SDL_GetWindowSize(window, &windowWidth, &windowHeight);
            require(windowWidth == 960 && windowHeight == 540, "window size 960x540");
            std::printf("P2_WATERWRAITH_ENCOUNTER_WINDOW size=960x540\n");
            windowPrinted = true;
        }
        if (!readyPrinted) {
            // Pin the captain (unconditional: Navi::Navi already allocs a Kontroller)
            // and park it far from the corpse and the corpse->Pod haul path, so the
            // post-work join-party (range 250, aiAction.cpp:462-468) cannot re-adopt
            // a freed Pikmin whose transport aborted near the corpse.
            Navi* navi = naviMgr->getNavi();
            if (navi) {
                navi->mKontroller = new NullNaviController();
                Vector3f park(-400.0f, 0.0f, 0.0f);
                if (mapMgr) {
                    park.y = mapMgr->getMinY(park.x, park.z, true);
                }
                navi->resetPosition(park);
                std::printf("P2_WATERWRAITH_NAVI_PARKED pos=%.1f,%.1f,%.1f\n", park.x, park.y,
                            park.z);
            }
            std::printf("P2_WATERWRAITH_ENCOUNTER_READY\n");
            readyPrinted = true;
        }

        const P2WaterwraithEncounterStats& stats = pc_p2_waterwraith_encounter_stats();
        const P2WaterwraithVec3 roller = pc_p2_waterwraith_register_roller_position();
        const P2WaterwraithVec3 wraith = pc_p2_waterwraith_register_wraith_position();
        const P2WaterwraithVec3 ref = pc_p2_waterwraith_register_attached() ? roller : wraith;

        // Collect a small live Piki working set once.
        static std::vector<Piki*> squad;
        if (!stagedReds) {
            if (pikiMgr) {
                Iterator iterator(pikiMgr);
                CI_LOOP(iterator) {
                    Piki* piki = static_cast<Piki*>(*iterator);
                    if (piki && piki->isAlive() && squad.size() < 8) {
                        squad.push_back(piki);
                    }
                }
            }
            stagedReds = !squad.empty();
            if (!stagedReds) {
                return result;
            }
            std::printf("P2_WATERWRAITH_ENCOUNTER_SQUAD count=%d\n", static_cast<int>(squad.size()));
        }

        // Keep two reds under the rollers (crush). This never damages the actor.
        // Once the wraith is finished, stop steering the squad so idle Pikmin
        // can pick up the corpse stand-in and carry it to the Pod.
        const bool dead = pc_p2_waterwraith_register_finished();
        if (!dead) {
            const int redCount = 2;
            for (int i = 0; i < redCount && i < static_cast<int>(squad.size()); ++i) {
                if (!squad[i]->isAlive()) {
                    continue;
                }
                squad[i]->resetPosition(Vector3f(ref.x + kRedOffsetX[i], 0.0f, ref.z + kRedOffsetZ[i]));
            }
        }

        if (!stageAOk) {
            ++stageAFrames;
            if (stats.damageDealt != 0.0f || stats.acceptedHits != 0) {
                require(false, "non-Purple squad damaged the actor");
            }
            if (stageAFrames >= kStageA_Frames) {
                require(stats.crushes > 0, "roller did not crush adjacent non-Purple Pikmin");
                stageAOk = true;
                std::printf("P2_WATERWRAITH_ENCOUNTER_STAGE_A crushes=%llu damage=%.1f\n",
                            static_cast<unsigned long long>(stats.crushes), stats.damageDealt);
            }
            return result;
        }

        // Convert three squad members to Purple and keep them adjacent.
        if (!convertedPurple) {
            for (int i = 0; i < 3 && i < static_cast<int>(squad.size()); ++i) {
                if (squad[i]->isAlive()) {
                    pc_p2_make_purple(squad[i]);
                }
            }
            convertedPurple = true;
            std::printf("P2_WATERWRAITH_ENCOUNTER_PURPLE_SETUP\n");
        }
        if (!dead) {
            for (int i = 0; i < 3 && i < static_cast<int>(squad.size()); ++i) {
                if (!squad[i]->isAlive()) {
                    continue;
                }
                squad[i]->resetPosition(Vector3f(ref.x + kPurpleOffsetX[i], 0.0f, ref.z + kPurpleOffsetZ[i]));
            }
        } else if (!corpseGrabStaged) {
            // Death is done: release the squad from formation (player-equivalent
            // whistle/dismiss) and place the survivors on the corpse stand-in so
            // the free-mode `graspSituation` idle search picks it up and carries
            // it to the preview Pod (natural pickup, same as preview_p2_room's
            // P2_CORPSE_FREE_RECRUIT idiom). Labelled player-equivalent stimulus.
            for (int i = 0; i < static_cast<int>(squad.size()); ++i) {
                if (!squad[i]->isAlive()) {
                    continue;
                }
                Navi* navi = naviMgr ? naviMgr->getNavi() : nullptr;
                squad[i]->changeMode(PikiMode::FreeMode, navi);
            }
            // Scatter the freed squad onto the corpse stand-in (one Free Pikmin
            // suffices for a NewNumberPellet; strength is not the issue).
            const float ring[8][2] = { { 12.0f, 0.0f }, { -12.0f, 0.0f }, { 0.0f, 12.0f },
                                       { 0.0f, -12.0f }, { 16.0f, 10.0f }, { -16.0f, -10.0f },
                                       { 16.0f, -10.0f }, { -16.0f, 10.0f } };
            for (int i = 0; i < static_cast<int>(squad.size()); ++i) {
                if (!squad[i]->isAlive()) {
                    continue;
                }
                const float ox = ring[i % 8][0];
                const float oz = ring[i % 8][1];
                squad[i]->resetPosition(Vector3f(ref.x + ox, 0.0f, ref.z + oz));
            }
            std::printf("P2_WATERWRAITH_SQUAD_FREE count=%d\n",
                        static_cast<int>(squad.size()));
            for (int i = 0; i < static_cast<int>(squad.size()); ++i) {
                if (!squad[i]->isAlive()) {
                    continue;
                }
                std::printf("P2_WATERWRAITH_SQUAD_FREED_MODE pik=%p mode=%d\n",
                            static_cast<void*>(squad[i]), int(squad[i]->mMode));
            }
            corpseGrabStaged = true;
        }

        // Natural carry observation: count Pikmin in TransportMode toward the
        // corpse stand-in, log the corpse state/position and per-Pikmin
        // mode/distance, and (after a grace period) apply a labelled transport
        // assist so the receipt path can still be exercised when free pickup
        // does not complete (injected, never a natural PASS).
        if (dead && corpseGrabStaged) {
            int transport = 0;
            if (pikiMgr) {
                Iterator iterator(pikiMgr);
                CI_LOOP(iterator) {
                    Piki* piki = static_cast<Piki*>(*iterator);
                    if (piki && piki->isAlive() && piki->mMode == PikiMode::TransportMode) {
                        ++transport;
                    }
                }
            }
            if (transport > maxCarriers) {
                maxCarriers = transport;
            }
            ++carryFrames;
            Pellet* corpse = pc_p2_waterwraith_corpse_pellet();
            if (carryFrames % 120 == 0) {
                std::printf("P2_WATERWRAITH_CARRY_OBSERVE frame=%d carriers=%d max=%d deliveries=%u "
                            "corpse_state=%d corpse_alive=%d\n",
                            frames, transport, maxCarriers,
                            pc_p2_waterwraith_delivery_count(),
                            corpse ? int(corpse->getState()) : -1,
                            corpse ? int(corpse->isAlive()) : -1);
                if (pikiMgr) {
                    Iterator iterator(pikiMgr);
                    CI_LOOP(iterator) {
                        Piki* piki = static_cast<Piki*>(*iterator);
                        if (!piki || !piki->isAlive()) {
                            continue;
                        }
                        const float dx = piki->mSRT.t.x - ref.x;
                        const float dz = piki->mSRT.t.z - ref.z;
                        // mCurrActionIdx is public on TopAction; the transport
                        // action's internal mState is protected, so the current
                        // action index + mode name the step (PikiMode::TransportMode == 9;
                        // PikiAction::Transport == 21).
                        const int actionIdx
                            = piki->mActiveAction ? int(piki->mActiveAction->mCurrActionIdx) : -1;
                        std::printf("P2_WATERWRAITH_PIKIMODE pik=%p mode=%d action=%d "
                                    "dist=%.1f\n",
                                    static_cast<void*>(piki), int(piki->mMode), actionIdx,
                                    std::sqrt(dx * dx + dz * dz));
                    }
                }
            }
            // Labelled transport assist: if free pickup has not completed, hand
            // an idle Pikmin the real Transport action (the same mechanism the
            // Mamuta assisted fixture uses). This is INJECTED (assisted=1), not a
            // natural-carry PASS.
            if (!assistAssigned && carryFrames > kAssistGraceFrames
                && pc_p2_waterwraith_delivery_count() == 0 && corpse && corpse->isAlive()) {
                int count = 0;
                if (pikiMgr && naviMgr) {
                    Iterator iterator(pikiMgr);
                    CI_LOOP(iterator) {
                        Piki* piki = static_cast<Piki*>(*iterator);
                        if (!piki || !piki->isAlive()) {
                            continue;
                        }
                        piki->mActiveAction->abandon(nullptr);
                        piki->mActiveAction->mCurrActionIdx = PikiAction::Transport;
                        piki->mActiveAction->mChildActions[PikiAction::Transport].initialise(corpse);
                        piki->mMode = PikiMode::TransportMode;
                        ++count;
                    }
                }
                assistAssigned = true;
                std::printf("P2_WATERWRAITH_SQUAD_ASSIST carriers=%d assisted=1\n", count);
            }
        }

        return result;
    }

    void draw(Graphics& gfx) override
    {
        PlugPikiApp::draw(gfx);
        if (!stageAOk || !convertedPurple || captured) {
            return;
        }
        const P2WaterwraithEncounterStats& stats = pc_p2_waterwraith_encounter_stats();
        // Full natural chain: stun -> roller death -> child removal -> exposed
        // body death -> corpse drop -> teardown.
        if (!(stats.stunned > 0 && stats.acceptedHits > 0 && stats.damageDealt > 0.0f
              && stats.rollerZeroed && stats.childRemoved && stats.bodyZeroed
              && stats.treasureReleased && stats.killed
              && pc_p2_waterwraith_register_corpse_spawned()
              && pc_p2_waterwraith_register_finished())) {
            return;
        }

        require(pc_p2_waterwraith_register_tyre_health() <= 0.0f, "roller health not zeroed");
        require(pc_p2_waterwraith_register_body_health() <= 0.0f, "body health not zeroed");

        // Snapshot the combat counters before cleanup zeroes them.
        const P2WaterwraithEncounterStats summary = pc_p2_waterwraith_encounter_stats();
        require(summary.stunned > 0 && summary.acceptedHits > 0 && summary.crushes > 0
                    && summary.damageDealt > 0.0f && summary.bodyZeroed
                    && summary.treasureReleased && summary.killed,
                "combat counters incomplete");

        // Corpse carry + Pod receipt. The stand-in is a registered P1 number
        // pellet (ActTransport::decideGoal routes every pellet to the preview Pod
        // regardless of view). Wait for the receipt to fire through
        // pc_p2_preview_deliver -> pc_p2_waterwraith_receipt; if natural carry
        // does not complete, log the carrier evidence and report the host reason.
        if (!carrySetupLogged) {
            std::printf("P2_WATERWRAITH_CARRY_SETUP\n");
            carrySetupLogged = true;
        }
        if (pc_p2_waterwraith_delivery_count() == 0
            && carryFrames < kCarryDeadlineFrames) {
            return; // still carrying to the Pod
        }
        if (!carryResolved) {
            if (pc_p2_waterwraith_delivery_count() > 0) {
                std::printf("P2_WATERWRAITH_ENCOUNTER_DELIVERED deliveries=%u\n",
                            pc_p2_waterwraith_delivery_count());
            } else {
                std::printf("P2_WATERWRAITH_CARRY_UNRESOLVED frame=%d max_carriers=%d deliveries=%u\n",
                            carryFrames, maxCarriers, pc_p2_waterwraith_delivery_count());
            }
            carryResolved = true;
        }
        // Capture the carry outcome BEFORE the re-entry reset zeroes the counter.
        const bool delivered = pc_p2_waterwraith_delivery_count() > 0;

        // Cleanup and re-entry: tear the seam down and bring it back with no
        // stale actor/child/squad/body/corpse state.
        if (!reentryChecked) {
            pc_p2_waterwraith_register_reset();
            require(!pc_p2_waterwraith_register_ready(), "register seam did not reset");
            require(!pc_p2_waterwraith_register_finished(),
                    "finished flag did not clear on reset");
            require(!pc_p2_waterwraith_register_corpse_spawned(),
                    "corpse flag did not clear on reset");
            require(pc_p2_waterwraith_encounter_stats().stunned == 0, "encounter stats did not reset");
            require(pc_p2_waterwraith_register_setup("p2-waterwraith-actor.txt"),
                    "register seam re-setup failed");
            require(pc_p2_waterwraith_register_ready() && pc_p2_waterwraith_register_attached(),
                    "re-entry seam not ready/attached");
            require(pc_p2_waterwraith_register_body_health() > 0.0f,
                    "re-entry body health not restored");
            std::printf("P2_WATERWRAITH_ENCOUNTER_DEATH_REENTRY ready=1 attached=1\n");
            reentryChecked = true;
        }

        capture("waterwraith-encounter.ppm");
        std::printf("P2_WATERWRAITH_ENCOUNTER_PASS stuns=%llu hits=%llu crushes=%llu damage=%.1f "
                    "zeroed=1 child_removed=1 body_zeroed=1 treasure=1 kill=1 delivered=%d\n",
                    static_cast<unsigned long long>(summary.stunned),
                    static_cast<unsigned long long>(summary.acceptedHits),
                    static_cast<unsigned long long>(summary.crushes), summary.damageDealt,
                    delivered ? 1 : 0);
        captured = true;
        if (delivered) {
            std::puts(assistAssigned ? "PASS WATERWRAITH_ENCOUNTER_RUNTIME ASSISTED"
                                     : "PASS WATERWRAITH_ENCOUNTER_RUNTIME");
        } else {
            std::puts("BLOCKED WATERWRAITH_ENCOUNTER_RUNTIME carry=no_natural_carry");
        }
        std::fflush(stdout);
        std::_Exit(0);
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
    require(pc_window_init("Waterwraith encounter runtime fixture", 960, 540), "window init");
    pc_settings_init();
    pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);
    pc_window_set_window_size(960, 540);
    pc_window_center();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new WaterwraithEncounterApp());
    return 0;
}
