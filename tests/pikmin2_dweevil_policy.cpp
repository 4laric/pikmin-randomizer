// Standalone lane-22 dweevil family policy test (#170, child #447).
// Compile with MinGW strict flags:
//   g++ -std=c++17 -Wall -Wextra -Werror -I <native>/pc_port tests/pikmin2_dweevil_policy.cpp -o dweevil_policy.exe
// Mirrors tests/test_pikmin2_elemental_behavior.py (the delivered Python model
// experimental/pikmin2_elemental_behavior.py) against pc_p2_dweevil_policy.h.
#include "pc_p2_dweevil_policy.h"
#include <cassert>
#include <cmath>
#include <cstdio>
#include <sstream>
#include <string>

using namespace p2dweevil;

namespace {
bool parse(const std::string& text, Config& config) {
    std::istringstream in(text);
    return readConfig(in, config);
}
} // namespace

int main() {
    // Shared OtakaraBase StateID, OtakaraBase.h:22-39.
    static_assert(Dead == 0 && Flick == 1 && Wait == 2 && Move == 3 && Turn == 4 && Take == 5
                      && ItemWait == 6 && ItemMove == 7 && ItemTurn == 8 && ItemFlick == 9
                      && ItemDrop == 10 && BombWait == 11 && BombMove == 12 && BombTurn == 13,
                  "dweevil state IDs");

    // Identity / classification.
    static_assert(FireId == 59 && WaterId == 60 && GasId == 61 && ElecId == 62 && BombId == 93,
                  "dweevil source IDs");
    assert(isDweevilSpecies(FireId) && isDweevilSpecies(BombId));
    assert(!isDweevilSpecies(TankId));
    assert(isFixedHazard(HibaId) && isFixedHazard(GasHibaId) && isFixedHazard(ElecHibaId));
    assert(!isFixedHazard(FireId));
    assert(std::string(speciesName(FireId)) == "FireOtakara");
    assert(std::string(speciesName(BombId)) == "BombOtakara");

    // Emitted stimulus (audit lines 16-20); BombOtakara delegates to its Bomb.
    assert(stimulusFor(FireId) == StimFire);
    assert(stimulusFor(WaterId) == StimBubble);
    assert(stimulusFor(GasId) == StimGas);
    assert(stimulusFor(ElecId) == StimDenki);
    assert(stimulusFor(BombId) == StimNone);
    assert(std::string(stimulusName(stimulusFor(FireId))) == "InteractFire");
    assert(blowhogStimulus(TankId) == StimFire && blowhogStimulus(WtankId) == StimBubble);

    bool threw = false;
    try {
        stimulusFor(TankId);
    } catch (const std::runtime_error&) {
        threw = true;
    }
    assert(threw);
    threw = false;
    try {
        blowhogStimulus(FireId);
    } catch (const std::runtime_error&) {
        threw = true;
    }
    assert(threw);

    // Receiver immunity (interactPiki.cpp:334,445,503,531).
    assert(pikminImmune(StimFire, Red) && !pikminImmune(StimFire, Blue));
    assert(pikminImmune(StimBubble, Blue) && !pikminImmune(StimBubble, Red));
    assert(pikminImmune(StimGas, White) && !pikminImmune(StimGas, Red));
    assert(pikminImmune(StimGas, Red, true));
    assert(pikminImmune(StimDenki, Yellow) && !pikminImmune(StimDenki, Red));
    for (Stimulus stimulus : {StimFire, StimBubble, StimGas, StimDenki}) {
        assert(pikminImmune(stimulus, Bulbmin));
    }
    assert(!pikminImmune(StimNone, Red));
    assert(receiverAccepts(StimFire, Blue));
    assert(!receiverAccepts(StimFire, Red));
    assert(!receiverAccepts(StimFire, Blue, true));
    assert(!receiverAccepts(StimGas, Red, false, true));

    // Fixed hazard activation; disc wait times differ from header defaults.
    assert(hazardActivate(HibaId, 10.0f, 2.0f) == HazardWait);
    assert(hazardActivate(HibaId, 10.0f, 3.0f) == HazardAttack);
    assert(hazardActivate(GasHibaId, 10.0f, 0.0f) == HazardAttack);
    assert(hazardActivate(HibaId, 0.0f, 9.0f) == HazardDead);
    assert(hazardActivate(HibaId, 10.0f, 2.5f, 2.5f) == HazardAttack);
    threw = false;
    try {
        hazardActivate(TankId, 1.0f, 1.0f);
    } catch (const std::runtime_error&) {
        threw = true;
    }
    assert(threw);
    threw = false;
    try {
        hazardActivate(HibaId, std::nanf(""), 1.0f);
    } catch (const std::runtime_error&) {
        threw = true;
    }
    assert(threw);

    // Theft / capture / damage / exactly-once drop.
    assert(theftDecision(true, true, false, true, false));
    assert(!theftDecision(false, true, false, true, false));
    assert(!theftDecision(true, false, false, true, false));
    assert(!theftDecision(true, true, true, true, false));
    assert(!theftDecision(true, true, false, false, false));
    assert(!theftDecision(true, true, false, true, true));
    assert(captureHealth(80.0f) == 80.0f);
    threw = false;
    try {
        captureHealth(0.0f);
    } catch (const std::runtime_error&) {
        threw = true;
    }
    assert(threw);
    threw = false;
    try {
        captureHealth(-5.0f);
    } catch (const std::runtime_error&) {
        threw = true;
    }
    assert(threw);
    assert(damageRoute(true) == RouteTreasure);
    assert(damageRoute(false) == RouteDweevil);
    {
        const DropResult first = drop(true, false, DropDeath);
        assert(first.dropped && !first.carryingAfter);
        const DropResult replay = drop(true, true, DropDeath);
        assert(!replay.dropped && !replay.carryingAfter);
        const DropResult nothing = drop(false, false, DropInterruption);
        assert(!nothing.dropped && !nothing.carryingAfter);
        const DropResult stone = drop(true, false, DropStone);
        assert(stone.dropped);
    }

    // Strict P2_DWEEVIL_NATIVE_1 config: good parse.
    const std::string good =
        "P2_DWEEVIL_NATIVE_1\n"
        "1\n"
        "235300 59 34 30 1896 0 80\n"
        "1\n"
        "900001 30 30 1880 1 1 0\n";
    {
        Config config;
        assert(parse(good, config));
        assert(config.units.size() == 1 && config.treasures.size() == 1);
        assert(config.units[0].generator == 235300 && config.units[0].species == FireId);
        assert(config.units[0].otakaraLife == 80.0f);
        assert(config.treasures[0].id == 900001 && config.treasures[0].alive
               && config.treasures[0].pickable && !config.treasures[0].captured);
    }

    auto reject = [](const std::string& text) {
        Config config;
        assert(!parse(text, config));
    };
    reject("P2_DWEEVIL_NATIVE_2\n1\n235300 59 0 0 0 0 80\n0\n"); // wrong version
    reject("P2_DWEEVIL_NATIVE_1\n0\n0\n");                      // no units
    reject("P2_DWEEVIL_NATIVE_1\n9\n0\n");                      // unit budget
    reject("P2_DWEEVIL_NATIVE_1\n1\n235300 58 0 0 0 0 80\n0\n"); // unknown species
    reject("P2_DWEEVIL_NATIVE_1\n1\n235300 59 0 0 0 0 0\n0\n");  // zero life
    reject("P2_DWEEVIL_NATIVE_1\n1\n235300 59 100001 0 0 0 80\n0\n"); // xyz bound
    reject("P2_DWEEVIL_NATIVE_1\n1\n235300 59 0 0 0 361 80\n0\n");     // yaw bound
    reject("P2_DWEEVIL_NATIVE_1\n1\n4294967296 59 0 0 0 0 80\n0\n");  // id overflow
    reject("P2_DWEEVIL_NATIVE_1\n2\n235300 59 0 0 0 0 80\n235300 60 0 0 0 0 80\n0\n"); // dup unit
    reject("P2_DWEEVIL_NATIVE_1\n1\n235300 59 1e39 0 0 0 80\n0\n");   // non-finite xyz
    reject("P2_DWEEVIL_NATIVE_1\n1\n235300 59 0 0 0 0 80\n1\n900001 0 0 0 2 1 0\n");  // flag bound
    reject("P2_DWEEVIL_NATIVE_1\n1\n235300 59 0 0 0 0 80\n1\n900001 0 0 0 1 1 2\n");  // captured flag
    reject("P2_DWEEVIL_NATIVE_1\n1\n235300 59 0 0 0 0 80\n2\n900001 0 0 0 1 1 0\n900001 0 0 0 1 1 0\n"); // dup treasure
    reject("P2_DWEEVIL_NATIVE_1\n1\n900001 59 0 0 0 0 80\n1\n900001 0 0 0 1 1 0\n");  // id reuse
    reject("P2_DWEEVIL_NATIVE_1\n1\n235300 59 0 0 0 0 80\n0\njunk");                  // trailing token
    reject(good.substr(0, good.size() - 3));                                          // truncated

    std::puts("pikmin2_dweevil_policy PASS");
    return 0;
}
