#pragma once

// Generic held ship part (#901). See pc_held_part_policy.h for the contract.
// Adoption for new enemy families: nothing to do as long as a real death goes
// through BTeki::die() or BTeki::dieSoon() (P2-bound actors, including
// pcEscapeNow) or BTeki::spawnItems (P1 strategies). Do not spawn the part
// from family code. P1 holders keep the vanilla spawnItems path only.

class BTeki;

// P2 source bound to this actor (family binding, seed generator uid, or the
// generator uid of the birth in progress), 0 for a P1 actor.
unsigned pc_held_part_p2_source(BTeki* teki);

// Generator uid of the teki being born right now. GenObjectTeki::birth and
// pc_p2_boss_arena_birth set it around reset()/startAI(), before the newborn
// has mGenerator, so the birth decision can see its P2 binding. Pass 0 to
// clear. Sim state: set and cleared synchronously inside one birth.
void pc_held_part_birth_uid(unsigned uid);

// Ship part carried by the P1 boss generator's pellet config, or 0 when the
// arena boss holds none. Resolved at runtime (BossMgr::setBossParam rule).
unsigned pc_held_part_for_pellet_config(int pelletConfigIdx);

// BTeki::startAI: returns true when the holder keeps its part (register the
// radar marker and use list). A P1 holder always keeps it (vanilla); a
// P2-bound holder is cleared when its part already exists.
bool pc_held_part_birth(BTeki* teki);

// Real-death funnel for P2-bound holders (die / dieSoon): drops the held part
// once. No-op for a P1 holder. Returns true when a part pellet was spawned.
bool pc_held_part_drop(BTeki* teki, const char* via);

// BTeki::spawnItems part branch: true when the vanilla spawn should run now.
// Always true for a P1 holder; latched for a P2-bound holder.
bool pc_held_part_claim_spawn_items(BTeki* teki);

// A P1 teki slot whose only protection is a held ship part (mID a UFO part,
// Parameter0 unset) stops being protected when the seed binds a P2 source
// there: the P2 occupant is born from the same personality and holds the part.
// The root seed only binds such a slot when its held_part_transfer flag is set
// (randomizer/p2_held_parts.py), so the binding itself is the contract.
bool pc_held_part_transfers(unsigned heldId, int parameter0, const void* generator);

// Make sure the part's pellet shape exists before a late spawn
// (PCT_LoadIfExists / un** parts are otherwise built only at stage init).
void pc_held_part_ensure_shape(unsigned partId);

// Log a held part assigned to a P2 occupant. via = "arena" (P1 boss arena)
// or "slot" (P1 part-holder teki slot).
void pc_held_part_log_assign(unsigned partId, unsigned source, unsigned target, int p1Kind, const char* via);
