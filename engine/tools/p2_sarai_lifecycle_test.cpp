// Sarai23 manager/central-seam lifecycle test (rd-p2-sarai-combat-repair,
// #828, supervisor finding 2).
//
// What is REAL here: the production pc_p2_sarai_manager.cpp TU compiles
// unchanged; the real P2SaraiHost class declaration with all of its real
// support headers (FSM, captor, lifecycle, pose bank, retail table); the
// real pc_p2_campaign_actor.h token logic; the real pc_randomizer_p2_roster.h
// bindability rule; the real retail motion-table reader (the staged events
// file below is valid P2_RETAIL_EVENTS_1, so the manager's own motion-name
// matching loop runs); and the real pc_p2_delivery_host.cpp ledger that the
// campaign receipt path calls.
// What is doubled: the engine (actor/transform/roster walk), the host
// behavior bodies (build gate plus binding bookkeeping with the production
// one-actor contract, defined in this TU against the real class), the
// generated-placement sweep routing (bridge coverage lives in
// p2_sarai_seed_bridge_test), and the central pointer->source index with the
// EXACT documented contract of pc_randomizer.cpp:517-538 (roster gate
// logged, store on bind, erase on forget). The durable Granted/Duplicate
// ledger itself is never reimplemented: the rebind sequence below delivers
// through the real delivery host.
// Covers the Definition of done lifecycle: ordinary setup binds source 23
// with the delivery marker; repeated setup never double-binds; dynamic bind
// claims fresh actors and refuses null/zero/already-bound; forget drops the
// central binding; death retains the anchor with the receipt intact; reset
// drops live AND corpse-map central bindings (the review defect: pre-fix
// defect: pre-fix reset stranded them for recycled addresses); rebind after
// reset delivers exactly once on the real ledger; bridge-mode setup claims
// nothing.
// Exit 0 only if every check passes; any failure prints FAIL and exits 1.
#include "teki.h"
#include "Generator.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_sarai_manager.h"
#include "pc_p2_sarai_host.h"
#include "pc_p2_delivery_host.h"
#include "pc_randomizer_p2_roster.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <map>
#include <string>
#include <utility>
#include <vector>

#ifdef _WIN32
#include <process.h>
inline int currentPid() { return _getpid(); }
#else
#include <unistd.h>
inline int currentPid() { return static_cast<int>(getpid()); }
#endif

// --- Host behavior definitions (real P2SaraiHost class; test-owned bodies)
// Only what the manager drives is defined: the build gate plus binding
// bookkeeping with the production one-actor contract (revalidate re-derives
// the campaign token exactly like the native host). Visual/FSM/captor
// behavior is out of scope here (host/captor/capture suites own it).
bool gSaraiHostPresent = true;
int gHostUnbinds = 0;

P2SaraiHost::P2SaraiHost() = default;
P2SaraiHost::~P2SaraiHost() = default;
void P2SaraiHost::update() {}
void P2SaraiHost::refresh(Graphics&) {}
void P2SaraiHost::doKill() {}
int P2SaraiHost::naturalPhase() const { return 1; }
bool P2SaraiHost::load(const char* modelPath, const Vector3f&, const Vector3f&)
{
    return gSaraiHostPresent && modelPath != nullptr;
}
bool P2SaraiHost::preloadPoseMeshes(const char* profile) { return gSaraiHostPresent && profile != nullptr; }
bool P2SaraiHost::applyPoseFrame(int) { return gSaraiHostPresent; }
void P2SaraiHost::setNaturalMotions(const p2retail::Motion&, const p2retail::Motion&, const p2retail::Motion&,
                                    const p2retail::Motion&, const p2retail::Motion&) {}
void P2SaraiHost::setNaturalPoseProfiles(const char*, const char*, const char*, const char*, const char*) {}
void P2SaraiHost::setPosition(const Vector3f& position) { mSRT.t = position; }
void P2SaraiHost::enableNatural(float, float, float, float, float, float, float, const Vector3f&)
{
    mNaturalEnabled = true;
}
bool P2SaraiHost::bindNativeActor(BTeki* actor, unsigned generatorId, int tekiType)
{
    if (!actor || (mBoundActor && mBoundActor != actor)) return false;
    mBoundActor = actor;
    mDead = false;
    (void)generatorId;
    (void)tekiType;
    return true;
}
void P2SaraiHost::unbindNativeActor(BTeki* actor)
{
    if (actor && mBoundActor == actor) {
        mBoundActor = nullptr;
        ++gHostUnbinds;
    }
}
bool P2SaraiHost::revalidateNativeActor(BTeki* actor, unsigned generatorId, int tekiType)
{
    if (!actor || mBoundActor != actor) return false;
    if (!actor->mGenerator || pc_p2_campaign_token(actor) != generatorId || actor->mTekiType != tekiType) {
        mBoundActor = nullptr;
        return false;
    }
    return true;
}

