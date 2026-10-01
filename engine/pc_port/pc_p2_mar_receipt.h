#pragma once
class BTeki;
class PelletView;

// Family-owned corpse receipt adapter: Puffy Blowhog (Mar, EnemyID 29).
// Binds TEKI_Mar actors to their generators and resolves a delivered corpse
// view to a generator for the shared Pod dispatch
// (`pc_p2_preview_deliver` -> receipt "corpse:mar:<generator>").
//
// This adapter only names and resolves; it never credits a ledger itself.
// Exactly-once credit is owned by the caller through the lane-06 receipt host
// (`pc_p2_receipt_host.h`) or the Pod economy. Every function is a no-op for
// unregistered actors. The shared `pc_p2_preview.cpp` dispatch arm that calls
// `pc_p2_mar_receipt` requires existing-owner review (#186); this adapter must
// not be wired into shared dispatch without it.
void pc_p2_mar_receipt_setup();
void pc_p2_mar_receipt_reset();
// Record a bound Mar actor (idempotent). Returns false when the actor has no
// generator. Emits P2_MAR_RECEIPT_BIND on first bind.
bool pc_p2_mar_receipt_bind(BTeki* actor);
// Resolve a delivered corpse view to its generator. Returns false for unknown
// views. Emits P2_MAR_CORPSE_READY once per generator (first resolution).
bool pc_p2_mar_receipt(PelletView* view, unsigned& generator);
// Read-only registration observability (mirrors pc_p2_sokkuri/armor/elecbug)
// so a lifecycle fixture can prove forget clears a stale binding. Additive.
unsigned long pc_p2_mar_receipt_count();
bool pc_p2_mar_receipt_registered(BTeki* actor);
void pc_p2_mar_receipt_forget(BTeki* actor);