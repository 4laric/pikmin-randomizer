// Sarai23 combat-repair regression test (rd-p2-sarai-combat-repair, #828).
//
// Engine-free proof over the REAL ordinary-delivery bridge
// (pc_p2_delivery_host.cpp, the same seam pc_randomizer_p2_corpse_delivered
// calls when GoalItem::suckMe absorbs a hauled corpse) plus the standalone
// source weigh-down policy (pc_p2_sarai_policy.h) that the repaired host now
// feeds with live anchor facts. No engine is booted, no health/state is
// written, no Transport is assigned.
//
// Delivery half: corpse (source 23, ordinary generator 385875968, encounter
// "corpse") -> Granted once; any repeat of the same corpse tuple ->
// Duplicate (never a second receipt), durable across close/reopen (process
// restart); a second generator is a distinct actor with its own receipt.
// Fail-closed inputs (null handle/seed/encounter, unbound source 0) return
// Error and grant nothing.
//
// Policy half: with no body-latched Pikmin the height decision is None (the
// host keeps flying: the pre-fix hardcoded zero could never leave this
// state); death or a Purple latch forces Fall; one latched Pikmin resolves
// deterministically at the random-unit extremes (0.0 -> Flick, ~1.0 ->
// Fall); the stick census excludes mouth captives; the climb factor falls as
// weight rises; the Attack catch window opens only past frame 16.
//
// The family delivery bind itself (pc_p2_sarai_manager_setup /
// pc_p2_sarai_manager_bind_dynamic binding source 23 to the live actor with a
// P2_SARAI_DELIVERY_BIND marker) is covered by the guarded combat fixture
// (tools/p2_sarai_combat_repair_runtime.cpp): this test proves the receipt
// half of that path is exactly-once, so a carried Sarai corpse can yield one
// and only one onion:p2:23 receipt.
//
// Optional log mode: p2_sarai_combat_repair_test <native.log> additionally
// verifies the combat-repair run ordering (READY + DELIVERY_BIND, then
// controller-driven throws, then DAMAGE before DEAD, then exactly one
// onion:p2:23 receipt with new=1, with no injected markers).
//
// Exit 0 only if every check passes; any failure prints FAIL and exits 1.
#include "pc_p2_delivery_host.h"
#include "pc_p2_sarai_policy.h"
#include "pc_randomizer_p2_roster.h"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <string>

#ifdef _WIN32
#include <process.h>
inline int currentPid() { return _getpid(); }
#else
#include <unistd.h>
inline int currentPid() { return static_cast<int>(getpid()); }
#endif

namespace {

constexpr unsigned kSourceId = 23;
constexpr unsigned kOrdinaryGen = 385875968u;
constexpr unsigned kDynamicGen = 568677317u;
constexpr int kTekiType = 3; // P1-proxy Chappy anchor type, disjoint from the P2 source id
constexpr int kStage = 1;
constexpr const char* kEncounter = "corpse";
constexpr const char* kSeed = "sarai23-combat-repair-test";

int failures = 0;

#define CHECK(cond, name) do { \
    if (cond) { std::printf("PASS %s\n", name); } \
    else { std::printf("FAIL %s\n", name); ++failures; } \
} while (0)

using R = P2DeliveryHostResult;

int ledgerMentions(const std::string& path, const char* token)
{
    std::ifstream in(path);
    if (!in) return 0;
    int count = 0;
    std::string line;
    while (std::getline(in, line)) {
        if (line.find(token) != std::string::npos) ++count;
    }
    return count;
}

