#include "pc_p2_campaign_actor.h"
#include "pc_p2_sarai_host.h"
#include "pc_p2_demon_bridge.h"
#include "pc_p2_sarai_capture_bridge.h"
#include "Collision.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Shape.h"
#include "Stickers.h"
#include "Graphics.h"
#include "Texture.h"
#include "gameflow.h"
#include "sysNew.h"
#include "Generator.h"
#include "teki.h"
#include <cmath>
#include <cstdio>
#include <vector>

namespace {
std::uint64_t nextSaraiHostToken = 0;
// Opaque lane identity for the bound captain; the shared bridge keeps the real
// Navi* link, this only keys the engine-free lifecycle bookkeeping.
std::uint64_t saraiCaptainId(Navi* captain) { return reinterpret_cast<std::uintptr_t>(captain); }
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
    // Teardown revokes before disposal: manager reset destroys bound hosts,
    // and without this the Pikmin mouth bridge would keep a mouth link (and
    // claim) against a freed owner. sceneExit() is idempotent.
    sceneExit();
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
    if (mNaturalEnabled) { updateNatural(); return; }
    updateMouths();
}

void P2SaraiHost::sceneExit()
{
    if (mSceneExited) return;
    pc_p2_sarai_owner_lost(mOwnerToken);
    mSceneExited = true;
    mRenderedFrame = -1;
    mNaturalMotionStarted = false;
    mPlayer.cancel();
    pc_demon_owner_lost(mOwnerToken);
    mLifecycle.sceneExit();
    mPikminTarget = nullptr;
    mReacquireCooldown = 0.0f;
    resetMouthPose();
}

// Mouth capture/attachment receiver (source eatPikmin admission against the
// live mouth CollPart; carried, never swallowed). Delegates the stick binding
// to the bridge, which owns exactly-once/address-reuse safety.
bool P2SaraiHost::capturePiki(Piki* piki, unsigned slot)
{
    if (!mLoaded || slot >= 2 || !mMouths[slot]) return false;
    return pc_p2_sarai_piki_capture(piki, this, mMouths[slot], mOwnerToken, slot);
}
bool P2SaraiHost::releasePiki(Piki* piki) { return pc_p2_sarai_piki_release(piki); }
unsigned P2SaraiHost::carriedCount() const { return pc_p2_sarai_carried_count(const_cast<P2SaraiHost*>(this)); }
unsigned P2SaraiHost::dropOwned(float damage, float downSpeed) { return pc_p2_sarai_drop_owned(this, damage, downSpeed); }
unsigned P2SaraiHost::flickOwned() { return pc_p2_sarai_flick_owned(this); }

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

// --- Natural captor route (#457) --------------------------------------------

void P2SaraiHost::enableNatural(float moveSpeed, float turnSpeed, float maxTurnAngleDegrees,
                                float attackRange, float territoryRadius, float viewAngleDegrees,
                                float sightRadius, const Vector3f& home)
{
    const bool finite = std::isfinite(moveSpeed) && moveSpeed >= 0.0f
        && std::isfinite(turnSpeed) && turnSpeed >= 0.0f
        && std::isfinite(maxTurnAngleDegrees) && maxTurnAngleDegrees >= 0.0f
        && std::isfinite(attackRange) && attackRange >= 0.0f
        && std::isfinite(territoryRadius) && territoryRadius >= 0.0f
        && std::isfinite(viewAngleDegrees) && viewAngleDegrees >= 0.0f
        && std::isfinite(sightRadius) && sightRadius >= 0.0f
        && std::isfinite(home.x) && std::isfinite(home.y) && std::isfinite(home.z);
    if (!finite) return;
    mNatMoveSpeed = moveSpeed;
    mNatTurnSpeed = turnSpeed;
    mNatMaxTurnDegrees = maxTurnAngleDegrees;
    mNatAttackRange = attackRange;
    mNatTerritoryRadius = territoryRadius;
    mNatViewAngle = viewAngleDegrees;
    mNatSightRadius = sightRadius;
    mNatHome = home;
    mFacingRadians = mSRT.r.y;
    mCaptor.reset();
    mPlayer.cancel();
    mNaturalMotionStarted = false;
    mLifecycle.reset();
    mCaptureWindowTicks = 0;
    mPikminTarget = nullptr;
    mReacquireCooldown = 0.0f;
    mStatusTicks = 0;
    mNatKeyEvent = p2sarai::KeyEvent::None;
    // Deterministic Wait spawn so the approach route is reproducible.
    mFsm.spawn(0.1f);
    mNaturalEnabled = true;
}

