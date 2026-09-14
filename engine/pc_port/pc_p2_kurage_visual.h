#pragma once
class BTeki;
class Graphics;
class Matrix4f;
class Shape;
bool pc_p2_kurage_visual_setup();
void pc_p2_kurage_visual_reset();
Shape* pc_p2_kurage_visual_wait_shape();
Shape* pc_p2_kurage_visual_attack_shape();
bool pc_p2_kurage_visual_draw(BTeki*, Graphics&, const Matrix4f&, bool corpse = false);
