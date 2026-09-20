// Sarai seed-bridge campaign test (rd-p2ap-sarai, #439). Engine-free: stub
// engine headers shadow the real ones (BEFORE pc_port), so the REAL
// pc_p2_generated_placement.cpp compiles against doubles for
// tekiMgr/Generator. The Sarai dynamic binder is doubled here with the real
// contract (first claim wins; absent sidecar refuses quietly, mirroring
// buildHost returning null); the real binder ships in pc_p2_sarai_manager.cpp
// and is compile-verified by the full engine build.
//
// Covers the Definition of done: bridge mode binds all campaign ids for
// source 23 with no env var, several copies allowed; an absent sidecar
// returns quietly; the generated-placement dispatcher stays wired to the
// Sarai dynamic binder (birth-time claim) alongside the setup-time sweep.
#include "teki.h"
#include "Generator.h"
#include "pc_p2_generated_placement.h"

#include <cstdio>
#include <cstdlib>
#include <map>
#include <string>
#include <vector>

// --- Engine doubles -------------------------------------------------------
TekiMgr manager;
TekiMgr* tekiMgr = &manager;

namespace {
int gChecks = 0;
bool gBridge = false;
bool gHostPresent = true; // false mirrors buildHost returning null
std::map<unsigned long, unsigned> gSourceForUid;
std::map<const void*, unsigned> gUidForGenerator;
std::vector<Generator*> gGenerators;
std::vector<BTeki*> gActors;

struct BindCall {
    const BTeki* actor;
    unsigned generatorId;
    unsigned seedTargetUid;
};
std::vector<BindCall> gBindCalls;
std::vector<const BTeki*> gBound;

void require(bool ok, const char* what)
{
    ++gChecks;
    if (!ok) {
        std::printf("FAIL p2_sarai_campaign_test: %s\n", what);
        std::fflush(stdout);
        std::exit(1);
    }
}

BTeki* makeActor(unsigned uid, unsigned source, unsigned token70)
{
    Generator* gen = new Generator();
    gen->_70 = token70;
    BTeki* actor = new BTeki();
    actor->mGenerator = gen;
    gUidForGenerator[gen] = uid;
    gSourceForUid[uid] = source;
    gGenerators.push_back(gen);
    gActors.push_back(actor);
    manager.actors.push_back(actor);
    return actor;
}

void clearActors()
{
    manager.actors.clear();
    for (BTeki* actor : gActors) delete actor;
    for (Generator* gen : gGenerators) delete gen;
    gActors.clear();
    gGenerators.clear();
    gUidForGenerator.clear();
    gSourceForUid.clear();
}

void resetBinds()
{
    gBindCalls.clear();
    gBound.clear();
    gHostPresent = true;
}
} // namespace

// --- Randomizer bridge doubles --------------------------------------------
bool pc_randomizer_p2_bridge() { return gBridge; }
unsigned pc_randomizer_p2_source_for_id(unsigned long id)
{
    auto it = gSourceForUid.find(id);
    return it == gSourceForUid.end() ? 0 : it->second;
}
unsigned pc_randomizer_generator_id(const void* generator)
{
    auto it = gUidForGenerator.find(generator);
    return it == gUidForGenerator.end() ? 0 : it->second;
}
void pc_randomizer_set_generator_id(const void*, unsigned) {}

// --- Sibling modules (not under test here) --------------------------------
bool pc_p2_otakara_bind_dynamic(BTeki*, unsigned, unsigned) { return false; }
bool pc_p2_bluechappy_bind_dynamic(BTeki*, unsigned, unsigned) { return false; }

// --- Sarai dynamic binder double (real contract) ---------------------------
// Mirrors pc_p2_sarai_manager_bind_dynamic: refuses null/zero/already-bound
// actors and refuses quietly when the sidecar host cannot be built.
bool pc_p2_sarai_manager_bind_dynamic(BTeki* actor, unsigned generatorId, unsigned seedTargetUid)
{
    if (!actor || !generatorId || !seedTargetUid) return false;
    for (const BTeki* bound : gBound)
        if (bound == actor) return false;
    if (!gHostPresent) return false;
    gBindCalls.push_back({actor, generatorId, seedTargetUid});
    gBound.push_back(actor);
    return true;
}

