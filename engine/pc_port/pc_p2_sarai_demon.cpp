// Bumbling Snitchbug (Demon, P2 enemy ID 32) route of the Sarai host (#215).
//
// Demon::Obj is a Sarai::Obj subclass (pikmin2-research Demon.h/Demon.cpp):
// Sarai's eleven-state FSM runs unchanged (p2sarai::Fsm, transcribed from
// SaraiState.cpp) and only the target differs: naviMgr captains, gated by the
// 3 s mAttackTimer (armed at 12800 by Sarai::onInit, reset to 0 by
// FallMeck::cleanup), with catchTarget sending the captain into a mouth slot.
// Every state's exec body below cites the retail function it transcribes.
//
// Engine vehicle (labelled): the bound P1 anchor actor carries health, the
// Pikmin stickers (mStuckPikminCount), the collision the Pikmin hit and the
// engine corpse. Its P1 strategy is suppressed by the manager; its stored
// damage is drained here (frog/elecbug pattern) and it follows this host.
#include "pc_p2_campaign_actor.h"
#include "pc_p2_sarai_host.h"
#include "pc_p2_demon_bridge.h"
#include "pc_p2_sarai_manager.h"
#include "pc_p2_sfx.h"
#include "pc_p2_demon_anchor.h"
#include "Collision.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Piki.h"
#include "CPlate.h"
#include "Shape.h"
#include "Stickers.h"
#include "Graphics.h"
#include "Interactions.h"
#include "MapMgr.h"
#include "gameflow.h"
#include "sysNew.h"
#include "Generator.h"
#include "teki.h"
#include <cmath>
#include <map>
#include <cstdio>
#include <vector>

namespace {
// aiConstants gravity (P2 EnemyBase::doSimulationGround). Labelled value: the
// retail constant file is not staged; 1000 is the P1/P2 shared default.
constexpr float kGravity = 1000.0f;
// demon/enemyparm.txt s003 (CreatureProperty accel), GPVE01 rev 0.
constexpr float kAccel = 0.1f;

const char* stateName(p2sarai::State s)
{
    switch (s) {
    case p2sarai::State::Dead: return "dead";
    case p2sarai::State::Fall: return "fall";
    case p2sarai::State::Damage: return "damage";
    case p2sarai::State::TakeOff: return "takeoff";
    case p2sarai::State::Flick: return "flick";
    case p2sarai::State::Wait: return "wait";
    case p2sarai::State::Move: return "move";
    case p2sarai::State::Attack: return "attack";
    case p2sarai::State::Fail: return "fail";
    case p2sarai::State::CatchFly: return "catchfly";
    case p2sarai::State::FallMeck: return "fallmeck";
    }
    return "?";
}

// Sarai.h AnimID clip names, indexed by p2sarai::Motion.
const char* const kClip[12] = {
    nullptr, "wait1.bca", "move1.bca", "attack1.bca", "waitact2.bca", "waitact1.bca",
    "flick.bca", "type1.bca", "type2.bca", "type3.bca", "type4.bca", "dead.bca",
};

float mapMinY(float x, float z, float fallback)
{
    return mapMgr ? mapMgr->getMinY(x, z, true) : fallback;
}

int plateCount(Navi* n)
{
    if (!n || !n->mPlateMgr) return -1;
    int count = 0;
    Iterator it(n->mPlateMgr);
    CI_LOOP(it) { if (*it) ++count; }
    return count;
}
} // namespace

float P2SaraiHost::demonRand()
{
    // Deterministic per-host LCG standing in for randWeightFloat(1.0f).
    mRng = mRng * 1103515245u + 12345u;
    return float((mRng >> 8) & 0xFFFFu) / 65536.0f;
}

unsigned P2SaraiHost::demonGenerator() const
{
    return mBoundActor && mBoundActor->mGenerator ? pc_p2_campaign_token(mBoundActor) : 0u;
}