// --- Engine doubles --------------------------------------------------------
TekiMgr manager;
TekiMgr* tekiMgr = &manager;

namespace {
int gChecks = 0;
int gFailures = 0;

#define CHECK(cond, name) do { \
    ++gChecks; \
    if (cond) { std::printf("PASS %s\n", name); } \
    else { std::printf("FAIL %s\n", name); ++gFailures; } \
} while (0)

bool gBridge = false;
std::map<const Generator*, unsigned> gUidForGenerator;
std::map<unsigned, unsigned> gSourceForUid;

struct CentralCall {
    std::string kind;
    const void* view;
    unsigned source;
    unsigned generator;
};
std::vector<CentralCall> gCentralCalls;
// Faithful minimal store for the central pointer->source index contract
// (pc_randomizer.cpp: bind stores source+generatorUid gated by the real
// roster; forget erases; close/reopen is the real ledger's job).
std::map<const void*, std::pair<unsigned, unsigned>> gCentralSources;

std::vector<Generator*> gGenerators;
std::vector<BTeki*> gActors;

void require(bool ok, const char* what)
{
    ++gChecks;
    if (!ok) {
        std::printf("FAIL p2_sarai_lifecycle_test: %s\n", what);
        std::fflush(stdout);
        std::exit(1);
    }
}

BTeki* makeActor(unsigned token70, int type, float health)
{
    Generator* gen = new Generator();
    gen->_70 = token70;
    BTeki* actor = new BTeki();
    actor->mGenerator = gen;
    actor->mTekiType = type;
    actor->mHealth = health;
    actor->alive = true;
    actor->mSRT.t.set(10.0f, 0.0f, 20.0f);
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

int countCalls(const char* kind, const void* view)
{
    int n = 0;
    for (const CentralCall& c : gCentralCalls)
        if (c.kind == kind && (!view || c.view == view)) ++n;
    return n;
}

bool centralBound(const void* view, unsigned source, unsigned generator)
{
    const auto it = gCentralSources.find(view);
    return it != gCentralSources.end() && it->second.first == source && it->second.second == generator;
}
} // namespace

// --- Randomizer bridge doubles (routing; cf. test_p2_sarai_campaign.cpp) ---
bool pc_randomizer_p2_bridge() { return gBridge; }
unsigned pc_randomizer_p2_source_for_id(unsigned long id)
{
    const auto it = gSourceForUid.find(unsigned(id));
    return it == gSourceForUid.end() ? 0 : it->second;
}
unsigned pc_randomizer_generator_id(const void* generator)
{
    const auto it = gUidForGenerator.find(static_cast<const Generator*>(generator));
    return it == gUidForGenerator.end() ? 0 : it->second;
}

// --- Central delivery-index doubles (recording; real roster gating) ---------
void pc_randomizer_p2_bind_source(const void* tekiview, unsigned sourceId, unsigned generatorUid)
{
    gCentralCalls.push_back({"bind", tekiview, sourceId, generatorUid});
    if (!tekiview || !sourceId) return;
    if (!randomizerP2IsBindable(sourceId)) {
        std::printf("[Pikmin Randomizer] P2_DELIVERY_BIND_REJECTED source=%u\n", sourceId);
        return;
    }
    gCentralSources[tekiview] = {sourceId, generatorUid};
}
void pc_randomizer_p2_forget_source(const void* tekiview)
{
    gCentralCalls.push_back({"forget", tekiview, 0, 0});
    if (!tekiview) return;
    gCentralSources.erase(tekiview);
}

// --- Generated-placement routing double (bridge sweep only) ----------------
bool pc_p2_generated_placement_sweep_sarai()
{
    gCentralCalls.push_back({"sweep", nullptr, 0, 0});
    return false;
}

