#pragma once

#include "pc_p2_bigtreasure.h"

// Isolated per-element attack controller policies for BigTreasure (Titan
// Dweevil), issue #246. Mirrors US GPVE01 rev 0 semantics from
// src/plugProjectNishimuraU/BigTreasureAttack.cpp (BTA) and
// BigTreasure.cpp (BTC) at research revision
// 632af93787b9c95b63f0c13be32b161375ce3a96. No actor, map, damage-receiver,
// sound or effect dependency. Ticks are the 30 Hz source rate; all
// randomness enters as explicit host-supplied values. The lane-owned host
// terrain/trace adapter interface below follows the #169 Groink pattern; a
// future host integration supplies the real P1 map trace.

// ---------------------------------------------------------------------------
// Lane-owned host terrain/trace adapter interface (interface only; the host
// implements it, fixtures provide a mock). Mirrors the Groink P2GroinkTraceFn
// shape: one call per node per source update, with a mutable velocity like
// traceMove's MoveInfo.

struct P2BigTreasureTraceResult {
    P2BigTreasureVec3 position;
    P2BigTreasureVec3 velocity; // trace-mutated velocity (bounce applied)
    bool floor = false;
    bool wall = false;
    float groundY = 0.0f; // valid when hasGroundY (getMinY equivalent)
    bool hasGroundY = false;
};

// Sphere trace for elec bounce nodes. `bounceFactor` is the source MoveInfo
// bounce coefficient; the adapter applies bounces and reports contacts.
// Return false only when no trace was performed.
typedef bool (*P2BigTreasureTraceFn)(void* context, const P2BigTreasureVec3& position,
                                     const P2BigTreasureVec3& velocity, float delta, float radius,
                                     float bounceFactor, P2BigTreasureTraceResult& result);

// Ground height query (mapMgr->getMinY equivalent) for water bubble impact.
// Return false when no map is loaded.
typedef bool (*P2BigTreasureGroundFn)(void* context, float x, float z, float* outY);

// ---------------------------------------------------------------------------
// Shared parameter selection: strict > 3000 HP normal/damaged boundary
// (BTC isNormalAttack :1200-1203).

struct P2BigTreasureFireParams {
    float scale; // 1.0 normal, 1.25 damaged (parms ff00/ff10)
};
struct P2BigTreasureGasParams {
    int armNum;           // 3 normal, 4 damaged
    float rotationSpeed;  // rad per source update (fg00/fg10)
    float reversalTime;   // seconds (30 normal; 30 or 2 damaged)
};
struct P2BigTreasureWaterParams {
    float shotInterval;   // 0.5 normal, 0.25 damaged (fw00/fw10)
    float jitterAngle;    // fw01/fw11
    float jitterDistance; // fw02/fw12
};
struct P2BigTreasureElecParams {
    float bounceFactor;
    float frictionFactor;
    float baseHSpeed;
    float jitterHSpeed;
    float baseVSpeed;
    float jitterVSpeed;
    float scatterTime;     // discharge start (fe*6)
    float chainInterval;   // fe*8
    int maxDischarge;      // fe*7; 1 anchor + maxDischarge <= 17
};

P2BigTreasureFireParams p2_bigtreasure_fire_params(float weaponHealth);
// `damagedPick` is the host's 50/50 randWeightFloat input for the damaged set
// (< 0.5 -> set 2 with 30 s reversal, else set 3 with 2 s reversal).
P2BigTreasureGasParams p2_bigtreasure_gas_params(float weaponHealth, float damagedPick);
P2BigTreasureWaterParams p2_bigtreasure_water_params(float weaponHealth);
// `pick01` is the host's 50/50 input selecting within the normal (set 1/2)
// or damaged (set 3/4) group; the strict > 3000 boundary selects the group
// (BTA setElecAttackParameter :2252-2321).
P2BigTreasureElecParams p2_bigtreasure_elec_params(float weaponHealth, float pick01);

// Fire directional pre-attack selection (BTC getFireAttackAnimIndex
// :1116-1146): relative angle (target minus facing, wrapped to [0, TAU))
// selects the F/FL/FB/FR animation triplet. Returns 0=F, 1=FL, 2=FB, 3=FR.
int p2_bigtreasure_fire_direction(float relativeAngle);

// ---------------------------------------------------------------------------
// Fire (Flare Cannon): swept InteractFire segments. Node emit ratio grows at
// 3/s; extent scale*200, radius 25, Y gate 40*scale; new node every 0.1 s
// while started; nodes self-recycle at full extent, including after finish
// (BTA :85-139, :1203-1268).

