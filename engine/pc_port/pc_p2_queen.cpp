// Empress Bulblax (Queen, enemy ID 30) sampled actor (#256, parent #172).
// Extends the #235 sampled display bank with a behavior FSM mirrored from
// experimental/pikmin2_bulblax_behavior.py (#227). Actor-local receivers
// only: generic physics/damage, captain states, manager/heap lifetime and
// save/reward code are untouched. HoH crash rocks are recorded but disabled.
#include "pc_p2_queen.h"
#include "pc_p2_queen_policy.h"
#include "pc_p2_animation.h"
#include "pc_bbft.h"
#include "Shape.h"
#include "Texture.h"
#include "Graphics.h"
#include "Camera.h"
#include "gameflow.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "NaviMgr.h"
#include "Navi.h"
#include "Interactions.h"
#include <SDL.h>
#include <map>
#include <set>
#include <vector>
#include <string>
#include <fstream>
#include <cmath>
#include <cstdio>
#include <cstdlib>
namespace {
constexpr float Tick = 1.0f / 30.0f; // 30 Hz bounded behavior clock
constexpr float QueenMoveSpeed = 125.0f; // general fp06 disc
constexpr int StuckMax = 32;             // bounded stuck-Pikmin receiver set
p2queen::ActorConfig config;
std::map<size_t, std::vector<Shape*>> shapes; // clip index -> pose shapes
size_t totalBytes = 0;

struct Larva {
	bool active = false;
	int state = 2; // born
	float health = p2queen::BabyHealth;
	float x = 0, y = 0, z = 0, yaw = 0, vx = 0, vy = 0, vz = 0;
	float frame = 0;
	bool landed = false;
	bool loggedDead = false;
};
struct Queen {
	p2queen::Placement cfg;
	p2queen::VariantInfo info;
	int state = p2queen::Sleep;
	float frame = 0;
	float x = 0, y = 0, z = 0, yaw = 0;
	float health = p2queen::HealthDefault;
	// rolling
	bool rollingLeft = false;
	bool firstRoll = true;
	float dirX = 0, dirZ = 1, originX = 0, originZ = 0, rollElapsed = 0;
	// receivers
	Piki* stuck[StuckMax];
	int stuckCount = 0;
	int blows = 0;
	int flickTier = 0;
	bool hitUp = false;
	// timers / larvae
	float idleSec = 0, birthTimer = 0;
	bool roomFlag = true;
	std::vector<Larva> larvae; // fixed-size pool, allocated once at setup
	bool loggedState[8] = {};
	bool loggedAtari = false;
	bool loggedRocks = false;
};
std::vector<Queen> queens;
unsigned clockLast = 0;
float clockAcc = 0;

void fail() {
	std::fputs("P2_QUEEN_ACTOR invalid profile/model\n", stderr);
	std::abort();
}
const char* stateClip(int state, bool rollingLeft) {
	switch (state) {
	case p2queen::Dead: return "dead";
	case p2queen::Sleep: return "sleep";
	case p2queen::Wait: return "wait1";
	case p2queen::Damage: return "damage";
	case p2queen::Flick: return "flick";
	case p2queen::Rolling: return rollingLeft ? "rolling_l" : "rolling_r";
	case p2queen::Born: return "born";
	}
	return "wait1";
}
Shape* load(const std::string& name, std::vector<unsigned char>& reference, size_t& clipBytes) {
	std::ifstream in("assets/dataDir/courses/pikmin2room/" + name, std::ios::binary | std::ios::ate);
	if (!in) fail();
	auto size = in.tellg();
	if (size <= 0 || size > 1024 * 1024 || clipBytes + size_t(size) > 1024 * 1024 || totalBytes + size_t(size) > 16 * 1024 * 1024)
		fail();
	clipBytes += size_t(size);
	totalBytes += size_t(size);
	in.seekg(0);
	std::vector<unsigned char> data(size_t(size), 0), resources;
	if (!in.read(reinterpret_cast<char*>(data.data()), size) || !p2animation::resources(data, resources)) fail();
	if (!reference.empty() && reference != resources) fail();
	reference = resources;
	Shape* shape = gameflow.loadShape(("courses/pikmin2room/" + name).c_str(), true);
	if (!shape) fail();
	for (int i = 0; i < shape->mTexAttrCount; ++i)
		if (shape->mTexAttrList[i].mTexture) shape->mTexAttrList[i].mTexture->attach();
	return shape;
}
const char* speciesName(int enemy) { return enemy == 30 ? "Queen" : "Baby"; }

void enter(Queen& q, int state) {
	q.state = state;
	q.frame = 0;
	if (state == p2queen::Wait) q.idleSec = 0;
	if (state == p2queen::Rolling) q.rollElapsed = 0;
}

void spawnLarva(Queen& q) {
	for (auto& l : q.larvae) {
		if (l.active) continue;
		const float rad = q.yaw * 0.0174532925199433f;
		const float back = -p2queen::RootRadius; // body_end-equivalent: behind the Queen
		l = Larva{};
		l.active = true;
		l.x = q.x + std::sin(rad) * back;
		l.y = q.y;
		l.z = q.z + std::cos(rad) * back;
		l.yaw = q.yaw + 180.0f; // facing away
		const float lrad = l.yaw * 0.0174532925199433f;
		l.vx = std::sin(lrad) * p2queen::LaunchSpeed;
		l.vz = std::cos(lrad) * p2queen::LaunchSpeed;
		l.vy = p2queen::LaunchSpeed * 0.5f;
		std::printf("P2_QUEEN_LARVA id=%u xyz=%.6f,%.6f,%.6f yaw=%.3f launch_speed=50\n", q.cfg.id, l.x, l.y, l.z,
		            l.yaw);
		return;
	}
}

void flickStuck(Queen& q) {
	const float rad = q.yaw * 0.0174532925199433f;
	for (int i = 0; i < q.stuckCount; ++i) {
		Piki* p = q.stuck[i];
		if (!p || !p->isAlive()) continue;
		const Vector3f& pos = p->getPosition();
		const float dx = pos.x - q.x, dz = pos.z - q.z;
		const float facing = std::atan2(std::sin(rad), std::cos(rad));
		float rel = std::atan2(dx, dz) - facing;
		while (rel > 3.14159265f) rel -= 6.2831853f;
		while (rel < -3.14159265f) rel += 6.2831853f;
		// Approximate joint binding from the stick sector: front nose/head,
		// rear bod5 (reversed), sides bod1. Queen.cpp:324-345.
		const p2queen::Part part = std::fabs(rel) < 0.7853982f ? p2queen::Part::Nose
		                       : std::fabs(rel) > 2.3561945f ? p2queen::Part::Bod5
		                                                     : p2queen::Part::Bod1;
		const p2queen::FlickEffect effect = p2queen::flickEffect(part);
		float angle = std::atan2(dx, dz);
		if (effect == p2queen::FlickEffect::FlickReversed) angle += 3.14159265f;
		InteractFlick flick(nullptr, p2queen::ShakeKnockback, p2queen::ShakeDamage, angle);
		p->stimulate(flick);
	}
	std::printf("P2_QUEEN_FLICK id=%u shaken=%d knockback=300 damage=1 joints=nose/head/bod1 bod5=reversed\n", q.cfg.id,
	            q.stuckCount);
	q.stuckCount = 0;
	q.blows = 0;
	if (q.flickTier < 3) ++q.flickTier;
}

void pressScan(Queen& q) {
	if (!pikiMgr) return;
	Iterator it(pikiMgr);
	CI_LOOP(it) {
		Piki* p = static_cast<Piki*>(*it);
		if (!p || !p->isAlive() || p->getState() == PIKISTATE_Pressed) continue;
		const Vector3f& pos = p->getPosition();
		const float dx = pos.x - q.x, dz = pos.z - q.z;
		if (std::fabs(pos.y - q.y) > p2queen::PressHeightBand) continue;
		const float dist = std::sqrt(dx * dx + dz * dz);
		if (dist > p2queen::AttackRadius) continue;
		const float along = dist > 1.0e-6f ? (dx * q.dirX + dz * q.dirZ) / dist : 1.0f;
		if (std::acos(along > 1.0f ? 1.0f : along < -1.0f ? -1.0f : along)
		    > p2queen::AttackHitAngleDeg * 0.0174532925199433f)
			continue;
		InteractPress press(nullptr, p2queen::PressDamage);
		p->stimulate(press);
		std::printf("P2_QUEEN_PRESS id=%u damage=10 radius=150 angle=25 height_band=50\n", q.cfg.id);
	}
}

void receiveScan(Queen& q, float dt) {
	// Actor-local Pikmin-attack receiver: Pikmin inside the root collision
	// sphere and height band stick and land blows. Captain punches and purple
	// quake are never sampled: Queen is immune by construction (Queen.cpp:
	// 184-207), so those channels do not exist here.
	if (!pikiMgr || q.state == p2queen::Dead || q.state == p2queen::Rolling) return;
	Iterator it(pikiMgr);
	CI_LOOP(it) {
		Piki* p = static_cast<Piki*>(*it);
		if (!p || !p->isAlive()) continue;
		const Vector3f& pos = p->getPosition();
		const float dx = pos.x - q.x, dy = pos.y - q.y, dz = pos.z - q.z;
		if (dx * dx + dy * dy + dz * dz > p2queen::RootRadius * p2queen::RootRadius) continue;
		if (std::fabs(dy) > p2queen::PressHeightBand) continue;
		bool known = false;
		for (int i = 0; i < q.stuckCount; ++i)
			if (q.stuck[i] == p) known = true;
		if (known || q.stuckCount >= StuckMax) continue;
		q.stuck[q.stuckCount++] = p;
		++q.blows;
		q.hitUp = true;
		// Approximate per-blow Pikmin damage of 1 (part-only coefficient from
		// the policy; the P1 per-color blow strength is out of scope).
		q.health -= 1.0f * p2queen::damageFactor(q.state, p2queen::Attacker::PikminPart, false);
		if (q.health < 0.0f) q.health = 0.0f;
	}
	for (int i = 0; i < q.stuckCount; ++i) {
		Piki* p = q.stuck[i];
		if (!p || !p->isAlive()) {
			q.stuck[i] = q.stuck[--q.stuckCount];
			--i;
		}
	}
	(void)dt;
}

void tickLarva(Queen& q, Larva& l) {
	l.frame += 1.0f;
	if (l.state == 2) { // born: damp until landed, BabyState.cpp:107-127
		l.vx *= 0.95f;
		l.vz *= 0.95f;
		l.vy -= 980.0f * Tick;
		l.x += l.vx * Tick;
		l.y += l.vy * Tick;
		l.z += l.vz * Tick;
		if (l.y <= q.y) {
			l.y = q.y;
			l.landed = true;
		}
		const int next = p2queen::babyBornNext(l.landed, l.health);
		if (next >= 0) {
			l.state = next;
			l.frame = 0;
		}
	} else if (l.state == 3) { // move toward nearest target, BabyState.cpp:153-186
		Piki* best = nullptr;
		float bestDist = p2queen::BabySight;
		if (pikiMgr) {
			Iterator it(pikiMgr);
			CI_LOOP(it) {
				Piki* p = static_cast<Piki*>(*it);
				if (!p || !p->isAlive()) continue;
				const Vector3f& pos = p->getPosition();
				const float dx = pos.x - l.x, dz = pos.z - l.z;
				const float dist = std::sqrt(dx * dx + dz * dz);
				if (dist < bestDist) {
					bestDist = dist;
					best = p;
				}
			}
		}
		if (best) {
			const Vector3f& pos = best->getPosition();
			const float want = std::atan2(pos.x - l.x, pos.z - l.z) * 57.29577951308232f;
			float off = want - l.yaw;
			while (off > 180.0f) off -= 360.0f;
			while (off < -180.0f) off += 360.0f;
			const float step = off > 10.0f ? 10.0f : off < -10.0f ? -10.0f : off;
			l.yaw += step;
			const auto move = p2queen::babyMoveStep(off, 45.0f, p2queen::BabySpeed, bestDist, 30.0f, true);
			const float rad = l.yaw * 0.0174532925199433f;
			l.x += std::sin(rad) * move.first * Tick;
			l.z += std::cos(rad) * move.first * Tick;
			// Baby attack (damage 2 to captains) is deferred: UNTESTED slice.
		}
		// Instant crush when pressed (a roll pass or a press): hp 5 disc.
		if (pikiMgr) {
			Iterator it(pikiMgr);
			CI_LOOP(it) {
				Piki* p = static_cast<Piki*>(*it);
				if (!p || !p->isAlive()) continue;
				const Vector3f& pos = p->getPosition();
				const float dx = pos.x - l.x, dy = pos.y - l.y, dz = pos.z - l.z;
				if (dx * dx + dy * dy + dz * dz > p2queen::BabyRootRadius * p2queen::BabyRootRadius) continue;
				if (p2queen::babyPressKills(l.state, false)) {
					l.health = 0;
				} else {
					l.health -= 1.0f;
				}
			}
		}
		if (l.health <= 0.0f) {
			l.state = 0;
			l.frame = 0;
		}
	} else if (l.state == 0 && !l.loggedDead) {
		l.loggedDead = true;
		std::printf("P2_QUEEN_LARVA_DEAD id=%u no_corpse=1\n", q.cfg.id);
	}
	if (l.state == 0) {
		const p2queen::ActorClip* clip = config.clip(31, "dead");
		if (clip && l.frame >= clip->duration) {
			l.active = false; // larvae leave no corpse; slot returns to the pool
			std::printf("P2_QUEEN_LARVA_RELEASE id=%u\n", q.cfg.id);
		}
	}
}

void tickQueen(Queen& q) {
	receiveScan(q, Tick);
	q.birthTimer += Tick;
	int alive = 0;
	for (const auto& l : q.larvae)
		if (l.active) ++alive;
	q.roomFlag = p2queen::larvaRoom(alive, q.roomFlag);
	const bool canCreate = q.cfg.larvae && !q.info.noLarvae;
	const bool larvaDue = p2queen::birthDue(canCreate, q.roomFlag, q.birthTimer, p2queen::BirthIntervalSec);
	const bool startFlick = p2queen::isStartFlick(q.blows, q.stuckCount, q.flickTier);

	const char* clipName = stateClip(q.state, q.rollingLeft);
	const p2queen::ActorClip* clip = config.clip(30, clipName);
	const p2queen::ClipKeys keys = p2queen::clipKeys(clipName);
	const float prev = q.frame;
	q.frame += 1.0f;
	// Sampled key events (disc frames) crossed this tick.
	for (int i = 0; i < keys.keyCount; ++i) {
		const int key = keys.keys[i];
		if (!(prev < float(key) && q.frame >= float(key))) continue;
		if (q.state == p2queen::Flick && key == 40) flickStuck(q);
		if (q.state == p2queen::Born && key == 24 && larvaDue) {
			spawnLarva(q);
			q.birthTimer = 0;
		}
		if (q.state == p2queen::Rolling && key == 67)
			std::printf("P2_QUEEN_ROLL_EVENT id=%u frame=67 rumble=1 shake=1 camera_dep=0\n", q.cfg.id);
		if (q.state == p2queen::Dead)
			std::printf("P2_QUEEN_DEAD_KEY id=%u frame=%d\n", q.cfg.id, key);
	}
	if (q.state == p2queen::Rolling) {
		if (!q.loggedAtari) {
			q.loggedAtari = true;
			std::printf("P2_QUEEN_IGNORE_ATARI id=%u rolling=1 captains_enemies_untouched=1\n", q.cfg.id);
		}
		q.rollElapsed += Tick;
		q.x += q.dirX * QueenMoveSpeed * Tick;
		q.z += q.dirZ * QueenMoveSpeed * Tick;
		const float dot = (q.x - q.originX) * q.dirX + (q.z - q.originZ) * q.dirZ;
		const p2queen::RollOutcome outcome = p2queen::rollPass(dot, q.rollElapsed, p2queen::RollingTimeSec,
		                                                     p2queen::HomeRadius, p2queen::TerritoryRadius, q.health);
		if (outcome == p2queen::RollOutcome::Crash) {
			std::printf("P2_QUEEN_CRASH id=%u dot=%.3f territory=200 margin=50 rumble=1 shake=1\n", q.cfg.id, dot);
			if (q.cfg.variant == p2queen::Variant::L02 && !q.loggedRocks) {
				q.loggedRocks = true;
				std::printf("P2_QUEEN_CRASH_ROCKS id=%u recorded=7 lifetime=30 disabled=1\n", q.cfg.id);
			}
			// Bounce back off the territory bound: reverse travel, alternate
			// the sampled side (rolling_r -> next left) and keep the roll
			// clock running so the timed pass end near home stays reachable.
			q.dirX = -q.dirX;
			q.dirZ = -q.dirZ;
			q.rollingLeft = p2queen::nextRollIsLeft(q.rollingLeft ? 5 : p2queen::QueenAnimRollingR);
			q.originX = q.x;
			q.originZ = q.z;
		} else if (outcome == p2queen::RollOutcome::Wait) {
			std::printf("P2_QUEEN_STATE id=%u from=5 to=2 roll_elapsed=%.3f near_home=1\n", q.cfg.id, q.rollElapsed);
			enter(q, p2queen::Wait);
		}
		pressScan(q);
	}
	// Deferred next state, applied at the end of the clip loop pass
	// (KEYEVENT_END semantics on the sampled clips). Loop ranges follow the
	// disc key pairs: sleep 59..118, wait1 full, damage 10..29, rolling
	// 20..69; flick/born always transition at end; dead holds its last pose.
	const int duration = clip ? clip->duration : keys.frames;
	int loopStart = 0, loopEnd = duration;
	if (q.state == p2queen::Sleep) {
		loopStart = 59;
		loopEnd = 118;
	} else if (q.state == p2queen::Damage) {
		loopStart = 10;
		loopEnd = 29;
	} else if (q.state == p2queen::Rolling) {
		loopStart = 20;
		loopEnd = 69;
	}
	if (duration > 0 && q.frame >= float(loopEnd)) {
		q.frame = float(loopStart);
		int next = -1;
		if (q.state == p2queen::Sleep)
			next = p2queen::sleepNext(q.health, q.hitUp, larvaDue, startFlick, q.stuckCount > 0);
		else if (q.state == p2queen::Wait)
			next = p2queen::waitNext(larvaDue, q.idleSec, q.hitUp, startFlick, q.health);
		else if (q.state == p2queen::Damage)
			next = p2queen::damageNext(larvaDue, q.stuckCount > 0, startFlick, q.health);
		else if (q.state == p2queen::Flick) {
			const auto end = p2queen::flickEnd(q.health, q.rollingLeft);
			next = end.first;
			if (next == p2queen::Rolling) {
				bool left = end.second;
				if (q.info.easyFirstRoll && q.firstRoll && naviMgr && naviMgr->getNavi()) {
					const Vector3f& np = naviMgr->getNavi()->getPosition();
					left = p2queen::easyRollLeft(q.yaw, np.x - q.x, np.z - q.z);
					std::printf("P2_QUEEN_EASY_ROLL id=%u f_01=1 away_from_captain=1 left=%d\n", q.cfg.id, int(left));
				}
				q.rollingLeft = left;
				q.firstRoll = false;
				const auto dir = p2queen::rollDirection(q.yaw, left);
				q.dirX = dir.first;
				q.dirZ = dir.second;
				q.originX = q.x;
				q.originZ = q.z;
			}
		} else if (q.state == p2queen::Born)
			next = q.health <= 0.0f ? p2queen::Dead : p2queen::Wait;
		else if (q.state == p2queen::Dead)
			q.frame = float(duration); // stays on the last sampled pose
		q.hitUp = false;
		if (next >= 0 && next != q.state) {
			std::printf("P2_QUEEN_STATE id=%u from=%d to=%d health=%.1f blows=%d stuck=%d\n", q.cfg.id, q.state, next,
			            q.health, q.blows, q.stuckCount);
			enter(q, next);
		}
	}
	if (q.state == p2queen::Wait) q.idleSec += Tick;
	if (q.state != p2queen::Dead && q.health <= 0.0f && q.state != p2queen::Flick) {
		std::printf("P2_QUEEN_STATE id=%u from=%d to=0 health=0\n", q.cfg.id, q.state);
		enter(q, p2queen::Dead);
	}
	for (auto& l : q.larvae)
		if (l.active) tickLarva(q, l); // larvae persist after Queen death
}
} // namespace

