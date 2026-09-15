// Unmarked Spectralids (ShijimiChou, EnemyID 77) bounded source lifecycle for
// the lane-15 flying remainder (#166). Implements the source
// shijimiChouState.cpp machine Wait/Fly/Fall/Dead/Leave/Rest on the private P1
// Chappy placement vehicle, driven by p2-shijimi-bank.txt /
// p2-shijimi-actors.txt written by the lane arena. Source revision
// 632af93787b9c95b63f0c13be32b161375ce3a96 (include/Game/Entities/ShijimiChou.h,
// src/plugProjectMorimuraU/shijimiChouState.cpp, shijimiChou.cpp).
//
// Port adaptations (recorded, not retail-faithful):
//   * The P1 engine has no Spectralid group factory. The private arena stages a
//     small cluster on independent Chappy generators; the lowest generator is
//     the group leader, and members trace the live leader position (source
//     setTraceGoal) instead of the P2 group-owner offset formula. The full
//     25-member group and the sound cluster are documented gaps.
//   * The private fixture stages a plant-origin group so the fly duration is the
//     source plant value (fp08) and genItem's plant term holds; the fp02 nectar
//     roll is computed and logged. The source StartsOfu/Fall latch (a Pikmin
//     sticking) has no P1 host equivalent, so Fall begins at health <= 0.
//   * genItem fires at the source dead-animation end and births one P1 nectar
//     item; the mEfxDown feather effect, PS SEs and PS cluster are not ported.
//   * Battle: source damageCallBack returns false; the P1 host retains its
//     corpse handoff. No lethal injection is performed here.
// Every hook is a no-op for unregistered actors.
#include "pc_p2_shijimi.h"
#include "pc_p2_shijimi_policy.h"
#include "pc_p2_enemy.h"
#include "pc_p2_sheargrub.h"
#include "pc_p2_qurione.h"
#include "teki.h"
#include "system.h"
#include "MapMgr.h"
#include "Generator.h"
#include "Shape.h"
#include "Texture.h"
#include "Material.h"
#include "gameflow.h"
#include "Graphics.h"
#include "Camera.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "ItemMgr.h"
#include "ObjType.h"
#include <map>
#include <set>
#include <vector>
#include <string>
#include <fstream>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>

