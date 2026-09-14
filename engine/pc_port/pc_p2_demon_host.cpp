#include "pc_p2_demon_host.h"
#include "pc_p2_demon_bridge.h"
#include "Collision.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Shape.h"
#include "Graphics.h"
#include "Texture.h"
#include "teki.h"
#include "Generator.h"
#include "gameflow.h"
#include "sysNew.h"
#include <cmath>
#include <utility>
#include <map>
#include <memory>
#include <fstream>
#include <cstdlib>
#include <cstring>

namespace {
std::uint64_t nextHostToken = 0;
struct ManagerBinding { P2DemonHost* host; unsigned generator; int type; };
std::map<BTeki*, ManagerBinding> managerBindings;
std::vector<std::unique_ptr<P2DemonHost>> managerHosts;
std::size_t managerOrdinaryBindings = 0;

// Find the one spawned arena actor the ordinary Demon host binds to. The
// converted private room spawns a single Dwarf Bulborb (native TEKI_Chappy)
// placeholder as its only enemy generator; an explicit identity may be supplied
// instead. Exactly one match is required, so a stale/ambiguous scene fails closed.
bool findOrdinaryActor(unsigned wantedGenerator, int wantedType, bool fixedIdentity, BTeki*& match)
{
    match = nullptr;
    Iterator actors(tekiMgr); CI_LOOP(actors) {
        BTeki* actor = static_cast<BTeki*>(*actors);
        if (!actor || !actor->mGenerator) continue;
        if (fixedIdentity) {
            if (actor->mGenerator->_70 != wantedGenerator || actor->mTekiType != wantedType) continue;
        } else if (actor->mTekiType != TEKI_Chappy) {
            continue;
        }
        if (match) return false;
        match = actor;
    }
    return match != nullptr;
}

// Ordinary natural captor: bind a private Demon host to the spawned arena actor
// and enable the source front end (target/approach/attack/capture) so the
// production update hook drives it. Default-off; only PIKMIN_DEMON_ORDINARY=1
// reaches here. The captain is never touched by this setup.
void setupOrdinaryHost()
{
    if (!tekiMgr) return;
    const char* gen = std::getenv("PIKMIN_DEMON_ORDINARY_GENERATOR");
    const char* type = std::getenv("PIKMIN_DEMON_ORDINARY_TYPE");
    const bool fixedIdentity = gen && *gen && type && *type;
    const unsigned wantedGenerator = fixedIdentity ? unsigned(std::strtoul(gen, nullptr, 10)) : 0u;
    const int wantedType = fixedIdentity ? std::atoi(type) : TEKI_Chappy;
    BTeki* match = nullptr;
    if (!findOrdinaryActor(wantedGenerator, wantedType, fixedIdentity, match)) return;

    const char* model = std::getenv("PIKMIN_DEMON_ORDINARY_MODEL");
    if (!model || !*model) model = "courses/pikmin2room/demon0.mod";
    float ax, ay, az, bx, by, bz;
    std::ifstream mouths("demon-mouths.txt");
    if (!(mouths >> ax >> ay >> az >> bx >> by >> bz)) return;

    const char* catchProfile = std::getenv("DEMON_CATCHFLY_POSES");
    const char* fallProfile = std::getenv("DEMON_FALLMECK_POSES");
    if (!catchProfile || !*catchProfile) catchProfile = "demon-waitact2-poses.txt";
    if (!fallProfile || !*fallProfile) fallProfile = "demon-waitact1-poses.txt";
    std::ifstream events("demon-retail-events.txt");
    if (!events) return;
    p2retail::Table table;
    try { table = p2retail::read(events); } catch (...) { return; }
    p2retail::Motion attack, catchFly, fallMeck;
    for (const auto& motion : table.motions) {
        if (motion.name == "attack1.bca") attack = motion;
        else if (motion.name == "waitact2.bca") catchFly = motion;
        else if (motion.name == "waitact1.bca") fallMeck = motion;
    }
    if (attack.name.empty() || catchFly.name.empty() || fallMeck.name.empty()) return;

    auto host = std::make_unique<P2DemonHost>();
    if (!host->load(model, Vector3f(ax, ay, az), Vector3f(bx, by, bz))) return;
    if (!host->preloadPoseMeshes("demon-attack-poses.txt")
        || !host->preloadPoseMeshes(catchProfile)
        || !host->preloadPoseMeshes(fallProfile)) return;
    host->setNaturalMotions(attack, catchFly, fallMeck);
    host->setNaturalPoseProfiles(catchProfile, fallProfile);
    if (!pc_p2_demon_manager_bind(host.get(), match, match->mGenerator->_70, match->mTekiType)) return;
    const Vector3f home = match->getPosition();
    host->setPosition(home);
    // The converted private room's only spawned enemy starts away from the
    // captain, and no patrol/scan state is implemented here, so the view cone is
    // widened and the territory/sight radii cover the room. Approach speed, turn
    // cap and grab range stay at the fixture's natural values.
    host->enableNatural(30.0f, 3.0f, 20.0f, 12.0f, 1000.0f, 360.0f, 1200.0f, home);
    if (!host->naturalEnabled()) return;
    ++managerOrdinaryBindings;
    managerHosts.push_back(std::move(host));
}
}

