#pragma once

// Generated-placement bridge (lane 03/04, #242/#439).
//
// When the randomizer resolves a spawned generator to a seeded P2 source
// (`ENEMY_P2` target -> source id), the actor the engine actually instantiated
// is still a P1 stand-in (`genteki.cpp` replacement is a P1 type under the P2
// bridge). This dispatcher hands that actor to the seeded identity's module so
// the module can claim it (bind its own behaviour/visual/corpse to the
// actor). Returns true when a P2 module took the actor.
//
// Placement policy (#948, CONTRIBUTING "Placement: don't hard-code where a
// species may go"): root placement data is the single source of truth. Native
// spawns what the seed binds. This dispatcher never refuses a binding because
// of the slot id; the compiled per-species slot whitelist
// (`pc_p2_campaign_placements.h`) and the `*_slot()` evidence constants that
// used to live here are gone. A refusal is logged with a specific
// `reason=` and is only ever a runtime incompatibility:
//   * `bad-request`          null actor / zero source or target
//   * `seed-target-mismatch` the seed does not bind this source at this target
//   * `registry-full`        more than 64 recorded binds in one stage
//   * `no-campaign-module`   the seed bound a roster id that has no
//                            campaign-keyed native module (informational;
//                            a proxy-tier row may still claim the actor)
//   * `protected-drop`       logged by genteki.cpp when the generator holds a
//                            non-transferable protected drop (P1 type spawns)
//
// For the sidecar-driven families (57 Kurage, 58 BombSarai, 78 MiniHoudai,
// 99 Waterwraith) the dispatcher records the (actor, source, target,
// generator) triple, emits `P2_GENERATED_PLACEMENT ... bound=1`, and returns
// false: family behaviour still binds through the family sidecar path, so no
// P2 module has taken the actor yet. Gate observers correlate that marker
// with `P2_SEED_RESOLVE` and the `P2_PLACEMENT_*` slot markers on the shared
// target uid. The Waterwraith consumer (pc_p2_waterwraith_encounter.cpp)
// joins the `p2-waterwraith-generated.txt` sidecar's generator/slot pair to a
// bound actor; the slot comes from the seed's own sidecar, not from a
// compiled constant.
class BTeki;

bool pc_p2_generated_placement_bind(BTeki* actor, unsigned sourceId, unsigned seedTargetUid, unsigned generatorId);

// Seed-bridge setup sweep (rd-p2ap-sarai, #439, Otakara pattern): bind every
// live actor the randomizer resolved to Sarai source 23 through the Sarai
// dynamic binder. No env var is consulted and several copies may bind;
// actors whose sidecar is absent are skipped quietly by the dynamic binder.
// Returns true when at least one actor was claimed. Called from
// pc_p2_sarai_manager_setup() in bridge mode; complements the birth-time
// claim in pc_p2_generated_placement_bind (called from genteki birth).
bool pc_p2_generated_placement_sweep_sarai();

// True when sourceId binds through the sidecar-record path above (57/58/78/99):
// the placement marker is recorded here and behaviour binds in the family
// setup sweep. Fixtures use this to know which ids leave a registry record.
inline bool pc_p2_generated_placement_is_sidecar_recorded(unsigned sourceId)
{
    return sourceId == 57 || sourceId == 58 || sourceId == 78 || sourceId == 99;
}

// Registry queries for fixtures and gate observers. A record exists only for
// a recorded sidecar bind; refused binds leave no record.
bool pc_p2_generated_placement_is_bound(const BTeki* actor);
int pc_p2_generated_placement_bound_count();
// Death-funnel / slot-reuse forget and stage-boundary reset.
void pc_p2_generated_placement_forget(const BTeki* actor);
void pc_p2_generated_placement_reset();

