// Standalone receipt-ledger endpoint checker (lane overworld-yakushima-receipt-ledger-endpoint, #749).
//
// Engine-free and stdlib-only: drives P2ReceiptEndpoint::Endpoint through its
// four pinned stages against an in-memory ledger, verifying the happy path,
// out-of-order refusals, duplicate-ledger refusal and malformed-token
// refusals. Includes the vendored #632 captain guard with its self-test and
// negative path. Builds with -Wall -Wextra -Werror and no engine link.
//
// Usage: p2_receipt_ledger_endpoint_fixture [--guard-self-test] [--guard-negative-test]
// Exit: 0 PASS, 1 contract violation, 2 usage error.
#include "../pc_port/pc_p2_receipt_ledger_endpoint.h"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

// Captain-safety guard (#632), vendored verbatim from
// scripts/p2_fixture_captain_guard.h (sha256
// d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474);
// observation-only, equivalent tested guard.
inline bool p2_fixture_captain_down(bool orimaDead, bool deadState, float hp) {
    return orimaDead || deadState || !std::isfinite(hp) || hp <= 1.0f;
}
inline void p2_fixture_require_captain(bool orimaDead, bool deadState, float hp, int tick) {
    if (!p2_fixture_captain_down(orimaDead, deadState, hp)) return;
    std::printf("P2_FIXTURE_CAPTAIN_DOWN tick=%d hp=%.3f orima_dead=%d dead_state=%d outcome=BLOCKED\n",
                tick, hp, int(orimaDead), int(deadState));
    std::fflush(nullptr);
    std::_Exit(86);
}

namespace {
struct Row { bool orima; bool dead; float hp; bool expectDown; };
const Row kGuardRows[] = {
    {false, false, 100.0f, false},
    {false, false, 1.5f, false},
    {false, false, 1.0f, true},
    {false, false, 0.0f, true},
    {false, true, 100.0f, true},
    {true, false, 100.0f, true},
    {true, true, 0.0f, true},
};

int guardSelfTest() {
    for (size_t i = 0; i < sizeof(kGuardRows) / sizeof(kGuardRows[0]); ++i) {
        const bool down = p2_fixture_captain_down(
            kGuardRows[i].orima, kGuardRows[i].dead, kGuardRows[i].hp);
        if (down != kGuardRows[i].expectDown) {
            std::printf("FAIL RECEIPT_LEDGER selftest row=%d\n", int(i));
            return 1;
        }
    }
    std::printf("P2_RECEIPT_LEDGER_SELFTEST_PASS rows=%d\n",
                int(sizeof(kGuardRows) / sizeof(kGuardRows[0])));
    return 0;
}

int check(bool condition, const char* name) {
    if (!condition) {
        std::printf("FAIL RECEIPT_LEDGER %s\n", name);
        return 1;
    }
    return 0;
}

int runContract() {
    P2Receipt::MemoryReceiptPersistence persistence;
    P2Receipt::ReceiptLedger ledger(persistence);
    P2ReceiptEndpoint::Endpoint endpoint(ledger, "seed-yakushima-1");
    if (check(endpoint.stage() == 0, "initial-idle")) return 1;
    // Out-of-order stages refuse without state change.
    if (check(!endpoint.actOnyon("g1"), "act-before-ready-refused")) return 1;
    if (check(endpoint.stage() == 0, "refusal-preserves-idle")) return 1;
    if (check(!endpoint.obtainPellet("enc1"), "obtain-before-act-refused")) return 1;
    if (check(endpoint.ledgerWrite() == 0, "write-before-obtain-refused")) return 1;
    // Malformed identity refuses.
    if (check(!endpoint.suckReady("has space"), "bad-identity-refused")) return 1;
    // Happy path: the four pins in order, durable grant.
    if (check(endpoint.suckReady("onion:p2:38:0"), "ready")) return 1;
    if (check(!endpoint.suckReady("onion:p2:38:0"), "double-ready-refused")) return 1;
    if (check(endpoint.actOnyon("g186081"), "act")) return 1;
    if (check(endpoint.obtainPellet("contest"), "obtain")) return 1;
    if (check(endpoint.ledgerWrite() == 1, "grant")) return 1;
    if (check(endpoint.stage() == 0, "reset-after-grant")) return 1;
    // Same coordinates again: the ledger refuses the duplicate.
    if (check(!endpoint.suckReady(""), "empty-identity-refused")) return 1;
    if (check(endpoint.suckReady("onion:p2:38:0"), "ready-again")) return 1;
    if (check(endpoint.actOnyon("g186081"), "act-again")) return 1;
    if (check(endpoint.obtainPellet("contest"), "obtain-again")) return 1;
    if (check(endpoint.ledgerWrite() == 2, "duplicate-refused")) return 1;
    // A fresh identity still grants after a duplicate.
    if (check(endpoint.suckReady("onion:p2:39:0"), "ready-fresh")) return 1;
    if (check(endpoint.actOnyon("g2"), "act-fresh")) return 1;
    if (check(endpoint.obtainPellet("contest"), "obtain-fresh")) return 1;
    if (check(endpoint.ledgerWrite() == 1, "grant-fresh")) return 1;
    std::printf("PASS RECEIPT_LEDGER contract stages=4 negatives=8\n");
    return 0;
}
} // namespace

int main(int argc, char** argv) {
    for (int i = 1; i < argc; ++i) {
        if (std::strcmp(argv[i], "--guard-self-test") == 0) return guardSelfTest();
        if (std::strcmp(argv[i], "--guard-negative-test") == 0) {
            p2_fixture_require_captain(true, true, 0.0f, 0);
            std::printf("FAIL RECEIPT_LEDGER negative test did not trip\n");
            return 1;
        }
    }
    p2_fixture_require_captain(false, false, 100.0f, 0);
    return runContract();
}
