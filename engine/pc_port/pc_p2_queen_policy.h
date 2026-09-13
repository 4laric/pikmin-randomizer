#pragma once
// Empress Bulblax (Queen, enemy ID 30) sampled-actor policy (#256, parent #172).
// Pure, engine-independent mirror of experimental/pikmin2_bulblax_behavior.py
// (#227). Every constant names its source; disc values stay distinct from
// header defaults. Keep this header free of game-engine includes so the
// standalone policy test compiles with strict MinGW flags.
#include <cmath>
#include <cstdint>
#include <istream>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
namespace p2queen {

// Queen FSM state IDs, include/Game/Entities/Queen.h:26-34.
enum State : int { Dead = 0, Sleep = 1, Wait = 2, Damage = 3, Flick = 4, Rolling = 5, Born = 6 };

enum class Attacker { PikminPart, CaptainPunch, Earthquake };
enum class Part { Nose, Head, Bod1, Bod5, Other };
enum class FlickEffect { Flick, FlickReversed, ShakeOff };
enum class RollOutcome { Crash, Wait, Continue };
enum class Variant { Default, F01, L02 };

// Disc key frames per clip, queen/enemyanimmgr.txt via the #227 reference
// (QUEEN_CLIPS). Sleep loop is 59..118; gameplay event at 120. Rolling clips
// loop 20..69 with the gameplay event at 67.
struct ClipKeys {
	int frames;
	int keys[4];
	int keyCount;
};
inline ClipKeys clipKeys(const std::string& name) {
	if (name == "dead") return {140, {60, 73, 86, 99}, 4};
	if (name == "sleep") return {210, {59, 118, 120, 0}, 3};
	if (name == "wait1") return {30, {0, 29, 0, 0}, 2};
	if (name == "damage") return {50, {10, 29, 0, 0}, 2};
	if (name == "flick") return {60, {40, 0, 0, 0}, 1};
	if (name == "rolling_l") return {110, {20, 67, 69, 0}, 3};
	if (name == "rolling_r") return {110, {20, 67, 69, 0}, 3};
	if (name == "born") return {28, {24, 0, 0, 0}, 1};
	return {0, {0, 0, 0, 0}, 0};
}

constexpr int QueenAnimRollingR = 6; // Queen.h:202; roll side alternates off this index.

// Proper parameters (disc), Queen.h:167-179 + bulblax.json proper_retail.
constexpr float RollingTimeSec = 3.5f;   // fp01
constexpr float BirthIntervalSec = 2.0f; // fp02
constexpr float HealthDefault = 5000.0f; // general fp00
constexpr float HealthF01 = 3300.0f;     // fp11 HoH/HoB override
constexpr int MaxBirths = 50;            // ip01
constexpr int MinBirths = 25;            // ip02

// General parameters (disc), queen/enemyparm.txt.
constexpr float TerritoryRadius = 200.0f; // fp09
constexpr float HomeRadius = 25.0f;       // fp10
constexpr float ShakeKnockback = 300.0f;  // fp17
constexpr float ShakeDamage = 1.0f;       // fp18
constexpr float AttackRadius = 150.0f;    // fp22
constexpr float AttackHitAngleDeg = 25.0f; // fp23
constexpr float PressDamage = 10.0f;      // fp24
constexpr float LaunchSpeed = 50.0f;      // fp14 (larva launch)

// QueenState.cpp:403-409, 154.
constexpr float TerritoryCrashMargin = 50.0f;
constexpr float WaitIdleSleepSec = 30.0f;

// Shake-off thresholds (disc), general ip01..ip07 (audit lines 107-108).
constexpr int ShakeBlows[4] = {30, 35, 45, 50};
constexpr int ShakeSticking[3] = {5, 10, 15};

// Damage coefficients, Queen.cpp:184-198 + audit lines 104-105.
constexpr float SleepDamageFactor = 0.1f;
constexpr float FlickDamageFactor = 0.2f;
constexpr float PetrifiedDamageFactor = 0.25f;

// rollingAttack geometry, Queen.cpp:287-318.
constexpr float PressHeightBand = 50.0f;

// Collision tree, queen/enemycoll.txt.
constexpr float RootRadius = 275.0f;

// Larva birth, Queen.cpp:423-479.
constexpr int LarvaPoolMax = 50;

// Baby (Bulborb Larva, enemy ID 31) minimal slice, baby/enemyparm.txt.
constexpr float BabyHealth = 5.0f;
constexpr float BabySpeed = 40.0f;
constexpr float BabySight = 800.0f;
constexpr float BabyAttackDamage = 2.0f; // captain bite; deferred (UNTESTED)
constexpr float BabyRootRadius = 25.0f;

// HoH (l_02) crash rocks: recorded, disabled in this lane (explicit limit).
constexpr int L02CrashRocks = 7;
constexpr float L02RockLifetimeSec = 30.0f;

inline void finite(float value) {
	if (!std::isfinite(value)) throw std::runtime_error("Expected finite number");
}

// Entry state: Wait when larvae are allowed, else Sleep. Queen.cpp:62-66.
inline int entryState(bool canCreateLarva) { return canCreateLarva ? Wait : Sleep; }

// StateSleep deferred next state at clip end; -1 keeps sleeping.
// QueenState.cpp:89-103: motion finishes on death, hit-counter rise or a due
// larva; then Dead > Flick > Damage (Pikmin stuck) > Wait.
inline int sleepNext(float health, bool hitCounterUp, bool larvaDue, bool startFlick, bool stuckPikmin) {
	finite(health);
	if (!(health <= 0.0f || hitCounterUp || larvaDue)) return -1;
	if (health <= 0.0f) return Dead;
	if (startFlick) return Flick;
	if (stuckPikmin) return Damage;
	return Wait;
}

// StateWait deferred next state; later checks override (Sleep, Damage, Born,
// Flick, Dead). QueenState.cpp:153-173.
inline int waitNext(bool larvaDue, float idleSeconds, bool hitCounterUp, bool startFlick, float health) {
	finite(idleSeconds);
	finite(health);
	int next = -1;
	if (!larvaDue && idleSeconds > WaitIdleSleepSec) next = Sleep;
	if (hitCounterUp) next = Damage;
	if (larvaDue) next = Born;
	if (startFlick) next = Flick;
	if (health <= 0.0f) next = Dead;
	return next;
}

// StateDamage deferred next state: Born, Wait when unstuck, Flick, Dead.
// QueenState.cpp:219-237.
inline int damageNext(bool larvaDue, bool stuckPikmin, bool startFlick, float health) {
	finite(health);
	int next = -1;
	if (larvaDue) next = Born;
	if (!stuckPikmin) next = Wait;
	if (startFlick) next = Flick;
	if (health <= 0.0f) next = Dead;
	return next;
}

// StateFlick KEYEVENT_END: Dead, else Rolling with side from
// isRollingAttackLeft. QueenState.cpp:281-293.
inline std::pair<int, bool> flickEnd(float health, bool rollingLeft) {
	finite(health);
	if (health <= 0.0f) return {Dead, false};
	return {Rolling, rollingLeft};
}

// Next Rolling pass is "left" when the current animation is rolling_r.
// QueenState.cpp:441-447.
inline bool nextRollIsLeft(int currentAnimIndex) { return currentAnimIndex == QueenAnimRollingR; }

// Rolling pass outcome per frame. QueenState.cpp:405-433 (RECONSTRUCTED).
inline RollOutcome rollPass(float dotAlongRoll, float rollingElapsed, float rollingTime, float homeRadius,
                            float territoryRadius, float health) {
	finite(dotAlongRoll);
	finite(rollingElapsed);
	finite(rollingTime);
	finite(homeRadius);
	finite(territoryRadius);
	finite(health);
	if (dotAlongRoll > territoryRadius - TerritoryCrashMargin) return RollOutcome::Crash;
	if (rollingElapsed > rollingTime && dotAlongRoll > -(50.0f + homeRadius) && dotAlongRoll < 50.0f)
		return RollOutcome::Wait;
	return RollOutcome::Continue;
}

// Room-flag hysteresis on the larva pool. Queen.cpp:469-479.
inline bool larvaRoom(int aliveLarvae, bool roomFlag, int maxBirths = MaxBirths, int minBirths = MinBirths) {
	if (aliveLarvae < 0) throw std::runtime_error("Expected non-negative larva count");
	if (aliveLarvae >= maxBirths) return false;
	if (aliveLarvae <= minBirths) return true;
	return roomFlag;
}

// Birth due: larvae allowed, room, timer past interval. Queen.cpp:469-479.
inline bool birthDue(bool canCreateLarva, bool roomFlag, float birthTimer, float birthInterval) {
	finite(birthTimer);
	finite(birthInterval);
	return canCreateLarva && roomFlag && birthTimer > birthInterval;
}

// Damage coefficient; 0.0 means ignored. Only Pikmin hitting a collision part
// count (Queen.cpp:184-198); captain punches and earthquake do nothing.
inline float damageFactor(int state, Attacker attacker, bool petrified = false) {
	if (attacker == Attacker::Earthquake) return 0.0f;
	if (petrified) return PetrifiedDamageFactor;
	if (attacker == Attacker::CaptainPunch) return 0.0f;
	if (state == Sleep) return SleepDamageFactor;
	if (state == Flick) return FlickDamageFactor;
	return 1.0f;
}

// flickPikmin joint routing, Queen.cpp:324-345.
inline FlickEffect flickEffect(Part part) {
	if (part == Part::Nose || part == Part::Head || part == Part::Bod1) return FlickEffect::Flick;
	if (part == Part::Bod5) return FlickEffect::FlickReversed;
	return FlickEffect::ShakeOff;
}

// isStartFlick: tiered shake-off thresholds (blows 30/35/45/50, sticking
// 5/10/15); tier clamps at the top row. Audit lines 107-108.
inline bool isStartFlick(int blows, int sticking, int tier) {
	if (blows < 0 || sticking < 0 || tier < 0) throw std::runtime_error("Expected non-negative counters");
	const int blowTier = tier > 3 ? 3 : tier;
	const int stickTier = tier > 2 ? 2 : tier;
	return blows >= ShakeBlows[blowTier] || sticking >= ShakeSticking[stickTier];
}

// Variant overrides, Queen.cpp:85-105, 355-410. zukan/piklopedia mode maps to
// no larvae. l_02 crash rocks are recorded but disabled in this lane.
struct VariantInfo {
	bool noLarvae;
	bool easyFirstRoll;
	float health;
	int crashRocks;
	float rockLifetimeSec;
};
inline VariantInfo variantInfo(Variant variant, bool zukanMode = false) {
	if (zukanMode) return {true, false, HealthDefault, 0, 0.0f};
	if (variant == Variant::F01) return {true, true, HealthF01, 0, 0.0f};
	if (variant == Variant::L02) return {false, false, HealthDefault, L02CrashRocks, L02RockLifetimeSec};
	return {false, false, HealthDefault, 0, 0.0f};
}

// Baby press crush: any press while past Born and not petrified.
// Baby.cpp:114-137 (state IDs: dead 0, press 1, born 2, move 3, attack 4).
inline bool babyPressKills(int stateId, bool petrified) {
	if (stateId < 0) throw std::runtime_error("Expected state ID");
	return !petrified && stateId > 2;
}

// Baby StateMove step (RECONSTRUCTED), BabyState.cpp:153-186. Returns
// (targetSpeed, attack?).
inline std::pair<float, bool> babyMoveStep(float angleDist, float maxAttackAngle, float moveSpeed,
                                           float targetDistance, float maxAttackRange, bool hasTarget) {
	finite(angleDist);
	finite(maxAttackAngle);
	finite(moveSpeed);
	finite(targetDistance);
	finite(maxAttackRange);
	if (!hasTarget) return {0.0f, false};
	const float speed = std::fabs(angleDist) <= std::fabs(maxAttackAngle) ? moveSpeed : 0.25f * moveSpeed;
	const bool attack = targetDistance <= maxAttackRange && std::fabs(angleDist) <= std::fabs(maxAttackAngle);
	return {speed, attack};
}

// Baby StateBorn: damp until landed, then Move or Dead. BabyState.cpp:107-127.
inline int babyBornNext(bool landed, float health) {
	finite(health);
	if (!landed) return -1;
	return health <= 0.0f ? 0 : 3;
}

// Sideways roll direction: yaw +/- 90 degrees. Returns (dx, dz) unit vector.
inline std::pair<float, float> rollDirection(float yawDeg, bool left) {
	finite(yawDeg);
	const float rad = (yawDeg + (left ? 90.0f : -90.0f)) * 0.0174532925199433f;
	return {std::sin(rad), std::cos(rad)};
}

// f_01 easy first roll: pick the side whose roll direction points away from
// the captain. Queen.cpp:355-380.
inline bool easyRollLeft(float yawDeg, float toCaptainDx, float toCaptainDz) {
	finite(yawDeg);
	finite(toCaptainDx);
	finite(toCaptainDz);
	const auto l = rollDirection(yawDeg, true);
	return l.first * toCaptainDx + l.second * toCaptainDz < 0.0f;
}

// ---------------------------------------------------------------------------
// P2_QUEEN_ACTOR_1 actor configuration (strict, fail-closed).
// ---------------------------------------------------------------------------
struct ActorClip {
	int enemy = 0; // 30 Queen, 31 Baby
	std::string name;
	int duration = 0;
	std::vector<int> frames;
	size_t index(float sourceFrame) const {
		if (!std::isfinite(sourceFrame)) throw std::runtime_error("invalid frame");
		sourceFrame = std::fmod(std::fmax(0.0f, sourceFrame), float(duration));
		size_t best = 0;
		for (size_t i = 1; i < frames.size(); ++i)
			if (std::fabs(frames[i] - sourceFrame) < std::fabs(frames[best] - sourceFrame)) best = i;
		return best;
	}
};
struct Placement {
	uint32_t id = 0;
	Variant variant = Variant::Default;
	bool larvae = false;
	float x = 0, y = 0, z = 0, yaw = 0;
};
struct ActorConfig {
	std::vector<ActorClip> clips;
	std::vector<Placement> placements;
	const ActorClip* clip(int enemy, const std::string& name) const {
		for (const auto& c : clips)
			if (c.enemy == enemy && c.name == name) return &c;
		return nullptr;
	}
};
inline bool queenClipName(const std::string& name) {
	return clipKeys(name).frames > 0; // carry is P1-authoritative; not sampled here
}
inline bool babyClipName(const std::string& name) {
	const std::string names = " dead deadpress move attack attackfail born ";
	return names.find(" " + name + " ") != std::string::npos;
}
inline ActorConfig readActorConfig(std::istream& in) {
	auto fail = []() { throw std::runtime_error("invalid Queen actor profile"); };
	ActorConfig cfg;
	std::string magic;
	int count;
	if (!(in >> magic >> count) || magic != "P2_QUEEN_ACTOR_1" || count < 1 || count > 16) fail();
	std::set<std::pair<int, std::string>> seen;
	for (int i = 0; i < count; ++i) {
		ActorClip c;
		int n;
		if (!(in >> c.enemy >> c.name >> c.duration >> n)) fail();
		const bool known = c.enemy == 30 ? queenClipName(c.name) : c.enemy == 31 ? babyClipName(c.name) : false;
		if (!known || c.name.size() > 24 || c.name.find_first_not_of("abcdefghijklmnopqrstuvwxyz0123456789_") != std::string::npos
		    || !seen.insert({c.enemy, c.name}).second || c.duration < 1 || c.duration > 10000 || n < 1 || n > 12)
			fail();
		for (int j = 0; j < n; ++j) {
			int f;
			if (!(in >> f) || f < 0 || f >= c.duration || (j && f <= c.frames.back())) fail();
			c.frames.push_back(f);
		}
		cfg.clips.push_back(c);
	}
	// The Queen FSM needs the full sampled state set.
	for (const char* need : {"dead", "sleep", "wait1", "damage", "flick", "rolling_l", "rolling_r", "born"})
		if (!cfg.clip(30, need)) fail();
	if (!(in >> count) || count < 1 || count > 4) fail();
	std::set<uint32_t> ids;
	for (int i = 0; i < count; ++i) {
		unsigned long long id;
		std::string variant;
		int larvae;
		Placement p;
		if (!(in >> id >> variant >> larvae >> p.x >> p.y >> p.z >> p.yaw) || id > 0xffffffffULL
		    || !ids.insert(uint32_t(id)).second || (larvae != 0 && larvae != 1) || !std::isfinite(p.x) || !std::isfinite(p.y)
		    || !std::isfinite(p.z) || !std::isfinite(p.yaw) || std::fabs(p.x) > 100000 || std::fabs(p.y) > 100000
		    || std::fabs(p.z) > 100000 || std::fabs(p.yaw) > 360)
			fail();
		p.id = uint32_t(id);
		p.larvae = larvae != 0;
		if (variant == "default")
			p.variant = Variant::Default;
		else if (variant == "f_01")
			p.variant = Variant::F01;
		else if (variant == "l_02")
			p.variant = Variant::L02;
		else
			fail();
		if (p.variant == Variant::F01 && p.larvae) fail(); // HoB disables larvae, Queen.cpp:95-100
		if (p.larvae && (!cfg.clip(31, "born") || !cfg.clip(31, "move") || !cfg.clip(31, "dead"))) fail();
		cfg.placements.push_back(p);
	}
	if (in >> magic) fail();
	return cfg;
}
} // namespace p2queen
