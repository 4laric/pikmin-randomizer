#pragma once
class BTeki;
class Creature;
class Graphics;
struct Matrix4f;

// Family-owned ground-invertebrate source behavior: Skitter Leaf (Sokkuri,
// EnemyID 79) on the batch-2 Chappy placement vehicle (#165/#346/#407).
// Every hook is a no-op for unregistered actors; ordinary P1 play is untouched.
void pc_p2_sokkuri_setup();
void pc_p2_sokkuri_reset();
void pc_p2_sokkuri_forget(BTeki*);
void pc_p2_sokkuri_update(BTeki*);

// InteractPress receiver: source pressCallBack -> StatePress (crushed) for a
// living, non-bithered Sokkuri. Returns false for any other actor.
bool pc_p2_sokkuri_pressed(BTeki*, Creature*);

// Source Life (fp00=120) plus harmless-host parameter zeroing for registered
// actors only.
float pc_p2_sokkuri_param_f(const BTeki*, int idx, float fallback);

// Draw support: for a registered live Sokkuri, writes the source clip name and
// normalized [0,1] phase for the current FSM state and returns true. The batch-2
// draw path consults this before its generic motion/velocity selection.
bool pc_p2_sokkuri_clip(const BTeki*, const char*& name, float& phase);

// Fixture observability: behavior-neutral, read-only registration queries so the
// lifecycle fixture can prove pc_p2_sokkuri_forget() clears a stale binding
// (count returns to zero). Additive; no runtime behavior changes.
unsigned long pc_p2_sokkuri_count();
bool pc_p2_sokkuri_registered(BTeki*);

// #578 receipt boundary observability: read-only reveal query. True once the
// actor's disguise has dropped (delivery bind established), false while
// still disguised. Lets the receipt fixture prove a disguised Sokkuri
// carries no bound source. Additive; no runtime behavior changes.
bool pc_p2_sokkuri_revealed(BTeki*);
