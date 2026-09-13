#pragma once
class BTeki;
class Graphics;
struct Matrix4f;
void pc_p2_breadbug_actor_setup();
void pc_p2_breadbug_actor_reset();
void pc_p2_breadbug_actor_forget(BTeki*);
bool pc_p2_breadbug_actor_draw(BTeki*,Graphics&,const Matrix4f&);
