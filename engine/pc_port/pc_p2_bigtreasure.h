#pragma once

#include <cstddef>

// Isolated BigTreasure (Titan Dweevil, enemy ID 73) weapon-ownership and
// teardown policy for issue #246. Mirrors US GPVE01 rev 0 semantics from
// src/plugProjectNishimuraU/BigTreasure{,State,Attack}.cpp at research
// revision 632af93787b9c95b63f0c13be32b161375ce3a96. It deliberately has no
// actor, pellet, map, damage-receiver, sound or effect dependency; a future
// host integration owns those concerns. All randomness enters as explicit
// host-supplied values (randWeightFloat inputs), so fixtures are
// deterministic and tick at the 30 Hz source rate, never wall clock.
//
// Source gaps the lane defines policy for (audit:
// docs/PIKMIN2_BIGTREASURE_AUDIT.md):
//  1. Weapons still captured at death are never released in source.
//     Lane policy: defeat releases each captured weapon with the same
//     knock-off upward pop (endCapture + (0,100,0)); Louie keeps its source
//     release velocity (0,150,0). No captured pellet may outlive its owner.
//  2. finishWaterAttack() is empty in source: in-flight water bubbles keep
//     flying and hitting until ground impact after any normal state exit.
//     Lane policy preserves that, but defeat force-recycles in-flight
//     bubbles without hit events (attacker is dying; attribution invalid).
//  3. hipdropCallBack returns the negation of damageCallBack
//     (BigTreasure.cpp:281-284). Lane policy preserves this exactly.

struct P2BigTreasureVec3 {
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
};

enum P2BigTreasureWeapon {
    P2BTWEAPON_Elec = 0,
    P2BTWEAPON_Fire = 1,
    P2BTWEAPON_Gas = 2,
    P2BTWEAPON_Water = 3,
    P2BTWEAPON_Count = 4,
};

// Mirrors StateID in include/Game/Entities/BigTreasure.h:57-72.
enum P2BigTreasurePhase {
    P2BT_Dead = 0,
    P2BT_Stay = 1,
    P2BT_Land = 2,
    P2BT_Wait = 3,
    P2BT_ItemWait = 4,
    P2BT_Flick = 5,
    P2BT_PreAttack = 6,
    P2BT_Attack = 7,
    P2BT_PutItem = 8,
    P2BT_DropItem = 9,
    P2BT_Walk = 10,
    P2BT_ItemWalk = 11,
};

struct P2BigTreasureDropEvent {
    int weapon = -1; // P2BigTreasureWeapon, or -1 for Louie
    bool isLouie = false;
    P2BigTreasureVec3 velocity;
};

enum P2BigTreasureDamageResult {
    P2BTDMG_Ignored = 0, // non-Pikmin source, missing coll part, or body hit while armed
    P2BTDMG_Weapon = 1,  // routed to a weapon's HP
    P2BTDMG_Body = 2,    // routed to boss HP (only when no weapons remain)
};

class P2BigTreasureOwnership {
public:
    static constexpr float kWeaponMaxHealth = 6000.0f;
    static constexpr float kPinchSmokeThreshold = 3000.0f;
    static constexpr float kKnockOffPopY = 100.0f;
    static constexpr float kLouiePopY = 150.0f;
    static constexpr float kLandDamageFactor = 0.25f;
    static constexpr float kBitterWeaponFactor = 0.1f;
    static constexpr float kPickWeightBase = 12000.0f;

    P2BigTreasureOwnership();

    // Captures a weapon pellet onto its otakara_* joint at full health.
    void attachWeapon(int weapon);
    void attachLouie();

    bool isWeaponAttached(int weapon) const;
    bool hasAnyWeapon() const;
    int weaponCount() const;
    float weaponHealth(int weapon) const;
    bool louieAttached() const { return mLouieAttached; }

    // Mirrors addTreasureDamage: bittered hits deal 0.1x; returns true when
    // the pinch-smoke threshold (3000) was crossed downward by this hit.
    bool addWeaponDamage(int weapon, float damage, bool bittered);

    // Mirrors isNormalAttack: weapon is in its "normal" parameter set while
    // its health is above 3000.
    bool isNormalAttack(int weapon) const;

    // Mirrors damageCallBack routing (BigTreasure.cpp:248-275). Only Pikmin
    // sources with a collision part count; Land quarters the damage; weapon
    // coll parts route to weapon HP; body damage applies only with zero
    // weapons. `collWeapon` is the weapon index of the hit coll part, or -1
    // for a body part. Outputs pinch-smoke transitions through
    // `outPinchSmoke` when non-null.
    P2BigTreasureDamageResult damageCallBack(bool fromPiki, bool hasCollPart, int collWeapon,
                                             float damage, P2BigTreasurePhase state, bool bittered,
                                             bool* outPinchSmoke = nullptr);

    // Mirrors hipdropCallBack (BigTreasure.cpp:281-284): returns the
    // negation of the equivalent damageCallBack decision. Source gap 3.
    bool hipdropCallBack(bool fromPiki, bool hasCollPart, int collWeapon,
                         float damage, P2BigTreasurePhase state, bool bittered);

