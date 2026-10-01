#pragma once
class BTeki;
class Creature;
class PelletView;

// Family-owned lane-22 elemental-dweevil source behavior on the batch-2 Chappy
// placement vehicle (#170, child #447). Implements the shared OtakaraBase normal
// FSM subset (Wait / Move / Turn / Flick / Dead) for FireOtakara (59),
// WaterOtakara (60), GasOtakara (61) and ElecOtakara (62), driven from
// p2-dweevil-actors.txt / p2-dweevil-bank.txt written by the batch-2 dweevil
// arena.
//
// Unlike the earlier pc_p2_dweevil sidecar (a policy simulation over a staged
// treasure set), this module binds the real arena Teki actor by generator ID,
// sets the source health (fp00 general life) and drives the Flick discharge
// through the engine elemental receivers (InteractFire/Bubble/Gas/Denki), so the
// actor is now a real damageable elemental enemy rather than a sidecar. Death is
// the natural queue-then-apply path (see docs/PIKMIN2_RECEIVER_PATHS.md): the
// host Chappy TAI fulfils the reaction → makeDamaged → dieSoon → corpse, and this
// module only drives the source dead clip.
//
// BombOtakara (93) IS bound here (inst3-misc OWN): the carrier FSM drives
// locomotion/targeting and detonates the carried Bomb via the shared blast
// primitive on its own BTeki tick. The lane-20 sidecar remains preview-only.
class CollPart;
void pc_p2_otakara_setup();
// Generated-placement bridge (lane 03/04): register the randomizer-claimed
// actor for its seeded elemental-dweevil source (59-62) by generator ID.
bool pc_p2_otakara_bind_dynamic(BTeki*, unsigned generatorId, unsigned sourceId);
void pc_p2_otakara_reset();
void pc_p2_otakara_forget(BTeki*);
void pc_p2_otakara_update(BTeki*);

// Host death-seam hook (BTeki::die): logs P2_OTAKARA_DEAD from the real
// die()/mDeadState transition, distinct from the module's own mHealth<=0
// observation (P2_OTAKARA_MODULE_DEAD). No-op for unregistered actors.
void pc_p2_otakara_died(BTeki*);

// Lane-06 ordinary-Onion receipt hook (pc_p2_preview_deliver): pure lookup —
// returns true and writes the generator ID only for a pellet whose mPelletView
// is a registered Otakara actor. It performs no ledger grant; the caller credits
// the shared Pod economy and emits P2_POD_RECEIPT.
bool pc_p2_otakara_receipt(PelletView*, unsigned& generator);

// Damage attribution: records the queued attack interaction (label + owner
// colour) for the next P2_OTAKARA_HIT log, so a natural Pikmin melee drop is
// named rather than left as an unlabelled delta. Read-only no-op for
// unregistered actors; hooked from BTeki::interactDefault's Attack branch.
void pc_p2_otakara_attack(BTeki*, Creature* owner, const char* interaction);

// Source per-species general life (fp00) plus harmless-host parameter zeroing for
// registered actors only.
float pc_p2_otakara_param_f(const BTeki*, int idx, float fallback);

// Draw support: for a registered live dweevil, writes the source clip name and
// normalized [0,1] phase for the current FSM state and returns true. The batch-2
// draw path consults this before its generic motion/velocity selection.
bool pc_p2_otakara_clip(const BTeki*, const char*& name, float& phase);
// Volatile Dweevil (93) carried-Bomb visuals (pc_p2_bomb_telegraph.h), output-only:
// the P1 bomb-rock shape on the Dweevil's back (flashing while the fuse burns)
// and the bomb's own countdown wheel gauge. No-ops for other actors.
class Graphics;
class Matrix4f;
void pc_p2_otakara_draw_bomb(BTeki*, Graphics&, const Matrix4f& matrix);
// Returns true for a Volatile Dweevil: the caller then skips the carrier's own gauge.
bool pc_p2_otakara_bomb_gauge(BTeki*, Graphics&);


// Fixture observability: behavior-neutral, read-only registration queries so the
// lifecycle fixture can prove pc_p2_otakara_forget() clears a stale binding and
// that a bound actor is damageable. Additive; no runtime behavior changes.
unsigned long pc_p2_otakara_count();
bool pc_p2_otakara_registered(BTeki*);

// Press/landing hooks (#884, pc_p2_otakara_press_policy.h). Both return true only
// for a registered Dweevil (59-62, 93), meaning "consumed: skip the P1 host squash".
// Source OtakaraBase has no pressCallBack/flyCollisionCallBack override, so a press
// or a thrown Pikmin landing does no damage and the Pikmin latches on (P2
// pikiState.cpp:2321-2342). Each logs P2_OTAKARA_PRESS once per press.
//   pc_p2_otakara_pressed: InteractPress::actTeki, before the host Pressed event.
//   pc_p2_otakara_smashed: TaiSmashedAction::actByEvent, for a PIKISTATE_Flying
//                          Piki Entity contact, before the host smash transit.
bool pc_p2_otakara_pressed(BTeki*, Creature* presser);
bool pc_p2_otakara_smashed(BTeki*, Creature* presser);

// Dweevil family fidelity hooks (pc_p2_otakara_part.h / pc_p2_otakara_item.h).
//
// pc_p2_otakara_attack_part (InteractAttack::actTeki): -1 = not a registered 59-62 Dweevil or
// not a Pikmin/Navi hit (caller continues unchanged), 1 = accepted (a collision part came with the
// hit), 0 = refused (partless ground punch: source OtakaraBase::damageCallBack returns false
// without a part, OtakaraBase.cpp:190-197). Logs P2_OTAKARA_PART.
int pc_p2_otakara_attack_part(BTeki*, Creature* owner, CollPart* part, float damage);

// pc_p2_otakara_divert (BTeki::interactDefault Attack branch): true when the registered Dweevil
// is carrying a treasure and the damage was absorbed by the treasure's health instead
// (damageTreasure, OtakaraBase.cpp:563-574); the caller then skips mStoredDamage.
bool pc_p2_otakara_divert(BTeki*, Creature* owner, float damage);
