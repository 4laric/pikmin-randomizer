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
// BombOtakara (93) is deliberately NOT bound here: it consumes the lane-20 shared
// Bomb blast contract and remains covered by pc_p2_bombotakara plus the batch-2
// visual path. Every hook is a no-op for unregistered actors.
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

// Fixture observability: behavior-neutral, read-only registration queries so the
// lifecycle fixture can prove pc_p2_otakara_forget() clears a stale binding and
// that a bound actor is damageable. Additive; no runtime behavior changes.
unsigned long pc_p2_otakara_count();
bool pc_p2_otakara_registered(BTeki*);
