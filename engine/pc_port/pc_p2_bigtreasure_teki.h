#pragma once
class BTeki;
class Creature;
class Graphics;
class Matrix4f;
// Titan Dweevil (BigTreasure, source 73) campaign actor (#246 OWN).
//
// In a campaign (bridge) session every seed actor whose source is 73 rides
// the TEKI_Swallow placement vehicle (p2campaign::hostType(73) == 4) and is
// driven by the engine-free source-order core (pc_p2_bigtreasure_own):
// the P1 Spotty Bulborb TAI is suppressed and blinded, Pikmin hits are routed
// through the source damageCallBack to the four weapon HP pools and then the
// body, the IK gait moves and turns the actor, the four element attacks hit
// real Pikmin/captains through the P1 receivers, and Dead KEYEVENT_END runs the
// host death funnel. Retail inputs are staged by the root installer:
//   p2-bigtreasure-parms.txt  (verbatim bigtreasure/enemyparm.txt)
//   p2_bigtreasure_events.txt (P2_RETAIL_EVENTS_1, 29 clips)
//   p2-bigtreasure-bank.txt   (P2_BIGTREASURE_BANK_1: pose frames, otakara_*
//                              joint matrices per pose, leg layout)
//   p2-bigtreasure-coll.txt   (verbatim bigtreasure/enemycoll.txt: the Titan's
//                              own CollPart tree, replacing the host's while
//                              bound; late spawns bind on their first tick)
//   assets/dataDir/courses/pikmin2room/bigtreasure_<clip>_<ii>.mod and
//   bigtreasure_pellet_<weapon>.mod
// All emissions are P2_BIGTREASURE_* markers keyed on the generator token.
void pc_p2_bigtreasure_teki_setup();
void pc_p2_bigtreasure_teki_reset();
void pc_p2_bigtreasure_teki_forget(BTeki*);
void pc_p2_bigtreasure_teki_tick(BTeki*);
bool pc_p2_bigtreasure_teki_is_bound(const BTeki*);
// Per-hit ingress from BTeki::interact (InteractAttack, before the host
// strategy sees it): records the attacker, damage and the InteractAttack
// CollPart (the part a Pikmin is stuck to; nullptr for a ground swing). The
// bound Titan wears its own retail collision tree, so the part decides the
// target exactly as BigTreasure::damageCallBack does. No-op when unbound.
class CollPart;
void pc_p2_bigtreasure_attack(BTeki* teki, Creature* attacker, float damage, CollPart* part);
// Blind the suppressed host and give it the source body life (fp00).
float pc_p2_bigtreasure_teki_param_f(const BTeki* teki, int idx, float fallback);
bool pc_p2_bigtreasure_teki_suppress_ai(const BTeki* teki);
// Read-only probe for the test-only autoplay bot: body health plus the live
// weapon HP of a bound, living Titan; `fallback` for anything else.
float pc_p2_bigtreasure_teki_effective_health(const BTeki* teki, float fallback);
// Read-only probe for the test-only autoplay bot (#246 bot assistance): the
// world XZ of the captured weapon nearest (x, z) -- where a player aims the
// throw cursor, since only the weapon parts are stickable while armed.
// False when unbound or unarmed.
bool pc_p2_bigtreasure_teki_aim_point(const BTeki* teki, float x, float z, float* outX, float* outZ);
// Draws the staged P2 pose for the FSM's clip/frame with the captured
// weapons on the animated otakara_* joints (corpse: last dead pose).
bool pc_p2_bigtreasure_teki_draw(BTeki* teki, Graphics& gfx, const Matrix4f& view, bool corpse = false);
