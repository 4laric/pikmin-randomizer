#include "pc_p2_bigtreasure_attacks.h"

#include <cmath>

namespace {
constexpr float kPi = 3.14159265358979323846f;
constexpr float kTau = 6.2831853071795864769f;

float wrapTau(float angle)
{
    angle = std::fmod(angle, kTau);
    return angle < 0.0f ? angle + kTau : angle;
}

float dist2D(P2BigTreasureVec3 a, P2BigTreasureVec3 b)
{
    const float dx = a.x - b.x;
    const float dz = a.z - b.z;
    return std::sqrt(dx * dx + dz * dz);
}

float sqrDist3D(P2BigTreasureVec3 a, P2BigTreasureVec3 b)
{
    const float dx = a.x - b.x;
    const float dy = a.y - b.y;
    const float dz = a.z - b.z;
    return dx * dx + dy * dy + dz * dz;
}

float sqrDist2D(P2BigTreasureVec3 a, P2BigTreasureVec3 b)
{
    const float dx = a.x - b.x;
    const float dz = a.z - b.z;
    return dx * dx + dz * dz;
}
} // namespace

// ---------------------------------------------------------------------------
// Parameter selection (BTA :1187-1197, :1315-1350, :1761-1777, :2252-2321)

P2BigTreasureFireParams p2_bigtreasure_fire_params(float weaponHealth)
{
    // Strict > 3000 boundary; flame scale 1.0 normal / 1.25 damaged.
    return P2BigTreasureFireParams{ weaponHealth > 3000.0f ? 1.0f : 1.25f };
}

P2BigTreasureGasParams p2_bigtreasure_gas_params(float weaponHealth, float damagedPick)
{
    if (weaponHealth > 3000.0f) {
        return P2BigTreasureGasParams{ 3, 0.015f, 30.0f };
    }
    if (damagedPick < 0.5f) {
        return P2BigTreasureGasParams{ 4, 0.02f, 30.0f };
    }
    return P2BigTreasureGasParams{ 4, 0.02f, 2.0f };
}

P2BigTreasureWaterParams p2_bigtreasure_water_params(float weaponHealth)
{
    if (weaponHealth > 3000.0f) {
        return P2BigTreasureWaterParams{ 0.5f, 0.5f, 100.0f };
    }
    return P2BigTreasureWaterParams{ 0.25f, 0.4f, 50.0f };
}

P2BigTreasureElecParams p2_bigtreasure_elec_params(float weaponHealth, float pick01)
{
    // Four discharge sets (parms fe00-fe37). Strict > 3000 selects the
    // normal (1-x) group; pick01 selects within the group.
    const int set = (weaponHealth > 3000.0f ? 0 : 2) + (pick01 < 0.5f ? 1 : 2);
    switch (set) {
    case 1:
        return P2BigTreasureElecParams{ 0.75f, 0.65f, 100.0f, 220.0f, 170.0f, 200.0f, 2.7f, 0.02f, 10 };
    case 2:
        return P2BigTreasureElecParams{ 0.7f, 0.65f, 80.0f, 250.0f, 350.0f, 100.0f, 4.5f, 0.02f, 12 };
    case 3:
        return P2BigTreasureElecParams{ 0.97f, 0.75f, 60.0f, 70.0f, 350.0f, 100.0f, 0.5f, 0.25f, 8 };
    default:
        return P2BigTreasureElecParams{ 0.2f, 0.985f, 100.0f, 90.0f, 70.0f, 20.0f, 0.2f, 0.15f, 14 };
    }
}

int p2_bigtreasure_fire_direction(float relativeAngle)
{
    const float angle = wrapTau(relativeAngle);
    if (angle > kPi / 4.0f && angle <= 3.0f * kPi / 4.0f) return 1; // FL
    if (angle > 3.0f * kPi / 4.0f && angle <= 5.0f * kPi / 4.0f) return 2; // FB
    if (angle > 5.0f * kPi / 4.0f && angle <= 7.0f * kPi / 4.0f) return 3; // FR
    return 0; // F
}

// ---------------------------------------------------------------------------
// Fire

