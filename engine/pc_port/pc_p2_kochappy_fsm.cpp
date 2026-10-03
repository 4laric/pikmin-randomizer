// Native shared source FSM for Dwarf Orange (BlueKochappy) and opt-in Red (Kochappy),
// EnemyID 44) on the P1 Chappy placement vehicle. This is lane-13 gate
// B ("source behavior") + own44 (#871): it replaces the host P1-AI proxy for
// actors already registered by pc_p2_dwarf_orange. In bridge-mode campaign
// sessions the audited retail defaults drive the FSM without requiring
// `p2-dwarf-orange-fsm.txt` (an explicit file still overrides); outside bridge
// (room preview) the file stays required (default OFF there). Source revision
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
//   * Attack at source frame 8 (KEYEVENT_2, kochappyState.cpp:1403-1414):
//     EnemyFunc::attackNavi bites the captain only (attack hit radius fp22 = 35,
//     damage fp24 = 10; Pikmin are never damaged by the bite), then the source
//     EnemyFunc::eatPikmin (enemyAction.cpp:1107-1142) runs through
//     pc_p2_chappy_mouth.h (#884): a Pikmin is swallowed only within r=15 of
//     the "kamu" mouth joint (KochappyBase.cpp:175-183) sampled at attack frame
//     8 from the retail model (about 30 units in front of the feet), so a
//     Pikmin beside or behind the actor is never eaten. The P2 slot sticks to
//     the P1 host 'slot' child; with no host mouth part the capture is refused
//     (never InteractSwallow with a null part, which would kill outright).
//     EnemyFunc::swallowPikmin (frame 88, KEYEVENT_3) kills the mouth-stuck
//     Pikmin via InteractKill; a White Pikmin applies proper-fp02 poison
//     (eatWhitePikminCallBack -> mStoredDamage).
//     flickStickPikmin (frame 8) remains approximated by the standalone Flick
//     contact-radius test / not modelled in the attack posture.
//   * `isTargetOutOfRange` is approximated by distance > sight fp12 = 95.
//   * Press is implemented as a state and a `pc_p2_kochappy_fsm_press` trigger
//     (source Press: health 0, type1 anim, then Dead). The P1 Chappy vehicle
//     exposes no press callback for this P2 actor, so no in-engine trigger is
//     wired for legacy Orange/preview. Original Red source1 receives the actual
//     descending PikiFlying InteractPress and completes source Press->Demo at END;
//     its natural gameplay acceptance remains open.
//   * The Wait notice cry (PSSE_EN_KOCHAPPY_NOTICE, wait1 frame 61) and the
//     wait1 frame-60 random-frame latch have no host sound/anim equivalent.
// Movement uses the source fp06 = 60 speed; turn rate 2.0 rad/s is a recorded
// adaptation because the host drive API takes a rate, not the source per-frame
// turn speed fp08. Every hook is a no-op for unregistered actors and, outside
// bridge mode, for the default-OFF path (no config file).
#include "pc_p2_kochappy_fsm.h"
#include "pc_p2_kochappy_fsm_policy.h"
#include "pc_p2_chappy_mouth.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_dwarf_orange.h"
#include "pc_p2_kochappy.h"
#include "pc_p2_kochappy_policy.h"
#include "pc_p2_kochappy_stun.h"
#include "Pellet.h"
#include "pc_p2_white.h"
#include "pc_bbft.h"
#include "teki.h"
#include "Interactions.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "pc_p2_navi_select.h"
#include "Generator.h"
#include "Stickers.h"
#include "system.h"
#include "nlib/System.h"
#include <algorithm>
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
constexpr float SWALLOW_EVENT_FRAME = 88.0f; // KEYEVENT_3 (swallow/white poison)
constexpr float FLICK_EVENT_FRAME  = 31.0f;
constexpr float NOTICE_DELAY       = 0.5f;  // port adaptation: source animation end
constexpr float TURN_RATE          = 2.0f;  // port adaptation (host drive rate)
constexpr float FLICK_CONTACT_RADIUS = 8.0f; // port adaptation (isStartFlick latch)
constexpr float SHAKE_RANGE        = 17.0f;   // general fp19
constexpr float SHAKE_KNOCKBACK    = 50.0f;   // general fp17

struct FsmActor {
	int sourceId = 44;
    bool original=false,bittered=false;
	p2kochappyfsm::Params params;
	State state           = p2kochappyfsm::STATE_WAIT;
	State returnState     = p2kochappyfsm::STATE_WAIT;
	float stateTime       = 0.0f;
	float heading         = 0.0f;
	Vector3f home;
	bool attackFired      = false;
	bool swallowFired     = false;
	bool flickFired       = false;
	bool deadLogged       = false;
	bool itemsSpawned     = false;
	bool died             = false;
	bool healthAsserted   = false;
	bool stunPaused       = false;
	bool stunManualMotion = false;
	float stunMotionSpeed = 0.0f;
	float logTimer        = 0.0f;
	// #884: the Pikmin stuck into each source mouth slot; compared against the
	// live mouth-sticker set only, never dereferenced.
	Creature* mouth[p2chappymouth::MaxSlots] = {};
};

