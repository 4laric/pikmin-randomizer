// Engine-free port of the P2 Long Legs leg IK (#173). See pc_p2_long_legs_ik.h.
#include "pc_p2_long_legs_ik.h"

#include <cmath>
#include <cstdlib>
#include <sstream>

namespace p2ik {
namespace {
constexpr float kPi = 3.14159265358979323846f;
constexpr float kTau = 2.0f * kPi;

V3 sub(const V3& a, const V3& b) { return V3(a.x - b.x, a.y - b.y, a.z - b.z); }
V3 add(const V3& a, const V3& b) { return V3(a.x + b.x, a.y + b.y, a.z + b.z); }
V3 scale(const V3& a, float s) { return V3(a.x * s, a.y * s, a.z * s); }
V3 cross(const V3& a, const V3& b)
{
    return V3(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x);
}
float dot(const V3& a, const V3& b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
float length(const V3& a) { return std::sqrt(dot(a, a)); }
// Vector3f::normalise: leaves a zero vector unchanged.
V3 normalise(const V3& a)
{
    const float len = length(a);
    return len > 0.0f ? scale(a, 1.0f / len) : a;
}
float clampf(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }
// clampAngle / angDist: wrap into (-pi, pi].
float wrapPi(float a)
{
    while (a > kPi) a -= kTau;
    while (a <= -kPi) a += kTau;
    return a;
}
float wrapTau(float a)
{
    while (a >= kTau) a -= kTau;
    while (a < 0.0f) a += kTau;
    return a;
}
} // namespace

M34 mul(const M34& a, const M34& b)
{
    M34 r;
    for (int i = 0; i < 3; ++i) {
        for (int j = 0; j < 4; ++j) {
            float v = a.m[i][0] * b.m[0][j] + a.m[i][1] * b.m[1][j] + a.m[i][2] * b.m[2][j];
            if (j == 3) v += a.m[i][3];
            r.m[i][j] = v;
        }
    }
    return r;
}

bool inverse(const M34& a, M34& out)
{
    const float c00 = a.m[1][1] * a.m[2][2] - a.m[1][2] * a.m[2][1];
    const float c01 = a.m[1][2] * a.m[2][0] - a.m[1][0] * a.m[2][2];
    const float c02 = a.m[1][0] * a.m[2][1] - a.m[1][1] * a.m[2][0];
    const float det = a.m[0][0] * c00 + a.m[0][1] * c01 + a.m[0][2] * c02;
    if (!(std::fabs(det) > 1.0e-12f) || !std::isfinite(det)) return false;
    const float inv = 1.0f / det;
    M34 r;
    r.m[0][0] = c00 * inv;
    r.m[1][0] = c01 * inv;
    r.m[2][0] = c02 * inv;
    r.m[0][1] = (a.m[0][2] * a.m[2][1] - a.m[0][1] * a.m[2][2]) * inv;
    r.m[1][1] = (a.m[0][0] * a.m[2][2] - a.m[0][2] * a.m[2][0]) * inv;
    r.m[2][1] = (a.m[0][1] * a.m[2][0] - a.m[0][0] * a.m[2][1]) * inv;
    r.m[0][2] = (a.m[0][1] * a.m[1][2] - a.m[0][2] * a.m[1][1]) * inv;
    r.m[1][2] = (a.m[0][2] * a.m[1][0] - a.m[0][0] * a.m[1][2]) * inv;
    r.m[2][2] = (a.m[0][0] * a.m[1][1] - a.m[0][1] * a.m[1][0]) * inv;
    for (int i = 0; i < 3; ++i)
        r.m[i][3] = -(r.m[i][0] * a.m[0][3] + r.m[i][1] * a.m[1][3] + r.m[i][2] * a.m[2][3]);
    out = r;
    return true;
}

V3 apply(const M34& a, const V3& p)
{
    return V3(a.m[0][0] * p.x + a.m[0][1] * p.y + a.m[0][2] * p.z + a.m[0][3],
              a.m[1][0] * p.x + a.m[1][1] * p.y + a.m[1][2] * p.z + a.m[1][3],
              a.m[2][0] * p.x + a.m[2][1] * p.y + a.m[2][2] * p.z + a.m[2][3]);
}

V3 applyDir(const M34& a, const V3& d)
{
    return V3(a.m[0][0] * d.x + a.m[0][1] * d.y + a.m[0][2] * d.z,
              a.m[1][0] * d.x + a.m[1][1] * d.y + a.m[1][2] * d.z,
              a.m[2][0] * d.x + a.m[2][1] * d.y + a.m[2][2] * d.z);
}

// NsMathExp::calcLagrange (nslibmath.cpp): quadratic through the three
// control points at t = 0, 1, 2.
void calcLagrange(const V3* cp, float t, V3& out)
{
    const float a = t - 1.0f;
    const float b = t - 2.0f;
    out.x = a * (cp[2].x * 0.5f * t) + (b * (cp[0].x * 0.5f * a) - (b * (cp[1].x * t)));
    out.y = a * (cp[2].y * 0.5f * t) + (b * (cp[0].y * 0.5f * a) - (b * (cp[1].y * t)));
    out.z = a * (cp[2].z * 0.5f * t) + (b * (cp[0].z * 0.5f * a) - (b * (cp[1].z * t)));
}

// NsMathExp::calcJointPos (nslibmath.cpp): the two-bone knee. The decomp names
// the fifth argument "middleJointPos" but it is read as the bend hint and the
// knee is written to the sixth.
void calcJointPos(const V3& top, const V3& bottom, float d1, float d2, const V3& hint, V3& out)
{
    const V3 t = sub(bottom, top);
    const float dTopMiddle = d1 * d1;
    const float dMiddleBottom = d2 * d2;
    const float dTopTarget = dot(t, t);
    if (!(dTopTarget < 0.000001f)) {
        const float s = (0.5f / dTopTarget) * (dTopTarget + (dTopMiddle - dMiddleBottom));
        const V3 foot(s * t.x + top.x, s * t.y + top.y, s * t.z + top.z);
        const V3 off = sub(foot, top);
        const float rest = dTopMiddle - off.x * off.x - off.y * off.y - off.z * off.z;
        if (!(rest <= 0.0f)) {
            const V3 perp = cross(t, cross(hint, t));
            const float outSqr = dot(perp, perp);
            if (outSqr != 0.0f) {
                const float k = std::sqrt(rest / outSqr);
                out = V3(k * perp.x + foot.x, k * perp.y + foot.y, k * perp.z + foot.z);
                return;
            }
        }
    }
    const float a = std::sqrt(dTopMiddle);
    const float b = std::sqrt(dMiddleBottom);
    const float r = a / (a + b);
    out = V3(r * t.x + top.x, r * t.y + top.y, r * t.z + top.z);
}

Parms houdaiParms()
{
    Parms p;
    p.bendFactor = 0.67f;
    p.maxTurnAngleDeg = 60.0f;
    p.moveSpeed = 250.0f;
    p.bottomJointMoveSpeed = 9.0f;
    p.raiseSlowdownFactor = -0.1f;
    p.downwardAccelFactor = 0.5f;
    p.maxDecelFactor = 10.0f;
    p.minDecelFactor = -2.0f;
    p.heightOffset = 40.0f;
    return p;
}

// ---- IKSystemBase -------------------------------------------------------

void Leg::startProgramedIK(const M34 joints[3])
{
    enabled = true;
    blend = false;
    scaleJoints = false;
    bendRatio = 0.0f;
    moveRatio = 2.0f;
    moveTimer = 0.0f;
    target = joints[BOTTOM].col(3);
    const V3 top = joints[TOP].col(3);
    const V3 mid = joints[MIDDLE].col(3);
    topToMiddle = length(sub(top, mid));
    middleToBottom = length(sub(mid, target));
}

void Leg::startMovePosition(V3 targetMove, const Parms& p, GroundFn ground, void* ctx)
{
    onGround = false;
    bendRatio = 0.0f;
    moveRatio = 0.0f;
    moveTimer = 0.0f;
    ik[TOP] = target;
    targetMove.y = ground ? ground(ctx, targetMove.x, targetMove.z) : targetMove.y;
    ik[BOTTOM] = targetMove;
    const float fc = p.moveInterpolationRate;
    const float fcn = 1.0f - p.moveInterpolationRate;
    ik[MIDDLE].x = fc * ik[BOTTOM].x + fcn * ik[TOP].x;
    ik[MIDDLE].y = fc * ik[BOTTOM].y + fcn * ik[TOP].y;
    ik[MIDDLE].z = fc * ik[BOTTOM].z + fcn * ik[TOP].z;
    ik[MIDDLE].y += p.heightOffset;
}

void Leg::update(const Parms& p, float dt, GroundFn ground, void* ctx, const M34& bottomJoint)
{
    if (!enabled) return;
    if (!onGround) {
        moveBottomJointPosition(p, dt);
        if (moveRatio > 1.0f && onGroundPosition(p, ground, ctx, bottomJoint)) onGround = true;
    }
    makeBendRatio(p);
    wasOnGround = onGround;
}

void Leg::moveBottomJointPosition(const Parms& p, float dt)
{
    moveTimer += moveRatio < 1.0f ? p.raiseSlowdownFactor : p.downwardAccelFactor;
    moveTimer = clampf(moveTimer, p.minDecelFactor, p.maxDecelFactor);
    moveRatio += (p.bottomJointMoveSpeed + moveTimer) * dt;
    calcLagrange(ik, moveRatio, target);
}

bool Leg::onGroundPosition(const Parms& p, GroundFn ground, void* ctx, const M34& bottomJoint)
{
    bool adjusted = false;
    float height = -12800.0f;
    const float minY = ground ? ground(ctx, target.x, target.z) : -12800.0f;
    if (minY > target.y) {
        height = minY;
        adjusted = true;
    }
    if (p.legCount > 0) {
        V3 offset = scale(bottomJoint.col(0), p.footPositionOffset);
        offset = add(offset, target);
        float angle = 0.0f;
        const float inc = kTau / float(p.legCount);
        for (int i = 0; i < p.legCount; ++i) {
            const V3 s(p.footPositionRadius * std::sin(angle) + offset.x, offset.y,
                       p.footPositionRadius * std::cos(angle) + offset.z);
            const float sy = ground ? ground(ctx, s.x, s.z) : -12800.0f;
            angle += inc;
            if (sy > s.y && sy > height) {
                height = sy;
                adjusted = true;
            }
        }
    }
    if (adjusted) target.y = height;
    return adjusted;
}

void Leg::makeBendRatio(const Parms& p)
{
    if (onGround) {
        bendRatio = 0.0f;
        return;
    }
    const float ratio = 1.33f * ((1.0f - std::fabs(1.0f - moveRatio)) - 0.25f);
    bendRatio = p.bendFactor * clampf(ratio, 0.0f, 1.0f);
}

void Leg::makeMatrix(M34 joints[3], const Parms&) const
{
    if (!enabled) return;
    const V3 top = joints[TOP].col(3);
    // getMiddleDirection
    V3 hint;
    if (blend) {
        hint = joints[TOP].col(0);
    } else {
        // Vector3f::setFlatDirectionFromTo: unit XZ direction top -> target.
        V3 flat(target.x - top.x, 0.0f, target.z - top.z);
        const float len = std::sqrt(flat.x * flat.x + flat.z * flat.z);
        hint = len > 0.0f ? V3(flat.x / len, 0.0f, flat.z / len) : V3(0.0f, 0.0f, 0.0f);
        hint.y += 100.0f;
    }
    V3 knee;
    calcJointPos(top, target, topToMiddle, middleToBottom, hint, knee);

    // The port keeps the drawn joint scale (source mScaleJoints) so a scaled
    // host draw stays proportional; at unit scale this equals the source.
    auto rotate = [&](M34& joint, const V3& xAxis) {
        V3 x = xAxis, y, z;
        if (blend) {
            const V3 oldY = joint.col(1);
            z = cross(x, oldY);
            y = cross(z, x);
        } else {
            const V3 tSep(target.z - top.z, 0.0f, top.x - target.x);
            y = cross(tSep, x);
            z = cross(x, y);
        }
        const float sx = length(joint.col(0));
        const float sy = length(joint.col(1));
        const float sz = length(joint.col(2));
        joint.setCol(0, scale(normalise(x), sx));
        joint.setCol(1, scale(normalise(y), sy));
        joint.setCol(2, scale(normalise(z), sz));
    };
    rotate(joints[TOP], sub(knee, top));
    rotate(joints[MIDDLE], sub(target, knee));
    joints[MIDDLE].setCol(3, knee);
    joints[BOTTOM].setCol(3, target);

    // makeBottomMatrix
    if (blend) return;
    const float bs = length(joints[BOTTOM].col(0));
    V3 newX(target.x - top.x, 0.0f, target.z - top.z);
    newX = normalise(newX);
    const V3 newY(0.0f, -1.0f, 0.0f);
    const V3 newZ = normalise(joints[MIDDLE].col(2));
    // Bottom * RotZ(bend): x' = x cos + y sin, y' = -x sin + y cos.
    const float c = std::cos(bendRatio), s = std::sin(bendRatio);
    const V3 x2 = add(scale(newX, c), scale(newY, s));
    const V3 y2 = add(scale(newX, -s), scale(newY, c));
    joints[BOTTOM].setCol(0, scale(x2, bs));
    joints[BOTTOM].setCol(1, scale(y2, bs));
    joints[BOTTOM].setCol(2, scale(newZ, bs));
}

// ---- IKSystemMgr --------------------------------------------------------

void Mgr::init(const V3& ownerPos, float ownerFace)
{
    mActive = false;
    mInMotion = false;
    mOnGround = false;
    mFace = ownerFace;
    mDistanceOffset = 100.0f;
    for (int i = 0; i < kLegCount; ++i) {
        mLegAngle[i] = 0.0f;
        mLegStates[i] = 0;
        mLegs[i] = Leg();
    }
    mTarget = V3();
    mCentre = ownerPos;
    mTrace = ownerPos;
    mTraceVel = V3();
    mLiftedMask = mPlantedMask = 0;
    mCycles = 0;
}

void Mgr::startProgramedIK(const M34 legJoints[kLegCount][3], const V3& ownerPos, float ownerFace)
{
    mActive = true;
    mInMotion = false;
    mOnGround = false;
    for (int i = 0; i < kLegCount; ++i) {
        mLegStates[i] = 0;
        mLegs[i].startProgramedIK(legJoints[i]);
    }
    mCentre = ownerPos;
    mFace = ownerFace;
    mDistanceOffset = length(sub(ownerPos, mLegs[0].target));
    for (int i = 0; i < kLegCount; ++i) {
        const V3 foot = mLegs[i].target;
        const float diff = std::atan2(foot.x - ownerPos.x, foot.z - ownerPos.z);
        mLegAngle[i] = diff - ownerFace;
    }
}

void Mgr::startIKMotion()
{
    mInMotion = true;
    mOnGround = false;
    for (int i = 0; i < kLegCount; ++i) mLegStates[i] = 0;
}

void Mgr::startCycleTo(const V3& next, float newFace, const Parms& p, GroundFn ground, void* ctx)
{
    if (!mActive) return;
    mInMotion = false; // one cycle: the chain runs to leg 3, then all legs rest in state 3
    mOnGround = false;
    for (int i = 0; i < kLegCount; ++i) {
        mLegStates[i] = 0;
        const float angle = newFace + mLegAngle[i];
        mLegTarget[i] = add(V3(next.x, 0.0f, next.z),
                            V3(mDistanceOffset * std::sin(angle), 0.0f, mDistanceOffset * std::cos(angle)));
    }
    mLegs[0].startMovePosition(mLegTarget[0], p, ground, ctx);
    mLegStates[0] = 1;
    mLiftedMask |= 1;
    ++mCycles;
}

void Mgr::setBlend(bool on)
{
    for (Leg& leg : mLegs) leg.blend = on;
}

bool Mgr::isFinishIKMotion() const
{
    if (mInMotion) return false;
    for (int i = 0; i < kLegCount; ++i)
        if (mLegStates[i] != 3) return false;
    return true;
}

void Mgr::update(const Parms& p, float dt, GroundFn ground, void* ctx, const M34 legJoints[kLegCount][3])
{
    mLiftedMask = mPlantedMask = 0;
    for (int i = 0; i < kLegCount; ++i) mLegs[i].update(p, dt, ground, ctx, legJoints[i][BOTTOM]);
    updateController(p, ground, ctx);
    calcFaceDir();
    calcCentrePosition();
    calcTraceCentrePosition(p);
}

void Mgr::updateController(const Parms& p, GroundFn ground, void* ctx)
{
    if (mInMotion) {
        bool all3 = true;
        for (int i = 0; i < kLegCount; ++i)
            if (mLegStates[i] != 3) all3 = false;
        if (all3)
            for (int i = 0; i < kLegCount; ++i) mLegStates[i] = 0;
        bool all0 = true;
        for (int i = 0; i < kLegCount; ++i)
            if (mLegStates[i] != 0) all0 = false;
        if (all0) {
            setNextCentrePosition(p);
            mLegs[0].startMovePosition(mLegTarget[0], p, ground, ctx);
            mLegStates[0] = 1;
            mLiftedMask |= 1;
            ++mCycles;
        }
    }
    for (int i = 0; i < kLegCount; ++i) {
        if (mLegStates[i] == 1) {
            if (mLegs[i].onGround) mLegStates[i] = 2;
        } else if (mLegStates[i] == 2) {
            mLegStates[i] = 3;
            mTraceVel.y += p.traceHeightOffset;
            mPlantedMask |= 1 << i;
            const int next = (i + 1 < 0) ? i + 5 : (i + 1 > 3) ? i - 3 : i + 1;
            if (next > 0 && !mOnGround) {
                mLegs[next].startMovePosition(mLegTarget[next], p, ground, ctx);
                mLegStates[next] = 1;
                mLiftedMask |= 1 << next;
            }
        }
    }
}

void Mgr::setNextCentrePosition(const Parms& p)
{
    // EnemyBase::getAngDist(mTargetPosition): owner = the IK centre/face,
    // which Houdai::updateIKSystem copied into mPosition/mFaceDir.
    float angleDist = wrapPi(std::atan2(mTarget.x - mCentre.x, mTarget.z - mCentre.z) - mFace);
    V3 next;
    const float view = p.viewAngleDeg * kPi / 180.0f;
    const float maxTurn = p.maxTurnAngleDeg * kPi / 180.0f;
    if (std::fabs(angleDist) <= view) {
        const V3 owner(mCentre.x, 0.0f, mCentre.z);
        next = V3(mTarget.x, 0.0f, mTarget.z);
        const float dist = length(sub(owner, next));
        if (dist > p.moveSpeed) {
            next = add(scale(normalise(sub(next, owner)), p.moveSpeed), owner);
        } else if (dist < p.minimumMoveSpeed) {
            next = add(scale(normalise(sub(next, owner)), p.minimumMoveSpeed), owner);
        }
    } else {
        next = V3(mCentre.x, 0.0f, mCentre.z);
        if (!(std::fabs(angleDist) <= maxTurn)) angleDist = angleDist > 0.0f ? maxTurn : -maxTurn;
    }
    const float newFace = angleDist + mFace;
    for (int i = 0; i < kLegCount; ++i) {
        const float angle = newFace + mLegAngle[i];
        mLegTarget[i] = add(next, V3(mDistanceOffset * std::sin(angle), 0.0f, mDistanceOffset * std::cos(angle)));
    }
}

void Mgr::calcFaceDir()
{
    if (!mActive) return; // owner face is kept by the host
    const V3 a = mLegs[0].target, b = mLegs[1].target;
    mFace = wrapTau(std::atan2((a.x + b.x) / 2.0f - mCentre.x, (a.z + b.z) / 2.0f - mCentre.z));
}

void Mgr::calcCentrePosition()
{
    if (!mActive) return;
    V3 c;
    float h[kLegCount];
    for (int i = 0; i < kLegCount; ++i) {
        c.x += mLegs[i].target.x;
        c.z += mLegs[i].target.z;
        h[i] = mLegs[i].target.y;
    }
    c.x *= 0.25f;
    c.z *= 0.25f;
    for (int i = 0; i < 3; ++i)
        for (int j = i + 1; j < 4; ++j)
            if (h[i] > h[j]) { const float t = h[i]; h[i] = h[j]; h[j] = t; }
    const float w[4] = {0.4f, 0.3f, 0.2f, 0.1f};
    for (int i = 0; i < 4; ++i) c.y += w[i] * h[i];
    mCentre = c;
}

void Mgr::calcTraceCentrePosition(const Parms& p)
{
    if (!mActive) {
        mTrace = mCentre;
        return;
    }
    mTraceVel = add(mTraceVel, scale(sub(mCentre, mTrace), p.traceMoveRate));
    mTrace = add(mTrace, mTraceVel);
    mTraceVel = scale(mTraceVel, p.traceVelocityDamping);
}

void Mgr::makeMatrix(M34 legJoints[kLegCount][3], const Parms& p) const
{
    for (int i = 0; i < kLegCount; ++i) mLegs[i].makeMatrix(legJoints[i], p);
}

// ---- Skin ----------------------------------------------------------------

const char* const kHoudaiLegJoints[kLegCount][3] = {
    {"rhand1jnt", "rhand2jnt", "rhand3jnt"},
    {"lhand1jnt", "lhand2jnt", "lhand3jnt"},
    {"rfoot1jnt", "rfoot2jnt", "rfoot3jnt"},
    {"lfoot1jnt", "lfoot2jnt", "lfoot3jnt"},
};

int Skin::joint(const char* name) const
{
    for (size_t i = 0; i < names.size(); ++i)
        if (names[i] == name) return int(i);
    return -1;
}

bool Skin::parse(const std::string& text, std::string* error)
{
    auto fail = [&](const char* why) {
        if (error) *error = why;
        names.clear();
        bind.clear();
        posJoint.clear();
        nrmJoint.clear();
        posLocal.clear();
        nrmLocal.clear();
        return false;
    };
    std::istringstream in(text);
    std::string word;
    int count = 0;
    if (!(in >> word) || word != "P2_LONG_LEGS_SKIN_1") return fail("header");
    if (!(in >> word >> count) || word != "joints" || count < 1 || count > 256) return fail("joints");
    names.assign(size_t(count), std::string());
    bind.assign(size_t(count), M34());
    for (int i = 0; i < count; ++i) {
        int index = -1;
        if (!(in >> word >> index >> names[size_t(i)]) || word != "j" || index != i) return fail("joint row");
        for (int r = 0; r < 3; ++r)
            for (int c = 0; c < 4; ++c)
                if (!(in >> bind[size_t(i)].m[r][c]) || !std::isfinite(bind[size_t(i)].m[r][c])) return fail("joint matrix");
    }
    for (int pass = 0; pass < 2; ++pass) {
        const char* label = pass == 0 ? "positions" : "normals";
        std::vector<int>& joints = pass == 0 ? posJoint : nrmJoint;
        std::vector<V3>& values = pass == 0 ? posLocal : nrmLocal;
        int n = 0;
        if (!(in >> word >> n) || word != label || n < 1 || n > 65536) return fail(label);
        joints.assign(size_t(n), 0);
        values.assign(size_t(n), V3());
        for (int i = 0; i < n; ++i) {
            V3& v = values[size_t(i)];
            if (!(in >> joints[size_t(i)] >> v.x >> v.y >> v.z)) return fail("vertex row");
            if (joints[size_t(i)] < 0 || joints[size_t(i)] >= count) return fail("vertex joint");
            if (!std::isfinite(v.x) || !std::isfinite(v.y) || !std::isfinite(v.z)) return fail("vertex value");
        }
    }
    if (!(in >> word) || word != "end" || (in >> word)) return fail("trailer");
    return true;
}

void Skin::evaluate(const std::vector<M34>& joints, std::vector<V3>& pos, std::vector<V3>& nrm) const
{
    pos.resize(posLocal.size());
    nrm.resize(nrmLocal.size());
    for (size_t i = 0; i < posLocal.size(); ++i) pos[i] = apply(joints[size_t(posJoint[i])], posLocal[i]);
    for (size_t i = 0; i < nrmLocal.size(); ++i) {
        // Rigid normal: rotate (joint scale is uniform) and renormalise.
        const V3 n = normalise(applyDir(joints[size_t(nrmJoint[i])], nrmLocal[i]));
        nrm[i] = n;
    }
}

} // namespace p2ik
