#pragma once
class BTeki; class Graphics; struct Matrix4f; class Teki; struct InteractAttack; class Pellet; class PelletView;
// Family-owned Long Legs (#312, parent #173) native registration for the
// installed bind-pose meshes. Optional, additive, opt-in via the Pikipelago
// room preview. Ordinary P1 actors and unconfigured families are untouched.
void pc_p2_long_legs_setup();
void pc_p2_long_legs_reset();
void pc_p2_long_legs_forget(BTeki*);
// Per-frame source-FSM tick, called from BTeki::update so it no longer depends
// on the actor being on camera. No-op for unregistered/dead actors.
void pc_p2_long_legs_update(BTeki*);
// Manager-level tick (gameCoreSection, unculled): advances every registered
// actor's FSM each frame even when the placement proxy is off-camera / grid
// culled, so the source 50 s cooldown path to Shot still runs.
void pc_p2_long_legs_update_all();
bool pc_p2_long_legs_draw(BTeki*, Graphics&, const Matrix4f&, bool corpse = false);
// Fixture observability (#397): read-only registration count / membership.
unsigned long pc_p2_long_legs_count();
bool pc_p2_long_legs_registered(BTeki*);
// Read-only damageable-window accessor (fixture/receiver observability): true
// only while a registered Long Legs has passed its landing immunity gate
// (Wait/Flick/Walk/Shot), false during Stay/Land or when unregistered.
bool pc_p2_long_legs_damageable(const BTeki*);
// Read-only fixture accessor: current FSM state name for a registered Long
// Legs ("unregistered" otherwise), so the walk fixture can re-visit a still
// dormant BigFoot with the staged captain instead of touching the actor.
const char* pc_p2_long_legs_state_name(const BTeki*);
// Source damage receiver (Houdai.cpp damageCallBack + EB_BitterImmune): true when
// a registered Long Legs must reject this InteractAttack because it is still
// bitter-immune (Stay or Land). False for unregistered actors so the shared
// tekiinteraction hook is a no-op for ordinary P1 play.
bool pc_p2_long_legs_receiver_rejects(Teki*, const InteractAttack*);
// Read-only fixture accessor: true while a registered Houdai's FSM is in Shot
// (the gun-exposed state), so the fixture can stage the squad until Shot is
// reached before assigning attacks (source timings, no clip compression).
bool pc_p2_long_legs_shot(const BTeki*);
// Pod receipt lookup (ordinary corpse delivery, mirrors lane 31's Waterwraith
// receipt + kurage/otakara): true and writes the source generator id when the
// delivered Pellet is a registered Long Legs corpse. Keyed on the corpse Pellet*
// captured at death (view-less-safe), with the PelletView backlink as fallback.
// Pure lookup, no ledger grant; the caller credits the shared Pod economy.
bool pc_p2_long_legs_receipt(Pellet*, unsigned& generator);
// Read-only fixture accessor: sweeps dead/undelivered corpse registrations and
// returns the surviving count. Proves the receipt is one-shot (a delivered corpse
// leaves no registration) and the liveness sweep runs.
unsigned long pc_p2_long_legs_corpse_count();
