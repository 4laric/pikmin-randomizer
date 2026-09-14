#include "pc_p2_sarai_host.h"
#include "Collision.h"
#include "Shape.h"
#include "Graphics.h"
#include "Texture.h"
#include "gameflow.h"
#include "sysNew.h"
#include <cmath>

namespace {
std::uint64_t nextSaraiHostToken = 0;
}

P2SaraiHost::P2SaraiHost()
    : Creature(nullptr)
    , mShape(nullptr)
    , mMouths { new CollPart, new CollPart }
    , mLoaded(false)
    , mSceneExited(false)
    , mOwnerToken(++nextSaraiHostToken)
{
    mStickListHead = nullptr;
    mSRT.s.set(1.0f, 1.0f, 1.0f);
}

P2SaraiHost::~P2SaraiHost()
{
    // The private host owns its two mouth parts and never registers them with
    // the engine, so teardown deletes them explicitly.
    delete mMouths[0];
    delete mMouths[1];
    mMouths[0] = nullptr;
    mMouths[1] = nullptr;
}

bool P2SaraiHost::load(const char* modelPath, const Vector3f& mouthA, const Vector3f& mouthB)
{
    if (!modelPath || !std::isfinite(mouthA.x) || !std::isfinite(mouthA.y) || !std::isfinite(mouthA.z)
        || !std::isfinite(mouthB.x) || !std::isfinite(mouthB.y) || !std::isfinite(mouthB.z))
        return false;
    const int previousHeap = gsys->setHeap(SYSHEAP_App);
    mShape = gameflow.loadShape(modelPath, true);
    gsys->setHeap(previousHeap);
    if (!mShape)
        return false;
    for (int i = 0; i < mShape->mTexAttrCount; ++i)
        if (mShape->mTexAttrList[i].mTexture) mShape->mTexAttrList[i].mTexture->attach();
    mMouthLocal[0].makeSRT(Vector3f(1, 1, 1), Vector3f(0, 0, 0), mouthA);
    mMouthLocal[1].makeSRT(Vector3f(1, 1, 1), Vector3f(0, 0, 0), mouthB);
    mStaticMouth[0] = mMouthLocal[0];
    mStaticMouth[1] = mMouthLocal[1];
    for (auto* mouth : mMouths) {
        mouth->mPartType = PART_BoundSphere;
        mouth->mRadius = 15.0f;
        mouth->mJointMatrix.makeIdentity();
    }
    mLoaded = true;
    mSceneExited = false;
    updateMouths();
    return true;
}

void P2SaraiHost::setPosition(const Vector3f& position)
{
    mSRT.t = position;
    updateMouths();
}

bool P2SaraiHost::setMouthPose(const Matrix4f& mouthA, const Matrix4f& mouthB)
{
    if (!mLoaded) return false;
    const Matrix4f* poses[2] = { &mouthA, &mouthB };
    for (const Matrix4f* pose : poses) {
        for (int r = 0; r < 4; ++r)
            for (int c = 0; c < 4; ++c)
                if (!std::isfinite(pose->mMtx[r][c]) || std::fabs(pose->mMtx[r][c]) > 1.0e6f) return false;
        if (pose->mMtx[3][0] != 0 || pose->mMtx[3][1] != 0 || pose->mMtx[3][2] != 0 || pose->mMtx[3][3] != 1) return false;
    }
    mMouthLocal[0] = mouthA;
    mMouthLocal[1] = mouthB;
    updateMouths();
    return true;
}

void P2SaraiHost::updateMouths()
{
    Matrix4f world;
    world.makeSRT(mSRT.s, mSRT.r, mSRT.t);
    for (int i = 0; i < 2; ++i) {
        world.multiplyTo(mMouthLocal[i], mMouths[i]->mJointMatrix);
        const Matrix4f& joint = mMouths[i]->mJointMatrix;
        mMouths[i]->mCentre.set(joint.mMtx[0][3], joint.mMtx[1][3], joint.mMtx[2][3]);
    }
}

// Restore the static rest mouth offsets after a sampled pose bank moved the
// local matrices. A later admission slice can use these stable parts.
void P2SaraiHost::resetMouthPose()
{
    mMouthLocal[0] = mStaticMouth[0];
    mMouthLocal[1] = mStaticMouth[1];
    updateMouths();
}

Vector3f P2SaraiHost::mouthCentre(unsigned slot) const { return slot < 2 ? mMouths[slot]->mCentre : Vector3f(0, 0, 0); }
Vector3f P2SaraiHost::staticMouthCentre(unsigned slot) const
{
    if (slot >= 2) return Vector3f(0, 0, 0);
    Matrix4f world, joint;
    world.makeSRT(mSRT.s, mSRT.r, mSRT.t);
    world.multiplyTo(mStaticMouth[slot], joint);
    return Vector3f(joint.mMtx[0][3], joint.mMtx[1][3], joint.mMtx[2][3]);
}