bool P2SaraiHost::enableDemon(const p2demon::Parms& parms, const p2retail::Table& motions, const char* prefix,
                              const Vector3f& home, unsigned seed)
{
    if (!mLoaded || !parms.retail || !prefix || !*prefix) return false;
    for (int m = 1; m < 12; ++m) {
        mDemonMotion[m] = p2retail::Motion();
        for (const auto& motion : motions.motions)
            if (motion.name == kClip[m]) mDemonMotion[m] = motion;
        if (mDemonMotion[m].name.empty()) return false;
        std::string stem(kClip[m]);
        stem = stem.substr(0, stem.size() - 4);
        mDemonBank[m] = std::string(prefix) + "-" + stem + "-poses.txt";
        if (!preloadPoseMeshes(mDemonBank[m].c_str())) return false;
    }
    mCarryMotion = p2retail::Motion();
    for (const auto& motion : motions.motions)
        if (motion.name == "type5.bca") mCarryMotion = motion;
    if (mCarryMotion.name.empty()) return false;
    mCarryBank = std::string(prefix) + "-type5-poses.txt";
    if (!preloadPoseMeshes(mCarryBank.c_str())) return false;

    mDemonParms = parms;
    mFsm = p2sarai::Fsm(parms.proper);
    mNatHome = home;
    mFacingRadians = mSRT.r.y;
    mRng = seed ? seed : 1u;
    mAttackTimer.reset(12800.0f);             // Sarai::onInit resetAttackableTimer(12800)
    mDemonTarget = mDemonHeld = nullptr;
    mVel = p2demon::Velocity();
    mTargetVel = p2demon::Velocity();
    mDemonKill = false;
    mDemonCaptures = mDemonDrops = 0;
    mDemonClock = 0.0f;
    mLastDropClock = -1.0f;
    mLastDemonState = -1;
    mPlayer.cancel();
    mNaturalMotionStarted = false;
    // Anchor latch fix (#215): body joint offset for the retail collision
    // spheres, measured from the loaded rest-pose mesh (pc_p2_demon_anchor.h).
    {
        p2demonanchor::Vec3 body = p2demonanchor::defaultBodyOffset();
        bool measured = false;
        if (mShape && mShape->mVertexList && mShape->mVertexCount > 0) {
            const Vector3f* verts = mShape->mVertexList;
            measured = p2demonanchor::bodyOffsetFromMesh(std::size_t(mShape->mVertexCount),
                [verts](std::size_t i) { return p2demonanchor::Vec3{verts[i].x, verts[i].y, verts[i].z}; }, body);
        }
        mDemonBodyOffset.set(body.x, body.y, body.z);
        std::printf("P2_DEMON_BODY_OFFSET source_id=32 measured=%d x=%.1f y=%.1f z=%.1f stick_bottom=%.1f\n",
                    int(measured), body.x, body.y, body.z, p2demonanchor::stickableBottom(body));
    }
    mDemonAirborne = true; // Move: EB_Untargetable
    // Sarai::onInit: mFsm->start(this, SARAI_Move) (Move init sets a patrol target).
    mFsm.forceState(p2sarai::State::Move, demonRand());
    demonSetRandTarget();
    mDemonEnabled = true;
    return true;
}

bool P2SaraiHost::startDemonMotion(p2sarai::Motion motion)
{
    const int m = int(motion);
    if (m <= 0 || m >= 12 || mDemonMotion[m].name.empty()) return false;
    if (!switchPoseMeshes(mDemonBank[m].c_str())) return false;
    if (!mPlayer.start(mDemonMotion[m])) return false;
    mNaturalMotionStarted = true;
    applyNaturalPose();
    return true;
}

// Sarai::setRandTarget().
void P2SaraiHost::demonSetRandTarget()
{
    const auto& g = mDemonParms.general;
    float radius;
    if (mDemonHeld) radius = g.homeRadius * demonRand();
    else radius = g.homeRadius + (g.territoryRadius - g.homeRadius) * demonRand();
    const float dirToSelf = std::atan2(mSRT.t.x - mNatHome.x, mSRT.t.z - mNatHome.z);
    const float angle = 0.5f * p2sarai::kPi + (dirToSelf + p2sarai::kPi * demonRand());
    mRandTarget.set(radius * std::sin(angle) + mNatHome.x, mNatHome.y, radius * std::cos(angle) + mNatHome.z);
}

// Sarai::setHeightVelocity(): writes mCurrentVelocity.y, returns altitude.
float P2SaraiHost::demonHeightVelocity(float mapY, int bodyStuck)
{
    mVel.y = p2sarai::heightVelocity(mDemonParms.proper, bodyStuck, mDemonHeld != nullptr, mapY, mSRT.t.y);
    return mSRT.t.y - mapY;
}

// EnemyBase::turnToTarget.
void P2SaraiHost::demonTurnTo(const Vector3f& target)
{
    const float ang = p2demon::wrapPi(std::atan2(target.x - mSRT.t.x, target.z - mSRT.t.z) - mFacingRadians);
    mFacingRadians = p2demon::wrapPi(mFacingRadians
        + p2demon::turnStep(ang, mDemonParms.general.turnSpeed, mDemonParms.general.maxTurnAngle));
    mSRT.r.y = mFacingRadians;
}

// EnemyFunc::walkToTarget: turn, then target velocity along the facing.
void P2SaraiHost::demonWalkTo(const Vector3f& target, float speed)
{
    demonTurnTo(target);
    mTargetVel.x = std::sin(mFacingRadians) * speed;
    mTargetVel.z = std::cos(mFacingRadians) * speed;
    mTargetVel.y = 0.0f;
}

// Demon::getAttackableTarget(): mAttackTimer += dt, then (> 3 s) the first
// live, not-mouth-stuck captain inside territory/view/sight.
Navi* P2SaraiHost::demonAcquire(float dt)
{
    if (!mAttackTimer.query(dt) || !naviMgr) return nullptr;
    const float hx = mSRT.t.x - mNatHome.x, hz = mSRT.t.z - mNatHome.z;
    Iterator it(naviMgr);
    CI_LOOP(it) {
        Navi* n = static_cast<Navi*>(*it);
        if (!n) continue;
        const Vector3f p = n->getPosition();
        const float dx = p.x - mSRT.t.x, dz = p.z - mSRT.t.z;
        const float ang = p2demon::wrapPi(std::atan2(dx, dz) - mFacingRadians);
        if (p2demon::captainTargetable(mDemonParms.general, hx * hx + hz * hz, n->isAlive(),
                                       n->isStickToMouth(), ang, dx * dx + dz * dz))
            return n;
    }
    return nullptr;
}

