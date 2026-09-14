// Standalone lane-22 fixed-hazard policy test (#170, child #447).
// Compile with MinGW strict flags:
//   g++ -std=c++17 -Wall -Wextra -Werror -I <native>/pc_port tests/pikmin2_hiba_policy.cpp -o hiba_policy.exe
// Mirrors the fixed-hazard section of experimental/pikmin2_elemental_behavior.py
// against pc_port/pc_p2_hiba_policy.h (which reuses pc_p2_dweevil_policy.h).
#include "pc_p2_hiba_policy.h"
#include <cassert>
#include <cmath>
#include <cstdio>
#include <sstream>
#include <string>

using namespace p2hiba;

namespace {
bool parse(const std::string& text, Config& config) {
    std::istringstream in(text);
    return readConfig(in, config);
}
} // namespace

int main() {
    // Per-hazard state IDs (Hiba.h:136-141; GasHiba.h:151-156; ElecHiba.h:197-203).
    static_assert(HibaDead == 0 && HibaWait == 1 && HibaAttack == 2, "Hiba states");
    static_assert(GasHibaDead == 0 && GasHibaWait == 1 && GasHibaAttack == 2, "GasHiba states");
    static_assert(ElecHibaDead == 0 && ElecHibaWait == 1 && ElecHibaSign == 2 && ElecHibaAttack == 3,
                  "ElecHiba states");

    // Element mapping and identity.
    assert(isFixedHazard(HibaId) && isFixedHazard(GasHibaId) && isFixedHazard(ElecHibaId));
    assert(!isFixedHazard(p2dweevil::FireId));
    assert(hazardStimulus(HibaId) == StimFire);
    assert(hazardStimulus(GasHibaId) == StimGas);
    assert(hazardStimulus(ElecHibaId) == StimDenki);
    assert(std::string(p2dweevil::stimulusName(hazardStimulus(HibaId))) == "InteractFire");
    assert(std::string(p2dweevil::stimulusName(hazardStimulus(ElecHibaId))) == "InteractDenki");
    assert(std::string(panicFor(StimFire)) == "Fire");
    assert(std::string(panicFor(StimGas)) == "Gas");
    assert(std::string(panicFor(StimDenki)) == "DenkiDying");

    bool threw = false;
    try {
        hazardStimulus(p2dweevil::TankId);
    } catch (const std::runtime_error&) {
        threw = true;
    }
    assert(threw);

    // Header defaults stay distinct from the retail disc blocks.
    assert(discTiming(HibaId).wait == 3.0f && headerTiming(HibaId).wait == 2.5f);
    assert(discTiming(GasHibaId).wait == 0.0f && discTiming(GasHibaId).attackStart == 0.6f);
    assert(discTiming(ElecHibaId).wait == 1.5f && discTiming(ElecHibaId).warning == 1.5f);
    assert(headerTiming(GasHibaId).attackStart == 1.0f);

    // Wait -> Attack activation (Hiba.cpp:31-50, GasHiba.cpp:33-53).
    assert(hazardActivate(HibaId, 10.0f, 2.0f) == HazardWait);
    assert(hazardActivate(HibaId, 10.0f, 3.0f) == HazardAttack);
    assert(hazardActivate(GasHibaId, 10.0f, 0.0f) == HazardAttack);
    assert(hazardActivate(HibaId, 0.0f, 9.0f) == HazardDead);
    assert(hazardActivate(HibaId, 10.0f, 2.5f, 2.5f) == HazardAttack);

    // Hiba Attack stimulates each update until active-time expiry.
    assert(hibaEmit(HibaAttack, 10.0f, 0.0f, 2.5f));
    assert(hibaEmit(HibaAttack, 10.0f, 2.4f, 2.5f));
    assert(!hibaEmit(HibaAttack, 10.0f, 2.5f, 2.5f));
    assert(!hibaEmit(HibaWait, 10.0f, 0.0f, 2.5f));
    assert(!hibaEmit(HibaAttack, 0.0f, 0.0f, 2.5f));

    // GasHiba Attack has an attack-start gate; a positive wait time finishes it.
    assert(!gashibaEmit(GasHibaAttack, 0.5f, 0.5f, 0.6f, 3.0f, 0.0f));
    assert(gashibaEmit(GasHibaAttack, 0.6f, 0.6f, 0.6f, 3.0f, 0.0f));
    assert(!gashibaEmit(GasHibaAttack, 1.0f, 3.0f, 0.6f, 3.0f, 1.0f));
    assert(gashibaEmit(GasHibaAttack, 1.0f, 99.0f, 0.6f, 3.0f, 0.0f)); // disc wait 0 never finishes
    assert(!gashibaEmit(GasHibaWait, 1.0f, 0.0f, 0.6f, 3.0f, 0.0f));

    // ElecHiba Wait -> Sign -> Attack -> Wait chain.
    assert(elechibaAdvance(ElecHibaWait, 10.0f, 1.0f, 1.5f, 1.5f, 2.5f, false).next == ElecHibaWait);
    assert(elechibaAdvance(ElecHibaWait, 10.0f, 1.5f, 1.5f, 1.5f, 2.5f, false).next == ElecHibaSign);
    assert(elechibaAdvance(ElecHibaSign, 10.0f, 1.0f, 1.5f, 1.5f, 2.5f, false).next == ElecHibaSign);
    {
        const ElecStep step = elechibaAdvance(ElecHibaSign, 10.0f, 1.5f, 1.5f, 1.5f, 2.5f, false);
        assert(step.next == ElecHibaAttack && step.emits);
    }
    assert(elechibaAdvance(ElecHibaAttack, 10.0f, 1.0f, 1.5f, 1.5f, 2.5f, false).emits);
    assert(elechibaAdvance(ElecHibaAttack, 10.0f, 2.5f, 1.5f, 1.5f, 2.5f, false).next == ElecHibaWait);
    assert(elechibaAdvance(ElecHibaAttack, 10.0f, 0.1f, 1.5f, 1.5f, 2.5f, true).next == ElecHibaWait);
    assert(elechibaAdvance(ElecHibaWait, 0.0f, 0.0f, 1.5f, 1.5f, 2.5f, false).next == ElecHibaDead);

    // Two-node wire geometry and team-head damage routing.
    {
        const std::pair<float, float> nodes = elechibaNodePositions(100.0f, 40.0f);
        assert(nodes.first == 80.0f && nodes.second == 120.0f);
    }
    assert(elechibaTeamHeadDamage(true, false) == SidedRouteToHead);
    assert(elechibaTeamHeadDamage(false, false) == SidedRouteToHead);
    assert(elechibaTeamHeadDamage(true, true) == SidedReject);

    // GasHiba bridge/gate link owner.
    assert(gashibaLinkedOwner(false, false) == LinkNone);
    assert(gashibaLinkedOwner(true, false) == LinkBridge);
    assert(gashibaLinkedOwner(false, true) == LinkGate);
    assert(gashibaLinkedOwner(true, true) == LinkBridgeGate);
    assert(std::string(linkOwnerName(LinkBridgeGate)) == "bridge+gate");

    // Versus attribute discharge modes.
    assert(elechibaVersusStimulus("neutral") == StimDenki);
    assert(elechibaVersusStimulus("red") == StimFire);
    assert(elechibaVersusStimulus("blue") == StimBubble);
    threw = false;
    try {
        elechibaVersusStimulus("green");
    } catch (const std::runtime_error&) {
        threw = true;
    }
    assert(threw);

    // Receiver colour immunity: fire excludes Red/Bulbmin, gas White,
    // denki Yellow (interactPiki.cpp:334,445,503,531).
    assert(!receiverAccepts(StimFire, Red));
    assert(receiverAccepts(StimFire, Blue));
    assert(receiverAccepts(StimFire, Yellow));
    assert(!receiverAccepts(StimGas, White));
    assert(receiverAccepts(StimGas, Red));
    assert(!receiverAccepts(StimDenki, Yellow));
    assert(receiverAccepts(StimDenki, Red));
    assert(!receiverAccepts(StimFire, Blue, true));

    // Strict P2_HIBA_NATIVE_1 config: good parse.
    const std::string good =
        "P2_HIBA_NATIVE_1\n"
        "3\n"
        "20 20 0 0 0 0 100 -1 0 0\n"
        "21 21 10 0 10 0 100 0.5 0 1\n"
        "22 22 -10 0 -10 0 100 -1 40 0\n";
    {
        Config config;
        assert(parse(good, config));
        assert(config.hazards.size() == 3);
        assert(config.hazards[0].hazardId == HibaId && config.hazards[0].waitOverride == -1.0f);
        assert(config.hazards[1].hazardId == GasHibaId && config.hazards[1].link == 1);
        assert(config.hazards[2].hazardId == ElecHibaId && config.hazards[2].separation == 40.0f);
    }

    auto reject = [](const std::string& text) {
        Config config;
        assert(!parse(text, config));
    };
    reject("P2_HIBA_NATIVE_2\n1\n20 20 0 0 0 0 100 -1 0 0\n");            // wrong version
    reject("P2_HIBA_NATIVE_1\n0\n");                                      // empty
    reject("P2_HIBA_NATIVE_1\n9\n0\n");                                   // budget
    reject("P2_HIBA_NATIVE_1\n1\n20 23 0 0 0 0 100 -1 0 0\n");            // unknown hazard
    reject("P2_HIBA_NATIVE_1\n1\n20 20 0 0 0 0 0 -1 0 0\n");              // zero health
    reject("P2_HIBA_NATIVE_1\n1\n20 20 1e39 0 0 0 100 -1 0 0\n");         // non-finite xyz
    reject("P2_HIBA_NATIVE_1\n1\n20 20 0 0 0 361 100 -1 0 0\n");          // yaw bound
    reject("P2_HIBA_NATIVE_1\n1\n20 20 0 0 0 0 100 1001 0 0\n");          // wait bound
    reject("P2_HIBA_NATIVE_1\n1\n20 20 0 0 0 0 100 -1 1 0\n");            // separation on Hiba
    reject("P2_HIBA_NATIVE_1\n1\n20 20 0 0 0 0 100 -1 0 1\n");            // link on Hiba
    reject("P2_HIBA_NATIVE_1\n1\n21 21 0 0 0 0 100 -1 0 4\n");            // link bound
    reject("P2_HIBA_NATIVE_1\n1\n22 22 0 0 0 0 100 -1 -1 0\n");           // negative separation
    reject("P2_HIBA_NATIVE_1\n1\n4294967296 20 0 0 0 0 100 -1 0 0\n");    // id overflow
    reject("P2_HIBA_NATIVE_1\n2\n20 20 0 0 0 0 100 -1 0 0\n20 21 0 0 0 0 100 -1 0 0\n"); // dup generator
    reject(good + "junk");                                                 // trailing
    reject(good.substr(0, good.size() - 3));                               // truncated

    std::puts("pikmin2_hiba_policy PASS");
    return 0;
}