std::map<PelletView*, FsmActor> actors;
bool ready = false;
PelletConfig* redCorpseConfig = nullptr;

// Actual US carcass_config.txt Kochappy: min3/max6, pikicountmin/max4.
// Construct a fresh Parameter/CoreNode chain; never copy intrusive links or
// edit the shared P1/Orange host config. This immutable Red-only config lives
// on the scene App heap, like the carcass; reset drops only the borrowed handle.
void adoptRedCorpse(BTeki* actor)
{
 if (!actor->mPellet || !actor->mPellet->mConfig) {
  std::fprintf(stderr, "P2 Red source corpse missing native pellet/config\n");
  std::abort();
 }
 if (!redCorpseConfig) {
  PelletConfig* source = actor->mPellet->mConfig;
  const int heap = gsys->setHeap(SYSHEAP_App);
  redCorpseConfig = new PelletConfig;
#define COPY_VALUE(name) redCorpseConfig->name.mValue = source->name.mValue
  COPY_VALUE(mPelletName); COPY_VALUE(mPelletType); COPY_VALUE(mPelletColor);
  COPY_VALUE(mUseDynamicMotion); COPY_VALUE(_A0); COPY_VALUE(_B0); COPY_VALUE(_C0);
  COPY_VALUE(mPelletScale); COPY_VALUE(mCarryInfoHeight);
  COPY_VALUE(mAnimSoundID); COPY_VALUE(mBounceSoundID);
#undef COPY_VALUE
  redCorpseConfig->mModelId = source->mModelId;
  redCorpseConfig->mPelletId = source->mPelletId;
  redCorpseConfig->mUnusedId = source->mUnusedId;
  redCorpseConfig->mRepairAnimJointIndex = source->mRepairAnimJointIndex;
  redCorpseConfig->mCarryMinPikis.mValue = 3;
  redCorpseConfig->mCarryMaxPikis.mValue = 6;
  redCorpseConfig->mMatchingOnyonSeeds.mValue = 4;
  redCorpseConfig->mNonMatchingOnyonSeeds.mValue = 4;
  gsys->setHeap(heap);
 }
 actor->mPellet->mConfig = redCorpseConfig;
 std::printf("P2_KOCHAPPY_SOURCE_CARCASS source_id=1 min=3 max=6 seeds=4 private_config=1\n");
 std::fflush(stdout);
}

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
	const Vector3f drive(std::sin(state.heading) * state.params.moveSpeed, 0.0f,
	                     std::cos(state.heading) * state.params.moveSpeed);
	actor->inputDrive(drive);
	actor->mVelocity.set(drive);
}

void doFlick(BTeki* actor)
{
	// Source StateFlick::exec KEYEVENT_2 (kochappyState.cpp:1772-1779) flicks
	// stuck Pikmin, nearby Pikmin and nearby Navi with the same shake
	// (fp17/fp19). The host has no stuck/nearby split, so one contact-radius
	// sweep covers Pikmin and the captain is flicked on the same radius.
	if (!pikiMgr && !naviMgr) return;
	const Vector3f pos = actor->getPosition();
	if (pikiMgr) {
		Iterator it(pikiMgr);
		CI_LOOP(it) {
			Piki* piki = static_cast<Piki*>(*it);
			if (piki && piki->isAlive() && distXZ(piki->getPosition(), pos) < SHAKE_RANGE) {
				piki->stimulate(InteractFlick(actor, SHAKE_KNOCKBACK, 0.0f, actor->getDirection()));
			}
		}
	}
	for (Navi* navi : pc_p2_navis()) {
		if (navi->isAlive() && distXZ(navi->getPosition(), pos) < SHAKE_RANGE) {
			navi->stimulate(InteractFlick(actor, SHAKE_KNOCKBACK, 0.0f, actor->getDirection()));
		}
	}
}

struct EatStats {
	int captured       = 0;
	int freeBefore     = 0;
	int refusedNoHost  = 0;
	int hostSlots      = 0;
	bool nearestBehind = false;
	p2chappymouth::WindowDiag diag; // #884 geometry fields on P2_KOCHAPPY_EAT
	float headingDeg = 0.0f;
	float drawYawDeg = 0.0f;
};

p2chappymouth::Vec3 mouthVec(const Vector3f& v)
{
	return p2chappymouth::Vec3{v.x, v.y, v.z};
}

