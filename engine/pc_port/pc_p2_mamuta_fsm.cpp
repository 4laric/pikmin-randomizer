// Native source FSM for Miulin (Mamuta, EnemyID 54) on the P1 Miurin placement
// vehicle. own44 (#871): it replaces the host P1-AI proxy for actors already
// registered by pc_p2_mamuta. In bridge-mode campaign sessions the audited
// defaults drive the FSM without requiring `p2-mamuta-fsm.txt` (an explicit
// file still overrides); outside bridge (room preview) the file stays required.
// Source revision 632af93787b9c95b63f0c13be32b161375ce3a96
// (include/Game/Entities/Miulin.h,
// src/plugProjectMorimuraU/miulin.cpp, miulinState.cpp).
//
// Source states covered: Wait(0), Walk(1), AttackStart(2), Attacking(3),
// AttackEnd(4), Turn(5), Flick(6), Dead(7). Null(-1) is the unset sentinel.
//
// Recorded port adaptations / partials:
//   * The P1 host applies accumulated Pikmin damage in a TAI damage reaction
//     inside doAI; because the FSM suppresses doAI it calls
//     actor->makeDamaged() itself so real Pikmin hits still reach mHealth (no
//     damage is injected). Mirrors pc_p2_kochappy_fsm.
//   * EnemyFunc::isStartFlick (a Pikmin actually stuck to the body) is
//     approximated by a contact-radius test; attack posture takes precedence.
//   * Attacking KEYEVENT_2 (miulinState.cpp:264-330) plants Pikmin via the P1
//     host bury receiver (flower-stage + PIKISTATE_Bury, the in-place P1
//     contract) instead of the P2 itemized sprout birth
//     (interactPiki.cpp:377-442 births an ItemPikihead sprout and kills the
//     original); the 99-planted cap (GameStat::mePikis) and the +-20 vertical
//     band are honored, terrain/bald/manager rejections are not modelled. Navi
//     takes the source 5.0 damage (no captain burial). The same tick flicks
//     nearby/stuck Pikmin and captains with the retail shake (1.0/40/40).
//   * StateWalk's source turn-timer/return-timer machinery (mTurnTimer 30f,
//     mReturnTime ip01) is approximated by an elapsed-time return timer and a
//     direct territory leash; walkFunc dash (fp04 x2 inside mDashableAngle
//     fp07=30) runs at flat move speed.
//   * Birth's five ShijimiChou side-spawns at +80 (miulin.cpp:27-39) have no
//     host equivalent and are not reproduced.
//   * State durations are port adaptations at the engine's fixed 30 fps (the
//     decomp drives transitions off animation KEYEVENT_END, not seconds).
// Movement uses the source fp06 speed; turn rate 2.5 rad/s is a recorded
// adaptation because the host drive API takes a rate, not the source per-frame
// turn speed fp08. Every hook is a no-op for unregistered actors and, outside
// bridge mode, for the default-OFF path (no config file).
#include "pc_p2_mamuta_fsm.h"
#include "pc_p2_mamuta_fsm_policy.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_mamuta.h"
#include "pc_p2_mamuta_navi_hit.h"
#include "pc_bbft.h"
#include "teki.h"
#include "Interactions.h"
#include "GameStat.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "pc_p2_navi_select.h"
#include "Generator.h"
#include "StateMachine.h"
#include "system.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <vector>

