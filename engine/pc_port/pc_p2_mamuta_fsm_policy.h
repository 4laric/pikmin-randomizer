#pragma once
// Strict parser for the Miulin (Mamuta, EnemyID 54) source-FSM configuration
// (pc_p2_mamuta_fsm). In bridge-mode campaign sessions the defaults below
// drive the FSM without requiring a file (an explicit `p2-mamuta-fsm.txt` with
// magic `P2_MAMUTA_FSM_1` still overrides); outside bridge the file stays
// required so the default proxy preview path is unchanged. Values are the
// decomp-informed block: lifegauge/health 500 (docs/PIKMIN2_MAMUTA_BEHAVIOR.md),
// general fp06 move 80 / fp12 sight 200 / fp22 attack radius 70 / fp23 hit
// angle 15 deg / fp10 home 15 / fp09 territory 200, proper fp08 min attack
// range 25 / ip01 return time 100, bury payload 0.0 Pikmin / 5.0 Navi
// (miulinState.cpp:292,312), shake 1.0/40/40 (miulinState.cpp:317-326).
// Malformed or unknown keys are rejected before any actor is touched.
#include <cmath>
#include <cstdint>
#include <istream>
#include <string>

namespace p2mamutafsm {
struct Params {
	float health         = 500.0f; // lifegauge fp00
	float moveSpeed      = 80.0f;  // general fp06
	float sight          = 200.0f; // general fp12
	float attackRange    = 70.0f;  // general fp22 mAttackRadius
	float minAttackRange = 25.0f;  // proper fp08
	float attackAngle    = 15.0f;  // general fp23 degrees
	float naviDamage     = 5.0f;   // interactNavi bury damage (Pikmin 0.0)
	float flickDamage    = 1.0f;   // general shake fp18
	float flickKnockback = 40.0f;  // general shake fp17
	float flickRange     = 40.0f;  // general shake fp19
	float homeRadius     = 15.0f;  // general fp10
	float territory      = 200.0f; // general fp09
	float returnTime     = 100.0f; // proper ip01
};

// Source Miulin::StateID order (include/Game/Entities/Miulin.h:20-31):
// Wait(0), Walk(1), AttackStart(2), Attacking(3), AttackEnd(4), Turn(5),
// Flick(6), Dead(7). Null(-1) is the unset sentinel, never entered here.
enum State {
	STATE_WAIT         = 0,
	STATE_WALK         = 1,
	STATE_ATTACK_START = 2,
	STATE_ATTACKING    = 3,
	STATE_ATTACK_END   = 4,
	STATE_TURN         = 5,
	STATE_FLICK        = 6,
	STATE_DEAD         = 7,
	STATE_COUNT        = 8,
};

inline const char* stateName(State state)
{
	switch (state) {
	case STATE_WAIT: return "wait";
	case STATE_WALK: return "walk";
	case STATE_ATTACK_START: return "attack_start";
	case STATE_ATTACKING: return "attacking";
	case STATE_ATTACK_END: return "attack_end";
	case STATE_TURN: return "turn";
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
	if (!(in >> magic) || magic != "P2_MAMUTA_FSM_1") {
		return false;
	}
	Params params;
	unsigned seen = 0;
	std::string key;
	while (in >> key) {
		unsigned bit = 0;
		if (key == "health") bit = 1u << 0;
		else if (key == "move_speed") bit = 1u << 1;
		else if (key == "sight") bit = 1u << 2;
		else if (key == "attack_range") bit = 1u << 3;
		else if (key == "min_attack_range") bit = 1u << 4;
		else if (key == "attack_angle") bit = 1u << 5;
		else if (key == "navi_damage") bit = 1u << 6;
		else if (key == "flick_damage") bit = 1u << 7;
		else if (key == "flick_knockback") bit = 1u << 8;
		else if (key == "flick_range") bit = 1u << 9;
		else if (key == "home_radius") bit = 1u << 10;
		else if (key == "territory") bit = 1u << 11;
		else if (key == "return_time") bit = 1u << 12;
		else return false;
		if (seen & bit) {
			return false;
		}
		seen |= bit;
		float value = 0.0f;
		if (!(in >> value) || !std::isfinite(value)) {
			return false;
		}
		if (bit == (1u << 5)) {
			if (value <= 0.0f || value > 180.0f) return false;
			params.attackAngle = value;
		} else if (bit == (1u << 0)) {
			if (value < 1.0f || value > 100000.0f) return false;
			params.health = value;
		} else if (bit == (1u << 6) || bit == (1u << 7)) {
			if (value < 0.0f || value > 100000.0f) return false;
			if (bit == (1u << 6)) params.naviDamage = value;
			else params.flickDamage = value;
		} else if (bit == (1u << 12)) {
			if (!positive(value, 1000000.0f)) return false;
			params.returnTime = value;
		} else {
			if (!positive(value, 100000.0f)) return false;
			if (bit == (1u << 1)) params.moveSpeed = value;
			else if (bit == (1u << 2)) params.sight = value;
			else if (bit == (1u << 3)) params.attackRange = value;
			else if (bit == (1u << 4)) params.minAttackRange = value;
			else if (bit == (1u << 8)) params.flickKnockback = value;
			else if (bit == (1u << 9)) params.flickRange = value;
			else if (bit == (1u << 10)) params.homeRadius = value;
			else if (bit == (1u << 11)) params.territory = value;
		}
	}
	out = params;
	return true;
}
} // namespace p2mamutafsm