// Source EnemyFunc::eatPikmin (KEYEVENT_2, frame 8; enemyAction.cpp:1107-1142)
// through pc_p2_chappy_mouth.h: an eligible Pikmin (EatPikminDefaultCondition)
// within r=15 of the empty "kamu" slot at the retail attack frame 8 is stuck
// to the P1 host 'slot' child (p3=0 selects the eat/Esa motion). No reachable
// empty slot, or no host mouth part, means no capture: InteractSwallow is never
// sent with a null part and BTeki::getFreeSlot (unguarded getSphere) is unused.
EatStats doEat(BTeki* actor, FsmActor& state, unsigned generator)
{
	EatStats st;
	// Red1 and Orange44 share the Kochappy model/skeleton and exact kamu
 // slot table (KochappyBase::initMouthSlots); keep this family geometry.
 const p2chappymouth::Profile* prof = p2chappymouth::profileForSource(44);
	if (!prof || !pikiMgr) return st;
	CollPart* mouthPart = actor->mCollInfo ? actor->mCollInfo->getSphere('slot') : nullptr;
	const int hostCount = mouthPart ? mouthPart->getChildCount() : 0;
	st.hostSlots = hostCount;
	std::vector<Creature*> inMouth;
	{
		Stickers stickers(actor);
		Iterator it(&stickers);
		CI_LOOP(it) {
			Creature* stuck = *it;
			if (stuck && stuck->isPiki() && stuck->isStickToMouth()) inMouth.push_back(stuck);
		}
	}
	bool occupied[p2chappymouth::MaxSlots] = {};
	for (int i = 0; i < prof->slots; ++i) {
		if (state.mouth[i] && std::find(inMouth.begin(), inMouth.end(), state.mouth[i]) != inMouth.end()) {
			occupied[i] = true;
		} else {
			state.mouth[i] = nullptr;
			++st.freeBefore;
		}
	}
	// Snapshot the prey before any stimulate (receivers change stick state).
	std::vector<Piki*> pikis;
	std::vector<p2chappymouth::Prey> prey;
	{
		Iterator it(pikiMgr);
		CI_LOOP(it) {
			Piki* piki = static_cast<Piki*>(*it);
			if (!piki) continue;
			p2chappymouth::Prey q{};
			q.pos             = mouthVec(piki->getPosition());
			q.alive           = piki->isAlive();
			q.visible         = piki->isVisible();
			q.buried          = piki->isBuried();
			q.stuckToAnyMouth = piki->isStickToMouth() != 0;
			q.stuckToSelf     = piki->getStickObject() == actor && !q.stuckToAnyMouth;
			q.stuckToAny      = piki->isStickTo();
			pikis.push_back(piki);
			prey.push_back(q);
		}
	}
	const p2chappymouth::Vec3 apos = mouthVec(actor->getPosition());
	const int count = (int)prey.size();
	const int nearest = p2chappymouth::nearestIndex(prey.data(), count, apos, state.params.attackHitRange,
	                                                [](const p2chappymouth::Prey& q) { return p2chappymouth::eligible(q); });
	st.nearestBehind = nearest >= 0 && p2chappymouth::toLocal(apos, state.heading, prey[nearest].pos).z <= 0.0f;
	const int frame    = prof->firstFrame;
	const float radius = p2chappymouth::effectiveRadius(*prof);
	st.headingDeg      = wrapPi(state.heading) * 180.0f / PI;
	st.drawYawDeg      = wrapPi(actor->getDirection()) * 180.0f / PI;
	p2chappymouth::observe(st.diag, *prof, frame, apos, state.heading, prey.data(), count, occupied);
	st.captured = p2chappymouth::eat(*prof, frame, apos, state.heading, prey.data(), count, occupied, [&](int n, int slot) {
		const int idx  = p2chappymouth::hostPartIndex(slot, hostCount);
		CollPart* part = idx >= 0 ? mouthPart->getChildAt(idx) : nullptr;
		if (!part) {
			++st.refusedNoHost;
			return false;
		}
		Piki* piki       = pikis[n];
		const bool white = pc_p2_is_white(piki);
		if (!piki->stimulate(InteractSwallow(actor, part, 0))) return false;
		state.mouth[slot] = piki;
		const p2chappymouth::Vec3 local = p2chappymouth::toLocal(apos, state.heading, prey[n].pos);
		const float dist = p2chappymouth::distance(p2chappymouth::slotWorld(*prof, frame, slot, apos, state.heading), prey[n].pos);
		std::printf("P2_KOCHAPPY_EAT_PREY generator=%u source_id=%d frame=%d slot=%d prey_angle_deg=%.1f prey_dist=%.1f "
		            "slot_radius=%.1f local_x=%.1f local_y=%.1f local_z=%.1f white=%d\n",
		            generator, state.sourceId, frame, slot, std::atan2(local.x, local.z) * 180.0f / PI, dist, radius, local.x,
		            local.y, local.z, white ? 1 : 0);
		std::fflush(stdout);
		return true;
	});
	return st;
}

