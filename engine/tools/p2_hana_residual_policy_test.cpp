#include "pc_p2_hana_residual_policy.h"

#include <cstdio>

// Standalone gate matrix for the Creeping Chrysanthemum (Hana, EnemyID 84)
// buried/no-atari + fp02-poison residual gates. Source: Hana.cpp
// setUnderGround (:169-180) / resetUnderGround (:155-163), chappyState.cpp
// StateSleep/StateAttack (:98-179, :1613-1656) and enemyAction.cpp
// swallowPikmin (:1148-1173) at research revision 632af937.
// Build: g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port
//            tools/p2_hana_residual_policy_test.cpp -o hana_residual_test

#undef assert
#define assert(condition) do { if (!(condition)) return __LINE__; } while (false)

using namespace p2hanapolicy;

int main()
{
    // --- Buried / no-atari gate (source setUnderGround vs resetUnderGround). ---
    UndergroundInputs in;

    // Unregistered actors are always a no-op for the shared host hooks.
    assert(undergroundGate(in) == UndergroundGate::Inactive);

    // Registered but surfaced: targetable and damageable.
    in = {};
    in.registered = true;
    in.buried = false;
    assert(undergroundGate(in) == UndergroundGate::Inactive);
    assert(!noAtari(undergroundGate(in)));
    assert(!blocksDamage(undergroundGate(in)));

    // Registered and buried: non-targetable/no-atari and damage rejected.
    in = {};
    in.registered = true;
    in.buried = true;
    assert(undergroundGate(in) == UndergroundGate::NoAtariInvulnerable);
    assert(noAtari(undergroundGate(in)));
    assert(blocksDamage(undergroundGate(in)));
    assert(gateName(undergroundGate(in))[0] == 'b');

    // Registration is required: buried alone never blocks (unregistered lane no-op).
    in = {};
    in.buried = true;
    assert(!blocksDamage(undergroundGate(in)));

    // gateName labels the surfaced gate too.
    in = {};
    in.registered = true;
    assert(gateName(undergroundGate(in))[0] == 's');

    // --- fp02 poison (source eatWhitePikminCallBack on a successful swallow). ---
    assert(WhitePoisonDamage == 2500.0f);

    PoisonInputs poison;

    // Plain unfed input applies nothing.
    assert(!appliesWhitePoison(poison));
    assert(poisonDamage(poison) == 0.0f);

    // Successful White swallow applies the full fp02 exactly once.
    poison = {};
    poison.killSucceeded = true;
    poison.isWhite = true;
    assert(appliesWhitePoison(poison));
    assert(poisonDamage(poison) == WhitePoisonDamage);

    // A failed kill of a White applies nothing (source checks stimulate result).
    poison = {};
    poison.killSucceeded = false;
    poison.isWhite = true;
    assert(!appliesWhitePoison(poison));
    assert(poisonDamage(poison) == 0.0f);

    // A successful non-White swallow applies nothing.
    poison = {};
    poison.killSucceeded = true;
    poison.isWhite = false;
    assert(!appliesWhitePoison(poison));
    assert(poisonDamage(poison) == 0.0f);

    // Failed non-White swallow applies nothing.
    poison = {};
    poison.killSucceeded = false;
    poison.isWhite = false;
    assert(!appliesWhitePoison(poison));
    assert(poisonDamage(poison) == 0.0f);

    std::puts("p2_hana_residual_policy_test PASS");
    return 0;
}
