// P2 Miulin bury semantics for bound P1 Miurin actors (family lane #221, opt-in).
#include "pc_p2_mamuta_rules.h"
#include "pc_p2_mamuta.h"
#include "pc_bbft.h"
#include "GameStat.h"
#include "Interactions.h"
#include "MapCode.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "Piki.h"
#include "PikiState.h"
#include "StateMachine.h"
#include "teki.h"
#include <cstdio>
#include <cstring>
#include <fstream>

namespace {
bool enabled = false;
const float P2_NAVI_BURY_DAMAGE = 5.0f; // interactNavi.cpp:218-226 (damage only, no bury)
const int P2_BURIED_CAP_US = 99;        // interactPiki.cpp:382-384 (GameStat::mePikis >= 99)
const float P2_VERTICAL_BAND = 20.0f;   // miulinState.cpp:273-274 (+-20 around the attack point)
}

bool pc_p2_mamuta_rules_enabled() { return enabled; }

void pc_p2_mamuta_rules_reset() { enabled = false; }

void pc_p2_mamuta_rules_setup() {
    enabled = false;
    if (!pc_pikipelago_room_preview()) return;
    std::ifstream in("p2-mamuta-rules.txt");
    if (!in) return; // absent marker: P1 behavior retained
    std::string token, trailing;
    if (!(in >> token) || token != "P2_MAMUTA_RULES_1" || (in >> trailing) || in.bad()) {
        std::fputs("P2_MAMUTA invalid rules profile\n", stderr);
        std::abort();
    }
    enabled = true;
    std::puts("P2_MAMUTA_RULES enabled cap=99 navi_damage=5.0 vertical_band=20");
}

int pc_p2_mamuta_bury_piki(Creature* owner, Piki* piki) {
    if (!enabled || !owner || !piki || !pc_p2_mamuta_is_bound(static_cast<BTeki*>(owner))) return -1;
    // P2 rejection order (interactPiki.cpp:377-389): invincible-state approximation first.
    if (!piki->isAlive()) return 0;
    int state = piki->getCurrState() ? piki->getCurrState()->getID() : PIKISTATE_Normal;
    if (state == PIKISTATE_Pressed || state == PIKISTATE_Dying || state == PIKISTATE_Dead) return 0;
    // P2 population cap: 99 planted (US) rejects outright before any terrain work.
    if ((int)GameStat::mePikis >= P2_BURIED_CAP_US) {
        std::puts("P2_MAMUTA_PLANT_REJECT reason=cap99");
        return 0;
    }
    // P2 terrain/manager requirement: non-bald safe ground (P1 checks mirror this).
    if (!piki->isSafeMePos(piki->mSRT.t) || MapCode::isBald(piki->mGroundTriangle)) return 0;
    // P2 vertical band: +-20 around the attack origin (approximated against the owner).
    float dy = piki->mSRT.t.y - owner->mSRT.t.y;
    if (dy > P2_VERTICAL_BAND || dy < -P2_VERTICAL_BAND) return 0;
    // P2 conversion: flower-stage same-kind planted sprout; the actor is removed by
    // PIKISTATE_Bury without a death record (P1 engine Bury comment; P2 CKILL_DontCountAsDeath).
    if (piki->mHappa < Flower) piki->mHappa = Flower;
    piki->mFSM->transit(piki, PIKISTATE_Bury);
    std::printf("P2_MAMUTA_PLANT kind=%d happa=%d planted=%d\n", piki->mColor, piki->mHappa,
                (int)GameStat::mePikis);
    return 1;
}

int pc_p2_mamuta_bury_navi(Creature* owner, Navi* navi) {
    if (!enabled || !owner || !navi || !pc_p2_mamuta_is_bound(static_cast<BTeki*>(owner))) return -1;
    // P2 actNavi: invincible rejection, then damage only - no captain burial.
    NaviState* state = navi->mStateMachine->getNaviState(navi);
    if (state->invincible(navi)) return 0;
    navi->mHealth -= P2_NAVI_BURY_DAMAGE;
    navi->startDamageEffect();
    navi->mLifeGauge.updValue(navi->mHealth, C_NAVI_PARM(navi, mHealth));
    std::printf("P2_MAMUTA_NAVI damage=%.1f health=%.3f\n", P2_NAVI_BURY_DAMAGE, navi->mHealth);
    return 1;
}
