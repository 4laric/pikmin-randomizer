#pragma once
class Graphics;
class Piki;

// Hard-lane shared registration seam (#244 BombSarai, #245 Fuefuki, #246
// BigTreasure). Opt-in: only active inside the Pikipelago private room preview
// with a lane profile present; otherwise every entry point is a no-op and
// ordinary P1 play is untouched.
void pc_p2_hardlanes_setup();
void pc_p2_hardlanes_update();
void pc_p2_hardlanes_draw(Graphics&);
void pc_p2_hardlanes_reset();

// Additive (#246 motion staging): the private real-GL runtime fixture owns the
// BigTreasure visual clip player during its deterministic per-clip motion
// phase, so it can assert each staged clip dispatches its authored events.
// Production leaves the hardlanes source clock driving the visual bank.
void pc_p2_hardlanes_set_bigtreasure_visual_driven(bool driven);
// Read-only Fuefuki (#245) probes for the real-vehicle runtime fixture. The
// binding remains owned by the hardlane registration.
bool pc_p2_hardlanes_fuefuki_ready();
int pc_p2_hardlanes_fuefuki_state();   // P2FuefukiFsmState, or -1
int pc_p2_hardlanes_fuefuki_held_count();
Piki* pc_p2_hardlanes_fuefuki_held(int index); // k-th held Pikmin, or null
bool pc_p2_hardlanes_fuefuki_vehicle_position(float& x, float& y, float& z);
// Natural-hit ingress (#246): post one Pikmin-source hit against a BigTreasure
// weapon coll part (`weapon` in [0,3], or -1 for the body) into the ordinary
// FSM host drive. The lane-10 receiver / collision proxy is the intended
// caller. Returns false when the seam is inactive or the bounded queue rejects
// the hit (full, non-finite/non-positive damage or an out-of-range weapon).
bool pc_p2_hardlanes_bigtreasure_hit(int weapon, float damage, bool bittered);
