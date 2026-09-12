#pragma once
class Pellet;
class Graphics;
class GoalItem;
struct Suckable;
struct Matrix4f;
void pc_p2_preview_setup();
bool pc_p2_preview_draw(Pellet*, Graphics&, Matrix4f&);
bool pc_p2_preview_deliver(Pellet*);

bool pc_p2_preview_ready();
Pellet* pc_p2_preview_treasure();
Suckable* pc_p2_preview_goal();
bool pc_p2_preview_is_pod(GoalItem*);
bool pc_p2_preview_draw_pod(GoalItem*, Graphics&, Matrix4f&);
int pc_p2_preview_pokos();