namespace {
enum SState { SS_WAIT = 0, SS_FLY = 1, SS_FALL = 2, SS_DEAD = 3, SS_LEAVE = 4, SS_REST = 5 };

const char* sStateName(SState s) {
	switch (s) {
	case SS_WAIT: return "wait";
	case SS_FLY: return "fly";
	case SS_FALL: return "fall";
	case SS_DEAD: return "dead";
	case SS_LEAVE: return "leave";
	case SS_REST: return "rest";
	default: return "null";
	}
}

// Source enemyparm.txt / ShijimiChou.h retail values (GPVE01 rev 0).
constexpr float LIFE = 200.0f;                 // general fp00
constexpr float MOVE_SPEED = 150.0f;           // general fp06
constexpr float TERRITORY = 250.0f;            // general fp09
constexpr float MAX_FLY_TIME = 250.0f;         // proper fp01 (frames)
constexpr float MAX_FLY_TIME_PLANT = 250.0f;   // proper fp08 (frames)
constexpr float NECTAR_RATE = 0.2f;            // proper fp02
constexpr float FLIGHT_HEIGHT = 70.0f;         // proper fp03
constexpr float PITCH_RATE = 0.02f;            // proper fp04
constexpr float PITCH_AMP_RATE = 2.0f;         // proper fp05
constexpr float ENEMY_FLY_TIME = 60.0f;        // source StateFly::exec:125-127
constexpr float NEAR_PIKMIN_RADIUS = 180.0f;   // source StateWait::exec:72
constexpr float NEAR_PIKMIN_HEIGHT = 150.0f;   // source StateWait::exec:72
constexpr float MAX_FALL_SPEED = 70.0f;        // Parms mMaxFallSpeed
constexpr float HORIZ_FALL_SCATTER = 5.0f;     // Parms mHorizFallScatter
constexpr float FALL_ROTATE_RATE = 0.3f;       // Parms mFallRotateRate
constexpr float LEAVE_SPEED_FACTOR = 0.8f;     // Parms mLeaveInitSpeedFactor
constexpr float WAIT_FRAMES = 10.0f;           // source StateWait mWaitTimer > 10
constexpr float REST_TIME = 2.0f;              // host-bounded (source 30+100*rand frames)
constexpr float LEAVE_TIME = 4.0f;             // host-bounded departure cleanup
constexpr float ARRIVE_SQ = 1000.0f;           // source sqrDistanceXZ < 1000
// Spawn source is fixed for this private slice: plant-origin group.
constexpr int SPAWN_SOURCE_PLANTS = 2;

struct Shijimi {
	SState state = SS_WAIT;
	std::uint32_t generator = 0;
	float stateTime = 0.0f;
	float heading = 0.0f;
	float pitchPhase = 0.0f;
	float flyTime = 0.0f;
	float fallTimer = 0.0f;
	float fallDir = 0.0f;
	bool isLeader = false;
	bool nectarDropped = false;
	bool killed = false;
	bool deadLogged = false;
	float logTimer = 0.0f;
	Vector3f home;
	Vector3f goal;
	Vector3f fallStart;
	std::string clip = "move";
	float phase = 0.0f;
};

std::map<std::string, std::vector<Shape*>> clips;
std::map<std::string, p2animation::Clip> timing;
std::map<PelletView*, Shijimi> actors;
std::map<std::uint32_t, BTeki*> tekis;
std::uint32_t leaderGenerator = 0;
bool ready = false;
bool logged[2] = {false, false};

float wrapPi(float a) {
	while (a > PI) a -= TAU;
	while (a < -PI) a += TAU;
	return a;
}
float distXZ(const Vector3f& a, const Vector3f& b) {
	const float dx = a.x - b.x, dz = a.z - b.z;
	return std::sqrt(dx * dx + dz * dz);
}
float clipDuration(const std::string& name) {
	auto it = timing.find(name);
	return it == timing.end() || it->second.duration <= 0 ? 1.0f : float(it->second.duration) / 30.0f;
}
float groundHeight(const Vector3f& pos) {
	return mapMgr ? mapMgr->getMinY(pos.x, pos.z, true) : pos.y;
}
Piki* nearestPikmin(const Vector3f& pos, float radius, float height) {
	Piki* best = nullptr;
	float bestSq = radius * radius;
	if (pikiMgr) {
		Iterator it(pikiMgr);
		CI_LOOP(it) {
			Piki* p = static_cast<Piki*>(*it);
			if (!p || !p->isAlive()) continue;
			const Vector3f q = p->getPosition();
			if (std::fabs(q.y - pos.y) > height) continue;
			const float dx = q.x - pos.x, dz = q.z - pos.z;
			const float d = dx * dx + dz * dz;
			if (d < bestSq) { bestSq = d; best = p; }
		}
	}
	return best;
}
void enter(Shijimi& s, SState state, const char* clip) {
	s.state = state;
	s.stateTime = 0.0f;
	if (clip) s.clip = clip;
}
// Source setNextGoal: random goal around the home position inside the territory
// radius with the source `+50*sin` vertical term (shijimiChou.cpp).
void setNextGoal(Shijimi& s) {
	float radius = TERRITORY;
	if (SPAWN_SOURCE_PLANTS == 2) radius = 100.0f;
	radius *= 0.5f * gsys->getRand(1.0f) + 0.5f;
	const float angle = TAU * gsys->getRand(1.0f);
	const float sn = std::sin(angle);
	s.goal = Vector3f(s.home.x + radius * sn, s.home.y + 50.0f * sn,
	                  s.home.z + radius * std::cos(angle));
}
// Host flight hold: keep the actor near FLIGHT_HEIGHT above the floor with the
// source pitch bob. The source fly() eases y toward mGoalPosition.y.
void setHeightVelocity(BTeki* a, Shijimi& s) {
	const Vector3f pos = a->getPosition();
	const float groundY = groundHeight(pos);
	s.pitchPhase += PITCH_RATE;
	if (s.pitchPhase > TAU) s.pitchPhase -= TAU;
	const float idealHeight = FLIGHT_HEIGHT + PITCH_AMP_RATE * 2.5f * std::sin(s.pitchPhase);
	a->mVelocity.y = (groundY + idealHeight - pos.y);
}
void turnAndFly(BTeki* a, Shijimi& s, const Vector3f& target, float dt) {
	const Vector3f pos = a->getPosition();
	const float desired = std::atan2(target.x - pos.x, target.z - pos.z);
	const float maxTurn = 2.0f * dt;
	float diff = wrapPi(desired - s.heading);
	if (diff > maxTurn) diff = maxTurn;
	if (diff < -maxTurn) diff = -maxTurn;
	s.heading = wrapPi(s.heading + diff);
	a->setDirection(s.heading);
	const Vector3f drive(std::sin(s.heading) * MOVE_SPEED, 0.0f,
	                     std::cos(s.heading) * MOVE_SPEED);
	a->inputDrive(drive);
	a->mVelocity.x = drive.x;
	a->mVelocity.z = drive.z;
	setHeightVelocity(a, s);
}
// Source Obj::fly: ease toward the goal at move speed; pick a new goal when
// within sqrDistanceXZ < 1000. Members trace the live leader (setTraceGoal).
void fly(BTeki* a, Shijimi& s, float dt) {
	const Vector3f pos = a->getPosition();
	if (!s.isLeader) {
		auto l = tekis.find(leaderGenerator);
		if (l != tekis.end() && l->second) s.goal = l->second->getPosition();
	} else if ((pos.x - s.goal.x) * (pos.x - s.goal.x)
	           + (pos.z - s.goal.z) * (pos.z - s.goal.z) < ARRIVE_SQ) {
		setNextGoal(s);
	}
	if (distXZ(pos, s.goal) < 1.0f) {
		a->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
		a->mVelocity.x = 0.0f;
		a->mVelocity.z = 0.0f;
		setHeightVelocity(a, s);
		return;
	}
	turnAndFly(a, s, s.goal, dt);
}
// Source Obj::leaveInit: the leader departs 500 units behind the captain.
void leaveInit(BTeki* a, Shijimi& s, float dt) {
	if (s.isLeader && naviMgr) {
		Navi* n = naviMgr->getNavi();
		if (n) {
			const Vector3f navi = n->getPosition();
			const float angle = n->mFaceDirection;
			const Vector3f target(navi.x - 500.0f * std::sin(angle), navi.y,
			                      navi.z - 500.0f * std::cos(angle));
			turnAndFly(a, s, target, dt);
			a->mVelocity.x *= LEAVE_SPEED_FACTOR;
			a->mVelocity.z *= LEAVE_SPEED_FACTOR;
			return;
		}
	}
	fly(a, s, dt);
}
// Source Obj::genItem: outside Piklopedia, a plant origin or a passing nectar
// roll births one Honey item. Yellow has no first-spray flag gate. Exactly-once.
void genItem(BTeki* a, Shijimi& s) {
	if (s.nectarDropped) return;
	s.nectarDropped = true;
	const std::uint32_t generator = a->mGenerator ? a->mGenerator->_70 : 0u;
	const bool plant = SPAWN_SOURCE_PLANTS == 2;
	const bool roll = !(gsys->getRand(1.0f) > NECTAR_RATE);
	std::printf("P2_SHIJIMI_NECTAR generator=%u source_id=77 plant=%d roll=%d\n",
	            generator, int(plant), int(roll));
	if (!(plant || roll) || !itemMgr) { std::fflush(stdout); return; }
	const Vector3f pos = a->getPosition();
	Creature* drop = itemMgr->birth(OBJTYPE_Water);
	if (!drop) { std::fflush(stdout); return; }
	drop->init(pos);
	drop->startAI(0);
	std::printf("P2_SHIJIMI_HONEY generator=%u source_id=77\n", generator);
	std::fflush(stdout);
}
void setPhase(Shijimi& s) {
	const float duration = clipDuration(s.clip);
	s.phase = s.stateTime / (duration > 0.0f ? duration : 1.0f);
	if (s.phase > 1.0f) s.phase = 1.0f;
}
} // namespace

