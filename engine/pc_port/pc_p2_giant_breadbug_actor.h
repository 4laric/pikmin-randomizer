#pragma once
class BTeki;
class Graphics;
class TekiEvent;
struct Matrix4f;
void pc_p2_giant_breadbug_actor_setup();
void pc_p2_giant_breadbug_actor_reset();
void pc_p2_giant_breadbug_actor_forget(BTeki*);
void pc_p2_giant_breadbug_actor_tick();
bool pc_p2_giant_breadbug_actor_press(BTeki*,const TekiEvent&);
bool pc_p2_giant_breadbug_actor_draw(BTeki*,Graphics&,const Matrix4f&);
