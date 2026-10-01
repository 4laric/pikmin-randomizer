#pragma once

// Isolated Egg (EnemyID 37) hazard policy: the single ROCK-free `EGG_Wait`
// state, destruction triggers and the `genItem` reward drop table. It
// deliberately has no engine, map, creature, item, sound or effect dependency;
// a future host integration owns capture/fall physics, the item/pellet births,
// effects and sound.
//
// Source reference: projectPiki/pikmin2 revision
// 632af93787b9c95b63f0c13be32b161375ce3a96 (US GPVE01 rev 0):
//   src/plugProjectMorimuraU/egg.cpp / eggState.cpp,
//   include/Game/Entities/Egg.h.
// See docs/PIKMIN2_EGG_HAZARD.md for the contract.

struct P2EggVec3 {
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
};

// Egg.h:18-26. Values are the exact source enum; mForcedDropType is 1-based in
// the parms so the policy applies the source `- 1` mapping (egg.cpp:277-279).
enum class P2EggDropType {
    OnePellets = 0,
    FivePellets = 1,
    SingleNectar = 2,
    DoubleNectar = 3,
    Mitites = 4,
    Spicy = 5,
    Bitter = 6,
};

// Lifespan: one Wait state (Egg.h:159-162). Broken is the same-tick
// genItem + kill(nullptr) path (eggState.cpp:45-65); the host frees the slot.
enum class P2EggPhase { Inactive, Wait, Broken };

// Item kinds the host must birth. PelletOne/PelletFive go through pelletMgr,
// Nectar/Spicy/Bitter through ItemHoney, MititeGroup through the TamagoMushi
// manager (`createGroup`).
enum class P2EggSpawnKind { PelletOne, PelletFive, Nectar, Spicy, Bitter, MititeGroup };

// Host/converter parameters. The drop chances are disc proper parms fp01-fp05
// (PIKMIN2_CANNON_PROJECTILE_ASSETS.md §5); they are never invented here.
struct P2EggConfig {
    float singleNectarChance = 0.0f; // fp01, disc 0.5
    float doubleNectarChance = 0.0f; // fp02, disc 0.35
    float mititesChance = 0.0f;      // fp03, disc 0.05
    float spicyChance = 0.0f;        // fp04, disc 0.05
    float bitterChance = 0.0f;       // fp05, disc 0.05
    int forcedDropType = 0;          // parms mForcedDropType; 0 = none, else 1-based
    bool checkHasSpray = true;       // parms mDoCheckHasSpray
    bool firstSpicySprayMade = false;  // playData DEMO_First_Spicy_Spray_Made
    bool firstBitterSprayMade = false; // playData DEMO_First_Bitter_Spray_Made
    float health = 0.0f;             // general fp00, disc 50
};

struct P2EggItem {
    P2EggSpawnKind kind = P2EggSpawnKind::Nectar;
    int pelletColor = 0;    // randInt(3) for pellets (egg.cpp:295,302)
    P2EggVec3 velocity;     // source spawn velocity
    int mititeCount = 0;    // 10 for the Mitite group (egg.cpp:348)
};

struct P2EggDrop {
    P2EggDropType type = P2EggDropType::SingleNectar;
    int itemCount = 0;
    P2EggItem items[2];                 // DoubleNectar spawns two
    float positionOffsetY = 2.0f;       // egg.cpp:249
    bool mititeFallbackToNectar = false; // createGroup failure -> nectar (egg.cpp:351-360)
};

// Scripted host RNG. randFloat returns [0,1); randInt returns [0,count).
typedef float (*P2EggRandFloatFn)(void* context);
typedef int (*P2EggRandIntFn)(void* context, int count);

class P2Egg {
public:
    void reset(const P2EggConfig& config);

    // onInit (egg.cpp:35-62). `dropGroup` mirrors isBirthTypeDropGroup(); a
    // non-drop-group Egg is constrained (host snaps its Y to the map).
    bool birth(bool dropGroup);

    // StateWait::exec break path (eggState.cpp:45-65): when health <= 0 the
    // policy computes the drop and transits to Broken. Returns true exactly
    // once; the host births the items and kill()s the Egg.
    bool update(P2EggRandFloatFn randFloat, void* randFloatContext,
                P2EggRandIntFn randInt, void* randIntContext);

    // Host-injected damage (Egg is not press-damageable: pressCallBack returns
    // false, egg.cpp:157-160). Returns the remaining health.
    float damage(float amount);

    // bounceCallback (egg.cpp:166-172): a falling or drop-group Egg that
    // touches a floor zeroes its health and exposes the gauge. Returns true
    // only when this call zeroed health.
    bool bounce();

    // collisionCallback (egg.cpp:178-186): a drop-group Egg touched by a
    // non-null, non-Teki creature in Wait zeroes its health and exposes the
    // gauge. Returns true only when this call zeroed health.
    bool contact(bool collidingIsNull, bool collidingIsTeki);

    // Capture lifecycle (egg.cpp:215-237). The host moves the Egg with the
    // capture matrix; the policy only records the source event flags.
    void onStartCapture();
    void onEndCapture();

    P2EggPhase phase() const { return mPhase; }
    bool isAlive() const { return mPhase == P2EggPhase::Wait; }
    bool hasDrop() const { return mPhase == P2EggPhase::Broken; }
    const P2EggDrop& drop() const { return mDrop; }
    float health() const { return mHealth; }
    bool dropGroup() const { return mDropGroup; }
    bool falling() const { return mFalling; }
    bool lifegaugeVisible() const { return mLifegaugeVisible; }
    bool constrained() const { return mConstrained; }
    bool invulnerable() const { return mInvulnerable; }
    bool cullable() const { return mCullable; }

    // Exposed for the host/fixtures. The source spawn velocity and position
    // offset for every non-spray item (egg.cpp:247-249).
    static P2EggVec3 baseSpawnVelocity() { return { 0.0f, 250.0f, 0.0f }; }

private:
    bool buildDrop(P2EggRandFloatFn randFloat, void* randFloatContext,
                   P2EggRandIntFn randInt, void* randIntContext);
    P2EggDropType selectType(P2EggRandFloatFn randFloat, void* randFloatContext);

    P2EggConfig mConfig;
    P2EggPhase mPhase = P2EggPhase::Inactive;
    float mHealth = 0.0f;
    bool mDropGroup = false;
    bool mFalling = false;
    bool mLifegaugeVisible = false;
    bool mConstrained = false;
    bool mInvulnerable = false;
    bool mCullable = true;
    P2EggDrop mDrop;
};
