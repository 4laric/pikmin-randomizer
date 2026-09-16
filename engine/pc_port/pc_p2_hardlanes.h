#pragma once
class Graphics;
class Piki;
class Creature;
class Teki;
class PelletView;
class Generator;
struct BTeki;

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
// Natural combat receiver (#245): source pressCallBack/hipdropCallBack enter
// Struggle when mCanStruggle and not bittered. The host maps a P1 InteractPress
// stimulus onto the bound Fuefuki vehicle; admission stays in the FSM. Returns
// true and latches the press fact when the pressed Teki is the bound vehicle;
// false otherwise, so ordinary P1 play is untouched. Only active inside the
// private room preview with the Fuefuki vehicle bound.
bool pc_p2_hardlanes_fuefuki_pressed(Teki*, Creature* stimulus);
// Introspection for the runtime fixture: count of press/hipdrop stimuli
// latched since the current vehicle was bound.
unsigned pc_p2_hardlanes_fuefuki_press_count();
// Lifecycle seam (#397/#245): when the bound Fuefuki vehicle is forgotten at
// death teardown or manager-slot reuse, drop the raw Teki* and the pending press
// latch so the per-tick sticker walk and pointer-equality press check never run
// on a despawned/reused actor. No-op for any other actor.
void pc_p2_hardlanes_forget(BTeki*);

// (#245 transport_reward) Per-actor hook called from BTeki::update after the P1
// strategy's act()/moveNew(). Grounds the flying Napkid host so a FreeMode squad
// can attack it and registers the carcass on the natural death tick. Preview-only
// and a no-op for any actor that is not the bound Fuefuki vehicle.
void pc_p2_hardlanes_fuefuki_actor(BTeki*);
// (#245 transport_reward) Research Pod corpse receipt: resolves the live vehicle
// or its naturally dead carcass to the generator for `corpse:...fuefuki:<gen>`.
// Returns false for any unregistered pellet so ordinary cargo is untouched.
bool pc_p2_hardlanes_fuefuki_receipt(PelletView*, unsigned& generator);

// (#245 gate probes) Read-only observation hooks for the real-GL gate fixture.
// The bound vehicle's lane FSM state + the converted motion clip name and its
// advancing pose counter (the "animation state/counter"); the P1 Napkid host
// position is read separately through the fixture so the two are labelled
// independently. `pose` is -1 when no converted motion bank is staged.
int pc_p2_hardlanes_fuefuki_motion_state();
int pc_p2_hardlanes_fuefuki_motion_pose();
const char* pc_p2_hardlanes_fuefuki_motion_clip();
// Source ticks driven into the lane FSM since the vehicle was bound (lane-side
// animation/FSM time, distinct from the P1 host's own frame clock).
unsigned long pc_p2_hardlanes_fuefuki_tick_count();
// (#245 gate 3) Real engine receiver ingress: `InteractAttack::actTeki` delivers
// an attack to the bound vehicle; called from tekiinteraction.cpp after the
// engine's `teki->interact()` applied the hit. Records the hit and the live
// target's health so the fixture can observe the health/state change.
void pc_p2_hardlanes_fuefuki_hit(Teki*, Creature* owner, float damage, bool accepted);
unsigned pc_p2_hardlanes_fuefuki_hit_count();
// (#245 gate 6) Lifecycle observation: forget/reset marker counts and the bound
// generator object captured at bind time (so a fixture can drive the real
// generator rebirth + scene re-entry and prove no stale pointer survives).
unsigned pc_p2_hardlanes_fuefuki_forget_count();
unsigned pc_p2_hardlanes_fuefuki_reset_count();
Generator* pc_p2_hardlanes_fuefuki_generator_object();
// Natural-hit ingress (#246): post one Pikmin-source hit against a BigTreasure
// weapon coll part (`weapon` in [0,3], or -1 for the body) into the ordinary
// FSM host drive. The lane-10 receiver / collision proxy is the intended
// caller. Returns false when the seam is inactive or the bounded queue rejects
// the hit (full, non-finite/non-positive damage or an out-of-range weapon).
bool pc_p2_hardlanes_bigtreasure_hit(int weapon, float damage, bool bittered);

// Slice-2 read/probe hooks (lane 32, #246; additive, opt-in room-preview only):
//   * ready() reports whether the ordinary BigTreasure seam is installed live.
//   * weapon_count() reports the live attached-weapon count (4 at full loadout),
//     so a natural-hit ingress can be observed knocking a weapon off (4->3).
//   * recv_probe() drives the ordinary loop's per-attack handled set +
//     elemental receiver against one live Piki exactly as the loop would, and
//     is only here so a real-GL fixture can prove "no re-stimulation"
//     deterministically. Returns 1 applied-accepted, -1 applied-but-immunity,
//     0 already-handled this attack (or inactive seam).
bool pc_p2_hardlanes_bigtreasure_ready();
int pc_p2_hardlanes_bigtreasure_weapon_count();
// Current FSM phase (P2BigTreasurePhase, or P2BT_Dead when inactive); read-only
// so a real-GL fixture can observe the weapon-loss re-pick after a knock-off.
int pc_p2_hardlanes_bigtreasure_phase();
int pc_p2_hardlanes_bigtreasure_recv_probe(int weapon, Piki* piki);