// Combat-repair log ordering check: bind markers, controller-driven throws,
// damage after the first throw, no injected markers anywhere. Death and the
// Onion receipt are stage-aware: a DEAD line without prior damage fails, and
// any onion:p2:23 receipt must be exactly one with new=1 -- but an
// engagement-only run (damage, no death yet) is not failed for lacking them.
// Setup markers alone never prove a delivery.
int checkCombatLog(const char* logPath)
{
    std::ifstream in(logPath);
    if (!in) {
        std::printf("FAIL log-open path=%s\n", logPath);
        return 1;
    }
    std::string text((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());

    static const char* const kInjected[] = {
        "P2_SARAI_INJECT", "P2_LIFECYCLE_INJECT", "injected_health", "mHealth=",
        "InteractAttack", "not_natural_combat=1",
    };
    for (const char* token : kInjected) {
        if (text.find(token) != std::string::npos) {
            std::printf("FAIL log-injected token=%s\n", token);
            return 1;
        }
    }
    const size_t readyAt = text.find("P2_SARAI_READY source_id=23");
    // The manager binds the delivery source immediately before printing
    // READY, so DELIVERY_BIND precedes it; both must precede the throws.
    const size_t bindAt = text.find("P2_SARAI_DELIVERY_BIND generator=");
    if (readyAt == std::string::npos) {
        std::printf("FAIL log-missing-ready\n");
        return 1;
    }
    if (bindAt == std::string::npos) {
        std::printf("FAIL log-missing-delivery-bind\n");
        return 1;
    }
    const size_t throwAt = text.find("P2_SARAI_COMBAT_THROW");
    if (throwAt == std::string::npos || throwAt < bindAt || throwAt < readyAt) {
        std::printf("FAIL log-missing-controller-throw-after-bind\n");
        return 1;
    }
    const size_t damageAt = text.find("P2_SARAI_COMBAT_DAMAGE");
    const size_t deadAt = text.find("P2_SARAI_DEAD source_id=23");
    if (damageAt == std::string::npos || damageAt < throwAt) {
        std::printf("FAIL log-missing-damage-after-throw\n");
        return 1;
    }
    if (deadAt != std::string::npos && deadAt < damageAt) {
        std::printf("FAIL log-death-before-damage\n");
        return 1;
    }
    int receipts = 0, grants = 0;
    for (size_t at = 0; (at = text.find("id=onion:p2:23:", at)) != std::string::npos; ++at) {
        ++receipts;
        const size_t newAt = text.find("new=", at);
        if (newAt != std::string::npos && text.compare(newAt + 4, 1, "1") == 0) ++grants;
    }
    if (receipts > 1 || grants > 1 || (receipts == 1 && grants != 1)) {
        std::printf("FAIL log-receipt-not-exactly-once receipts=%d grants=%d\n", receipts, grants);
        return 1;
    }
    if (deadAt == std::string::npos) {
        std::printf("PASS P2_SARAI_COMBAT_LOG bind=1 throws=1 damage=1 death=0 receipts=%d\n", receipts);
        return 0;
    }
    std::printf("PASS P2_SARAI_COMBAT_LOG bind=1 throws=1 damage_before_death=1 receipts=%d\n", receipts);
    return 0;
}

} // namespace

