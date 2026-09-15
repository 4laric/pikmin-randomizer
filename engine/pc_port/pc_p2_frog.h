#pragma once
class BTeki;class PelletView;class Graphics;struct Matrix4f;
void pc_p2_frog_setup();
void pc_p2_frog_reset();
void pc_p2_frog_forget(BTeki*);
void pc_p2_frog_set_bittered(BTeki*,bool);
const char* pc_p2_frog_name(PelletView*);
float pc_p2_frog_param_f(const BTeki*,int idx,float fallback);
bool pc_p2_frog_draw(BTeki*,Graphics&,const Matrix4f&,bool corpse=false);
// Source Frog FSM (FrogState.cpp) ported onto the P1 Wollywog host (#167).
// `pc_p2_frog_update` advances the ten-state source FSM each frame for registered
// actors; `pc_p2_frog_suppress_ai` disables the P1 Otimoti TAI so the source FSM
// has exclusive control. Both are no-ops for unregistered actors.
void pc_p2_frog_update(BTeki*);
bool pc_p2_frog_suppress_ai(const BTeki*);
// Lane 21 read-only probe (#198): expose the running source-FSM animation state
// of a registered frog (state name, current clip, clip phase) for the Groink
// movement/animation evidence. Never mutates the actor or FSM.
bool pc_p2_frog_probe(const BTeki*, const char** state, const char** clip, float* phase);
