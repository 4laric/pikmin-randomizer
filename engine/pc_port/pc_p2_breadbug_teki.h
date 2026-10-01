#pragma once
class BTeki;
class Creature;
class Graphics;
class Matrix4f;
class TekiEvent;
// Campaign OWN driver for the Breadbug (PanModoki, P2 source 38, #898).
//
// In a bridge (campaign) session every generator the seed binds to source 38
// spawns the P1 TEKI_Collec placement vehicle (p2campaign::hostType 38 -> 8).
// This sidecar binds each one to the engine-free source FSM
// (pc_p2_breadbug_fsm), suppresses and blinds the P1 Collec TAI, and binds the
// ordinary-delivery source (onion:p2:38) so the carried corpse credits 38.
// Retail damage model: ordinary Pikmin attacks are refused; thrown Pikmin that
// land on it while falling press it (fp06); a held cargo sucked into the Onion
// drops it for container damage (fp04); bombs hurt. Room preview actors keep
// the old visual proxy (pc_p2_breadbug_actor).
void pc_p2_breadbug_teki_setup();
// Dev console (#942): bind one late-spawned seed-38 actor (loads the staged
// parms/bank on first use). True when bound (or already bound).
bool pc_p2_breadbug_teki_bind_dynamic(BTeki*);
void pc_p2_breadbug_teki_reset();
void pc_p2_breadbug_teki_forget(BTeki*);
void pc_p2_breadbug_teki_tick(BTeki*);
bool pc_p2_breadbug_teki_is_bound(const BTeki*);
// True while the source FSM owns a bound Breadbug (alive or in its dead clip):
// BTeki::doAI returns before the P1 Collec strategy acts.
bool pc_p2_breadbug_teki_suppress_ai(const BTeki*);
// BTeki::eventPerformed seam: consumes every TekiEvent of an OWN Breadbug so
// the P1 Collec TAI never transitions, and turns a falling thrown Pikmin
// contact into a press and a map landing into bounceCallback. True = consumed.
bool pc_p2_breadbug_teki_event(BTeki*, const TekiEvent&);
// InteractAttack::actTeki seam: an ordinary attack on an OWN Breadbug is
// refused (damageCallBack is bitter-only). True = this sidecar decided.
// With the target-selection seam below this is a backstop only: a campaign run
// must show zero of these (attacker kind is logged to find any leak).
bool pc_p2_breadbug_teki_attack(BTeki*, const Creature* attacker, float damage);
// Target-selection seam (#898 fix): retail PanModokiBase::isLivingThing() is
// true only while bittered (PanModokiBase.h:93), and Pikmin free/attack AI
// (pikiAI.cpp:260/574/666), the captain's swarm (naviState.cpp:598) and a
// thrown Pikmin's stick (pikiState.cpp:2336) all skip a non-living teki. The
// port has no bitter spray, so a live bound Breadbug is never a Pikmin,
// captain punch, swarm or lock-on target. `site` names the P1 caller; the
// first skip per site is logged and all are counted (P2_BREADBUG_OWN_POS
// target_skips=). False for anything that is not a live bound Breadbug.
bool pc_p2_breadbug_teki_untargetable(const Creature*, const char* site);
// getParameterF chain: source life for TPF_Life, no P1 life regeneration.
float pc_p2_breadbug_teki_param_f(const BTeki*, int idx, float fallback);
// Draw hook: staged PanModoki pose bank keyed on the FSM clip/frame; the
// corpse draws the carcass clip (startCarcassMotion -> type5).
bool pc_p2_breadbug_teki_draw(BTeki*, Graphics&, const Matrix4f&, bool corpse = false);
// #1022 lair visual: every living bound Breadbug's PanHouse nest (world pass).
void pc_p2_breadbug_teki_draw_nests(Graphics&);