// Demon::catchTarget(): any live, free captain within a free mouth slot's
// radius (animated slot position, 3D distance) receives InteractSarai.
void P2SaraiHost::demonCatch()
{
    if (!naviMgr || mDemonHeld) return;
    Iterator it(naviMgr);
    CI_LOOP(it) {
        Navi* n = static_cast<Navi*>(*it);
        if (!n || !n->isAlive() || n->isStickToMouth()) continue;
        for (unsigned slot = 0; slot < 2; ++slot) {
            const Vector3f d = n->getPosition() - mMouths[slot]->mCentre;
            if (d.length() < mCatchMin) {
                mCatchMin = d.length();
                mCatchDy = d.y;
                mCatchDxz = std::sqrt(d.x * d.x + d.z * d.z);
            }
            if (!(d.length() < mMouths[slot]->mRadius)) continue;
            const int squadBefore = plateCount(n);
            if (!pc_demon_capture(n, this, mMouths[slot], mOwnerToken, slot)) break;
            mDemonHeld = n;
            ++mDemonCaptures;
            mLifecycle.capture(reinterpret_cast<std::uintptr_t>(n), mOwnerToken, slot);
            const AState<Navi>* st = n->getCurrState();
            std::printf("P2_DEMON_CAPTURE source_id=32 generator=%u captain=1 slot=%u held=%d stick_mouth=%d "
                        "navi_state=%d squad_before=%d squad_after=%d navi_health=%.1f attack_timer=%.2f t=%.2f\n",
                        demonGenerator(), slot, int(pc_demon_owned_by(n, this)), int(n->isStickToMouth()),
                        st ? const_cast<AState<Navi>*>(st)->getID() : -1, squadBefore, plateCount(n),
                        n->mHealth, mAttackTimer.value(), mDemonClock);
            std::fflush(stdout);
            return;
        }
    }
}

// Sarai::flickStickTarget(): mouth captives receive InteractFlick (no damage).
void P2SaraiHost::demonReleaseHeld(const char* why)
{
    if (!mDemonHeld) return;
    Navi* n = mDemonHeld;
    mDemonHeld = nullptr;
    const bool owned = pc_demon_owned_by(n, this);
    if (owned) pc_demon_release(n);
    mLifecycle.detach();
    std::printf("P2_DEMON_FLICK_CAPTAIN source_id=32 generator=%u reason=%s released=%d stick_mouth=%d "
                "navi_health=%.1f t=%.2f\n",
                demonGenerator(), why, int(owned), int(n->isStickToMouth()), n->mHealth, mDemonClock);
    std::fflush(stdout);
}