void pc_p2_demon_manager_setup()
{
    const char* ordinary = std::getenv("PIKMIN_DEMON_ORDINARY");
    if (ordinary && std::strcmp(ordinary, "1") == 0) { setupOrdinaryHost(); return; }
    const char* enabled = std::getenv("PIKMIN_DEMON_AUTO_BIND");
    if (!enabled || std::strcmp(enabled, "1") != 0 || !tekiMgr) return;
    const char* path = std::getenv("PIKMIN_DEMON_BINDINGS");
    std::ifstream input(path && *path ? path : "demon-host-bindings.txt");
    if (!input) return;
    unsigned generator = 0; int type = 0;
    std::string model, pose;
    float ax, ay, az, bx, by, bz;
    while (input >> generator >> type >> model >> ax >> ay >> az >> bx >> by >> bz >> pose) {
        auto host = std::make_unique<P2DemonHost>();
        if (!host->load(model.c_str(), Vector3f(ax, ay, az), Vector3f(bx, by, bz)) || !host->preloadPoseMeshes(pose.c_str())) continue;
        BTeki* match = nullptr;
        Iterator actors(tekiMgr); CI_LOOP(actors) {
            BTeki* actor = static_cast<BTeki*>(*actors);
            if (actor && actor->mGenerator && actor->mGenerator->_70 == generator && actor->mTekiType == type) {
                if (match) { match = nullptr; break; }
                match = actor;
            }
        }
        if (!match || !pc_p2_demon_manager_bind(host.get(), match, generator, type)) continue;
        host->setPosition(match->getPosition());
        managerHosts.push_back(std::move(host));
    }
}

