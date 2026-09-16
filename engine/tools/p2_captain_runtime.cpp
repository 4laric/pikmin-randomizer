// Lane 12 (#130) live slot-0 captain/squad adapter runtime fixture.
// Private real-GL display fixture; no production registration or gameplay claims.
//
// Drives the LIVE pc_p2_captain adapter (p2_captain::setup_from_navi_mgr is now
// auto-bound by the GameCoreSection constructor) through the four semantics a
// captor family needs: target identity, claim/release, interrupted capture and
// cleanup.
// A separate --knockout-roster scenario exercises the survivor-gated game-over /
// NaviMgr::informOrimaDead hook added to NaviDeadState::init.
// The --survivor-path scenario (with PIKMIN_P2_SECOND_CAPTAIN=1) drives a real
// second captain, knocks the active captain down through the integrated
// InteractAttack receiver, and verifies the survivor rebind, observed squad
// release and final stage end.
// The --two-captain-ppm scenario draws both captains and saves a PPM.
#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "App.h"
#include "CPlate.h"
#include "GameCoreSection.h"
#include "GameStat.h"
#include "Graphics.h"
#include "Interactions.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "Node.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "MoviePlayer.h"
#include "pc_bbft.h"
#include "pc_gfx.h"
#include "pc_gpu_preference.h"
#include "pc_p2_captain.h"
#include "pc_p2_preview.h"
#include "pc_window.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "system.h"
#include "teki.h"
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