bool P2BigTreasureFirePolicy::start(const P2BigTreasureFireParams& params)
{
    if (mStarted) return false;
    mStarted   = true;
    mParams    = params;
    mEmitTimer = 0.0f;
    // Source emits one node immediately in startFireAttack.
    if (mNodeCount < kCapacity) {
        mRatios[mNodeCount++] = 0.0f;
    }
    return true;
}

void P2BigTreasureFirePolicy::finish()
{
    mStarted = false;
}

int P2BigTreasureFirePolicy::tick(float delta)
{
    int recycled = 0;
    for (int i = 0; i < mNodeCount; i++) {
        mRatios[i] += kRatioRate * delta;
        if (mRatios[i] >= 1.0f) {
            // Recycle: swap-remove.
            mRatios[i] = mRatios[mNodeCount - 1];
            mNodeCount--;
            i--;
            recycled++;
        }
    }
    if (mStarted) {
        mEmitTimer += delta;
        if (mEmitTimer > kEmitPeriod && mNodeCount < kCapacity) {
            mEmitTimer = 0.0f;
            mRatios[mNodeCount++] = 0.0f;
        }
    }
    return recycled;
}

float P2BigTreasureFirePolicy::nodeRatio(int index) const
{
    return (index >= 0 && index < mNodeCount) ? mRatios[index] : 0.0f;
}

bool P2BigTreasureFirePolicy::nodeHit(int index, const P2BigTreasureVec3& emitPosition,
                                      const P2BigTreasureVec3& emitDirection,
                                      const P2BigTreasureVec3& target) const
{
    if (index < 0 || index >= mNodeCount) return false;
    const float scale  = mRatios[index] * (mParams.scale * kExtent);
    const float yGate  = 40.0f * mParams.scale;
    const float radius = kRadius * mParams.scale;
    P2BigTreasureVec3 pos{ emitPosition.x + emitDirection.x * scale,
                           emitPosition.y + emitDirection.y * scale - 25.0f,
                           emitPosition.z + emitDirection.z * scale };
    if (std::fabs(pos.y - target.y) >= yGate) return false;
    return sqrDist2D(pos, target) < radius * radius;
}

// ---------------------------------------------------------------------------
// Gas

bool P2BigTreasureGasPolicy::start(const P2BigTreasureGasParams& params, float startAngle,
                                   bool clockwise)
{
    if (mStarted) return false;
    mStarted       = true;
    mParams        = params;
    mClockwise     = clockwise;
    mEmitTimer     = 0.0f;
    mReversalTimer = 0.0f;
    const float spacing = kTau / static_cast<float>(params.armNum);
    for (int i = 0; i < params.armNum; i++) {
        mArmAngles[i] = startAngle + spacing * static_cast<float>(i);
    }
    // Source emits one arm set immediately in startGasAttack.
    for (int i = 0; i < params.armNum && mNodeCount < kCapacity; i++) {
        mRatios[mNodeCount]  = 0.0f;
        mNodeArm[mNodeCount] = i;
        mNodeCount++;
    }
    return true;
}

void P2BigTreasureGasPolicy::finish()
{
    mStarted = false;
}

float P2BigTreasureGasPolicy::armAngle(int arm) const
{
    return (arm >= 0 && arm < mParams.armNum) ? mArmAngles[arm] : 0.0f;
}

int P2BigTreasureGasPolicy::tick(float delta, bool bittered)
{
    int recycled = 0;
    for (int i = 0; i < mNodeCount; i++) {
        mRatios[i] += kRatioRate * delta;
        if (mRatios[i] >= 1.0f) {
            mRatios[i]  = mRatios[mNodeCount - 1];
            mNodeArm[i] = mNodeArm[mNodeCount - 1];
            mNodeCount--;
            i--;
            recycled++;
        }
    }
    if (!mStarted) return recycled;

    if (!bittered) {
        for (int i = 0; i < mParams.armNum; i++) {
            if (mClockwise) {
                mArmAngles[i] += mParams.rotationSpeed;
                if (mArmAngles[i] > kTau) mArmAngles[i] -= kTau;
            } else {
                mArmAngles[i] -= mParams.rotationSpeed;
                if (mArmAngles[i] < 0.0f) mArmAngles[i] += kTau;
            }
        }
    }

    mEmitTimer += delta;
    if (mEmitTimer > kEmitPeriod) {
        mEmitTimer = 0.0f;
        for (int i = 0; i < mParams.armNum && mNodeCount < kCapacity; i++) {
            mRatios[mNodeCount]  = 0.0f;
            mNodeArm[mNodeCount] = i;
            mNodeCount++;
        }
    }

    mReversalTimer += delta;
    if (mReversalTimer > mParams.reversalTime) {
        mClockwise     = !mClockwise;
        mReversalTimer = 0.0f;
    }
    return recycled;
}

