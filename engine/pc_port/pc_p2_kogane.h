#pragma once
class BTeki;class PelletView;class Graphics;struct Matrix4f;class Teki;class Creature;
void pc_p2_kogane_setup();void pc_p2_kogane_reset();void pc_p2_kogane_forget(BTeki*);
const char* pc_p2_kogane_name(PelletView*);int pc_p2_kogane_source_id(PelletView*);
bool pc_p2_kogane_draw(BTeki*,Graphics&,const Matrix4f&,bool);
// Batch-4 behavior hooks (#219): all no-op for unregistered actors.
// A real Pikmin stick-attack (InteractAttack) on a registered beetle is the
// host's natural press stimulus and flips it (finite, frame-7 drop, escape on
// the third flip); the injected InteractPress path remains for fixtures.
float pc_p2_kogane_param_f(const BTeki*,int idx,float fallback);
int pc_p2_kogane_corpse_type(const BTeki*,int fallback);
bool pc_p2_kogane_pressed(Teki*,Creature* stimulus);
bool pc_p2_kogane_attacked(Teki*);
void pc_p2_kogane_update(BTeki*);
// Introspection for fixtures: 1 when a gas cloud is active, with anchor/radius out.
int pc_p2_kogane_gas_state(BTeki*,float* x,float* z,float* remaining);
// Slice 3 restart-dedupe introspection: read the persisted lane-06 onion-ledger
// row count (P2_RECEIPTS_1 + one row per grant) and re-drive a farmed beetle's
// three flip grants through the real pc_p2_receipt_host_grant Duplicate path,
// proving the reward cap holds even if the flip-count sidecar were lost.
int pc_p2_kogane_onion_ledger_rows();
int pc_p2_kogane_reprobe_duplicates(unsigned generator,int id);
int pc_p2_kogane_nectar_dropped(unsigned generator);
// #571 receipt-boundary introspection: true once this beetle burrowed/fled
// (terminal escape: corpse suppressed, delivery bind dropped) and true while it
// still holds the ordinary-delivery bind. Read-only; false when unregistered.
bool pc_p2_kogane_escaped(BTeki*);
bool pc_p2_kogane_delivery_bound(BTeki*);
