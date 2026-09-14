// Opt-in native source FSM for the Dwarf Orange Bulborb (BlueKochappy,
// EnemyID 44) on the private P1 Chappy placement vehicle. This is lane-13 gate
// B ("source behavior"): it replaces the host P1-AI proxy for actors already
// registered by pc_p2_dwarf_orange, but only when the arena opts in with
// `p2-dwarf-orange-fsm.txt` (default OFF). Source revision
// 632af93787b9c95b63f0c13be32b161375ce3a96
// (include/Game/Entities/KochappyBase.h, src/plugProjectYamashitaU/kochappyState.cpp).
//
// Source states covered: Wait(0), Dead(1), Turn(2), Walk(3), Attack(4),
// Flick(5), TurnToHome(6), GoHome(7), Press(8). Demo(9) is the source
// kill(nullptr) terminal; on the host the Dead end finalizes with
// actor->pcEscapeNow() (die + dieSoon), so Demo is folded into Dead.
//
// Recorded port adaptations / partials (docs/PIKMIN2_KOCHAPPY_FSM.md):
//   * The P1 host applies accumulated Pikmin damage in a TAI damage reaction
//     inside doAI; because the FSM suppresses doAI it calls actor->makeDamaged()
//     itself so real Pikmin hits still reach mHealth (no damage is injected).
//   * EnemyFunc::isStartFlick (a Pikmin actually stuck to the body) is
//     approximated by a contact-radius test; attack posture takes precedence.
//   * Attack applies one InteractAttack at source frame 8 (attack hit radius
//     fp22 = 35, damage fp24 = 10). eatPikmin/flickStickPikmin and the frame-88
//     swallow / white-Pikmin poison are not modelled.
//   * `isTargetOutOfRange` is approximated by distance > sight fp12 = 95.
//   * Press is implemented as a state and a `pc_p2_kochappy_fsm_press` trigger
//     (source Press: health 0, type1 anim, then Dead). The P1 Chappy vehicle
//     exposes no press callback for this P2 actor, so no in-engine trigger is
//     wired; it is UNTESTED at runtime.
//   * The Wait notice cry (PSSE_EN_KOCHAPPY_NOTICE, wait1 frame 61) and the
//     wait1 frame-60 random-frame latch have no host sound/anim equivalent.
// Movement uses the source fp06 = 60 speed; turn rate 2.0 rad/s is a recorded
// adaptation because the host drive API takes a rate, not the source per-frame
// turn speed fp08. Every hook is a no-op for unregistered actors and for the
// default-OFF path.
#include "pc_p2_kochappy_fsm.h"
#include "pc_p2_kochappy_fsm_policy.h"
#include "pc_p2_dwarf_orange.h"
#include "pc_randomizer.h"
#include "teki.h"
#include "Interactions.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Generator.h"
#include "system.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <vector>

