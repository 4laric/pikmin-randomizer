#include <SDL2/SDL.h>
#include "system.h"
#include "App.h"
#include "Node.h"
#include "FlowController.h"
#include "MoviePlayer.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "teki.h"
#include "ItemMgr.h"
#include "GoalItem.h"
#include "Pellet.h"
#include "Interactions.h"
#include "pc_randomizer.h"
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cstdio>
#include <cstdlib>
#include <cmath>

// Lane 18 ordinary Onion endpoint probe for the small Breadbug (PanModoki,
// source enemy 38, native TEKI_Collec). With the native randomizer ready in an
// ordinary campaign stage (Forest Navel, the audited native area for type 8),
// kill a real Breadbug, drive its real corpse through the Onion absorption
// endpoint (GoalItem::suckMe -> pc_randomizer_corpse_delivered ->
// pc_randomizer_check("Bestiary: Deliver Breadbug") -> checks.txt). Natural
// Pikmin carry is attempted first; a labeled fallback calls the same public
// endpoint directly if the carry stalls. This is the ordinary Onion/AP ledger,
// not the experimental Pod path.

static void require(bool ok, const char* why)
{
    if (!ok) { std::printf("FAIL lane18 breadbug ordinary: %s\n", why); std::fflush(nullptr); std::_Exit(1); }
}

class BreadbugOrdinaryApp : public PlugPikiApp {
    unsigned frames = 0;
    int phase = 0, waited = 0;
    bool natural = false;
    Vector3f spawn;
    Teki* target = nullptr;
    Pellet* corpse = nullptr;
public:
    int idle() override
    {
        int result = PlugPikiApp::idle();
        require(++frames < 9000, "startup timeout");
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) { gameflow.mMoviePlayer->requestSkip(); return result; }
        if (!pc_randomizer_ready() || !naviMgr || !tekiMgr || !itemMgr || !pikiMgr) return result;
        Navi* n = naviMgr->getNavi();
        if (!n || gameflow.mPauseAll || gameflow.mIsUIOverlayActive) return result;

        if (phase == 0) {
            Iterator it(tekiMgr);
            CI_LOOP(it) {
                auto* e = static_cast<Teki*>(*it);
                if (e && e->mTekiType == TEKI_Collec && e->isAlive()) { target = e; break; }
            }
            if (!target) return result;
            Vector3f p = target->mSRT.t;
            n->resetPosition(p + Vector3f(45, 0, 45));
            std::printf("P2_BREADBUG_ORD_TARGET type=%d x=%.1f y=%.1f z=%.1f\n", target->mTekiType, p.x, p.y, p.z);
            std::fflush(stdout);
            phase = 1;
        }
        if (phase == 1) {
            if (!target || !target->isAlive()) { phase = 2; std::printf("P2_BREADBUG_ORD_DEATH frame=%u\n", frames); std::fflush(stdout); }
            else {
                const bool hit = target->stimulate(InteractAttack(n, nullptr, 100000, false));
                if (frames % 30 == 0) std::printf("P2_BREADBUG_ORD_ATTACK accepted=%d health=%.1f\n", int(hit), target->mHealth);
            }
        }
        if (phase == 2) {
            if (target && target->mPellet && target->mDeadState == 2) {
                corpse = target->mPellet;
                spawn = corpse->mSRT.t;
                phase = 3;
                std::printf("P2_BREADBUG_ORD_CORPSE ready x=%.1f z=%.1f\n", spawn.x, spawn.z); std::fflush(stdout);
            }
        }
        if (phase >= 3) {
            ++waited;
            // Natural-transport evidence: does the real corpse move toward the Onion?
            if (phase == 3 && waited % 60 == 0) {
                const float dx = corpse ? (corpse->mSRT.t.x - spawn.x) : 0.0f;
                const float dz = corpse ? (corpse->mSRT.t.z - spawn.z) : 0.0f;
                const float moved = std::sqrt(dx * dx + dz * dz);
                if (moved > 40.0f) natural = true;
                std::printf("P2_BREADBUG_ORD_CARRY frame=%u moved=%.2f natural=%d checked=%d\n", frames, moved,
                            int(natural), int(pc_randomizer_checked("Bestiary: Deliver Breadbug")));
                std::fflush(stdout);
            }
            if (phase == 3 && waited > 900) {
                require(corpse != nullptr, "no corpse for endpoint");
                GoalItem* onion = nullptr;
                for (int c = 0; c < 3 && !onion; ++c) onion = itemMgr->getContainer(c);
                require(onion != nullptr, "no Onion in stage");
                std::printf("P2_BREADBUG_ORD_FALLBACK_SUCKME onion=%p natural_carry=%d\n", (void*)onion, int(natural));
                std::fflush(stdout);
                onion->suckMe(corpse);
                phase = 4;
            }
            if (phase == 4 && waited > 1500) {
                const bool checked = pc_randomizer_checked("Bestiary: Deliver Breadbug");
                std::printf("P2_BREADBUG_ORD_RESULT natural_carry=%d checked=%d\n", int(natural), int(checked));
                std::printf(checked ? "PASS P2_BREADBUG_ORDINARY_RECEIPT\n" : "P2_BREADBUG_ORD_NO_CHECK\n");
                std::fflush(stdout);
                std::_Exit(checked ? 0 : 2);
            }
        }
        return result;
    }
};

int main(int argc, char** argv)
{
    SDL_SetMainReady(); pc_gpu_preference_apply(); _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    pc_bbft_init(argc, argv);
    if (!pc_window_init("lane18 breadbug ordinary endpoint", 960, 540)) return 3;
    pc_window_center();
    pc_settings_init(); gsys->Initialise(); pc_settings_p2d_init();
    nodeMgr = new NodeMgr(); gsys->run(new BreadbugOrdinaryApp()); return 0;
}
