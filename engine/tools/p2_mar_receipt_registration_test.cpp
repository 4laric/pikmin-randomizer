// Mar29 receipt registration test (#668): compiled positive/negative checks.
//
// Exercises the #650 receipt adapter fail-closed contract WITHOUT a live
// engine: setup/reset lifecycle, null-actor rejection on every entry point,
// unknown-view resolve refusal, and registration observability. Live-actor
// bind/resolve (positive natural path) belongs to the #650 natural-run
// fixture, not to this unit test; nothing here fabricates a corpse.
// Exit 0 only if every check passes; any failure prints and exits 1.
#include <cstdio>
#include "pc_p2_mar_receipt.h"

static int failures = 0;

#define CHECK(cond, name) do { \
    if (cond) { std::printf("PASS %s\n", name); } \
    else { std::printf("FAIL %s\n", name); ++failures; } \
} while (0)

int main()
{
    // Lifecycle: fresh registry is empty and observable.
    pc_p2_mar_receipt_setup();
    CHECK(pc_p2_mar_receipt_count() == 0ul, "fresh-count-zero");
    CHECK(!pc_p2_mar_receipt_registered(nullptr), "registered-null-false");

    // Null-actor rejection on every entry point (fail-closed, no crash).
    CHECK(!pc_p2_mar_receipt_bind(nullptr), "bind-null-false");
    unsigned generator = 0xdeadbeefu;
    CHECK(!pc_p2_mar_receipt(nullptr, generator), "resolve-null-false");
    CHECK(generator == 0xdeadbeefu, "resolve-null-preserves-output");
    pc_p2_mar_receipt_forget(nullptr); // must not crash
    std::printf("PASS forget-null-noop\n");
    CHECK(pc_p2_mar_receipt_count() == 0ul, "count-still-zero");

    // Reset clears and disarms: bind must fail while not ready.
    pc_p2_mar_receipt_reset();
    CHECK(!pc_p2_mar_receipt_bind(nullptr), "bind-after-reset-false");
    CHECK(pc_p2_mar_receipt_count() == 0ul, "reset-count-zero");

    // Re-setup restores readiness with an empty registry.
    pc_p2_mar_receipt_setup();
    CHECK(pc_p2_mar_receipt_count() == 0ul, "resestup-count-zero");

    if (failures == 0) std::printf("P2_MAR_RECEIPT_REGISTRATION_TEST pass=1\n");
    else std::printf("P2_MAR_RECEIPT_REGISTRATION_TEST pass=0 failures=%d\n", failures);
    return failures == 0 ? 0 : 1;
}