#pragma once
struct BTeki;struct Graphics;struct Matrix4f;struct PelletView;
void pc_p2_kabuto_fsm_setup();
void pc_p2_kabuto_fsm_reset();
void pc_p2_kabuto_fsm_forget(BTeki*);
bool pc_p2_kabuto_fsm_draw(BTeki*,Graphics&,const Matrix4f&,bool corpse=false);
float pc_p2_kabuto_fsm_param_f(const BTeki*,int idx,float fallback);
void pc_p2_kabuto_fsm_update(BTeki*);
bool pc_p2_kabuto_fsm_suppress_ai(const BTeki*);
// #884 travelling Stone fleet: 30 Hz tick (stones outlive their shooter) and
// the stand-in draw. Called from gameCoreSection next to the projectile host.
void pc_p2_kabuto_fsm_update_stones();
void pc_p2_kabuto_fsm_draw_stones(Graphics&);
