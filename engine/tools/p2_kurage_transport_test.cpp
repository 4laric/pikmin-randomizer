// Kurage57 corpse -> carried -> exactly one Onion receipt test (#768).
//
// Engine-free proof over the REAL ordinary-delivery bridge
// (pc_p2_delivery_host.cpp, the same seam pc_randomizer_p2_corpse_delivered
// calls when GoalItem::suckMe absorbs a hauled corpse). No engine is booted,
// no health/state is written, no Transport is assigned: the test drives the
// durable ledger exactly as the bound source-57 delivery path does and proves
// the transport contract:
//
//   corpse (source 57, generator 201001, encounter "corpse") -> Granted once;
//   any repeat of the same corpse tuple -> Duplicate (never a second receipt),
//   durable across close/reopen (process restart); the pair mate (generator
//   201002) is a distinct actor with its own receipt. Fail-closed inputs
//   (null handle, unbound source 0) return Error and grant nothing.
//
// The family delivery bind itself (pc_p2_kurage_teki_setup binding source 57
// to the live actor, death-drop-to-ground settling the flyer corpse, and the
// corpse-tail carry to the Pod credited via pc_p2_preview_deliver ->
// pc_p2_kurage_receipt) is covered by the natural-run fixture (a future
// guard-adopted Kurage receipt run, same recipe as
// tools/p2_elecbug28_receipt_fixture.cpp): this test proves the receipt half
// of that path is exactly-once, so a carried corpse can yield one and only
// one onion:p2:57 receipt. The death-drop step is production code in
// pc_port/pc_p2_kurage_teki.cpp (P2_KURAGE_DEATH_DROP / P2_KURAGE_CORPSE_DROP).
//
// Optional log mode: p2_kurage_transport_test <native.log> additionally
// verifies the natural corpse -> carried -> delivered ordering in a captured
// run log (P2_KURAGE57_CORPSE, then P2_KURAGE57_CARRY moved>=100, then
// P2_KURAGE57_DELIVERED_TO_GOAL, then exactly one P2_ORDINARY_P2_RECEIPT
// new=1 for source 57, with no injected markers), using the same marker
// contract as the future Kurage receipt fixture.
//
// Exit 0 only if every check passes; any failure prints FAIL and exits 1.
#include "pc_p2_delivery_host.h"

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

constexpr unsigned kSourceId = 57;
constexpr unsigned kKurageGen = 201001;
constexpr unsigned kPairMateGen = 201002;
constexpr int kTekiType = 0; // P1-proxy vehicle type (generated Frog), disjoint from the P2 source id
constexpr int kStage = 1;
constexpr const char* kEncounter = "corpse";
constexpr const char* kSeed = "kurage57-transport-test";

int failures = 0;

#define CHECK(cond, name) do { \
    if (cond) { std::printf("PASS %s\n", name); } \
    else { std::printf("FAIL %s\n", name); ++failures; } \
} while (0)

using R = P2DeliveryHostResult;

bool ledgerContains(const std::string& path, const char* token)
{
    std::ifstream in(path);
    if (!in) return false;
    std::string line;
    while (std::getline(in, line)) {
        if (line.find(token) != std::string::npos) return true;
    }
    return false;
}

// Number of durable receipt rows mentioning `token` (exactly-once census).
// A missing ledger file holds zero rows (the persistence starts empty).
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

// Natural-log ordering check: corpse -> carried (moved>=100) -> delivered to
// goal -> exactly one onion:p2:57 receipt with new=1, no injected markers.
int checkNaturalLog(const char* logPath)
{
    std::ifstream in(logPath);
    if (!in) {
        std::printf("FAIL log-open path=%s\n", logPath);
        return 1;
    }
    std::string text((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());

    static const char* const kInjected[] = {
        "P2_LL_INJECT", "P2_LIFECYCLE_INJECT", "injected_health", "mHealth=",
        "P2_KURAGE_FALLBACK", "not_natural_combat=1", ":injected", "injected",
    };
    for (const char* token : kInjected) {
        if (text.find(token) != std::string::npos) {
            std::printf("FAIL log-injected token=%s\n", token);
            return 1;
        }
    }
    const size_t corpseAt = text.find("P2_KURAGE57_CORPSE pellet=1");
    const size_t carryAt = text.find("P2_KURAGE57_CARRY");
    const size_t deliveredAt = text.find("P2_KURAGE57_DELIVERED_TO_GOAL");
    if (corpseAt == std::string::npos) {
        std::printf("FAIL log-missing-corpse\n");
        return 1;
    }
    if (carryAt == std::string::npos || carryAt < corpseAt) {
        std::printf("FAIL log-missing-carry-after-corpse\n");
        return 1;
    }
    // Best haul movement across all carry markers must clear the natural
    // threshold (same 100.0 room-traversal bar as the receipt validator).
    double best = 0.0;
    for (size_t at = 0; (at = text.find("P2_KURAGE57_CARRY", at)) != std::string::npos; ++at) {
        const size_t movedAt = text.find("moved=", at);
        if (movedAt == std::string::npos) break;
        best = std::max(best, std::atof(text.c_str() + movedAt + 6));
    }
    if (best < 100.0) {
        std::printf("FAIL log-no-natural-haul best=%.1f\n", best);
        return 1;
    }
    if (deliveredAt == std::string::npos || deliveredAt < carryAt) {
        std::printf("FAIL log-missing-delivery-after-carry\n");
        return 1;
    }
    int receipts = 0, grants = 0;
    for (size_t at = 0; (at = text.find("id=onion:p2:57:", at)) != std::string::npos; ++at) {
        ++receipts;
        const size_t newAt = text.find("new=", at);
        if (newAt != std::string::npos && text.compare(newAt + 4, 1, "1") == 0) ++grants;
    }
    if (receipts != 1 || grants != 1) {
        std::printf("FAIL log-receipt-not-exactly-once receipts=%d grants=%d\n", receipts, grants);
        return 1;
    }
    std::printf("PASS P2_KURAGE_TRANSPORT_LOG corpse=1 carry_best=%.1f delivered=1 receipts=1\n", best);
    return 0;
}

} // namespace