void pc_p2_queen_reset() {
	config = p2queen::ActorConfig{};
	shapes.clear();
	queens.clear();
	totalBytes = 0;
	clockLast = 0;
	clockAcc = 0;
}

void pc_p2_queen_setup() {
	pc_p2_queen_reset();
	if (!pc_pikipelago_room_preview()) return;
	std::ifstream in("p2-queen-actor.txt");
	if (!in) return;
	try {
		config = p2queen::readActorConfig(in);
	} catch (...) {
		fail();
	}
	std::map<int, std::vector<unsigned char>> resources;
	// Validate/copy the whole referenced bank before allocating Shapes; clips
	// not selected by this profile never touch the App heap.
	for (size_t ci = 0; ci < config.clips.size(); ++ci) {
		const auto& clip = config.clips[ci];
		size_t bytes = 0;
		for (size_t i = 0; i < clip.frames.size(); ++i) {
			char name[100];
			std::snprintf(name, sizeof(name), "bulblax_%s_%s_%02u.mod", speciesName(clip.enemy), clip.name.c_str(),
			              unsigned(i));
			shapes[ci].push_back(load(name, resources[clip.enemy], bytes));
		}
	}
	for (const auto& p : config.placements) {
		Queen q;
		q.cfg = p;
		q.info = p2queen::variantInfo(p.variant, false);
		q.health = q.info.health;
		q.x = p.x;
		q.y = p.y;
		q.z = p.z;
		q.yaw = p.yaw;
		q.larvae.resize(p2queen::LarvaPoolMax); // bounded pool, allocated once
		enter(q, p2queen::entryState(p.larvae && !q.info.noLarvae));
		std::printf("P2_QUEEN_READY id=%u enemy=30 variant=%s xyz=%.6f,%.6f,%.6f yaw=%.3f health=%.1f larvae=%d "
		            "entry_state=%d pool=%d hysteresis=50/25\n",
		            p.id, p.variant == p2queen::Variant::F01 ? "f_01" : p.variant == p2queen::Variant::L02 ? "l_02" : "default",
		            p.x, p.y, p.z, p.yaw, q.health, int(p.larvae), q.state, p2queen::LarvaPoolMax);
		queens.push_back(q);
	}
	clockLast = SDL_GetTicks();
}