void P2SaraiHost::updateDemon()
{
    const float dt = gsys ? gsys->getFrameTime() : 0.0f;
    if (!std::isfinite(dt) || dt <= 0.0f || dt > 0.5f) return;
    if (!mBoundActor) return;
    mDemonClock += dt;
    const unsigned generator = demonGenerator();
    // Fade/staleness time must advance from the living Demon simulation too: without it a
    // clip-change crossfade never left weight 0 and the body froze on the previous clip's pose.
    advanceSmooth(dt);
    demonAnimDiagnostic(dt, stateName(mFsm.state()));

    // Held-captain bookkeeping: the captain can leave on its own (escape mash,
    // death, reset); the bridge is the authority.
    if (mDemonHeld && !pc_demon_owned_by(mDemonHeld, this)) {
        std::printf("P2_DEMON_CAPTAIN_LEFT source_id=32 generator=%u stick_mouth=%d t=%.2f\n", generator,
                    int(mDemonHeld->isStickToMouth()), mDemonClock);
        std::fflush(stdout);
        mDemonHeld = nullptr;
        mLifecycle.observeDetached();
    }

    // Advance the current retail clip (30 fps frames, capped to one frame per
    // update so no key event is skipped).
    float frames = dt * 30.0f;
    if (frames > 1.0f) frames = 1.0f;
    bool ended = false, key2 = false;
    p2sarai::KeyEvent key = p2sarai::KeyEvent::None;
    if (mNaturalMotionStarted) {
        std::vector<p2retail::Event> events;
        const auto r = mPlayer.advance(frames, [&](p2retail::Event e) { events.push_back(e); });
        if (r == p2retail::Update::Ok || r == p2retail::Update::Replaced) {
            for (const auto& e : events) {
                if (e.type == 1000) ended = true;
                else if (e.type == 2 && key == p2sarai::KeyEvent::None) { key = p2sarai::KeyEvent::Key2; key2 = true; }
                else if (e.type == 3 && key == p2sarai::KeyEvent::None) key = p2sarai::KeyEvent::Key3;
                else if (e.type == 4 && key == p2sarai::KeyEvent::None) key = p2sarai::KeyEvent::Key4;
            }
            applyNaturalPose();
        }
    }

    const p2sarai::State before = mFsm.state();
    // getAttackableTarget() is only called from Wait/Move exec.
    Navi* found = nullptr;
    if (before == p2sarai::State::Wait || before == p2sarai::State::Move) found = demonAcquire(dt);

    int bodyStuck = 0;
    {
        Stickers stuck(mBoundActor);
        bodyStuck = stuck.getNumStickers();
        if (bodyStuck < 0) bodyStuck = 0;
    }
    const int mouth = mDemonHeld ? 1 : 0;
    const float mapY = mapMinY(mSRT.t.x, mSRT.t.z, mSRT.t.y);

    p2sarai::In in;
    in.deltaTime = dt;
    in.health = mBoundActor->mHealth;
    // Demon::getStickPikminNum() == mStuckPikminCount (a captain in the mouth is
    // not a Pikmin); the FSM subtracts mouthCarried, so feed body + mouth.
    in.bodyStuckCount = bodyStuck + mouth;
    in.mouthCarried = mouth;
    in.purpleLatched = false;
    in.mapY = mapY;
    in.positionY = mSRT.t.y;
    in.targetPresent = found != nullptr;
    in.hasTargetCreature = mDemonTarget != nullptr;
    in.targetFrame = mPlayer.frame();
    {
        const float dx = mSRT.t.x - mRandTarget.x, dz = mSRT.t.z - mRandTarget.z;
        in.distToPatrolTargetXZ = std::sqrt(dx * dx + dz * dz);
    }
    in.keyEvent = key;
    in.motionFinished = ended;
    in.randomUnit = demonRand();
    const p2sarai::Out out = mFsm.tick(in);
    const p2sarai::State now = mFsm.state();
    // P1 Sarai bank approximation (output-only, #946): damage cry on a health
    // drop, state cries on entry, hover pulse while airborne.
    {
        const unsigned generator = demonGenerator();
        static std::map<unsigned, float> sLastHealth;
        const float hp = mBoundActor->mHealth;
        auto hit = sLastHealth.find(generator);
        if (hit != sLastHealth.end() && hp < hit->second && hp > 0.0f)
            pc_p2_sfx(32, generator, p2sfx::Event::Damage, mBoundActor);
        sLastHealth[generator] = hp;
        if (now != before) {
            switch (now) {
            case p2sarai::State::Attack: pc_p2_sfx(32, generator, p2sfx::Event::Attack, mBoundActor); break;
            case p2sarai::State::Flick: pc_p2_sfx(32, generator, p2sfx::Event::Flick, mBoundActor); break;
            case p2sarai::State::Damage: pc_p2_sfx(32, generator, p2sfx::Event::Damage, mBoundActor); break;
            case p2sarai::State::Dead:
                pc_p2_sfx_stop(32, p2sfx::Event::Hover, mBoundActor);
                pc_p2_sfx(32, generator, p2sfx::Event::Dead, mBoundActor);
                break;
            case p2sarai::State::Fall: pc_p2_sfx(32, generator, p2sfx::Event::Land, mBoundActor); break;
            default: break;
            }
        }
        if (mFsm.flags().untargetable && now != p2sarai::State::Dead)
            pc_p2_sfx(32, generator, p2sfx::Event::Hover, mBoundActor);
    }

    if (now != before) {
        // cleanup() of the state being left.
        if (before == p2sarai::State::Attack) {
            mDemonTarget = nullptr;
            // Diagnostic only: nearest captain-to-mouth approach in the window.
            std::printf("P2_DEMON_CATCH_WINDOW source_id=32 generator=%u caught=%d min_dist=%.1f dy=%.1f dxz=%.1f "
                        "radius=%.1f t=%.2f\n", generator, int(mDemonHeld != nullptr), mCatchMin, mCatchDy,
                        mCatchDxz, mMouths[0]->mRadius, mDemonClock);
        }
        if (before == p2sarai::State::FallMeck) {
            mAttackTimer.reset(0.0f);             // FallMeck::cleanup resetAttackableTimer(0)
            std::printf("P2_DEMON_GATE source_id=32 generator=%u reset=0 reason=fallmeck_cleanup t=%.2f\n",
                        generator, mDemonClock);
        }
        // init() of the state entered.
        switch (now) {
        case p2sarai::State::Wait: mTargetVel = p2demon::Velocity(); mDemonTarget = nullptr; break;
        case p2sarai::State::Move: demonSetRandTarget(); mDemonTarget = nullptr; break;
        case p2sarai::State::Attack:
            mDemonTarget = found;
            mTargetVel = p2demon::Velocity();
            mHuntStopped = false;
            mCatchMin = 1.0e9f; mCatchDy = 0.0f; mCatchDxz = 0.0f;
            std::printf("P2_DEMON_TARGET source_id=32 generator=%u captain=1 attack_timer=%.2f since_drop=%.2f t=%.2f\n",
                        generator, mAttackTimer.value(),
                        mLastDropClock >= 0.0f ? mDemonClock - mLastDropClock : -1.0f, mDemonClock);
            break;
        case p2sarai::State::CatchFly: demonSetRandTarget(); mDemonTarget = nullptr; break;
        case p2sarai::State::FallMeck: mDemonTarget = nullptr; mTargetVel = p2demon::Velocity(); break;
        case p2sarai::State::Fall:
        case p2sarai::State::Damage:
        case p2sarai::State::Dead: mTargetVel = p2demon::Velocity(); break;
        default: break;
        }
        std::printf("P2_DEMON_STATE source_id=32 generator=%u from=%s to=%s state_id=%d health=%.1f "
                    "body_stuck=%d held=%d alt=%.1f t=%.2f\n",
                    generator, stateName(before), stateName(now), int(now), mBoundActor->mHealth,
                    bodyStuck, mouth, mSRT.t.y - mapY, mDemonClock);
        std::fflush(stdout);
    }
    // Dead/Fall/Damage init call flickStickTarget(): the captive goes free.
    if (out.flickAttackers && mDemonHeld) demonReleaseHeld(stateName(now));
    if (out.motionChanged) startDemonMotion(out.motion);
    if (out.finishing) mPlayer.finishMotion();

    // --- exec physics, per SaraiState.cpp -----------------------------------
    bool flying = mFsm.flags().untargetable; // EB_Untargetable -> doSimulationFlying
    switch (now) {
    case p2sarai::State::Wait:
    case p2sarai::State::TakeOff:
        demonHeightVelocity(mapY, bodyStuck);
        break;
    case p2sarai::State::Move:
        demonHeightVelocity(mapY, bodyStuck);
        if (found || mFsm.generalTimer() > 10.0f || in.distToPatrolTargetXZ < 25.0f) mTargetVel = p2demon::Velocity();
        else demonWalkTo(mRandTarget, mDemonParms.proper.normalMovementSpeed);
        break;
    case p2sarai::State::CatchFly:
        demonHeightVelocity(mapY, bodyStuck);
        if (mFsm.generalTimer() > 10.0f || in.distToPatrolTargetXZ < 25.0f) mTargetVel = p2demon::Velocity();
        else demonWalkTo(mRandTarget, mDemonParms.proper.grabMovementSpeed);
        break;
    case p2sarai::State::Attack:
        if (mDemonTarget) {
            const float frame = mPlayer.frame();
            const Vector3f tp = mDemonTarget->getPosition();
            if (frame <= 10.0f) {
                demonHeightVelocity(mapY, bodyStuck);
                demonTurnTo(tp);
            } else if (frame <= 30.0f) {
                if (mSRT.t.y - mapY <= 1.0f) mHuntStopped = true; // mFloorTriangle -> mGeneralTimer = 30
                if (!mHuntStopped) {
                    mVel.y = p2demon::huntDescentVelocity(mDemonParms.proper, tp.y, mSRT.t.y, dt);
                    if (frame > 16.0f) demonCatch();
                    demonTurnTo(tp);
                }
            } else {
                demonHeightVelocity(mapY, bodyStuck);
                mTargetVel.x *= mDemonParms.proper.postHuntDecayRate;
                mTargetVel.z *= mDemonParms.proper.postHuntDecayRate;
            }
            if (key2) {
                // KEYEVENT_2 lunge: close to 25 units short of the target in 2/30 s units.
                float sx = tp.x - mSRT.t.x, sz = tp.z - mSRT.t.z;
                const float len = std::sqrt(sx * sx + (tp.y - mSRT.t.y) * (tp.y - mSRT.t.y) + sz * sz);
                if (len > 0.0f) {
                    sx -= (tp.x - mSRT.t.x) / len * 25.0f;
                    sz -= (tp.z - mSRT.t.z) / len * 25.0f;
                }
                const float k = 0.06666667f / dt;
                mVel.x = sx * k; mVel.y = 0.0f; mVel.z = sz * k;
                mTargetVel.x = mVel.x; mTargetVel.y = 0.0f; mTargetVel.z = mVel.z;
            }
        }
        break;
    case p2sarai::State::Fail:
        demonHeightVelocity(mapY, bodyStuck);
        mTargetVel.x *= mDemonParms.proper.postHuntDecayRate;
        mTargetVel.z *= mDemonParms.proper.postHuntDecayRate;
        break;
    case p2sarai::State::FallMeck:
        demonHeightVelocity(mapY, bodyStuck);
        break;
    case p2sarai::State::Flick:
        demonHeightVelocity(mapY, bodyStuck);
        if (key2) {
            // EnemyFunc::flickStickPikmin(shakeChance fp16, knockback fp17, damage fp18).
            const auto& g = mDemonParms.general;
            InteractFlick flick(mBoundActor, g.shakeKnockback, g.shakeDamage, FLICK_BACKWARDS_ANGLE);
            Stickers stuck(mBoundActor);
            Iterator iter(&stuck);
            int flicked = 0;
            CI_LOOP(iter) {
                Creature* c = *iter;
                if (!c) break;
                if (demonRand() < g.shakeChance) { c->stimulate(flick); iter.dec(); ++flicked; }
            }
            std::printf("P2_DEMON_FLICK source_id=32 generator=%u flicked=%d body_stuck=%d t=%.2f\n",
                        generator, flicked, bodyStuck, mDemonClock);
            std::fflush(stdout);
        }
        break;
    case p2sarai::State::Fall:
        // StateFall::exec spins the face while the clip runs.
        if (!out.finishing) {
            mFacingRadians = p2demon::wrapPi(mFacingRadians - 0.275f);
            mSRT.r.y = mFacingRadians;
        }
        flying = false;
        break;
    case p2sarai::State::Damage:
    case p2sarai::State::Dead:
        flying = false;
        break;
    }

    // FallMeck KEYEVENT_3: fallMeckGround() -> InteractFallMeck(fp24) with the
    // captive's velocity y = -fp41, through the registered navi drop state.
    if (out.drop && mDemonHeld) {
        Navi* n = mDemonHeld;
        const float hp = n->mHealth;
        const bool dropped = pc_demon_forced_release(n, mDemonParms.general.attackDamage,
                                                     mDemonParms.proper.fallMeckSpeed);
        mDemonHeld = nullptr;
        mLifecycle.detach();
        ++mDemonDrops;
        mLastDropClock = mDemonClock;
        std::printf("P2_DEMON_DROP source_id=32 generator=%u accepted=%d damage=%.1f speed=%.1f navi_health=%.1f "
                    "alt=%.1f t=%.2f\n",
                    generator, int(dropped), mDemonParms.general.attackDamage, mDemonParms.proper.fallMeckSpeed,
                    hp, mSRT.t.y - mapY, mDemonClock);
        std::fflush(stdout);
    }
    if (out.kill && !mDemonKill) {
        mDemonKill = true;
        std::printf("P2_DEMON_KILL source_id=32 generator=%u health=%.1f t=%.2f\n", generator,
                    mBoundActor->mHealth, mDemonClock);
        std::fflush(stdout);
    }

    // The anchor mirrors this as CF_IsFlying (demonAnchorFollow, #215 latch fix).
    mDemonAirborne = flying;

    // EnemyBase::collisionMapAndPlat simulation + integrate; floor clamp.
    mVel = p2demon::simulate(mVel, mTargetVel, flying, dt, kAccel, kGravity);
    mSRT.t.x += mVel.x * dt;
    mSRT.t.y += mVel.y * dt;
    mSRT.t.z += mVel.z * dt;
    const float floorY = mapMinY(mSRT.t.x, mSRT.t.z, mapY);
    if (mSRT.t.y < floorY) {
        mSRT.t.y = floorY;
        if (mVel.y < 0.0f) mVel.y = 0.0f;
    }
    updateMouths();

    if (++mDemonLogTicks % 30 == 0 || int(now) != mLastDemonState) {
        mLastDemonState = int(now);
        std::printf("P2_DEMON_TICK source_id=32 generator=%u state=%s state_id=%d health=%.1f max_health=%.1f "
                    "body_stuck=%d held=%d alt=%.1f attack_timer=%.2f pos=(%.1f,%.1f,%.1f) t=%.2f\n",
                    generator, stateName(now), int(now), mBoundActor->mHealth, mDemonParms.general.life,
                    bodyStuck, int(mDemonHeld != nullptr), mSRT.t.y - floorY,
                    mAttackTimer.value() > 1000.0f ? 1000.0f : mAttackTimer.value(),
                    mSRT.t.x, mSRT.t.y, mSRT.t.z, mDemonClock);
        std::fflush(stdout);
    }
}

