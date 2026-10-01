#include "pc_p2_bigtreasure_elements.h"

namespace {
// Deterministic per-attack scatter for the elec nodes. The source draws
// startAngle = rand(TAU), per node angle = base + rand(0.2) - 0.1, speedXZ =
// baseH + rand(jitterH), yVel = baseV + rand(jitterV) (BigTreasureAttack.cpp
// startElecAttack :2356-2373). The runtime has no RNG of its own, so the host's
// two random inputs are hashed into the same ranges (splitmix-style), which keeps
// every attack distinct and reproducible from the logged inputs.
float scatter01(float a, float b, unsigned index, unsigned channel) {
    unsigned ia, ib;
    static_assert(sizeof(ia) == sizeof(a), "float is 32-bit");
    __builtin_memcpy(&ia, &a, sizeof(ia));
    __builtin_memcpy(&ib, &b, sizeof(ib));
    unsigned long long x = 0x9E3779B97F4A7C15ULL ^ ((unsigned long long)ia << 32 | ib);
    x += (unsigned long long)(index * 4u + channel + 1u) * 0xBF58476D1CE4E5B9ULL;
    x ^= x >> 30; x *= 0xBF58476D1CE4E5B9ULL;
    x ^= x >> 27; x *= 0x94D049BB133111EBULL;
    x ^= x >> 31;
    return float(double(x >> 40) / double(1ULL << 24));
}
constexpr float kElecJointRaise = 100.0f;
constexpr float kWaterEmitRaise = 100.0f;
constexpr float kWaterTargetRange = 200.0f;
} // namespace

bool P2BigTreasureElementRuntime::start(int weapon, const P2BigTreasureVec3& origin,
                                        float groundHeight, float weaponHealth,
                                        float damagedPick, float pick01)
{
    const P2BigTreasureElementAim aim = mAim;
    reset();
    mAim = aim;
    if (weapon < 0 || weapon >= P2BTWEAPON_Count) {
        return false;
    }
    mWeapon = weapon;
    mGround = groundHeight;
    mOrigin = origin;
    switch (weapon) {
    case P2BTWEAPON_Fire:
        return mFire.start(p2_bigtreasure_fire_params(weaponHealth));
    case P2BTWEAPON_Gas:
        mGasArms = p2_bigtreasure_gas_params(weaponHealth, damagedPick).armNum;
        return mGas.start(p2_bigtreasure_gas_params(weaponHealth, damagedPick), 0.0f, true);
    case P2BTWEAPON_Water:
        return mWater.start(p2_bigtreasure_water_params(weaponHealth));
    case P2BTWEAPON_Elec: {
        P2BigTreasureVec3 joint{ origin.x, origin.y + kElecJointRaise, origin.z };
        if (mAim.set) joint = mAim.emit;
        const P2BigTreasureElecParams params = p2_bigtreasure_elec_params(weaponHealth, pick01);
        float angleJitter[P2BigTreasureElecPolicy::kCapacity] = {};
        float speedH[P2BigTreasureElecPolicy::kCapacity] = {};
        float speedV[P2BigTreasureElecPolicy::kCapacity] = {};
        for (unsigned i = 0; i < unsigned(P2BigTreasureElecPolicy::kCapacity); ++i) {
            angleJitter[i] = scatter01(damagedPick, pick01, i, 0) * 0.2f - 0.1f;
            speedH[i] = scatter01(damagedPick, pick01, i, 1) * params.jitterHSpeed;
            speedV[i] = scatter01(damagedPick, pick01, i, 2) * params.jitterVSpeed;
        }
        const float startAngle = scatter01(damagedPick, pick01, 99u, 3) * 6.2831853f;
        return mElec.start(params, joint, startAngle, angleJitter, speedH, speedV);
    }
    default:
        break;
    }
    mWeapon = -1;
    return false;
}

void P2BigTreasureElementRuntime::finish()
{
    switch (mWeapon) {
    case P2BTWEAPON_Fire: mFire.finish(); break;
    case P2BTWEAPON_Gas: mGas.finish(); break;
    case P2BTWEAPON_Water: mWater.finish(); break;
    case P2BTWEAPON_Elec: mElec.finish(); break;
    default: break;
    }
    mWeapon = -1;
    mPrevNodes = 0;
}

void P2BigTreasureElementRuntime::defeat()
{
    mFire.finish();
    mGas.finish();
    mWater.defeat();
    mElec.finish();
    mWeapon = -1;
    mPrevNodes = 0;
}

