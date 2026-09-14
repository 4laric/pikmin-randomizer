#pragma once

#include "pc_p2_bigtreasure_attacks.h"
#include <cstddef>
#include <cstdint>

// Lane-owned registration/install-profile glue and multi-actor lifetime
// wiring for the BigTreasure host seam, issue #246. Engine-free: the runtime
// fixture (tools/p2_bigtreasure_runtime.cpp) and the future root-owned
// integration call these entry points; the map binding lives in
// pc_p2_bigtreasure_map_trace.h. Opt-in per the #186 profile convention: the
// caller only reaches setup when the room-preview experiment flag is active
// AND the profile file exists; fixed placement comes first per the boss
// staged-phases gate (no locomotion, no spawn-table registration yet).
//
// Lifetime contract at the seam (lane teardown decisions, see
// docs/PIKMIN2_BIGTREASURE_CONTRACT.md and PIKMIN2_BIGTREASURE_ATTACKS.md):
//  - setup captures the full retail loadout: 4 weapon pellets (elec, fire,
//    gas, water) at full 6000 HP plus Louie = 5 captured pellets.
//  - defeat ordering is deterministic: director/pools force-recycle first
//    (including in-flight water bubbles, no hit events), then ownership
//    releases every still-captured pellet (weapons pop (0,100,0), Louie
//    (0,150,0)). No captured pellet or pooled attack node outlives the seam.
//  - reset without setup is a safe no-op.

// Fixed first-install placement parsed from the opt-in profile.
struct P2BigTreasureHostPlacement {
    P2BigTreasureVec3 owner;  // boss origin (fixed placement, staged gate)
    float ownerYaw = 0.0f;    // facing, radians
    P2BigTreasureVec3 target; // stationary harness target
    float initialTimer = 0.0f; // host randWeightFloat(2.0) pacing input
    int maxDischarge = 16;     // elec discharge count; 1 + maxDischarge <= 17
};

struct P2BigTreasureHostSeam {
    bool active = false;
    P2BigTreasureHostPlacement placement;
    P2BigTreasureOwnership ownership;
    P2BigTreasureAttackDirector director;
    std::uint64_t ticks = 0;
    std::uint64_t attacksStarted = 0;
    std::uint64_t defeatEvents = 0;
};

// Parses profile `P2_BIGTREASURE_HOST_1`:
//   line 1: P2_BIGTREASURE_HOST_1
//   line 2: placement <x> <y> <z> <yawRadians>
//   line 3: target <x> <y> <z>
//   line 4: timer <initialTimerSeconds>
//   line 5: discharge <maxDischarge 0..16>
// All coordinates must be finite and within +/-100000; timer finite in
// [0, 2]. Returns false on any malformed content (fail-closed, no partial
// install).
bool p2_bigtreasure_host_parse(const char* profilePath, P2BigTreasureHostPlacement& out);

// Installs the seam from the profile: captures the 4 weapon pellets and
// Louie at full health, resets the pacer with the profile timer and applies
// the elec discharge invariant. Any prior seam state is torn down first
// (defeat semantics) so reinstall never leaks captures or pooled nodes.
// Returns false when the profile is missing/invalid.
bool p2_bigtreasure_host_setup(const char* profilePath, P2BigTreasureHostSeam& seam);

// One 30 Hz attack-entry step from the fixed placement: the target-in-box
// input is derived from the placement's stationary target (source 225-unit
// XZ box); `unstuckOutsiderNearby` and `pickThreshold` are host inputs.
// Returns the started element or -1.
int p2_bigtreasure_host_tick_entry(P2BigTreasureHostSeam& seam, float delta,
                                   bool unstuckOutsiderNearby, float pickThreshold);

// Deterministic multi-actor teardown: pools force-recycled first, then the
// 5 captured pellets released. Writes up to `maxDrops` ownership drop events
// (4 weapons + Louie when fully captured) and returns the TOTAL released
// count, which exceeds `maxDrops` when the buffer truncates; releases are
// never lost. Safe on an inactive seam (returns 0).
std::size_t p2_bigtreasure_host_defeat(P2BigTreasureHostSeam& seam,
                                       P2BigTreasureDropEvent* outDrops, std::size_t maxDrops);

// Full seam reset: defeat teardown plus counter/state clearing.
void p2_bigtreasure_host_reset(P2BigTreasureHostSeam& seam);