namespace {
using p2kochappyfsm::State;

// Source frames (kochappy/enemyanimmgr.txt, docs/PIKMIN2_DWARF_VARIANTS.md §3)
// at the engine's fixed 30 fps.
constexpr float TURN_DURATION    = 25.0f / 30.0f;  // waitact1
constexpr float ATTACK_DURATION  = 90.0f / 30.0f;
constexpr float FLICK_DURATION   = 80.0f / 30.0f;
constexpr float DEAD_DURATION    = 90.0f / 30.0f;
constexpr float PRESS_DURATION   = 105.0f / 30.0f; // type1
constexpr float ATTACK_EVENT_FRAME = 8.0f;
constexpr float FLICK_EVENT_FRAME  = 31.0f;
constexpr float NOTICE_DELAY       = 0.5f;  // port adaptation: source animation end
constexpr float TURN_RATE          = 2.0f;  // port adaptation (host drive rate)
constexpr float FLICK_CONTACT_RADIUS = 8.0f; // port adaptation (isStartFlick latch)
constexpr float SHAKE_RANGE        = 17.0f;   // general fp19
constexpr float SHAKE_KNOCKBACK    = 50.0f;   // general fp17

struct FsmActor {
	State state           = p2kochappyfsm::STATE_WAIT;
	State returnState     = p2kochappyfsm::STATE_WAIT;
	float stateTime       = 0.0f;
	float heading         = 0.0f;
	Vector3f home;
	bool attackFired      = false;
	bool flickFired       = false;
	bool deadLogged       = false;
	bool died             = false;
	float logTimer        = 0.0f;
};

std::map<PelletView*, FsmActor> actors;
p2kochappyfsm::Params params;
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
		Navi* navi = naviMgr->getNavi();
		if (navi && navi->isAlive()) {
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

// Source turnToTarget / turnToTargetPos: rotate in place toward a point. Returns
// true once the facing is inside the given tolerance (radians).
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

// Source EnemyFunc::walkToTarget: turn toward the point while driving forward at
// the source move speed.
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

void doFlick(BTeki* actor)
{
	if (!pikiMgr) return;
	const Vector3f pos = actor->getPosition();
	Iterator it(pikiMgr);
	CI_LOOP(it) {
		Piki* piki = static_cast<Piki*>(*it);
		if (piki && piki->isAlive() && distXZ(piki->getPosition(), pos) < SHAKE_RANGE) {
			piki->stimulate(InteractFlick(actor, SHAKE_KNOCKBACK, 0.0f, actor->getDirection()));
		}
	}
}

float attackAngleRadians()
{
	return params.attackAngle * PI / 180.0f;
}

// Source CG_GENERALPARMS attack gate (fp20/fp21). The host has no true
// stuck-Pikmin latch, so the attack posture is checked before the flick
// approximation; this is a recorded port adaptation.
bool attackReady(const Vector3f& pos, float heading, const Creature* target)
{
	const Vector3f targetPos = target->getPosition();
	if (distXZ(targetPos, pos) > params.attackRange) return false;
	const float angle = std::fabs(wrapPi(std::atan2(targetPos.x - pos.x, targetPos.z - pos.z) - heading));
	return angle <= attackAngleRadians();
}

int motionFor(State state)
{
	switch (state) {
	case p2kochappyfsm::STATE_WALK:
	case p2kochappyfsm::STATE_GO_HOME: return TekiMotion::Move1;
	case p2kochappyfsm::STATE_TURN:
	case p2kochappyfsm::STATE_TURN_TO_HOME: return TekiMotion::WaitAct1;
	case p2kochappyfsm::STATE_ATTACK: return TekiMotion::Attack;
	case p2kochappyfsm::STATE_FLICK: return TekiMotion::Flick;
	case p2kochappyfsm::STATE_PRESS: return TekiMotion::Type1;
	case p2kochappyfsm::STATE_DEAD: return TekiMotion::Dead;
	default: return TekiMotion::Wait1;
	}
}

void enter(BTeki* actor, FsmActor& state, State next)
{
	state.state       = next;
	state.stateTime   = 0.0f;
	state.attackFired = false;
	state.flickFired  = false;
	actor->startMotion(motionFor(next));
	const unsigned generator = actor->mGenerator ? actor->mGenerator->_70 : 0u;
	std::printf("P2_KOCHAPPY_STATE generator=%u state=%s\n", generator,
	            p2kochappyfsm::stateName(next));
	std::fflush(stdout);
}

bool adopt_actor(Teki* actor)
{
	FsmActor& state = actors[static_cast<PelletView*>(actor)];
	state.home      = actor->getPosition();
	state.heading   = actor->getDirection();
	state.logTimer  = 0.0f;
	actor->mHealth  = params.health;
	const unsigned generator = actor->mGenerator ? actor->mGenerator->_70 : 0u;
	const Vector3f pos = actor->getPosition();
	std::printf("P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=%u "
	            "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native source_FSM=implemented "
	            "move_speed=%.0f sight=%.0f attack_range=%.0f attack_angle=%.0f\n",
	            generator, pos.x, pos.y, pos.z, actor->mHealth, params.health,
	            params.moveSpeed, params.sight, params.attackRange, params.attackAngle);
	std::fflush(stdout);
	enter(actor, state, p2kochappyfsm::STATE_WAIT);
	return true;
}
} // namespace

void pc_p2_kochappy_fsm_reset()
{
	actors.clear();
	ready = false;
}

void pc_p2_kochappy_fsm_forget(BTeki* actor)
{
	if (actors.erase(static_cast<PelletView*>(actor)) != 0) {
		std::printf("P2_KOCHAPPY_FSM_FORGET registered=1\n");
		std::fflush(stdout);
	}
}

bool pc_p2_kochappy_fsm_enabled()
{
	return ready;
}

void pc_p2_kochappy_fsm_setup()
{
	pc_p2_kochappy_fsm_reset();
	if (!tekiMgr) return;
	const bool generated = pc_randomizer_p2_bridge() && pc_randomizer_p2_bound(44);
	if (generated) {
		// Generated sessions with a bound source-44 identity opt the FSM in
		// regardless of the arena file; an override staged as
		// assets/p2-dwarf-orange-fsm.txt is honored, otherwise the audited
		// defaults retained by Params apply.
		std::ifstream config("assets/p2-dwarf-orange-fsm.txt");
		if (config && !p2kochappyfsm::parseConfig(config, params)) {
			std::fprintf(stderr, "Invalid assets/p2-dwarf-orange-fsm.txt\n");
			std::abort();
		}
		ready = true;
	} else {
		std::ifstream config("p2-dwarf-orange-fsm.txt");
		if (!config) return; // default OFF: no host-path change, no markers
		if (!p2kochappyfsm::parseConfig(config, params)) {
			std::fprintf(stderr, "Invalid p2-dwarf-orange-fsm.txt\n");
			std::abort();
		}
	}
	// Own only the actors the Dwarf Orange module already registered; do not
	// duplicate identity resolution or bank loading here.
	std::vector<Teki*> selected;
	Iterator it(tekiMgr);
	CI_LOOP(it) {
		Teki* actor = static_cast<Teki*>(*it);
		if (!actor || !actor->mGenerator || !pc_p2_dwarf_orange_registered(actor)) continue;
		selected.push_back(actor);
	}
	if (!generated && selected.empty()) {
		std::fprintf(stderr, "p2-dwarf-orange-fsm.txt present but no Dwarf Orange actor\n");
		return; // keeps ready=false for the arena path
	}
	for (Teki* actor : selected) {
		adopt_actor(actor);
	}
}

void pc_p2_kochappy_fsm_adopt(BTeki* actor)
{
	if (!ready || !actor) return;
	if (!pc_p2_dwarf_orange_registered(actor)) return; // own Dwarf Orange actors only
	if (actors.count(static_cast<PelletView*>(actor))) return; // idempotent
	adopt_actor(static_cast<Teki*>(actor));
}

bool pc_p2_kochappy_fsm_suppress_ai(const BTeki* actor)
{
	return ready && actors.count(static_cast<PelletView*>(const_cast<BTeki*>(actor))) != 0;
}

// Source Obj::pressCallBack transitions to Press (health 0, type1 anim, then
// the terminal Demo kill). No in-engine P1 Chappy press callback is wired to
// this P2 actor, so callers that own a bounded squash event may invoke this.
void pc_p2_kochappy_fsm_press(BTeki* actor)
{
	if (!ready || !actor) return;
	auto found = actors.find(static_cast<PelletView*>(actor));
	if (found == actors.end()) return;
	actor->mHealth = 0.0f;
	enter(actor, found->second, p2kochappyfsm::STATE_PRESS);
}

void pc_p2_kochappy_fsm_update(BTeki* actor)
{
	if (!ready) return;
	auto found = actors.find(static_cast<PelletView*>(actor));
	if (found == actors.end()) return;
	FsmActor& state = found->second;
	const float dt = gsys->getFrameTime();
	if (dt <= 0.0f || dt > 0.5f) return;
	const unsigned generator = actor->mGenerator ? actor->mGenerator->_70 : 0u;
	const Vector3f pos = actor->getPosition();

	// The P1 host applies accumulated Pikmin damage through a TAI damage
	// reaction that lives in the suppressed strategy (doAI). Apply the queued
	// damage here so real Pikmin hits reach mHealth; no damage is injected.
	if (actor->mStoredDamage > 0.0f) {
		actor->makeDamaged();
	}

	if (actor->mHealth <= 0.0f && state.state != p2kochappyfsm::STATE_DEAD
	    && state.state != p2kochappyfsm::STATE_PRESS) {
		enter(actor, state, p2kochappyfsm::STATE_DEAD);
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
	const bool engaged = target && distXZ(target->getPosition(), pos) <= params.attackRange;
	const bool flickWanted = !engaged && nearestPiki(pos, FLICK_CONTACT_RADIUS) != nullptr;

	switch (state.state) {
	case p2kochappyfsm::STATE_WAIT: {
		stop(actor);
		if (target && attackReady(pos, state.heading, target)) {
			enter(actor, state, p2kochappyfsm::STATE_ATTACK);
			break;
		}
		if (flickWanted) {
			state.returnState = p2kochappyfsm::STATE_WAIT;
			enter(actor, state, p2kochappyfsm::STATE_FLICK);
			break;
		}
		if (target && state.stateTime > NOTICE_DELAY) {
			enter(actor, state, p2kochappyfsm::STATE_TURN);
		}
		break;
	}
	case p2kochappyfsm::STATE_TURN: {
		stop(actor);
		if (target && attackReady(pos, state.heading, target)) {
			enter(actor, state, p2kochappyfsm::STATE_ATTACK);
			break;
		}
		if (!target || distXZ(target->getPosition(), pos) > params.sight) {
			enter(actor, state, p2kochappyfsm::STATE_TURN_TO_HOME);
			break;
		}
		if (flickWanted) {
			state.returnState = p2kochappyfsm::STATE_TURN;
			enter(actor, state, p2kochappyfsm::STATE_FLICK);
			break;
		}
		if (turnTo(actor, state, target->getPosition(), dt, attackAngleRadians())
		    || state.stateTime >= TURN_DURATION) {
			enter(actor, state, p2kochappyfsm::STATE_WALK);
		}
		break;
	}
	case p2kochappyfsm::STATE_WALK: {
		if (target && attackReady(pos, state.heading, target)) {
			enter(actor, state, p2kochappyfsm::STATE_ATTACK);
			break;
		}
		if (!target || distXZ(target->getPosition(), pos) > params.sight) {
			enter(actor, state, p2kochappyfsm::STATE_TURN_TO_HOME);
			break;
		}
		if (flickWanted) {
			state.returnState = p2kochappyfsm::STATE_WALK;
			enter(actor, state, p2kochappyfsm::STATE_FLICK);
			break;
		}
		if (distXZ(pos, state.home) > params.territory) {
			enter(actor, state, p2kochappyfsm::STATE_TURN_TO_HOME);
			break;
		}
		walkTo(actor, state, target->getPosition(), dt);
		break;
	}
	case p2kochappyfsm::STATE_TURN_TO_HOME: {
		stop(actor);
		if (distXZ(pos, state.home) < params.homeRadius) {
			enter(actor, state, p2kochappyfsm::STATE_WAIT);
			break;
		}
		if (target && attackReady(pos, state.heading, target)) {
			enter(actor, state, p2kochappyfsm::STATE_ATTACK);
			break;
		}
		if (flickWanted) {
			state.returnState = p2kochappyfsm::STATE_TURN_TO_HOME;
			enter(actor, state, p2kochappyfsm::STATE_FLICK);
			break;
		}
		if (turnTo(actor, state, state.home, dt, attackAngleRadians())
		    || state.stateTime >= TURN_DURATION) {
			enter(actor, state, p2kochappyfsm::STATE_GO_HOME);
		}
		break;
	}
	case p2kochappyfsm::STATE_GO_HOME: {
		if (distXZ(pos, state.home) < params.homeRadius) {
			enter(actor, state, p2kochappyfsm::STATE_WAIT);
			break;
		}
		if (target && attackReady(pos, state.heading, target)) {
			enter(actor, state, p2kochappyfsm::STATE_ATTACK);
			break;
		}
		if (flickWanted) {
			state.returnState = p2kochappyfsm::STATE_GO_HOME;
			enter(actor, state, p2kochappyfsm::STATE_FLICK);
			break;
		}
		if (target) {
			enter(actor, state, p2kochappyfsm::STATE_WALK);
			break;
		}
		walkTo(actor, state, state.home, dt);
		break;
	}
	case p2kochappyfsm::STATE_ATTACK: {
		stop(actor);
		if (!state.attackFired && state.stateTime * 30.0f >= ATTACK_EVENT_FRAME) {
			state.attackFired = true;
			Creature* hit     = nearestCreature(pos, params.attackHitRange);
			if (hit) {
				hit->stimulate(InteractAttack(actor, nullptr, params.attackDamage, false));
				std::printf("P2_KOCHAPPY_ATTACK generator=%u frame=%.0f damage=%.0f\n", generator,
				            ATTACK_EVENT_FRAME, params.attackDamage);
				std::fflush(stdout);
			}
		}
		if (state.stateTime >= ATTACK_DURATION) {
			if (!target) {
				enter(actor, state, p2kochappyfsm::STATE_TURN_TO_HOME);
			} else if (attackReady(pos, state.heading, target)) {
				enter(actor, state, p2kochappyfsm::STATE_ATTACK);
			} else {
				enter(actor, state, p2kochappyfsm::STATE_TURN);
			}
		}
		break;
	}
	case p2kochappyfsm::STATE_FLICK: {
		stop(actor);
		if (!state.flickFired && state.stateTime * 30.0f >= FLICK_EVENT_FRAME) {
			state.flickFired = true;
			doFlick(actor);
			std::printf("P2_KOCHAPPY_FLICK generator=%u frame=%.0f\n", generator, FLICK_EVENT_FRAME);
			std::fflush(stdout);
		}
		if (state.stateTime >= FLICK_DURATION) {
			enter(actor, state, state.returnState);
		}
		break;
	}
	case p2kochappyfsm::STATE_PRESS: {
		stop(actor);
		if (state.stateTime >= PRESS_DURATION) {
			enter(actor, state, p2kochappyfsm::STATE_DEAD);
		}
		break;
	}
	case p2kochappyfsm::STATE_DEAD: {
		stop(actor);
		if (!state.deadLogged) {
			state.deadLogged = true;
			std::printf("P2_KOCHAPPY_DEAD generator=%u source_id=44 health=%.1f\n", generator, actor->mHealth);
			std::fflush(stdout);
		}
		if (!state.died && state.stateTime >= DEAD_DURATION) {
			state.died = true;
			std::printf("P2_KOCHAPPY_CORPSE generator=%u source_id=44 native=host_escape_now\n", generator);
			std::fflush(stdout);
			// die() alone only arms mDeadState; dieSoon() normally runs inside
			// doAI, which this module suppresses. pcEscapeNow() finalizes the
			// death (carcass birth) outside doAI (teki.h family-lane helper #219).
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
		std::printf("P2_KOCHAPPY_POS generator=%u state=%s x=%.2f z=%.2f\n", generator,
		            p2kochappyfsm::stateName(state.state), pos.x, pos.z);
		std::fflush(stdout);
	}
}
