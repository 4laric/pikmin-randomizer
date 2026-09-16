#pragma once

// Generated-placement bridge (lane 03/04, #242/#439).
//
// When the randomizer resolves a spawned generator to a seeded P2 source
// (`ENEMY_P2` target -> source id), the actor the engine actually instantiated
// is still a P1 stand-in (`genteki.cpp` replacement is a P1 type under the P2
// bridge). This dispatcher hands that actor to the seeded identity's module so
// the module can claim it (bind its own behaviour/visual/corpse to the
// Returns true when a P2 module took the actor.
//
// Muse placement slice (#492): candidate-only generated-placement binding for
// Fuefuki41, Kurage57, BombSarai58 and MiniHoudai78. For these four ids the
// dispatcher records the (actor, source, target, generator) triple, emits the
// `P2_GENERATED_PLACEMENT` marker with the slot-acceptance verdict, and
// returns false: family behavior still binds through the family sidecar path
// (lane-owned teki modules, untouched by this slice), so no P2 module has
// taken the actor yet. Gate observers (#497-#500) correlate that marker with
// the `P2_SEED_RESOLVE` source-id marker and the `P2_PLACEMENT_*` slot markers
// on the shared target uid.
//
// Slot contract mirror: the accepted generated slot per candidate source id.
// Must match `randomizer/p2_placement_catalog.py` MUSE_GENERATED_SLOTS; the
// `tests/test_pikmin2_muse_placement.py` sync test fails on drift.
class BTeki;

bool pc_p2_generated_placement_bind(BTeki* actor, unsigned sourceId, unsigned seedTargetUid, unsigned generatorId);

static const unsigned MUSE_GENERATED_SLOT_FUEFUKI41 = 1254096625u;
static const unsigned MUSE_GENERATED_SLOT_KURAGE57 = 689702860u;
static const unsigned MUSE_GENERATED_SLOT_BOMBSARAI58 = 1787125272u;
static const unsigned MUSE_GENERATED_SLOT_MINIHOUDAI78 = 328297937u;

// True when sourceId is a muse #492 candidate (41/57/58/78).
inline bool pc_p2_generated_placement_is_muse_candidate(unsigned sourceId)
{
    return sourceId == 41 || sourceId == 57 || sourceId == 58 || sourceId == 78;
}
// Accepted generated slot for a muse candidate, or 0 for any other id.
inline unsigned pc_p2_generated_placement_muse_slot(unsigned sourceId)
{
    switch (sourceId) {
    case 41: return MUSE_GENERATED_SLOT_FUEFUKI41;
    case 57: return MUSE_GENERATED_SLOT_KURAGE57;
    case 58: return MUSE_GENERATED_SLOT_BOMBSARAI58;
    case 78: return MUSE_GENERATED_SLOT_MINIHOUDAI78;
    default: return 0;
    }
}

// Registry queries for fixtures and gate observers. A record exists only for
// a placement-accepted muse bind; rejected binds leave no record.
bool pc_p2_generated_placement_is_bound(const BTeki* actor);
int pc_p2_generated_placement_bound_count();
// Death-funnel / slot-reuse forget and stage-boundary reset.
void pc_p2_generated_placement_forget(const BTeki* actor);
void pc_p2_generated_placement_reset();
