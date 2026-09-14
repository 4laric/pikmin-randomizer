#pragma once
// Strict parser for the opt-in Dwarf Orange source-FSM configuration
// (pc_p2_kochappy_fsm). The file is present only when the operator opts in;
// its absence keeps the host P1-AI path byte-for-byte unchanged. Values are the
// audited retail BlueKochappy block (docs/PIKMIN2_DWARF_VARIANTS.md §2/§3,
// `bluekochappy/enemyparm.txt`): health 250, move speed 60, sight 95,
// attack range 30 / angle 20, attack hit range 35 / damage 10, home radius 80,
// territory 500, private radius 70. Malformed or unknown keys are rejected
// before any actor is touched.
#include <cmath>
#include <cstdint>
#include <istream>
#include <string>

namespace p2kochappyfsm {
struct Params {
	float health         = 250.0f; // general fp00
	float moveSpeed      = 60.0f;  // general fp06
	float sight          = 95.0f;  // general fp12
	float attackRange    = 30.0f;  // general fp20 (max attack range)
	float attackAngle    = 20.0f;  // general fp21 (degrees)
	float attackHitRange = 35.0f;  // general fp22
	float attackDamage   = 10.0f;  // general fp24
	float homeRadius     = 80.0f;  // general fp10
	float territory      = 500.0f; // general fp09
	float privateRadius  = 70.0f;  // general fp11
};

// Source KochappyBase::StateID is Wait(0), Dead(1), Turn(2), Walk(3),
// Attack(4), Flick(5), TurnToHome(6), GoHome(7), Press(8), Demo(9). This
// opt-in module implements the five covered states and leaves Turn/TurnToHome/
// GoHome/Press/Demo partial (documented in docs/PIKMIN2_KOCHAPPY_FSM.md).
enum State {
	STATE_WAIT   = 0,
	STATE_WALK   = 1,
	STATE_ATTACK = 2,
	STATE_FLICK  = 3,
	STATE_DEAD   = 4,
	STATE_COUNT  = 5,
};

inline const char* stateName(State state)
{
	switch (state) {
	case STATE_WAIT: return "wait";
	case STATE_WALK: return "walk";
	case STATE_ATTACK: return "attack";
	case STATE_FLICK: return "flick";
	case STATE_DEAD: return "dead";
	default: return "null";
	}
}

inline bool positive(float value, float maximum)
{
	return std::isfinite(value) && value > 0.0f && value <= maximum;
}

inline bool parseConfig(std::istream& in, Params& out)
{
	std::string magic;
	if (!(in >> magic) || magic != "P2_DWARF_ORANGE_FSM_1") {
		return false;
	}
	Params params;
	const unsigned keys = 0x3FF; // all ten keys below
	unsigned seen       = 0;
	std::string key;
	while (in >> key) {
		unsigned bit = 0;
		if (key == "health") bit = 1u << 0;
		else if (key == "move_speed") bit = 1u << 1;
		else if (key == "sight") bit = 1u << 2;
		else if (key == "attack_range") bit = 1u << 3;
		else if (key == "attack_angle") bit = 1u << 4;
		else if (key == "attack_hit_range") bit = 1u << 5;
		else if (key == "attack_damage") bit = 1u << 6;
		else if (key == "home_radius") bit = 1u << 7;
		else if (key == "territory") bit = 1u << 8;
		else if (key == "private_radius") bit = 1u << 9;
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
		} else if (bit == (1u << 4)) {
			if (value <= 0.0f || value > 180.0f) return false;
			params.attackAngle = value;
		} else if (bit == (1u << 6)) {
			if (value < 0.0f || value > 100000.0f) return false;
			params.attackDamage = value;
		} else if (bit == (1u << 1)) {
			if (!positive(value, 10000.0f)) return false;
			params.moveSpeed = value;
		} else if (bit == (1u << 2)) {
			if (!positive(value, 100000.0f)) return false;
			params.sight = value;
		} else if (bit == (1u << 3)) {
			if (!positive(value, 100000.0f)) return false;
			params.attackRange = value;
		} else if (bit == (1u << 5)) {
			if (!positive(value, 100000.0f)) return false;
			params.attackHitRange = value;
		} else if (bit == (1u << 7)) {
			if (!positive(value, 100000.0f)) return false;
			params.homeRadius = value;
		} else if (bit == (1u << 8)) {
			if (!positive(value, 100000.0f)) return false;
			params.territory = value;
		} else {
			if (!positive(value, 100000.0f)) return false;
			params.privateRadius = value;
		}
	}
	out = params;
	return true;
}
} // namespace p2kochappyfsm