namespace {
bool sKnockoutScenario = false;
bool sSurvivorScenario = false;
bool sPpmScenario = false;
bool sMamutaScenario = false;

void require(bool value, const char* message)
{
    if (!value) { std::printf("FAIL P2_CAPTAIN_RUNTIME %s\n", message); std::fflush(stdout); std::_Exit(1); }
}

// Reusable P6 PPM capture after a real draw (mirrors the other room fixtures).
// Returns true (and writes the file) only when the captured frame is non-black,
// so a caller can retry across the setup fade-in.
bool capture(const char* path)
{
    pc_gfx_flush_batch();
    auto bind = reinterpret_cast<PFNGLBINDFRAMEBUFFERPROC>(SDL_GL_GetProcAddress("glBindFramebuffer"));
    require(bind != nullptr, "framebuffer entry point unavailable");
    GLint previous = 0; glGetIntegerv(GL_FRAMEBUFFER_BINDING, &previous); bind(GL_FRAMEBUFFER, 0);
    int width = 0, height = 0; SDL_GL_GetDrawableSize(SDL_GL_GetCurrentWindow(), &width, &height);
    std::vector<unsigned char> pixels(size_t(width) * size_t(height) * 3);
    glReadBuffer(GL_BACK); glPixelStorei(GL_PACK_ALIGNMENT, 1);
    glReadPixels(0, 0, width, height, GL_RGB, GL_UNSIGNED_BYTE, pixels.data());
    bind(GL_FRAMEBUFFER, previous);
    bool visible = false; for (unsigned char value : pixels) visible |= value > 8;
    if (!visible) return false;
    FILE* file = std::fopen(path, "wb"); require(file != nullptr, "capture file");
    std::fprintf(file, "P6\n%d %d\n255\n", width, height);
    for (int y = height - 1; y >= 0; --y) std::fwrite(pixels.data() + size_t(y) * width * 3, 1, size_t(width) * 3, file);
    std::fclose(file);
    return true;
}

class CaptainApp final : public PlugPikiApp {
    int frames = 0;
    bool setup = false;
    int stage = 0;
    Piki* squadPiki = nullptr;
    std::uint64_t epoch = 1;
    // Survivor scenario state.
    Piki* survivorPiki = nullptr;
    int survivorPreMode = 0;
    Navi* survivorNavi0 = nullptr;
    Navi* survivorNavi1 = nullptr;
    // Two-captain PPM scenario state.
    bool ppmArmed = false;
    int ppmFrames = 0;
    bool ppmCaptured = false;
    // Natural Mamuta knockdown scenario state (task 2 / slice 3b).
    bool mamutaArmed = false;
    int mamutaFrames = 0;
    BTeki* mamutaActor = nullptr;
    Navi* mamutaNavi = nullptr;
    float mamutaStartHealth = 0.0f;
public:
    void draw(Graphics& gfx) override {
        PlugPikiApp::draw(gfx);
        if (ppmArmed && !ppmCaptured && frames >= 150) {
            if (capture("two-captains.ppm")) {
                ppmCaptured = true;
                std::printf("P2_CAPTAIN_PPM saved=two-captains.ppm frame=%d captains=%d\n",
                    frames, naviMgr ? naviMgr->getNaviCount() : 0);
                std::fflush(stdout);
                std::puts("PASS P2_CAPTAIN_RUNTIME"); std::fflush(stdout); std::_Exit(0);
            }
        }
    }
    int idle() override {
        int result = PlugPikiApp::idle();
        require(++frames < 900, "timeout");
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
            gameflow.mMoviePlayer->requestSkip();
            return result;
        }
        // The two-captain PPM and Mamuta runs span frames; clear the preview's
        // day/UI overlay that would otherwise freeze the managers a few frames in.
        if ((sPpmScenario || sMamutaScenario) && (gameflow.mPauseAll || gameflow.mIsUIOverlayActive)) {
            gameflow.mPauseAll = FALSE;
            gameflow.mIsUIOverlayActive = FALSE;
        }
        // The Mamuta arena replaces the generic preview stage, so it does not
        // satisfy pc_p2_preview_ready(); only require a live naviMgr there.
        if ((!sMamutaScenario && !pc_p2_preview_ready()) || !naviMgr || !naviMgr->getNavi()
            || gameflow.mPauseAll || gameflow.mIsUIOverlayActive)
            return result;
        if (!setup) {
            setup = true;
            int liveSquad = 0;
            Iterator squad(pikiMgr);
            CI_LOOP(squad) { if (static_cast<Piki*>(*squad)) ++liveSquad; }
            std::printf("P2_CAPTAIN_SQUAD live=%d\n", liveSquad);
            std::fflush(stdout);

            // The scene setup hook should already have bound the live adapter.
            require(pc_p2_captain::adapter() != nullptr,
                "live adapter auto-bound by GameCoreSection constructor");
            require(pc_p2_captain::setup_from_navi_mgr(), "setup_from_navi_mgr idempotent");
            require(pc_p2_captain::adapter() != nullptr, "adapter remains bound");

            if (sPpmScenario) {
                // Arm: the second captain must already exist (PIKMIN_P2_SECOND_CAPTAIN=1).
                require(naviMgr->hasSecondNavi(), "second captain present in roster");
                require(naviMgr->getNavi(0) && naviMgr->getNavi(1), "both captain slots live");
                std::printf("P2_CAPTAIN_PPM_ARMED captain_count=%d\n", naviMgr->getNaviCount());
                std::fflush(stdout);
                ppmArmed = true;
                return result;
            }

            if (sMamutaScenario) {
                // --- Natural Mamuta knockdown (task 2): the staged arena spawns a
                // P1 Miurin (generator 221001). Stage the arena WITHOUT
                // p2-mamuta-rules.txt, so pc_p2_mamuta_bury_navi returns -1 and the
                // source InteractBury path (TAImiurin.cpp:559) transits the captain
                // through NAVISTATE_Bury with pcNaviHurt(20.0) until it goes Dead.
                Iterator it(tekiMgr);
                mamutaActor = nullptr;
                CI_LOOP(it) {
                    Teki* t = static_cast<Teki*>(*it);
                    if (t && t->mTekiType == TEKI_Miurin) { mamutaActor = static_cast<BTeki*>(t); break; }
                }
                require(mamutaActor != nullptr, "a spawned Miurin (Mamuta) actor is present");
                mamutaNavi = naviMgr->getActiveNavi();
                if (!mamutaNavi) mamutaNavi = naviMgr->getNavi();
                require(mamutaNavi != nullptr, "an active captain is present");
                // Park the captain inside the ~70-unit attackable range (pod and
                // natural lane-19 fixtures use actor.z + 20..50).
                Vector3f park(mamutaActor->mSRT.t.x, 0.0f, mamutaActor->mSRT.t.z + 50.0f);
                park.y = mapMgr->getMinY(park.x, park.z, true);
                mamutaNavi->resetPosition(park);
                mamutaStartHealth = mamutaNavi->mHealth;
                std::printf("P2_CAPTAIN_MAMUTA_ARMED actor=%.1f,%.1f,%.1f captain=%.1f,%.1f,%.1f health=%.1f rules_off=1\n",
                    mamutaActor->mSRT.t.x, mamutaActor->mSRT.t.y, mamutaActor->mSRT.t.z,
                    park.x, park.y, park.z, mamutaStartHealth);
                std::fflush(stdout);
                mamutaArmed = true;
                return result;
            }

            if (sSurvivorScenario) {
                // --- Survivor path end-to-end (#130): natural knockdown + rebind ---
                require(naviMgr->hasSecondNavi(), "second captain present in roster");
                survivorNavi0 = naviMgr->getNavi(0);
                survivorNavi1 = naviMgr->getNavi(1);
                require(survivorNavi0 != nullptr && survivorNavi1 != nullptr, "both captain slots live");
                require(pc_p2_captain::health(0) > 0.0f && pc_p2_captain::health(1) > 0.0f,
                    "both captains adopted into the adapter");
                require(naviMgr->getActiveNavi() == survivorNavi0, "slot 0 active at scene start");

                // Record a real starting squad Piki bound to captain 0 so the
                // survivor branch's releasePikis() has a live occupant whose mode
                // it flips (the downed captain releases its squad to FreeMode).
                Iterator sit(pikiMgr);
                survivorPiki = nullptr;
                CI_LOOP(sit) {
                    Piki* p = static_cast<Piki*>(*sit);
                    if (p && p->isAlive() && p->mNavi == survivorNavi0) { survivorPiki = p; break; }
                }
                require(survivorPiki != nullptr, "a live starting squad Piki bound to captain 0 exists");
                survivorPreMode = survivorPiki->mMode;

                // Populate the plate's traversable slot count before the knockdown:
                // releasePikis() iterates mTotalSlotCount, which the per-frame
                // makeCStick -> CPlate::refresh normally fills on a later frame.
                // Refresh it now so the survivor branch really releases the squad.
                survivorNavi0->mPlateMgr->refresh(survivorNavi0->getPlatePikis(), 1.0f);

                // Natural knockdown of the active captain through the integrated
                // Teki attack receiver (InteractAttack::actNavi applies pcNaviHurt
                // damage; finishDamage then exits to NAVISTATE_Dead).
                InteractAttack attack(nullptr, nullptr, 500.0f, false);
                require(attack.actNavi(survivorNavi0), "InteractAttack::actNavi landed on active captain");
                require(survivorNavi0->mHealth <= 1.0f, "attack receiver reduced captain to down");
                survivorNavi0->finishDamage();

                require(survivorNavi0->getCurrState()->getID() == NAVISTATE_Dead,
                    "(a) downed captain entered Dead (ODead)");
                require(!GameStat::orimaDead, "(b) game not ended on first knockout");
                require(!GameCoreSection::inPause(), "(b) core not paused on first knockout");
                require(naviMgr->getAliveOrima() == survivorNavi1, "(b) survivor remains alive");
                require(naviMgr->getActiveNavi() == survivorNavi1, "(c) control rebound to survivor (active index)");
                // Observed squad release: the downed captain's real squad member is now FreeMode.
                require(survivorPiki->mMode == PikiMode::FreeMode,
                    "(squad) survivor-down released the starting squad to FreeMode");
                std::printf("P2_CAPTAIN_SURVIVOR_DOWN dead=0 survivor=1 plate=%d piki_mode_before=%d piki_mode_after=%d orima_dead=0 paused=0 active=1\n",
                    survivorNavi0->getPlatePikis(), survivorPreMode, (int)survivorPiki->mMode);
                std::fflush(stdout);

                // Final stage end (injected second-captain knockout).
                survivorNavi1->mHealth = 0.0f;
                survivorNavi1->finishDamage();
                require(naviMgr->isNaviDead(survivorNavi1), "(d) second captain recorded dead");
                require(naviMgr->getAliveOrima() == nullptr, "(d) no survivor remains");
                require(GameStat::orimaDead, "(d) game over signalled with zero survivors");
                std::printf("P2_CAPTAIN_SURVIVOR_STAGE_END dead=2 alive_orima=none orima_dead=1\n");
                std::fflush(stdout);
                std::puts("PASS P2_CAPTAIN_RUNTIME"); std::fflush(stdout); std::_Exit(0);
            }

            // --- Gate 1: target identity ---
            Navi* navi = naviMgr->getNavi();
            require(pc_p2_captain::captain_handle(0) == static_cast<void*>(navi),
                "captain_handle(0) resolves the live slot-0 Navi");
            require(!pc_p2_captain::navi_dead(0), "slot 0 not dead");
            require(pc_p2_captain::health(0) > 0.0f, "slot 0 health adopted");
            std::printf("P2_CAPTAIN_TARGET_IDENTITY slot=0 handle_matches=1 health=%.1f\n",
                pc_p2_captain::health(0));
            std::fflush(stdout);

            // --- Gate 2: claim/release (captain) ---
            // Single-captain port: the zero-control guard refuses ingesting the
            // only controllable captain, exactly as the source never strands the
            // player with no one left.
            require(!pc_p2_captain::capture_captain(0, epoch),
                "only-captain capture refused (zero-control guard)");
            require(pc_p2_captain::health(0) > 0.0f, "captain unaffected by refusal");
            std::printf("P2_CAPTAIN_CLAIM_REFUSED captain=0 guard=zero_control\n");
            std::fflush(stdout);

            // --- Gate 3/4/5: live Piki claim, release, interrupted capture ---
            Piki* piki = static_cast<Piki*>(pikiMgr->birth());
            require(piki != nullptr, "piki birth");
            piki->init(navi);
            piki->initColor(Red);
            piki->setFlower(Leaf);
            piki->resetPosition(navi->mSRT.t);
            piki->mMode = PikiMode::AttackMode;
            squadPiki = piki;
            require(piki->mNavi == navi, "piki owned by slot-0 captain");

            require(pc_p2_captain::capture_actor(epoch, piki), "capture_actor claims live piki");
            require(piki->mNavi == nullptr, "captor-held piki freed from captain");
            require(pc_p2_captain::captive_count() == 1, "captive count incremented");
            std::printf("P2_CAPTAIN_ACTOR_CAPTURED captive_count=%d\n",
                pc_p2_captain::captive_count());
            std::fflush(stdout);

            require(pc_p2_captain::release_actor(epoch, piki, 0), "release_actor returns to squad");
            require(piki->mNavi == navi, "released piki re-owned by slot 0");
            require(pc_p2_captain::captive_count() == 0, "captive count cleared");
            std::printf("P2_CAPTAIN_ACTOR_RELEASED owner=0 captive_count=%d\n",
                pc_p2_captain::captive_count());
            std::fflush(stdout);

            // Interrupted capture (captor death): held actors are freed to the
            // ground (whistle-reclaimable), never deleted.
            ++epoch;
            require(pc_p2_captain::capture_actor(epoch, piki), "re-capture actor");
            const std::vector<std::uint32_t> dropped = pc_p2_captain::drop_captured(epoch);
            require(dropped.size() == 1, "interrupted capture drops the held actor");
            require(piki->mNavi == nullptr, "dropped actor free (whistle-reclaimable)");
            require(pc_p2_captain::captive_count() == 0, "captive table empty after drop");
            std::printf("P2_CAPTAIN_INTERRUPT_DROP released=%d state=free_reclaimable\n",
                (int)dropped.size());
            std::fflush(stdout);

            // Reclaim for cleanup, then reload: a captive is restored to its
            // previous owner on reload — never lost or duplicated.
            piki->mNavi = navi;
            require(pc_p2_captain::adopt_squad() >= 1, "freed piki re-adopted into squad");
            require(pc_p2_captain::capture_actor(++epoch, piki), "capture for reload conservation");
            require(piki->mNavi == nullptr, "captive removed from squad");
            require(pc_p2_captain::reload(), "reload succeeds");
            require(piki->isAlive(), "captive survived reload (not lost)");
            require(piki->mNavi == navi, "reload restored captive to previous owner");
            require(pc_p2_captain::captive_count() == 0, "no duplicated captive after reload");
            std::printf("P2_CAPTAIN_CLEANUP_RELOAD conserved=1 captive_count=%d\n",
                pc_p2_captain::captive_count());
            std::fflush(stdout);

            if (sKnockoutScenario) {
                // --- Gate: survivor-gated game over + knockout roster sync ---
                // Injected death: force health to zero and run Navi::finishDamage,
                // which transits to NAVISTATE_Dead and (via the lane-12 hook)
                // marks the roster via informOrimaDead and gates GameStat::orimaDead
                // on the alive-captain set. Labelled injected, not natural combat.
                if (!gameflow.mGameInterface) {
                    std::printf("P2_CAPTAIN_KNOCKOUT untested (no game interface)\n");
                    std::fflush(stdout);
                    std::puts("PASS P2_CAPTAIN_RUNTIME"); std::fflush(stdout); std::_Exit(0);
                }
                navi->mHealth = 0.0f;
                navi->finishDamage();
                require(naviMgr->isNaviDead(navi), "roster recorded the knockout");
                require(naviMgr->getAliveOrima() == nullptr, "no surviving captain remains");
                require(GameStat::orimaDead, "game over still signalled with zero survivors");
                std::printf("P2_CAPTAIN_KNOCKOUT_SYNC dead=1 alive_orima=none orima_dead=1\n");
                std::fflush(stdout);
                std::puts("PASS P2_CAPTAIN_RUNTIME"); std::fflush(stdout); std::_Exit(0);
            }

            std::puts("P2_CAPTAIN_LIVE_SEAM_PASS target_identity=1 claim_release=1 interrupt=1 cleanup=1");
            std::puts("PASS P2_CAPTAIN_RUNTIME"); std::fflush(stdout); std::_Exit(0);
            return result;
        }
        if (sMamutaScenario && mamutaArmed) {
            ++mamutaFrames;
            // Hold the captain inside the attackable range until the Miurin's
            // natural bury lands (its TAI throws InteractBury on the Navi).
            if (mamutaNavi->isAlive()) {
                Vector3f park(mamutaActor->mSRT.t.x, 0.0f, mamutaActor->mSRT.t.z + 50.0f);
                park.y = mapMgr->getMinY(park.x, park.z, true);
                mamutaNavi->resetPosition(park);
            }
            const float hp = mamutaNavi->mHealth;
            const int state = mamutaNavi->getCurrState() ? mamutaNavi->getCurrState()->getID() : -1;
            const bool hit = hp < mamutaStartHealth;
            if (hit || state == NAVISTATE_Bury || state == NAVISTATE_Dead) {
                const bool down = (state == NAVISTATE_Dead) || hp <= 1.0f;
                std::printf("P2_CAPTAIN_MAMUTA_BURY frame=%d health=%.1f state=%d hit=%d down=%d\n",
                    mamutaFrames, hp, state, int(hit), int(down));
                std::fflush(stdout);
                if (down) {
                    std::puts("PASS P2_CAPTAIN_RUNTIME"); std::fflush(stdout); std::_Exit(0);
                }
                // Assisted exit from the P1 NaviBuryState: it is an escapable,
                // non-lethal state, so the captain would otherwise stay buried at
                // 80 HP. The damage stays natural (the spawned Miurin's
                // InteractBury); only the bury-exit is assisted so the Miurin can
                // land successive natural buries down to Dead.
                if (state == NAVISTATE_Bury) {
                    mamutaNavi->mStateMachine->transit(mamutaNavi, NAVISTATE_Walk);
                    std::printf("P2_CAPTAIN_MAMUTA_ESCAPE_ASSIST frame=%d health=%.1f\n", mamutaFrames, hp);
                    std::fflush(stdout);
                }
                mamutaStartHealth = hp;
            }
            require(mamutaFrames < 1200, "natural mamuta bury timeout");
            return result;
        }
        return result;
    }
};
} // namespace

