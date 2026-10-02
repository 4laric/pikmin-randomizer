#pragma once
class Pellet;
class GoalItem;
class Graphics;
struct Matrix4f;
void pc_p2_white_treasure_setup();
bool pc_p2_white_treasure_deliver(Pellet*);
bool pc_p2_white_treasure_draw(Pellet*, Graphics&, Matrix4f&);
bool pc_p2_white_treasure_is_pod(GoalItem*);
bool pc_p2_white_treasure_draw_pod(GoalItem*, Graphics&, Matrix4f&);
