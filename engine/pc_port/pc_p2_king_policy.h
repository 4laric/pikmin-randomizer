#pragma once
// Emperor Bulblax (KingChappy, enemy ID 53) sampled-actor policy (#289, parent
// #172). Pure, engine-independent mirror of the KingChappy section of
// experimental/pikmin2_bulblax_behavior.py (#227). Every constant names its
// source; disc values stay distinct from header defaults. Keep this header
// free of game-engine includes so the standalone policy test compiles with
// strict MinGW flags.
#include <cmath>
#include <cstdint>
#include <istream>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
namespace p2king {

// KingChappy FSM state IDs, include/Game/Entities/KingChappy.h:22-36.
enum State : int {
	Walk = 0, Attack = 1, Dead = 2, Flick = 3, WarCry = 4, Damage = 5, Turn = 6,
	Eat = 7, Hide = 8, HideWait = 9, Appear = 10, Caution = 11, Swallow = 12
};

enum class Variant { Default, F03, ForceBig };
enum class TurnDecision { Turn, FinishTurn, Walk };
enum class DeadChoice { Dead, WarCry };

// Disc key frames per clip, kingchappy/enemyanimmgr.txt via the #227
// reference (KING_CLIPS, audit lines 225-231). Type 0/1 pairs bracket loop
// ranges; types 2-6 are gameplay events. carry is P1-authoritative.
struct ClipKeys {
	int frames;
	int keys[8];
	int keyCount;
};
inline ClipKeys clipKeys(const std::string& name) {
	if (name == "attack") return {95, {25, 40, 70, 86, 92, 0, 0, 0}, 5};
	if (name == "cry") return {138, {33, 38, 65, 100, 103, 0, 0, 0}, 5};
	if (name == "damage") return {135, {12, 14, 15, 46, 60, 65, 94, 0}, 7};
	if (name == "dead") return {200, {185, 0, 0, 0, 0, 0, 0, 0}, 1};
	if (name == "dive") return {142, {58, 60, 90, 0, 0, 0, 0, 0}, 3};
	if (name == "flick") return {70, {30, 35, 0, 0, 0, 0, 0, 0}, 2};
	if (name == "move1") return {80, {15, 54, 0, 0, 0, 0, 0, 0}, 2};
	if (name == "type1") return {45, {0, 0, 0, 0, 0, 0, 0, 0}, 0};
	if (name == "type2") return {35, {0, 0, 0, 0, 0, 0, 0, 0}, 0};
	if (name == "type3") return {75, {3, 55, 58, 0, 0, 0, 0, 0}, 3};
	if (name == "wait2") return {40, {0, 39, 0, 0, 0, 0, 0, 0}, 2};
	if (name == "waitact1") return {50, {10, 33, 0, 0, 0, 0, 0, 0}, 2};
	if (name == "waitact2") return {60, {0, 0, 0, 0, 0, 0, 0, 0}, 0};
	return {0, {0, 0, 0, 0, 0, 0, 0, 0}, 0};
}

// Attack clip event frames (attack: 25:2 40:3 70:4 86:5 92:6).
constexpr int AttackArmKey = 40;      // key 3 arms Pikmin eating
constexpr int AttackBombKey = 92;     // key 6 allows bomb eating
// WarCry clip event frames (cry: 33:2 38:3 65:4 100:5 103:6).
constexpr int CryCrossEmperorKey = 38; // key 3 cross-Emperor manager request
constexpr int CryAstonishKey = 65;     // key 4 astonish
// Damage clip event frames (damage: 12:2 14:3 15:4 46:5 60:6 65:0 94:1).
constexpr int DamageKillKey = 46;      // key 4 kills mouth contents, applies damage
constexpr int DamageLoopStart = 65;
constexpr int DamageLoopEnd = 94;
// Appear clip event frames (type3: 3:2 55:3 58:4).
constexpr int AppearShakeOffKey = 55;
// Flick clip event frames (flick: 30:2 35:3).
constexpr int FlickTrampleKey = 35;
// Dive clip event frames (dive: 58:2 60:3 90:4). Effects are flags only.

// Proper parameters (disc vs header), include/Game/Entities/KingChappy.h:51-74
// + bulblax.json proper_retail (#227 KING_PROPER_PARMS).
constexpr float RequiredTurningAngleDeg = 60.0f; // fp01 disc (header 20)
constexpr float DistanceToSpawn = 60.0f;         // fp02 disc (header 150)
constexpr float RoarEffectiveAngleDeg = 180.0f;  // fp03 disc (header 45)
constexpr float RoarEffectiveRange = 300.0f;     // fp04 disc (header 100)
constexpr float BombDamage = 200.0f;             // fp05 header == disc
constexpr float InvisibleRange = 80.0f;          // fp06 disc (header 70)
constexpr float TurningEndAngleDeg = 40.0f;      // fp07 disc (header 10)
constexpr float TramplingRange = 45.0f;          // fp08 header == disc
constexpr float AppearShakeOffRange = 100.0f;    // fp09 header == disc
constexpr float AppearShakeOffPower = 200.0f;    // fp10 header == disc
constexpr float DeathRate = 0.0f;                // fp12 header == disc
constexpr float FlickShoutRate = 0.5f;           // fp13 header == disc
// fp14 white Pikmin poison parm: header 300 / disc 200; the actual swallow
// poison damage is a hardcoded 300 (StateSwallow::exec, the #227 finding).
// All three stay distinct here.
constexpr float WhitePikminParmHeader = 300.0f;
constexpr float WhitePikminParmDisc = 200.0f;
constexpr float SwallowPoisonDamage = 300.0f; // hardcoded
constexpr int PeriodOfIncubation = 500;       // ip01 header == disc
constexpr int TimeToAppearance = 0;           // ip02 disc (header 200)
constexpr int BombDamageTime = 180;           // ip03 disc (header 10)

// General parameters (disc), kingchappy/enemyparm.txt (#227 KING_GENERAL_DISC).
constexpr float HealthDefault = 1300.0f; // fp00
constexpr float ShakeRange = 60.0f;      // fp19
constexpr float AttackDamage = 5.0f;     // fp24 (captain mouth-slot damage)

// Big variant (f_03 or force-big), kingChappy.cpp:60-72, 148-158.
constexpr float BigScale = 1.5f;     // fp15 disc
constexpr float BigHealth = 1800.0f; // fp16 disc
constexpr float BigSpeed = 45.0f;    // fp17 disc
constexpr float BigFloorOffset = 60.0f;

// Mouth: 9 slots kamu1..kamu9, radius 25 * scale; tongue tip bero6 radius 5
// aborts the lick on floor/wall contact. kingChappy.cpp:98, 993-1003.
constexpr int MouthSlots = 9;
constexpr float MouthSlotRadius = 25.0f;
constexpr float TongueTipRadius = 5.0f;

// Bomb ingestion, kingChappy.cpp:1009-1043 (audit lines 201-205).
constexpr float ExternalBlastFactor = 0.25f; // bombCallBack, :873-877

// Damage tiers, kingChappy.cpp:824-856.
constexpr float PetrifiedDamageFactor = 0.1f;
constexpr float GroundAttackFactor = 0.2f;
constexpr float GroundAttackRange = 40.0f;
constexpr float GroundAttackMaxDy = 5.0f;

// Flick trample height band, kingChappyState.cpp StateFlick::exec.
constexpr float TrampleHeightBand = 30.0f;

inline void finite(float value) {
	if (!std::isfinite(value)) throw std::runtime_error("Expected finite number");
}

// Entry state: buried in HideWait. kingChappy.cpp:107.
inline int entryState() { return HideWait; }

// HideWait -> Appear when a captain or any Pikmin is within mDistanceToSpawn *
// scale after mTimeToAppearance frames. kingChappyState.cpp:1970-2016.
inline bool hidewaitWake(float nearestTargetDistance, int framesWaited, float scale, float distanceToSpawn,
                         int timeToAppearance) {
	finite(nearestTargetDistance);
	finite(scale);
	finite(distanceToSpawn);
	if (framesWaited < 0 || timeToAppearance < 0) throw std::runtime_error("Expected non-negative frame count");
	if (framesWaited <= timeToAppearance) return false;
	return nearestTargetDistance < distanceToSpawn * scale;
}

// Walk turn decision. kingChappyState.cpp:53-117.
inline TurnDecision walkTurn(float goalAngleOff, float requiredTurningAngle, float turningEndAngle) {
	finite(goalAngleOff);
	finite(requiredTurningAngle);
	finite(turningEndAngle);
	const float off = std::fabs(goalAngleOff);
	if (off > requiredTurningAngle) return TurnDecision::Turn;
	if (off <= turningEndAngle) return TurnDecision::FinishTurn;
	return TurnDecision::Walk;
}

// Walk loses interest after mPeriodOfIncubation frames without a target or
// when out of territory; returns home and enters Hide. kingChappyState.cpp:53-117.
inline bool walkGiveUp(int framesWithoutTarget, int periodOfIncubation, bool outOfTerritory) {
	if (framesWithoutTarget < 0 || periodOfIncubation < 0) throw std::runtime_error("Expected non-negative frame count");
	return outOfTerritory || framesWithoutTarget > periodOfIncubation;
}

// checkDead: Dead, or WarCry with probability mDeathRate (0 by default).
// kingChappyState.cpp + kingChappy.cpp checkDead.
inline DeadChoice checkDead(float roll, float deathRate) {
	finite(roll);
	finite(deathRate);
	if (roll < 0.0f || roll > 1.0f || deathRate < 0.0f || deathRate > 1.0f)
		throw std::runtime_error("Invalid checkDead input");
	return roll < deathRate ? DeadChoice::WarCry : DeadChoice::Dead;
}

// checkFlick once isStartFlick fires: WarCry with probability mFlickShoutRate
// when under half health, otherwise Flick. kingChappy.cpp:2457-2474.
inline int checkFlick(float health, float maxHealth, float roll, float flickShoutRate = FlickShoutRate) {
	finite(health);
	finite(maxHealth);
	finite(roll);
	finite(flickShoutRate);
	if (roll < 0.0f || roll > 1.0f || maxHealth <= 0.0f) throw std::runtime_error("Invalid flick input");
	if (health < 0.5f * maxHealth && roll < flickShoutRate) return WarCry;
	return Flick;
}

// damageCallBack coefficient; 0.0 means ignored. kingChappy.cpp:824-856.
// The decomp collisionCallback no-op quirk (audit line 254) is recorded, not
// "fixed": no extra channel is synthesized here.
inline float damageTier(bool petrified, bool hasPart, bool stuckToPart, float attackerDy, float sqrDistanceXZ) {
	finite(attackerDy);
	finite(sqrDistanceXZ);
	if (petrified) return PetrifiedDamageFactor;
	if (hasPart) return stuckToPart ? 1.0f : 0.0f;
	if (attackerDy < GroundAttackMaxDy) return sqrDistanceXZ < GroundAttackRange * GroundAttackRange ? GroundAttackFactor : 0.0f;
	return 0.0f;
}

// Damage key 4: kills everything in the mouth and applies bombs * mBombDamage.
// kingChappyState.cpp StateDamage::exec.
inline float bombDamage(int bombsEaten, float damagePerBomb = BombDamage) {
	finite(damagePerBomb);
	if (bombsEaten < 0) throw std::runtime_error("Expected non-negative bomb count");
	return bombsEaten * damagePerBomb;
}

// eatBomb only accepts a Bomb (enemy ID 36) in BOMB_Wait that is not already
// stuck to a mouth. kingChappy.cpp:1009-1043.
inline bool eatableBomb(const std::string& bombState) { return bombState == "BOMB_Wait"; }

// Big variant in forest_3 (getCaveID() == 'f_03') or with mDoForceBig.
// kingChappy.cpp:148-158.
inline bool isBig(Variant variant) { return variant != Variant::Default; }

// Attack armed-frame contract: key 3 arms eating, key 6 allows bombs.
// Returns bit 0 = eat Pikmin, bit 1 = eat bomb. RECONSTRUCTED
// (StateAttack::exec / searchTarget / checkAttack, audit lines 249-251).
inline int attackStep(int keyEvent, bool mouthSlotsFree, bool bombsInRange, bool pikminInRange) {
	int actions = 0;
	if (keyEvent == 6 && bombsInRange && mouthSlotsFree) actions |= 2;
	if ((keyEvent == 3 || keyEvent == 6) && pikminInRange && mouthSlotsFree) actions |= 1;
	return actions;
}

// checkAttack may target eatable bombs beyond mInvisibleRange (80 disc) when
// mCanAttackBombs is set (default on). kingChappy.cpp (audit line 204).
inline bool canTargetBomb(float distanceXZ, bool canAttackBombs = true) {
	finite(distanceXZ);
	return canAttackBombs && distanceXZ > InvisibleRange;
}

// Flick key 3: presses every Pikmin and captain within mTramplingRange * scale
// of the foot in a 30 unit height band, then the standard flick shake; captains
// are flicked only if none was pressed. RECONSTRUCTED (StateFlick::exec).
struct FlickStep {
	int pressedPikmin;
	int pressedCaptains;
	bool flickCaptains;
};
inline FlickStep flickStep(int pikminInTrampleRange, int captainsInTrampleRange) {
	if (pikminInTrampleRange < 0 || captainsInTrampleRange < 0) throw std::runtime_error("Expected non-negative counts");
	return {pikminInTrampleRange, captainsInTrampleRange, captainsInTrampleRange == 0};
}

// WarCry key 3 cross-Emperor contract: wake one buried Emperor (force transit
// to Appear) and make one walking Emperor roar (force transit to WarCry).
// kingChappyMgr.cpp:53-62 + kingChappy.cpp:1548. Two-Emperor scope only.
inline int crossEmperorTarget(int otherState) {
	if (otherState == HideWait) return Appear;
	if (otherState == Walk) return WarCry;
	return -1;
}

// Damage end: Dead or Walk. kingChappyState.cpp:1706-1775.
inline int damageEnd(float health) {
	finite(health);
	return health <= 0.0f ? Dead : Walk;
}

// Attack end routing: bombs in mouth -> Eat; Pikmin in mouth -> Swallow;
// otherwise Walk. kingChappyState.cpp:133-743.
inline int attackEnd(int bombsInMouth, int pikminInMouth) {
	if (bombsInMouth < 0 || pikminInMouth < 0) throw std::runtime_error("Expected non-negative mouth counts");
	if (bombsInMouth > 0) return Eat;
	if (pikminInMouth > 0) return Swallow;
	return Walk;
}

// Variant parameter block. Normal walk speed is an approximation (the #227
// reference only pins the big-variant speed, fp17 disc 45).
struct VariantInfo {
	bool big;
	float scale;
	float health;
	float speed;
	float floorOffset;
};
inline VariantInfo variantInfo(Variant variant) {
	if (isBig(variant)) return {true, BigScale, BigHealth, BigSpeed, BigFloorOffset};
	return {false, 1.0f, HealthDefault, 30.0f /* approximation */, 0.0f};
}

// ---------------------------------------------------------------------------
// P2_KING_ACTOR_1 actor configuration (strict, fail-closed).
// ---------------------------------------------------------------------------
struct ActorClip {
	int enemy = 0; // 53 KingChappy
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
	float x = 0, y = 0, z = 0, yaw = 0;
};
// Actor-local BOMB_Wait bomb stub (enemy ID 36). externalBlastTick > 0 is a
// fixture injection: the bomb detonates externally at that behavior tick and
// the blast is quartered (bombCallBack, kingChappy.cpp:873-877).
struct BombPlacement {
	uint32_t id = 0;
	float x = 0, y = 0, z = 0;
	uint32_t externalBlastTick = 0;
};
struct ActorConfig {
	std::vector<ActorClip> clips;
	std::vector<Placement> placements;
	std::vector<BombPlacement> bombs;
	const ActorClip* clip(int enemy, const std::string& name) const {
		for (const auto& c : clips)
			if (c.enemy == enemy && c.name == name) return &c;
		return nullptr;
	}
};
inline bool kingClipName(const std::string& name) {
	return clipKeys(name).frames > 0; // carry is P1-authoritative; not sampled here
}
inline ActorConfig readActorConfig(std::istream& in) {
	auto fail = []() { throw std::runtime_error("invalid King actor profile"); };
	ActorConfig cfg;
	std::string magic;
	int count;
	if (!(in >> magic >> count) || magic != "P2_KING_ACTOR_1" || count < 1 || count > 16) fail();
	std::set<std::pair<int, std::string>> seen;
	for (int i = 0; i < count; ++i) {
		ActorClip c;
		int n;
		if (!(in >> c.enemy >> c.name >> c.duration >> n)) fail();
		const bool known = c.enemy == 53 && kingClipName(c.name);
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
	// The King FSM needs the full sampled state set.
	for (const char* need : {"attack", "cry", "damage", "dead", "dive", "flick", "move1", "type1", "type2", "type3",
	                         "wait2", "waitact1", "waitact2"})
		if (!cfg.clip(53, need)) fail();
	// Two-Emperor scope: at most 2 placements (kingChappyMgr cross contract).
	if (!(in >> count) || count < 1 || count > 2) fail();
	std::set<uint32_t> ids;
	for (int i = 0; i < count; ++i) {
		unsigned long long id;
		std::string variant;
		Placement p;
		if (!(in >> id >> variant >> p.x >> p.y >> p.z >> p.yaw) || id > 0xffffffffULL || !ids.insert(uint32_t(id)).second
		    || !std::isfinite(p.x) || !std::isfinite(p.y) || !std::isfinite(p.z) || !std::isfinite(p.yaw)
		    || std::fabs(p.x) > 100000 || std::fabs(p.y) > 100000 || std::fabs(p.z) > 100000 || std::fabs(p.yaw) > 360)
			fail();
		p.id = uint32_t(id);
		if (variant == "default")
			p.variant = Variant::Default;
		else if (variant == "f_03")
			p.variant = Variant::F03;
		else if (variant == "force_big")
			p.variant = Variant::ForceBig;
		else
			fail();
		cfg.placements.push_back(p);
	}
	// Actor-local bomb stubs (fixture injection channel).
	if (!(in >> count) || count < 0 || count > 4) fail();
	for (int i = 0; i < count; ++i) {
		unsigned long long id, blastTick;
		BombPlacement b;
		if (!(in >> id >> b.x >> b.y >> b.z >> blastTick) || id > 0xffffffffULL || blastTick > 1000000ULL
		    || !ids.insert(uint32_t(id)).second || !std::isfinite(b.x) || !std::isfinite(b.y) || !std::isfinite(b.z)
		    || std::fabs(b.x) > 100000 || std::fabs(b.y) > 100000 || std::fabs(b.z) > 100000)
			fail();
		b.id = uint32_t(id);
		b.externalBlastTick = uint32_t(blastTick);
		cfg.bombs.push_back(b);
	}
	if (in >> magic) fail();
	return cfg;
}
} // namespace p2king