void P2SaraiHost::update()
{
    if (!mLoaded) return;
    updateMouths();
}

void P2SaraiHost::sceneExit()
{
    mSceneExited = true;
    mRenderedFrame = -1;
    resetMouthPose();
}

void P2SaraiHost::doKill() { sceneExit(); }

void P2SaraiHost::refresh(Graphics& gfx)
{
    // The host draws only while live; sceneExit() stops rendering without
    // invalidating the loaded shape.
    if (!mShape || mSceneExited || !gfx.mCamera)
        return;
    gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx, gfx.mCamera->mFov,
        gfx.mCamera->mAspectRatio, gfx.mCamera->mNear, gfx.mCamera->mFar, 1.0f);
    gfx.useMaterial(nullptr);
    gfx.setDepth(true);
    Matrix4f world, view;
    world.makeSRT(mSRT.s, mSRT.r, mSRT.t);
    gfx.mCamera->mLookAtMtx.multiplyTo(world, view);
    mShape->updateAnim(gfx, view, nullptr, nullptr);
    mShape->drawshape(gfx, *gfx.mCamera, nullptr);
    ++mRenderCount;
}

bool P2SaraiHost::loadMouthPoses(const char* path) { return mPoseMeshes.empty() && mPoseBank.load(path); }
bool P2SaraiHost::applyMouthFrame(int frame)
{
    const auto* pose = mPoseBank.exact(frame);
    if (!pose) return false;
    Matrix4f mouths[2];
    for (int slot = 0; slot < 2; ++slot) {
        mouths[slot].makeIdentity();
        for (int r = 0; r < 3; ++r)
            for (int c = 0; c < 4; ++c)
                mouths[slot].mMtx[r][c] = pose->values[slot * 12 + r * 4 + c];
    }
    return setMouthPose(mouths[0], mouths[1]);
}

// Load sampled meshes once in the App heap. Switching only changes pointers and
// the active bank. Bank/vector copies can allocate at transitions; there are no
// per-frame model loads or global cache mutations.
bool P2SaraiHost::preloadPoseMeshes(const char* profile)
{
    if (!mLoaded || !profile || !*profile) return false;
    for (const auto& set : mPoseSets)
        if (set.profile == profile) return true;

    PoseSet set;
    set.profile = profile;
    if (!set.bank.load(profile)) return false;
    for (const auto& pose : set.bank.samples()) if (pose.model.empty()) return false;
    const int previousHeap = gsys->setHeap(SYSHEAP_App);
    for (const auto& pose : set.bank.samples()) {
        const std::string path = "courses/pikmin2room/" + pose.model;
        Shape* shape = gameflow.loadShape(path.c_str(), true);
        if (!shape) { gsys->setHeap(previousHeap); return false; }
        for (int i = 0; i < shape->mTexAttrCount; ++i)
            if (shape->mTexAttrList[i].mTexture) shape->mTexAttrList[i].mTexture->attach();
        set.meshes.push_back(shape);
    }
    gsys->setHeap(previousHeap);
    mPoseSets.push_back(std::move(set));
    if (mPoseMeshes.empty()) return switchPoseMeshes(profile);
    return true;
}

bool P2SaraiHost::switchPoseMeshes(const char* profile)
{
    if (!mLoaded || !profile || !*profile) return false;
    for (const auto& set : mPoseSets) {
        if (set.profile != profile) continue;
        if (set.bank.samples().size() != set.meshes.size() || set.meshes.empty()) return false;
        mPoseBank = set.bank;
        mPoseMeshes = set.meshes;
        return true;
    }
    // Transitions must use a bank explicitly preloaded during setup; this keeps
    // the host clock free of allocations and makes missing assets observable.
    return false;
}

bool P2SaraiHost::loadPoseMeshes(const char* profile)
{
    if (!mLoaded || !mPoseMeshes.empty()) return false;
    return preloadPoseMeshes(profile);
}

bool P2SaraiHost::applyPoseFrame(int frame)
{
    const auto& samples = mPoseBank.samples();
    if (samples.size() != mPoseMeshes.size()) return false;
    for (unsigned i = 0; i < samples.size(); ++i) {
        if (samples[i].frame != frame) continue;
        if (!applyMouthFrame(frame)) return false;
        mShape = mPoseMeshes[i];
        mRenderedFrame = frame;
        return true;
    }
    return false;
}
