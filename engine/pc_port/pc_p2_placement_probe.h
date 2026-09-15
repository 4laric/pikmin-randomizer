#pragma once
// Lane-04 (placement/encounter compatibility) native evidence probe.
//
// Lane 04 owns the machine-readable placement/encounter schema and audit. Its
// acceptance contract is "native XYZ/terrain/return-route evidence for
// generated placements": before a placement pair can be admitted, the slot must
// carry real native evidence that a spawn at its coordinates (a) rests on
// terrain, (b) has the claimed terrain/water class, and (c) lies within a
// bounded coverage radius of the navigation route graph (so a corpse corridor
// exists). "Covered" here is a distance-capped nearest-waypoint check, not a
// full path-to-Onion find; the latter is lane-06 transport scope.
//
// This module probes native placement evidence in two generated-spawn paths:
// the disposable P2-room scanner and the campaign/generator birth hook. It is
// a read-only audit: it samples the live map and route graph at each spawned
// Teki actor's position, emits `P2_PLACEMENT_SLOT` / `P2_PLACEMENT_PROBE`
// markers for the root audit tooling, and mutates no actor, map or economy
// state. When a `p2-placement-slots.txt` sidecar is present it also folds in
// the placement catalog slot uid (`slot=` field) so the root audit can join a
// staged actor to a real catalog slot instead of the raw generator id.
//
// It does not implement family FSM, seed serialization, reward semantics or
// any universal replacement permission.
void pc_p2_placement_probe_run();

// Campaign birth hook: sample terrain/water/route at a generated placement's
// birth position and emit one `P2_PLACEMENT_SLOT` marker. `slot` is the catalog
// slot uid the seed bridge already resolved for this generator (no sidecar
// needed on the campaign path). Read-only; mutates nothing.
void pc_p2_placement_probe_birth(float x, float y, float z, unsigned generator, unsigned slot, int actorType);