void P2SaraiHost::setNaturalMotions(const p2retail::Motion& wait, const p2retail::Motion& move,
                                    const p2retail::Motion& attack, const p2retail::Motion& catchFly,
                                    const p2retail::Motion& fallMeck)
{
    mNatWait = wait;
    mNatMove = move;
    mNatAttack = attack;
    mNatCatchFly = catchFly;
    mNatFallMeck = fallMeck;
    mNaturalMotionsSet = wait.name == "wait1.bca" && move.name == "move1.bca"
        && attack.name == "attack1.bca" && catchFly.name == "waitact2.bca"
        && fallMeck.name == "waitact1.bca";
}

void P2SaraiHost::setNaturalPoseProfiles(const char* waitProfile, const char* moveProfile,
                                         const char* attackProfile, const char* catchProfile,
                                         const char* fallProfile)
{
    mNatWaitProfile = waitProfile ? waitProfile : "";
    mNatMoveProfile = moveProfile ? moveProfile : "";
    mNatAttackProfile = attackProfile ? attackProfile : "";
    mNatCatchProfile = catchProfile ? catchProfile : "";
    mNatFallProfile = fallProfile ? fallProfile : "";
}

int P2SaraiHost::naturalPhase() const
{
    switch (mFsm.state()) {
    case p2sarai::State::Attack: return 2;
    case p2sarai::State::CatchFly: return 3;
    case p2sarai::State::FallMeck: return 4;
    case p2sarai::State::Wait:
    case p2sarai::State::Move: return 1;
    default: return 0;
    }
}

bool P2SaraiHost::forceDrop(Navi* target, float damage, float speed)
{
    const std::uint64_t captain = saraiCaptainId(target);
    if (!mLifecycle.occupied() || !target || !pc_demon_owned_by(target, this)) {
        mLifecycle.observeDetached();
        return false;
    }
    const bool released = pc_demon_forced_release(target, damage, speed);
    if (released) {
        mLifecycle.interrupt(captain);
        armReacquireCooldown();
    }
    return released;
}

void P2SaraiHost::release(Navi* target)
{
    if (target && pc_demon_owned_by(target, this)) pc_demon_release(target);
    mLifecycle.detach();
    mPikminTarget = nullptr;
    mNaturalMotionStarted = false;
    mPlayer.cancel();
}

// Map the FSM's symbolic motion to the matching source clip and sampled pose
// bank. Returns false and leaves the previous motion in place when the profile
// is not preloaded (assets are staged during setup, never loaded mid-clock).
bool P2SaraiHost::startNaturalMotion(p2sarai::Motion motion)
{
    const p2retail::Motion* source = nullptr;
    const char* profile = nullptr;
    switch (motion) {
    case p2sarai::Motion::Wait:     source = &mNatWait;     profile = mNatWaitProfile.c_str(); break;
    case p2sarai::Motion::Move:     source = &mNatMove;     profile = mNatMoveProfile.c_str(); break;
    case p2sarai::Motion::Attack:   source = &mNatAttack;   profile = mNatAttackProfile.c_str(); break;
    case p2sarai::Motion::CatchFly: source = &mNatCatchFly; profile = mNatCatchProfile.c_str(); break;
    case p2sarai::Motion::FallMeck: source = &mNatFallMeck; profile = mNatFallProfile.c_str(); break;
    default: return false;
    }
    if (!mNaturalMotionsSet || source->name.empty() || !profile || !*profile) return false;
    if (!switchPoseMeshes(profile)) return false;
    if (!mPlayer.start(*source)) return false;
    mNaturalMotionStarted = true;
    applyNaturalPose();
    return true;
}

