// Engine-free test for the Miulin (Mamuta, 54) OWN FSM policy (own44 #871).
// Build: g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_mamuta_fsm_policy_test.cpp -o p2_mamuta_fsm_policy_test.exe
#include <cassert>
#include <cmath>
#include <cstdio>
#include <sstream>
#include "pc_p2_mamuta_fsm_policy.h"

int main() {
    // Decomp-informed defaults: lifegauge 500, bury 0/5, shake 1/40/40.
    const p2mamutafsm::Params defaults;
    assert(defaults.health == 500.0f);
    assert(defaults.moveSpeed == 80.0f);
    assert(defaults.sight == 200.0f);
    assert(defaults.attackRange == 70.0f);
    assert(defaults.minAttackRange == 25.0f);
    assert(defaults.attackAngle == 15.0f);
    assert(defaults.naviDamage == 5.0f);
    assert(defaults.flickDamage == 1.0f);
    assert(defaults.flickKnockback == 40.0f);
    assert(defaults.flickRange == 40.0f);
    assert(defaults.homeRadius == 15.0f);
    assert(defaults.territory == 200.0f);
    assert(defaults.returnTime == 100.0f);
    // Source state order (Miulin.h:20-31).
    assert(std::string(p2mamutafsm::stateName(p2mamutafsm::STATE_WAIT)) == "wait");
    assert(std::string(p2mamutafsm::stateName(p2mamutafsm::STATE_WALK)) == "walk");
    assert(std::string(p2mamutafsm::stateName(p2mamutafsm::STATE_ATTACK_START)) == "attack_start");
    assert(std::string(p2mamutafsm::stateName(p2mamutafsm::STATE_ATTACKING)) == "attacking");
    assert(std::string(p2mamutafsm::stateName(p2mamutafsm::STATE_ATTACK_END)) == "attack_end");
    assert(std::string(p2mamutafsm::stateName(p2mamutafsm::STATE_TURN)) == "turn");
    assert(std::string(p2mamutafsm::stateName(p2mamutafsm::STATE_FLICK)) == "flick");
    assert(std::string(p2mamutafsm::stateName(p2mamutafsm::STATE_DEAD)) == "dead");
    assert(std::string(p2mamutafsm::stateName(p2mamutafsm::STATE_COUNT)) == "null");
    // Valid override file.
    {
        std::stringstream in;
        in << "P2_MAMUTA_FSM_1 health 600 move_speed 90 sight 220 attack_range 75 "
              "min_attack_range 30 attack_angle 20 navi_damage 6 flick_damage 2 "
              "flick_knockback 45 flick_range 42 home_radius 20 territory 250 return_time 120";
        p2mamutafsm::Params out;
        assert(p2mamutafsm::parseConfig(in, out));
        assert(out.health == 600.0f);
        assert(out.moveSpeed == 90.0f);
        assert(out.territory == 250.0f);
    }
    // Empty override (magic only) keeps defaults.
    {
        std::stringstream in;
        in << "P2_MAMUTA_FSM_1";
        p2mamutafsm::Params out;
        assert(p2mamutafsm::parseConfig(in, out));
        assert(out.health == 500.0f);
    }
    // Reject bad magic, unknown key, duplicate key, out-of-range value.
    {
        std::stringstream bad;
        bad << "P2_MAMUTA_FSM_0";
        p2mamutafsm::Params out;
        assert(!p2mamutafsm::parseConfig(bad, out));
    }
    {
        std::stringstream bad;
        bad << "P2_MAMUTA_FSM_1 bogus 1";
        p2mamutafsm::Params out;
        assert(!p2mamutafsm::parseConfig(bad, out));
    }
    {
        std::stringstream bad;
        bad << "P2_MAMUTA_FSM_1 health 100 health 200";
        p2mamutafsm::Params out;
        assert(!p2mamutafsm::parseConfig(bad, out));
    }
    {
        std::stringstream bad;
        bad << "P2_MAMUTA_FSM_1 attack_angle 999";
        p2mamutafsm::Params out;
        assert(!p2mamutafsm::parseConfig(bad, out));
    }
    std::puts("PASS p2_mamuta_fsm_policy_test");
    return 0;
}