void pc_p2_queen_update() {
	if (queens.empty()) return;
	const unsigned now = SDL_GetTicks();
	clockAcc += float(now - clockLast) * 0.001f;
	clockLast = now;
	int steps = 0;
	while (clockAcc >= Tick && steps < 4) { // bounded: never catch up more than 4 ticks
		clockAcc -= Tick;
		++steps;
		for (auto& q : queens) tickQueen(q);
	}
	if (steps == 4) clockAcc = 0; // drop backlog; 30 Hz stays bounded
}

void pc_p2_queen_draw(Graphics& gfx) {
	if (queens.empty() || !gfx.mCamera) return;
	gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx, gfx.mCamera->mFov, gfx.mCamera->mAspectRatio,
	                   gfx.mCamera->mNear, gfx.mCamera->mFar, 1.f);
	gfx.useMaterial(nullptr);
	gfx.setDepth(true);
	auto drawOne = [&](int enemy, const char* clipName, float frame, float x, float y, float z, float yaw) {
		const p2queen::ActorClip* clip = config.clip(enemy, clipName);
		if (!clip) return;
		size_t ci = size_t(clip - &config.clips[0]);
		size_t pose = clip->index(frame);
		Shape* shape = shapes.at(ci)[pose];
		Matrix4f world, view;
		world.makeSRT(Vector3f(1, 1, 1), Vector3f(0, yaw * 0.0174532925199433f, 0), Vector3f(x, y, z));
		gfx.mCamera->mLookAtMtx.multiplyTo(world, view);
		shape->updateAnim(gfx, view, nullptr, nullptr);
		shape->drawshape(gfx, *gfx.mCamera, nullptr);
	};
	for (auto& q : queens) {
		drawOne(30, stateClip(q.state, q.rollingLeft), q.frame, q.x, q.y, q.z, q.yaw);
		for (const auto& l : q.larvae) {
			if (!l.active) continue;
			drawOne(31, l.state == 2 ? "born" : l.state == 3 ? "move" : "dead", l.frame, l.x, l.y, l.z, l.yaw);
		}
	}
}
