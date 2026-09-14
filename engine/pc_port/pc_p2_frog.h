#pragma once
class BTeki;class PelletView;class Graphics;struct Matrix4f;
void pc_p2_frog_setup();
void pc_p2_frog_reset();
void pc_p2_frog_forget(BTeki*);
void pc_p2_frog_set_bittered(BTeki*,bool);
const char* pc_p2_frog_name(PelletView*);
float pc_p2_frog_param_f(const BTeki*,int idx,float fallback);
bool pc_p2_frog_draw(BTeki*,Graphics&,const Matrix4f&,bool corpse=false);
