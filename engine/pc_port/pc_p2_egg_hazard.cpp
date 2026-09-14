#include "pc_p2_egg_hazard.h"

#include <cmath>

namespace {
constexpr float kPi = 3.14159265358979323846f;
constexpr float kTau = 2.0f * kPi;
constexpr float kDoubleNectarSpraySpeed = 50.0f; // egg.cpp:329-330
constexpr float kMititeVelocityY = 200.0f;       // egg.cpp:347
constexpr int kMititeCount = 10;                 // egg.cpp:348

bool finite(float value) { return std::isfinite(value); }

bool validConfig(const P2EggConfig& config)
{
    return finite(config.singleNectarChance) && config.singleNectarChance >= 0.0f
        && finite(config.doubleNectarChance) && config.doubleNectarChance >= 0.0f
        && finite(config.mititesChance) && config.mititesChance >= 0.0f
        && finite(config.spicyChance) && config.spicyChance >= 0.0f
        && finite(config.bitterChance) && config.bitterChance >= 0.0f
        && config.forcedDropType >= 0 && config.forcedDropType <= 7
        && finite(config.health) && config.health > 0.0f;
}
} // namespace

void P2Egg::reset(const P2EggConfig& config)
{
    mConfig = config;
    mPhase = P2EggPhase::Inactive;
    mHealth = 0.0f;
    mDropGroup = false;
    mFalling = false;
    mLifegaugeVisible = false;
    mConstrained = false;
    mInvulnerable = false;
    mCullable = true;
    mDrop = P2EggDrop{};
}

bool P2Egg::birth(bool dropGroup)
{
    if (mPhase != P2EggPhase::Inactive || !validConfig(mConfig)) {
        return false;
    }
    mPhase = P2EggPhase::Wait;
    mHealth = mConfig.health;
    mDropGroup = dropGroup;
    mFalling = false;
    mLifegaugeVisible = false;
    mConstrained = !dropGroup; // onInit EB_Constrained (egg.cpp:46-47)
    mInvulnerable = false;
    mCullable = true;
    mDrop = P2EggDrop{};
    return true;
}

float P2Egg::damage(float amount)
{
    if (mPhase == P2EggPhase::Wait && finite(amount) && amount > 0.0f) {
        mHealth -= amount;
    }
    return mHealth;
}

bool P2Egg::bounce()
{
    // bounceCallback (egg.cpp:166-172).
    if (mPhase != P2EggPhase::Wait) {
        return false;
    }
    if (mFalling || mDropGroup) {
        mLifegaugeVisible = true;
        mHealth = 0.0f;
        return true;
    }
    return false;
}

bool P2Egg::contact(bool collidingIsNull, bool collidingIsTeki)
{
    // collisionCallback (egg.cpp:178-186).
    if (mPhase != P2EggPhase::Wait || !mDropGroup || collidingIsNull || collidingIsTeki) {
        return false;
    }
    mLifegaugeVisible = true;
    mHealth = 0.0f;
    return true;
}

void P2Egg::onStartCapture()
{
    // onStartCapture (egg.cpp:215-226).
    mConstrained = true;
    mInvulnerable = true;
    mCullable = false;
}

void P2Egg::onEndCapture()
{
    // onEndCapture (egg.cpp:232-237).
    mConstrained = false;
    mFalling = true;
    mCullable = true;
}

P2EggDropType P2Egg::selectType(P2EggRandFloatFn randFloat, void* randFloatContext)
{
    // genItem cumulative roll (egg.cpp:251-275).
    const float randVal = randFloat(randFloatContext);
    float test = mConfig.singleNectarChance;
    if (randVal < test) {
        return P2EggDropType::SingleNectar;
    }
    test += mConfig.doubleNectarChance;
    if (randVal < test) {
        return P2EggDropType::DoubleNectar;
    }
    test += mConfig.mititesChance;
    if (randVal < test) {
        return P2EggDropType::Mitites;
    }
    test += mConfig.spicyChance;
    if (randVal < test) {
        return P2EggDropType::Spicy;
    }
    test += mConfig.bitterChance;
    if (randVal < test) {
        return P2EggDropType::Bitter;
    }
    return P2EggDropType::SingleNectar; // source default
}