void pc_p2_demon_manager_reset()
{
    for (auto& entry : managerBindings) entry.second.host->unbindNativeActor(entry.first);
    managerBindings.clear();
    managerHosts.clear();
    managerOrdinaryBindings = 0;
}
void pc_p2_demon_manager_forget(BTeki* actor)
{
    if (!actor) return;
    auto it = managerBindings.find(actor);
    if (it != managerBindings.end()) { it->second.host->unbindNativeActor(actor); managerBindings.erase(it); }
}
bool pc_p2_demon_manager_bind(P2DemonHost* host, BTeki* actor, unsigned generatorId, int tekiType)
{
    if (!host || !actor || !host->bindNativeActor(actor, generatorId, tekiType)) return false;
    auto it = managerBindings.find(actor);
    if (it != managerBindings.end() && it->second.host != host) { host->unbindNativeActor(actor); return false; }
    managerBindings[actor] = {host, generatorId, tekiType};
    return true;
}
std::size_t pc_p2_demon_manager_binding_count() { return managerBindings.size(); }
std::size_t pc_p2_demon_manager_render_count() {
    std::size_t total = 0;
    for (const auto& entry : managerBindings) total += entry.second.host->renderCount();
    return total;
}
bool pc_p2_demon_manager_is_bound(BTeki* actor)
{
    auto it = managerBindings.find(actor);
    return it != managerBindings.end() && it->second.host->revalidateNativeActor(actor, it->second.generator, it->second.type);
}
void pc_p2_demon_manager_update()
{
    for (auto it = managerBindings.begin(); it != managerBindings.end();) {
        auto current = it++;
        auto& binding = current->second;
        if (!binding.host->revalidateNativeActor(current->first, binding.generator, binding.type)) {
            managerBindings.erase(current);
            continue;
        }
        binding.host->update();
    }
}
void pc_p2_demon_manager_draw(Graphics& gfx)
{
    for (auto it = managerBindings.begin(); it != managerBindings.end();) {
        auto current = it++;
        auto& binding = current->second;
        if (!binding.host->revalidateNativeActor(current->first, binding.generator, binding.type)) {
            managerBindings.erase(current);
            continue;
        }
        binding.host->refresh(gfx);
    }
}
void pc_p2_demon_manager_update_actor(BTeki* actor)
{
    auto it = managerBindings.find(actor);
    if (it == managerBindings.end()) return;
    auto& binding = it->second;
    if (!binding.host->revalidateNativeActor(actor, binding.generator, binding.type)) {
        managerBindings.erase(it); return;
    }
    // A natural host owns its own approaching position; the spawned actor is its
    // lifetime/identity anchor, not a per-frame transform source. Fixture/injected
    // hosts (natural disabled) keep following the anchor exactly as before.
    if (!binding.host->naturalEnabled()) binding.host->setPosition(actor->getPosition());
    binding.host->update();
}
int pc_p2_demon_manager_natural_phase()
{
    for (const auto& entry : managerBindings)
        if (entry.second.host->naturalEnabled()) return entry.second.host->naturalPhase();
    return 0;
}
std::size_t pc_p2_demon_manager_natural_binding_count() { return managerOrdinaryBindings; }
bool pc_p2_demon_manager_draw_actor(BTeki* actor, Graphics& gfx, const Matrix4f&, bool)
{
    auto it = managerBindings.find(actor);
    if (it == managerBindings.end()) return false;
    auto& binding = it->second;
    if (!binding.host->revalidateNativeActor(actor, binding.generator, binding.type)) {
        managerBindings.erase(it); return false;
    }
    binding.host->refresh(gfx);
    return true;
}

P2DemonHost::P2DemonHost()
    : Creature(nullptr)
    , mShape(nullptr)
    , mMouths { new CollPart, new CollPart }
    , mLoaded(false)
    , mAttackActive(false)
    , mOccupied(0)
    , mOwnerToken(++nextHostToken)
{
    mStickListHead = nullptr;
    mSRT.s.set(1.0f, 1.0f, 1.0f);
}

bool P2DemonHost::load(const char* modelPath, const Vector3f& mouthA, const Vector3f& mouthB)
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
    updateMouths();
    return true;
}

void P2DemonHost::setPosition(const Vector3f& position)
{
    mSRT.t = position;
    updateMouths();
}

bool P2DemonHost::setMouthPose(const Matrix4f& mouthA, const Matrix4f& mouthB)
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

void P2DemonHost::updateMouths()
{
    Matrix4f world;
    world.makeSRT(mSRT.s, mSRT.r, mSRT.t);
    for (int i = 0; i < 2; ++i) {
        world.multiplyTo(mMouthLocal[i], mMouths[i]->mJointMatrix);
        const Matrix4f& joint = mMouths[i]->mJointMatrix;
        mMouths[i]->mCentre.set(joint.mMtx[0][3], joint.mMtx[1][3], joint.mMtx[2][3]);
    }
}

// Restore the static rest mouth offsets after a sampled pose bank rotated the
// local matrices. The approach/acquisition path uses these stable parts.
void P2DemonHost::resetMouthPose()
{
    mMouthLocal[0] = mStaticMouth[0];
    mMouthLocal[1] = mStaticMouth[1];
    updateMouths();
}

