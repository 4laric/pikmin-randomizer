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
#include <cstring>
#include <cmath>
#include <string>

static void require(bool ok, const char* why)
{
    if (!ok) { std::printf("FAIL ordinary: %s\n", why); std::fflush(nullptr); std::_Exit(1); }
}

// Ordinary Onion endpoint probe (parameterised): with the native randomizer ready
// in an ordinary campaign stage, kill an actual enemy of the requested Teki type,
// then drive its real corpse through the Onion absorption endpoint
// (GoalItem::suckMe -> pc_randomizer_corpse_delivered -> pc_randomizer_check ->
// checks.txt) for the requested bestiary check name. Natural Pikmin carry is
// attempted first; a labeled fallback calls the same endpoint directly if the
// carry stalls. `--enemy-type <int>` and `--check <name>` select the target
// (defaults preserve lane 06's Dwarf Bulborb probe).
class OrdinaryApp : public PlugPikiApp {
    unsigned frames = 0;
    int phase = 0, waited = 0;
    bool natural = false;
    Vector3f spawn;
    Teki* target = nullptr;
    Pellet* corpse = nullptr;
    int enemyType;
    std::string checkName;
public:
    OrdinaryApp(int type, std::string check) : enemyType(type), checkName(std::move(check)) {}

    int idle() override
    {
        int result = PlugPikiApp::idle();
        require(++frames < 9000, "startup timeout");
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) { gameflow.mMoviePlayer->requestSkip(); return result; }
        if (!pc_randomizer_ready() || !naviMgr || !tekiMgr || !itemMgr || !pikiMgr) return result;

        // Phase 4 result polling runs before the pause/overlay guard so a UI
        // toast raised by corpse delivery cannot stall the exit deterministically.
        if (phase == 4) {
            if (++waited > 1500) {
                const bool checked = pc_randomizer_checked(checkName.c_str());
                std::printf("P2_ORD_RESULT natural_carry=%d checked=%d\n", int(natural), int(checked));
                std::printf(checked ? "PASS P2_ORDINARY_RECEIPT\n" : "P2_ORD_NO_CHECK\n");
                std::fflush(stdout);
                std::_Exit(checked ? 0 : 2);
            }
            return result;
        }

        Navi* n = naviMgr->getNavi();
        if (!n) return result;

        if (phase == 0) {
            Iterator it(tekiMgr);
            CI_LOOP(it) {
                auto* e = static_cast<Teki*>(*it);
                if (e && e->mTekiType == enemyType && e->isAlive()) { target = e; break; }
            }
            if (!target) return result;
            Vector3f p = target->mSRT.t;
            n->resetPosition(p + Vector3f(45, 0, 45));
            std::printf("P2_ORD_TARGET type=%d x=%.1f y=%.1f z=%.1f\n", target->mTekiType, p.x, p.y, p.z);
            std::fflush(stdout);
            phase = 1;
        }
        if (phase == 1) {
            if (!target || !target->isAlive()) { phase = 2; std::printf("P2_ORD_DEATH frame=%u\n", frames); std::fflush(stdout); }
            else {
                const bool hit = target->stimulate(InteractAttack(n, nullptr, 100000, false));
                if (frames % 30 == 0) std::printf("P2_ORD_ATTACK accepted=%d health=%.1f\n", int(hit), target->mHealth);
            }
        }
        if (phase == 2) {
            if (target && target->mPellet && target->mDeadState == 2) {
                corpse = target->mPellet;
                spawn = corpse->mSRT.t;
                phase = 3;
                waited = 0;
                std::printf("P2_ORD_CORPSE ready x=%.1f z=%.1f\n", spawn.x, spawn.z); std::fflush(stdout);
            }
        }
        if (phase == 3) {
            ++waited;
            if (waited % 60 == 0) {
                const float dx = corpse ? (corpse->mSRT.t.x - spawn.x) : 0.0f;
                const float dz = corpse ? (corpse->mSRT.t.z - spawn.z) : 0.0f;
                const float moved = std::sqrt(dx * dx + dz * dz);
                if (moved > 40.0f) natural = true;
                std::printf("P2_ORD_CARRY frame=%u moved=%.2f natural=%d checked=%d\n", frames, moved,
                            int(natural), int(pc_randomizer_checked(checkName.c_str())));
                std::fflush(stdout);
            }
            if (waited > 900) {
                require(corpse != nullptr, "no corpse for endpoint");
                GoalItem* onion = nullptr;
                for (int c = 0; c < 3 && !onion; ++c) onion = itemMgr->getContainer(c);
                require(onion != nullptr, "no Onion in stage");
                std::printf("P2_ORD_FALLBACK_SUCKME onion=%p natural_carry=%d\n", (void*)onion, int(natural));
                std::fflush(stdout);
                onion->suckMe(corpse);
                phase = 4;
                waited = 0;
            }
        }
        return result;
    }
};

int main(int argc, char** argv)
{
    int enemyType = 3; // TEKI_Chappy (lane 06 default)
    std::string checkName = "Bestiary: Deliver Dwarf Bulborb";
    for (int i = 1; i < argc; ++i) {
        if (!std::strcmp(argv[i], "--enemy-type") && i + 1 < argc) { enemyType = std::atoi(argv[++i]); }
        else if (!std::strcmp(argv[i], "--check") && i + 1 < argc) { checkName = argv[++i]; }
    }

    SDL_SetMainReady(); pc_gpu_preference_apply(); _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    pc_bbft_init(argc, argv);
    if (!pc_window_init("ordinary endpoint", 960, 540)) return 3;
    pc_window_center();
    pc_settings_init(); gsys->Initialise(); pc_settings_p2d_init();
    nodeMgr = new NodeMgr(); gsys->run(new OrdinaryApp(enemyType, checkName)); return 0;
}
