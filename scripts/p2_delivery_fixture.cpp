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
#include "Generator.h"
#include "PelletView.h"
#include "ItemMgr.h"
#include "GoalItem.h"
#include "Pellet.h"
#include "Interactions.h"
#include "pc_randomizer.h"
#include "pc_p2_delivery_host.h"
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cstdio>
#include <cstdlib>
#include <cmath>

static void require(bool ok, const char* why)
{
    if (!ok) { std::printf("FAIL lane06 delivery: %s\n", why); std::fflush(nullptr); std::_Exit(1); }
}

// Lane 06 first real consumer: bind a live P2 source onto the ordinary Chappy host,
// kill it, drive its corpse through the real Onion endpoint (GoalItem::suckMe ->
// pc_randomizer_p2_corpse_delivered) and let the durable ordinary receipt host write the
// exactly-once grant. The source bind here is a labelled fixture intervention (lane 13
// supplies it in a generated session); the kill, corpse, Onion endpoint and durable
// receipt are real. The receipt file path is taken from PIKMIN_P2_RECEIPT_PATH so two
// processes (restart) share one ledger.
class DeliveryApp : public PlugPikiApp {
    unsigned frames = 0;
    int phase = 0, waited = 0;
    bool natural = false;
    Vector3f spawn;
    Teki* target = nullptr;
    PelletView* view = nullptr;
    Pellet* corpse = nullptr;
    const char* receiptPath = nullptr;
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
                if (e && e->mTekiType == TEKI_Chappy && e->isAlive()) { target = e; break; }
            }
            if (!target) return result;
            receiptPath = std::getenv("PIKMIN_P2_RECEIPT_PATH");
            if (!receiptPath || !*receiptPath) receiptPath = "p2-delivery-receipts.txt";
            view = static_cast<PelletView*>(target);
            require(target->mGenerator != nullptr, "target has no generator");
            require(pc_p2_delivery_host_open(receiptPath), "cannot open receipt host");
            pc_randomizer_p2_bind_source(view, 44, target->mGenerator->_70); // labelled bind: Dwarf Orange 44
            Vector3f p = target->mSRT.t;
            n->resetPosition(p + Vector3f(45, 0, 45));
            std::printf("P2_DELIVERY_BOUND source=44 teki_type=%d generator=%u receipt=%s x=%.1f z=%.1f\n",
                        target->mTekiType, target->mGenerator->_70, receiptPath, p.x, p.z);
            std::fflush(stdout);
            phase = 1;
        }
        if (phase == 1) {
            if (!target || !target->isAlive()) { phase = 2; std::printf("P2_DELIVERY_DEATH frame=%u\n", frames); std::fflush(stdout); }
            else { target->stimulate(InteractAttack(n, nullptr, 100000, false)); }
        }
        if (phase == 2) {
            if (target && target->mPellet && target->mDeadState == 2) {
                corpse = target->mPellet;
                spawn = corpse->mSRT.t;
                phase = 3;
                std::printf("P2_DELIVERY_CORPSE ready x=%.1f z=%.1f\n", spawn.x, spawn.z); std::fflush(stdout);
            }
        }
        if (phase >= 3) {
            ++waited;
            if (phase == 3 && waited % 60 == 0) {
                const float dx = corpse ? (corpse->mSRT.t.x - spawn.x) : 0.0f;
                const float dz = corpse ? (corpse->mSRT.t.z - spawn.z) : 0.0f;
                const float moved = std::sqrt(dx * dx + dz * dz);
                if (moved > 40.0f) natural = true;
                std::printf("P2_DELIVERY_CARRY frame=%u moved=%.2f natural=%d\n", frames, moved, int(natural));
                std::fflush(stdout);
            }
            if (phase == 3 && waited > 900) {
                require(corpse != nullptr, "no corpse for endpoint");
                GoalItem* onion = nullptr;
                for (int c = 0; c < 3 && !onion; ++c) onion = itemMgr->getContainer(c);
                require(onion != nullptr, "no Onion in stage");
                std::printf("P2_DELIVERY_SUCKME onion=%p natural_carry=%d\n", (void*)onion, int(natural));
                std::fflush(stdout);
                onion->suckMe(corpse); // real Onion endpoint -> pc_randomizer_p2_corpse_delivered
                phase = 4;
            }
            if (phase == 4 && waited > 1200) {
                std::printf("P2_DELIVERY_RESULT natural_carry=%d receipt=%s\n", int(natural), receiptPath);
                std::printf("PASS P2_DELIVERY_RECEIPT\n");
                std::fflush(stdout);
                std::_Exit(0);
            }
        }
        return result;
    }
};

int main(int argc, char** argv)
{
    setvbuf(stdout, nullptr, _IONBF, 0);
    SDL_SetMainReady(); pc_gpu_preference_apply(); _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    pc_bbft_init(argc, argv);
    if (!pc_window_init("lane06 delivery", 960, 540)) return 3;
    pc_window_center();
    pc_settings_init(); gsys->Initialise(); pc_settings_p2d_init();
    nodeMgr = new NodeMgr(); gsys->run(new DeliveryApp()); return 0;
}
