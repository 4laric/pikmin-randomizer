// Opt-in native source FSM for the Dwarf Orange Bulborb (BlueKochappy,
// EnemyID 44) on the private P1 Chappy placement vehicle. This is lane-13 gate
// B ("source behavior"): it replaces the host P1-AI proxy for actors already
// registered by pc_p2_dwarf_orange, but only when the arena opts in with
// `p2-dwarf-orange-fsm.txt` (default OFF). Source revision
// 632af93787b9c95b63f0c13be32b161375ce3a96
// (include/Game/Entities/KochappyBase.h, src/plugProjectYamashitaU/kochappyState.cpp).
//
// Source states covered: Wait(0), Walk(3), Attack(4), Flick(5), Dead(1).
// Intentionally partial (documented in docs/PIKMIN2_KOCHAPPY_FSM.md):
//   * Turn/TurnToHome/GoHome are collapsed into the Walk home-return branch
//     (territory fp09=500, home radius fp10=80); the source Turn clip
//     (waitact1) is not played.
//   * Press(8) squash death is not entered here; the host corpse handoff owns
//     the carrier motion. Demo(9) kill(nullptr) is not reached because this
//     module calls the host actor->die() at the dead-animation end.
//   * The Wait notice cry (PSSE_EN_KOCHAPPY_NOTICE, wait1 frame 61) and the
//     wait1 frame-60 random-frame latch have no host sound/anim equivalent.
//   * Attack applies one InteractAttack at source frame 8 (attack radius fp22
//     = 35, damage fp24 = 10). eatPikmin/flickStickPikmin and the frame-88
//     swallow/white-pikmin poison are not modelled. Flick applies
//     InteractFlick at source frame 31 (shake range fp19 = 17, knockback
//     fp17 = 50) to Pikmin in range; the stuck-pikmin latch
//     (EnemyFunc::isStartFlick) is approximated by a contact-radius test.
// Movement uses the source fp06 = 60 speed; turn rate 2.0 rad/s is a recorded
// port adaptation because the host drive API takes a rate, not the source
// per-frame turn speed fp08. Every hook is a no-op for unregistered actors and
// for the default-OFF path.
#include "pc_p2_kochappy_fsm.h"
#include "pc_p2_kochappy_fsm_policy.h"
#include "pc_p2_dwarf_orange.h"
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
constexpr float ATTACK_DURATION  = 90.0f / 30.0f;
constexpr float FLICK_DURATION   = 80.0f / 30.0f;
constexpr float DEAD_DURATION    = 90.0f / 30.0f;
constexpr float ATTACK_EVENT_FRAME = 8.0f;
constexpr float FLICK_EVENT_FRAME  = 31.0f;
constexpr float NOTICE_DELAY       = 0.5f;  // port adaptation: source animation end
constexpr float TURN_RATE          = 2.0f;  // port adaptation (host drive rate)
constexpr float FLICK_CONTACT_RADIUS = 8.0f; // port adaptation (isStartFlick latch)
constexpr float SHAKE_RANGE        = 17.0f;   // general fp19
constexpr float SHAKE_KNOCKBACK    = 50.0f;   // general fp17

