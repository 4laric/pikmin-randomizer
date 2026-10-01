#pragma once

// Engine-free DangoMushi (94, Segmented Crawbster) Turn/flip-hazard policy
// (#174/#376), covering the two source behaviors the existing native FSM
// explicitly left out (docs/PIKMIN2_DANGOMUSHI_NATIVE.md "Remaining work"):
//
//   * the Turn LOOP_START..key-3 vulnerability window, during which bod0/bod1
//     become stickable and EB_Invulnerable clears, and
//   * the flip hazard rain: Obj::createCrashEnemy runs on EVERY StateTurn::init
//     and births 10 Rock enemies (30 s lifetime) around the active captain plus
//     one Egg at home with probability equal to the captain's group share of
//     all Pikmin (DangoMushi.cpp:649-776). The 30 Rock / 10 Egg reservation
//     (generalEnemyMgr.cpp:842) is a manager POOL size (concurrent objects,
//     slots return when a Rock dies), not a lifetime budget; the host slot
//     pool models it. (#897: the former lifetime budget stopped the rain after
//     three Turns.)
//
// Source: docs/PIKMIN2_SNAGRET_CRAWBSTER_AUDIT.md (US GPVE01 rev 0). Pure
// policy: the host owns the animation clock, the Rock/Egg managers from lane 20,
// collision parts and creature effects. This module only decides what to spawn,
// how long it lives and when the body is damageable.

struct P2DangoMushiHazardParms {
    int rocksPerTurn = 10;         // source rain count
    float rockLifetime = 30.0f;    // source Rock lifetime
    int turnLoopStartFrame = 32;   // turn clip key type 0 (frame:type 32:0)
    int turnKey3Frame = 108;       // turn clip key type 3 (frame:type 108:3)
};

struct P2DangoMushiHazardInput {
    bool turnEntered = false;      // host transitioned into Turn this tick
    bool turnExited = false;       // host left Turn this tick
    float turnFrame = 0.0f;        // current turn animation frame
    float activeCaptainGroupShare = 0.0f; // [0,1] captain's share of all Pikmin
    float eggRoll = 0.0f;          // host uniform [0,1) for the Egg decision
    float rockAngle = 0.0f;        // host heading offset (radians) for the rain
};

struct P2DangoMushiHazardOutput {
    int rocksToSpawn = 0;          // request this many Rocks this tick
    float rockLifetime = 0.0f;     // lifetime for each requested Rock
    bool eggRequested = false;     // one Egg at home this turn
    bool stickable = false;        // bod0/bod1 latch window open
    bool invulnerable = true;      // !stickable while in Turn
    int turnIndex = 0;             // 1-based Turn counter (rain fires on each)
};

class P2DangoMushiHazardPolicy {
public:
    void reset(const P2DangoMushiHazardParms& parms);

    // One source tick. The host feeds the Turn entry/exit edges and frame.
    void update(const P2DangoMushiHazardInput& input, P2DangoMushiHazardOutput& output);

    bool windowActive() const { return mWindowActive; }
    int turns() const { return mTurns; }

    // Source DangoMushiState.cpp:530 clears EB_Invulnerable only inside the Turn
    // stickable window; every attack/bomb outside it is rejected. Pure predicate
    // so the host damage gate (pc_p2_dangomushi_invulnerable) and the engine-free
    // fixture share one definition instead of re-deriving it.
    static bool attackRejected(bool stickable) { return !stickable; }

    // Source createCrashEnemy layout (DangoMushi.cpp:664-700) for rock `index`
    // around the fall position, with the source random jitter replaced by its
    // midpoint so fixtures are reproducible: rock 0 near the centre, rocks
    // 1-3 on a 120-degree ring at 70-85, rocks 4-9 on a 60-degree ring at
    // 140-155. `angle` is the source angleOffset1.
    static void rockOffset(int index, int count, float angle, float* x, float* z);

private:
    P2DangoMushiHazardParms mParms;
    int mTurns = 0;
    bool mInTurn = false;
    bool mRocksThisTurn = false;
    bool mEggThisTurn = false;
    bool mWindowActive = false;
};
