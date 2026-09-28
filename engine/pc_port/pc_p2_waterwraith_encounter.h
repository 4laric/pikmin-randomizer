#pragma once

// Lane 31 (#443 / parent #175): engine-facing Waterwraith combat consumer.
//
// This is the missing consumer for the family rules in
// pc_p2_waterwraith_attack_policy.h and the actor receiver
// `p2_waterwraith_actor_apply_damage`. It scans the live Piki squad for the
// registered Waterwraith host actor:
//
//   * Purple Pikmin in stun range while the rig is closed -> a roller
//     quakeFreeze edge (Purple landing stun);
//   * Purple Pikmin in hit range while the rig is open -> accepted damage on
//     the frozen roller / dismounted body;
//   * non-Purple Pikmin in crush range while rolling -> InteractFlick (the P1
//     host analogue of the source roller contact, fp24 damage 10);
//   * the host death script: roller death -> dismount -> tyre_getoff ->
//     child removal.
//
// It owns no actor, map or lifetime; the register seam owns the actor and calls
// this once per source tick. Cleanup/teardown stays with the register seam.
//
// Muse l63 (#503): this consumer also feeds the actor-owned movement driver
// each tick (live active-captain XZ for the source escape chase; podValid
// stays false on this host) and emits the BIRTH/STEER observation markers the
// muse observer verifies. It synthesizes no positions and injects no state.

#include "pc_p2_waterwraith_actor.h"

#include <cstdint>

struct P2WaterwraithEncounterStats {
    std::uint64_t ticks = 0;
    std::uint64_t stunned = 0;   // Purple landing stuns applied
    std::uint64_t acceptedHits = 0; // accepted hits (Purple on the roller; any color on the body)
    std::uint64_t crushes = 0;   // non-Purple Pikmin flicked by the roller
    float damageDealt = 0.0f;
    bool rollerZeroed = false;   // roller health reached zero
    bool childRemoved = false;   // tyre_getoff end removed the Tyre child
    bool bodyZeroed = false;     // dismounted wraith body health reached zero
    bool treasureReleased = false; // source Dead KEYEVENT_5
    bool killed = false;         // source Dead KEYEVENT_END (kill requested)
    // Autonomous driver observation (muse l63, #503).
    std::uint64_t steerTicks = 0; // ticks with an actor-owned steer target
    std::uint64_t chaseTicks = 0; // ticks steering to the live captain
    bool birthRecorded = false;  // first-observation anchor stored
    float birthX = 0.0f;         // planar anchor for travel measurement
    float birthZ = 0.0f;
    float travel = 0.0f;         // planar travel from the anchor
};

void pc_p2_waterwraith_encounter_reset();
bool pc_p2_waterwraith_encounter_ready();
const P2WaterwraithEncounterStats& pc_p2_waterwraith_encounter_stats();

// One source tick, called just before `actor.tick`. Fills `in` with the
// encounter-derived triggers (stun, roller death, tyre_getoff, body death
// animation) and applies accepted Purple damage / roller crushes to the live
// squad. Safe when no squad is present (no-op triggers).
void pc_p2_waterwraith_encounter_step(P2WaterwraithActor& actor, P2WaterwraithActorInput& in);