// Sample the latest banked pose at or before the source clock frame; no
// interpolation or event scheduling is implied.
void P2SaraiHost::applyNaturalPose()
{
    const auto& samples = mPoseBank.samples();
    const float frame = mPlayer.frame();
    const P2SaraiMouthFrame* selected = nullptr;
    for (const auto& pose : samples)
        if (float(pose.frame) <= frame) selected = &pose;
    if (!selected && !samples.empty()) selected = &samples.front();
    if (selected) applyPoseFrame(selected->frame);
}

// Post-drop reacquisition arm (FallMeck::cleanup resetAttackableTimer(0)
// analogue): suppress acquisition/catch for kReacquireCooldownSeconds and
// re-arm the captor 3 s acquisition gate, so the next approach is a fresh
// retail Wait/Move scan instead of an instant recapture.
void P2SaraiHost::armReacquireCooldown()
{
    mReacquireCooldown = kReacquireCooldownSeconds;
    mPikminTarget = nullptr;
    mCaptor.reset();
}

// Retail getAttackableTarget() (Sarai.cpp) transcribed against the P1 Pikmin
// manager: inside-territory gate, then alive Pikmin that are not mouth-stuck
// anywhere, not stuck to this host or its bound anchor (retail mSticker !=
// this), within the source view half-angle (PI * DEG2RAD * mViewAngle) and
// sight radius. Nearest-first selection spreads multiple Sarai across the
// squad (the lane's capture.h mouth-selection order); eligibility itself is
// verbatim retail. Floor-triangle check has no P1-port equivalent and is
// treated as true (labelled accommodation: P1 Pikmin are always grounded).
// The captain is NEVER a candidate here: retail scans pikiMgr only.
Piki* P2SaraiHost::acquirePikminTarget(int& enumerated)
{
    enumerated = 0;
    if (!pikiMgr) return nullptr;
    const float homeX = mSRT.t.x - mNatHome.x, homeZ = mSRT.t.z - mNatHome.z;
    const p2sarai::TargetQuery query{
        homeX * homeX + homeZ * homeZ, mNatTerritoryRadius, mNatViewAngle, mNatSightRadius};
    Piki* best = nullptr;
    float bestDist = 0.0f;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (!p) continue;
        ++enumerated;
        if (!p->isAlive() || p->isStickToMouth()) continue;
        Creature* stick = p->getStickObject();
        if (stick == static_cast<Creature*>(this)) continue;
        if (mBoundActor && stick == static_cast<Creature*>(mBoundActor)) continue;
        const Vector3f delta = p->getPosition() - mMouths[0]->mCentre;
        const float sqrDistXZ = delta.x * delta.x + delta.z * delta.z;
        float bearing = std::atan2(delta.x, delta.z) - mFacingRadians;
        while (bearing > p2sarai::kPi) bearing -= 2.0f * p2sarai::kPi;
        while (bearing < -p2sarai::kPi) bearing += 2.0f * p2sarai::kPi;
        p2sarai::TargetCandidate candidate;
        candidate.alive = true;
        candidate.isPikmin = true;
        candidate.stickToMouth = false;
        candidate.stickerIsSelf = false;
        candidate.floorTriangle = true;
        candidate.angleRad = bearing;
        candidate.sqrDistXZ = sqrDistXZ;
        if (!p2sarai::targetable(query, candidate)) continue;
        if (!best || sqrDistXZ < bestDist) {
            best = p;
            bestDist = sqrDistXZ;
        }
    }
    return best;
}

