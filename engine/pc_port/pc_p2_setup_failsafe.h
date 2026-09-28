#pragma once
// P2 campaign setup failsafe (#440).
//
// A live Archipelago seed must degrade, not crash, when a P2 species setup
// cannot stage its files. In bridge mode (`pc_randomizer_p2_bridge()` true) a
// failed setup calls pc_p2_setup_skip(), which logs exactly one
// `P2_SETUP_SKIP <species> <reason>` line to stderr and returns true so the
// caller returns early and leaves that species' actors as their P1 stand-ins.
// In fixture mode (bridge == false) it aborts: the existing fixtures rely on
// fail-closed setups.
//
// `bridge` is passed in rather than read here so this header stays engine-free
// and is consumed directly by p2_setup_failsafe_test.
#include <cstdio>
#include <cstdlib>

inline bool pc_p2_setup_skip(bool bridge, const char* species, const char* reason) {
    if (!bridge) {
        std::fprintf(stderr, "P2_SETUP_ABORT %s %s\n", species, reason);
        std::fflush(stderr);
        std::abort();
    }
    std::fprintf(stderr, "P2_SETUP_SKIP %s %s\n", species, reason);
    std::fflush(stderr);
    return true;
}