bool P2Egg::buildDrop(P2EggRandFloatFn randFloat, void* randFloatContext,
                      P2EggRandIntFn randInt, void* randIntContext)
{
    if (!randFloat || !randInt) {
        return false;
    }

    P2EggDropType type = selectType(randFloat, randFloatContext);

    // Forced drop overrides the roll (egg.cpp:277-279). Type stays 1-based in
    // the parms; 0 means none.
    if (mConfig.forcedDropType != 0) {
        type = static_cast<P2EggDropType>(mConfig.forcedDropType - 1);
    }

    // Spicy/Bitter are downgraded to single nectar until the first-spray demo
    // flag exists (egg.cpp:281-289).
    if (mConfig.checkHasSpray) {
        if (type == P2EggDropType::Spicy && !mConfig.firstSpicySprayMade) {
            type = P2EggDropType::SingleNectar;
        } else if (type == P2EggDropType::Bitter && !mConfig.firstBitterSprayMade) {
            type = P2EggDropType::SingleNectar;
        }
    }

    mDrop = P2EggDrop{};
    mDrop.type = type;
    mDrop.positionOffsetY = 2.0f; // egg.cpp:249
    const P2EggVec3 base = baseSpawnVelocity();

    switch (type) {
    case P2EggDropType::OnePellets:
    case P2EggDropType::FivePellets: {
        mDrop.itemCount = 1;
        P2EggItem& item = mDrop.items[0];
        item.kind = (type == P2EggDropType::OnePellets) ? P2EggSpawnKind::PelletOne
                                                        : P2EggSpawnKind::PelletFive;
        item.pelletColor = randInt(randIntContext, 3); // egg.cpp:295,302
        item.velocity = base;
        break;
    }
    case P2EggDropType::SingleNectar: {
        mDrop.itemCount = 1;
        mDrop.items[0].kind = P2EggSpawnKind::Nectar;
        mDrop.items[0].velocity = base; // egg.cpp:309-316
        break;
    }
    case P2EggDropType::DoubleNectar: {
        const float angle = kTau * randFloat(randFloatContext); // egg.cpp:320
        mDrop.itemCount = 2;
        for (int i = 0; i < 2; ++i) {
            const float theta = kPi * static_cast<float>(i) + angle; // egg.cpp:328
            mDrop.items[i].kind = P2EggSpawnKind::Nectar;
            mDrop.items[i].velocity = { kDoubleNectarSpraySpeed * std::sin(theta), base.y,
                                        kDoubleNectarSpraySpeed * std::cos(theta) };
        }
        break;
    }
    case P2EggDropType::Mitites: {
        mDrop.itemCount = 1;
        mDrop.items[0].kind = P2EggSpawnKind::MititeGroup;
        mDrop.items[0].mititeCount = kMititeCount;
        mDrop.items[0].velocity = { base.x, kMititeVelocityY, base.z };
        (void)randFloat(randFloatContext); // birthArg.mFaceDir = TAU * randFloat() (egg.cpp:346)
        mDrop.mititeFallbackToNectar = true; // egg.cpp:351-360
        break;
    }
    case P2EggDropType::Spicy:
    case P2EggDropType::Bitter: {
        mDrop.itemCount = 1;
        mDrop.items[0].kind = (type == P2EggDropType::Spicy) ? P2EggSpawnKind::Spicy
                                                             : P2EggSpawnKind::Bitter;
        mDrop.items[0].velocity = base; // egg.cpp:364-379
        break;
    }
    }
    return true;
}

bool P2Egg::update(P2EggRandFloatFn randFloat, void* randFloatContext,
                   P2EggRandIntFn randInt, void* randIntContext)
{
    if (mPhase != P2EggPhase::Wait || mHealth > 0.0f) {
        return false;
    }
    if (!buildDrop(randFloat, randFloatContext, randInt, randIntContext)) {
        return false;
    }
    mPhase = P2EggPhase::Broken;
    return true;
}