void P2BigTreasureElementRuntime::reset()
{
    mFire = P2BigTreasureFirePolicy();
    mGas = P2BigTreasureGasPolicy();
    mWater = P2BigTreasureWaterPolicy();
    mElec = P2BigTreasureElecPolicy();
    mWeapon = -1;
    mGround = 0.0f;
    mOrigin = P2BigTreasureVec3{};
    mGasArms = 3;
    mPrevNodes = 0;
    mAim = P2BigTreasureElementAim{};
}

void P2BigTreasureElementRuntime::tick(float delta, const P2BigTreasureElementHost& host,
                                       P2BigTreasureElementStats& out)
{
    out = P2BigTreasureElementStats{};
    if (mWeapon < 0) {
        return;
    }
    switch (mWeapon) {
    case P2BTWEAPON_Fire:
        mFire.tick(delta);
        out.nodes = mFire.nodeCount();
        break;
    case P2BTWEAPON_Gas:
        mGas.tick(delta, false);
        out.nodes = mGas.nodeCount();
        break;
    case P2BTWEAPON_Water: {
        if (mWater.tickEmitter(delta)) {
            P2BigTreasureVec3 emit{ mOrigin.x, mGround + kWaterEmitRaise, mOrigin.z };
            P2BigTreasureVec3 target{ mOrigin.x, mGround, mOrigin.z + kWaterTargetRange };
            if (mAim.set) emit = mAim.emit;
            if (mAim.set && mAim.haveWaterTarget) target = mAim.waterTarget;
            mWater.emitShot(emit, target, 0.0f, 0.0f, delta);
        }
        int groundHits = 0;
        mWater.tick(delta, host.ground, host.context, &groundHits);
        out.groundHits = groundHits;
        out.nodes = mWater.activeCount();
        break;
    }
    case P2BTWEAPON_Elec: {
        P2BigTreasureVec3 joint{ mOrigin.x, mOrigin.y + kElecJointRaise, mOrigin.z };
        if (mAim.set) joint = mAim.emit;
        int bounces = 0;
        mElec.tick(delta, joint, host.trace, host.context, &bounces);
        out.bounces = bounces;
        out.nodes = mElec.activeCount();
        break;
    }
    default:
        break;
    }
    if (out.nodes > mPrevNodes) {
        out.emits = out.nodes - mPrevNodes;
    }
    mPrevNodes = out.nodes;
}

bool P2BigTreasureElementRuntime::queryHit(const P2BigTreasureVec3& target, int* outIndex) const
{
    if (outIndex) {
        *outIndex = -1;
    }
    switch (mWeapon) {
    case P2BTWEAPON_Fire: {
        P2BigTreasureVec3 emit{ mOrigin.x, mGround + 60.0f, mOrigin.z };
        P2BigTreasureVec3 dir{ 0.0f, 0.0f, 1.0f };
        if (mAim.set) { emit = mAim.emit; dir = mAim.direction; }
        for (int i = 0; i < P2BigTreasureFirePolicy::kCapacity; ++i) {
            if (mFire.nodeRatio(i) <= 0.0f) continue;
            if (mFire.nodeHit(i, emit, dir, target)) {
                if (outIndex) *outIndex = i;
                return true;
            }
        }
        return false;
    }
    case P2BTWEAPON_Gas: {
        P2BigTreasureVec3 emit{ mOrigin.x, mGround + 60.0f, mOrigin.z };
        if (mAim.set) emit = mAim.emit;
        const float ratio = mGas.nodeRatio(0);
        for (int arm = 0; arm < mGasArms; ++arm) {
            if (mGas.nodeHit(emit, arm, ratio, target)) {
                if (outIndex) *outIndex = arm;
                return true;
            }
        }
        return false;
    }
    case P2BTWEAPON_Water:
        for (int i = 0; i < P2BigTreasureWaterPolicy::kCapacity; ++i) {
            if (!mWater.node(i).active) continue;
            if (mWater.nodeHit(i, target, false)) {
                if (outIndex) *outIndex = i;
                return true;
            }
        }
        return false;
    case P2BTWEAPON_Elec:
        for (int i = 0; i < P2BigTreasureElecPolicy::kCapacity; ++i) {
            const P2BigTreasureElecNode& node = mElec.node(i);
            if (!node.active || !node.visible || node.connected < 0) continue;
            const P2BigTreasureElecNode& partner = mElec.node(node.connected);
            if (!partner.active) continue;
            if (P2BigTreasureElecPolicy::chainHit(node.position, partner.position, target)) {
                if (outIndex) *outIndex = i;
                return true;
            }
        }
        return false;
    default:
        return false;
    }
}
