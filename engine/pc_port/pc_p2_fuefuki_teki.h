#pragma once
// Campaign OWN port of the Antenna Beetle (P2 Fuefuki, source 41), #245.
//
// A seed-bound 41 rides a suppressed TEKI_Chappy placement vehicle (hostType
// 41 -> 3). Every live tick is decided by the engine-free source FSM
// (pc_p2_fuefuki_fsm.h), keyed on the actor's own campaign token; the host
// only integrates the FSM's velocity against its map collision. The retail
// key events (landing/landfail/jump/whisle/...) come from the staged
// P2_RETAIL_EVENTS_1 table through the verified retail player, the staged
// retail enemyparm.txt supplies every general/proper parameter, and the staged
// pose bank draws the P2 model (the P1 host model never draws while bound).
//
// Whistle theft is the source ActTeki contract: claimed Pikmin leave the party
// and walk the beetle's footmark trail (pc_p2_fuefuki_follow.h); they cannot be
// whistled back while the beetle lives, end with the emote -> Free exit when the
// beetle takes off (Jump KEYEVENT_3, EB_Untargetable), and fall into a
// non-lethal astonished Panic when it dies, from which a captain whistle
// reclaims them. None of the room-preview hardlanes concessions (engage slide,
// captain park, forced FreeMode recruits, carry-min=1) exist on this path.
class BTeki;
class Piki;
class Navi;
class Creature;
class Graphics;
class Matrix4f;

void pc_p2_fuefuki_teki_setup();
// Dev console (#942): bind one late-spawned seed-41 actor (loads the staged
// parms/motions/poses on first use). True when bound (or already bound).
bool pc_p2_fuefuki_teki_bind_dynamic(BTeki*);
void pc_p2_fuefuki_teki_reset();
void pc_p2_fuefuki_teki_forget(BTeki*);
void pc_p2_fuefuki_teki_tick(BTeki*);
bool pc_p2_fuefuki_teki_is_bound(const BTeki*);
int pc_p2_fuefuki_teki_bound_count();
// Read-only bot sense: true while a bound, living beetle is in its whistle
// cast (source StateWhisle), the only state that claims Pikmin.
bool pc_p2_fuefuki_teki_casting(const BTeki*);
// Host suppression: true while a bound beetle is alive or playing its dead clip.
bool pc_p2_fuefuki_teki_suppress_ai(const BTeki*);
// TPF_Life = retail fp00 and a blinded host strategy while bound and alive.
float pc_p2_fuefuki_teki_param_f(const BTeki*, int idx, float fallback);
// InteractPress receiver (source pressCallBack). True when the actor is bound
// (the host squash never runs on a bound beetle).
bool pc_p2_fuefuki_teki_pressed(BTeki*, Creature* presser);
// PikiFlyingState descending contact (source PikiFlyingState::collisionCallback
// InteractPress, pikiState.cpp:2319-2327). Returns true when the source
// pressCallBack returns true (beetle not in its mCanStruggle window): the press
// is absorbed and the thrown Pikmin must NOT latch. Returns false when the actor
// is not bound or the press was accepted (Struggle; the Pikmin latches as usual).
// `descending` is the source pikiVel.y < 0 gate; an ascending contact never
// presses (it only logs P2_FUEFUKI_FLY_CONTACT for evidence) and returns false.
bool pc_p2_fuefuki_teki_flying_press(BTeki*, Piki* presser, bool descending);
// InteractAttack::actTeki observer: attributes each accepted hit to its source
// (Pikmin, captain, other) for the DAMAGE marker. No gameplay effect.
void pc_p2_fuefuki_teki_attacked(BTeki*, Creature* owner, float damage, bool accepted);
// Draw hook: staged P2 pose bank (false -> host model draws), plus the
// whistle-ring stand-in while casting.
bool pc_p2_fuefuki_teki_draw(BTeki*, Graphics&, const Matrix4f&, bool corpse = false);

// Piki-side seams (all are O(1) no-ops while nothing is bound).
// Piki::doAI: true when a live beetle owns this Pikmin (ActTeki follow ran).
bool pc_p2_fuefuki_follower_controls(Piki*);
// Navi::callPikis: an ActTeki follower is not whistle-callable while its beetle
// lives (InteractFue::actPiki ACT_Teki branch).
bool pc_p2_fuefuki_follower_blocks_recruit(const Piki*);
// Piki::changeMode(FormationMode): any other path into a party (day-end
// gather, co-op transfer, ...) ends the ActTeki follow (source Brain::start of
// another action runs ActTeki::cleanup); a Pikmin the beetle released earlier
// logs P2_FUEFUKI_RECLAIM when it rejoins a captain.
void pc_p2_fuefuki_note_formation(Piki*, Navi*);
// PikiPanicState: true when this Panic is the owner-death PIKIPANIC_Panic
// (astonish) release, not the gas panic.
bool pc_p2_fuefuki_panic_astonish(const Piki*);
void pc_p2_fuefuki_panic_end(Piki*, bool timedOut);
// Navi::callPikis: records that a captain whistle reached a Pikmin this beetle
// released (reclaim itself is logged at the formation entry).
void pc_p2_fuefuki_note_whistle(Piki*, Navi*);