namespace {
constexpr unsigned kOrdinaryGen = 385875968u;
constexpr unsigned kDynamicGen = 568677317u;
constexpr int kChappy = 3;

void writeStagedFiles(const std::filesystem::path& dir)
{
    // The manager parses the mouth bank itself (magic + frame + 24 floats).
    // The retail-events table below is in the REAL P2_RETAIL_EVENTS_1 format
    // (registry sha + 5 named motions, zero events each), so the real table
    // reader and the manager's own motion-name matching loop both run.
    std::ofstream mouths(dir / "sarai-attack-mouths.txt");
    mouths << "P2_DEMON_MOUTHS_1 test 1\n0\n";
    for (int i = 0; i < 24; ++i) mouths << "1.0" << (i == 23 ? "\n" : " ");
    std::ofstream events(dir / "sarai-retail-events.txt");
    events << "P2_RETAIL_EVENTS_1 0000000000000000000000000000000000000000000000000000000000000000 5\n";
    for (const char* name : {"wait1.bca", "move1.bca", "attack1.bca", "waitact2.bca", "waitact1.bca"})
        events << name << " 100 0 0000000000000000000000000000000000000000000000000000000000000000 0\n";
}
} // namespace

int main()
{
    namespace fs = std::filesystem;
    const auto dir = fs::temp_directory_path()
        / ("p2-sarai-lifecycle-test-" + std::to_string(currentPid()));
    fs::create_directories(dir);
    writeStagedFiles(dir);
    const auto savedCwd = fs::current_path();
    fs::current_path(dir);

#ifdef _WIN32
    _putenv_s("PIKMIN_SARAI_ORDINARY", "1");
#else
    setenv("PIKMIN_SARAI_ORDINARY", "1", 1);
#endif

    // 1. Ordinary setup binds source 23 with the delivery marker; the central
    // index holds exactly this actor; the corpse receipt resolves it.
    gBridge = false;
    gSaraiHostPresent = true;
    gCentralCalls.clear();
    gCentralSources.clear();
    clearActors();
    pc_p2_sarai_manager_reset();
    gCentralCalls.clear();
    BTeki* first = makeActor(kOrdinaryGen, kChappy, 130.0f);
    pc_p2_sarai_manager_setup();
    CHECK(countCalls("bind", first) == 1, "setup-binds-once");
    CHECK(centralBound(first, 23, kOrdinaryGen), "setup-central-index");
    CHECK(pc_p2_sarai_manager_bound_count() == 1, "setup-bound-count");
    unsigned resolved = 0;
    CHECK(pc_p2_sarai_receipt(first, resolved) && resolved == kOrdinaryGen, "setup-receipt");

    // 2. Repeated setup never double-binds (first bind wins).
    pc_p2_sarai_manager_setup();
    CHECK(countCalls("bind", first) == 1, "repeat-setup-no-double-bind");
    CHECK(pc_p2_sarai_manager_bound_count() == 1, "repeat-setup-count");

    // 3. Dynamic binding claims fresh actors and refuses bad ones.
    BTeki* second = makeActor(kDynamicGen, kChappy, 130.0f);
    CHECK(pc_p2_sarai_manager_bind_dynamic(second, kDynamicGen, kDynamicGen), "dynamic-binds");
    CHECK(centralBound(second, 23, kDynamicGen), "dynamic-central-index");
    CHECK(!pc_p2_sarai_manager_bind_dynamic(nullptr, kDynamicGen, kDynamicGen), "dynamic-rejects-null");
    CHECK(!pc_p2_sarai_manager_bind_dynamic(second, 0, kDynamicGen), "dynamic-rejects-zero");
    CHECK(!pc_p2_sarai_manager_bind_dynamic(second, kDynamicGen, kDynamicGen), "dynamic-rejects-bound");
    CHECK(pc_p2_sarai_manager_bound_count() == 2, "dynamic-count");

    // 4. Forget drops the central binding; the survivor is untouched.
    pc_p2_sarai_manager_forget(first);
    CHECK(countCalls("forget", first) == 1, "forget-central-drop");
    CHECK(!centralBound(first, 23, kOrdinaryGen), "forget-index-cleared");
    CHECK(!pc_p2_sarai_receipt(first, resolved), "forget-receipt-gone");
    CHECK(pc_p2_sarai_manager_bound_count() == 1, "forget-survivor-count");
    CHECK(centralBound(second, 23, kDynamicGen), "forget-survivor-index");

    // 5. Death retains the anchor in the live map AND records the corpse map
    // entry (observed production contract: update_actor keeps the s entry
    // while adding corpses, so bound_count counts it twice; receipt still
    // resolves). The double-count is pre-existing behavior, out of scope.
    second->alive = false;
    pc_p2_sarai_manager_update_actor(second);
    CHECK(pc_p2_sarai_manager_bound_count() == 2, "death-live-plus-corpse-count");
    CHECK(pc_p2_sarai_receipt(second, resolved) && resolved == kDynamicGen, "death-receipt");

    // 6. Reset drops live AND corpse-map central bindings (the review
    // defect): no stale source-23 entry may survive stage teardown.
    const int unbindsBefore = gHostUnbinds;
    pc_p2_sarai_manager_reset();
    CHECK(countCalls("forget", second) >= 1, "reset-forgets-corpse-binding");
    CHECK(gCentralSources.empty(), "reset-central-empty");
    CHECK(gHostUnbinds > unbindsBefore, "reset-unbinds-hosts");
    CHECK(pc_p2_sarai_manager_bound_count() == 0, "reset-count-zero");
    CHECK(!pc_p2_sarai_receipt(second, resolved), "reset-receipt-gone");

    // 7. Rebind after reset works and delivers exactly once on the REAL
    // ledger across the reset boundary.
    gCentralCalls.clear();
    second->alive = true;
    second->mHealth = 130.0f;
    CHECK(pc_p2_sarai_manager_bind_dynamic(second, kDynamicGen, kDynamicGen), "rebind-after-reset");
    CHECK(centralBound(second, 23, kDynamicGen), "rebind-central-index");
    const std::string ledger = (dir / "receipts.txt").string();
    fs::remove(ledger);
    P2DeliveryHostHandle h = pc_p2_delivery_host_open(ledger.c_str());
    require(h != nullptr, "rebind-ledger-open");
    using R = P2DeliveryHostResult;
    CHECK(pc_p2_delivery_host_deliver(h, "sarai-lifecycle", 23, kChappy, 1, kDynamicGen, "corpse") == R::Granted,
          "rebind-first-granted");
    CHECK(pc_p2_delivery_host_deliver(h, "sarai-lifecycle", 23, kChappy, 1, kDynamicGen, "corpse") == R::Duplicate,
          "rebind-repeat-duplicate");
    pc_p2_delivery_host_close(h);

    // 8. Bridge-mode setup claims nothing itself (sweep routing).
    clearActors();
    pc_p2_sarai_manager_reset();
    gBridge = true;
    gCentralCalls.clear();
    BTeki* bridged = makeActor(999u, kChappy, 130.0f);
    (void)bridged;
    pc_p2_sarai_manager_setup();
    CHECK(countCalls("sweep", nullptr) == 1, "bridge-sweep-routed");
    CHECK(countCalls("bind", nullptr) == 0, "bridge-no-direct-bind");
    CHECK(pc_p2_sarai_manager_bound_count() == 0, "bridge-count-zero");
    gBridge = false;

    // 9. Missing sidecar/model binds nothing and stays silent-ish.
    clearActors();
    pc_p2_sarai_manager_reset();
    gSaraiHostPresent = false;
    gCentralCalls.clear();
    makeActor(kOrdinaryGen, kChappy, 130.0f);
    pc_p2_sarai_manager_setup();
    CHECK(countCalls("bind", nullptr) == 0, "absent-sidecar-no-bind");
    CHECK(pc_p2_sarai_manager_bound_count() == 0, "absent-sidecar-count-zero");
    gSaraiHostPresent = true;

    fs::current_path(savedCwd);
#ifdef _WIN32
    _putenv_s("PIKMIN_SARAI_ORDINARY", "");
#else
    unsetenv("PIKMIN_SARAI_ORDINARY");
#endif
    clearActors();
    pc_p2_sarai_manager_reset();

    if (gFailures == 0) std::printf("PASS P2_SARAI_LIFECYCLE checks=%d\n", gChecks);
    else std::printf("P2_SARAI_LIFECYCLE pass=0 failures=%d checks=%d\n", gFailures, gChecks);
    return gFailures == 0 ? 0 : 1;
}
