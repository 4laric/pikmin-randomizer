#include "pc_p2_bulbmin.h"
#include <cassert>
#include <cstdio>
#include <sstream>
#include <string>

// Lane 11 (#131) dedicated Mother Bulbmin harness, sub-slice 3.
//
// Proves the opt-in mother registration path end to end at the engine-double
// level: a labeled mother identity is registered, the source LeafChappy ten-body
// birthChildren() flock is driven behind it, one body is whistled into the
// captain ownership table, mother death releases only wild dependents, and the
// cave save filter keeps only whistled Bulbmin on a descent and drops all on an
// exit. There is no LeafChappy/KumaChappy actor or model in the port, so the
// registered mother is the labeled Chappy-family Kochappy proxy. No rendered run
// and no invincibility are claimed here.

static bool read(const char* text, P2BulbminConfig& out) {
    std::istringstream in(text);
    return p2_bulbmin_read(in, out);
}

static void test_proxy_config_parse() {
    P2BulbminConfig config;

    // P2_BULBMIN_1 keeps the old three-token form; the label is optional.
    assert(read("P2_BULBMIN_1 100 10", config));
    assert(config.motherEpoch == 100 && config.maxDependents == 10);
    assert(config.motherModel == "kochappy_proxy");

    // An explicit proxy label is accepted on P2_BULBMIN_1.
    assert(read("P2_BULBMIN_1 100 10 kochappy_proxy", config));
    assert(config.motherModel == "kochappy_proxy");
    assert(read("P2_BULBMIN_1 7 3 chappy_bank", config));
    assert(config.motherModel == "chappy_bank");

    // P2_BULBMIN_2 is the same body with a required model label.
    assert(read("P2_BULBMIN_2 42 10 chappy_bank", config));
    assert(config.motherEpoch == 42 && config.maxDependents == 10);
    assert(config.motherModel == "chappy_bank");
    assert(!read("P2_BULBMIN_2 42 10", config));
    assert(read("P2_BULBMIN_2 42 10", config) == false);

    // Malformed labels and extra trailing tokens are rejected.
    assert(!read("P2_BULBMIN_1 100 10 bad label", config));
    assert(!read("P2_BULBMIN_1 100 10 bad/label", config));
    assert(!read("P2_BULBMIN_1 100 10 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", config));
    assert(!read("P2_BULBMIN_1 100 10 kochappy_proxy extra", config));
    assert(!read("P2_BULBMIN_2 42 10 kochappy_proxy extra", config));
}

// Engine double for the live pikiMgr->birth() callback: one body per call.
struct SpawnDouble {
    P2BulbminBridge* bridge;
    std::uint32_t nextId;
};

static std::uint32_t spawn_double(void* context, int) {
    SpawnDouble* engine = static_cast<SpawnDouble*>(context);
    const std::uint32_t id = engine->nextId++;
    return engine->bridge->birth(id).accepted ? id : 0;
}

static void test_dedicated_mother_registration() {
    // An inert bridge has no mother and refuses registration.
    P2BulbminBridge inert;
    int fakeHost = 0;
    assert(!inert.hasMother());
    assert(!inert.registerMother(&fakeHost, "kochappy_proxy", true));
    assert(inert.motherDied(&fakeHost) == -1);

    P2BulbminBridge bridge;
    P2CaptainOwnershipTable table;
    P2BulbminConfig config;
    config.motherEpoch = 900;
    config.maxDependents = P2BULBMIN_MAX_DEPENDENTS;
    config.motherModel = "chappy_bank";
    assert(bridge.setup(config, &table));
    assert(bridge.enabled() && !bridge.hasMother());

    int motherHost = 0;
    assert(bridge.registerMother(&motherHost, "", true));
    assert(bridge.hasMother() && bridge.motherIs(&motherHost));
    assert(bridge.motherActorInfo().proxy);
    // Empty label falls back to the configured proxy model.
    assert(bridge.motherActorInfo().model == "chappy_bank");

    // Re-registering the same host refreshes the label but is not "new".
    assert(!bridge.registerMother(&motherHost, "redwarf_bank", true));
    assert(bridge.motherActorInfo().model == "redwarf_bank");

    // A second, different host is refused: one mother per bridge.
    int otherHost = 0;
    assert(!bridge.registerMother(&otherHost, "kochappy_proxy", true));
    assert(bridge.motherIs(&motherHost) && !bridge.motherIs(&otherHost));

    // Death of a non-mother host is refused and leaves the registration intact.
    assert(bridge.motherDied(&otherHost) == -1);
    assert(bridge.hasMother());
}

