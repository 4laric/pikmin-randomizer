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
