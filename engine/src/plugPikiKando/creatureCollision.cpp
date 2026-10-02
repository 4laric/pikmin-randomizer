#include "Collision.h"
#include "DebugLog.h"
#include "Piki.h"
#include "PikiState.h"
#if defined(PIKI_PC_PORT)
#include "Navi.h"
#include "pc_purple_collision_trace.h"
#include "timing/pc_render_phase.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
namespace {
PcPurpleCollisionTraceWindow purpleCollisionTrace;
PcPurpleCollisionClosure purpleCollisionClosure;
PcPurpleQueuedForce purpleForce(const Vector3f& v) { return {v.x,v.y,v.z}; }
bool purpleAcquisitionMode() {
    return pcPurpleCollisionAcquisitionMode(std::getenv("P2_PURPLE_COMBAT_MODE"));
}
bool purpleCollisionTraceEnabled() {
    static const bool enabled = [] {
        const char* flag = std::getenv("P2_PURPLE_COLLISION_TRACE");
        const char* mode = std::getenv("P2_PURPLE_COMBAT_MODE");
        return flag && std::strcmp(flag, "1") == 0 && mode && std::strcmp(mode, "sdl_acquire") == 0;
    }();
    return enabled;
}
void purpleCollisionTraceEmit(Creature* actor, Creature* partner, const Vector3f& before,
                              const Vector3f& point, const char* side) {
    const Vector3f after = actor->mVolatileVelocity;
    const bool changed = before.x != after.x || before.y != after.y || before.z != after.z;
    Piki* piki = partner->mObjType == OBJTYPE_Piki ? static_cast<Piki*>(partner) : nullptr;
    purpleCollisionClosure.record(actor,pc_render_is_authoritative()?pc_render_tick_serial():0,
        piki && piki->isAlive() && piki->getState()==PIKISTATE_Normal
            && piki->mMode==PikiMode::FormationMode && piki->mNavi==actor,
        purpleForce(before),purpleForce(after));
    if (!pc_render_is_authoritative() || !purpleCollisionTrace.take(actor, changed)) return;
    std::printf("P2_PURPLE_COLLISION_PROVENANCE fixture_tick=%llu auth_tick=%llu sequence=%u "
                "side=%s captain=%p captain_index=%d partner=%p partner_type=%d "
                "partner_piki_state=%d partner_piki_mode=%d partner_navi=%p "
                "before=%.9g,%.9g,%.9g after=%.9g,%.9g,%.9g delta=%.9g,%.9g,%.9g "
                "point=%.9g,%.9g,%.9g dt=%.9g native_path=respondColl_separation read_only=1\n",
                static_cast<unsigned long long>(purpleCollisionTrace.tick()),
                static_cast<unsigned long long>(pc_render_tick_serial()), purpleCollisionTrace.sequence(),
                side, static_cast<void*>(actor), static_cast<Navi*>(actor)->getNaviIndex(),
                static_cast<void*>(partner), int(partner->mObjType), piki ? piki->getState() : -1,
                piki ? int(piki->mMode) : -1, piki ? static_cast<void*>(piki->mNavi) : nullptr,
                before.x, before.y, before.z, after.x, after.y, after.z,
                after.x-before.x, after.y-before.y, after.z-before.z,
                point.x, point.y, point.z, gsys->getFrameTime());
}
}
void pc_purple_collision_trace_context(const Creature* captain, bool active, std::uint64_t fixtureTick) {
    const bool enabled = purpleCollisionTraceEnabled();
    const bool valid = captain && captain->mObjType == OBJTYPE_Navi;
    const PcPurpleQueuedForce initial=valid?purpleForce(captain->mVolatileVelocity):PcPurpleQueuedForce{};
    // update() consumes and clears the previous queue before postUpdate()
    // separation writes. Permit that previous queue only when its exact value
    // and preceding fixture/auth ticks already have complete owned provenance.
    // The new closure still requires the FIRST actual write to start at zero;
    // any intervening force or failure to clear it invalidates this tick.
    purpleCollisionClosure.beginIdle(purpleAcquisitionMode() && active && valid,
        captain,fixtureTick,pc_render_tick_serial(),initial);
    purpleCollisionTrace.begin(enabled, active && valid, captain, fixtureTick);
    if (!enabled || !active || !valid || !purpleCollisionTrace.eligible(captain)) return;
    std::printf("P2_PURPLE_COLLISION_CONTEXT fixture_tick=%llu preceding_auth_tick=%llu "
                "captain=%p captain_index=%d before_idle_volatile=%.9g,%.9g,%.9g read_only=1\n",
                static_cast<unsigned long long>(fixtureTick), static_cast<unsigned long long>(pc_render_tick_serial()),
                static_cast<const void*>(captain), static_cast<const Navi*>(captain)->getNaviIndex(),
                captain->mVolatileVelocity.x, captain->mVolatileVelocity.y, captain->mVolatileVelocity.z);
}
bool pc_purple_collision_owned_queued_force(const Creature* captain,std::uint64_t fixtureTick) {
    return captain && captain->mObjType==OBJTYPE_Navi && purpleCollisionClosure.matches(captain,
        fixtureTick,pc_render_tick_serial(),purpleForce(captain->mVolatileVelocity));
}
#endif