void pc_p2_shijimi_reset() {
	clips.clear();
	timing.clear();
	actors.clear();
	tekis.clear();
	leaderGenerator = 0;
	ready = false;
	logged[0] = logged[1] = false;
}
void pc_p2_shijimi_forget(BTeki* actor) {
	actors.erase(static_cast<PelletView*>(actor));
	for (auto it = tekis.begin(); it != tekis.end(); ) {
		if (it->second == actor) it = tekis.erase(it);
		else ++it;
	}
}
const char* pc_p2_shijimi_name(PelletView* actor) {
	return actors.count(actor) ? "Unmarked Spectralids (source FSM)" : nullptr;
}

float pc_p2_shijimi_param_f(const BTeki* actor, int idx, float fallback) {
	if (!ready || !actors.count(static_cast<PelletView*>(const_cast<BTeki*>(actor)))) return fallback;
	if (idx == TPF_Life) return LIFE;
	if (idx == TPF_LifeRecoverRate) return 0.0f;
	switch (idx) {
	case TPF_VisibleRange:
	case TPF_VisibleAngle:
	case TPF_AttackableRange:
	case TPF_AttackableAngle:
	case TPF_AttackRange:
	case TPF_AttackHitRange:
	case TPF_AttackPower:
	case TPF_DangerTerritoryRange:
	case TPF_SafetyTerritoryRange:
		return 0.0f;
	default:
		return fallback;
	}
}

