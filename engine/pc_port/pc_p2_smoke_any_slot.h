#pragma once

// Dev-only smoke-seed switch (#944).
//
// Owner ruling (2026-09-29): hand-played smoke seeds must be able to put ANY
// playable P2 species on ANY ordinary enemy slot. Since #948 native carries
// no compiled slot approvals at all (root placement data is the single
// source of truth and native spawns what the seed binds), so this switch no
// longer bypasses anything in the placement binder. It is kept as the
// documented smoke-seed marker: `scripts/p2_smoke_seed.py` sets it, the
// state is logged once, and the netplay force-off latch below stays as the
// hook for any future dev-only bypass.
//
// Contract:
// * `PIKMIN_P2_SMOKE_ANY_SLOT=1` (any value other than unset/empty/"0")
//   enables the bypass. Unset means inert: every slot check runs unchanged.
// * The verdict is cached on first use and logged once as
//   `P2_SMOKE_ANY_SLOT enabled` / `P2_SMOKE_ANY_SLOT disabled reason=...`.
// * `pc_p2_smoke_any_slot_force_off(reason)` latches the bypass off for the
//   rest of the process regardless of the env var. A netplay session start
//   must call it (peers must never disagree on slot acceptance); the dev
//   console may call it to restore enforcement.
// * Only the *slot-approval* verdict is bypassed. Host substitution still
//   goes through `p2campaign::hostType` and each family module still binds on
//   its own host type / staged content, so a family that cannot run on the
//   substituted host reports its usual UNBOUND/host reason, never a silent
//   accept.
//
// Callers (the generated-placement binder, later the dev console spawn path)
// consult `pc_p2_smoke_any_slot()` and log `bypass=1` on the bind they let
// through so the evidence stays distinguishable from a real approval.
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace pc_p2_smoke_any_slot_detail {
inline bool& forcedOff()
{
    static bool value = false;
    return value;
}
inline int& cached()
{
    static int value = -1; // -1 unresolved, 0 off, 1 on
    return value;
}
inline bool envRequested()
{
    const char* value = std::getenv("PIKMIN_P2_SMOKE_ANY_SLOT");
    return value && *value && std::strcmp(value, "0") != 0;
}
} // namespace pc_p2_smoke_any_slot_detail

// Latch the bypass off for the rest of the process (netplay sessions, dev
// console "enforce" toggle). Idempotent; logs once when it actually changes
// the verdict.
inline void pc_p2_smoke_any_slot_force_off(const char* reason)
{
    using namespace pc_p2_smoke_any_slot_detail;
    if (forcedOff()) return;
    forcedOff() = true;
    if (envRequested()) {
        std::printf("P2_SMOKE_ANY_SLOT disabled reason=%s\n", reason && *reason ? reason : "forced-off");
        std::fflush(stdout);
    }
    cached() = 0;
}

// True when smoke-seed slot bypass is active. Inert (false) unless
// PIKMIN_P2_SMOKE_ANY_SLOT is set and no force-off latched.
inline bool pc_p2_smoke_any_slot()
{
    using namespace pc_p2_smoke_any_slot_detail;
    if (forcedOff()) return false;
    if (cached() < 0) {
        cached() = envRequested() ? 1 : 0;
        if (cached() == 1) {
            std::printf("P2_SMOKE_ANY_SLOT enabled\n");
            std::fflush(stdout);
        }
    }
    return cached() == 1;
}

// Test seam: forget the cached verdict and the force-off latch so a unit test
// can exercise both branches in one process. Never called by the game.
inline void pc_p2_smoke_any_slot_reset_for_test()
{
    using namespace pc_p2_smoke_any_slot_detail;
    forcedOff() = false;
    cached() = -1;
}