    // Mirrors updateTreasure -> dropTreasure: every weapon at HP 0 is
    // released with the upward knock-off pop. Appends drop events (weapons
    // only; Louie is never dropped by damage).
    std::size_t update(P2BigTreasureDropEvent* outDrops, std::size_t maxDrops);

    // Body exposure (tam1/tam2 reconfiguration in setupBigTreasureCollision):
    // the body only becomes damageable once every weapon is gone.
    bool isBodyExposed() const { return !hasAnyWeapon(); }

    // Health-weighted next-weapon pick (setTreasureAttack): weight per live
    // weapon is kPickWeightBase - health, bands ordered elec/fire/gas/water.
    // `threshold` is the host's randWeightFloat(totalWeights) input. Returns
    // the chosen weapon or -1 (BIGATTACK_NULL) when nothing is attached.
    int pickWeapon(float threshold) const;

    // Mirrors releaseItemLoozy; appends one event when Louie was captured.
    bool releaseLouie(P2BigTreasureDropEvent* outDrop);

    // Lane teardown for source gap 1: defeat releases every still-captured
    // weapon with the standard knock-off pop, then Louie at its source
    // velocity. Returns the number of events written.
    std::size_t defeat(P2BigTreasureDropEvent* outDrops, std::size_t maxDrops);

private:
    // Lane 32 persistence proposal (#246): engine-free serialization access
    // defined in pc_p2_bigtreasure_save.cpp. This grants no runtime hooks and
    // is not wired into the game save path.
    friend struct P2BigTreasureSaveAccess;

    bool mAttached[P2BTWEAPON_Count];
    float mHealth[P2BTWEAPON_Count];
    bool mLouieAttached;
};

// Mirrors isAttackLimitTime (BigTreasure.cpp:356-403). The threshold is
// 4 + 2 * liveWeapons seconds; the timer accrues at 3x while an unstuck
// outsider is nearby; an attack is only allowed when a live Navi/Pikmin is
// inside the 225-unit XZ box.
class P2BigTreasureAttackPacer {
public:
    static constexpr float kBoxHalfExtent = 225.0f;

    // `initialTimer` is the host's randWeightFloat(2.0) input.
    void reset(float initialTimer) { mTimer = initialTimer; }

    // Returns true when an attack may start this tick.
    bool tick(float delta, int liveWeapons, bool targetInBox, bool unstuckOutsiderNearby);

    float timer() const { return mTimer; }

private:
    float mTimer = 0.0f;
};

// Weapon-loss guards shared by ItemWait/PreAttack/Attack/PutItem
// (BigTreasureState.cpp:375-377,497-505,573-581,642-650): losing every
// weapon exits to DropItem; losing the chosen weapon mid-charge/attack
// re-enters PreAttack (init re-runs pick). Other states pass through.
P2BigTreasurePhase p2_bigtreasure_weapon_loss_guard(P2BigTreasurePhase current, bool anyWeapons,
                                                    bool chosenWeaponAlive);

// Pooled attack node lifetimes (BigTreasureAttackMgr constructor,
// BigTreasureAttack.cpp:1043-1097). Capacities are source-fixed. Emission
// silently skips when a pool is exhausted (`if (mXxxAttackNodes->mChild)`).
// finishAttack() clears started flags, recycles fire/gas/elec nodes, and
// intentionally leaves water nodes in flight (empty finishWaterAttack).
// defeat() is the lane teardown: it force-recycles everything, including
// in-flight water bubbles, without hit events (source gap 2).
class P2BigTreasureAttackPools {
public:
    static constexpr int kFireCapacity = 8;
    static constexpr int kGasCapacity = 200;
    static constexpr int kWaterCapacity = 16;
    static constexpr int kElecCapacity = 17; // 1 invisible anchor + 16 visible max

    P2BigTreasureAttackPools();

    int capacity(int element) const;
    int inFlight(int element) const;
    bool isStarted(int element) const;

    // Mirrors start*Attack: no-op when already started.
    bool start(int element);
    // Mirrors startNew*List emission: fails softly at pool exhaustion.
    bool emit(int element);
    // Recycles one node (ground hit for water, finish for elec, extent
    // reached for fire/gas). Returns false when nothing was in flight.
    bool recycleOne(int element);

    // Sets the elec discharge count (mElecMaxNodes). Source invariant:
    // 1 anchor + maxDischarge visible nodes must fit the 17-node pool;
    // startNewElecList dereferences the next node while chaining.
    bool setElecMaxDischarge(int maxNodes);

    // Mirrors finishAttack: stops all controllers; fire/gas/elec nodes are
    // recycled, water nodes keep flying (source gap 2, preserved).
    void finishAttack();
    // Bitter + lost-weapon force-finish guard (BigTreasureAttack.cpp:1167-1175).
    void bitterWeaponLost(int element);

    // Lane teardown: recycle every node of every element, including
    // in-flight water bubbles (no hit events).
    void defeat();

private:
    // Lane 32 persistence proposal (#246): see P2BigTreasureOwnership above.
    friend struct P2BigTreasureSaveAccess;

    int poolIndex(int element) const;
    bool mStarted[P2BTWEAPON_Count];
    int mInFlight[P2BTWEAPON_Count];
    int mElecMaxNodes;
};