void P2SaraiHost::demonAnchorInit()
{
    if (!mBoundActor || !mDemonEnabled) return;
    // EnemyBase::onInit: mHealth = mMaxHealth = fp00 (Demon life 1500).
    mBoundActor->mHealth = mDemonParms.general.life;
    mBoundActor->mMaxHealth = mDemonParms.general.life;
    mBoundActor->mStoredDamage = 0.0f;
    mBoundActor->mSRT.t = mSRT.t;
    demonAnchorBuildColl();
    demonAnchorFollow();
}

// Anchor latch fix (#215): replace the anchor's vehicle CollInfo (Dwarf
// Bulborb joint spheres sampled in its own draw) with the retail Demon tree
// (pc_p2_demon_anchor.h). Parts are update-inactive: demonAnchorFollow owns
// centre/radius every sim tick from host state (BigTreasure #246 pattern), so
// the collision is deterministic and never depends on the anchor being drawn.
// Anchor latch fix (#215): four-character part ids/codes, '_' padded.
static u32 demonFourcc(const char* id)
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
extern Matrix4f invCamMat; // collInfo.cpp: camera inverse used by CollPart::getMatrix

void P2SaraiHost::demonAnchorBuildColl()
{
    if (!mBoundActor || mAnchorOwnColl || !mBoundActor->mCollInfo) return;
    ObjCollInfo* nodes[p2demonanchor::kSphereCount] = {};
    for (int i = 0; i < p2demonanchor::kSphereCount; ++i) {
        const p2demonanchor::CollSphere& s = p2demonanchor::spheres()[i];
        auto* node = new ObjCollInfo();
        node->mId.setID(demonFourcc(s.id));
        node->mCode.setID(demonFourcc(s.code));
        node->mRadius = s.radius;
        node->mCentrePosition.set(s.offset.x, s.offset.y, s.offset.z);
        node->mJointIndex = -1;
        nodes[i] = node;
    }
    for (int i = 0; i < p2demonanchor::kSphereCount; ++i) {
        const int parent = p2demonanchor::spheres()[i].parent;
        if (parent >= 0) nodes[parent]->add(nodes[i]);
    }
    mAnchorOwnColl = new CollInfo(32); // >= any vehicle tree
    mAnchorOwnColl->initInfoTree(nodes[0]);
    for (int i = 0; i < p2demonanchor::kSphereCount; ++i) {
        CollPart* part = mAnchorOwnColl->getSphere(demonFourcc(p2demonanchor::spheres()[i].id));
        if (part) {
            part->mIsUpdateActive = false;
            part->mJointMatrix = Matrix4f::ident;
        }
        mAnchorParts[i] = part;
    }
    mAnchorVehicleColl = mBoundActor->mCollInfo;
    mBoundActor->mCollInfo = mAnchorOwnColl;
    std::printf("P2_DEMON_COLL_BIND source_id=32 generator=%u parts=%d vehicle_replaced=1 body=(%.1f,%.1f,%.1f)\n",
                demonGenerator(), p2demonanchor::kSphereCount, mDemonBodyOffset.x, mDemonBodyOffset.y,
                mDemonBodyOffset.z);
    std::fflush(stdout);
}

