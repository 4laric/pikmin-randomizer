#pragma once
class BTeki;
class PelletView;
class Graphics;
struct Matrix4f;
void pc_p2_snow_setup();
void pc_p2_snow_reset();
void pc_p2_snow_forget(BTeki*);
float pc_p2_snow_max_health(const BTeki*, float fallback);
const char* pc_p2_enemy_name(PelletView*);
bool pc_p2_snow_draw(BTeki*, Graphics&, const Matrix4f&, bool corpse=false);