bool P2BigTreasureGasPolicy::nodeHit(const P2BigTreasureVec3& emitPosition, int arm, float ratio,
                                     const P2BigTreasureVec3& target) const
{
    if (arm < 0 || arm >= mParams.armNum) return false;
    float gasDist = ratio > 0.5f ? 15.0f : 10.0f;
    gasDist *= gasDist;
    const float angle = mArmAngles[arm];
    P2BigTreasureVec3 pos{ emitPosition.x + std::sin(angle) * (kExtent * ratio),
                           emitPosition.y - 15.0f,
                           emitPosition.z + std::cos(angle) * (kExtent * ratio) };
    if (std::fabs(pos.y - target.y) >= 30.0f) return false;
    return sqrDist2D(pos, target) < gasDist;
}

// ---------------------------------------------------------------------------
// Water

bool P2BigTreasureWaterPolicy::start(const P2BigTreasureWaterParams& params)
{
    if (mStarted) return false;
    mStarted   = true;
    mParams    = params;
    mEmitTimer = 0.0f;
    return true;
}

void P2BigTreasureWaterPolicy::finish()
{
    mStarted = false;
}

void P2BigTreasureWaterPolicy::defeat()
{
    mStarted = false;
    for (int i = 0; i < kCapacity; i++) mNodes[i] = P2BigTreasureWaterNode{};
}

int P2BigTreasureWaterPolicy::activeCount() const
{
    int count = 0;
    for (int i = 0; i < kCapacity; i++) {
        if (mNodes[i].active) count++;
    }
    return count;
}

bool P2BigTreasureWaterPolicy::emitShot(const P2BigTreasureVec3& emitPosition,
                                        const P2BigTreasureVec3& targetPosition, float jitterDist,
                                        float jitterAng, float delta)
{
    int slot = -1;
    for (int i = 0; i < kCapacity; i++) {
        if (!mNodes[i].active) {
            slot = i;
            break;
        }
    }
    if (slot < 0) return false; // exhausted: silent skip

    // Source velocity computation (BTA :1824-1842).
    const float dist = dist2D(targetPosition, emitPosition);
    float speedFactor = dist + jitterDist;
    if (speedFactor < 1.0f) speedFactor = 1.0f;

    const float vertSpeed = 350.0f / delta / 20.0f;
    const float speed     = ((0.5f * speedFactor) / (vertSpeed / 20.0f)) / delta;

    const float angle = std::atan2(targetPosition.x - emitPosition.x,
                                   targetPosition.z - emitPosition.z)
                        + jitterAng;

    P2BigTreasureWaterNode& node = mNodes[slot];
    node.active        = true;
    node.position      = emitPosition;
    node.velocity      = P2BigTreasureVec3{ speed * std::sin(angle), vertSpeed,
                                            speed * std::cos(angle) };
    return true;
}

bool P2BigTreasureWaterPolicy::tickEmitter(float delta)
{
    if (!mStarted) return false;
    mEmitTimer += delta;
    if (mEmitTimer > mParams.shotInterval) {
        mEmitTimer = 0.0f;
        return true;
    }
    return false;
}