class P2BigTreasureFirePolicy {
public:
    static constexpr int kCapacity = 8;
    static constexpr float kEmitPeriod = 0.1f;
    static constexpr float kRatioRate = 3.0f; // per second
    static constexpr float kExtent = 200.0f;
    static constexpr float kRadius = 25.0f;

    bool start(const P2BigTreasureFireParams& params);
    void finish(); // stops emission; in-flight nodes still step to extent
    bool isStarted() const { return mStarted; }
    int nodeCount() const { return mNodeCount; }

    // Steps all nodes; spawns a node when due. Returns nodes recycled.
    int tick(float delta);

    // Source hit geometry for node i against a target position.
    bool nodeHit(int index, const P2BigTreasureVec3& emitPosition,
                 const P2BigTreasureVec3& emitDirection, const P2BigTreasureVec3& target) const;
    float nodeRatio(int index) const;
    const P2BigTreasureFireParams& params() const { return mParams; }

private:
    bool mStarted = false;
    P2BigTreasureFireParams mParams{ 1.0f };
    float mEmitTimer = 0.0f;
    int mNodeCount = 0;
    float mRatios[kCapacity] = {};
};

// ---------------------------------------------------------------------------
// Gas (Comedy Bomb): rotating arms of InteractGas nodes. Node ratio grows at
// 0.27/s to extent 480; radius 10 (15 past half extent), Y gate 30; new arm
// set every 0.1 s; arm angles rotate unless bittered; direction reverses on
// the reversal timer (BTA :189-244, :1315-1467).

class P2BigTreasureGasPolicy {
public:
    static constexpr int kCapacity = 200;
    static constexpr float kEmitPeriod = 0.1f;
    static constexpr float kRatioRate = 0.27f; // per second
    static constexpr float kExtent = 480.0f;

    // `startAngle` and `clockwise` are host randWeightFloat inputs.
    bool start(const P2BigTreasureGasParams& params, float startAngle, bool clockwise);
    void finish();
    bool isStarted() const { return mStarted; }
    int nodeCount() const { return mNodeCount; }
    float armAngle(int arm) const;
    bool isClockwise() const { return mClockwise; }

    // `bittered` freezes arm rotation (BTA :1440-1457).
    int tick(float delta, bool bittered);

    bool nodeHit(const P2BigTreasureVec3& emitPosition, int arm, float ratio,
                 const P2BigTreasureVec3& target) const;

private:
    bool mStarted = false;
    P2BigTreasureGasParams mParams{ 3, 0.015f, 30.0f };
    bool mClockwise = true;
    float mArmAngles[4] = {};
    float mEmitTimer = 0.0f;
    float mReversalTimer = 0.0f;
    int mNodeCount = 0;
    float mRatios[kCapacity] = {};
    int mNodeArm[kCapacity] = {};
};

// ---------------------------------------------------------------------------
// Water (Monster Pump): ballistic InteractBubble shots. velocity.y -= 20 per
// source update; impact at adapter ground height ends the node with a ground
// hit (radius 30 vs 20 in flight). Bubbles persist across finish (source
// gap 2) and are force-recycled only on defeat (BTA :283-337, :2171-2205).

struct P2BigTreasureWaterNode {
    bool active = false;
    P2BigTreasureVec3 position;
    P2BigTreasureVec3 velocity;
};

class P2BigTreasureWaterPolicy {
public:
    static constexpr int kCapacity = 16;
    static constexpr float kFlightRadius = 20.0f;
    static constexpr float kGroundRadius = 30.0f;
    static constexpr float kGravityPerUpdate = 20.0f; // per 30 Hz update

    bool start(const P2BigTreasureWaterParams& params);
    void finish(); // stops emission; in-flight bubbles persist (source gap 2)
    void defeat(); // lane teardown: force-recycle in-flight bubbles
    bool isStarted() const { return mStarted; }
    int activeCount() const;
    const P2BigTreasureWaterNode& node(int index) const { return mNodes[index]; }

    // Source shot velocity (BTA startNewWaterList :1802-1849). `jitterDist`
    // is the host's randWeightFloat(2*off)-off input, `jitterAng` the angle
    // equivalent. Emits from `emitPosition` toward `targetPosition`.
    bool emitShot(const P2BigTreasureVec3& emitPosition, const P2BigTreasureVec3& targetPosition,
                  float jitterDist, float jitterAng, float delta);

