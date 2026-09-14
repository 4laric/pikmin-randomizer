#include "pc_p2_bulbmin.h"
#include <cassert>
#include <cstdio>
#include <sstream>

// Lane 11 bridge test: the opt-in config parser must accept exactly the
// source-bounded `P2_BULBMIN_1 <epoch> <dependents>` body and reject every
// malformed variant, and the bridge core must wire that config into the
// dependent ledger, the whistle->captain handoff and the cave save filter.
// Engine-double only: no Piki/pikiMgr is constructed here.

static bool read(const char* text, P2BulbminConfig& out) {
    std::istringstream in(text);
    return p2_bulbmin_read(in, out);
}

static void test_parse() {
    P2BulbminConfig config;

    assert(read("P2_BULBMIN_1 100 10", config));
    assert(config.motherEpoch == 100 && config.maxDependents == 10);

    assert(read("\n  P2_BULBMIN_1 1 1  \n", config));
    assert(config.motherEpoch == 1 && config.maxDependents == 1);

    assert(read("P2_BULBMIN_1 4294967296 3", config));
    assert(config.motherEpoch == 4294967296ULL && config.maxDependents == 3);

    assert(!read("P2_BULBMIN_2 100 10", config));
    assert(!read("P2_BULBMIN_1 0 10", config));
    assert(!read("P2_BULBMIN_1 100 0", config));
    assert(!read("P2_BULBMIN_1 100 11", config));
    assert(!read("P2_BULBMIN_1 100", config));
    assert(!read("P2_BULBMIN_1", config));
    assert(!read("P2_BULBMIN_1 abc 10", config));
    assert(!read("P2_BULBMIN_1 -5 10", config));
    assert(!read("P2_BULBMIN_1 100 x", config));
    // Lane-11 sub-slice 3: the optional fourth token is the proxy label, so
    // `extra` now parses as a label; only true trailing data is rejected.
    assert(read("P2_BULBMIN_1 100 10 extra", config));
    assert(config.motherModel == "extra");
    assert(!read("P2_BULBMIN_1 100 10 kochappy_proxy trailing", config));
}

static void test_birth_and_recruitment() {
    P2BulbminBridge bridge;
    P2CaptainOwnershipTable table;

    // Epoch zero / over-cap configuration is refused and leaves it inert.
    P2BulbminConfig bad;
    bad.motherEpoch = 0;
    assert(!bridge.setup(bad));
    assert(!bridge.enabled());
    assert(!bridge.birth(1).accepted);
    bad.motherEpoch = 7;
    bad.maxDependents = P2BULBMIN_MAX_DEPENDENTS + 1;
    assert(!bridge.setup(bad));
    assert(!bridge.enabled());

    P2BulbminConfig config;
    config.motherEpoch = 77;
    config.maxDependents = 3;
    assert(bridge.setup(config, &table));
    assert(bridge.enabled());
    assert(bridge.settings().motherEpoch == 77 && bridge.settings().maxDependents == 3);

    for (std::uint32_t i = 0; i < 3; ++i) {
        P2BulbminCommand command = bridge.birth(1001 + i);
        assert(command.accepted && command.phase == P2BulbminWild);
        assert(!command.countsAsPikmin);
    }
    assert(bridge.dependentCount() == 3 && bridge.size() == 3 && bridge.wildCount() == 3);
    // Configured cap and duplicate id are both refused.
    assert(!bridge.birth(1004).accepted);
    assert(!bridge.birth(1001).accepted);
    assert(bridge.size() == 3);

    // Whistle converts in place and hands the body to the bound captain.
    P2BulbminCommand recruited = bridge.whistle(1001, P2CaptainA);
    assert(recruited.accepted && recruited.phase == P2BulbminRecruited);
    assert(recruited.countsAsPikmin && recruited.detachFromLeader);
    assert(bridge.phaseOf(1001) == P2BulbminRecruited);
    assert(table.isOwned(1001) && table.ownerOf(1001) == P2CaptainA);
    assert(bridge.wildCount() == 2 && bridge.recruitedCount() == 1);
    // A second whistle is a no-op; an unknown id is refused.
    assert(!bridge.whistle(1001, P2CaptainA).accepted);
    assert(!bridge.whistle(9999, P2CaptainA).accepted);

    // Mother death releases only wild dependents; the whistled one keeps its
    // captain ownership and survives.
    std::vector<std::uint32_t> released = bridge.leaderDied();
    assert(released.size() == 2);
    assert(bridge.size() == 1 && bridge.recruitedCount() == 1);
    assert(bridge.phaseOf(1001) == P2BulbminRecruited);
    assert(table.isOwned(1001));

    // Forget drops the surviving body (engine Piki destruction).
    assert(bridge.forget(1001));
    assert(bridge.size() == 0 && !bridge.forget(1001));

    // Re-setup resets all prior state.
    config.motherEpoch = 88;
    config.maxDependents = 10;
    assert(bridge.setup(config, &table));
    assert(bridge.size() == 0 && bridge.dependentCount() == 0);
    assert(bridge.birth(2001).accepted);

    // Without a captain table a whistle still converts the body but does not
    // claim it.
    P2BulbminBridge orphan;
    config.motherEpoch = 5;
    assert(orphan.setup(config));
    assert(orphan.birth(3001).accepted);
    assert(orphan.whistle(3001, P2CaptainB).accepted);
    assert(orphan.recruitedCount() == 1);
}

