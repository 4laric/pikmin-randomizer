// Standalone lane-22 BombOtakara payload policy test (#170, child #447).
// Compile with MinGW strict flags:
//   g++ -std=c++17 -Wall -Wextra -Werror -I <native>/pc_port tests/pikmin2_bombotakara_policy.cpp -o bombotakara_policy.exe
// Mirrors the BombOtakara section of experimental/pikmin2_elemental_behavior.py
// against pc_port/pc_p2_bombotakara_policy.h.
#include "pc_p2_bombotakara_policy.h"
#include <cassert>
#include <cmath>
#include <cstdio>
#include <sstream>
#include <string>

using namespace p2bombotakara;

namespace {
bool parse(const std::string& text, Config& config) {
    std::istringstream in(text);
    return readConfig(in, config);
}
} // namespace

int main() {
    // Shared OtakaraBase Bomb-carry states 11..13.
    static_assert(p2dweevil::BombWait == 11 && p2dweevil::BombMove == 12 && p2dweevil::BombTurn == 13,
                  "bomb carry states");
    assert(isBombCarryState(p2dweevil::BombWait));
    assert(isBombCarryState(p2dweevil::BombMove));
    assert(isBombCarryState(p2dweevil::BombTurn));
    assert(!isBombCarryState(p2dweevil::Dead));
    assert(!isBombCarryState(p2dweevil::ItemDrop));

    // stimulateBomb -> forceBomb delay.
    assert(kForceDelaySeconds == 1.5f);

    // Payload decision (BombOtakara.cpp:42-87; OtakaraBase.cpp:699-707).
    assert(payloadAction(false, false, false, 0.0f) == KillCarrier);
    assert(payloadAction(true, false, true, 0.0f) == ForceBomb);
    assert(payloadAction(true, true, false, 0.0f) == DamagePayload);
    assert(payloadAction(true, false, false, 1.4f) == ChasePayload);
    assert(payloadAction(true, false, false, 1.5f) == ForceBomb);
    assert(payloadAction(true, true, true, 0.0f) == ForceBomb); // earthquake wins over bittered
    assert(std::string(payloadActionName(KillCarrier)) == "kill_carrier");
    assert(std::string(payloadActionName(ForceBomb)) == "force_bomb");
    assert(std::string(payloadActionName(DamagePayload)) == "damage_payload");
    assert(std::string(payloadActionName(ChasePayload)) == "chase_payload");

    bool threw = false;
    try {
        payloadAction(true, false, false, std::nanf(""));
    } catch (const std::runtime_error&) {
        threw = true;
    }
    assert(threw);

    // Exactly-once detonation.
    {
        const DetonationResult first = detonate(true, false);
        assert(first.detonated && !first.alreadyDetonated);
        const DetonationResult second = detonate(true, true);
        assert(!second.detonated && second.alreadyDetonated);
        const DetonationResult gone = detonate(false, false);
        assert(!gone.detonated && !gone.alreadyDetonated);
    }

    // Trigger names.
    assert(std::string(triggerName(TriggerContact)) == "contact");
    assert(std::string(triggerName(TriggerPress)) == "press");
    assert(std::string(triggerName(TriggerDeath)) == "death");
    assert(std::string(triggerName(TriggerEarthquake)) == "earthquake");

    // Strict P2_BOMBOTAKARA_NATIVE_1 config: good parse.
    const std::string good =
        "P2_BOMBOTAKARA_NATIVE_1\n"
        "2\n"
        "30 0 0 0 0 150 40 10 0 10\n"
        "31 5 0 5 0 150 41 15 0 15\n";
    {
        Config config;
        assert(parse(good, config));
        assert(config.units.size() == 2);
        assert(config.units[0].generator == 30 && config.units[0].payloadId == 40);
        assert(config.units[0].health == 150.0f && config.units[1].bx == 15.0f);
    }

    auto reject = [](const std::string& text) {
        Config config;
        assert(!parse(text, config));
    };
    reject("P2_BOMBOTAKARA_NATIVE_2\n1\n30 0 0 0 0 150 40 0 0 0\n");         // wrong version
    reject("P2_BOMBOTAKARA_NATIVE_1\n0\n");                                 // empty
    reject("P2_BOMBOTAKARA_NATIVE_1\n5\n0\n");                              // budget
    reject("P2_BOMBOTAKARA_NATIVE_1\n1\n4294967296 0 0 0 0 150 40 0 0 0\n"); // generator overflow
    reject("P2_BOMBOTAKARA_NATIVE_1\n1\n30 0 0 0 0 150 4294967296 0 0 0\n"); // payload overflow
    reject("P2_BOMBOTAKARA_NATIVE_1\n1\n30 1e39 0 0 0 150 40 0 0 0\n");      // non-finite xyz
    reject("P2_BOMBOTAKARA_NATIVE_1\n1\n30 0 0 0 361 150 40 0 0 0\n");       // yaw bound
    reject("P2_BOMBOTAKARA_NATIVE_1\n1\n30 0 0 0 0 0 40 0 0 0\n");           // zero health
    reject("P2_BOMBOTAKARA_NATIVE_1\n2\n30 0 0 0 0 150 40 0 0 0\n30 1 0 1 0 150 41 0 0 0\n"); // dup generator
    reject("P2_BOMBOTAKARA_NATIVE_1\n2\n30 0 0 0 0 150 40 0 0 0\n31 1 0 1 0 150 40 0 0 0\n"); // dup payload
    reject("P2_BOMBOTAKARA_NATIVE_1\n2\n30 0 0 0 0 150 40 0 0 0\n40 1 0 1 0 150 41 0 0 0\n"); // id collision
    reject(good + "junk");                                                   // trailing
    reject(good.substr(0, good.size() - 3));                                 // truncated

    std::puts("pikmin2_bombotakara_policy PASS");
    return 0;
}
