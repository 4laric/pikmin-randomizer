#pragma once
class BTeki;
class Teki;
class Creature;

// Family-owned ground-invertebrate source behavior: Anode Beetle (ElecBug,
// EnemyID 28) on the batch-2 Chappy placement vehicle (#165/#407).
// Implements the source Charge/ChildCharge two-beetle partner link and the
// press-to-flip Reverse runtime path. Every hook is a no-op for unregistered
// actors, and a registered singleton (no partner) falls back to the standalone
// Charge -> Discharge -> Return cycle.
void pc_p2_elecbug_setup();
void pc_p2_elecbug_reset();
void pc_p2_elecbug_forget(BTeki*);
void pc_p2_elecbug_update(BTeki*);
float pc_p2_elecbug_param_f(const BTeki*, int idx, float fallback);
bool pc_p2_elecbug_clip(const BTeki*, const char*& name, float& phase);
// Read-only FSM state name ("wait"/"charge"/"discharge"/"reverse"/...) for the
// private runtime fixture; nullptr when the actor is not a registered ElecBug.
const char* pc_p2_elecbug_state_name(const BTeki*);
// Attack receiver: true = swallow the attack. Registered ElecBugs are invulnerable
// until pressed into the source Reverse state (source ElecBug::init enables it,
// StateReverse::init disables it); a reversed beetle prints ATTACK_ACCEPTED and
// returns false so the host applies damage. Emits P2_ELECBUG_ATTACK_BLOCKED /
// P2_ELECBUG_ATTACK_ACCEPTED, and P2_ELECBUG_HIT from update on a health drop.
bool pc_p2_elecbug_attacked(Teki*);
// Press receiver: breaks any active partner link, then flips a live,
// non-bithered, non-reversed beetle into Reverse (P2_ELECBUG_FLIP, then
// P2_ELECBUG_STATE state=reverse). Pressing an actively discharging beetle also
// delivers the real lane-10 InteractDenki receiver to the pressing Pikmin
// (P2_ELECBUG_PRESS_DENKI): P2_ELECBUG_PRESS_SHOCK for a shockable species and
// P2_ELECBUG_PRESS_IMMUNE for an electric-immune Yellow/Bulbmin, decided by the
// lane-11 capability matrix.
bool pc_p2_elecbug_pressed(BTeki*, Creature*);
// Read-only registration observability (mirrors pc_p2_sokkuri/armor) so the
// lifecycle fixture can prove forget clears a stale binding. Additive.
unsigned long pc_p2_elecbug_count();
bool pc_p2_elecbug_registered(BTeki*);
// Natural press adaptation (#165): the source ElecBug::pressCallBack is triggered
// by a thrown-Pikmin / Purple-hipdrop landing (PikiFlyingState/PikiHipDropState
// collision, velocity.y<0). The P1 host routes no Pikmin->enemy InteractPress, so
// this family-local probe detects a descending Purple Pikmin overlapping a
// registered ElecBug once per descent and delegates to pc_p2_elecbug_pressed.
// P1-derived adaptation; logged P2_ELECBUG_NATURAL_PRESS. No-op for other actors.
void pc_p2_elecbug_check_landing_press(BTeki*);