int main(int argc, char** argv)
{
    namespace fs = std::filesystem;
    const auto dir = fs::temp_directory_path()
        / ("p2-sarai-combat-repair-test-" + std::to_string(currentPid()));
    fs::create_directories(dir);
    const std::string path = (dir / "receipts.txt").string();
    fs::remove(path);

    P2DeliveryHostHandle h = pc_p2_delivery_host_open(path.c_str());
    CHECK(h != nullptr, "open-ledger");
    CHECK(pc_p2_delivery_host_path(h) != nullptr
        && std::strcmp(pc_p2_delivery_host_path(h), path.c_str()) == 0, "open-path");

    // Fail-closed: nothing grants without a live handle, a seed, an encounter,
    // or a bound source.
    CHECK(pc_p2_delivery_host_deliver(nullptr, kSeed, kSourceId, kTekiType,
        kStage, kOrdinaryGen, kEncounter) == R::Error, "failclosed-null-handle");
    CHECK(pc_p2_delivery_host_deliver(h, nullptr, kSourceId, kTekiType,
        kStage, kOrdinaryGen, kEncounter) == R::Error, "failclosed-null-seed");
    CHECK(pc_p2_delivery_host_deliver(h, kSeed, 0, kTekiType,
        kStage, kOrdinaryGen, kEncounter) == R::Error, "failclosed-unbound-source");
    CHECK(pc_p2_delivery_host_deliver(h, kSeed, kSourceId, kTekiType,
        kStage, kOrdinaryGen, nullptr) == R::Error, "failclosed-null-encounter");
    CHECK(ledgerMentions(path, "onion:p2:23") == 0, "failclosed-grants-nothing");

    // Corpse carried to the Onion: the bound source-23 delivery grants once.
    CHECK(pc_p2_delivery_host_deliver(h, kSeed, kSourceId, kTekiType,
        kStage, kOrdinaryGen, kEncounter) == R::Granted, "corpse-first-granted");
    CHECK(ledgerMentions(path, "onion:p2:23:1") == 1, "corpse-count-one");

    // The same corpse re-delivered is a durable duplicate, never a receipt.
    CHECK(pc_p2_delivery_host_deliver(h, kSeed, kSourceId, kTekiType,
        kStage, kOrdinaryGen, kEncounter) == R::Duplicate, "corpse-repeat-duplicate");
    CHECK(ledgerMentions(path, "onion:p2:23:1") == 1, "corpse-still-one");

    // The dynamic-bind generator is a distinct actor with its own receipt.
    CHECK(pc_p2_delivery_host_deliver(h, kSeed, kSourceId, kTekiType,
        kStage, kDynamicGen, kEncounter) == R::Granted, "dynamic-granted");
    CHECK(ledgerMentions(path, "onion:p2:23:1") == 2, "dynamic-count-two");
    CHECK(pc_p2_delivery_host_deliver(h, kSeed, kSourceId, kTekiType,
        kStage, kDynamicGen, kEncounter) == R::Duplicate, "dynamic-repeat-duplicate");

    // Process restart over the same path never re-grants a carried corpse.
    pc_p2_delivery_host_close(h);
    h = pc_p2_delivery_host_open(path.c_str());
    CHECK(h != nullptr, "reopen-ledger");
    CHECK(pc_p2_delivery_host_deliver(h, kSeed, kSourceId, kTekiType,
        kStage, kOrdinaryGen, kEncounter) == R::Duplicate, "restart-corpse-duplicate");
    CHECK(ledgerMentions(path, "onion:p2:23:1") == 2, "restart-count-two");
    pc_p2_delivery_host_close(h);

    // Roster admission: source 23 is bindable, so the family delivery bind
    // the manager performs cannot be a REJECTED no-op; source 0 is not.
    CHECK(randomizerP2IsBindable(kSourceId), "roster-23-bindable");
    CHECK(!randomizerP2IsBindable(0), "roster-0-unbindable");

    // Weigh-down policy: the repaired host feeds these decisions with the
    // anchor's live sticker census instead of a hardcoded zero.
    using namespace p2sarai;
    const Parms parms;
    CHECK(stickPikminNum(0, 0) == 0, "policy-no-attackers-zero");
    CHECK(stickPikminNum(3, 1) == 2, "policy-body-excludes-mouth");
    CHECK(nextStateOnHeight(parms, 100.0f, 0, 0, false, 0.0f) == HeightDecision::None,
        "policy-clean-climb-continues");
    CHECK(nextStateOnHeight(parms, 0.0f, 0, 0, false, 0.99f) == HeightDecision::Fall,
        "policy-death-falls");
    CHECK(nextStateOnHeight(parms, 100.0f, 0, 3, true, 0.99f) == HeightDecision::Fall,
        "policy-purple-falls");
    CHECK(nextStateOnHeight(parms, 100.0f, 0, 1, false, 0.0f) == HeightDecision::Flick,
        "policy-lone-attacker-flicks-at-zero");
    CHECK(nextStateOnHeight(parms, 100.0f, 0, 1, false, 0.999f) == HeightDecision::Fall,
        "policy-lone-attacker-falls-at-one");
    CHECK(climbingFactor(parms, 0) > climbingFactor(parms, 5), "policy-weight-slows-climb");
    CHECK(!attackMayCatch(16.0f) && attackMayCatch(16.5f), "policy-catch-window-past-16");

    if (argc > 1) {
        if (checkCombatLog(argv[1]) != 0) ++failures;
    }

    fs::remove(path);
    fs::remove(dir);

    if (failures == 0) std::printf("PASS P2_SARAI_COMBAT_REPAIR source=23 granted=1 duplicates_refused=1 roster=2 policy=9\n");
    else std::printf("P2_SARAI_COMBAT_REPAIR pass=0 failures=%d\n", failures);
    return failures == 0 ? 0 : 1;
}