    // Steps nodes; ground impact via the adapter ends the node and reports
    // through `outGroundHits` (count). Returns recycled node count.
    int tick(float delta, P2BigTreasureGroundFn ground, void* groundContext, int* outGroundHits);

    // Source hit geometry: 3D distance, radius 20 in flight / 30 on impact.
    bool nodeHit(int index, const P2BigTreasureVec3& target, bool onGround) const;

    const P2BigTreasureWaterParams& params() const { return mParams; }

private:
    bool mStarted = false;
    P2BigTreasureWaterParams mParams{ 0.5f, 0.5f, 100.0f };
    float mEmitTimer = 0.0f;
    P2BigTreasureWaterNode mNodes[kCapacity];
    // Emission timing lives in tick via shouldEmit().
public:
    // True when a shot is due this tick (interval from params).
    bool tickEmitter(float delta);
};

// ---------------------------------------------------------------------------
// Elec (Shock Therapist): bouncing spheres chained pairwise into
// InteractDenki arcs after a scatter delay. First node is the invisible
// anchor tracking the otakara_elec_eff joint; visible nodes trace through
// the host adapter with bounce/friction; velocity.y -= 20 per update. After
// the scatter time, chains link successive nodes pairwise every chain
// interval (BTA :404-494, :2252-2782). finishAttack recycles all nodes with
// break effects; defeat does the same.

struct P2BigTreasureElecNode {
    bool active = false;
    bool visible = true;
    bool onFloor = false;
    int connected = -1; // index of chained partner, -1 = unchained
    P2BigTreasureVec3 position;
    P2BigTreasureVec3 velocity;
};

class P2BigTreasureElecPolicy {
public:
    static constexpr int kCapacity = 17;

    // `startAngle` is the host randWeightFloat(TAU) input; per-node angle and
    // speed jitters are supplied through `angleJitter`/`speedJitterH`/
    // `speedJitterV` arrays by the host (deterministic fixtures pass fixed
    // values). Anchor starts invisible at `jointPosition`.
    bool start(const P2BigTreasureElecParams& params, const P2BigTreasureVec3& jointPosition,
               float startAngle, const float* angleJitter, const float* speedJitterH,
               const float* speedJitterV);
    void finish(); // recycles every node with break effects (BTA :2979-3003)
    bool isStarted() const { return mStarted; }
    int activeCount() const;
    const P2BigTreasureElecNode& node(int index) const { return mNodes[index]; }

    // Steps visible nodes through the adapter; anchor tracks `jointPosition`.
    // After scatterTime, links pairwise chains every chainInterval until all
    // placed. Returns floor-bounce event count via `outBounces`.
    int tick(float delta, const P2BigTreasureVec3& jointPosition, P2BigTreasureTraceFn trace,
             void* traceContext, int* outBounces);

    // Source chain-segment hit geometry (BTA :436-491): creature within
    // |dot1| < 10 of the cross axis, |dot2| < 20 of the second axis, and
    // 0 < dotSep < dist along the segment between node a and its partner.
    static bool chainHit(const P2BigTreasureVec3& a, const P2BigTreasureVec3& b,
                         const P2BigTreasureVec3& target);

    int chainedCount() const;
    const P2BigTreasureElecParams& params() const { return mParams; }

private:
    bool mStarted = false;
    P2BigTreasureElecParams mParams{};
    P2BigTreasureElecNode mNodes[kCapacity];
    float mScatterTimer = 0.0f;
    float mChainTimer = 0.0f;
    int mPlacedLinks = 0;
    int mVisibleCount = 0;
};

// ---------------------------------------------------------------------------
// Director: integrates the 4 + 2*liveWeapons pacing limiter with the
// health-weighted pick and the pooled controllers. One attack at a time, as
// enforced by the source started flags.

class P2BigTreasureAttackDirector {
public:
    P2BigTreasureAttackPacer pacer;
    P2BigTreasureAttackPools pools;

    // Mirrors ItemWait/ItemWalk attack entry: when the pacer allows, pick a
    // weapon (host threshold input) and start its controller. Returns the
    // started element or -1.
    int tickEntry(const P2BigTreasureOwnership& ownership, float delta, bool targetInBox,
                  bool unstuckOutsiderNearby, float pickThreshold);

    // Bittered + lost-weapon force-finish (BTA :1167-1175).
    void bitterWeaponLost() { pools.bitterWeaponLost(0); }

    // Lane defeat teardown: pools force-recycled, caller runs
    // ownership.defeat() and each element policy's defeat path.
    void defeat() { pools.defeat(); }
};
