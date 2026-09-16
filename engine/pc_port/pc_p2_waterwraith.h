#pragma once

// Waterwraith (99 BlackMan) + Tyre (98) dependent-roller ownership and
// vulnerability policy for lane 31 (#175 / #443). Mirrors US GPVE01 rev 0
// semantics reconstructed from blackMan.cpp, tyre.cpp, tyreState.cpp,
// blackManState.cpp, TyreShadow.cpp and the registration tables at research
// revision 632af937. Engine-free: no actor, map, receiver, sound or effect
// dependency. The wraith births exactly one child roller and pushes position,
// velocity, facing and scale into it every frame; the roller has no steering
// or AI of its own. Retained-assembly functions (walk/route/joint callbacks)
// are out of scope; this policy owns the dependent lifetime and the
// vulnerability gate, not locomotion.
//
// Source facts encoded here:
//  - 98 Tyre is BDT_Empty (helper, no carcass/drops, not a boss); 99 BlackMan
//    is BDT_Boss with childID = Tyre x1.
//  - Tyre starts in `land` (tyre.cpp:79); first floor contact flicks and enters
//    `freeze` (tyreState.cpp:105-115); moveRestart -> `move` (Tyre.cpp:565-572);
//    a quake while moving -> `freeze` (tyre.cpp:347-353).
//  - Six collision spheres (tyr1..tyr6) are stickable only in freeze/stone.
//  - Death requires health <= 0 AND the wraith having set EB_Invulnerable
//    after its dismount (tyreState.cpp:67-69, :152-153); dead plays
//    tyre_getoff and is removed on the end key.
//  - Roll rate = distance travelled / WRAITH_ROLLER_CIRCUMFERENCE (44*pi),
//    scaled by the proper key fp01 (blackMan.cpp:988-995, tyreState.cpp:51-65).
//  - The wraith regenerates 5 HP per frame while riding (blackMan.cpp:843-848).
//  - The roller shadow ramps from 0.01 to 1 after the fall begins
//    (tyre.cpp:721-727, TyreShadow.cpp:217-257).

struct P2WaterwraithVec3 {
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
};

// StateID order from include/Game/Entities/Tyre.h:235-240.
enum P2TyrePhase {
    P2TYRE_Move = 0,
    P2TYRE_Land = 1,
    P2TYRE_Freeze = 2,
    P2TYRE_Dead = 3,
};

// StateID order from include/Game/Entities/BlackMan.h:367-378.
enum P2BlackManPhase {
    P2BM_Walk = 0,
    P2BM_Dead = 1,
    P2BM_Freeze = 2,
    P2BM_Bend = 3,
    P2BM_Escape = 4,
    P2BM_Fall = 5,
    P2BM_Flick = 6,
    P2BM_Recover = 7,
    P2BM_Tired = 8,
};

class P2WaterwraithRig {
public:
    static constexpr float kRollerCircumference = 44.0f * 3.14159265358979323846f;
    static constexpr float kRideRegenPerTick = 5.0f; // wraith HP/frame while riding
    static constexpr float kTyreMaxHealth = 1800.0f; // general fp00
    static constexpr float kTyreAttackDamage = 10.0f; // general fp24
    static constexpr float kShadowMinScale = 0.01f;
    static constexpr float kShadowMaxScale = 1.0f;

    // `properRotationSpeed` is Tyre fp01 (retail 25.0; header default 0.5).
    explicit P2WaterwraithRig(float properRotationSpeed = 25.0f);

    // Births the single child roller (BlackMan::onInit). False if already
    // alive. Lifetime invariant: at most one child, owned by the wraith.
    bool birth();
    bool alive() const { return mAlive; }
    bool attachedToOwner() const { return mAttached; }
    P2TyrePhase tyrePhase() const { return mTyre; }
    P2BlackManPhase wraithPhase() const { return mWraith; }
    float tyreHealth() const { return mHealth; }
    bool ownerInvulnerableSet() const { return mInvulnerable; }

    // Per-frame push from the wraith. Accumulates planar distance for the roll
    // angle; the roller itself never steers.
    void push(const P2WaterwraithVec3& position, const P2WaterwraithVec3& velocity,
              float facing, float scale);
    float travelledDistance() const { return mDistance; }
    float rollAngle() const { return mRollAngle; }
    P2WaterwraithVec3 position() const { return mPosition; }
    float facing() const { return mFacing; }
    float scale() const { return mScale; }

    // Tyre state transitions. Each is a no-op returning false when the source
    // precondition does not hold.
    bool landFloorContact(); // Land  -> Freeze (flick requested)
    bool moveRestart();      // Freeze -> Move
    bool quakeFreeze();      // Move  -> Freeze
    // Six stickable collision spheres only in freeze/stone.
    bool collisionSticky() const { return mAlive && mTyre == P2TYRE_Freeze; }

    // Vulnerability gate. The armed riding roller is not damageable except in
    // freeze; after the wraith dismounts (EB_Invulnerable) it stays damageable.
    bool damageable() const;
    // Applies damage when allowed. `outDead` is true only when health reached
    // zero AND the dismounted invulnerable flag is set (source death gate).
    bool applyDamage(float damage, bool* outDead = nullptr);

    // Dismount sets EB_Invulnerable and releases ownership so the roller can
    // die. The wraith phase moves to Escape/Fall per the host.
    void dismount();
    void setWraithPhase(P2BlackManPhase phase) { mWraith = phase; }

    // Death sequence: beginDead requires health <= 0 AND dismounted; it enters
    // Dead and requests tyre_getoff. finishDead runs the end key and removes
    // the child. Both are no-ops returning false otherwise.
    bool beginDead();
    bool finishDead();

    // Wraith HP regenerated this tick while the roller is attached and riding.
    float rideRegen(bool riding) const;

    // Roller shadow scale, ramped from the minimum toward the maximum after
    // the fall begins. `delta` is the 30 Hz source delta.
    void beginFall();
    float tickShadow(float delta);

private:
    bool mAlive = false;
    bool mAttached = false;
    bool mInvulnerable = false;
    P2TyrePhase mTyre = P2TYRE_Land;
    P2BlackManPhase mWraith = P2BM_Walk;
    float mHealth = 0.0f;
    P2WaterwraithVec3 mPosition{};
    P2WaterwraithVec3 mVelocity{};
    float mFacing = 0.0f;
    float mScale = 1.0f;
    float mDistance = 0.0f;
    float mRollAngle = 0.0f;
    float mProperRotationSpeed = 25.0f;
    bool mFalling = false;
    float mShadow = kShadowMinScale;
};