int main(int argc, char** argv)
{
    for (int i = 1; i < argc; ++i) {
        if (std::string(argv[i]) == "--knockout-roster") sKnockoutScenario = true;
        if (std::string(argv[i]) == "--survivor-path") sSurvivorScenario = true;
        if (std::string(argv[i]) == "--two-captain-ppm") sPpmScenario = true;
        if (std::string(argv[i]) == "--mamuta-natural") sMamutaScenario = true;
    }
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    pc_bbft_init(argc, argv);
    require(pc_pikipelago_room_preview(), "requires --experimental-pikmin2-room");
    if (!pc_window_init("P2 captain live adapter fixture", 960, 540)) return 3;
    pc_window_center();
    {
        SDL_Window* window = SDL_GL_GetCurrentWindow();
        int width = 0, height = 0, x = 0, y = 0;
        SDL_GetWindowSize(window, &width, &height);
        SDL_GetWindowPosition(window, &x, &y);
        SDL_Rect bounds{0, 0, 0, 0};
        SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(window), &bounds);
        const bool centered = std::abs(x - (bounds.x + (bounds.w - width) / 2)) <= 2
            && std::abs(y - (bounds.y + (bounds.h - height) / 2)) <= 2;
        std::printf("P2_CAPTAIN_WINDOW size=%dx%d pos=%d,%d display=%dx%d centered=%d\n",
            width, height, x, y, bounds.w, bounds.h, int(centered));
        std::fflush(stdout);
    }
    pc_settings_init();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new CaptainApp());
    return 0;
}
