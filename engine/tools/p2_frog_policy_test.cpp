// Engine-free test for the Frog/MaroFrog identity policy (inst-frogs #871).
// Build: g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_frog_policy_test.cpp -o p2_frog_policy_test.exe
#include <cassert>
#include <cmath>
#include <cstdio>
#include <sstream>
#include "pc_p2_frog_policy.h"

int main() {
    // Retail params: Frog (17) vs MaroFrog (18).
    const p2frog::Params& frog = p2frog::params(0);
    const p2frog::Params& maro = p2frog::params(1);
    assert(frog.health == 800.0f);
    assert(maro.health == 1100.0f);
    assert(frog.sight == 360.0f && maro.sight == 360.0f);
    assert(frog.attackRange == 200.0f && maro.attackRange == 250.0f);
    assert(frog.attackDamage == 10.0f && maro.attackDamage == 20.0f);
    assert(frog.jumpFail == 0.2f && maro.jumpFail == 0.1f);
    assert(p2frog::headRadius(0) == 23.0f);
    assert(p2frog::headRadius(1) == 21.0f);
    // State names cover the 10-state source FSM.
    assert(std::string(p2frog::stateName(0)) == "dead");
    assert(std::string(p2frog::stateName(6)) == "attack");
    assert(std::string(p2frog::stateName(9)) == "gohome");
    assert(std::string(p2frog::stateName(99)) == "null");
    // Motion clip mapping.
    assert(std::string(p2frog::motionClip(2)) == "wait1");
    assert(std::string(p2frog::motionClip(8)) == "attack");
    assert(p2frog::motionClip(99) == nullptr);
    // Protocol parse: one Frog actor + both banks.
    {
        std::stringstream in;
        in << "P2_FROG_1\n1\n123 Frog\n";
        in << "Frog\n";
        const char* clips[] = {"dead","wait1","waitact2","move1","waitact1","type1","wait2","type2","attack","damage","type5"};
        for (const char* c : clips) in << c << " 2 2 0 1\n";
        in << "MaroFrog\n";
        for (const char* c : clips) in << c << " 2 2 0 1\n";
        std::map<unsigned,int> actors;
        std::vector<p2animation::Clip> banks[2];
        assert(p2frog::parse(in, actors, banks));
        assert(actors.size() == 1 && actors[123] == 0);
        assert(banks[0].size() == 11 && banks[1].size() == 11);
    }
    // Reject bad header / unknown species.
    {
        std::stringstream bad;
        bad << "P2_FROG_0\n1\n123 Frog\n";
        std::map<unsigned,int> actors;
        std::vector<p2animation::Clip> banks[2];
        assert(!p2frog::parse(bad, actors, banks));
    }
    std::printf("p2_frog_policy_test: all checks passed\n");
    return 0;
}