int main()
{
    // 1. Bridge sweep binds every campaign id for 23 with no env var set.
    gBridge = true;
    resetBinds();
    clearActors();
    pc_p2_generated_placement_reset();
    BTeki* first = makeActor(5465461u, 23, 1001);
    BTeki* second = makeActor(328297937u, 23, 1002);
    BTeki* third = makeActor(407876267u, 23, 1003);
    BTeki* other = makeActor(513430982u, 44, 1004); // BlueKochappy: skipped
    require(std::getenv("PIKMIN_SARAI_ORDINARY") == nullptr
                || std::string(std::getenv("PIKMIN_SARAI_ORDINARY")) != "1",
            "bridge sweep must not need the ordinary env var");
    require(pc_p2_generated_placement_sweep_sarai(), "sweep claims the source-23 actors");
    require(gBindCalls.size() == 3, "sweep binds all three source-23 actors");
    for (const BindCall& call : gBindCalls) {
        require(call.actor == first || call.actor == second || call.actor == third,
                "sweep binds only source-23 actors");
        require(call.actor != other, "sweep skips the source-44 actor");
        const unsigned uid = pc_randomizer_generator_id(call.actor->mGenerator);
        require(call.generatorId == uid && call.seedTargetUid == uid, "sweep passes the campaign token");
    }
    require(!pc_p2_generated_placement_sweep_sarai(), "repeat sweep claims nothing new");
    require(gBindCalls.size() == 3, "repeat sweep does not double-bind");

    // 2. Absent sidecar returns quietly: no claim, no abort.
    resetBinds();
    gHostPresent = false;
    require(!pc_p2_generated_placement_sweep_sarai(), "absent sidecar claims nothing quietly");
    require(gBindCalls.empty(), "absent sidecar leaves no claim");

    // 3. Empty campaign set and bridge-off both return quietly.
    resetBinds();
    clearActors();
    require(!pc_p2_generated_placement_sweep_sarai(), "empty campaign set claims nothing");
    makeActor(5465461u, 23, 1001);
    gBridge = false;
    require(!pc_p2_generated_placement_sweep_sarai(), "bridge-off claims nothing");
    gBridge = true;

    // 4. Generated-placement dispatch stays wired to the Sarai dynamic binder.
    resetBinds();
    clearActors();
    pc_p2_generated_placement_reset();
    BTeki* placed = makeActor(568677317u, 23, 2001);
    require(pc_p2_generated_placement_bind(placed, 23, 568677317u, 568677317u),
            "placement bind claims source 23");
    require(gBindCalls.size() == 1 && gBindCalls[0].actor == placed
                && gBindCalls[0].generatorId == 568677317u && gBindCalls[0].seedTargetUid == 568677317u,
            "placement bind forwards actor, generator and target to the Sarai binder");
    require(!pc_p2_generated_placement_bind(nullptr, 23, 568677317u, 568677317u),
            "null actor rejected quietly");
    require(!pc_p2_generated_placement_bind(placed, 98, 568677317u, 568677317u),
            "unknown source rejected quietly");

    // 5. Placement bind with an absent sidecar fails quietly (not wired away).
    resetBinds();
    gHostPresent = false;
    clearActors();
    BTeki* unplaced = makeActor(873045719u, 23, 2002);
    require(!pc_p2_generated_placement_bind(unplaced, 23, 873045719u, 873045719u),
            "absent sidecar fails the dynamic bind quietly");
    require(gBindCalls.empty(), "failed bind leaves no claim");

    clearActors();
    resetBinds();
    std::printf("p2_sarai_campaign_test PASS checks=%d\n", gChecks);
    std::fflush(stdout);
    return 0;
}
