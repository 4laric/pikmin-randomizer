#pragma once
// Engine-free Otakara treasure pickup / carry / drop policy (Dweevil family 59-62).
//
// Owner playtest 2026-09-30: "never saw it pick up a treasure". The port had no item states at
// all (pc_p2_otakara.cpp header: "The item-carry (5..10) states are source-backed N/A: no
// treasure payload is staged"), so a Dweevil could only wait, flee and flick. This header
// encodes the source decisions the engine glue now runs:
//
//   * OtakaraBase::Obj::isMovePositionSet(ignoringTreasures)    OtakaraBase.cpp:361-389
//       treasure search runs only when mItemSearchDelayTimer > fp21 (2.5 s); otherwise the
//       timer advances by dt. A treasure target wins over any Pikmin/Navi.
//   * OtakaraBase::Obj::getNearestTreasure                      OtakaraBase.cpp:395-417
//       alive, not captured, pickable pellet whose XZ distance to HOME is < territory (fp09
//       200) and to the Dweevil is < sight (fp12 200); nearest wins (strict <).
//   * OtakaraBase::Obj::isTakeTreasure                          OtakaraBase.cpp:472-489
//       3D distance < max(50, 20 + pickRadius).
//   * OtakaraBase::Obj::takeTreasure / fallTreasure / resetTreasure  OtakaraBase.cpp:493-548
//       treasure health = fp01 (otakara life: 80, Munge 100), body part moves up by half the
//       cylinder height and grows to the pick radius; fallTreasure(true) pops it up at
//       (0,100,0).
//   * OtakaraBase::Obj::isDropTreasure / damageTreasure         OtakaraBase.cpp:550-574
//       while carrying, every damage callback reduces TREASURE health (the Dweevil's own life
//       is untouched); at <= 0 the state machine drops the treasure. Hipdrop and earthquake
//       while carrying take the full otakara life (OtakaraBase.cpp:203-231).
//   * StateTake / StateItem* / StateItemDrop                    OtakaraBaseState.cpp:349-740
//       Take -> (treasure ? (drop ? ItemDrop : flick ? ItemFlick : ItemMove) : ItemDrop);
//       Item states flee exactly like the normal ones but ignore treasures
//       (isMovePositionSet(true)); ItemFlick uses the fp11 otakara-attack timer (1.25 s);
//       ItemDrop returns to Flick/Move/Turn/Wait and, on cleanup, restarts the pickup delay.
//
// No engine types: the glue in pc_p2_otakara.cpp feeds plain numbers in and acts on the result.
#include "pc_p2_otakara_move.h"