bool P2DemonHost::beginAttack()
{
    if (!mLoaded || mAttackActive)
        return false;
    mWindow.reset();
    mOccupied = 0;
    mAttackActive = true;
    return true;
}

bool P2DemonHost::updateAttack(Navi* target, float sourceFrame, bool floorContact)
{
    if (!mAttackActive || !target)
        return false;
    updateMouths();
    const auto decision = mWindow.step(sourceFrame, true, floorContact);
    if (!decision.valid)
        return false;
    if (decision.attemptCapture && !mOccupied) {
        const Vector3f delta = target->mSRT.t - staticMouthCentre(0);
        if (delta.squaredLength() < 15.0f * 15.0f && pc_demon_capture(target, this, mMouths[0], mOwnerToken, 0))
            mOccupied = 1;
    }
    return mOccupied != 0;
}

bool P2DemonHost::endAttack(Navi* target)
{
    if (!mAttackActive)
        return false;
    if (mOccupied && (!target || !pc_demon_owned_by(target, this))) mOccupied = 0;
    const auto decision = P2DemonAttackWindow::eventDecision(target != nullptr, true,
        P2DemonAttackEvent::End, mOccupied);
    mAttackActive = false;
    return decision.next == P2DemonAttackNext::CatchFly && mOccupied != 0;
}

bool P2DemonHost::forceDrop(Navi* target, float damage, float speed)
{
    if (mOccupied && (!target || !pc_demon_owned_by(target, this)))
        mOccupied = 0;
    if (!mOccupied || !target)
        return false;
    const bool released = pc_demon_forced_release(target, damage, speed);
    if (released)
        mOccupied = 0;
    return released;
}
void P2DemonHost::release(Navi* target)
{
    if (target && pc_demon_owned_by(target, this))
        pc_demon_release(target);
    mOccupied = 0;
    mAttackActive = false;
}

bool P2DemonHost::occupied() const { return mOccupied != 0; }
Vector3f P2DemonHost::mouthCentre(unsigned slot) const { return slot < 2 ? mMouths[slot]->mCentre : Vector3f(0, 0, 0); }
Vector3f P2DemonHost::staticMouthCentre(unsigned slot) const
{
    if (slot >= 2) return Vector3f(0, 0, 0);
    Matrix4f world, joint;
    world.makeSRT(mSRT.s, mSRT.r, mSRT.t);
    world.multiplyTo(mStaticMouth[slot], joint);
    return Vector3f(joint.mMtx[0][3], joint.mMtx[1][3], joint.mMtx[2][3]);
}
void P2DemonHost::update()
{
    if (!mLoaded) return;
    if (mNaturalEnabled) { updateNatural(); return; }
    if (mClockMode != 1) return;
    const float dt = gsys ? gsys->getFrameTime() : 0.0f;
    if (!std::isfinite(dt) || dt <= 0.0f || dt > 1.0f) return;
    mSRT.t.x += mTargetVelocity.x * dt;
    mSRT.t.y += mTargetVelocity.y * dt;
    mSRT.t.z += mTargetVelocity.z * dt;
    updateMouths();
}

