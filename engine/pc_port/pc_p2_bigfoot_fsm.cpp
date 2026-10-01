#include "pc_p2_bigfoot_fsm.h"
#include "pc_p2_bigfoot_tables.h"

#include <cmath>
#include <cstring>

namespace {
constexpr float kPi = 3.14159265f;
constexpr float kHalfPi = 1.57079633f;
constexpr float kDeg2Rad = kPi / 180.0f;

float clamp01(float v) { return v < 0.0f ? 0.0f : (v > 1.0f ? 1.0f : v); }

float sqrDistXZ(const p2ik::V3& a, const p2ik::V3& b)
{
    const float dx = a.x - b.x, dz = a.z - b.z;
    return dx * dx + dz * dz;
}

} // namespace

// rhand, lhand, rfoot, lfoot (BigFoot.cpp:393-399), by the JNT1 index of
// rhand1jnt.. lfoot3jnt in enemy.bmd (pc_p2_bigfoot_tables.h kJointNames).
const int P2BigFootFsm::kLegJoint[p2ik::kLegCount][3] = {
    {10, 11, 12}, // rhand1jnt rhand2jnt rhand3jnt
    {4, 5, 6},    // lhand1jnt lhand2jnt lhand3jnt
    {7, 8, 9},    // rfoot1jnt rfoot2jnt rfoot3jnt
    {1, 2, 3},    // lfoot1jnt lfoot2jnt lfoot3jnt
};

// IKSystemMgr::isCollisionCheck: rhsp -> 0, lhsp -> 1, rfsp -> 2, lfsp -> 3.
const char* const P2BigFootFsm::kFootNode[p2ik::kLegCount] = {"rhsp", "lhsp", "rfsp", "lfsp"};

int P2BigFootFsm::clipFrames(int clip)
{
    if (clip < 0 || clip >= p2bigfoot::kClipCount) return 1;
    return p2bigfoot::kClips[clip].frames;
}

// bigfoot/enemyanimmgr.txt key frames: dead 85:2 150:3, landing 18:2,
// wait 0:0 75:1 (loop), flick 35:2; END once the clip runs past its length.
int P2BigFootFsm::keyAt(int clip, int frame)
{
    if (frame >= clipFrames(clip)) return kKeyEnd;
    switch (clip) {
    case ClipDead:
        if (frame == 85) return 2;
        if (frame == 150) return 3;
        return -1;
    case ClipLanding:
        return frame == 18 ? 2 : -1;
    case ClipWait:
        if (frame == 0) return 0;
        if (frame == 75) return 1;
        return -1;
    case ClipFlick:
        return frame == 35 ? 2 : -1;
    default:
        return -1;
    }
}

void P2BigFootFsm::clipJoints(int clip, float frame, p2ik::M34 out[kJoints])
{
    if (clip < 0 || clip >= p2bigfoot::kClipCount) clip = ClipWait;
    const p2bigfoot::Clip& c = p2bigfoot::kClips[clip];
    const float last = float(c.frames > 1 ? c.frames - 1 : 1);
    const float u = !(frame > 0.0f) ? 0.0f : (frame >= last ? 1.0f : frame / last);
    const float t = u * float(p2bigfoot::kSamples - 1);
    int i0 = int(t);
    if (i0 >= p2bigfoot::kSamples - 1) i0 = p2bigfoot::kSamples - 2;
    const float f = t - float(i0);
    for (int j = 0; j < kJoints; ++j) {
        const float (*a)[4] = c.joint[i0][j];
        const float (*b)[4] = c.joint[i0 + 1][j];
        for (int r = 0; r < 3; ++r)
            for (int k = 0; k < 4; ++k) out[j].m[r][k] = a[r][k] + (b[r][k] - a[r][k]) * f;
    }
}

bool P2BigFootFsm::isStartFlickFor(const P2BigFootParms& p, int stuck, float flickTimer)
{
    // EnemyFunc::isStartFlick (enemyAction.cpp:1209-1244): round the hit
    // counter, truncate to u8, compare against the blow tier of the stuck count.
    const float rounded = flickTimer >= 0.0f ? flickTimer + 0.5f : flickTimer - 0.5f;
    const int flickInt = static_cast<int>(static_cast<unsigned char>(static_cast<int>(rounded)));
    if (stuck < p.shakeOffSticking1) return flickInt > p.shakeOffBlowA;
    if (stuck < p.shakeOffSticking2) return flickInt > p.shakeOffBlowB;
    if (stuck < p.shakeOffSticking3) return flickInt > p.shakeOffBlowC;
    return flickInt > p.shakeOffBlowD;
}