struct FsmActor {
	State state           = p2kochappyfsm::STATE_WAIT;
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

void walkTo(BTeki* actor, FsmActor& state, const Vector3f& target, float dt)
{
	const Vector3f pos    = actor->getPosition();
	const float desired   = std::atan2(target.x - pos.x, target.z - pos.z);
	const float maxTurn   = TURN_RATE * dt;
	float diff            = wrapPi(desired - state.heading);
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

// Source CG_GENERALPARMS attack gate (fp20/fp21). The host has no true
// stuck-Pikmin latch, so the attack posture is checked before the flick
// approximation; this is a recorded port adaptation.
bool attackReady(const Vector3f& pos, float heading, const Creature* target)
{
	const Vector3f targetPos = target->getPosition();
	if (distXZ(targetPos, pos) > params.attackRange) return false;
	const float angle = std::fabs(wrapPi(std::atan2(targetPos.x - pos.x, targetPos.z - pos.z) - heading));
	return angle <= params.attackAngle * PI / 180.0f;
}

int motionFor(State state)
{
	switch (state) {
	case p2kochappyfsm::STATE_WALK: return TekiMotion::Move1;
	case p2kochappyfsm::STATE_ATTACK: return TekiMotion::Attack;
	case p2kochappyfsm::STATE_FLICK: return TekiMotion::Flick;
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
} // namespace

void pc_p2_kochappy_fsm_reset()
{
	actors.clear();
	ready = false;
}

void pc_p2_kochappy_fsm_forget(BTeki* actor)
{
	actors.erase(static_cast<PelletView*>(actor));
}

bool pc_p2_kochappy_fsm_enabled()
{
	return ready;
}

void pc_p2_kochappy_fsm_setup()
{
	pc_p2_kochappy_fsm_reset();
	if (!tekiMgr) return;
	std::ifstream config("p2-dwarf-orange-fsm.txt");
	if (!config) return; // default OFF: no host-path change, no markers
	if (!p2kochappyfsm::parseConfig(config, params)) {
		std::fprintf(stderr, "Invalid p2-dwarf-orange-fsm.txt\n");
		std::abort();
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
	if (selected.empty()) {
		std::fprintf(stderr, "p2-dwarf-orange-fsm.txt present but no Dwarf Orange actor\n");
		return;
	}
	for (Teki* actor : selected) {
		FsmActor& state   = actors[static_cast<PelletView*>(actor)];
		state.home     = actor->getPosition();
		state.heading  = actor->getDirection();
		state.logTimer = 0.0f;
		actor->mHealth = params.health;
		const Vector3f pos = actor->getPosition();
		const unsigned generator = actor->mGenerator->_70;
		std::printf("P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=%u "
		            "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native source_FSM=implemented "
		            "move_speed=%.0f sight=%.0f attack_range=%.0f attack_angle=%.0f\n",
		            generator, pos.x, pos.y, pos.z, actor->mHealth, params.health,
		            params.moveSpeed, params.sight, params.attackRange, params.attackAngle);
		std::fflush(stdout);
		enter(actor, state, p2kochappyfsm::STATE_WAIT);
	}
	ready = true;
}

bool pc_p2_kochappy_fsm_suppress_ai(const BTeki* actor)
{
	return ready && actors.count(static_cast<PelletView*>(const_cast<BTeki*>(actor))) != 0;
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

	if (actor->mHealth <= 0.0f && state.state != p2kochappyfsm::STATE_DEAD) {
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

	switch (state.state) {
	case p2kochappyfsm::STATE_WAIT: {
		stop(actor);
		if (target && attackReady(pos, state.heading, target)) {
			enter(actor, state, p2kochappyfsm::STATE_ATTACK);
			break;
		}
		const bool engaged = target && distXZ(target->getPosition(), pos) <= params.attackRange;
		if (!engaged && nearestPiki(pos, FLICK_CONTACT_RADIUS)) {
			enter(actor, state, p2kochappyfsm::STATE_FLICK);
			break;
		}
		if (target && state.stateTime > NOTICE_DELAY) {
			enter(actor, state, p2kochappyfsm::STATE_WALK);
		}
		break;
	}
	case p2kochappyfsm::STATE_WALK: {
		if (target && attackReady(pos, state.heading, target)) {
			enter(actor, state, p2kochappyfsm::STATE_ATTACK);
			break;
		}
		const Vector3f targetPos = target ? target->getPosition() : pos;
		const bool engaged     = target && distXZ(targetPos, pos) <= params.attackRange;
		if (!engaged && nearestPiki(pos, FLICK_CONTACT_RADIUS)) {
			enter(actor, state, p2kochappyfsm::STATE_FLICK);
			break;
		}
		if (!target) {
			if (distXZ(pos, state.home) > params.homeRadius) {
				walkTo(actor, state, state.home, dt);
			} else {
				enter(actor, state, p2kochappyfsm::STATE_WAIT);
			}
			break;
		}
		if (distXZ(pos, state.home) > params.territory) {
			walkTo(actor, state, state.home, dt);
			if (distXZ(pos, state.home) <= params.homeRadius) {
				enter(actor, state, p2kochappyfsm::STATE_WAIT);
			}
			break;
		}
		walkTo(actor, state, targetPos, dt);
		break;
	}
	case p2kochappyfsm::STATE_ATTACK: {
		stop(actor);
		if (!state.attackFired && state.stateTime * 30.0f >= ATTACK_EVENT_FRAME) {
			state.attackFired = true;
			Creature* target  = nearestCreature(pos, params.attackHitRange);
			if (target) {
				target->stimulate(InteractAttack(actor, nullptr, params.attackDamage, false));
				std::printf("P2_KOCHAPPY_ATTACK generator=%u frame=%.0f damage=%.0f\n", generator,
				            ATTACK_EVENT_FRAME, params.attackDamage);
				std::fflush(stdout);
			}
		}
		if (state.stateTime >= ATTACK_DURATION) {
			enter(actor, state, p2kochappyfsm::STATE_WALK);
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
			enter(actor, state, p2kochappyfsm::STATE_WAIT);
		}
		break;
	}
	case p2kochappyfsm::STATE_DEAD: {
		stop(actor);
		if (!state.deadLogged) {
			state.deadLogged = true;
			std::printf("P2_KOCHAPPY_DEAD generator=%u source_id=44 health=0\n", generator);
			std::fflush(stdout);
		}
		if (!state.died && state.stateTime >= DEAD_DURATION) {
			state.died = true;
			std::printf("P2_KOCHAPPY_CORPSE generator=%u source_id=44 native=host_die\n", generator);
			std::fflush(stdout);
			actor->die();
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
