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
#include "PikiState.h"
#include "PikiHeadItem.h"
#include "teki.h"
#include "Generator.h"
#include "ItemMgr.h"
#include "GoalItem.h"
#include "Pellet.h"
#include "Interactions.h"
#include "Route.h"
#include "Demo.h"
#include "PlayerState.h"
#include "PikiAI.h"
#include "pc_randomizer.h"
#include "pc_p2_input_script.h"
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "Dolphin/pad.h"
#include <cstdio>
#include <cstdlib>
#include <cmath>

static const char* TARGET = "Bestiary: Deliver Dwarf Bulborb";

static void require(bool ok, const char* why)
{
    if (!ok) { std::printf("FAIL lane06 ordinary: %s\n", why); std::fflush(nullptr); std::_Exit(1); }
}

// Lane 06 real endpoint probe: with the native randomizer ready in an ordinary
// campaign stage, muster the real squad onto the field (the day start leaves one
// Pikmin out plus Onion sprouts; plucking is a squad-deployment stimulus only),
// deploy it as a free squad around a real Dwarf Bulborb, let the squad kill it,
// then observe the real corpse being naturally carried into the real Onion
// endpoint. The Onion absorption fires GoalItem::suckMe ->
// pc_randomizer_corpse_delivered -> pc_randomizer_check -> checks.txt. No enemy
// health/state is injected and the carry is not injected.
class OrdinaryApp : public PlugPikiApp {
    unsigned frames = 0;
    int phase = 0, waited = 0;
    bool deployed = false;
    bool natural = false;
    bool blockReported = false;
    int otherEnemies = 0, musterPulled = 0;
    Vector3f genPos, actorSpawn, corpseStart, corpseEnd, onionPos;
    Teki* target = nullptr;
    Pellet* corpse = nullptr;
public:
    int countPiki(int* alive)
    {
        int total = 0, live = 0;
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            ++total;
            if (p->isAlive()) ++live;
        }
        if (alive) *alive = live;
        return total;
    }
    int pluckSprouts(Navi* n)
    {
        int pulled = 0;
        Iterator it(itemMgr->getPikiHeadMgr());
        CI_LOOP(it) {
            Creature* c = *it;
            if (c->mObjType != OBJTYPE_Pikihead) continue;
            PikiHeadItem* sprout = static_cast<PikiHeadItem*>(c);
            if (!sprout->canPullout()) continue;
            PikiMgr::meBirthMode = true;
            Piki* p = static_cast<Piki*>(pikiMgr->birth());
            PikiMgr::meBirthMode = false;
            if (!p) continue;
            p->init(n);
            p->initColor(sprout->mSeedColor);
            p->setFlower(sprout->mFlowerStage);
            p->resetPosition(sprout->mSRT.t);
            p->changeMode(PikiMode::FreeMode, n);
            sprout->kill(false);
            ++pulled;
        }
        return pulled;
    }
    int idle() override
    {
        // A tutorial/message overlay pauses gameplay. Tap the pad through the
        // fixture-only input script so the window can be dismissed; this is a
        // harness input, not a gameplay stimulus.
        if (gameflow.mIsTutorialTextActive || gameflow.mIsUIOverlayActive) {
            if ((frames / 15) % 2 == 0) pc_p2_input_script_set(1, KBBTN_A);
            else pc_p2_input_script_clear(1);
        } else {
            pc_p2_input_script_clear(1);
        }
        int result = PlugPikiApp::idle();
        require(++frames < 15000, "startup timeout");
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) { gameflow.mMoviePlayer->requestSkip(); return result; }
        if (!pc_randomizer_ready() || !naviMgr || !tekiMgr || !itemMgr || !pikiMgr) return result;
        Navi* n = naviMgr->getNavi();
        if (!n || gameflow.mPauseAll || gameflow.mIsUIOverlayActive) return result;

        if (phase == 0) {
            int others = 0;
            Iterator it(tekiMgr);
            CI_LOOP(it) {
                auto* e = static_cast<Teki*>(*it);
                if (!e || !e->isAlive()) continue;
                if (e->mTekiType == TEKI_Chappy) { if (!target) target = e; }
                else ++others;
            }
            if (!target) return result;
            otherEnemies = others;
            // Mustering: pluck Onion sprouts so the real squad is on the field.
            if (frames > 60 && musterPulled < 40) musterPulled += pluckSprouts(n);
            int alive = 0, total = countPiki(&alive);
            if (frames % 120 == 0)
                std::printf("P2_ORD_MUSTER frame=%u pikis=%d alive=%d pulled=%d\n", frames, total, alive, musterPulled);
            const bool ready = alive >= 5 || frames > 2400;
            if (!ready) return result;
            genPos = target->mGenerator ? target->mGenerator->mGenPosition : target->mSRT.t;
            actorSpawn = target->mSRT.t;
            n->resetPosition(actorSpawn + Vector3f(40, 0, 40));
            int count = 0;
            Iterator squad(pikiMgr);
            CI_LOOP(squad) {
                Piki* p = static_cast<Piki*>(*squad);
                if (!p->isAlive()) continue;
                float angle = float(count) * 6.2831853f / 20.f;
                Vector3f point = actorSpawn + Vector3f(22 * std::sin(angle), 0, 22 * std::cos(angle));
                p->resetPosition(point);
                p->changeMode(PikiMode::FreeMode, n);
                ++count;
            }
            deployed = count > 0;
            std::printf("P2_ORD_SLOT gen=%.3f,%.3f,%.3f actor=%.3f,%.3f,%.3f chappy=1\n",
                        genPos.x, genPos.y, genPos.z, actorSpawn.x, actorSpawn.y, actorSpawn.z);
            std::printf("P2_ORD_SQUAD free=%d control_others=%d\n", count, otherEnemies);
            std::fflush(stdout);
            phase = 1;
        }
        if (phase == 1) {
            if (!target || !target->isAlive()) {
                std::printf("P2_ORD_DEATH frame=%u\n", frames);
                std::fflush(stdout);
                phase = 2;
            }
        }
        if (phase == 2) {
            if (target && target->mPellet && target->mDeadState == 2) {
                corpse = target->mPellet;
                corpseStart = corpse->mSRT.t;
                for (int c = 0; c < 3 && onionPos.y == 0.0f; ++c) {
                    GoalItem* onion = itemMgr->getContainer(c);
                    if (onion) onionPos = onion->mSRT.t;
                }
                phase = 3;
                std::printf("P2_ORD_CORPSE x=%.3f y=%.3f z=%.3f onion=%.3f,%.3f,%.3f\n",
                            corpseStart.x, corpseStart.y, corpseStart.z, onionPos.x, onionPos.y, onionPos.z);
                std::fflush(stdout);
            }
        }
        if (phase >= 3) {
            ++waited;
            if (phase == 3 && waited % 60 == 0) {
                Vector3f now = corpse ? corpse->mSRT.t : corpseStart;
                float dx = now.x - corpseStart.x, dz = now.z - corpseStart.z;
                float moved = std::sqrt(dx * dx + dz * dz);
                if (moved > 40.0f) natural = true;
                int transporting = 0;
                Iterator squad(pikiMgr);
                CI_LOOP(squad) {
                    Piki* p = static_cast<Piki*>(*squad);
                    if (p->isAlive() && p->mMode == PikiMode::TransportMode) ++transporting;
                }
                int blockflag = playerState && playerState->mDemoFlags.isFlag(DEMOFLAG_CarryPathBlocked);
                if (blockflag && !blockReported) {
                    blockReported = true;
                    int count = routeMgr ? routeMgr->getNumWayPoints('test') : 0;
                    for (int i = 0; i < count; ++i) {
                        WayPoint* wp = routeMgr->getWayPoint('test', i);
                        if (!wp) continue;
                        Vector3f d = wp->mPosition - now;
                        float dist = std::sqrt(d.x * d.x + d.z * d.z);
                        if (dist < 400.0f && (!wp->mIsOpen || (wp->mFlags & WayPointFlags::Pebble))) {
                            std::printf("P2_ORD_WP idx=%d pos=%.3f,%.3f,%.3f open=%d flags=%d dist=%.1f\n",
                                        wp->mIndex, wp->mPosition.x, wp->mPosition.y, wp->mPosition.z,
                                        int(wp->mIsOpen), int(wp->mFlags), dist);
                        }
                    }
                    std::fflush(stdout);
                }
                std::printf("P2_ORD_CARRY frame=%u moved=%.2f natural=%d transporting=%d corpse_alive=%d checked=%d pos=%.3f,%.3f,%.3f blocked=%d\n",
                            frames, moved, int(natural), transporting, int(corpse && corpse->isAlive()),
                            int(pc_randomizer_checked(TARGET)), now.x, now.y, now.z, blockflag);
                std::fflush(stdout);
            }
            if (pc_randomizer_checked(TARGET)) {
                corpseEnd = corpse ? corpse->mSRT.t : corpseStart;
                float dx = corpseEnd.x - corpseStart.x, dz = corpseEnd.z - corpseStart.z;
                float route = std::sqrt(dx * dx + dz * dz);
                std::printf("P2_ORD_RESULT natural_carry=%d route=%.3f frame=%u control_others=%d\n",
                            int(natural), route, frames, otherEnemies);
                std::printf("P2_ORD_ROUTE origin=%.3f,%.3f,%.3f corner=%.3f,%.3f,%.3f onion=%.3f,%.3f,%.3f\n",
                            corpseStart.x, corpseStart.y, corpseStart.z,
                            corpseEnd.x, corpseEnd.y, corpseEnd.z,
                            onionPos.x, onionPos.y, onionPos.z);
                std::printf(natural && deployed ? "PASS P2_ORDINARY_RECEIPT natural\n" : "FAIL P2_ORDINARY_RECEIPT no_natural_carry\n");
                std::fflush(stdout);
                std::_Exit(natural && deployed ? 0 : 2);
            }
            if (waited > 5000) {
                std::printf("P2_ORD_RESULT natural_carry=%d frame=%u checked=0\n", int(natural), frames);
                std::printf("FAIL P2_ORDINARY_RECEIPT no_natural_delivery\n");
                std::fflush(stdout);
                std::_Exit(2);
            }
        }
        return result;
    }
};

int main(int argc, char** argv)
{
    SDL_SetMainReady(); pc_gpu_preference_apply(); _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    pc_bbft_init(argc, argv);
    if (!pc_window_init("lane06 ordinary endpoint", 960, 540)) return 3;
    pc_window_center();
    pc_settings_init(); gsys->Initialise(); pc_settings_p2d_init();
    nodeMgr = new NodeMgr(); gsys->run(new OrdinaryApp()); return 0;
}
