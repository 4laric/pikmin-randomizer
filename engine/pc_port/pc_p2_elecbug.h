#pragma once
class BTeki;
class Teki;
class Creature;

// Family-owned ground-invertebrate source behavior: Anode Beetle (ElecBug,
// EnemyID 28) on the batch-2 Chappy placement vehicle (#165/#407).
// Every hook is a no-op for unregistered actors.
void pc_p2_elecbug_setup();
void pc_p2_elecbug_reset();
void pc_p2_elecbug_forget(BTeki*);
void pc_p2_elecbug_update(BTeki*);
float pc_p2_elecbug_param_f(const BTeki*, int idx, float fallback);
bool pc_p2_elecbug_clip(const BTeki*, const char*& name, float& phase);
// Attack receiver: true = swallow the attack (registered ElecBugs are invulnerable
// until pressed into the source Reverse state).
bool pc_p2_elecbug_attacked(Teki*);
// Press receiver: flips a live, non-bithered, non-reversed beetle into Reverse.
bool pc_p2_elecbug_pressed(BTeki*, Creature*);
