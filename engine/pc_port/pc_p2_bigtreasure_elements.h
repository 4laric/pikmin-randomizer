#pragma once

#include "pc_p2_bigtreasure_attacks.h"

// Lane-owned persistent element-controller runtime for the BigTreasure
// ordinary encounter (#246). The FSM host starts an attack through the attack
// pools (lifetime ledger); this module owns the actual per-element node motion
// so a started attack is not inert in ordinary play. It reuses the existing
// source policies (fire/gas/water/elec) and the lane terrain/trace adapter; the
// Pikmin-damage receiver is lane 10's boundary and is intentionally not
// invented here.
//
// Engine-free: the map trace/ground are injected through P2BigTreasureElementHost.

struct P2BigTreasureElementHost {
    void* context = nullptr;
    P2BigTreasureTraceFn trace = nullptr;   // elec sphere trace
    P2BigTreasureGroundFn ground = nullptr; // water bubble impact sample
};

struct P2BigTreasureElementStats {
    int nodes = 0;      // currently active nodes for the running element
    int emits = 0;      // nodes spawned this tick
    int bounces = 0;    // elec floor-bounce events this tick
    int groundHits = 0; // water ground impacts this tick
};

class P2BigTreasureElementRuntime {
public:
    // Starts the source controller for `weapon` at `origin` (boss base) on a
    // floor at `groundHeight`, scaled by the weapon's current health. The
    // damaged-set and elec pick inputs are host randWeightFloat values.
    bool start(int weapon, const P2BigTreasureVec3& origin, float groundHeight,
               float weaponHealth, float damagedPick, float pick01);

    // Mirrors finishAttack: stops emission; fire/gas/elec recycle, water keeps
    // flying (source gap 2, preserved by the policy).
    void finish();

    // Lane teardown: force-recycle everything, including in-flight water.
    void defeat();
    void reset();

    bool active() const { return mWeapon >= 0; }
    int activeWeapon() const { return mWeapon; }

    // One 30 Hz source tick for the running element.
    void tick(float delta, const P2BigTreasureElementHost& host,
              P2BigTreasureElementStats& out);

    // Detection only: true when the running element's source hit geometry
    // registers on `target`. Applying damage is the lane-10 receiver's job;
    // this lets an ordinary-update consumer observe that an emitted node
    // intersects a live target. `outIndex` receives the node/arm index.
    bool queryHit(const P2BigTreasureVec3& target, int* outIndex = nullptr) const;

private:
    int mWeapon = -1;
    float mGround = 0.0f;
    P2BigTreasureVec3 mOrigin{};
    int mGasArms = 3;
    P2BigTreasureFirePolicy mFire;
    P2BigTreasureGasPolicy mGas;
    P2BigTreasureWaterPolicy mWater;
    P2BigTreasureElecPolicy mElec;
    int mPrevNodes = 0;
};
