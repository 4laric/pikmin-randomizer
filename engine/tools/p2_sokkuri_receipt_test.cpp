// Sokkuri79 corpse -> carried -> exactly one Onion receipt test (#578).
//
// Engine-free proof over the REAL ordinary-delivery bridge
// (pc_p2_delivery_host.cpp, the same seam pc_randomizer_p2_corpse_delivered
// calls when GoalItem::suckMe absorbs a hauled corpse). No engine is booted,
// no health/state is written, no Transport is assigned: the test drives the
// durable ledger exactly as the bound source-79 delivery path does and proves
// the transport contract:
//
//   corpse (source 79, generator 346005, encounter "corpse") -> Granted once;
//   any repeat of the same corpse tuple -> Duplicate (never a second receipt),
//   durable across close/reopen (process restart); a distinct generator token
//   is its own single receipt (per-actor identity). Fail-closed inputs
//   (null handle, unbound source 0) return Error and grant nothing.
//
// The disguise/reveal boundary (#578) lives in the family module
// (pc_port/pc_p2_sokkuri.cpp): the single-use delivery bind is established
// only on the first STAY -> APPEAR reveal, never at setup, so a
// still-disguised Sokkuri carries no bound source and GoalItem::suckMe can
// never mint onion:p2:79 for it; pc_p2_sokkuri_revealed() exposes the gate
// read-only to the natural-run fixture. That gate needs the live engine and
// is covered by the natural-run fixture
// (tools/p2_sokkuri79_receipt_fixture.cpp, validated by
// experimental/pikmin2_sokkuri79_receipt.py): this test proves the receipt
// half of that path is exactly-once, so a carried corpse can yield one and
// only one onion:p2:79 receipt.
//
// Optional log mode: p2_sokkuri_receipt_test <native.log> additionally
// verifies the natural corpse -> carried -> delivered ordering in a captured
// run log (P2_SOKKURI79_CORPSE, then P2_SOKKURI79_CARRY moved>=100, then
// P2_SOKKURI79_DELIVERED_TO_GOAL, then exactly one P2_ORDINARY_P2_RECEIPT
// new=1 for source 79 with the DISGUISE hidden=0 reveal preceding the
// corpse, i.e. no receipt while disguised, and no injected markers), using
// the same marker contract as experimental/pikmin2_sokkuri79_receipt.py.
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

constexpr unsigned kSourceId = 79;
constexpr unsigned kSokkuriGen = 346005;
constexpr unsigned kSecondGen = 346006; // distinct corpse tuple: ledger per-actor identity
constexpr int kTekiType = 3; // TEKI_Chappy, the Sokkuri P1-proxy vehicle type
constexpr int kStage = 1;
constexpr const char* kEncounter = "corpse";
constexpr const char* kSeed = "sokkuri79-receipt-test";

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

// Natural-log ordering check: reveal (DISGUISE hidden=0) -> corpse ->
// carried (moved>=100) -> delivered to goal -> exactly one onion:p2:79
// receipt with new=1, no injected markers. The reveal-before-corpse order
// is the log-visible half of the disguise boundary: no receipt can exist
// for a still-disguised Sokkuri because the bind is established at reveal.
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
        "P2_SOKKURI79_FALLBACK", "not_natural_combat=1", "direct transport assigned",
    };
    for (const char* token : kInjected) {
        if (text.find(token) != std::string::npos) {
            std::printf("FAIL log-injected token=%s\n", token);
            return 1;
        }
    }
    const size_t revealAt = text.find("P2_SOKKURI_DISGUISE generator=346005 hidden=0");
    const size_t corpseAt = text.find("P2_SOKKURI79_CORPSE pellet=1");
    const size_t carryAt = text.find("P2_SOKKURI79_CARRY");
    const size_t deliveredAt = text.find("P2_SOKKURI79_DELIVERED_TO_GOAL");
    if (revealAt == std::string::npos) {
        std::printf("FAIL log-missing-reveal\n");
        return 1;
    }
    if (corpseAt == std::string::npos || corpseAt < revealAt) {
        std::printf("FAIL log-missing-corpse-after-reveal\n");
        return 1;
    }
    if (carryAt == std::string::npos || carryAt < corpseAt) {
        std::printf("FAIL log-missing-carry-after-corpse\n");
        return 1;
    }
    // Best haul movement across all carry markers must clear the natural
    // threshold (same 100.0 room-traversal bar as the receipt validator).
    double best = 0.0;
    for (size_t at = 0; (at = text.find("P2_SOKKURI79_CARRY", at)) != std::string::npos; ++at) {
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
    size_t firstReceiptAt = std::string::npos;
    for (size_t at = 0; (at = text.find("id=onion:p2:79:", at)) != std::string::npos; ++at) {
        if (firstReceiptAt == std::string::npos) firstReceiptAt = at;
        ++receipts;
        const size_t newAt = text.find("new=", at);
        if (newAt != std::string::npos && text.compare(newAt + 4, 1, "1") == 0) ++grants;
    }
    if (receipts != 1 || grants != 1) {
        std::printf("FAIL log-receipt-not-exactly-once receipts=%d grants=%d\n", receipts, grants);
        return 1;
    }
    if (firstReceiptAt < revealAt) {
        std::printf("FAIL log-receipt-while-disguised\n");
        return 1;
    }
    std::printf("PASS P2_SOKKURI_RECEIPT_LOG reveal=1 corpse=1 carry_best=%.1f delivered=1 receipts=1\n", best);
    return 0;
}

} // namespace