// Ordinary captor front end: retail Pikmin-first target acquisition,
// capped-turn approach, the isolated Sarai FSM (Wait/Move/Attack/CatchFly/
// FallMeck), source Attack capture window and the registered Pikmin
// damaging drop (fallMeckGround). Pikmin capture delivery goes through the
// Pikmin mouth bridge; the captain path below runs only for zero-Pikmin
// rooms and never writes captain stick fields itself.
void P2SaraiHost::updateNatural()
{
    const float dt = gsys ? gsys->getFrameTime() : 0.0f;
    if (!std::isfinite(dt) || dt <= 0.0f || dt > 1.0f) return;
    // Ordinary anchor death: the spawned actor owns the corpse. Report once and
    // stop the captor clock; the engine's corpse pipeline (dieSoon/becomePellet)
    // handles the pellet that the Pod receipt resolves.
    if (mBoundActor && !mBoundActor->isAlive()) {
        if (!mDead) {
            mDead = true;
            const unsigned generator = mBoundActor->mGenerator ? pc_p2_campaign_token(mBoundActor) : 0u;
            std::printf("P2_SARAI_DEAD source_id=23 generator=%u\n", generator);
            std::fflush(stdout);
        }
        release(nullptr);
        return;
    }
    // Source clocks advance in 30 fps animation frames, capped to one frame per
    // update so the Attack capture window cannot be skipped.
    float frames = dt * 30.0f;
    if (frames > 1.0f) frames = 1.0f;

    Navi* target = naviMgr ? naviMgr->getNavi() : nullptr;
    const bool haveCaptain = target && target->isAlive();
    if (mLifecycle.occupied() && (!target || !pc_demon_owned_by(target, this))) mLifecycle.observeDetached();
    // Validate the chased Pikmin every tick (Attack mTargetCreature analogue):
    // a dead target, or one mouth-held by another owner, ends the hunt and the
    // FSM returns to Move. A captive WE hold stays targeted through Attack END
    // so the success path reaches CatchFly (retail mTargetCreature lifetime).
    if (mPikminTarget && (!mPikminTarget->isAlive()
        || (mPikminTarget->isStickToMouth() && !pc_p2_sarai_piki_owned_by(mPikminTarget, this))))
        mPikminTarget = nullptr;

    // Advance the current source motion and collect its due key events.
    bool ended = false;
    mNatKeyEvent = p2sarai::KeyEvent::None;
    if (mNaturalMotionStarted) {
        std::vector<p2retail::Event> events;
        const auto update = mPlayer.advance(frames, [&](p2retail::Event event) { events.push_back(event); });
        if (update == p2retail::Update::Ok || update == p2retail::Update::Replaced) {
            for (const auto& event : events) {
                if (event.type == 1000) ended = true;
                else if (event.type == 3) mNatKeyEvent = p2sarai::KeyEvent::Key3;
                else if (event.type == 4) mNatKeyEvent = p2sarai::KeyEvent::Key4;
            }
            applyNaturalPose();
        }
    }

    // Acquisition/approach runs against the stable rest effector; the Attack,
    // CatchFly and FallMeck states keep the sampled animated mouth pose.
    // Retail scans Pikmin first: while the post-drop cooldown runs, or both
    // mouths are full, no acquisition is attempted (bounded reacquisition).
    if (mReacquireCooldown > 0.0f) {
        mReacquireCooldown -= dt;
        if (mReacquireCooldown < 0.0f) mReacquireCooldown = 0.0f;
    }
    const unsigned mouthHeld = carriedCount();
    const bool cooldownFree = mReacquireCooldown <= 0.0f;
    // `scanned` records whether the Pikmin pass ran, so the captain fallback
    // below can tell "empty room" from "suppressed pass".
    Piki* pikmin = nullptr;
    int pikminEnumerated = 0;
    bool scanned = false;
    if (mPikminTargeting && cooldownFree && mouthHeld < p2sarai::kMouthSlots) {
        scanned = true;
        if (mPikminTarget && mPikminTarget->isAlive()) {
            pikmin = mPikminTarget;
        } else {
            pikmin = acquirePikminTarget(pikminEnumerated);
            mPikminTarget = pikmin;
        }
        if (pikmin) pikminEnumerated = pikminEnumerated > 0 ? pikminEnumerated : 1;
    } else if (mPikminTarget && !mPikminTarget->isAlive()) {
        mPikminTarget = nullptr;
    }
    // Captain fallback ONLY for rooms that stage zero Pikmin (private-room
    // fixture accommodation). Any enumerated Pikmin disables it: retail never
    // targets captains, and the #834 campaign loop was eight Sarai holding one
    // captain while ignoring twenty Pikmin.
    const bool useCaptain = !mPikminTargeting
        || (mPikminTargeting && scanned && pikminEnumerated == 0 && pikmin == nullptr);
    const bool approachPhase = useCaptain
        ? (!mLifecycle.occupied() && mFsm.state() != p2sarai::State::Attack)
        : (mouthHeld == 0 && mFsm.state() != p2sarai::State::Attack);
    P2SaraiCaptor::Output captorOut;
    // Pikmin approach drive: capped-turn toward the live target bearing,
    // advance while outside grab range (retail walkToTarget shape at the
    // fixture-tuned speed; the captor struct stays the captain path's).
    float pikminVelX = 0.0f, pikminVelZ = 0.0f;
    if (approachPhase && !useCaptain && pikmin) {
        const Vector3f delta = pikmin->getPosition() - mMouths[0]->mCentre;
        const float sqrDistXZ = delta.x * delta.x + delta.z * delta.z;
        float bearing = std::atan2(delta.x, delta.z) - mFacingRadians;
        while (bearing > p2sarai::kPi) bearing -= 2.0f * p2sarai::kPi;
        while (bearing < -p2sarai::kPi) bearing += 2.0f * p2sarai::kPi;
        const float cap = mNatMaxTurnDegrees * p2sarai::kDeg2Rad;
        const float turn = std::min(std::fabs(bearing) * mNatTurnSpeed, cap);
        if (std::isfinite(turn)) {
            mFacingRadians += bearing < 0.0f ? -turn : turn;
            mSRT.r.y = mFacingRadians;
        }
        if (sqrDistXZ <= mNatAttackRange * mNatAttackRange) {
            // Inside grab range: hold position so the Attack window runs
            // against a stable mouth (retail turnToTarget-only close-in).
        } else if (mNatMoveSpeed > 0.0f) {
            pikminVelX = std::sin(mFacingRadians) * mNatMoveSpeed;
            pikminVelZ = std::cos(mFacingRadians) * mNatMoveSpeed;
        }
    }
    if (approachPhase && useCaptain) {
        resetMouthPose();
        P2SaraiCaptor::Input captor;
        captor.faceDirection = mFacingRadians;
        const float homeX = mSRT.t.x - mNatHome.x, homeZ = mSRT.t.z - mNatHome.z;
        captor.homeDistanceSquaredXZ = homeX * homeX + homeZ * homeZ;
        captor.territoryRadius = mNatTerritoryRadius;
        captor.viewAngleDegrees = mNatViewAngle;
        captor.sightRadius = mNatSightRadius;
        captor.moveSpeed = mNatMoveSpeed;
        captor.turnSpeed = mNatTurnSpeed;
        captor.maxTurnAngleDegrees = mNatMaxTurnDegrees;
        captor.attackRange = mNatAttackRange;
        captor.delta = dt;
        P2SaraiCaptain captain;
        if (haveCaptain) {
            const Vector3f delta = target->mSRT.t - mMouths[0]->mCentre;
            captain.alive = target->isAlive();
            captain.stickToMouth = target->isStickToMouth();
            captain.sqrDistXZ = delta.x * delta.x + delta.z * delta.z;
            float bearing = std::atan2(delta.x, delta.z) - mFacingRadians;
            while (bearing > p2sarai::kPi) bearing -= 2.0f * p2sarai::kPi;
            while (bearing < -p2sarai::kPi) bearing += 2.0f * p2sarai::kPi;
            captain.angleRad = bearing;
            captor.captains = &captain;
            captor.count = 1;
        }
        captor.active = true;
        captorOut = mCaptor.step(captor);
    } else if (approachPhase) {
        resetMouthPose();
    }
    const bool targetPresent = useCaptain
        ? (captorOut.valid && captorOut.targetFound)
        : (pikmin != nullptr);
    const bool hasTargetCreature = useCaptain ? haveCaptain : (pikmin != nullptr);

    // Isolated source FSM tick with live facts. This private host owns no health
    // model; the bound anchor actor is the damage/lifetime anchor (real engine
    // health, Pikmin receivers, engine corpse on death).
    p2sarai::In in;
    in.deltaTime = dt;
    in.health = mBoundActor ? mBoundActor->mHealth : 100.0f;
    // Source Sarai.cpp: the climb/escape decisions read the live body-latched
    // Pikmin count (mStuckPikminCount) and the mouth-carried captives
    // (getCatchTargetNum). A hardcoded zero body count pins the FSM out of
    // Fall/Damage/Flick forever, so no amount of normally-thrown Pikmin could
    // ever weigh the host down. Feed the anchor's real sticker count; the
    // anchor only ever carries body-latched Pikmin (mouth captives bind to
    // this host, never to the anchor). No combat causality is claimed for
    // this input: guarded runs show zero anchor sticks, so the observed kills
    // come from the formation swarm bites, not from this path (which only
    // unblocks future Fall/Damage/Flick transitions once latches occur).
    int bodyStuck = 0;
    if (mBoundActor && mBoundActor->isAlive()) {
        Stickers stuck(mBoundActor);
        bodyStuck = stuck.getNumStickers();
        if (bodyStuck < 0) bodyStuck = 0;
    }
    in.bodyStuckCount = bodyStuck;
    // Mouth captives are the bridge-bound Pikmin (getCatchTargetNum); the
    // captain occupancy only counts on the legacy captain fallback path.
    in.mouthCarried = int(carriedCount()) + (mLifecycle.occupied() ? 1 : 0);
    in.purpleLatched = false;
    in.mapY = 0.0f;
    in.positionY = mSRT.t.y;
    in.targetPresent = targetPresent;
    in.hasTargetCreature = hasTargetCreature;
    in.targetFrame = mPlayer.frame();
    in.distToPatrolTargetXZ = 1.0e9f;
    in.keyEvent = mNatKeyEvent;
    in.motionFinished = ended;
    in.randomUnit = 0.5f;
    const p2sarai::Out out = mFsm.tick(in);

    if (out.motionChanged) startNaturalMotion(out.motion);
    // Loop-tolerant clips (wait1/move1/waitact2) only reach END once the source
    // finishMotion decision is forwarded.
    if (out.finishing) mPlayer.finishMotion();

    // Source Attack capture window: 16 < frame <= 30 (retail catchTarget() ->
    // EnemyFunc::eatPikmin against the mouth slots). Pikmin admission goes
    // through the Pikmin mouth bridge into the first free slot; the captain
    // window below runs ONLY on the zero-Pikmin fallback path.
    if (out.attemptCatch && !useCaptain && pikmin && cooldownFree
        && carriedCount() < p2sarai::kMouthSlots && !pikmin->isStickTo()) {
        ++mCaptureWindowTicks;
        const unsigned slot = carriedCount() == 0 ? 0u : 1u;
        const Vector3f delta = pikmin->getPosition() - staticMouthCentre(slot);
        if (delta.squaredLength() < p2sarai::kMouthRadius * p2sarai::kMouthRadius
            && capturePiki(pikmin, slot)) {
            ++mPikminCaptures;
            const unsigned generator = mBoundActor && mBoundActor->mGenerator
                ? pc_p2_campaign_token(mBoundActor) : 0u;
            std::printf("P2_SARAI_PIKMIN_CAPTURE source_id=23 generator=%u slot=%u owner_exact=1\n",
                        generator, slot);
            std::fflush(stdout);
        }
    }
    if (out.attemptCatch && useCaptain && !mLifecycle.occupied() && haveCaptain && !target->isStickTo()) {
        ++mCaptureWindowTicks;
        const Vector3f delta = target->mSRT.t - staticMouthCentre(0);
        if (delta.squaredLength() < 15.0f * 15.0f
            && pc_demon_capture(target, this, mMouths[0], mOwnerToken, 0)) {
            mLifecycle.capture(saraiCaptainId(target), mOwnerToken, 0);
        }
    }
    // Retail Dead/Fall/Damage entry calls flickStickTarget(): harmlessly
    // detach mouth captives (escape receiver, no damage). FallMeck Key3 owns
    // the one-shot damaging drop (fallMeckGround) through the registered
    // receiver; ownership is revoked by the bridge itself. Every damaging or
    // detaching release arms the reacquisition cooldown (bounded, no instant
    // recapture: the #834 loop).
    if (out.flickAttackers && carriedCount() > 0) {
        const unsigned detached = flickOwned();
        if (detached > 0) {
            std::printf("P2_SARAI_PIKMIN_FLICK source_id=23 detached=%u\n", detached);
            std::fflush(stdout);
            armReacquireCooldown();
        }
    }
    if (out.drop && carriedCount() > 0) {
        const unsigned released = dropOwned(10.0f, p2sarai::Parms().fallMeckSpeed);
        std::printf("P2_SARAI_PIKMIN_DROP source_id=23 released=%u\n", released);
        std::fflush(stdout);
        armReacquireCooldown();
    } else if (out.drop && mLifecycle.occupied() && target) {
        if (pc_demon_forced_release(target, 10.0f, p2sarai::Parms().fallMeckSpeed)) mLifecycle.detach();
        armReacquireCooldown();
    }

    if (approachPhase && !useCaptain && pikmin) {
        mSRT.t.x += pikminVelX * dt;
        mSRT.t.z += pikminVelZ * dt;
        // Keep the mouth at target height so the 3D capture proximity can
        // actually be satisfied, mirroring the captain path.
        mSRT.t.y += pikmin->getPosition().y - mMouths[0]->mCentre.y;
    }
    if (approachPhase && useCaptain && captorOut.valid && captorOut.targetFound) {
        mFacingRadians = captorOut.faceDirection;
        mSRT.r.y = mFacingRadians;
        if (!captorOut.beginAttack) {
            mSRT.t.x += captorOut.velocityX * dt;
            mSRT.t.z += captorOut.velocityZ * dt;
            // Keep the mouth at captain height so the 3D capture proximity can
            // actually be satisfied, mirroring the Demon natural host.
            if (target) mSRT.t.y += target->mSRT.t.y - mMouths[0]->mCentre.y;
        }
    }
    // Carriage/cooldown census for the campaign log (host-side so the
    // engine-free manager lifecycle test, which links test-owned host
    // bodies, is untouched).
    if (++mStatusTicks % 90 == 0) {
        const unsigned generator = mBoundActor && mBoundActor->mGenerator
            ? pc_p2_campaign_token(mBoundActor) : 0u;
        std::printf("P2_SARAI_CARRY tick=%d generator=%u state=%d pikmin=%u captures=%u cooldown=%.1f\n",
                    mStatusTicks, generator, int(mFsm.state()), carriedCount(),
                    mPikminCaptures, mReacquireCooldown);
        std::fflush(stdout);
    }
    updateMouths();
}

bool P2SaraiHost::bindNativeActor(BTeki* actor, unsigned generatorId, int tekiType)
{
    if (!actor || !actor->mGenerator || pc_p2_campaign_token(actor) != generatorId || actor->mTekiType != tekiType)
        return false;
    if (mBoundActor && mBoundActor != actor) return false;
    mBoundActor = actor;
    mDead = false;
    return true;
}

void P2SaraiHost::unbindNativeActor(BTeki* actor)
{
    if (actor && mBoundActor == actor) mBoundActor = nullptr;
}

bool P2SaraiHost::revalidateNativeActor(BTeki* actor, unsigned generatorId, int tekiType)
{
    if (!actor || mBoundActor != actor) return false;
    if (!actor->mGenerator || pc_p2_campaign_token(actor) != generatorId || actor->mTekiType != tekiType) {
        mBoundActor = nullptr;
        return false;
    }
    return true;
}
