// Kogane9 corpse -> carried -> exactly one Onion receipt test (#571).
//
// Engine-free proof over the REAL ordinary-delivery bridge
// (pc_p2_delivery_host.cpp, the same seam pc_randomizer_p2_corpse_delivered
// calls when GoalItem::suckMe absorbs a hauled corpse). No engine is booted,
// no health/state is written, no Transport is assigned: the test drives the
// durable ledger exactly as the bound source-9 delivery path does and proves
// the transport contract:
//
//   corpse (source 9, generator 219001, encounter "corpse") -> Granted once;
//   any repeat of the same corpse tuple -> Duplicate (never a second receipt),
//   durable across close/reopen (process restart); a distinct generator token
//   is its own single receipt (per-actor identity). Fail-closed inputs (null
//   handle, null seed, unbound source 0, null encounter) return Error and
//   grant nothing.
//
// The burrow/flee boundary (#571) lives in the family module
// (pc_port/pc_p2_kogane.cpp): the ordinary-delivery bind for source 9 is
// established at setup, a beetle that burrows/flees sets `escaped` (so
// pc_p2_kogane_corpse_type returns NoCorpse and the central lifetime seam
// drops the bind), and a beetle killed by the host keeps the bind and leaves a
// carryable corpse. A still-bound killed beetle therefore yields exactly one
// onion:p2:9 receipt, while an escaped beetle carries no corpse and no live
// bind, so the shared delivery seam sees source 0 and takes the same Error
// path as `failclosed-unbound-source` below. pc_p2_kogane_escaped() /
// pc_p2_kogane_delivery_bound() expose both gates read-only to the natural-run
// fixture. Those gates need the live engine; this test proves the receipt half
// is exactly-once so a carried corpse can yield one and only one receipt.
//
// Optional log mode: p2_kogane_receipt_test <native.log> additionally verifies
// the natural ordering in a captured run log (P2_KOGANE_DELIVERY_BIND present,
// no injected markers, exactly one `id=onion:p2:9:` receipt with `new=1`, and
// no receipt for a generator that emitted a P2_KOGANE_ESCAPE /
// P2_KOGANE_RESTORED_ESCAPE marker: a burrowed/fled beetle strands no corpse
// and double-fires nothing).
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

constexpr unsigned kSourceId = 9;
constexpr unsigned kKoganeGen = 219001;
constexpr unsigned kSecondGen = 219002; // distinct corpse tuple: per-actor identity
constexpr int kTekiType = 3; // TEKI_Chappy, the Kogane P1-proxy host type
constexpr int kStage = 1;
constexpr const char* kEncounter = "corpse";
constexpr const char* kSeed = "kogane9-receipt-test";

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

// Natural-log ordering check: a bind row exists, no injected markers, exactly
// one onion:p2:9 receipt with new=1, and no new receipt for any generator that
// emitted a burrow/flee escape marker (an escaped beetle strands no corpse and
// double-fires nothing).
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
        "P2_KOGANE_FALLBACK", "not_natural_combat=1", "direct transport assigned",
    };
    for (const char* token : kInjected) {
        if (text.find(token) != std::string::npos) {
            std::printf("FAIL log-injected token=%s\n", token);
            return 1;
        }
    }
    const size_t bindAt = text.find("P2_KOGANE_DELIVERY_BIND");
    if (bindAt == std::string::npos) {
        std::printf("FAIL log-missing-delivery-bind\n");
        return 1;
    }
    int receipts = 0, grants = 0;
    for (size_t at = 0; (at = text.find("id=onion:p2:9:", at)) != std::string::npos; ++at) {
        ++receipts;
        const size_t newAt = text.find("new=", at);
        if (newAt != std::string::npos && text.compare(newAt + 4, 1, "1") == 0) ++grants;
    }
    if (receipts != 1 || grants != 1) {
        std::printf("FAIL log-receipt-not-exactly-once receipts=%d grants=%d\n", receipts, grants);
        return 1;
    }
    // A burrow/flee must never be followed by a fresh receipt for that actor.
    for (const char* escape : {"P2_KOGANE_ESCAPE", "P2_KOGANE_RESTORED_ESCAPE"}) {
        for (size_t at = 0; (at = text.find(escape, at)) != std::string::npos; ++at) {
            const size_t genAt = text.find("generator=", at);
            if (genAt == std::string::npos) continue;
            const unsigned long gen = std::strtoul(text.c_str() + genAt + 10, nullptr, 10);
            const std::string row = "generator=" + std::to_string(gen);
            for (size_t rec = at; (rec = text.find("id=onion:p2:9:", rec)) != std::string::npos; ++rec) {
                const size_t rowAt = text.find(row, rec);
                if (rowAt == std::string::npos || rowAt - rec > 96) continue;
                const size_t newAt = text.find("new=", rowAt);
                if (newAt != std::string::npos && text.compare(newAt + 4, 1, "1") == 0) {
                    std::printf("FAIL log-receipt-after-escape generator=%lu\n", gen);
                    return 1;
                }
            }
        }
    }
    std::printf("PASS P2_KOGANE_RECEIPT_LOG bind=1 receipts=1 grants=1 escape_no_receipt=1\n");
    return 0;
}

} // namespace

