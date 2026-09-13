#pragma once
class BTeki;class PelletView;class Graphics;struct Matrix4f;
void pc_p2_qurione_setup();
void pc_p2_qurione_reset();
void pc_p2_qurione_forget(BTeki*);
const char* pc_p2_qurione_name(PelletView*);
bool pc_p2_qurione_draw(BTeki*,Graphics&,const Matrix4f&,bool corpse);
