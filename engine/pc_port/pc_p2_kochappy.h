#pragma once
class BTeki;
class PelletView;
class Graphics;
struct Matrix4f;
void pc_p2_kochappy_setup();
void pc_p2_kochappy_reset();
void pc_p2_kochappy_forget(BTeki*);
float pc_p2_kochappy_max_health(const BTeki*,float fallback);
const char* pc_p2_kochappy_name(PelletView*);
bool pc_p2_kochappy_draw(BTeki*,Graphics&,const Matrix4f&,bool corpse=false);
bool pc_p2_kochappy_registered(const BTeki*);