// Engine double: the driver's spawn callback creates one body and registers it
// in the bridge, exactly like the live pikiMgr->birth() hook. Returns 0 when
// the bridge refuses (configured cap reached), which stops the flock.
struct SpawnDouble {
    P2BulbminBridge* bridge;
    std::uint32_t nextId;
};

static std::uint32_t spawn_double(void* context, int) {
    SpawnDouble* engine = static_cast<SpawnDouble*>(context);
    const std::uint32_t id = engine->nextId++;
    return engine->bridge->birth(id).accepted ? id : 0;
}

static void test_driver() {
    P2BulbminBridge bridge;
    P2CaptainOwnershipTable table;
    P2BulbminConfig config;
    config.motherEpoch = 300;
    config.maxDependents = P2BULBMIN_MAX_DEPENDENTS;
    assert(bridge.setup(config, &table));

    SpawnDouble engine = {&bridge, 7000};
    P2BulbminDriver driver;
    assert(driver.bind(&bridge, &spawn_double, &engine));
    assert(driver.bound());

    // Source LeafChappy::birthChildren spawns exactly ten dependents, no eleventh.
    assert(driver.birthFlock(10) == 10);
    assert(driver.birthFlock(1) == 0);
    assert(driver.bornCount() == 10);
    assert(bridge.dependentCount() == 10 && bridge.wildCount() == 10);

    // Whistle through the driver recruits in place and claims the captain.
    P2BulbminCommand recruited = driver.whistle(7003, P2CaptainA);
    assert(recruited.accepted && recruited.phase == P2BulbminRecruited);
    assert(table.isOwned(7003) && table.ownerOf(7003) == P2CaptainA);

    // Leader death releases only the nine wild dependents; the whistled body
    // keeps its captain ownership and survives.
    std::vector<std::uint32_t> released = driver.leaderDied();
    assert(released.size() == 9);
    assert(bridge.size() == 1 && bridge.recruitedCount() == 1);
    assert(bridge.phaseOf(7003) == P2BulbminRecruited && table.isOwned(7003));
    assert(driver.bornCount() == 0);

    // A configured cap below ten bounds the flock even when ten are requested.
    P2BulbminBridge capped;
    P2BulbminConfig small;
    small.motherEpoch = 301;
    small.maxDependents = 3;
    assert(capped.setup(small));
    SpawnDouble cappedEngine = {&capped, 8000};
    P2BulbminDriver cappedDriver;
    assert(cappedDriver.bind(&capped, &spawn_double, &cappedEngine));
    assert(cappedDriver.birthFlock(10) == 3);
    assert(capped.dependentCount() == 3 && capped.wildCount() == 3);

    // Cave save filter through the driver: a floor descent keeps only the one
    // whistled Bulbmin; a full cave exit removes every Bulbmin.
    P2BulbminBridge cave;
    P2BulbminConfig caveConfig;
    caveConfig.motherEpoch = 400;
    caveConfig.maxDependents = 10;
    assert(cave.setup(caveConfig));
    SpawnDouble caveEngine = {&cave, 9000};
    P2BulbminDriver caveDriver;
    assert(caveDriver.bind(&cave, &spawn_double, &caveEngine));
    assert(caveDriver.birthFlock(10) == 10);
    assert(caveDriver.whistle(9000, P2CaptainA).accepted);
    P2BulbminTransitionOut down = caveDriver.transition(P2BulbminDescendFloor);
    assert(down.kept.size() == 1 && down.removed.size() == 9 && down.recruitedKept == 1);
    P2BulbminTransitionOut exitOut = caveDriver.transition(P2BulbminExitCave);
    assert(exitOut.kept.empty() && exitOut.removed.size() == 1 && cave.size() == 0);

    // An inert bridge cannot bind a driver.
    P2BulbminBridge inert;
    P2BulbminDriver inertDriver;
    SpawnDouble inertEngine = {&inert, 1};
    assert(!inertDriver.bind(&inert, &spawn_double, &inertEngine));
    assert(!inertDriver.bound() && inertDriver.birthFlock(10) == 0);
}

static void test_cave_transition() {
    P2BulbminBridge bridge;
    P2BulbminConfig config;
    config.motherEpoch = 200;
    config.maxDependents = 10;
    assert(bridge.setup(config));

    for (std::uint32_t i = 0; i < 10; ++i) assert(bridge.birth(5000 + i).accepted);
    assert(bridge.whistle(5000, P2CaptainA).accepted);

    // Floor descent keeps only the whistled Bulbmin.
    P2BulbminTransitionOut down = bridge.transition(P2BulbminDescendFloor);
    assert(down.kept.size() == 1 && down.removed.size() == 9 && down.recruitedKept == 1);
    assert(bridge.size() == 1 && bridge.phaseOf(5000) == P2BulbminRecruited);

    // Cave exit removes every Bulbmin, wild or recruited.
    P2BulbminTransitionOut exitOut = bridge.transition(P2BulbminExitCave);
    assert(exitOut.kept.empty() && exitOut.removed.size() == 1);
    assert(bridge.size() == 0);

    // An inert bridge filters nothing.
    P2BulbminBridge inert;
    assert(inert.transition(P2BulbminDescendFloor).kept.empty());
    assert(inert.transition(P2BulbminExitCave).removed.empty());
}

int main() {
    test_parse();
    test_birth_and_recruitment();
    test_driver();
    test_cave_transition();
    std::puts("PASS P2_BULBMIN_BRIDGE");
    return 0;
}