bool P2BigFootFsm::footPressing(int leg) const
{
    if (leg < 0 || leg >= p2ik::kLegCount || !mIk.active()) return false;
    const int s = mIk.legState(leg);
    return (s == 1 || s == 2) && mIk.leg(leg).moveRatio > 1.0f;
}

p2ik::M34 P2BigFootFsm::bodyMatrix() const
{
    const p2ik::V3 t = mIk.traceCentre();
    const float c = std::cos(mFace), n = std::sin(mFace), s = mParms.scale;
    p2ik::M34 m;
    m.m[0][0] = c * s;  m.m[0][1] = 0.0f; m.m[0][2] = n * s; m.m[0][3] = t.x;
    m.m[1][0] = 0.0f;   m.m[1][1] = s;    m.m[1][2] = 0.0f;  m.m[1][3] = t.y;
    m.m[2][0] = -n * s; m.m[2][1] = 0.0f; m.m[2][2] = c * s; m.m[2][3] = t.z;
    return m;
}

p2ik::V3 P2BigFootFsm::collCentre(int node) const
{
    if (node < 0 || node >= p2bigfoot::kCollNodeCount) return mPos;
    const p2bigfoot::CollNode& n = p2bigfoot::kColl[node];
    return p2ik::apply(mJoints[n.joint], p2ik::V3(n.offset[0], n.offset[1], n.offset[2]));
}

void P2BigFootFsm::jointsModel(p2ik::M34 out[kJoints]) const
{
    p2ik::M34 inv;
    if (!p2ik::inverse(bodyMatrix(), inv)) {
        for (int j = 0; j < kJoints; ++j) out[j] = mJoints[j];
        return;
    }
    for (int j = 0; j < kJoints; ++j) out[j] = p2ik::mul(inv, mJoints[j]);
}

void P2BigFootFsm::setIKParameter()
{
    // Obj::setIKParameter (BigFoot.cpp:411-435).
    p2ik::Parms p;
    p.legCount = 12;
    p.footPositionOffset = 10.0f;
    p.footPositionRadius = 40.0f;
    p.bendFactor = 0.5f;
    p.maxTurnAngleDeg = mParms.maxTurnDeg;
    p.moveSpeed = mParms.moveSpeed;
    if (mEnraged) {
        p.bottomJointMoveSpeed = mParms.eBaseCoefficient;
        p.raiseSlowdownFactor = mParms.eRaiseSlowdown;
        p.downwardAccelFactor = mParms.eDownwardAccel;
        p.maxDecelFactor = mParms.eMaxDecel;
        p.minDecelFactor = mParms.eMinDecel;
        p.heightOffset = mParms.eLegSwing;
    } else {
        p.bottomJointMoveSpeed = mParms.baseCoefficient;
        p.raiseSlowdownFactor = mParms.raiseSlowdown;
        p.downwardAccelFactor = mParms.downwardAccel;
        p.maxDecelFactor = mParms.maxDecel;
        p.minDecelFactor = mParms.minDecel;
        p.heightOffset = mParms.legSwing;
    }
    mIkParms = p;
}

void P2BigFootFsm::resetFlickWalkTimeMax(float roll)
{
    // BigFoot.cpp:312-318: half + randWeightFloat(travel).
    const float t = mParms.normalTravelTime;
    mFlickWalkTimeMax = t * 0.5f + clamp01(roll) * t;
}

void P2BigFootFsm::setFlickWalkTimeMax(float roll)
{
    // BigFoot.cpp:324-330.
    const float t = mParms.postShakeTravelTime;
    mFlickWalkTimeMax = t * 0.5f + clamp01(roll) * t;
}

void P2BigFootFsm::getTargetPosition(const P2BigFootInput& in)
{
    // Obj::getTargetPosition (BigFoot.cpp:336-372), literally.
    if (sqrDistXZ(mPos, mHome) < mParms.territoryRadius * mParms.territoryRadius) {
        if (mEnraged) {
            const float a = mIkParms.viewAngleDeg; // IKSystemParms::mEnragedAngle
            const float adjust = (clamp01(in.roll[1]) * (2.0f * a) - a) * kDeg2Rad * kPi;
            const float ang = mFace + adjust;
            mTarget.x = mParms.movementOffset * std::sin(ang) + mPos.x;
            mTarget.y = mPos.y;
            mTarget.z = mParms.movementOffset * std::cos(ang) + mPos.z;
        } else if (in.walkPikiFound) {
            mTarget = in.walkPiki;
        } else if (sqrDistXZ(mPos, mTarget) < 625.0f) {
            const float range = mParms.territoryRadius - mParms.homeRadius;
            const float randDist = mParms.homeRadius + clamp01(in.roll[2]) * range;
            const float ang2 = std::atan2(mPos.x - mHome.x, mPos.z - mHome.z);
            const float ang1 = clamp01(in.roll[3]) * kPi;
            const float randAngle = ang2 + ang1 + kHalfPi;
            // The retail code uses sin for both axes (BigFoot.cpp:361-364).
            mTarget.x = randDist * std::sin(randAngle) + mHome.x;
            mTarget.y = mHome.y;
            mTarget.z = randDist * std::sin(randAngle) + mHome.z;
        }
    } else {
        mTarget = mHome;
    }
    mIk.setTargetPosition(mTarget);
}

