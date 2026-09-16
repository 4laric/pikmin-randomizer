#pragma once
#include <cstdint>

// Isolated policy for the Creeping Chrysanthemum (Hana, EnemyID 84) residual
// fidelity gates. Source: src/plugProjectNishimuraU/Hana.cpp
// setUnderGround (:169-180) / resetUnderGround (:155-163), and
// src/plugProjectYamashitaU/chappyState.cpp StateSleep::init/cleanup (:98-179)
// plus StateAttack::exec (:1613-1656) with src/plugProjectYamashitaU/
// enemyAction.cpp swallowPikmin (:1148-1173) and EnemyBase::eatWhitePikminCallBack
// (enemyBase.cpp:3293). Research revision 632af93787b9c95b63f0c13be32b161375ce3a96.
// This header is engine-free (<cstdint> only) so the gate matrix can be compiled
// and exercised standalone.

namespace p2hanapolicy {

// Retail US GPVE01 rev 0 Hana proper fp02 "white Pikmin poison" = 2500.0,
// applied by EnemyBase::eatWhitePikminCallBack via addDamage on a swallowed
// White Pikmin. Equal to Hana's fp00 life, so one White is a fatal swallow.
constexpr float WhitePoisonDamage = 2500.0f;

// Source Hana::setUnderGround enables EB_Invulnerable, enables EB_BitterImmune,
// turns hardConstraint on, sets mBuried = true and setAtari(false); the window
// lasts the buried Sleep state and is cleared by Hana::resetUnderGround in
// StateSleep::cleanup. The P1 Chappy host has no EB_* event flags and no
// state-driven atari override, so the module tracks the same window and exposes
// this read-only gate for the host attack path.
enum class UndergroundGate {
    Inactive,            // surfaced: targetable and damageable
    NoAtariInvulnerable, // buried: non-targetable/no-atari and damage rejected
};

struct UndergroundInputs {
    bool registered = false; // actor is a Hana bound by pc_p2_hana_setup
    bool buried = false;     // FSM state == the buried Sleep state
};

inline UndergroundGate undergroundGate(const UndergroundInputs& in)
{
    if (!in.registered) {
        return UndergroundGate::Inactive;
    }
    return in.buried ? UndergroundGate::NoAtariInvulnerable : UndergroundGate::Inactive;
}

inline bool noAtari(UndergroundGate gate)
{
    return gate == UndergroundGate::NoAtariInvulnerable;
}

inline bool blocksDamage(UndergroundGate gate)
{
    return gate == UndergroundGate::NoAtariInvulnerable;
}

inline const char* gateName(UndergroundGate gate)
{
    return gate == UndergroundGate::NoAtariInvulnerable ? "buried" : "surfaced";
}

// fp02 poison is applied exactly once per *successfully consumed* White Pikmin.
// enemyAction.cpp:1159 only reaches eatWhitePikminCallBack when the InteractKill
// stimulate succeeds and the Piki kind is White; a failed kill, a non-White
// kind, or a second kill for the same Pikmin applies nothing.
struct PoisonInputs {
    bool killSucceeded = false;
    bool isWhite = false;
};

inline bool appliesWhitePoison(const PoisonInputs& in)
{
    return in.killSucceeded && in.isWhite;
}

inline float poisonDamage(const PoisonInputs& in)
{
    return appliesWhitePoison(in) ? WhitePoisonDamage : 0.0f;
}

} // namespace p2hanapolicy