namespace {
using p2mamutafsm::State;

// Source animation-driven transitions approximated at fixed 30 fps.
constexpr float ATTACK_START_DURATION = 12.0f / 30.0f;
constexpr float ATTACKING_DURATION    = 45.0f / 30.0f;
constexpr float ATTACK_END_DURATION   = 20.0f / 30.0f;
constexpr float TURN_DURATION         = 25.0f / 30.0f;
constexpr float FLICK_DURATION        = 30.0f / 30.0f;
constexpr float DEAD_DURATION         = 90.0f / 30.0f;
constexpr float BURY_EVENT_TIME       = 15.0f / 30.0f; // KEYEVENT_2 bury + flick
constexpr float FLICK_EVENT_TIME      = 12.0f / 30.0f;
constexpr float NOTICE_DELAY          = 0.5f;  // port adaptation
constexpr float TURN_RATE             = 2.5f;  // port adaptation (host drive rate)
constexpr float VERTICAL_BAND         = 20.0f; // miulinState.cpp:273-274
constexpr int BURIED_CAP              = 99;    // interactPiki.cpp:382-384 (US)

struct FsmActor {
	State state       = p2mamutafsm::STATE_WAIT;
	State returnState = p2mamutafsm::STATE_WAIT;
	float stateTime   = 0.0f;
	float heading     = 0.0f;
	Vector3f home;
	Vector3f goal;
	bool goalValid    = false;
	float returnTimer = 0.0f;
	bool buryFired    = false;
	bool flickFired   = false;
	bool deadLogged   = false;
	bool died         = false;
	bool healthAsserted = false;
	float logTimer    = 0.0f;
};

std::map<PelletView*, FsmActor> actors;
p2mamutafsm::Params params;
bool ready = false;

float wrapPi(float angle)
{
	while (angle > PI) angle -= TAU;
	while (angle < -PI) angle += TAU;
	return angle;
}

float distXZ(const Vector3f& a, const Vector3f& b)
{
	const float dx = a.x - b.x, dz = a.z - b.z;
	return std::sqrt(dx * dx + dz * dz);
}

Creature* nearestCreature(const Vector3f& pos, float radius)
{
	Creature* best = nullptr;
	float bestSq   = radius * radius;
	if (naviMgr) {
		for (Navi* navi : pc_p2_navis()) {
			if (!navi->isAlive()) continue;
			const Vector3f p = navi->getPosition();
			const float dx = p.x - pos.x, dz = p.z - pos.z;
			const float d  = dx * dx + dz * dz;
			if (d < bestSq) { bestSq = d; best = navi; }
		}
	}
	if (pikiMgr) {
		Iterator it(pikiMgr);
		CI_LOOP(it) {
			Piki* piki = static_cast<Piki*>(*it);
			if (!piki || !piki->isAlive()) continue;
			const Vector3f q = piki->getPosition();
			const float dx = q.x - pos.x, dz = q.z - pos.z;
			const float d  = dx * dx + dz * dz;
			if (d < bestSq) { bestSq = d; best = piki; }
		}
	}
	return best;
}

Piki* nearestPiki(const Vector3f& pos, float radius)
{
	Piki* best   = nullptr;
	float bestSq = radius * radius;
	if (pikiMgr) {
		Iterator it(pikiMgr);
		CI_LOOP(it) {
			Piki* piki = static_cast<Piki*>(*it);
			if (!piki || !piki->isAlive()) continue;
			const Vector3f q = piki->getPosition();
			const float dx = q.x - pos.x, dz = q.z - pos.z;
			const float d  = dx * dx + dz * dz;
			if (d < bestSq) { bestSq = d; best = piki; }
		}
	}
	return best;
}

void stop(BTeki* actor)
{
	actor->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
	actor->mVelocity.x = 0.0f;
	actor->mVelocity.z = 0.0f;
}

bool turnTo(BTeki* actor, FsmActor& state, const Vector3f& target, float dt, float tolerance)
{
	const Vector3f pos  = actor->getPosition();
	const float desired = std::atan2(target.x - pos.x, target.z - pos.z);
	const float diff    = wrapPi(desired - state.heading);
	const float maxTurn = TURN_RATE * dt;
	float step          = diff;
	if (step > maxTurn) step = maxTurn;
	if (step < -maxTurn) step = -maxTurn;
	state.heading = wrapPi(state.heading + step);
	actor->setDirection(state.heading);
	return std::fabs(wrapPi(desired - state.heading)) <= tolerance;
}

void walkTo(BTeki* actor, FsmActor& state, const Vector3f& target, float dt)
{
	const Vector3f pos  = actor->getPosition();
	const float desired = std::atan2(target.x - pos.x, target.z - pos.z);
	const float maxTurn = TURN_RATE * dt;
	float diff          = wrapPi(desired - state.heading);
	if (diff > maxTurn) diff = maxTurn;
	if (diff < -maxTurn) diff = -maxTurn;
	state.heading = wrapPi(state.heading + diff);
	actor->setDirection(state.heading);
	const Vector3f drive(std::sin(state.heading) * params.moveSpeed, 0.0f,
	                     std::cos(state.heading) * params.moveSpeed);
	actor->inputDrive(drive);
	actor->mVelocity.set(drive);
}

float attackAngleRadians()
{
	return params.attackAngle * PI / 180.0f;
}

// Source Obj::isAttackStart (miulin.cpp:170-190): the target ring between
// mMinAttackRange and mAttackRadius inside mContinuousPressAngle. The host has
// no press-angle latch, so the gate is range + facing angle.
bool attackReady(const Vector3f& pos, float heading, const Creature* target)
{
	const Vector3f targetPos = target->getPosition();
	const float dist = distXZ(targetPos, pos);
	if (dist > params.attackRange || dist < params.minAttackRange * 0.25f) return false;
	const float angle = std::fabs(wrapPi(std::atan2(targetPos.x - pos.x, targetPos.z - pos.z) - heading));
	return angle <= attackAngleRadians();
}

void doFlick(BTeki* actor, unsigned generator)
{
	const Vector3f pos = actor->getPosition();
	int hit = 0;
	if (pikiMgr) {
		Iterator it(pikiMgr);
		CI_LOOP(it) {
			Piki* piki = static_cast<Piki*>(*it);
			if (piki && piki->isAlive() && distXZ(piki->getPosition(), pos) < params.flickRange) {
				if (piki->stimulate(InteractFlick(actor, params.flickKnockback, params.flickDamage, actor->getDirection()))) ++hit;
			}
		}
	}
	for (Navi* navi : pc_p2_navis()) {
		if (navi->isAlive() && distXZ(navi->getPosition(), pos) < params.flickRange) {
			if (navi->stimulate(InteractFlick(actor, params.flickKnockback, params.flickDamage, actor->getDirection()))) ++hit;
		}
	}
	std::printf("P2_MAMUTA_FSM_FLICK generator=%u hit=%d\n", generator, hit);
	std::fflush(stdout);
}

// Source StateAttacking KEYEVENT_2 (miulinState.cpp:264-330): bury Pikmin in
// the strike disc, damage (not bury) the captain, and flick the neighborhood
// with the retail shake. Vertical window +-20 around the actor
// (miulinState.cpp:273-274). The strike centre is offset forward by
// minAttackRange along the facing (miulinState.cpp:269-271); Pikmin already
// stuck to this enemy are skipped (miulinState.cpp:282).
void doBury(BTeki* actor, unsigned generator)
{
	const Vector3f actorPos = actor->getPosition();
	const float face        = actor->getDirection();
	const Vector3f pos(actorPos.x + params.minAttackRange * std::sin(face), actorPos.y,
	                   actorPos.z + params.minAttackRange * std::cos(face));
	int planted = 0, rejected = 0, naviHit = 0;
	if (pikiMgr) {
		Iterator it(pikiMgr);
		CI_LOOP(it) {
			Piki* piki = static_cast<Piki*>(*it);
			if (!piki || !piki->isAlive()) continue;
			if (piki->isStickToMouth() || piki->isStickTo()) continue;
			const Vector3f q = piki->getPosition();
			const float dx = q.x - pos.x, dz = q.z - pos.z;
			if (dx * dx + dz * dz > params.attackRange * params.attackRange) continue;
			const float dy = q.y - pos.y;
			if (dy > VERTICAL_BAND || dy < -VERTICAL_BAND) continue;
			const int st = piki->getCurrState() ? piki->getCurrState()->getID() : PIKISTATE_Normal;
			if (st == PIKISTATE_Pressed || st == PIKISTATE_Dying || st == PIKISTATE_Dead) { ++rejected; continue; }
			if ((int)GameStat::mePikis >= BURIED_CAP) { ++rejected; continue; }
			if (piki->mHappa < Flower) piki->mHappa = Flower;
			piki->mFSM->transit(piki, PIKISTATE_Bury);
			++planted;
		}
	}
	if (naviMgr) {
		for (Navi* navi : pc_p2_navis()) {
			if (!navi->isAlive()) continue;
			const Vector3f np = navi->getPosition();
			const float dx = np.x - pos.x, dz = np.z - pos.z;
			if (dx * dx + dz * dz <= params.attackRange * params.attackRange) {
				const float dy = np.y - pos.y;
				if (dy <= VERTICAL_BAND && dy >= -VERTICAL_BAND && params.naviDamage > 0.0f) {
					if (pc_p2_mamuta_hit_navi(actor, navi, params.naviDamage)) ++naviHit;
				}
			}
		}
	}
	std::printf("P2_MAMUTA_FSM_BURY generator=%u planted=%d rejected=%d navi=%d\n", generator, planted, rejected, naviHit);
	std::fflush(stdout);
	doFlick(actor, generator);
}

int motionFor(State state)
{
	switch (state) {
	case p2mamutafsm::STATE_WALK: return TekiMotion::Move1;
	case p2mamutafsm::STATE_ATTACK_START: return TekiMotion::Type1;
	case p2mamutafsm::STATE_ATTACKING: return TekiMotion::Attack;
	case p2mamutafsm::STATE_ATTACK_END: return TekiMotion::Type1;
	case p2mamutafsm::STATE_TURN: return TekiMotion::WaitAct1;
	case p2mamutafsm::STATE_FLICK: return TekiMotion::Flick;
	case p2mamutafsm::STATE_DEAD: return TekiMotion::Dead;
	default: return TekiMotion::Wait1;
	}
}

void enter(BTeki* actor, FsmActor& state, State next)
{
	state.state     = next;
	state.stateTime = 0.0f;
	state.buryFired  = false;
	state.flickFired = false;
	if (next == p2mamutafsm::STATE_WALK) state.returnTimer = 0.0f;
	actor->startMotion(motionFor(next));
	const unsigned generator = pc_p2_campaign_token(actor);
	std::printf("P2_MAMUTA_FSM_STATE generator=%u state=%s\n", generator,
	            p2mamutafsm::stateName(next));
	std::fflush(stdout);
}
} // namespace