int P2BigTreasureWaterPolicy::tick(float delta, P2BigTreasureGroundFn ground, void* groundContext,
                                   int* outGroundHits)
{
    int recycled = 0;
    int groundHits = 0;
    for (int i = 0; i < kCapacity; i++) {
        P2BigTreasureWaterNode& node = mNodes[i];
        if (!node.active) continue;

        node.position.x += node.velocity.x * delta;
        node.position.y += node.velocity.y * delta;
        node.position.z += node.velocity.z * delta;
        node.velocity.y -= kGravityPerUpdate; // per source update

        float minY = 0.0f;
        if (ground && ground(groundContext, node.position.x, node.position.z, &minY)
            && node.position.y < minY) {
            node.position.y = minY;
            node.active     = false;
            recycled++;
            groundHits++;
        }
    }
    if (outGroundHits) *outGroundHits = groundHits;
    return recycled;
}

bool P2BigTreasureWaterPolicy::nodeHit(int index, const P2BigTreasureVec3& target,
                                       bool onGround) const
{
    if (index < 0 || index >= kCapacity) return false;
    const float radius = onGround ? kGroundRadius : kFlightRadius;
    return sqrDist3D(mNodes[index].position, target) < radius * radius;
}

// ---------------------------------------------------------------------------
// Elec

bool P2BigTreasureElecPolicy::start(const P2BigTreasureElecParams& params,
                                    const P2BigTreasureVec3& jointPosition, float startAngle,
                                    const float* angleJitter, const float* speedJitterH,
                                    const float* speedJitterV)
{
    if (mStarted) return false;
    // Pool invariant: 1 anchor + maxDischarge visible nodes <= 17.
    if (params.maxDischarge < 0 || 1 + params.maxDischarge > kCapacity) return false;

    mStarted      = true;
    mParams       = params;
    mScatterTimer = 0.0f;
    mChainTimer   = 0.0f;
    mPlacedLinks  = 0;
    mVisibleCount = 0;

    for (int i = 0; i < kCapacity; i++) mNodes[i] = P2BigTreasureElecNode{};

    // Anchor node: invisible, tracks the otakara_elec_eff joint.
    mNodes[0].active   = true;
    mNodes[0].visible  = false;
    mNodes[0].position = jointPosition;

    const float angleOffset = kTau / static_cast<float>(params.maxDischarge);
    float angle             = startAngle;
    for (int i = 0; i < params.maxDischarge; i++) {
        P2BigTreasureElecNode& node = mNodes[1 + i];
        node.active          = true;
        node.visible         = true;
        node.position        = jointPosition;
        const float aJit     = angleJitter ? angleJitter[i] : 0.0f;
        const float hJit     = speedJitterH ? speedJitterH[i] : 0.0f;
        const float vJit     = speedJitterV ? speedJitterV[i] : 0.0f;
        const float speedXZ  = params.baseHSpeed + hJit;
        const float speedY   = params.baseVSpeed + vJit;
        const float nodeAng  = angle + aJit;
        node.velocity        = P2BigTreasureVec3{ speedXZ * std::sin(nodeAng), speedY,
                                                  speedXZ * std::cos(nodeAng) };
        angle += angleOffset;
        mVisibleCount++;
    }
    return true;
}

void P2BigTreasureElecPolicy::finish()
{
    mStarted = false;
    for (int i = 0; i < kCapacity; i++) mNodes[i] = P2BigTreasureElecNode{};
    mPlacedLinks  = 0;
    mVisibleCount = 0;
}

int P2BigTreasureElecPolicy::activeCount() const
{
    int count = 0;
    for (int i = 0; i < kCapacity; i++) {
        if (mNodes[i].active) count++;
    }
    return count;
}

int P2BigTreasureElecPolicy::chainedCount() const
{
    int count = 0;
    for (int i = 0; i < kCapacity; i++) {
        if (mNodes[i].active && mNodes[i].connected >= 0) count++;
    }
    return count;
}