// Ordinary captor front end: source target acquisition (getAttackableTarget),
// capped-turn approach, then the existing Attack/CatchFly/FallMeck clocks with
// the selected live captain. Capture delivery still goes through pc_demon_capture;
// this method never touches captain stick state directly.
void P2DemonHost::updateNatural()
{
    const float dt = gsys ? gsys->getFrameTime() : 0.0f;
    if (!std::isfinite(dt) || dt <= 0.0f || dt > 1.0f) return;
    // Host clocks advance in source animation frames (30 fps). Cap to one frame
    // per update so the continuous capture window cannot be skipped.
    float frames = dt * 30.0f;
    if (frames > 1.0f) frames = 1.0f;
    Navi* target = naviMgr ? naviMgr->getNavi() : nullptr;
    if (mOccupied && (!target || !pc_demon_owned_by(target, this))) mOccupied = 0;

    if (mOccupied) {
        if (mClockMode == 0) {
            if (!mNaturalMotionsSet || !switchPoseMeshes(mNaturalCatchProfile.c_str()) || !beginCatchFly(mNaturalCatchFly)) {
                release(target);
                return;
            }
            selectCatchFlyTarget(mNaturalHome, 40.0f, mFacingRadians);
            return;
        }
        if (mClockMode == 1) {
            p2demon::CatchFlyInput input{};
            input.mapY = mSRT.t.y;
            input.grabFlightHeight = 25.0f;
            input.riseFactor = 0.4f;
            input.climbingFactor = 1.0f;
            input.grabSpeed = 10.0f;
            input.turnSpeed = mNaturalTurnSpeed;
            input.maxTurnAngleDegrees = mNaturalMaxTurnDegrees;
            input.stuckCount = 1;
            input.heightNext = p2demon::HeightNext::None;
            const auto decision = tickCatchFly(target, frames, input);
            if (decision.next == P2DemonAttackNext::FallMeck || decision.heightNext == p2demon::HeightNext::Fall) {
                if (!mNaturalMotionsSet || !switchPoseMeshes(mNaturalFallProfile.c_str()) || !beginFallMeck(mNaturalFallMeck))
                    release(target);
            }
            return;
        }
        if (mClockMode == 3) {
            const auto decision = tickFallMeck(target, frames, 10.0f, 200.0f);
            if (decision.next == P2DemonAttackNext::Move) mClockMode = 0;
            else if (decision.next == P2DemonAttackNext::Fail) { mClockMode = 0; mOccupied = 0; }
        }
        return;
    }

    if (mAttackActive) {
        const auto decision = tickTimedAttack(target, frames, false);
        if (decision.next == P2DemonAttackNext::CatchFly && mOccupied) {
            if (!mNaturalMotionsSet || !switchPoseMeshes(mNaturalCatchProfile.c_str()) || !beginCatchFly(mNaturalCatchFly))
                mAttackActive = false;
        } else if (decision.next == P2DemonAttackNext::Move) {
            mAttackActive = false;
        }
        return;
    }

    if (!mNaturalMotionsSet || !target || !target->isAlive() || target->isStickToMouth()) return;
    resetMouthPose();
    P2DemonCaptain captain;
    captain.alive = target->isAlive();
    captain.stuckToMouth = target->isStickToMouth();
    // Acquire and approach against the live mouth centre so the source grab
    // window and the capture proximity check share one reference point.
    const Vector3f delta = target->mSRT.t - mMouths[0]->mCentre;
    captain.distanceSquaredXZ = delta.x * delta.x + delta.z * delta.z;
    float bearing = std::atan2(delta.x, delta.z) - mFacingRadians;
    while (bearing > 3.14159265358979323846f) bearing -= 6.28318530717958647692f;
    while (bearing < -3.14159265358979323846f) bearing += 6.28318530717958647692f;
    captain.angleRadians = bearing;

    P2DemonCaptor::Input input;
    input.faceDirection = mFacingRadians;
    const float homeX = mSRT.t.x - mNaturalHome.x, homeZ = mSRT.t.z - mNaturalHome.z;
    input.homeDistanceSquaredXZ = homeX * homeX + homeZ * homeZ;
    input.territoryRadius = mNaturalTerritoryRadius;
    input.viewAngleDegrees = mNaturalViewAngle;
    input.sightRadius = mNaturalSightRadius;
    input.moveSpeed = mNaturalMoveSpeed;
    input.turnSpeed = mNaturalTurnSpeed;
    input.maxTurnAngleDegrees = mNaturalMaxTurnDegrees;
    input.attackRange = mNaturalAttackRange;
    input.delta = dt;
    input.captains = &captain;
    input.count = 1;
    input.active = true;
    const auto out = mCaptor.step(input);
    if (!out.valid) return;
    mFacingRadians = out.faceDirection;
    mSRT.r.y = mFacingRadians;
    if (out.beginAttack) {
        beginTimedAttack(mNaturalAttack);
        return;
    }
    mSRT.t.x += out.velocityX * dt;
    mSRT.t.z += out.velocityZ * dt;
    // The Demon grabs with mouths ~30 units below its origin. Track the
    // captain's height so the effector (mouth centre) can actually reach the
    // 3D capture proximity rather than hovering at a fixed altitude.
    mSRT.t.y += target->mSRT.t.y - mMouths[0]->mCentre.y;
    updateMouths();
}