void pc_p2_shijimi_setup() {
	pc_p2_shijimi_reset();
	std::ifstream bank("p2-shijimi-bank.txt"), bindings("p2-shijimi-actors.txt");
	if (!bank && !bindings) return;
	if (!tekiMgr) return;
	std::vector<p2animation::Clip> manifest;
	std::set<std::uint32_t> wanted;
	if (!bank || !bindings || !p2shijimi::bank(bank, manifest) || !p2shijimi::bindings(bindings, wanted)) std::abort();
	// Reject identity overlap and unresolved/duplicate generator IDs before loading.
	std::vector<Teki*> selected;
	std::set<std::uint32_t> seen;
	Iterator it(tekiMgr);
	CI_LOOP(it) {
		Teki* actor = static_cast<Teki*>(*it);
		if (!actor || !actor->mGenerator || !wanted.count(actor->mGenerator->_70)) continue;
		if (!seen.insert(actor->mGenerator->_70).second || actor->mTekiType != TEKI_Chappy
		    || pc_p2_enemy_name(actor) || pc_p2_sheargrub_name(actor) || pc_p2_qurione_name(actor)) {
			std::abort();
		}
		selected.push_back(actor);
	}
	if (seen != wanted) std::abort();
	size_t total = 0, poses = 0;
	std::vector<unsigned char> reference;
	for (const auto& clip : manifest) {
		size_t clipBytes = 0;
		for (int i = 0; i < clip.count; ++i) {
			char path[160];
			std::snprintf(path, sizeof(path), "assets/dataDir/courses/pikmin2room/shijimi_%s_%02d.mod", clip.name.c_str(), i);
			std::ifstream file(path, std::ios::binary | std::ios::ate);
			if (!file) std::abort();
			auto bytes = file.tellg();
			if (bytes <= 0 || size_t(bytes) > p2animation::ClipBytes - clipBytes || size_t(bytes) > p2animation::TotalBytes - total) std::abort();
			clipBytes += size_t(bytes);
			total += size_t(bytes);
			file.seekg(0);
			std::vector<unsigned char> data(size_t(bytes), 0), resources;
			if (!file.read(reinterpret_cast<char*>(data.data()), bytes) || !p2animation::resources(data, resources)) std::abort();
			if (!reference.empty() && reference != resources) std::abort();
			reference = resources;
		}
	}
	const auto started = std::chrono::steady_clock::now();
	Shape* shared = nullptr;
	int attachments = 0;
	for (const auto& clip : manifest) {
		timing[clip.name] = clip;
		for (int i = 0; i < clip.count; ++i) {
			char path[128];
			std::snprintf(path, sizeof(path), "courses/pikmin2room/shijimi_%s_%02d.mod", clip.name.c_str(), i);
			Shape* shape = gameflow.loadShape(path, true);
			if (!shape) std::abort();
			if (!shared) {
				shared = shape;
				for (int t = 0; t < shape->mTexAttrCount; ++t) {
					if (shape->mTexAttrList[t].mTexture) { shape->mTexAttrList[t].mTexture->attach(); ++attachments; }
				}
			} else {
				if (shape->mMaterialCount != shared->mMaterialCount || shape->mTexAttrCount != shared->mTexAttrCount
				    || shape->mTevInfoCount != shared->mTevInfoCount) {
					std::abort();
				}
				for (int j = 0; j < shape->mTotalMatpolyCount; ++j) {
					auto* poly = shape->mMatpolyList[j];
					if (!poly || !poly->mMaterial) continue;
					int material = -1;
					for (int m = 0; m < shape->mMaterialCount; ++m) {
						if (poly->mMaterial == &shape->mMaterialList[m]) material = m;
					}
					if (material < 0) std::abort();
					poly->mMaterial = &shared->mMaterialList[material];
				}
				shape->mMaterialList = shared->mMaterialList;
				shape->mTexAttrList = shared->mTexAttrList;
				shape->mTevInfoList = shared->mTevInfoList;
			}
			clips[clip.name].push_back(shape);
			++poses;
		}
	}
	leaderGenerator = wanted.empty() ? 0u : *wanted.begin();
	for (Teki* actor : selected) {
		Shijimi& s = actors[static_cast<PelletView*>(actor)];
		tekis[actor->mGenerator->_70] = actor;
		const Vector3f pos = actor->getPosition();
		s.generator = actor->mGenerator->_70;
		s.home = pos;
		s.goal = pos;
		s.heading = actor->getDirection();
		s.isLeader = actor->mGenerator->_70 == leaderGenerator;
		s.state = SS_WAIT;
		s.clip = "move";
		actor->mHealth = LIFE;
		std::printf("P2_SHIJIMI_BIND generator=%u source_id=77 visual_only=0\n", s.generator);
		std::printf("P2_ENEMY_READY species=ShijimiChou native_family=Chappy generator=%u x=%.7f y=%.7f z=%.7f "
		            "health=%.1f max_health=%.1f behavior=native source_FSM=implemented attack=none reward=P1_nectar "
		            "source=plants leader=%d group_count=%zu\n",
		            s.generator, pos.x, pos.y, pos.z, actor->mHealth, LIFE, int(s.isLeader), selected.size());
		std::printf("P2_SHIJIMI_STATE generator=%u state=wait\n", s.generator);
		std::fflush(stdout);
	}
	std::printf("P2_SHIJIMI_BANK poses=%zu mod_bytes=%zu texture_attach_calls=%d load_seconds=%.3f\n",
	            poses, total, attachments, std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count());
	ready = true;
}