int main(int argc, char** argv)
{
    namespace fs = std::filesystem;
    const auto dir = fs::temp_directory_path()
        / ("p2-kurage-transport-test-" + std::to_string(currentPid()));
    fs::create_directories(dir);
    const std::string path = (dir / "receipts.txt").string();
    fs::remove(path);

    P2DeliveryHostHandle h = pc_p2_delivery_host_open(path.c_str());
    CHECK(h != nullptr, "open-ledger");
    CHECK(pc_p2_delivery_host_path(h) != nullptr
        && std::strcmp(pc_p2_delivery_host_path(h), path.c_str()) == 0, "open-path");

    // Fail-closed: nothing grants without a live handle or a bound source.
    CHECK(pc_p2_delivery_host_deliver(nullptr, kSeed, kSourceId, kTekiType,
        kStage, kKurageGen, kEncounter) == R::Error, "failclosed-null-handle");
    CHECK(pc_p2_delivery_host_deliver(h, nullptr, kSourceId, kTekiType,
        kStage, kKurageGen, kEncounter) == R::Error, "failclosed-null-seed");
    CHECK(pc_p2_delivery_host_deliver(h, kSeed, 0, kTekiType,
        kStage, kKurageGen, kEncounter) == R::Error, "failclosed-unbound-source");
    CHECK(pc_p2_delivery_host_deliver(h, kSeed, kSourceId, kTekiType,
        kStage, kKurageGen, nullptr) == R::Error, "failclosed-null-encounter");
    CHECK(ledgerMentions(path, "onion:p2:57") == 0, "failclosed-grants-nothing");

    // Corpse carried to the Onion: the bound source-57 delivery grants once.
    CHECK(pc_p2_delivery_host_deliver(h, kSeed, kSourceId, kTekiType,
        kStage, kKurageGen, kEncounter) == R::Granted, "corpse-first-granted");
    CHECK(ledgerMentions(path, "onion:p2:57:1") == 1, "corpse-count-one");
    CHECK(ledgerContains(path, "onion:p2:57"), "corpse-identity-onion-p2-57");

    // The same corpse re-delivered is a durable duplicate, never a receipt.
    CHECK(pc_p2_delivery_host_deliver(h, kSeed, kSourceId, kTekiType,
        kStage, kKurageGen, kEncounter) == R::Duplicate, "corpse-repeat-duplicate");
    CHECK(ledgerMentions(path, "onion:p2:57:1") == 1, "corpse-still-one");

    // The pair mate is a distinct actor with its own single receipt.
    CHECK(pc_p2_delivery_host_deliver(h, kSeed, kSourceId, kTekiType,
        kStage, kPairMateGen, kEncounter) == R::Granted, "pairmate-granted");
    CHECK(ledgerMentions(path, "onion:p2:57:1") == 2, "pairmate-count-two");
    CHECK(pc_p2_delivery_host_deliver(h, kSeed, kSourceId, kTekiType,
        kStage, kPairMateGen, kEncounter) == R::Duplicate, "pairmate-repeat-duplicate");

    // Process restart over the same path never re-grants the carried corpse.
    pc_p2_delivery_host_close(h);
    h = pc_p2_delivery_host_open(path.c_str());
    CHECK(h != nullptr, "reopen-ledger");
    CHECK(pc_p2_delivery_host_deliver(h, kSeed, kSourceId, kTekiType,
        kStage, kKurageGen, kEncounter) == R::Duplicate, "restart-corpse-duplicate");
    CHECK(ledgerMentions(path, "onion:p2:57:1") == 2, "restart-count-two");
    pc_p2_delivery_host_close(h);

    if (argc > 1) {
        if (checkNaturalLog(argv[1]) != 0) ++failures;
    }

    fs::remove(path);
    fs::remove(dir);

    if (failures == 0) std::printf("PASS P2_KURAGE_TRANSPORT source=57 granted=1 duplicates_refused=1\n");
    else std::printf("P2_KURAGE_TRANSPORT pass=0 failures=%d\n", failures);
    return failures == 0 ? 0 : 1;
}
