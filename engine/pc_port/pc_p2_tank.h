#pragma once
struct BTeki;struct Graphics;struct Matrix4f;struct PelletView;
void pc_p2_tank_setup();
void pc_p2_tank_reset();
void pc_p2_tank_forget(BTeki*);
bool pc_p2_tank_draw(BTeki*,Graphics&,const Matrix4f&,bool corpse=false);
void pc_p2_tank_draw_water(Graphics&);
float pc_p2_tank_param_f(const BTeki*,int idx,float fallback);
void pc_p2_tank_update(BTeki*);
bool pc_p2_tank_suppress_ai(const BTeki*);
bool pc_p2_tank_probe(const BTeki*,const char**,const char**,float*);
