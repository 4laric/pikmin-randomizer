#include "pc_p2_ship.h"
#include "pc_p2_ship_store.h"
#include "pc_p2_purple.h"
#include "pc_randomizer.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "PikiHeadItem.h"
#include "Navi.h"
#include "ItemMgr.h"
#include "UfoItem.h"
#include "GameStat.h"
#include <SDL2/SDL.h>
#include <cstdio>

bool pc_p2_ship_special(const Piki* p) {
    return pc_randomizer_purple_campaign() && p && (p->mP2Purple || p->mP2White);
}
bool pc_p2_ship_deposit(Piki* p) {
    if (!pc_p2_ship_special(p) || !p->isAlive()) return false;
    const int species = p->mP2White ? 4 : 3;
    if (!p2ship::stock.add(species, p->mHappa)) return false;
    const int maturity = p->mHappa;
    p->setEraseKill(); p->kill(false);
    GameStat::update();
    std::printf("P2_SHIP_DEPOSIT species=%d maturity=%d stored=%d\n", species, maturity, p2ship::stock.total());
    return true;
}
bool pc_p2_ship_store_sprout(PikiHeadItem* p) {
    if (!pc_randomizer_purple_campaign() || !p || (!p->mP2Purple && !p->mP2White)) return false;
    return p2ship::stock.add(p->mP2White ? 4 : 3, p->mFlowerStage);
}
Piki* pc_p2_ship_withdraw(Navi* navi, int species) {
    // White has a reserved compartment, but no enabled campaign actor/provider.
    if (!pc_randomizer_purple_campaign() || !pc_p2_purples_enabled() || species != 3
        || !navi || !navi->isAlive() || !pikiMgr || !itemMgr || !itemMgr->getUfo()) return nullptr;
    if (int(GameStat::mapPikis) + itemMgr->getContainerExitCount() >= pc_randomizer_field_capacity()) return nullptr;
    int maturity = 2;
    while (maturity >= 0 && !p2ship::stock.counts[0][maturity]) --maturity;
    if (maturity < 0) return nullptr;
    Piki* p = static_cast<Piki*>(pikiMgr->birth());
    if (!p) return nullptr; // Never consume stock before successful allocation.
    GameStat::workPikis.inc(Red);
    p->init(navi); p->initColor(Red); p->setFlower(maturity);
    pc_p2_make_purple(p);
    Vector3f position = navi->mSRT.t;
    p->resetPosition(position);
    p->mFSM->transit(p, PIKISTATE_Normal);
    p->changeMode(PikiMode::FormationMode, navi);
    p2ship::stock.take(species, maturity);
    GameStat::update();
    std::printf("P2_SHIP_WITHDRAW species=%d maturity=%d stored=%d\n", species, maturity, p2ship::stock.total());
    return p;
}
void pc_p2_ship_tick(Navi* navi, bool active) {
    const Uint8* keys = SDL_GetKeyboardState(nullptr);
    const bool down = keys && keys[SDL_SCANCODE_F10];
    static bool previous = false;
    const bool pressed = down && !previous; previous = down;
    if (!pressed || !active || !pc_randomizer_purple_campaign() || !navi || !itemMgr) return;
    UfoItem* ship = itemMgr->getUfo();
    if (!ship) return;
    const Vector3f delta = navi->mSRT.t - ship->getGoalPos();
    if (delta.x * delta.x + delta.z * delta.z > 180.0f * 180.0f) return;
    if (keys[SDL_SCANCODE_LSHIFT] || keys[SDL_SCANCODE_RSHIFT]) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!pc_p2_ship_special(p) || p->mNavi != navi || p->mMode != PikiMode::FormationMode
                || p->getState() != PIKISTATE_Normal || p->isHolding() || p->isStickTo()) continue;
            const Vector3f d = p->mSRT.t - ship->getGoalPos();
            if (d.x*d.x + d.z*d.z <= 240.0f*240.0f && pc_p2_ship_deposit(p)) it.dec();
        }
    } else pc_p2_ship_withdraw(navi, 3);
}