int P2BigTreasureElecPolicy::tick(float delta, const P2BigTreasureVec3& jointPosition,
                                  P2BigTreasureTraceFn trace, void* traceContext, int* outBounces)
{
    if (!mStarted) {
        if (outBounces) *outBounces = 0;
        return 0;
    }
    int bounces = 0;
    for (int i = 0; i < kCapacity; i++) {
        P2BigTreasureElecNode& node = mNodes[i];
        if (!node.active) continue;
        if (!node.visible) {
            node.position = jointPosition; // anchor tracks the joint
            continue;
        }

        if (trace) {
            P2BigTreasureTraceResult result;
            // Source traces a radius-20 sphere raised by 20 (BTA :406-434).
            P2BigTreasureVec3 raised{ node.position.x, node.position.y + 20.0f,
                                      node.position.z };
            if (trace(traceContext, raised, node.velocity, delta, 20.0f, mParams.bounceFactor,
                      result)) {
                node.position = P2BigTreasureVec3{ result.position.x, result.position.y - 20.0f,
                                                   result.position.z };
                node.velocity = result.velocity;
                if (result.floor) {
                    node.velocity.x *= mParams.frictionFactor;
                    node.velocity.z *= mParams.frictionFactor;
                    if (!node.onFloor) bounces++; // first-contact bounce sound
                    node.onFloor = true;
                } else {
                    node.onFloor = false;
                }
            }
        }
        node.velocity.y -= 20.0f; // per source update
    }

    // Chain placement after the scatter delay (BTA :2777-2782).
    int placed = 0;
    if (mScatterTimer > mParams.scatterTime && mChainTimer > mParams.chainInterval
        && mPlacedLinks < mVisibleCount) {
        // startNewElecList: link the next unchained pair, anchor first.
        int prev = -1;
        for (int i = 0; i < kCapacity; i++) {
            if (!mNodes[i].active) continue;
            if (prev < 0) {
                prev = i;
                continue;
            }
            if (mNodes[prev].connected < 0) {
                mNodes[prev].connected = i;
                mPlacedLinks++;
                placed++;
                break; // one link per interval (source places a growing
                       // window; the lane models one link per interval which
                       // reaches full chaining within maxDischarge intervals)
            }
            prev = i;
        }
        mChainTimer = 0.0f;
    }
    mScatterTimer += delta;
    mChainTimer += delta;

    if (outBounces) *outBounces = bounces;
    return placed;
}

bool P2BigTreasureElecPolicy::chainHit(const P2BigTreasureVec3& a, const P2BigTreasureVec3& b,
                                       const P2BigTreasureVec3& target)
{
    P2BigTreasureVec3 sep{ b.x - a.x, b.y - a.y, b.z - a.z };
    const float dist = std::sqrt(sep.x * sep.x + sep.y * sep.y + sep.z * sep.z);
    if (dist <= 0.0f) return false;
    sep.x /= dist;
    sep.y /= dist;
    sep.z /= dist;

    // crossVec1 = sep x (0,1,0); crossVec2 = crossVec1 x sep.
    P2BigTreasureVec3 cross1{ -sep.z, 0.0f, sep.x };
    const float len1 = std::sqrt(cross1.x * cross1.x + cross1.z * cross1.z);
    if (len1 <= 0.0f) return false; // vertical segment: degenerate in source too
    cross1.x /= len1;
    cross1.z /= len1;

    P2BigTreasureVec3 cross2{ cross1.z * sep.y, cross1.x * sep.z - cross1.z * sep.x,
                              -cross1.x * sep.y };

    P2BigTreasureVec3 toTarget{ target.x - a.x, target.y - a.y, target.z - a.z };
    const float dot1 = cross1.x * toTarget.x + cross1.z * toTarget.z;
    if (std::fabs(dot1) >= 10.0f) return false;
    const float dot2 = cross2.x * toTarget.x + cross2.y * toTarget.y + cross2.z * toTarget.z;
    if (std::fabs(dot2) >= 20.0f) return false;
    const float dotSep = sep.x * toTarget.x + sep.y * toTarget.y + sep.z * toTarget.z;
    return dotSep > 0.0f && dotSep < dist;
}

// ---------------------------------------------------------------------------
// Director

int P2BigTreasureAttackDirector::tickEntry(const P2BigTreasureOwnership& ownership, float delta,
                                           bool targetInBox, bool unstuckOutsiderNearby,
                                           float pickThreshold)
{
    if (!pacer.tick(delta, ownership.weaponCount(), targetInBox, unstuckOutsiderNearby)) {
        return -1;
    }
    const int weapon = ownership.pickWeapon(pickThreshold);
    if (weapon < 0) return -1;
    if (!pools.start(weapon)) return -1;
    return weapon;
}
