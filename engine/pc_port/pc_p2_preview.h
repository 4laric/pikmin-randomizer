#pragma once
class Pellet;
class Graphics;
struct Matrix4f;
void pc_p2_preview_setup();
bool pc_p2_preview_draw(Pellet*, Graphics&, Matrix4f&);
bool pc_p2_preview_deliver(Pellet*);

bool pc_p2_preview_ready();
Pellet* pc_p2_preview_treasure();