// Source EnemyFunc::swallowPikmin (KEYEVENT_3, frame 88): kill every Pikmin
// stuck to the eater's mouth; a White Pikmin applies the proper-fp02 poison via
// eatWhitePikminCallBack (host: accumulate into mStoredDamage, applied by the
// next makeDamaged() call). Returns the swallowed count and sets whitePoisoned.
int doSwallow(BTeki* actor, const FsmActor& state, int& whitePoisoned)
{
	whitePoisoned = 0;
	int count = 0;
	Stickers stickers(actor);
	Iterator it(&stickers);
	CI_LOOP(it) {
		Creature* stuck = *it;
		if (!stuck || !stuck->isPiki() || !stuck->isStickToMouth()) continue;
		Piki* piki = static_cast<Piki*>(stuck);
		const bool white = pc_p2_is_white(piki);
		if (piki->stimulate(InteractKill(actor, 0))) {
			++count;
			if (white) {
				actor->mStoredDamage += state.params.poisonDamage;
				whitePoisoned = 1;
			}
		}
	}
	return count;
}

float attackAngleRadians(const FsmActor& state)
{
	return state.params.attackAngle * PI / 180.0f;
}

// Source CG_GENERALPARMS attack gate (fp20/fp21). The host has no true
// stuck-Pikmin latch, so the attack posture is checked before the flick
// approximation; this is a recorded port adaptation.
bool attackReady(const Vector3f& pos, float heading, const Creature* target, const FsmActor& state)
{
	const Vector3f targetPos = target->getPosition();
	if (distXZ(targetPos, pos) > state.params.attackRange) return false;
	const float angle = std::fabs(wrapPi(std::atan2(targetPos.x - pos.x, targetPos.z - pos.z) - heading));
	return angle <= attackAngleRadians(state);
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

void finishStun(BTeki* actor, FsmActor& state)
{
	if (!state.stunPaused) return;
	actor->mMotionSpeed = state.stunMotionSpeed;
	if (!state.stunManualMotion) actor->clearTekiOption(TEKIOPT_ManualAnimation);
	state.stunPaused = false;
	std::printf("P2_KOCHAPPY_STUN_RESUME generator=%u source_id=%d state=%s state_time=%.3f\n",
	            pc_p2_campaign_token(actor), state.sourceId, p2kochappyfsm::stateName(state.state), state.stateTime);
}

void enter(BTeki* actor, FsmActor& state, State next)
{
	if (next == p2kochappyfsm::STATE_DEAD || next == p2kochappyfsm::STATE_PRESS) {
		finishStun(actor, state);
		pc_p2_kochappy_stun_interrupt(actor);
	}
	state.state        = next;
	state.stateTime    = 0.0f;
	state.attackFired  = false;
	state.swallowFired = false;
	state.flickFired   = false;
 // Retail StateDead::init calls deathProcedure/throwupItem before its
 // death motion. The suppressed P1 strategy cannot emit generator pellets;
 // Red1's mapped personality owns this exactly-once ordinary drop boundary.
 // Orange44 remains unchanged until its separately-owned payload audit.
 if ((next == p2kochappyfsm::STATE_DEAD || (next == p2kochappyfsm::STATE_PRESS && state.original)) && state.sourceId == 1 && !state.itemsSpawned) {
  state.itemsSpawned = true;
  actor->spawnItems();
 }
	actor->startMotion(motionFor(next));
	const unsigned generator = pc_p2_campaign_token(actor);
	std::printf("P2_KOCHAPPY_STATE generator=%u state=%s\n", generator,
	            p2kochappyfsm::stateName(next));
	std::fflush(stdout);
}
} // namespace

void pc_p2_kochappy_fsm_reset()
{
	redCorpseConfig = nullptr;
	actors.clear();
	ready = false;
}

void pc_p2_kochappy_fsm_forget(BTeki* actor)
{
	auto found = actors.find(static_cast<PelletView*>(actor));
	if (found != actors.end()) finishStun(actor, found->second);
	if (actors.erase(static_cast<PelletView*>(actor)) != 0) {
		std::printf("P2_KOCHAPPY_FSM_FORGET registered=1\n");
		std::fflush(stdout);
	}
}

bool pc_p2_kochappy_fsm_enabled()
{
	return ready;
}