void P2DemonHost::sceneExit() { mClockMode = 0; mCatchElapsedFrames = 0; mAttackPlayer.cancel(); pc_demon_owner_lost(mOwnerToken); mOccupied = 0; mAttackActive = false; if (mBoundActor) pc_p2_demon_manager_forget(mBoundActor); mBoundActor = nullptr; }
void P2DemonHost::doKill() { sceneExit(); }

void P2DemonHost::refresh(Graphics& gfx)
{
    if (!mShape || !gfx.mCamera)
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
bool P2DemonHost::loadMouthPoses(const char* path) { return mPoseMeshes.empty() && mPoseBank.load(path); }
bool P2DemonHost::applyMouthFrame(int frame)
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
// the active bank. Bank/vector copies can allocate at transitions; there are
// no per-frame model loads or global cache mutations.
bool P2DemonHost::preloadPoseMeshes(const char* profile)
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

bool P2DemonHost::switchPoseMeshes(const char* profile)
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

bool P2DemonHost::loadPoseMeshes(const char* profile)
{
    if (!mLoaded || !mPoseMeshes.empty()) return false;
    return preloadPoseMeshes(profile);
}
bool P2DemonHost::applyPoseFrame(int frame)
{
    const auto& samples = mPoseBank.samples();
    if (samples.size() != mPoseMeshes.size()) return false;
    for (unsigned i=0; i<samples.size(); ++i) {
        if (samples[i].frame != frame) continue;
        if (!applyMouthFrame(frame)) return false;
        mShape = mPoseMeshes[i];
        mRenderedFrame = frame;
        return true;
    }
    return false;
}

// The caller supplies animation-frame deltas from its simulation clock.
// Keep updates <=1 frame so the continuous capture window cannot be skipped.
bool P2DemonHost::beginTimedAttack(const p2retail::Motion& motion)
{
    if (motion.name != "attack1.bca" || mPoseMeshes.empty() || mAttackActive) return false;
    if (!mAttackPlayer.start(motion)) return false;
    if (!beginAttack()) { mAttackPlayer.cancel(); return false; }
    return true;
}

bool P2DemonHost::beginCatchFly(const p2retail::Motion& motion)
{
    if (motion.name != "waitact2.bca" || !mOccupied || mClockMode != 0 || !mAttackPlayer.start(motion)) return false;
    mClockMode = 1;
    mCatchElapsedFrames = 0;
    mClockFinished = false;
    return true;
}

bool P2DemonHost::selectCatchFlyTarget(const Vector3f& home, float radius, float angle)
{
    mCatchTarget = p2demon::selectTarget(home.x, home.y, home.z, radius, angle);
    return mCatchTarget.valid;
}

bool P2DemonHost::selectCatchFlyTargetSeeded(const Vector3f& home, float radius, std::uint32_t seed)
{
    mCatchTarget = p2demon::selectTargetSeeded(home.x, home.y, home.z, radius, seed);
    return mCatchTarget.valid;
}

void P2DemonHost::enableNatural(float moveSpeed, float turnSpeed, float maxTurnAngleDegrees, float attackRange,
                                float territoryRadius, float viewAngleDegrees, float sightRadius, const Vector3f& home)
{
    mNaturalEnabled = std::isfinite(moveSpeed) && moveSpeed >= 0
        && std::isfinite(turnSpeed) && turnSpeed >= 0
        && std::isfinite(maxTurnAngleDegrees) && maxTurnAngleDegrees >= 0
        && std::isfinite(attackRange) && attackRange >= 0
        && std::isfinite(territoryRadius) && territoryRadius >= 0
        && std::isfinite(viewAngleDegrees) && viewAngleDegrees >= 0
        && std::isfinite(sightRadius) && sightRadius >= 0;
    if (!mNaturalEnabled) return;
    mNaturalMoveSpeed = moveSpeed;
    mNaturalTurnSpeed = turnSpeed;
    mNaturalMaxTurnDegrees = maxTurnAngleDegrees;
    mNaturalAttackRange = attackRange;
    mNaturalTerritoryRadius = territoryRadius;
    mNaturalViewAngle = viewAngleDegrees;
    mNaturalSightRadius = sightRadius;
    mNaturalHome = home;
    mCaptor.reset();
}

void P2DemonHost::setNaturalMotions(const p2retail::Motion& attack, const p2retail::Motion& catchFly, const p2retail::Motion& fallMeck)
{
    mNaturalAttack = attack;
    mNaturalCatchFly = catchFly;
    mNaturalFallMeck = fallMeck;
    mNaturalMotionsSet = attack.name == "attack1.bca" && catchFly.name == "waitact2.bca" && fallMeck.name == "waitact1.bca";
}

void P2DemonHost::setNaturalPoseProfiles(const char* catchProfile, const char* fallProfile)
{
    mNaturalCatchProfile = catchProfile ? catchProfile : "";
    mNaturalFallProfile = fallProfile ? fallProfile : "";
}

int P2DemonHost::naturalPhase() const
{
    if (mOccupied) return mClockMode == 3 ? 4 : 3;
    if (mAttackActive) return 2;
    return 1;
}


bool P2DemonHost::bindNativeActor(BTeki* actor, unsigned generatorId, int tekiType)
{
    if (!actor || !actor->mGenerator || actor->mGenerator->_70 != generatorId || actor->mTekiType != tekiType)
        return false;
    if (mBoundActor && mBoundActor != actor) return false;
    mBoundActor = actor;
    return true;
}

void P2DemonHost::unbindNativeActor(BTeki* actor)
{
    if (actor && mBoundActor == actor) mBoundActor = nullptr;
}

bool P2DemonHost::revalidateNativeActor(BTeki* actor, unsigned generatorId, int tekiType)
{
    if (!actor || mBoundActor != actor) return false;
    if (!actor->mGenerator || actor->mGenerator->_70 != generatorId || actor->mTekiType != tekiType) {
        mBoundActor = nullptr;
        return false;
    }
    return true;
}

P2DemonAttackDecision P2DemonHost::tickCatchFly(Navi* target, float delta, p2demon::CatchFlyInput input)
{
    P2DemonAttackDecision result;
    if (mClockMode != 1 || !std::isfinite(delta) || delta <= 0 || delta > 1) return result;
    // The host owns its evolving world position. Callers supply the destination
    // and bounded environment/parameter inputs, never a stale duplicate origin.
    input.x = mSRT.t.x;
    input.y = mSRT.t.y;
    input.z = mSRT.t.z;
    input.elapsedSeconds = mCatchElapsedFrames / 30.0f;
    if (mCatchTarget.valid) {
        input.targetX = mCatchTarget.x;
        input.targetY = mCatchTarget.y;
        input.targetZ = mCatchTarget.z;
    }
    input.targetAttached = mOccupied != 0 && target && pc_demon_owned_by(target, this);
    input.faceDirection = mFacingRadians;
    const auto movement = p2demon::catchFly(input);
    if (!input.targetAttached) {
        mOccupied = 0; mClockMode = 0; mAttackPlayer.cancel();
        result.valid = true; result.next = P2DemonAttackNext::Move; return result;
    }
    mTargetVelocity.set(movement.velocityX, movement.velocityY, movement.velocityZ);
    if (!movement.finishMotion) {
        mFacingRadians = movement.faceDirection;
        mSRT.r.y = mFacingRadians;
    }
    if (!mClockFinished && movement.finishMotion) {
        mAttackPlayer.finishMotion();
        mClockFinished = true;
    }
    mCatchElapsedFrames += delta; // 30 source animation frames per second; independent of loop rewinds.
    bool ended = false;
    if (mAttackPlayer.advance(delta, [&](p2retail::Event event) { ended |= event.type == 1000; }) != p2retail::Update::Ok)
        return result;
    const auto& samples = mPoseBank.samples();
    const P2DemonMouthFrame* selected = nullptr;
    for (const auto& pose : samples) if (pose.frame <= mAttackPlayer.frame()) selected = &pose;
    if (!selected || !applyPoseFrame(selected->frame)) return result;
    result.valid = true;
    if (ended) { mClockMode = 2; result.next = P2DemonAttackNext::FallMeck; }
    else if (movement.next != P2DemonAttackNext::None) result.next = movement.next;
    else if (movement.heightNext != p2demon::HeightNext::None) {
        mClockMode = 0;
        mAttackPlayer.cancel();
        result.heightNext = movement.heightNext;
    }
    return result;
}

bool P2DemonHost::beginFallMeck(const p2retail::Motion& motion)
{
    if (motion.name != "waitact1.bca" || mClockMode != 2 || !mAttackPlayer.start(motion)) return false;
    mClockMode = 3;
    mClockReleased = false;
    return true;
}

P2DemonAttackDecision P2DemonHost::tickFallMeck(Navi* target, float delta, float damage, float speed)
{
    P2DemonAttackDecision result;
    if (mClockMode != 3 || !std::isfinite(delta) || delta <= 0 || delta > 1) return result;
    bool ended = false;
    if (mAttackPlayer.advance(delta, [&](p2retail::Event event) {
            if (event.type == 3 && !mClockReleased)
                mClockReleased = forceDrop(target, damage, speed);
            if (event.type == 1000) ended = true;
        }) != p2retail::Update::Ok) return result;
    const auto& samples = mPoseBank.samples();
    const P2DemonMouthFrame* selected = nullptr;
    for (const auto& pose : samples) if (pose.frame <= mAttackPlayer.frame()) selected = &pose;
    if (!selected || !applyPoseFrame(selected->frame)) return result;
    result.valid = true;
    if (ended) {
        // KEY3 owns the one-shot release. Never claim the retail Move
        // transition if ownership was already lost or the release was refused.
        mClockMode = 0;
        result.next = mClockReleased ? P2DemonAttackNext::Move : P2DemonAttackNext::Fail;
    }
    return result;
}

P2DemonAttackDecision P2DemonHost::tickTimedAttack(Navi* target, float delta, bool floorContact)
{
    P2DemonAttackDecision result;
    if (!mAttackActive || !std::isfinite(delta) || delta <= 0 || delta > 1) return result;
    std::vector<p2retail::Event> events;
    if (mAttackPlayer.advance(delta, [&](p2retail::Event event){ events.push_back(event); }) != p2retail::Update::Ok) return result;
    const float frame = mAttackPlayer.frame();
    const P2DemonMouthFrame* selected = nullptr;
    for (const auto& pose : mPoseBank.samples()) if (pose.frame <= frame) selected = &pose;
    if (!selected || !applyPoseFrame(selected->frame)) return result;
    if (mOccupied && (!target || !pc_demon_owned_by(target, this))) mOccupied = 0;
    updateAttack(target, frame, floorContact);
    result.valid = true;
    if (!target) result.next = P2DemonAttackNext::Move;
    for (const auto& event : events) {
        P2DemonAttackEvent mapped = P2DemonAttackEvent::None;
        if (event.type == 2) mapped = P2DemonAttackEvent::Dash;
        else if (event.type == 3) mapped = P2DemonAttackEvent::Interruptible;
        else if (event.type == 4) mapped = P2DemonAttackEvent::CaptureCheck;
        else if (event.type == 1000) mapped = P2DemonAttackEvent::End;
        const auto decision = P2DemonAttackWindow::eventDecision(target != nullptr, true, mapped, mOccupied);
        result.dash |= decision.dash;
        result.clearNoInterrupt |= decision.clearNoInterrupt;
        if (decision.next != P2DemonAttackNext::None) result.next = decision.next;
    }
    if (result.next != P2DemonAttackNext::None) { mAttackActive = false; mAttackPlayer.cancel(); }
    return result;
}