bool pc_p2_shijimi_suppress_ai(const BTeki* actor) {
	return ready && actors.count(static_cast<PelletView*>(const_cast<BTeki*>(actor))) != 0;
}

void pc_p2_shijimi_update(BTeki* actor) {
	if (!ready) return;
	auto it = actors.find(static_cast<PelletView*>(actor));
	if (it == actors.end()) return;
	Shijimi& s = it->second;
	const float dt = gsys->getFrameTime();
	if (dt <= 0.0f || dt > 0.5f) return;
	const std::uint32_t gen = s.generator;
	const Vector3f pos = actor->getPosition();
	s.stateTime += dt;

	// Source health endpoint -> Fall; no P1 stick latch exists on this host.
	if (actor->mHealth <= 0.0f && s.state != SS_FALL && s.state != SS_DEAD
	    && s.state != SS_LEAVE) {
		if (!s.deadLogged) {
			s.deadLogged = true;
			std::printf("P2_SHIJIMI_DEAD generator=%u source_id=77 health=0\n", gen);
			std::fflush(stdout);
		}
		s.fallStart = pos;
		s.fallTimer = 0.0f;
		s.fallDir = 0.0f;
		std::printf("P2_SHIJIMI_STATE generator=%u state=fall\n", gen);
		enter(s, SS_FALL, "move");
	}

	switch (s.state) {
	case SS_WAIT: {
		actor->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
		actor->mVelocity.x = 0.0f;
		actor->mVelocity.z = 0.0f;
		setHeightVelocity(actor, s);
		if (s.stateTime * 30.0f > WAIT_FRAMES) {
			if (!s.isLeader) {
				std::printf("P2_SHIJIMI_STATE generator=%u state=fly\n", gen);
				enter(s, SS_FLY, "move");
			} else if (nearestPikmin(pos, NEAR_PIKMIN_RADIUS, NEAR_PIKMIN_HEIGHT)) {
				std::printf("P2_SHIJIMI_STATE generator=%u state=fly\n", gen);
				enter(s, SS_FLY, "move");
			} else {
				setNextGoal(s);
			}
		}
		break;
	}
	case SS_FLY: {
		// Source checkFlyStart: the leader always flies; members fly once the
		// leader has left Wait.
		bool flyStart = s.isLeader;
		if (!s.isLeader) {
			auto lk = tekis.find(leaderGenerator);
			if (lk != tekis.end() && lk->second) {
				auto l = actors.find(static_cast<PelletView*>(lk->second));
				if (l != actors.end()) flyStart = l->second.state != SS_WAIT;
			}
		}
		if (flyStart) s.flyTime += dt * 30.0f;
		const float flyMax = MAX_FLY_TIME_PLANT; // plant-origin group
		if (s.flyTime > flyMax) {
			std::printf("P2_SHIJIMI_STATE generator=%u state=leave\n", gen);
			enter(s, SS_LEAVE, "move");
			break;
		}
		fly(actor, s, dt);
		break;
	}
	case SS_FALL: {
		// Source fallBehavior: capped sink with the horizontal scatter.
		Vector3f vel = actor->mVelocity;
		if (vel.y < -MAX_FALL_SPEED) vel.y = -MAX_FALL_SPEED;
		if (vel.y > -20.0f) vel.y = -20.0f;
		s.fallDir += FALL_ROTATE_RATE;
		if (s.fallDir > TAU) s.fallDir -= TAU;
		vel.x = 0.0f;
		vel.z = 0.0f;
		actor->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
		actor->mVelocity = vel;
		actor->mSRT.t.x = HORIZ_FALL_SCATTER * 0.1f * std::sin(s.fallDir) + s.fallStart.x;
		actor->mSRT.t.z = 0.5f * HORIZ_FALL_SCATTER * 0.1f * std::sin(s.fallDir) + s.fallStart.z;
		++s.fallTimer;
		if (pos.y < 10.0f + groundHeight(pos) || s.fallTimer > 100.0f) {
			std::printf("P2_SHIJIMI_STATE generator=%u state=dead\n", gen);
			enter(s, SS_DEAD, "dead");
		}
		break;
	}
	case SS_DEAD: {
		actor->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
		actor->mVelocity.x = 0.0f;
		actor->mVelocity.z = 0.0f;
		if (s.stateTime >= clipDuration("dead")) {
			genItem(actor, s);
			if (!s.killed) {
				s.killed = true;
				std::printf("P2_SHIJIMI_KILL generator=%u source_id=77\n", gen);
				std::printf("P2_SHIJIMI_CORPSE generator=%u source_id=77 native=host_die\n", gen);
				std::fflush(stdout);
				actor->die();
			}
		}
		break;
	}
	case SS_LEAVE: {
		leaveInit(actor, s, dt);
		if (s.stateTime >= LEAVE_TIME && !s.killed) {
			s.killed = true;
			std::printf("P2_SHIJIMI_KILL generator=%u source_id=77\n", gen);
			std::printf("P2_SHIJIMI_CORPSE generator=%u source_id=77 native=host_die\n", gen);
			std::fflush(stdout);
			actor->die();
		}
		break;
	}
	case SS_REST: {
		actor->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
		actor->mVelocity.x = 0.0f;
		actor->mVelocity.z = 0.0f;
		setHeightVelocity(actor, s);
		if (s.stateTime >= REST_TIME) {
			std::printf("P2_SHIJIMI_STATE generator=%u state=fly\n", gen);
			enter(s, SS_FLY, "move");
		}
		break;
	}
	default:
		break;
	}
	setPhase(s);
	s.logTimer += dt;
	if (s.logTimer >= 1.0f) {
		s.logTimer = 0.0f;
		std::printf("P2_SHIJIMI_POS generator=%u state=%s clip=%s phase=%.2f x=%.2f y=%.2f z=%.2f leader=%d fly=%.1f\n",
		            gen, sStateName(s.state), s.clip.c_str(), s.phase, pos.x, pos.y, pos.z,
		            int(s.isLeader), s.flyTime);
		std::fflush(stdout);
	}
}

bool pc_p2_shijimi_draw(BTeki* actor, Graphics& gfx, const Matrix4f& matrix, bool corpse) {
	auto it = actors.find(static_cast<PelletView*>(actor));
	if (it == actors.end()) return false;
	if (!logged[corpse ? 1 : 0]) { std::printf("P2_SHIJIMI_DRAW corpse=%d\n", int(corpse)); logged[corpse ? 1 : 0] = true; }
	if (corpse) return false;
	const Shijimi& s = it->second;
	auto bankIt = clips.find(s.clip);
	if (bankIt == clips.end() || bankIt->second.empty()) return false;
	const p2animation::Clip& clip = timing.at(s.clip);
	size_t index = clip.index(s.phase, false);
	if (index >= bankIt->second.size()) index = bankIt->second.size() - 1;
	Shape* shape = bankIt->second[index];
	shape->updateAnim(gfx, matrix, nullptr, actor);
	shape->drawshape(gfx, *gfx.mCamera, nullptr);
	return true;
}