bool pc_p2_kochappy_fsm_stun_eligible(const BTeki* actor)
{
	if (!ready || !actor) return false;
	auto found = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
	return found != actors.end() && actor->mHealth > 0.0f
	    && found->second.state != p2kochappyfsm::STATE_DEAD
	    && found->second.state != p2kochappyfsm::STATE_PRESS;
}

void pc_p2_kochappy_fsm_begin_stun(BTeki* actor)
{
	auto found = actors.find(static_cast<PelletView*>(actor));
	if (found == actors.end() || found->second.stunPaused) return;
	FsmActor& state = found->second;
	state.stunPaused = true;
	state.stunManualMotion = actor->getTekiOption(TEKIOPT_ManualAnimation);
	state.stunMotionSpeed = actor->mMotionSpeed;
	actor->setTekiOption(TEKIOPT_ManualAnimation);
	actor->mMotionSpeed = 0.0f; // Source stopMotion; preserve the animator counter/event flags.
	std::printf("P2_KOCHAPPY_STUN_PAUSE generator=%u source_id=%d state=%s state_time=%.3f\n",
	            pc_p2_campaign_token(actor), state.sourceId, p2kochappyfsm::stateName(state.state), state.stateTime);
}

void pc_p2_kochappy_fsm_setup()
{
    for(const auto& row:p2original::originalActors().rows())if(row.second.enemy.source==1)return;
	pc_p2_kochappy_fsm_reset();
	if (!tekiMgr) return;
 // Orange44 retains its existing bridge/default and explicit-preview rules.
 // Red1 is separately opt-in: no Red sidecar means the legacy path remains.
 const bool bridge = pc_randomizer_p2_bridge() && !pc_pikipelago_room_preview();
 p2kochappyfsm::Params orangeParams, redParams = p2kochappyfsm::redDefaults();
 std::ifstream config("p2-dwarf-orange-fsm.txt"), redConfig("p2-dwarf-red-fsm.txt");
 const bool orangeEnabled = bool(config) || bridge;
 const bool redEnabled = bool(redConfig);
 if (config && !p2kochappyfsm::parseConfig(config, orangeParams)) {
  std::fprintf(stderr, "Invalid p2-dwarf-orange-fsm.txt\n"); std::abort();
 }
 if (redConfig && !p2kochappyfsm::parseConfig(redConfig, redParams,
                                           "P2_DWARF_RED_FSM_1", redParams)) {
  std::fprintf(stderr, "Invalid p2-dwarf-red-fsm.txt\n"); std::abort();
 }
 if (!orangeEnabled && !redEnabled) return;
 if (bridge && !config) {
  std::printf("P2_KOCHAPPY_FSM_BRIDGE_DEFAULTS source_id=44\n");
  std::fflush(stdout);
 }
 std::vector<Teki*> selected;
 Iterator it(tekiMgr);
 CI_LOOP(it) {
  Teki* actor = static_cast<Teki*>(*it);
  if (!actor || !actor->mGenerator) continue;
  if ((orangeEnabled && pc_p2_dwarf_orange_registered(actor)) ||
      (redEnabled && pc_p2_kochappy_registered(actor))) selected.push_back(actor);
 }
 if (selected.empty()) {
  std::fprintf(stderr, "p2 Kochappy FSM: no opted-in registered actor\n");
  return;
 }
	for (Teki* actor : selected) {
		FsmActor& state = actors[static_cast<PelletView*>(actor)];
        state.sourceId = pc_p2_kochappy_registered(actor) ? 1 : 44;
        state.params = state.sourceId == 1 ? redParams : orangeParams;
		state.home      = actor->getPosition();
		state.heading   = actor->getDirection();
		state.logTimer  = 0.0f;
		// #884: eat geometry is at P2 model scale 1; the draw uses mSRT.s.
		actor->mSRT.s.set(1.0f, 1.0f, 1.0f);
		actor->mHealth  = state.params.health;
		const Vector3f pos = actor->getPosition();
		const unsigned generator = pc_p2_campaign_token(actor);
		std::printf("P2_ENEMY_READY species=%s source_id=%d native_family=Chappy generator=%u "
		            "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native source_FSM=implemented "
		            "move_speed=%.0f sight=%.0f attack_range=%.0f attack_angle=%.0f\n",
		            state.sourceId == 1 ? "Kochappy" : "BlueKochappy", state.sourceId,
                    generator, pos.x, pos.y, pos.z, actor->mHealth, state.params.health,
		            state.params.moveSpeed, state.params.sight, state.params.attackRange, state.params.attackAngle);
		std::printf("P2_KOCHAPPY_SUPPRESS generator=%u host_ai=suppressed P1_doAI_skipped\n", generator);
		std::fflush(stdout);
		enter(actor, state, p2kochappyfsm::STATE_WAIT);
	}
	ready = true;
}