void pc_p2_mamuta_fsm_reset()
{
	actors.clear();
	ready = false;
}

void pc_p2_mamuta_fsm_forget(BTeki* actor)
{
	if (actors.erase(static_cast<PelletView*>(actor)) != 0) {
		std::printf("P2_MAMUTA_FSM_FORGET registered=1\n");
		std::fflush(stdout);
	}
}

bool pc_p2_mamuta_fsm_enabled()
{
	return ready;
}

void pc_p2_mamuta_fsm_setup()
{
	pc_p2_mamuta_fsm_reset();
	if (!tekiMgr) return;
	// own44 (#871): bridge-mode campaign OWN. The product seed stages the
	// Mamuta pose banks via IDENTITY_FAMILY but never stages an FSM config,
	// so in bridge mode the decomp-informed defaults drive the FSM without
	// requiring the file (an explicit file still overrides). Outside bridge
	// (room preview) the file stays required so the default proxy preview
	// path is unchanged.
	const bool bridge = pc_randomizer_p2_bridge() && !pc_pikipelago_room_preview();
	std::ifstream config("p2-mamuta-fsm.txt");
	if (config) {
		if (!p2mamutafsm::parseConfig(config, params)) {
			std::fprintf(stderr, "Invalid p2-mamuta-fsm.txt\n");
			std::abort();
		}
	} else if (!bridge) {
		return; // default OFF outside bridge: no host-path change, no markers
	} else {
		params = p2mamutafsm::Params();
		std::printf("P2_MAMUTA_FSM_BRIDGE_DEFAULTS source_id=54\n");
		std::fflush(stdout);
	}
	// Own only the actors the Mamuta module already registered; do not
	// duplicate identity resolution or bank loading here.
	std::vector<Teki*> selected;
	Iterator it(tekiMgr);
	CI_LOOP(it) {
		Teki* actor = static_cast<Teki*>(*it);
		if (!actor || !actor->mGenerator || !pc_p2_mamuta_is_bound(actor)) continue;
		selected.push_back(actor);
	}
	if (selected.empty()) {
		std::fprintf(stderr, "p2 mamuta FSM: no Mamuta actor\n");
		return;
	}
	for (Teki* actor : selected) {
		FsmActor& state = actors[static_cast<PelletView*>(actor)];
		state.home      = actor->getPosition();
		state.heading   = actor->getDirection();
		state.goal      = state.home;
		state.goalValid = true;
		state.logTimer  = 0.0f;
		actor->mHealth  = params.health;
		const Vector3f pos = actor->getPosition();
		const unsigned generator = pc_p2_campaign_token(actor);
		std::printf("P2_ENEMY_READY species=Miulin source_id=54 native_family=Miurin generator=%u "
		            "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native source_FSM=implemented "
		            "move_speed=%.0f sight=%.0f attack_range=%.0f attack_angle=%.0f\n",
		            generator, pos.x, pos.y, pos.z, actor->mHealth, params.health,
		            params.moveSpeed, params.sight, params.attackRange, params.attackAngle);
		std::printf("P2_MAMUTA_FSM_SUPPRESS generator=%u host_ai=suppressed P1_doAI_skipped\n", generator);
		std::fflush(stdout);
		enter(actor, state, p2mamutafsm::STATE_WAIT);
	}
	ready = true;
}