namespace p2otakaraitem {

using p2otakaramove::St;
using p2otakaramove::Vec2;

constexpr float kCatchDelay = 2.5f;       // OtakaraBase::Parms fp21 treasure catch (retail 2.5)
constexpr float kNormalAttack = 1.0f;     // fp10 normal attack timer
constexpr float kOtakaraAttack = 1.25f;   // fp11 otakara attack timer (carrying)
constexpr float kSearchOpen = 12800.0f;   // OtakaraBase.cpp:59 initial mItemSearchDelayTimer
constexpr float kMinTakeRadius = 50.0f;   // OtakaraBase.cpp:478
constexpr float kTakeMargin = 20.0f;      // OtakaraBase.cpp:477
constexpr float kDropPopVelocityY = 100.0f; // fallTreasure(true), OtakaraBase.cpp:536

// Retail fp01 "otakara life" (docs/PIKMIN2_DWEEVIL_ASSETS.md section 4): 80 for Fire, Water,
// Elec and Bomb; 100 for Gas (Munge).
inline float otakaraLife(int species) { return species == 61 ? 100.0f : 80.0f; }

// A candidate pellet as the glue measures it. `y` is the pellet base height.
struct Pellet {
    Vec2 pos;
    float y;
    float pickRadius;
    float height; // cylinder height
    bool alive;
    bool captured;  // already held (mCaptureMatrix in the source)
    bool pickable;  // isPickable(): not carried, not a ship part, not in a goal
};

// isMovePositionSet's gate (OtakaraBase.cpp:363-368). Returns true when the treasure search
// runs this frame; otherwise the delay timer advances.
inline bool searchOpen(float& timer, float dt, bool ignoringTreasures) {
    if (!ignoringTreasures && timer > kCatchDelay) return true;
    timer += dt;
    return false;
}

// getNearestTreasure (OtakaraBase.cpp:395-417). Returns an index or -1.
inline int nearestTreasure(const Pellet* p, int n, Vec2 self, Vec2 home, float sight, float territory) {
    int pick = -1;
    float best = sight * sight;
    for (int i = 0; i < n; ++i) {
        if (!p[i].alive || p[i].captured || !p[i].pickable) continue;
        if (p2otakaramove::distSqXZ(p[i].pos, home) >= territory * territory) continue;
        const float d = p2otakaramove::distSqXZ(p[i].pos, self);
        if (d < best) { best = d; pick = i; }
    }
    return pick;
}

// isTakeTreasure (OtakaraBase.cpp:472-489): |treasure - Dweevil| (3D) < max(50, 20 + pick).
inline float takeRadius(float pickRadius) {
    const float r = kTakeMargin + pickRadius;
    return r < kMinTakeRadius ? kMinTakeRadius : r;
}
inline bool isTake(float distance3d, float pickRadius) { return distance3d < takeRadius(pickRadius); }

// Carry bookkeeping (mTreasure / mTreasureHealth).
struct Hold {
    bool holding = false;
    float health = 0.0f;
};

inline void grab(Hold& h, float life) {
    h.holding = true;
    h.health = life;
}
inline void release(Hold& h) {
    h.holding = false;
    h.health = 0.0f;
}

// isDropTreasure (OtakaraBase.cpp:550-557): true when there is no health left (also true
// when nothing is held, which the state machine never asks).
inline bool isDrop(const Hold& h) { return !(h.health != 0.0f && h.health > 0.0f); }

struct DamageRoute {
    bool toTreasure; // absorbed by the carried treasure
    bool addDamage;  // reaches the Dweevil's own life (addDamage(damage, 1.0f))
};

// damageTreasure(damage) (OtakaraBase.cpp:563-574).
inline DamageRoute damageTreasure(Hold& h, float damage) {
    if (h.holding) {
        h.health -= damage;
        if (h.health < 0.0f) h.health = 0.0f;
        return {true, false};
    }
    return {false, true};
}

// hipdropCallBack / earthquakeCallBack (OtakaraBase.cpp:203-231): carrying takes the full
// otakara life, otherwise the plain damage (earthquake does nothing when empty-handed).
inline float hipdropDamage(const Hold& h, float damage, float life) { return h.holding ? life : damage; }

struct In {
    St cur;
    bool hasTarget;   // isMovePositionSet(ignoringTreasures) found something
    bool facing;      // |angDist| <= THIRD_PI
    bool takeNow;     // isTakeTreasure() (a treasure target within reach)
    bool flick;       // isStartFlick
    bool drop;        // isDropTreasure
    bool dead;        // mHealth <= 0
};

// The state requested this frame (mNextState), or `cur` for none. Sources:
// Wait 165-199, Move 225-269, Turn 297-334, ItemWait 415-452, ItemMove 475-526,
// ItemTurn 551-594 (OtakaraBaseState.cpp). Take/ItemFlick/ItemDrop/Flick transit on their
// clip end through the after* helpers below.
inline St decide(const In& in) {
    St next = in.cur;
    switch (in.cur) {
    case St::Wait:
    case St::Move:
    case St::Turn:
        if (in.hasTarget) {
            if (in.facing) {
                next = St::Move;
                if (in.takeNow) next = St::Take;
            } else {
                next = St::Turn;
            }
        } else if (in.cur != St::Wait) {
            next = St::Wait;
        }
        if (in.flick) next = St::Flick;
        if (in.dead) next = St::Dead;
        break;
    case St::ItemWait:
    case St::ItemMove:
    case St::ItemTurn:
        if (in.hasTarget) {
            next = in.facing ? St::ItemMove : St::ItemTurn;
        } else if (in.cur != St::ItemWait) {
            next = St::ItemWait;
        }
        if (in.flick) next = St::ItemFlick;
        if (in.drop) next = St::ItemDrop;
        break;
    default:
        break;
    }
    return next;
}

// StateTake KEYEVENT_END (OtakaraBaseState.cpp:373-389).
inline St afterTake(bool holding, bool drop, bool flick) {
    if (!holding) return St::ItemDrop;
    if (drop) return St::ItemDrop;
    if (flick) return St::ItemFlick;
    return St::ItemMove;
}

// StateItemFlick KEYEVENT_END (OtakaraBaseState.cpp:646-665).
inline St afterItemFlick(bool drop, bool hasTarget, bool facing) {
    if (drop) return St::ItemDrop;
    if (hasTarget) return facing ? St::ItemMove : St::ItemTurn;
    return St::ItemWait;
}

// StateItemDrop KEYEVENT_END (OtakaraBaseState.cpp:703-729).
inline St afterItemDrop(bool dead, bool flick, bool hasTarget, bool facing) {
    if (dead) return St::Dead;
    if (flick) return St::Flick;
    if (hasTarget) return facing ? St::Move : St::Turn;
    return St::Wait;
}

// Flick / ItemFlick finishMotion gate: the attack timer passes fp10 / fp11.
inline bool attackTimerDone(bool carrying, float timer) {
    return timer > (carrying ? kOtakaraAttack : kNormalAttack);
}

inline bool isItemState(St s) {
    return s == St::Take || s == St::ItemWait || s == St::ItemMove || s == St::ItemTurn
        || s == St::ItemFlick || s == St::ItemDrop;
}

} // namespace p2otakaraitem
