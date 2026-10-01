#pragma once

// Engine-free Snagret family source policy (#174/#376), mirroring the shared
// burrow/emerge/peck machinery and the two species state machines of SnakeCrow
// (34, Burrowing Snagret) and SnakeWhole (70, Pileated Snagret).
//
// Source: docs/PIKMIN2_SNAGRET_CRAWBSTER_AUDIT.md (US GPVE01 rev 0),
// src/plugProjectNishimuraU/{SnakeCrow,SnakeWhole}State.cpp and SnakeJointMgr.
// Pure policy: the host owns the actor, mouth slots, neck joint callback,
// animation key events, RNG, collision boxes and all interactions. The policy
// consumes host-fed spatial booleans (territory/home/facing) because the audit
// does not state a numeric territory radius for SnakeCrow, and emits intents.

enum class P2SnagretSpecies {
    SnakeCrow = 34,  // Burrowing Snagret
    SnakeWhole = 70, // Pileated Snagret
};

enum class P2SnagretState {
    Dead = 0,
    Stay = 1,       // buried
    Appear1 = 2,
    Appear2 = 3,
    Disappear = 4,
    Wait = 5,
    Walk = 6,       // SnakeWhole foot-assisted pursuit
    Home = 7,       // SnakeWhole return hop
    Attack = 8,
    Eat = 9,
    Struggle = 10,
};

// Forward/lateral peck boxes from the audit. `None` means no peck this tick.
enum class P2SnagretPeckBox {
    None = 0,
    Near,
    Normal,
    Far,
    Right,
    Left,
};

struct P2SnagretFsmParms {
    P2SnagretSpecies species = P2SnagretSpecies::SnakeCrow;
    float maxHealth = 1500.0f;          // SnakeCrow disc (2500 in White Flower Garden)
    float wfgHealth = 2500.0f;          // forest_2 override (unused unless applied)
    float buriedMinSeconds = 2.5f;      // fp12 disc (SnakeWhole 0.5)
    float diveNoTargetSeconds = 2.5f;   // fp11 disc (SnakeWhole 0.5)
    float struggleSeconds = 1.5f;
    float appear1Chance = 0.6f;         // fp01 disc
    float surfacingHeal = 10.0f;        // lifeIncrement
    float attackDamage = 10.0f;         // disc, captains and Pikmin in a box
    float poisonDamage = 300.0f;        // fp21 White Pikmin
    float purplePoundScale = 0.1f;      // hit with no collision part
    float petrifiedCoefficient = 0.25f;
    bool canWalk = false;               // SnakeWhole only
    bool targetsPlayer = false;         // host must never swallow a captain
};

P2SnagretFsmParms p2SnagretParmsFor(P2SnagretSpecies species);

struct P2SnagretFsmInput {
    float health = 0.0f;
    bool killed = false;
    bool holdingTreasure = false;       // thrown from kutijnt1 on the death key
    bool targetInTerritory = false;     // host territory query
    bool targetInHome = false;          // SnagWhole home query
    bool facingTargetWithin30 = false;  // SnakeWhole hop alignment gate
    bool targetInPeckBox = false;       // host box query (any of the five)
    float targetForward = 0.0f;         // policy box selection when the host
    float targetLateral = 0.0f;         // does not pre-select a box
    bool latchedPikmin = false;         // a stuck head Pikmin forces Struggle
    bool mouthSlotFree = false;         // one Pikmin per mouth, three slots
    bool animEnd = false;
    bool attackKey4 = false;            // strike / re-peck key
    bool runKey2 = false;               // SnakeWhole hop launch
    bool shakeThreshold = false;        // stuck-Pikmin shake forces a dive
    bool stuckPikmin = false;
    float roll = 0.0f;                  // host uniform [0,1) for appear1/2
};

struct P2SnagretFsmOutput {
    P2SnagretState state = P2SnagretState::Stay;
    bool entered = false;
    bool surfaced = false;              // heal 10 on surfacing
    bool diveFlick = false;             // dive key 2 flicks nearby creatures
    P2SnagretPeckBox peckBox = P2SnagretPeckBox::None;
    float strikeForward = 0.0f;
    bool swallowRequested = false;      // Eat: one Pikmin per free mouth slot
    bool struggle = false;
    bool hopRequested = false;          // SnakeWhole run1 key 2
    bool hopHome = false;
    bool dropTreasure = false;
    bool leaveCorpse = true;            // carriable type5 corpse
    bool bitterImmune = false;          // only while buried
};

class P2SnagretFsm {
public:
    static constexpr float kSourceDelta = 1.0f / 30.0f;

    void reset(const P2SnagretFsmParms& parms);

    void update(const P2SnagretFsmInput& input, P2SnagretFsmOutput& output);

    P2SnagretState state() const { return mState; }
    float buriedSeconds() const { return mBuriedTimer; }
    float stateSeconds() const { return mStateTimer; }
    static const char* stateName(P2SnagretState state);
    static const char* peckBoxName(P2SnagretPeckBox box);

    // Pure box selection from source extents (SnakeCrow or SnakeWhole).
    static P2SnagretPeckBox selectPeckBox(P2SnagretSpecies species,
                                          float forward, float lateral);
    static float strikeForward(P2SnagretSpecies species, P2SnagretPeckBox box);

private:
    void enter(P2SnagretState next, const P2SnagretFsmInput& input,
               P2SnagretFsmOutput& output);
    void emitPeck(const P2SnagretFsmInput& input, P2SnagretFsmOutput& output);

    P2SnagretFsmParms mParms;
    P2SnagretState mState = P2SnagretState::Stay;
    float mStateTimer = 0.0f;
    float mBuriedTimer = 0.0f;
    float mStruggleTimer = 0.0f;
};