int main(int argc, char** argv)
{
    namespace fs = std::filesystem;
    const auto dir = fs::temp_directory_path()
        / ("p2-sokkuri-receipt-test-" + std::to_string(currentPid()));
    fs::create_directories(dir);
    const std::string path = (dir / "receipts.txt").string();
    fs::remove(path);

    P2DeliveryHostHandle h = pc_p2_delivery_host_open(path.c_str());
    CHECK(h != nullptr, "open-ledger");
    CHECK(pc_p2_delivery_host_path(h) != nullptr
        && std::strcmp(pc_p2_delivery_host_path(h), path.c_str()) == 0, "open-path");

    // Fail-closed: nothing grants without a live handle or a bound source.
    // (A still-disguised Sokkuri carries no bind, so the shared delivery
    // seam sees source 0 for it and takes this same Error path.)
    CHECK(pc_p2_delivery_host_deliver(nullptr, kSeed, kSourceId, kTekiType,
        kStage, kSokkuriGen, kEncounter) == R::Error, "failclosed-null-handle");
    CHECK(pc_p2_delivery_host_deliver(h, nullptr, kSourceId, kTekiType,
        kStage, kSokkuriGen, kEncounter) == R::Error, "failclosed-null-seed");
    CHECK(pc_p2_delivery_host_deliver(h, kSeed, 0, kTekiType,
        kStage, kSokkuriGen, kEncounter) == R::Error, "failclosed-unbound-source");
    CHECK(pc_p2_delivery_host_deliver(h, kSeed, kSourceId, kTekiType,
        kStage, kSokkuriGen, nullptr) == R::Error, "failclosed-null-encounter");
    CHECK(ledgerMentions(path, "onion:p2:79") == 0, "failclosed-grants-nothing");

    // Corpse carried to the Onion: the bound source-79 delivery grants once.
    CHECK(pc_p2_delivery_host_deliver(h, kSeed, kSourceId, kTekiType,
        kStage, kSokkuriGen, kEncounter) == R::Granted, "corpse-first-granted");
    CHECK(ledgerMentions(path, "onion:p2:79:1") == 1, "corpse-count-one");
    CHECK(ledgerContains(path, "onion:p2:79"), "corpse-identity-onion-p2-79");

    // The same corpse re-delivered is a durable duplicate, never a receipt.
    CHECK(pc_p2_delivery_host_deliver(h, kSeed, kSourceId, kTekiType,
        kStage, kSokkuriGen, kEncounter) == R::Duplicate, "corpse-repeat-duplicate");
    CHECK(ledgerMentions(path, "onion:p2:79:1") == 1, "corpse-still-one");

    // A distinct corpse tuple (distinct generator) is its own single receipt.
    CHECK(pc_p2_delivery_host_deliver(h, kSeed, kSourceId, kTekiType,
        kStage, kSecondGen, kEncounter) == R::Granted, "second-granted");
    CHECK(ledgerMentions(path, "onion:p2:79:1") == 2, "second-count-two");
    CHECK(pc_p2_delivery_host_deliver(h, kSeed, kSourceId, kTekiType,
        kStage, kSecondGen, kEncounter) == R::Duplicate, "second-repeat-duplicate");

    // Process restart over the same path never re-grants the carried corpse.
    pc_p2_delivery_host_close(h);
    h = pc_p2_delivery_host_open(path.c_str());
    CHECK(h != nullptr, "reopen-ledger");
    CHECK(pc_p2_delivery_host_deliver(h, kSeed, kSourceId, kTekiType,
        kStage, kSokkuriGen, kEncounter) == R::Duplicate, "restart-corpse-duplicate");
    CHECK(ledgerMentions(path, "onion:p2:79:1") == 2, "restart-count-two");
    pc_p2_delivery_host_close(h);

    if (argc > 1) {
        if (checkNaturalLog(argv[1]) != 0) ++failures;
    }

    fs::remove(path);
    fs::remove(dir);

    if (failures == 0) std::printf("PASS P2_SOKKURI_RECEIPT source=79 granted=1 duplicates_refused=1\n");
    else std::printf("P2_SOKKURI_RECEIPT pass=0 failures=%d\n", failures);
    return failures == 0 ? 0 : 1;
}