void P2SaraiHost::demonAnchorDrain()
{
    // The P1 TAI damage reaction lives in the suppressed strategy; apply the
    // Pikmin damage queued by the engine receivers (frog/elecbug pattern).
    if (mBoundActor && mBoundActor->mStoredDamage > 0.0f) mBoundActor->makeDamaged();
}

void P2SaraiHost::demonAnchorFollow()
{
    if (!mBoundActor) return;
    // The anchor is the collision the Pikmin are thrown onto and stick to; it
    // rides the Demon body at its live (flight) position.
    mBoundActor->mSRT.t = mSRT.t;
    mBoundActor->mSRT.r.y = mFacingRadians;
    mBoundActor->mFaceDirection = mFacingRadians;
    mBoundActor->mVelocity.set(0.0f, 0.0f, 0.0f);
    mBoundActor->mTargetVelocity.set(0.0f, 0.0f, 0.0f);
    // #215 latch fix: EB_Untargetable while hovering -> CF_IsFlying on the
    // anchor (ground Pikmin stop chasing a body they cannot reach; thrown and
    // stuck Pikmin are unaffected). Fall/Damage/Dead clear it so the landed
    // Demon is attackable by the whole squad (Bombsarai precedent).
    if (mDemonAirborne) {
        if (!mBoundActor->isFlying()) mBoundActor->startFlying();
    } else if (mBoundActor->isFlying()) {
        mBoundActor->finishFlying();
    }
    // Retail Demon collision spheres on the drawn body (pc_p2_demon_anchor.h).
    // CollPart::getMatrix() = invCamMat * mJointMatrix (+ centre): give every
    // part R(invCamMat)^T * yaw so stuck Pikmin follow the body yaw whether
    // or not the anchor was drawn this frame (BigTreasure #246 pattern).
    if (mAnchorOwnColl) {
        Matrix4f yaw, camRot, camYaw;
        yaw.makeSRT(Vector3f(1.0f, 1.0f, 1.0f), Vector3f(0.0f, mFacingRadians, 0.0f), Vector3f(0.0f, 0.0f, 0.0f));
        camRot.makeIdentity();
        for (int r = 0; r < 3; ++r)
            for (int c = 0; c < 3; ++c) camRot.mMtx[r][c] = invCamMat.mMtx[c][r];
        camRot.multiplyTo(yaw, camYaw);
        const p2demonanchor::Vec3 root{mSRT.t.x, mSRT.t.y, mSRT.t.z};
        const p2demonanchor::Vec3 body{mDemonBodyOffset.x, mDemonBodyOffset.y, mDemonBodyOffset.z};
        for (int i = 0; i < p2demonanchor::kSphereCount; ++i) {
            CollPart* part = mAnchorParts[i];
            if (!part) continue;
            const p2demonanchor::Vec3 c = p2demonanchor::sphereCentre(i, root, mFacingRadians, body);
            part->mCentre.set(c.x, c.y, c.z);
            part->mRadius = p2demonanchor::spheres()[i].radius * mSRT.s.y;
            part->mJointMatrix = camYaw;
        }
        if (!mAnchorCollLogged) {
            mAnchorCollLogged = true;
            const float floorY = mapMinY(mSRT.t.x, mSRT.t.z, mSRT.t.y);
            std::printf("P2_DEMON_COLL_FOLLOW source_id=32 generator=%u flying=%d alt=%.1f stick_bottom_alt=%.1f\n",
                        demonGenerator(), int(mBoundActor->isFlying()), mSRT.t.y - floorY,
                        mSRT.t.y + p2demonanchor::stickableBottom(body) - floorY);
            std::fflush(stdout);
        }
    }
}