/**
 * @todo: Documentation
 * @note UNUSED Size: 00009C
 */
DEFINE_ERROR(__LINE__) // Never used in the DLL

/**
 * @todo: Documentation
 * @note UNUSED Size: 0000F4
 */
DEFINE_PRINT("CreatureColl")

/**
 * @todo: Documentation
 */
void Creature::respondColl(Creature* other, f32, CollPart* selfCollider, CollPart* otherCollider, const Vector3f& point)
{
	if (!ignoreAtari(other) && !other->ignoreAtari(this)) {

		CollEvent selfEvent(this, selfCollider, otherCollider);
		CollEvent otherEvent(other, otherCollider, selfCollider);
		other->collisionCallback(selfEvent);
		collisionCallback(otherEvent);

		if (!needFlick(other) || !other->needFlick(this)) {
			return;
		}

		if (!other->isAtari() || !isAtari()) {
			return;
		}

		if (!isAlive() || !other->isAlive()) {
			return;
		}

		if (!other->isObjType(OBJTYPE_Plant) && !isObjType(OBJTYPE_Plant) && other->mObjType != OBJTYPE_Plant) {
			// If the Pikmin has been thrown at something and hits it, print the name of the hit object
			if (mObjType == OBJTYPE_Piki && ((Piki*)this)->getState() == PIKISTATE_Flying) {
				PRINT("vs %s : \n", ObjType::getName(other->mObjType));
			}

			// Calculate collision response vectors
			Vector3f collisionNormal = point;
			if (collisionNormal.DP(collisionNormal) == 0.0f) {
				f32 angle = 0.0f;
				collisionNormal.set(sinf(angle), 0.0f, cosf(angle));
			}

			// Calculate relative velocity
			Vector3f relativeVelocity = mVelocity;
			relativeVelocity          = relativeVelocity - other->mVelocity;
			f32 impactSpeed           = relativeVelocity.DP(collisionNormal);

			// Get inverse masses for collision response
			f32 selfInvMass  = getiMass();
			f32 otherInvMass = other->getiMass();

			// Prevent division by zero in mass calculations
			if (selfInvMass + otherInvMass < 0.0001f) {
				selfInvMass  = 1e-05;
				otherInvMass = 1e-05;
			}

			// Calculate impulse scalar
			f32 restitution   = 1.35f; // Coefficient of restitution
			f32 impulseScalar = -restitution * impactSpeed;
			impulseScalar     = impulseScalar / ((selfInvMass + otherInvMass) * collisionNormal.DP(collisionNormal));
			collisionNormal   = impulseScalar * collisionNormal;

			// Apply impulse to self
			Vector3f impulse = collisionNormal;
			impulse          = selfInvMass * impulse;
			mVelocity        = mVelocity + impulse;

			// Apply impulse to other
			f32 unused;
			impulse          = collisionNormal;
			impulse          = -otherInvMass * impulse;
			other->mVelocity = other->mVelocity + impulse;

			// Calculate separation vector
			Vector3f separationVector = -1.0f * point;
			f32 distance              = separationVector.normalise();
			if (distance > 0.0f) {
				// Calculate mass ratios for separation
				f32 sepRatioSelf, sepRatioOther;
				f32 totalMass = getiMass() + other->getiMass();

				if (totalMass > 0) {
					sepRatioSelf  = getiMass() / totalMass;
					sepRatioOther = 1.0f - sepRatioSelf;
				} else {
					sepRatioOther = 0.5f;
					sepRatioSelf  = 0.5f;
				}

				// Adjust ratios based on fixed status
				if (isFixed() && !other->isFixed()) {
					sepRatioSelf  = 0.0f;
					sepRatioOther = 1.0f;
				} else if (!isFixed() && other->isFixed()) {
					sepRatioSelf  = 1.0f;
					sepRatioOther = 0.0f;
				} else if (isFixed() && other->isFixed()) {
					sepRatioOther = 0.0f;
					sepRatioSelf  = 0.0f;
				}

				// Separation velocity scaling factors
				f32 verticalScale   = 0.0f;
				f32 horizontalScale = 0.5f;

				// Calculate time-scaled separation velocities
				f32 sepSpeedSelf  = distance * sepRatioSelf / gsys->getFrameTime();
				f32 sepSpeedOther = distance * sepRatioOther / gsys->getFrameTime();

#if defined(PIKI_PC_PORT)
                const bool traceSelf = purpleCollisionTrace.eligible(this) || purpleCollisionClosure.watches(this);
                const bool traceOther = purpleCollisionTrace.eligible(other) || purpleCollisionClosure.watches(other);
                Vector3f traceBeforeSelf, traceBeforeOther;
                if (traceSelf) traceBeforeSelf = mVolatileVelocity;
                if (traceOther) traceBeforeOther = other->mVolatileVelocity;
#endif

				if (mObjType != OBJTYPE_Navi) {
					mVolatileVelocity.x = sepSpeedSelf * separationVector.x * horizontalScale;
					mVolatileVelocity.z = sepSpeedSelf * separationVector.z * horizontalScale;
					mVolatileVelocity.y = sepSpeedSelf * separationVector.y * verticalScale;
				} else {
					mVolatileVelocity.x += sepSpeedSelf * separationVector.x * horizontalScale;
					mVolatileVelocity.z += sepSpeedSelf * separationVector.z * horizontalScale;
					mVolatileVelocity.y += sepSpeedSelf * separationVector.y * verticalScale;
				}

				if (other->mObjType != OBJTYPE_Navi) {
					other->mVolatileVelocity.x = -sepSpeedOther * separationVector.x * horizontalScale;
					other->mVolatileVelocity.z = -sepSpeedOther * separationVector.z * horizontalScale;
					other->mVolatileVelocity.y = -sepSpeedOther * separationVector.y * verticalScale;
				} else {
					other->mVolatileVelocity.x += -sepSpeedOther * separationVector.x * horizontalScale;
					other->mVolatileVelocity.z += -sepSpeedOther * separationVector.z * horizontalScale;
					other->mVolatileVelocity.y += -sepSpeedOther * separationVector.y * verticalScale;
				}

#if defined(PIKI_PC_PORT)
                if (traceSelf) purpleCollisionTraceEmit(this, other, traceBeforeSelf, point, "self");
                if (traceOther) purpleCollisionTraceEmit(other, this, traceBeforeOther, point, "other");
#endif

				if (!isFixed()) {
					mHasCollChangedVelocity = 1;
				}

				if (!other->isFixed()) {
					other->mHasCollChangedVelocity = 1;
				}

				return;
			}

			mHasCollChangedVelocity = 0;
		}
	}
}
