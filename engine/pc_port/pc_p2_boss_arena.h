#pragma once
// P2 boss arenas (owner ruling 2026-09-29): a P1 boss generator whose spawn uid
// the seed binds (ENEMY_P2) to a P2 boss births that boss's teki vehicle in
// place of the P1 boss; its arena mates (pc_p2_boss_arena_policy.h) stay empty.
// Unbound boss generators keep the unchanged P1 path.

class Creature;
class BirthInfo;
class Generator;
class GenObjectBoss;

// Re-key a P1 boss generator that is a day-file alias of a bound arena primary
// (pc_p2_boss_arena_policy.h kAlias) to the primary's uid, so the seed binding,
// the family setup and the corpse receipt all see one generator token.
void pc_p2_boss_arena_rekey(Generator* generator);

// Host teki type to reserve for a bound arena generator, or -1 when the
// generator is not a bound P2 boss arena spawn.
int pc_p2_boss_arena_host(Generator* generator);
// Extra teki types a bound P2 source draws with beyond its host (the
// Crawbster 94 rain Rocks/Egg use the Iwagon mesh as a stand-in, #897).
// Marks them in tekiMgr->mUsingType so startStage loads their shapes.
void pc_p2_reserve_source_extras(Generator* generator);

// True when this P1 boss generator shares an arena with a bound spawn
// generator and must stay empty (no P1 boss, no host).
bool pc_p2_boss_arena_suppressed(Generator* generator);

// Birth the P2 boss vehicle for a bound arena generator and hand it to the
// ordinary generated-placement bind path. Returns nullptr (logged) when the
// generator is not bound or the host type is not loaded.
Creature* pc_p2_boss_arena_birth(BirthInfo& info, const GenObjectBoss& boss);

// Read-only clearance measurement at an arena generator's birth position
// (P2_BOSS_ARENA_PROBE). Emitted for every catalogued arena generator when
// PIKMIN_P2_BOSS_ARENA_PROBE=1, and always for a bound P2 boss birth.
void pc_p2_boss_arena_probe(float x, float y, float z, unsigned uid, const char* kind, int type);