int main(int argc, char** argv)
{
    namespace fs = std::filesystem;
    const auto dir = fs::temp_directory_path()
        / ("p2-kogane-receipt-test-" + std::to_string(currentPid()));
    fs::create_directories(dir);
    const std::string path = (dir / "receipts.txt").string();
    fs::remove(path);

    P2DeliveryHostHandle h = pc_p2_delivery_host_open(path.c_str());
    CHECK(h != nullptr, "open-ledger");
    CHECK(pc_p2_delivery_host_path(h) != nullptr
        && std::strcmp(pc_p2_delivery_host_path(h), path.c_str()) == 0, "open-path");

    // Fail-closed: nothing grants without a live handle or a bound source.
    // (A burrowed/fled beetle carries no bind, so the shared delivery seam
    // sees source 0 for it and takes this same Error path.)
    CHECK(pc_p2_delivery_host_deliver(nullptr, kSeed, kSourceId, kTekiType,
        kStage, kKoganeGen, kEncounter) == R::Error, "failclosed-null-handle");
    CHECK(pc_p2_delivery_host_deliver(h, nullptr, kSourceId, kTekiType,
        kStage, kKoganeGen, kEncounter) == R::Error, "failclosed-null-seed");
    CHECK(pc_p2_delivery_host_deliver(h, kSeed, 0, kTekiType,
        kStage, kKoganeGen, kEncounter) == R::Error, "failclosed-unbound-source");
    CHECK(pc_p2_delivery_host_deliver(h, kSeed, kSourceId, kTekiType,
        kStage, kKoganeGen, nullptr) == R::Error, "failclosed-null-encounter");
    CHECK(ledgerMentions(path, "onion:p2:9") == 0, "failclosed-grants-nothing");

    // A killed, bound Kogane's corpse carried to the Onion grants once.
    CHECK(pc_p2_delivery_host_deliver(h, kSeed, kSourceId, kTekiType,
        kStage, kKoganeGen, kEncounter) == R::Granted, "corpse-first-granted");
    CHECK(ledgerMentions(path, "onion:p2:9:1") == 1, "corpse-count-one");
    CHECK(ledgerContains(path, "onion:p2:9"), "corpse-identity-onion-p2-9");

    // The same corpse re-delivered is a durable duplicate, never a receipt.
    CHECK(pc_p2_delivery_host_deliver(h, kSeed, kSourceId, kTekiType,
        kStage, kKoganeGen, kEncounter) == R::Duplicate, "corpse-repeat-duplicate");
    CHECK(ledgerMentions(path, "onion:p2:9:1") == 1, "corpse-still-one");

    // A distinct corpse tuple (distinct generator) is its own single receipt.
    CHECK(pc_p2_delivery_host_deliver(h, kSeed, kSourceId, kTekiType,
        kStage, kSecondGen, kEncounter) == R::Granted, "second-granted");
    CHECK(ledgerMentions(path, "onion:p2:9:1") == 2, "second-count-two");
    CHECK(pc_p2_delivery_host_deliver(h, kSeed, kSourceId, kTekiType,
        kStage, kSecondGen, kEncounter) == R::Duplicate, "second-repeat-duplicate");

    // Burrow/flee boundary: an escaped beetle carries no bind, so its corpse
    // route (should one ever exist) cannot mint a receipt.
    CHECK(pc_p2_delivery_host_deliver(h, kSeed, 0, kTekiType,
        kStage, kKoganeGen, kEncounter) == R::Error, "escaped-no-receipt");
    CHECK(ledgerMentions(path, "onion:p2:9:1") == 2, "escaped-count-unchanged");

    // Process restart over the same path never re-grants the carried corpse.
    pc_p2_delivery_host_close(h);
    h = pc_p2_delivery_host_open(path.c_str());
    CHECK(h != nullptr, "reopen-ledger");
    CHECK(pc_p2_delivery_host_deliver(h, kSeed, kSourceId, kTekiType,
        kStage, kKoganeGen, kEncounter) == R::Duplicate, "restart-corpse-duplicate");
    CHECK(ledgerMentions(path, "onion:p2:9:1") == 2, "restart-count-two");
    pc_p2_delivery_host_close(h);

    if (argc > 1) {
        if (checkNaturalLog(argv[1]) != 0) ++failures;
    }

    fs::remove(path);
    fs::remove(dir);

    if (failures == 0) std::printf("PASS P2_KOGANE_RECEIPT source=9 granted=1 duplicates_refused=1\n");
    else std::printf("P2_KOGANE_RECEIPT pass=0 failures=%d\n", failures);
    return failures == 0 ? 0 : 1;
}
