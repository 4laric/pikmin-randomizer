#pragma once
class BTeki;
class Teki;
class Creature;
class Piki;

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
// Called only by the actual descending PikiFlying collision callback, before
// the host changes the presser to Normal. False outside source press states.
bool pc_p2_elecbug_flying_press(BTeki*, Piki*);
// Ground movement precedes creature collisions in P1. Before Flying grounds,
// dispatch only an actual collision-part intersection with a live ElecBug.
bool pc_p2_elecbug_ground_press(Piki*);
// Read-only registration observability (mirrors pc_p2_sokkuri/armor) so the
// lifecycle fixture can prove forget clears stale state. Additive.
unsigned long pc_p2_elecbug_count();
bool pc_p2_elecbug_registered(BTeki*);
// P2 FSM owns movement/targeting/attacks every tick for registered ElecBug
// (frog pattern): BTeki::doAI returns early so the Chappy host strategy
// never runs. Damage still reaches mHealth via the update-phase
// mStoredDamage -> makeDamaged() drain; death finalizes via pcEscapeNow().
bool pc_p2_elecbug_suppress_ai(const BTeki*);
// Natural press adaptation (#165, inst-bugs #871): the source
// ElecBug::pressCallBack is triggered by a thrown-Pikmin landing of ANY color
// (PikiFlyingState/PikiHipDropState collision, velocity.y<0). In addition to
// the early Flying hooks, this inherited family-local fallback detects a
// descending Pikmin overlapping a registered ElecBug once per flip
// (REVERSE/DEAD short-circuit) and delegates to pc_p2_elecbug_pressed.
// P1-derived adaptation; logged P2_ELECBUG_NATURAL_PRESS. No-op for other actors.
void pc_p2_elecbug_check_landing_press(BTeki*);
