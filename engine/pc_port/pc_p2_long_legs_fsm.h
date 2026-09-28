#pragma once

// Engine-free Long Legs family source policy (#173/#312), mirroring the shared
// IK-leg walk schedule and per-species state machines of Damagumo (56, Beady
// Long Legs), Houdai (66, Man-at-Legs) and BigFoot (69, Raging Long Legs).
//
// Source: docs/PIKMIN2_LONG_LEGS_AUDIT.md (US GPVE01 rev 0), state machines in
// src/plugProjectNishimuraU/{Damagumo,Houdai,BigFoot}State.cpp. This unit is a
// pure policy: the host owns IKSystemMgr, joint shadows, tube collision, the
// shot-gun shell pool, animation key events, random-number state and all
// creature effects. The host feeds per-tick inputs and performs the requested
// effects; the policy never dereferences a game object.
//
// The Long Legs family has no walk animation. Movement, foot crush and stomp
// are IK-driven; the policy therefore schedules leg activity and gates the
// crush exactly as the source collision check does (a foot only presses while
// descending or planting with a move ratio above 1). Shells are requested as
// events and must be consumed by lane 20's projectile contract, not spawned
// here.

enum class P2LongLegsSpecies {
    Damagumo = 56,  // Beady Long Legs
    Houdai = 66,    // Man-at-Legs
    BigFoot = 69,   // Raging Long Legs
};

enum class P2LongLegsState {
    Dead = 0,  // source Dead 0
    Stay = 1,  // dormant, model hidden, bitter-immune
    Land = 2,  // landing animation; key 2 removes immunity and fires feet
    Wait = 3,
    Flick = 4, // shake-off when Pikmin accumulate
    Walk = 5,
    Shot = 6,  // Houdai only
};

// Retail disc values from the audit; headers differ where noted. Nothing here
// is invented: fields the audit does not state are left at the source audit's
// documented default and marked. `pressDamage` 0 means the species has no foot
// press code (Houdai).
struct P2LongLegsFsmParms {
    P2LongLegsSpecies species = P2LongLegsSpecies::Damagumo;
    float maxHealth = 1300.0f;        // Damagumo disc
    float speed = 100.0f;             // Damagumo disc
    float privateRadius = 75.0f;      // all three disc
    float territoryRadius = 400.0f;   // Damagumo disc
    float homeRadius = 75.0f;         // all three disc
    float pressDamage = 10.0f;        // Damagumo 10; Houdai 0 (no press)
    bool hasShotGun = false;          // Houdai true
    float waitMinSeconds = 1.75f;     // Damagumo; Houdai 1.5; BigFoot fixed 5
    float waitMaxSeconds = 3.5f;      // Damagumo; Houdai 3.0; BigFoot fixed 5
    float walkMinSeconds = 3.25f;     // Damagumo; Houdai 3.5; BigFoot 10 normal
    float walkMaxSeconds = 6.5f;      // Damagumo; Houdai 7.0; BigFoot 10 normal
    float walkPostFlickSeconds = 0.0f; // BigFoot 5 s post-shake travel (fp21); 0 = unused
    // Man-at-Legs gun (HoudaiShotGun.cpp). The audit reuses general parameters
    // as seconds; values are the disc overrides.
    float burstCooldownSeconds = 50.0f; // mSearchHeight reused as seconds
    float burstOnSeconds = 2.5f;        // mMaxShootingOn disc
    float burstOffSeconds = 1.0f;       // mMaxShootingOff disc
    float maxAimSeconds = 120.0f;       // mSearchAngle reused as seconds
    int shellPool = 10;                 // fixed shell pool
    float shellDamage = 10.0f;          // disc
    float shellFriendlyDamage = 500.0f; // other enemies
    float shellSpeed = 600.0f;
    int deathChildren = 0;              // ShijimiChou x25 (Damagumo), Mitites x30 (BigFoot)
    bool damageRequiresStuck = true;    // US build: only stuck Pikmin damage
};

P2LongLegsFsmParms p2LongLegsParmsFor(P2LongLegsSpecies species);

// One 30 Hz source tick of host-fed inputs. The animation keyframe pulses
// (animEnd, landingKey2, flickKey2, shotLoop) are edges consumed this tick.
struct P2LongLegsFsmInput {
    float health = 0.0f;
    bool wakeTargetNearby = false;   // captain/Pikmin inside mPrivateRadius
    bool animEnd = false;            // state animation END key
    bool landingKey2 = false;        // landing key 2: immunity off, all feet fire
    bool flickKey2 = false;          // flick key 2: shake executes
    bool pikminAccumulating = false; // isStartFlick
    bool damageTaken = false;        // resets Houdai shot cooldown
    bool holdingTreasure = false;    // boss holds a treasure (death drop)
    bool killed = false;             // host kill event
    bool hasTargetInTerritory = false; // walk target selection/validity
    float ikMoveRatio = 1.0f;        // IK leg move ratio for the crush gate
    bool footDescendingOrPlanting = false; // a foot is descending/planting
    bool shotLoop = false;           // Attack animation loop boundary (fire one)
    int shellsInFlight = 0;          // host shell-pool occupancy (mSearchAngle pool of 10)
    float roll = 0.0f;               // host uniform [0,1) for duration selection
};

struct P2LongLegsFsmOutput {
    P2LongLegsState state = P2LongLegsState::Stay;
    bool entered = false;            // state entered this tick
    float chosenSeconds = 0.0f;      // Wait/Walk duration chosen on entry
    bool footCrush = false;          // press/stomp applies this tick
    bool feetFired = false;          // landing key 2 fires all four feet
    bool shake = false;              // Flick key 2 shake-off
    bool fireShell = false;          // Houdai: emit one shell (lane 20 contract)
    bool dropTreasure = false;       // death with a held treasure
    int birthChildren = 0;           // death with no treasure
    bool enragedWalk = false;        // BigFoot one-cycle rage walk
    bool bitterImmune = false;       // Stay, or Land before key 2
    bool damageable = false;         // awake and past the landing immunity gate
};

class P2LongLegsFsm {
public:
    static constexpr float kSourceDelta = 1.0f / 30.0f;

    void reset(const P2LongLegsFsmParms& parms);

    // One 30 Hz source update. Exactly one output per call.
    void update(const P2LongLegsFsmInput& input, P2LongLegsFsmOutput& output);

    P2LongLegsState state() const { return mState; }
    float stateSeconds() const { return mStateTimer; }
    float shotCooldownSeconds() const { return mShotCooldown; }
    bool landingFiredFeet() const { return mFeetFired; }
    bool enraged() const { return mEnraged; }
    static const char* stateName(P2LongLegsState state);
    static const char* speciesName(P2LongLegsSpecies species);

private:
    void enter(P2LongLegsState next, const P2LongLegsFsmInput& input, P2LongLegsFsmOutput& output);
    bool crushGate(const P2LongLegsFsmInput& input) const;
    float pickWaitSeconds(const P2LongLegsFsmInput& input) const;
    float pickWalkSeconds(const P2LongLegsFsmInput& input) const;

    P2LongLegsFsmParms mParms;
    P2LongLegsState mState = P2LongLegsState::Stay;
    float mStateTimer = 0.0f;
    float mChosenSeconds = 0.0f;
    float mShotCooldown = 0.0f;   // mShotGunBurstTimer
    float mBurstTimer = 0.0f;
    bool mBurstOn = false;
    float mAimTimer = 0.0f;
    bool mFeetFired = false;      // landing key 2 passed
    bool mEnraged = false;        // BigFoot one-cycle rage flag
};
