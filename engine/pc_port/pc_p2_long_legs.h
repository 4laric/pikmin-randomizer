#pragma once
class BTeki; class Graphics; struct Matrix4f; class Teki; struct InteractAttack;
// Family-owned Long Legs (#312, parent #173) native registration for the
// installed bind-pose meshes. Optional, additive, opt-in via the Pikipelago
// room preview. Ordinary P1 actors and unconfigured families are untouched.
void pc_p2_long_legs_setup();
void pc_p2_long_legs_reset();
void pc_p2_long_legs_forget(BTeki*);
// Per-frame source-FSM tick, called from BTeki::update so it no longer depends
// on the actor being on camera. No-op for unregistered/dead actors.
void pc_p2_long_legs_update(BTeki*);
bool pc_p2_long_legs_draw(BTeki*, Graphics&, const Matrix4f&, bool corpse = false);
// Fixture observability (#397): read-only registration count / membership.
unsigned long pc_p2_long_legs_count();
bool pc_p2_long_legs_registered(BTeki*);
// Read-only damageable-window accessor (fixture/receiver observability): true
// only while a registered Long Legs has passed its landing immunity gate
// (Wait/Flick/Walk/Shot), false during Stay/Land or when unregistered.
bool pc_p2_long_legs_damageable(const BTeki*);
// Source damage receiver (Houdai.cpp damageCallBack + EB_BitterImmune): true when
// a registered Long Legs must reject this InteractAttack because it is still
// bitter-immune (Stay or Land). False for unregistered actors so the shared
// tekiinteraction hook is a no-op for ordinary P1 play.
bool pc_p2_long_legs_receiver_rejects(Teki*, const InteractAttack*);