bool pc_p2_kochappy_fsm_bind_original(BTeki* actor,unsigned token,std::string& error){
 unsigned source=0,actual=0;
 if(!actor||!actor->mGenerator||!token||!pc_p2_kochappy_registered(actor)
 ||!p2original::originalActors().query(actor,source,actual)||source!=1||actual!=token
 ||actors.count(static_cast<PelletView*>(actor))){error="original Red FSM registry/visual ownership mismatch";return false;}
 FsmActor state;state.sourceId=1;state.original=true;state.params=p2kochappyfsm::redDefaults();
 state.home=actor->getPosition();state.heading=actor->getDirection();state.healthAsserted=true;
 actor->mSRT.s.set(1,1,1);actor->mHealth=actor->mMaxHealth=state.params.health;
 auto i=actors.emplace(static_cast<PelletView*>(actor),std::move(state)).first;
 enter(actor,i->second,p2kochappyfsm::STATE_WAIT);ready=true;
 std::printf("P2_ORIGINAL_RED_FSM_BIND source=1 token=%u health=200 move_speed=50 behavior=KochappyBase\n",token);std::fflush(stdout);
 error.clear();return true;
}
bool pc_p2_kochappy_fsm_suppress_ai(const BTeki* actor)
{
	return ready && actors.count(static_cast<PelletView*>(const_cast<BTeki*>(actor))) != 0;
}

PcKochappyFsmSnapshot pc_p2_kochappy_fsm_observe(const BTeki* actor)
{
 PcKochappyFsmSnapshot value;
 if(!ready||!actor)return value;
 const auto found=actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
 if(found==actors.end())return value;
 const auto& state=found->second;
 value.available=true;value.state=int(state.state);value.stateTime=state.stateTime;
 value.attackFired=state.attackFired;value.swallowFired=state.swallowFired;value.flickFired=state.flickFired;
 value.stunPaused=state.stunPaused;
 value.terminal=state.state==p2kochappyfsm::STATE_DEAD||state.state==p2kochappyfsm::STATE_PRESS;
 return value;
}

// Source pressCallBack enters Press. Original Red receives actual descending
// native contact through InteractPress and ends directly at Demo/kill.
// Legacy preview actors retain this explicit trigger.
void pc_p2_kochappy_fsm_press(BTeki* actor)
{
	if (!ready || !actor) return;
	auto found = actors.find(static_cast<PelletView*>(actor));
	if (found == actors.end()) return;
	found->second.healthAsserted = true; // keep the prologue from restoring health while pressed
	actor->mHealth = 0.0f;
	enter(actor, found->second, p2kochappyfsm::STATE_PRESS);
}

