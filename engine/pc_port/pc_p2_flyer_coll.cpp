#include "pc_p2_flyer_coll.h"

#include "Collision.h"
#include "CreatureCollPart.h"
#include "teki.h"
#include <cstdint>

extern Matrix4f invCamMat; // collInfo.cpp: camera inverse used by CollPart::getMatrix

namespace {
// Four-character part ids/codes, '_' padded (same packing as the retail tree).
u32 fourcc(const char* id)
{
    u32 v = 0;
    bool ended = false;
    for (int i = 0; i < 4; ++i) {
        char c = '_';
        if (!ended) {
            if (id[i]) c = id[i];
            else ended = true;
        }
        v = (v << 8) | u32(static_cast<unsigned char>(c));
    }
    return v;
}
} // namespace

bool P2FlyerColl::bind(BTeki* actor, const p2flyer::Sphere* table, int count)
{
    if (!actor || mOwn || !actor->mCollInfo || !table || count <= 0 || count > p2flyer::kMaxSpheres)
        return false;
    ObjCollInfo* nodes[p2flyer::kMaxSpheres] = {};
    for (int i = 0; i < count; ++i) {
        const p2flyer::Sphere& s = table[i];
        auto* node = new ObjCollInfo();
        node->mId.setID(fourcc(s.id));
        node->mCode.setID(fourcc(s.code));
        node->mRadius = s.radius;
        node->mCentrePosition.set(s.offset.x, s.offset.y, s.offset.z);
        node->mJointIndex = -1;
        nodes[i] = node;
    }
    for (int i = 0; i < count; ++i)
        if (table[i].parent >= 0) nodes[table[i].parent]->add(nodes[i]);
    mOwn = new CollInfo(32); // >= any vehicle tree
    mOwn->initInfoTree(nodes[0]);
    for (int i = 0; i < count; ++i) {
        CollPart* part = mOwn->getSphere(fourcc(table[i].id));
        if (part) {
            part->mIsUpdateActive = false;
            part->mJointMatrix = Matrix4f::ident;
        }
        mParts[i] = part;
    }
    mTable = table;
    mCount = count;
    mVehicle = actor->mCollInfo;
    actor->mCollInfo = mOwn;
    // The P2 flyers have no platform collision (EB_PlatformCollEnabled is off in
    // their onInit). The host's model platforms would otherwise stay in the map
    // at the flyer's position and report contacts whose part this tree cannot
    // resolve (a null CollEvent part crashed PikiFlyingState::procCollideMsg).
    // Same handling as the Titan Dweevil host (pc_p2_bigtreasure_teki.cpp).
    actor->mPlatMgr.release();
    mReleased = false;
    return true;
}

void P2FlyerColl::follow(BTeki* actor, const p2flyer::Vec3& root, float yaw, const p2flyer::Vec3& body, float scale)
{
    if (!actor || !mOwn || mReleased || !mTable) return;
    // CollPart::getMatrix() = invCamMat * mJointMatrix (+ centre): give every
    // part R(invCamMat)^T * yaw so stuck Pikmin follow the body yaw whether or
    // not the actor was drawn this frame (BigTreasure #246 pattern).
    Matrix4f yawMat, camRot, camYaw;
    yawMat.makeSRT(Vector3f(1.0f, 1.0f, 1.0f), Vector3f(0.0f, yaw, 0.0f), Vector3f(0.0f, 0.0f, 0.0f));
    camRot.makeIdentity();
    for (int r = 0; r < 3; ++r)
        for (int c = 0; c < 3; ++c) camRot.mMtx[r][c] = invCamMat.mMtx[c][r];
    camRot.multiplyTo(yawMat, camYaw);
    for (int i = 0; i < mCount; ++i) {
        CollPart* part = mParts[i];
        if (!part) continue;
        const p2flyer::Vec3 c = p2flyer::sphereCentre(mTable, mCount, i, root, yaw, body);
        part->mCentre.set(c.x, c.y, c.z);
        part->mRadius = mTable[i].radius * scale;
        part->mJointMatrix = camYaw;
    }
}

void P2FlyerColl::release(BTeki* actor, const p2flyer::Vec3& deadCentre)
{
    if (!actor || !mOwn || mReleased) return;
    mReleased = true;
    if (!mVehicle) return;
    actor->mCollInfo = mVehicle;
    mVehicle = nullptr;
    // The vehicle parts were last sampled before the swap (spawn pose): dieSoon
    // births the corpse pellet at the 'carc' sphere (or the bounding sphere via
    // getCentre), so seat both on the dead body now.
    if (CollPart* carcass = actor->mCollInfo->getSphere('carc')) carcass->mCentre.set(deadCentre.x, deadCentre.y, deadCentre.z);
    if (actor->mCollInfo->hasInfo()) {
        if (CollPart* bound = actor->mCollInfo->getBoundingSphere()) bound->mCentre.set(deadCentre.x, deadCentre.y, deadCentre.z);
        if (CollPart* cent = actor->mCollInfo->getSphere('cent')) cent->mCentre.set(deadCentre.x, deadCentre.y, deadCentre.z);
    }
}

void P2FlyerColl::detach(BTeki* actor)
{
    if (!actor || !mOwn || mReleased) return;
    if (mVehicle && actor->mCollInfo == mOwn) actor->mCollInfo = mVehicle;
    mVehicle = nullptr;
    mReleased = true;
}