void P2SaraiHost::demonAnchorFinalize()
{
    if (!mBoundActor) return;
    const unsigned generator = demonGenerator();
    demonReleaseHeld("dead");
    // #215 latch fix: the corpse is grounded and wears the vehicle CollInfo
    // again (the own tree is never freed: stuck Pikmin may still hold its
    // CollPart pointers, and a pooled actor re-inits whatever it holds).
    if (mBoundActor->isFlying()) mBoundActor->finishFlying();
    if (mAnchorVehicleColl) {
        mBoundActor->mCollInfo = mAnchorVehicleColl;
        mAnchorVehicleColl = nullptr;
        // The vehicle parts were last sampled before the swap (spawn pose):
        // dieSoon births the corpse pellet at the 'carc' sphere (or the
        // bounding sphere via getCentre), so seat both on the dead body now.
        const p2demonanchor::Vec3 body{mDemonBodyOffset.x, mDemonBodyOffset.y, mDemonBodyOffset.z};
        const p2demonanchor::Vec3 c = p2demonanchor::sphereCentre(
            0, p2demonanchor::Vec3{mSRT.t.x, mSRT.t.y, mSRT.t.z}, mFacingRadians, body);
        if (CollPart* carcass = mBoundActor->mCollInfo->getSphere('carc')) carcass->mCentre.set(c.x, c.y, c.z);
        if (mBoundActor->mCollInfo->hasInfo()) {
            if (CollPart* bound = mBoundActor->mCollInfo->getBoundingSphere()) bound->mCentre.set(c.x, c.y, c.z);
            if (CollPart* cent = mBoundActor->mCollInfo->getSphere('cent')) cent->mCentre.set(c.x, c.y, c.z);
        }
    }
    // StateDead::exec kill() -> engine corpse (dieSoon runs inside the
    // suppressed doAI, so finalise it here: frog/elecbug pcEscapeNow pattern).
    mBoundActor->mHealth = 0.0f;
    mBoundActor->pcEscapeNow();
    std::printf("P2_DEMON_CARCASS_BECOME source_id=32 generator=%u alive=%d pos=(%.1f,%.1f,%.1f)\n", generator,
                int(mBoundActor->isAlive()), mBoundActor->mSRT.t.x, mBoundActor->mSRT.t.y, mBoundActor->mSRT.t.z);
    std::fflush(stdout);
}