void P2BigFootFsm::startMotion(int clip)
{
    mClip = clip;
    mFrame = 0;
    mKey = -1;
    mStopped = false;
    mFinish = false;
    mEnded = false;
}

void P2BigFootFsm::reset(const P2BigFootParms& parms, const p2ik::V3& home, float faceDir)
{
    *this = P2BigFootFsm();
    mParms = parms;
    mHome = home;
    mPos = home;
    mTarget = home; // onInit: mTargetPosition = mHomePosition
    mFace = faceDir;
    mEnraged = false;
    resetFlickWalkTimeMax(0.5f);
    setIKParameter();
    mIk.init(home, faceDir);
    // StateStay::init (BigFootState.cpp:80-92): hidden, bitter-immune,
    // landing clip parked on frame 0.
    mState = P2LongLegsState::Stay;
    mBitterImmune = true;
    startMotion(ClipLanding);
    mStopped = true;
    pose();
}

void P2BigFootFsm::cleanup(P2LongLegsState s)
{
    switch (s) {
    case P2LongLegsState::Land: {
        // StateLand::cleanup (BigFootState.cpp:186-194): startProgramedIK
        // captures the landed legs.
        p2ik::M34 legs[p2ik::kLegCount][3];
        for (int l = 0; l < p2ik::kLegCount; ++l)
            for (int j = 0; j < 3; ++j) legs[l][j] = mJoints[kLegJoint[l][j]];
        mIk.startProgramedIK(legs, mPos, mFace);
        break;
    }
    case P2LongLegsState::Flick:
        // StateFlick::cleanup (BigFootState.cpp:289-296).
        mIk.setBlend(false);
        setFlickWalkTimeMax(mRoll[0]);
        mEnraged = true;
        setIKParameter();
        break;
    case P2LongLegsState::Walk:
        // StateWalk::cleanup (BigFootState.cpp:347-354).
        if (mEnraged) mEnraged = false;
        break;
    default:
        break;
    }
}

void P2BigFootFsm::transit(P2LongLegsState next, const P2BigFootInput& in, P2BigFootOutput& out)
{
    if (!out.entered) out.from = mState;
    cleanup(mState);
    out.entered = true;
    mState = next;
    mHasNext = false;
    switch (next) {
    case P2LongLegsState::Land:
        // StateLand::init (BigFootState.cpp:128-147).
        mBitterImmune = true;
        startMotion(ClipLanding);
        break;
    case P2LongLegsState::Wait:
        // StateWait::init (BigFootState.cpp:200-210).
        mStateTimer = 0.0f;
        resetFlickWalkTimeMax(in.roll[0]);
        setIKParameter();
        startMotion(ClipWait);
        break;
    case P2LongLegsState::Flick:
        // StateFlick::init (BigFootState.cpp:249-260).
        mStateTimer = 0.0f;
        startMotion(ClipFlick);
        mIk.setBlend(true);
        break;
    case P2LongLegsState::Walk:
        // StateWalk::init (BigFootState.cpp:302-315).
        mStateTimer = 0.0f;
        mIk.startIKMotion();
        getTargetPosition(in);
        out.chosenSeconds = mFlickWalkTimeMax;
        break;
    case P2LongLegsState::Dead:
        // StateDead::init (BigFootState.cpp:30-45).
        mIk.forceFinishIKMotion();
        startMotion(ClipDead);
        break;
    default:
        break;
    }
}

void P2BigFootFsm::pose()
{
    const int frames = clipFrames(mClip);
    const int f = mFrame >= frames ? frames - 1 : (mFrame < 0 ? 0 : mFrame);
    p2ik::M34 model[kJoints];
    clipJoints(mClip, float(f), model);
    const p2ik::M34 body = bodyMatrix();
    for (int j = 0; j < kJoints; ++j) mJoints[j] = p2ik::mul(body, model[j]);
    if (mIk.active()) {
        // IKSystemMgr::setAnimationCallBack: the programmed legs replace the
        // clip's three leg joints (Obj::doAnimationIKSystem).
        p2ik::M34 legs[p2ik::kLegCount][3];
        for (int l = 0; l < p2ik::kLegCount; ++l)
            for (int j = 0; j < 3; ++j) legs[l][j] = mJoints[kLegJoint[l][j]];
        mIk.makeMatrix(legs, mIkParms);
        for (int l = 0; l < p2ik::kLegCount; ++l)
            for (int j = 0; j < 3; ++j) mJoints[kLegJoint[l][j]] = legs[l][j];
    }
}

