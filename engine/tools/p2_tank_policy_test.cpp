// Engine-free test for the Tank/Wtank identity policy (inst2-frogs #871).
#include <cassert>
#include <cmath>
#include <cstdio>
#include <sstream>
#include "pc_p2_tank_policy.h"

int main() {
    const p2tank::Params& tank = p2tank::params(0);
    const p2tank::Params& wtank = p2tank::params(1);
    assert(tank.health == 1000.0f);
    assert(wtank.health == 1000.0f);
    assert(tank.sight == 200.0f && wtank.sight == 200.0f);
    assert(tank.attackRange == 120.0f && wtank.attackRange == 120.0f);
    assert(tank.attackRadius == 25.0f && wtank.attackRadius == 25.0f);
    assert(tank.attackDamage == 10.0f && wtank.attackDamage == 0.0f);
    assert(std::string(p2tank::stateName(0)) == "dead");
    assert(std::string(p2tank::stateName(5)) == "attack");
    assert(std::string(p2tank::stateName(6)) == "flick");
    assert(std::string(p2tank::stateName(99)) == "null");
    assert(p2tank::motionClip(99) == nullptr);
    {
        std::stringstream in;
        in << "P2_TANK_1\n1\n123 Tank\n";
        in << "Tank\n";
        const char* clips[] = {"dead","move1","flick","attack","waitact1","waitact2","type5"};
        for (const char* c : clips) in << c << " 2 2 0 1\n";
        in << "Wtank\n";
        for (const char* c : clips) in << c << " 2 2 0 1\n";
        std::map<unsigned,int> actors;
        std::vector<p2animation::Clip> banks[2];
        assert(p2tank::parse(in, actors, banks));
        assert(actors.size() == 1 && actors[123] == 0);
        assert(banks[0].size() == 7 && banks[1].size() == 7);
    }
    {
        std::stringstream bad;
        bad << "P2_TANK_0\n1\n123 Tank\n";
        std::map<unsigned,int> actors;
        std::vector<p2animation::Clip> banks[2];
        assert(!p2tank::parse(bad, actors, banks));
    }
    std::printf("p2_tank_policy_test: all checks passed\n");
    return 0;
}