void P2SaraiHost::demonDrawCarcass(Graphics& gfx, const Matrix4f& modelView)
{
    // The carried corpse is the engine Pellet; its viewDraw hands us the
    // pellet's own model-view matrix, so the carcass follows the carriers.
    if (!mLoaded || !gfx.mCamera || mCarryBank.empty()) return;
    if (!switchPoseMeshes(mCarryBank.c_str())) return;
    // startCarcassMotion(): type5 loops 10..29.
    const float dt = gsys ? gsys->getFrameTime() : 0.0f;
    if (std::isfinite(dt) && dt > 0.0f && dt < 0.5f) mCarcassFrame += dt * 30.0f;
    if (mCarcassFrame >= 29.0f) mCarcassFrame = 10.0f;
    const auto& samples = mPoseBank.samples();
    const P2SaraiMouthFrame* selected = samples.empty() ? nullptr : &samples.front();
    for (const auto& pose : samples)
        if (float(pose.frame) <= mCarcassFrame) selected = &pose;
    if (selected) applyPoseFrame(selected->frame);
    // Smoothness: lerp between the bracketing type5 samples (the same private
    // geometry the living body uses) instead of drawing the nearest pose.
    advanceSmooth(dt);
    presentSmooth(mCarcassFrame);
    if (!mShape) return;
    gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx, gfx.mCamera->mFov,
        gfx.mCamera->mAspectRatio, gfx.mCamera->mNear, gfx.mCamera->mFar, 1.0f);
    gfx.useMaterial(nullptr);
    gfx.setDepth(true);
    Matrix4f view = modelView;
    mShape->updateAnim(gfx, view, nullptr, nullptr);
    mShape->drawshape(gfx, *gfx.mCamera, nullptr);
    if (!mCarcassLogged) {
        mCarcassLogged = true;
        std::printf("P2_DEMON_DRAW corpse=1 source_id=32 generator=%u pose=type5 frame=%d interpolation=%d\n",
                    demonGenerator(), selected ? selected->frame : -1, int(smoothActive()));
        std::printf("P2_DEMON_INTERPOLATION_READY corpse=1 interpolation=%d poses=%zu gameplay_clock=P2_source\n",
                    int(smoothActive()), mPoseBank.samples().size());
        std::fflush(stdout);
    }
}

// doAI seam: a Demon-profile anchor runs no P1 strategy (no Dwarf Bulborb bite,
// walk or death reaction); the host owns behaviour, the drain owns damage.
bool pc_p2_sarai_suppress_ai(const BTeki* actor)
{
    return pc_p2_sarai_manager_demon_host(actor) != nullptr;
}

// Parameter seam: the anchor reports the Demon's retail life (fp00) as its
// max life so the engine life gauge and health fraction use 1500, not the
// Dwarf Bulborb vehicle's value.
float pc_p2_sarai_param_f(const BTeki* actor, int idx, float fallback)
{
    if (idx != TPF_Life) return fallback;
    P2SaraiHost* host = pc_p2_sarai_manager_demon_host(actor);
    return host ? host->demonLife() : fallback;
}

// Creature-collision seam: P2 EnemyBase::collisionMapAndPlat disables
// EB_CollisionActive while the enemy is untargetable (flying), so a flying
// Demon never shoves the captain it is hunting. Pikmin keep colliding with the
// anchor (that is how thrown Pikmin latch onto the body).
bool pc_p2_sarai_ignore_atari(const BTeki* actor, Creature* other)
{
    P2SaraiHost* host = pc_p2_sarai_manager_demon_host(actor);
    return host && other && other->mObjType == OBJTYPE_Navi && host->demonFlying();
}