void P2BigFootFsm::update(const P2BigFootInput& in, P2BigFootOutput& out)
{
    out = P2BigFootOutput();
    out.from = mState;
    for (int i = 0; i < 4; ++i) mRoll[i] = in.roll[i];
    mGround = in.ground;
    mGroundCtx = in.groundCtx;
    const float dt = kDelta;

    // EnemyBase::addDamage(damage, 1.0f): every accepted hit feeds the flick counter.
    mFlickTimer += static_cast<float>(in.hits);

    const int key = mKey;
    mKey = -1;

    switch (mState) {
    case P2LongLegsState::Stay:
        // StateStay::exec (BigFootState.cpp:98-114).
        if (in.wake) transit(P2LongLegsState::Land, in, out);
        break;

    case P2LongLegsState::Land:
        // StateLand::exec (BigFootState.cpp:153-180).
        if (key == 2) {
            mBitterImmune = false;
            out.landKey2 = true;
        } else if (key == kKeyEnd) {
            if (in.health <= 0.0f) transit(P2LongLegsState::Dead, in, out);
            else if (isStartFlick(in.stuck)) transit(P2LongLegsState::Flick, in, out);
            else transit(P2LongLegsState::Wait, in, out);
        }
        break;

    case P2LongLegsState::Wait:
        // StateWait::exec (BigFootState.cpp:216-235).
        mStateTimer += dt;
        if (in.health <= 0.0f) {
            mNext = P2LongLegsState::Dead; mHasNext = true; mFinish = true;
        } else if (isStartFlick(in.stuck)) {
            mNext = P2LongLegsState::Flick; mHasNext = true; mFinish = true;
        } else if (mStateTimer > 5.0f) {
            mNext = P2LongLegsState::Walk; mHasNext = true; mFinish = true;
        }
        if (key == kKeyEnd && mHasNext) transit(mNext, in, out);
        break;

    case P2LongLegsState::Flick:
        // StateFlick::exec (BigFootState.cpp:266-283).
        if (key == 2) {
            out.flickStuck = true;
            out.flickChance = mParms.shakeChance;
            out.flickKnockback = mParms.shakeKnockback;
            out.flickDamage = mParms.shakeDamage;
            mFlickTimer = 0.0f;
        } else if (key == kKeyEnd) {
            transit(in.health <= 0.0f ? P2LongLegsState::Dead : P2LongLegsState::Walk, in, out);
        }
        break;

    case P2LongLegsState::Walk:
        // StateWalk::exec (BigFootState.cpp:321-341).
        getTargetPosition(in);
        mStateTimer += dt;
        if (in.health <= 0.0f) {
            transit(P2LongLegsState::Dead, in, out);
        } else {
            if (isStartFlick(in.stuck)) {
                mNext = P2LongLegsState::Flick; mHasNext = true;
                mIk.finishIKMotion();
            } else if (mStateTimer > mFlickWalkTimeMax) {
                mNext = P2LongLegsState::Wait; mHasNext = true;
                mIk.finishIKMotion();
            }
            if (mIk.isFinishIKMotion() && mHasNext) transit(mNext, in, out);
        }
        break;

    case P2LongLegsState::Dead:
        // StateDead::exec (BigFootState.cpp:51-66).
        if (key == 2) out.deadKey2 = true;
        else if (key == kKeyEnd) out.deadEnd = true;
        break;

    default:
        break;
    }

    // Obj::updateIKSystem (BigFoot.cpp:450-456): the body follows the IK centre.
    {
        p2ik::M34 legs[p2ik::kLegCount][3];
        for (int l = 0; l < p2ik::kLegCount; ++l)
            for (int j = 0; j < 3; ++j) legs[l][j] = mJoints[kLegJoint[l][j]];
        mIk.update(mIkParms, dt, mGround, mGroundCtx, legs);
        mPos = mIk.centre();
        mFace = mIk.faceDir();
        out.lifted = mIk.liftedMask();
        out.planted = mIk.plantedMask();
    }

    // Animation advance: produces the key event the next exec reads.
    if (!mStopped && !mEnded) {
        ++mFrame;
        mKey = keyAt(mClip, mFrame);
        if (mKey == kKeyEnd) {
            mEnded = true;
        } else if (mClip == ClipWait && mFrame == 75 && !mFinish) {
            mFrame = 0; // loop key 1 -> key 0
        }
    }
    pose();

    out.state = mState;
    out.hidden = mState == P2LongLegsState::Stay;
    out.bitterImmune = mBitterImmune;
    out.enraged = mEnraged;
}
