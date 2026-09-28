#pragma once
struct BTeki;struct Graphics;struct Matrix4f;
void pc_p2_tank_setup();
void pc_p2_tank_reset();
void pc_p2_tank_forget(BTeki*);
bool pc_p2_tank_draw(BTeki*,Graphics&,const Matrix4f&);
void pc_p2_tank_draw_water(Graphics&);
