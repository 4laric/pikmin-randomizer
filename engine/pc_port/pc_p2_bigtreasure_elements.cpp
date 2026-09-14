#include "pc_p2_bigtreasure_elements.h"

namespace {
constexpr float kElecJointRaise = 100.0f;
constexpr float kWaterEmitRaise = 100.0f;
constexpr float kWaterTargetRange = 200.0f;
} // namespace

bool P2BigTreasureElementRuntime::start(int weapon, const P2BigTreasureVec3& origin,
                                        float groundHeight, float weaponHealth,
                                        float damagedPick, float pick01)
{
    reset();
    if (weapon < 0 || weapon >= P2BTWEAPON_Count) {
        return false;
    }
    mWeapon = weapon;
    mGround = groundHeight;
    mOrigin = origin;
    const float zero[P2BigTreasureElecPolicy::kCapacity] = {};
    switch (weapon) {
    case P2BTWEAPON_Fire:
        return mFire.start(p2_bigtreasure_fire_params(weaponHealth));
    case P2BTWEAPON_Gas:
        mGasArms = p2_bigtreasure_gas_params(weaponHealth, damagedPick).armNum;
        return mGas.start(p2_bigtreasure_gas_params(weaponHealth, damagedPick), 0.0f, true);
    case P2BTWEAPON_Water:
        return mWater.start(p2_bigtreasure_water_params(weaponHealth));
    case P2BTWEAPON_Elec: {
        const P2BigTreasureVec3 joint{ origin.x, origin.y + kElecJointRaise, origin.z };
        return mElec.start(p2_bigtreasure_elec_params(weaponHealth, pick01), joint, 0.0f,
                           zero, zero, zero);
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
            const P2BigTreasureVec3 emit{ mOrigin.x, mGround + kWaterEmitRaise, mOrigin.z };
            const P2BigTreasureVec3 target{ mOrigin.x, mGround,
                                            mOrigin.z + kWaterTargetRange };
            mWater.emitShot(emit, target, 0.0f, 0.0f, delta);
        }
        int groundHits = 0;
        mWater.tick(delta, host.ground, host.context, &groundHits);
        out.groundHits = groundHits;
        out.nodes = mWater.activeCount();
        break;
    }
    case P2BTWEAPON_Elec: {
        const P2BigTreasureVec3 joint{ mOrigin.x, mOrigin.y + kElecJointRaise, mOrigin.z };
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
        const P2BigTreasureVec3 emit{ mOrigin.x, mGround + 60.0f, mOrigin.z };
        const P2BigTreasureVec3 dir{ 0.0f, 0.0f, 1.0f };
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
        const P2BigTreasureVec3 emit{ mOrigin.x, mGround + 60.0f, mOrigin.z };
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
