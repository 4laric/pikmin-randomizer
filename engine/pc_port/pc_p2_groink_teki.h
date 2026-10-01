#pragma once
class BTeki;
class PelletView;
class Generator;
class Graphics;
class Matrix4f;
class Piki;
class Creature;
class CollPart;
// Family sidecar binding the parked P2GroinkCarcass policy to a live generated
// Groink host actor (MiniHoudai 78 / FminiHoudai 97).  Binding is read from
// p2-groink-teki.txt at finalSetup; the carcass lifecycle is then driven once
// per frame from the actor's own update and the KillPellet / RequestBirth /
// ActivateGauge / DeactivateGauge host commands act on the real pellet and
// life gauge.  All emissions are logged as P2_GROINK_CARCASS_* markers.
void pc_p2_groink_teki_setup();
// Dev console (#942): bind one late-spawned seed-78/97 actor in bridge mode
// (loads the staged parms/bank on first use). True when bound (or already bound).
bool pc_p2_groink_teki_bind_dynamic(BTeki*);
void pc_p2_groink_teki_reset();
void pc_p2_groink_teki_forget(BTeki*);
void pc_p2_groink_teki_tick(BTeki*);
bool pc_p2_groink_teki_is_bound(const BTeki*);
// Read-only probes for the runtime fixture / root validator.  timer() and
// health() surface the policy's own regeneration timeline; the requested-birth
// count confirms the carcass-birth marker was produced, not injected.
float pc_p2_groink_teki_timer(const BTeki*);
float pc_p2_groink_teki_health(const BTeki*);
int pc_p2_groink_teki_births(const BTeki*);
// Process-wide RequestBirth count. Survives pc_p2_groink_teki_forget (and the
// deferred pellet kill that erases the per-actor binding on the BIRTH tick), so a
// runtime fixture can observe that the birth marker fired without re-reading the
// now-torn-down actor. Monotonic; reset only on a full process reset.
int pc_p2_groink_teki_total_births();
// (#198 gate 6) Lifecycle probes for the cleanup/re-entry rehearsal. `bound_count`
// is the live binding count; the forget/reset counts surface the real engine
// seams (`pc_p2_forget_teki` death funnel, `pc_p2_reset_all_teki` stage teardown),
// and `generator_object` is the bound actor's generator captured at bind time so a
// fixture can drive the real `mGenType->init()` rebirth.
int pc_p2_groink_teki_bound_count();
unsigned pc_p2_groink_teki_forget_count();
unsigned pc_p2_groink_teki_reset_count();
Generator* pc_p2_groink_teki_generator_object();
// Pod receipt: maps a carried corpse pellet's PelletView back to the bound
// Groink host generator, so pc_p2_preview_deliver can credit
// `corpse:groink:<gen>`. Returns false for any pellet this sidecar does not own.
bool pc_p2_groink_receipt(PelletView* view, unsigned& generator);
// Host life-clamp seam (chained in teki.h getParameterF, like lane 24's King
// host). In the isolated room preview a natural free-mode squad cannot reliably
// out-damage the P1 Frog host, so the bound host's TPF_Life is capped. This is a
// parameter override, never a health write; returns `fallback` for any other
// parameter or unbound actor. For 97 live (inst3 OWN) it also blinds sight/
// attack ranges so the P2 pedestal FSM has last word.
float pc_p2_groink_teki_param_f(const BTeki* teki, int idx, float fallback);
// Host suppression (#888 OWN): true for a campaign-bound 78/97 while alive
// or dying, disabling the P1 Frog TAI so the source FSM decides each tick.
bool pc_p2_groink_teki_suppress_ai(const BTeki* teki);
// Draw hook (#888 WP5): a campaign-bound 78/97 draws the staged P2
// MiniHoudai pose bank driven by the source FSM animation (corpse: carcass
// clip). False (host model draws) when no bank is staged or unbound.
bool pc_p2_groink_teki_draw(BTeki* teki, Graphics& gfx, const Matrix4f& view, bool corpse = false);
// #892 armour cover: a Pikmin touched `part` of a bound campaign Groink while trying to
// latch (thrown landing or a jump attack). `site` names the caller. Part `body` (st__)
// takes the latch; the touch-only parts (cov1..cov3 face cover, asiL/asiR, coll) do not:
// the Pikmin bounces and no damage follows. Logs P2_GROINK_ARMOR_BLOCK / _HIT. Observer
// only: the engine's own CollPart::isStickable decides the latch. No-op for unbound actors.
void pc_p2_groink_teki_piki_contact(BTeki* teki, Piki* piki, CollPart* part, const char* site);
// Armour verdict counts for the actor (probe for runtime fixtures/bots).
void pc_p2_groink_teki_armor_counts(const BTeki* teki, int& blocks, int& hits);
// #892: damage rule for a hit from `owner` on a bound campaign Groink (InteractAttack::actTeki).
// Returns -1 when the rule does not apply (host path unchanged), 0 to refuse, else the scale.
float pc_p2_groink_teki_damage_rate(BTeki* teki, Creature* owner, CollPart* part);
