#pragma once
// Adult Orange Bulborb (BlueChappy, EnemyID 42) source policy.
//
// Source of truth (read-only decomp `native/pikmin2-research`):
//   include/Game/enemyInfo.h:101        EnemyID_BlueChappy = 42 // Orange Bulborb
//   include/Game/Entities/BlueChappy.h  Obj : public ChappyBase::Obj (adult)
//   src/plugProjectYamashitaU/BlueChappy.cpp / BlueChappyMgr.cpp
//   src/plugProjectYamashitaU/chappyState.cpp (adult ChappyBase::FSM)
//
// Retail values extracted from the local US GPVE01 revision 0 disc
// (`bluechappy/enemyparm.txt` and `chappy/enemyanimmgr.txt`); see
// `experimental/pikmin2_bluechappy_profile.py` for the audited extraction.
// BlueChappy is the ADULT branch and shares the "Chappy" model/anim/collision
// bank with the Red Bulborb; it is NOT the dwarf Kochappy bank (44/45).
//
// Malformed or unknown keys are rejected before any actor is touched.
#include <cmath>
#include <cstdint>
#include <istream>
#include <set>
#include <string>

namespace p2bluechappy {

struct Params {
	float health        = 850.0f;  // general fp00
	float moveSpeed     = 115.0f;  // general fp06
	float turnGain      = 0.4f;    // general fp08
	float sight         = 500.0f;  // general fp12
	float attackRange   = 75.0f;   // general fp20 (max attack range)
	float attackAngle   = 25.0f;   // general fp21 (degrees)
	float attackHitRange = 80.0f;  // general fp22
	float attackDamage  = 10.0f;   // general fp24
	float maxTurnAngle  = 4.0f;    // general fp28 (degrees per update)
	float purpleStun    = 5.0f;    // general fp38 (seconds)
	float poisonDamage  = 425.0f;  // proper fp02 (white-pikmin poison)
	float wakeRadius    = 130.0f;  // proper fp03 (mBulborbWakeRadius)
};

// Source adult ChappyBase::StateID order (include/Game/Entities/ChappyBase.h:176):
// Turn(0), Dead(1), Flick(2), Walk(3), Attack(4), TurnToHome(5), GoHome(6), Sleep(7).
enum State {
	STATE_TURN         = 0,
	STATE_DEAD         = 1,
	STATE_FLICK        = 2,
	STATE_WALK         = 3,
	STATE_ATTACK       = 4,
	STATE_TURN_TO_HOME = 5,
	STATE_GO_HOME      = 6,
	STATE_SLEEP        = 7,
	STATE_COUNT        = 8,
};

inline const char* stateName(State state)
{
	switch (state) {
	case STATE_TURN: return "turn";
	case STATE_DEAD: return "dead";
	case STATE_FLICK: return "flick";
	case STATE_WALK: return "walk";
	case STATE_ATTACK: return "attack";
	case STATE_TURN_TO_HOME: return "turn_to_home";
	case STATE_GO_HOME: return "go_home";
	case STATE_SLEEP: return "sleep";
	default: return "null";
	}
}

// Source `chappy/enemyanimmgr.txt` attack.bca events: type-2 frame 10 (bite +
// eatPikmin), type-3 frame 33 (swallowPikmin), type-4 frame 40 (transit).
// The adult branch differs from the dwarf Kochappy attack (frames 8/88).
constexpr int AttackBiteFrame    = 10;
constexpr int AttackSwallowFrame = 33;
constexpr int AttackEndFrame     = 40;

inline bool positive(float value, float maximum)
{
	return std::isfinite(value) && value > 0.0f && value <= maximum;
}

inline bool parseConfig(std::istream& in, Params& out)
{
	std::string magic;
	if (!(in >> magic) || magic != "P2_BLUECHAPPY_POLICY_1") {
		return false;
	}
	Params params;
	const unsigned keys = 0xFFF; // all twelve keys below
	unsigned seen       = 0;
	std::string key;
	while (in >> key) {
		unsigned bit = 0;
		if (key == "health") bit = 1u << 0;
		else if (key == "move_speed") bit = 1u << 1;
		else if (key == "turn_gain") bit = 1u << 2;
		else if (key == "sight") bit = 1u << 3;
		else if (key == "attack_range") bit = 1u << 4;
		else if (key == "attack_angle") bit = 1u << 5;
		else if (key == "attack_hit_range") bit = 1u << 6;
		else if (key == "attack_damage") bit = 1u << 7;
		else if (key == "max_turn_angle") bit = 1u << 8;
		else if (key == "purple_stun") bit = 1u << 9;
		else if (key == "poison_damage") bit = 1u << 10;
		else if (key == "wake_radius") bit = 1u << 11;
		else return false;
		if ((seen & bit) || !(keys & bit)) {
			return false;
		}
		seen |= bit;
		float value = 0.0f;
		if (!(in >> value) || !std::isfinite(value)) {
			return false;
		}
		if (bit == (1u << 0)) {
			if (value < 1.0f || value > 100000.0f) return false;
			params.health = value;
		} else if (bit == (1u << 7)) {
			if (value < 0.0f || value > 100000.0f) return false;
			params.attackDamage = value;
		} else if (bit == (1u << 10)) {
			if (value < 0.0f || value > 100000.0f) return false;
			params.poisonDamage = value;
		} else if (bit == (1u << 5)) {
			if (value <= 0.0f || value > 180.0f) return false;
			params.attackAngle = value;
		} else if (bit == (1u << 2)) {
			if (!positive(value, 1.0f)) return false;
			params.turnGain = value;
		} else if (bit == (1u << 8)) {
			if (value < 0.0f || value > 180.0f) return false;
			params.maxTurnAngle = value;
		} else if (bit == (1u << 1)) {
			if (!positive(value, 10000.0f)) return false;
			params.moveSpeed = value;
		} else if (bit == (1u << 3)) {
			if (!positive(value, 100000.0f)) return false;
			params.sight = value;
		} else if (bit == (1u << 4)) {
			if (!positive(value, 100000.0f)) return false;
			params.attackRange = value;
		} else if (bit == (1u << 6)) {
			if (!positive(value, 100000.0f)) return false;
			params.attackHitRange = value;
		} else if (bit == (1u << 9)) {
			if (!positive(value, 100000.0f)) return false;
			params.purpleStun = value;
		} else {
			if (!positive(value, 100000.0f)) return false;
			params.wakeRadius = value;
		}
	}
	out = params;
	return true;
}

// Source-parameter health registry for the bound adult Orange actors. Stores the
// configured fp00 per actor so the max-health hook and death thresholds use the
// adult value (850) rather than the host P1 dwarf life.
class Health {
	bool active = false;
	float value = 850.0f;
	std::set<const void*> actors;

public:
	void reset()
	{
		active = false;
		value  = 850.0f;
		actors.clear();
	}
	void configure(float maxHealth)
	{
		value = maxHealth;
	}
	void activate()
	{
		active = true;
	}
	bool bind(const void* actor)
	{
		return active && actor && actors.insert(actor).second;
	}
	void forget(const void* actor)
	{
		actors.erase(actor);
	}
	bool contains(const void* actor) const
	{
		return active && actors.count(actor) != 0;
	}
	float life(const void* actor, float fallback) const
	{
		return contains(actor) ? value : fallback;
	}
};

} // namespace p2bluechappy
