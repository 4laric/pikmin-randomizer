#pragma once

// Engine-free DangoMushi (94, Segmented Crawbster) Turn/flip-hazard policy
// (#174/#376), covering the two source behaviors the existing native FSM
// explicitly left out (docs/PIKMIN2_DANGOMUSHI_NATIVE.md "Remaining work"):
//
//   * the Turn LOOP_START..key-3 vulnerability window, during which bod0/bod1
//     become stickable and EB_Invulnerable clears, and
//   * the flip hazard rain: 10 Rock enemies (30 s lifetime) around the active
//     captain plus one Egg at home with probability equal to the captain's
//     group share of all Pikmin, capped by the reserved 30 Rock / 10 Egg
//     budgets (DangoMushi.cpp:649-776, generalEnemyMgr.cpp:842).
//
// Source: docs/PIKMIN2_SNAGRET_CRAWBSTER_AUDIT.md (US GPVE01 rev 0). Pure
// policy: the host owns the animation clock, the Rock/Egg managers from lane 20,
// collision parts and creature effects. This module only decides what to spawn,
// how long it lives and when the body is damageable.

struct P2DangoMushiHazardParms {
    int rocksPerTurn = 10;         // source rain count
    float rockLifetime = 30.0f;    // source Rock lifetime
    int rockBudget = 30;           // reserved per Crawbster (generalEnemyMgr)
    int eggBudget = 10;            // reserved per Crawbster
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
    int rocksRemaining = 0;        // budget after this tick
    int eggsRemaining = 0;
};

class P2DangoMushiHazardPolicy {
public:
    void reset(const P2DangoMushiHazardParms& parms);

    // One source tick. The host feeds the Turn entry/exit edges and frame.
    void update(const P2DangoMushiHazardInput& input, P2DangoMushiHazardOutput& output);

    bool windowActive() const { return mWindowActive; }
    int rocksRemaining() const { return mRocksRemaining; }
    int eggsRemaining() const { return mEggsRemaining; }

    // Deterministic ring offset (X, Z) for rock `index` of `count` around the
    // active captain, rotated by `angle`. Keeps fixture output reproducible
    // instead of depending on engine RNG.
    static void rockOffset(int index, int count, float angle, float* x, float* z);

private:
    P2DangoMushiHazardParms mParms;
    int mRocksRemaining = 0;
    int mEggsRemaining = 0;
    bool mInTurn = false;
    bool mRocksThisTurn = false;
    bool mEggThisTurn = false;
    bool mWindowActive = false;
};