bool pc_p2_kochappy_fsm_original_pressed(BTeki* actor,Creature* owner){
 unsigned source=0,token=0;auto i=actors.find(static_cast<PelletView*>(actor));
 if(!actor||!owner||!p2original::originalActors().query(actor,source,token)||i==actors.end()||!i->second.original
 ||!p2kochappy::originalPressAccepted(source,ready&&actor->isAlive(),actor->mHealth,owner->isPiki(),owner->isAlive(),i->second.bittered))return false;
 pc_p2_kochappy_fsm_press(actor);return true;
}
void pc_p2_kochappy_fsm_original_bittered(BTeki* actor,bool value){
 auto i=actors.find(static_cast<PelletView*>(actor));if(i!=actors.end()&&i->second.original)i->second.bittered=value;
}
void pc_p2_kochappy_fsm_update(BTeki* actor)
{
	if (!ready) return;
	auto found = actors.find(static_cast<PelletView*>(actor));
	if (found == actors.end()) return;
	FsmActor& state = found->second;
	const float dt = gsys->getFrameTime();
	if (dt <= 0.0f || dt > 0.5f) return;
	const unsigned generator = pc_p2_campaign_token(actor);
	const Vector3f pos = actor->getPosition();

	// The P1 Chappy vehicle re-initialises mHealth from its TPF_Life policy at
	// actor birth, which can land a frame after this module adopted the actor.
	// Re-assert the opted-in state.params.health on every update until the first real
	// Pikmin damage arrives (default 250 is a no-op), so a health override
	// survives the birth reset without masking any natural damage.
	if (!state.healthAsserted) {
		actor->mHealth = state.params.health;
	}

	// The P1 host applies accumulated Pikmin damage through a TAI damage
	// reaction that lives in the suppressed strategy (doAI). Apply the queued
	// damage here so real Pikmin hits reach mHealth; no damage is injected.
	if (actor->mStoredDamage > 0.0f) {
		state.healthAsserted = true; // first natural damage: stop re-asserting
		actor->makeDamaged();
	}

	if (actor->mHealth <= 0.0f && state.state != p2kochappyfsm::STATE_DEAD
	    && state.state != p2kochappyfsm::STATE_PRESS) {
		enter(actor, state, p2kochappyfsm::STATE_DEAD);
	}
	// EnemyBase Earthquake/Fit suspends doUpdate and the current motion. Keep
	// this source FSM's state clock and one-shot events frozen while its existing
	// registered receiver consumes bounce/Fit. Natural damage/death above still
	// runs, and source Red10s/Orange5s remain owned by stun registration.
	if (state.stunPaused) {
		const float roll = pc_p2_kochappy_stun_needs_fit_roll(actor) ? NSystem::random() : 1.0f;
		if (!pc_p2_kochappy_stun_step(actor, dt, roll)) return;
		finishStun(actor, state);
	}
	state.stateTime += dt;

	// Source StateWait/StateWalk acquire the nearest target and store it on the
	// enemy (`enemy->mTargetCreature = target`); the host equivalent is the
	// creature pointer slot used by the Pikmin attack response.
	Creature* target = nearestCreature(pos, state.params.sight);
	if (target) {
		actor->setCreaturePointer(0, target);
	} else {
		actor->clearCreaturePointer(0);
	}
	const bool engaged = target && distXZ(target->getPosition(), pos) <= state.params.attackRange;
	const bool flickWanted = !engaged && nearestPiki(pos, FLICK_CONTACT_RADIUS) != nullptr;

	switch (state.state) {
	case p2kochappyfsm::STATE_WAIT: {
		stop(actor);
		if (target && attackReady(pos, state.heading, target, state)) {
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
		if (target && attackReady(pos, state.heading, target, state)) {
			enter(actor, state, p2kochappyfsm::STATE_ATTACK);
			break;
		}
		if (!target || distXZ(target->getPosition(), pos) > state.params.sight) {
			enter(actor, state, p2kochappyfsm::STATE_TURN_TO_HOME);
			break;
		}
		if (flickWanted) {
			state.returnState = p2kochappyfsm::STATE_TURN;
			enter(actor, state, p2kochappyfsm::STATE_FLICK);
			break;
		}
		if (turnTo(actor, state, target->getPosition(), dt, attackAngleRadians(state))
		    || state.stateTime >= TURN_DURATION) {
			enter(actor, state, p2kochappyfsm::STATE_WALK);
		}
		break;
	}
	case p2kochappyfsm::STATE_WALK: {
		if (target && attackReady(pos, state.heading, target, state)) {
			enter(actor, state, p2kochappyfsm::STATE_ATTACK);
			break;
		}
		if (!target || distXZ(target->getPosition(), pos) > state.params.sight) {
			enter(actor, state, p2kochappyfsm::STATE_TURN_TO_HOME);
			break;
		}
		if (flickWanted) {
			state.returnState = p2kochappyfsm::STATE_WALK;
			enter(actor, state, p2kochappyfsm::STATE_FLICK);
			break;
		}
		if (distXZ(pos, state.home) > state.params.territory) {
			enter(actor, state, p2kochappyfsm::STATE_TURN_TO_HOME);
			break;
		}
		walkTo(actor, state, target->getPosition(), dt);
		break;
	}
	case p2kochappyfsm::STATE_TURN_TO_HOME: {
		stop(actor);
		if (distXZ(pos, state.home) < state.params.homeRadius) {
			enter(actor, state, p2kochappyfsm::STATE_WAIT);
			break;
		}
		if (target && attackReady(pos, state.heading, target, state)) {
			enter(actor, state, p2kochappyfsm::STATE_ATTACK);
			break;
		}
		if (flickWanted) {
			state.returnState = p2kochappyfsm::STATE_TURN_TO_HOME;
			enter(actor, state, p2kochappyfsm::STATE_FLICK);
			break;
		}
		if (turnTo(actor, state, state.home, dt, attackAngleRadians(state))
		    || state.stateTime >= TURN_DURATION) {
			enter(actor, state, p2kochappyfsm::STATE_GO_HOME);
		}
		break;
	}
	case p2kochappyfsm::STATE_GO_HOME: {
		if (distXZ(pos, state.home) < state.params.homeRadius) {
			enter(actor, state, p2kochappyfsm::STATE_WAIT);
			break;
		}
		if (target && attackReady(pos, state.heading, target, state)) {
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
			// Source attackNavi (kochappyState.cpp:1403-1406) bites the captain
			// only; Pikmin are eaten by the mouth slot, never damaged here.
			for (Navi* navi : pc_p2_navis()) {
				if (navi->isAlive() && distXZ(navi->getPosition(), pos) < state.params.attackHitRange) {
					navi->stimulate(InteractAttack(actor, nullptr, state.params.attackDamage, false));
					std::printf("P2_KOCHAPPY_ATTACK generator=%u frame=%.0f damage=%.0f\n", generator,
					            ATTACK_EVENT_FRAME, state.params.attackDamage);
					std::fflush(stdout);
				}
			}
			// Source eatPikmin (KEYEVENT_2): mouth-slot eat (pc_p2_chappy_mouth.h).
			const EatStats eat = doEat(actor, state, generator);
			// #884 geometry fields: see pc_p2_chappy.cpp printDiag (same meanings).
			// Red1 and Orange44 share the Kochappy model/skeleton and exact kamu
 // slot table (KochappyBase::initMouthSlots); keep this family geometry.
 const p2chappymouth::Profile* prof = p2chappymouth::profileForSource(44);
			const float tdist = target ? distXZ(target->getPosition(), pos) : -1.0f;
			const float tang  = target ? wrapPi(std::atan2(target->getPosition().x - pos.x, target->getPosition().z - pos.z)
			                                    - state.heading) * 180.0f / PI
			                           : 0.0f;
			std::printf("P2_KOCHAPPY_EAT generator=%u frame=%.0f eaten=%d slot=%d captured=%d nearest_behind=%d "
			            "refused_no_host=%d host_slots=%d closest=%.1f closest_local=%.1f,%.1f,%.1f "
			            "slot_radius=%.1f reach=%.1f front=%d stuck_self=%d eligible_min=%d heading_deg=%.1f "
			            "draw_yaw_deg=%.1f scale=%.2f target_kind=%c target_dist=%.1f closest_frame=%d closest_slot=%d "
			            "target_ang_deg=%.1f\n",
			            generator, ATTACK_EVENT_FRAME, eat.captured > 0 ? 1 : 0, eat.freeBefore > 0 ? 1 : 0,
			            eat.captured, eat.nearestBehind ? 1 : 0, eat.refusedNoHost, eat.hostSlots, eat.diag.closest,
			            eat.diag.closestLocal.x, eat.diag.closestLocal.y, eat.diag.closestLocal.z,
			            prof ? p2chappymouth::effectiveRadius(*prof) : 0.0f, prof ? p2chappymouth::maxReach(*prof) : 0.0f,
			            eat.diag.front, eat.diag.stuckSelf, eat.diag.eligibleMin, eat.headingDeg, eat.drawYawDeg,
			            actor->mSRT.s.x,
			            !target ? '-' : (!target->isPiki() ? 'n' : (target->getStickObject() == actor ? 's' : 'p')),
			            tdist, eat.diag.closestFrame, eat.diag.closestSlot, tang);
			std::fflush(stdout);
		}
		if (!state.swallowFired && state.stateTime * 30.0f >= SWALLOW_EVENT_FRAME) {
			state.swallowFired = true;
			int whitePoisoned = 0;
			const int swallowed = doSwallow(actor, state, whitePoisoned);
			std::printf("P2_KOCHAPPY_SWALLOW generator=%u frame=%.0f swallowed=%d white=%d\n",
			            generator, SWALLOW_EVENT_FRAME, swallowed, whitePoisoned);
			std::fflush(stdout);
		}
		if (state.stateTime >= ATTACK_DURATION) {
			if (!target) {
				enter(actor, state, p2kochappyfsm::STATE_TURN_TO_HOME);
			} else if (attackReady(pos, state.heading, target, state)) {
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
            // Original StatePress goes straight to source Demo/kill at END.
            if(state.original){if(!state.died){state.died=true;actor->pcEscapeNow();adoptRedCorpse(actor);}return;}
			enter(actor, state, p2kochappyfsm::STATE_DEAD);
		}
		break;
	}
	case p2kochappyfsm::STATE_DEAD: {
		stop(actor);
		if (!state.deadLogged) {
			state.deadLogged = true;
			std::printf("P2_KOCHAPPY_DEAD generator=%u source_id=%d health=%.1f\n", generator, state.sourceId, actor->mHealth);
			std::fflush(stdout);
		}
		if (!state.died && state.stateTime >= DEAD_DURATION) {
			state.died = true;
			std::printf("P2_KOCHAPPY_CORPSE generator=%u source_id=%d native=host_escape_now\n", generator, state.sourceId);
			std::fflush(stdout);
			// die() alone only arms mDeadState; dieSoon() normally runs inside
			// doAI, which this module suppresses. pcEscapeNow() finalizes the
			// death (carcass birth) outside doAI (teki.h family-lane helper #219).
            const bool red = state.sourceId == 1;
            actor->pcEscapeNow();
            if (red) {
                adoptRedCorpse(actor);
                return; // native teardown may have forgotten the FSM entry.
            }
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