bool pc_p2_mamuta_fsm_suppress_ai(const BTeki* actor)
{
	return ready && actors.count(static_cast<PelletView*>(const_cast<BTeki*>(actor))) != 0;
}

void pc_p2_mamuta_fsm_update(BTeki* actor)
{
	if (!ready) return;
	auto found = actors.find(static_cast<PelletView*>(actor));
	if (found == actors.end()) return;
	FsmActor& state = found->second;
	const float dt = gsys->getFrameTime();
	if (dt <= 0.0f || dt > 0.5f) return;
	const unsigned generator = pc_p2_campaign_token(actor);
	const Vector3f pos = actor->getPosition();

	// The P1 Miurin vehicle re-initialises mHealth from its TPF_Life policy at
	// actor birth, which can land a frame after this module adopted the actor.
	// Re-assert the params.health on every update until the first real Pikmin
	// damage arrives, so the override survives the birth reset without masking
	// any natural damage.
	if (!state.healthAsserted) {
		actor->mHealth = params.health;
	}

	// The P1 host applies accumulated Pikmin damage through a TAI damage
	// reaction that lives in the suppressed strategy (doAI). Apply the queued
	// damage here so real Pikmin hits reach mHealth; no damage is injected.
	if (actor->mStoredDamage > 0.0f) {
		state.healthAsserted = true; // first natural damage: stop re-asserting
		actor->makeDamaged();
	}

	if (actor->mHealth <= 0.0f && state.state != p2mamutafsm::STATE_DEAD) {
		enter(actor, state, p2mamutafsm::STATE_DEAD);
	}
	state.stateTime += dt;

	// Source StateWait/StateWalk acquire the nearest target and store it on the
	// enemy (`enemy->mTargetCreature = target`); the host equivalent is the
	// creature pointer slot used by the Pikmin attack response.
	Creature* target = nearestCreature(pos, params.sight);
	if (target) {
		actor->setCreaturePointer(0, target);
	} else {
		actor->clearCreaturePointer(0);
	}
	const bool engaged = target && attackReady(pos, state.heading, target);
	const bool flickWanted = !engaged && nearestPiki(pos, params.flickRange * 0.5f) != nullptr;

	switch (state.state) {
	case p2mamutafsm::STATE_WAIT: {
		stop(actor);
		if (target && attackReady(pos, state.heading, target)) {
			enter(actor, state, p2mamutafsm::STATE_ATTACK_START);
			break;
		}
		if (flickWanted) {
			state.returnState = p2mamutafsm::STATE_WAIT;
			enter(actor, state, p2mamutafsm::STATE_FLICK);
			break;
		}
		if (target && state.stateTime > NOTICE_DELAY) {
			enter(actor, state, p2mamutafsm::STATE_TURN);
		}
		break;
	}
	case p2mamutafsm::STATE_TURN: {
		stop(actor);
		if (target && attackReady(pos, state.heading, target)) {
			enter(actor, state, p2mamutafsm::STATE_ATTACK_START);
			break;
		}
		if (!target || distXZ(target->getPosition(), pos) > params.sight) {
			enter(actor, state, p2mamutafsm::STATE_WAIT);
			break;
		}
		if (flickWanted) {
			state.returnState = p2mamutafsm::STATE_TURN;
			enter(actor, state, p2mamutafsm::STATE_FLICK);
			break;
		}
		if (turnTo(actor, state, target->getPosition(), dt, attackAngleRadians())
		    || state.stateTime >= TURN_DURATION) {
			enter(actor, state, p2mamutafsm::STATE_WALK);
		}
		break;
	}
	case p2mamutafsm::STATE_WALK: {
		state.returnTimer += dt;
		if (target && attackReady(pos, state.heading, target)) {
			enter(actor, state, p2mamutafsm::STATE_ATTACK_START);
			break;
		}
		if (!target || distXZ(target->getPosition(), pos) > params.sight) {
			if (distXZ(pos, state.home) < params.homeRadius) {
				enter(actor, state, p2mamutafsm::STATE_WAIT);
			} else {
				walkTo(actor, state, state.home, dt);
			}
			break;
		}
		if (flickWanted) {
			state.returnState = p2mamutafsm::STATE_WALK;
			enter(actor, state, p2mamutafsm::STATE_FLICK);
			break;
		}
		if (distXZ(pos, state.home) > params.territory || state.returnTimer > params.returnTime) {
			walkTo(actor, state, state.home, dt);
			if (distXZ(pos, state.home) < params.homeRadius) {
				enter(actor, state, p2mamutafsm::STATE_WAIT);
			}
			break;
		}
		walkTo(actor, state, target->getPosition(), dt);
		break;
	}
	case p2mamutafsm::STATE_ATTACK_START: {
		stop(actor);
		if (state.stateTime >= ATTACK_START_DURATION) {
			enter(actor, state, p2mamutafsm::STATE_ATTACKING);
		}
		break;
	}
	case p2mamutafsm::STATE_ATTACKING: {
		stop(actor);
		if (!state.buryFired && state.stateTime >= BURY_EVENT_TIME) {
			state.buryFired = true;
			doBury(actor, generator);
		}
		if (state.stateTime >= ATTACKING_DURATION) {
			enter(actor, state, p2mamutafsm::STATE_ATTACK_END);
		}
		break;
	}
	case p2mamutafsm::STATE_ATTACK_END: {
		stop(actor);
		if (state.stateTime >= ATTACK_END_DURATION) {
			if (target && attackReady(pos, state.heading, target)) {
				enter(actor, state, p2mamutafsm::STATE_ATTACKING);
			} else if (!target) {
				enter(actor, state, p2mamutafsm::STATE_WAIT);
			} else {
				enter(actor, state, p2mamutafsm::STATE_TURN);
			}
		}
		break;
	}
	case p2mamutafsm::STATE_FLICK: {
		stop(actor);
		if (!state.flickFired && state.stateTime >= FLICK_EVENT_TIME) {
			state.flickFired = true;
			doFlick(actor, generator);
		}
		if (state.stateTime >= FLICK_DURATION) {
			enter(actor, state, state.returnState);
		}
		break;
	}
	case p2mamutafsm::STATE_DEAD: {
		stop(actor);
		if (!state.deadLogged) {
			state.deadLogged = true;
			std::printf("P2_MAMUTA_FSM_DEAD generator=%u source_id=54 health=%.1f\n", generator, actor->mHealth);
			std::fflush(stdout);
		}
		if (!state.died && state.stateTime >= DEAD_DURATION) {
			state.died = true;
			std::printf("P2_MAMUTA_FSM_CORPSE generator=%u source_id=54 native=host_escape_now\n", generator);
			std::fflush(stdout);
			// die() alone only arms mDeadState; dieSoon() normally runs inside
			// doAI, which this module suppresses. pcEscapeNow() finalizes the
			// death (carcass birth) outside doAI (teki.h family-lane helper).
			actor->pcEscapeNow();
		}
		break;
	}
	default:
		break;
	}

	state.logTimer += dt;
	if (state.logTimer >= 1.0f) {
		state.logTimer = 0.0f;
		std::printf("P2_MAMUTA_FSM_POS generator=%u state=%s x=%.2f z=%.2f\n", generator,
		            p2mamutafsm::stateName(state.state), pos.x, pos.z);
		std::fflush(stdout);
	}
}
