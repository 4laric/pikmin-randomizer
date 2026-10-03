#include "pc_p2_ship.h"
#include "pc_p2_ship_store.h"
#include "pc_p2_purple.h"
#include "pc_p2_white.h"
#include "pc_p2_white_campaign_policy.h"
#include "pc_p2_white_treasure_policy.h"
#include "pc_p2_campaign_economy.h"
#include "pc_p2_campaign_treasure_state.h"
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
#include <cstdlib>

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
    if (!p2whitecampaign::withdrawal_enabled(pc_randomizer_purple_campaign(), pc_p2_purples_enabled(),
            pc_randomizer_white_campaign() && pc_p2_whites_enabled(), species)
        || !navi || !navi->isAlive() || !pikiMgr || !itemMgr || !itemMgr->getUfo()) return nullptr;
    if (int(GameStat::mapPikis) + itemMgr->getContainerExitCount() >= pc_randomizer_field_capacity()) return nullptr;
    const int maturity = p2whitecampaign::maturity(p2ship::stock, species);
    if (maturity < 0) return nullptr;
    Piki* p = static_cast<Piki*>(pikiMgr->birth());
    if (!p) return nullptr; // Never consume stock before successful allocation.
    GameStat::workPikis.inc(Red);
    p->init(navi); p->initColor(Red); p->setFlower(maturity);
    if (species == 4) pc_p2_make_white(p); else pc_p2_make_purple(p);
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
    if (!active || !pc_randomizer_purple_campaign() || !navi || !itemMgr) return;
    UfoItem* ship = itemMgr->getUfo();
    if (!ship) return;
    const Vector3f delta = navi->mSRT.t - ship->getGoalPos();
    if (delta.x * delta.x + delta.z * delta.z > 180.0f * 180.0f) return;
    static int choice[2] = {3,3};
    const int captain = navi->mNaviID == 1 ? 1 : 0;
    const bool whiteLoaded = pc_randomizer_white_campaign() && pc_p2_whites_enabled();
    if (!whiteLoaded) choice[captain] = 3;
    if (pressed && (keys[SDL_SCANCODE_LCTRL] || keys[SDL_SCANCODE_RCTRL])) {
        choice[captain] = p2whitecampaign::next_choice(choice[captain], whiteLoaded);
        std::printf("P2_SHIP_CHOICE captain=%d species=%d\n",captain,choice[captain]);
    }
    if (whiteLoaded) {
        std::string economy;
        if (pc_randomizer_white_treasure_campaign() || p2treasurestate::state.active()) {
            static p2treasure::Catalog catalog;
            static const bool catalogReady = [] {
                const char* path = std::getenv("PIKMIN_P2_TREASURE_CATALOG");
                return catalog.load_retail(path && path[0] ? path : "p2-treasure-catalog.txt");
            }();
            if (catalogReady && p2treasurestate::state.active()) {
                const auto progress=p2treasurestate::state.progress(catalog,
                    pc_randomizer_white_treasure_campaign() && p2whitetreasure::ledger.delivered);
                const char* phase=progress.phase()==p2economy::Phase::Complete ? "Complete"
                    : progress.phase()==p2economy::Phase::TreasureHunt ? "Treasure Hunt" : "Repaying Debt";
                economy=std::to_string(progress.pokos)+" Pokos | Debt "+std::to_string(progress.remaining())
                    +" | "+std::to_string(progress.collected)+"/201 | "+phase+" | ";
            } else economy = p2economy::ship_summary(p2whitetreasure::ledger.delivered, catalogReady ? &catalog : nullptr) + " | ";
        }
        char title[320];const auto& counts=p2ship::stock.counts[choice[captain]-3];
        std::snprintf(title,sizeof(title),"Pikipelago Ship: %s%s (%d leaf/%d bud/%d flower) | F10 withdraw, Shift+F10 deposit, Ctrl+F10 species",economy.c_str(),choice[captain]==4?"White":"Purple",counts[0],counts[1],counts[2]);
        if(SDL_Window* window=SDL_GetKeyboardFocus())SDL_SetWindowTitle(window,title);
    }
    if (!pressed || keys[SDL_SCANCODE_LCTRL] || keys[SDL_SCANCODE_RCTRL]) return;
    if (keys[SDL_SCANCODE_LSHIFT] || keys[SDL_SCANCODE_RSHIFT]) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!pc_p2_ship_special(p) || p->mNavi != navi || p->mMode != PikiMode::FormationMode
                || p->getState() != PIKISTATE_Normal || p->isHolding() || p->isStickTo()) continue;
            const Vector3f d = p->mSRT.t - ship->getGoalPos();
            if (d.x*d.x + d.z*d.z <= 240.0f*240.0f && pc_p2_ship_deposit(p)) it.dec();
        }
    } else pc_p2_ship_withdraw(navi, choice[captain]);
}
