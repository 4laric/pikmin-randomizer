#pragma once
class BTeki;
class PelletView;
class Graphics;
struct Matrix4f;
void pc_p2_snow_setup();
const char* pc_p2_enemy_name(PelletView*);
bool pc_p2_snow_draw(BTeki*, Graphics&, const Matrix4f&, bool corpse=false);