static void test_mother_birth_whistle_death_cave() {
    P2BulbminBridge bridge;
    P2CaptainOwnershipTable table;
    P2BulbminConfig config;
    config.motherEpoch = 4242;
    config.maxDependents = P2BULBMIN_MAX_DEPENDENTS;
    config.motherModel = "kochappy_proxy";
    assert(bridge.setup(config, &table));

    int motherHost = 0;
    assert(bridge.registerMother(&motherHost, "kochappy_proxy", true));
    assert(bridge.hasMother() && bridge.motherIs(&motherHost));

    // Stage 1: the source birthChildren() ten-body flock.
    SpawnDouble engine = {&bridge, 3000};
    P2BulbminDriver driver;
    assert(driver.bind(&bridge, &spawn_double, &engine));
    assert(driver.birthFlock(10) == 10);
    assert(bridge.dependentCount() == 10 && bridge.wildCount() == 10);
    assert(bridge.recruitedCount() == 0);

    // Stage 2: whistle one body into the captain ownership table.
    assert(driver.whistle(3004, P2CaptainA).accepted);
    assert(bridge.phaseOf(3004) == P2BulbminRecruited);
    assert(table.isOwned(3004) && table.ownerOf(3004) == P2CaptainA);
    assert(bridge.wildCount() == 9 && bridge.recruitedCount() == 1);

    // Stage 3: mother death releases only the nine wild dependents.
    assert(bridge.motherDied(&motherHost) == 9);
    assert(!bridge.hasMother());
    assert(bridge.size() == 1 && bridge.recruitedCount() == 1);
    assert(bridge.phaseOf(3004) == P2BulbminRecruited && table.isOwned(3004));

    // Stage 4: cave filter. Floor descent keeps the whistled body; a cave exit
    // removes every Bulbmin.
    P2BulbminTransitionOut down = bridge.transition(P2BulbminDescendFloor);
    assert(down.kept.size() == 1 && down.removed.empty() && down.recruitedKept == 1);
    P2BulbminTransitionOut exitOut = bridge.transition(P2BulbminExitCave);
    assert(exitOut.kept.empty() && exitOut.removed.size() == 1 && bridge.size() == 0);

    // Forget drops a surviving body (engine Piki destruction).
    assert(bridge.forget(3000) == false); // already removed by the exit
}

static void test_transition_removes_is_nonmutating() {
    // The cave checkpoint computes the drop set before writing the transfer
    // file and commits the mutating transition only after a successful write, so
    // a failed write retry must still track every removed dependent. Prove the
    // non-mutating query (1) returns the correct drop set, (2) leaves the ledger
    // untouched, and (3) that only the mutating transition() erases bodies.
    P2BulbminBridge bridge;
    P2CaptainOwnershipTable table;
    P2BulbminConfig config;
    config.motherEpoch = 77;
    config.maxDependents = P2BULBMIN_MAX_DEPENDENTS;
    config.motherModel = "kochappy_proxy";
    assert(bridge.setup(config, &table));
    int motherHost = 0;
    assert(bridge.registerMother(&motherHost, "kochappy_proxy", true));

    SpawnDouble engine = {&bridge, 5000};
    P2BulbminDriver driver;
    assert(driver.bind(&bridge, &spawn_double, &engine));
    assert(driver.birthFlock(10) == 10);
    // Whistle two bodies so exactly eight wild dependents remain.
    assert(driver.whistle(5001, P2CaptainA).accepted);
    assert(driver.whistle(5002, P2CaptainA).accepted);
    assert(bridge.wildCount() == 8 && bridge.recruitedCount() == 2);

    // A failed-write retry path: the non-mutating query reports the eight wild
    // bodies without erasing them.
    const auto first = bridge.transitionRemoves(P2BulbminDescendFloor);
    assert(first.size() == 8);
    assert(bridge.size() == 10 && bridge.wildCount() == 8 && bridge.recruitedCount() == 2);
    const auto again = bridge.transitionRemoves(P2BulbminDescendFloor);
    assert(again.size() == 8); // identical drop set on retry

    // Commit after the (modeled) successful write: the eight wild bodies leave.
    P2BulbminTransitionOut commit = bridge.transition(P2BulbminDescendFloor);
    assert(commit.removed.size() == 8 && commit.kept.size() == 2);
    assert(bridge.wildCount() == 0 && bridge.recruitedCount() == 2);
}

int main() {
    test_proxy_config_parse();
    test_dedicated_mother_registration();
    test_mother_birth_whistle_death_cave();
    test_transition_removes_is_nonmutating();
    std::puts("PASS P2_BULBMIN_MOTHER");
    return 0;
}
