#pragma once
struct BTeki; struct Graphics; struct Matrix4f;
void pc_p2_mamuta_setup();
void pc_p2_mamuta_reset();
void pc_p2_mamuta_forget(BTeki*);
bool pc_p2_mamuta_draw(BTeki*, Graphics&, const Matrix4f&, bool corpse = false);
