#pragma once
class BTeki;class PelletView;class Graphics;struct Matrix4f;
void pc_p2_kogane_setup();void pc_p2_kogane_reset();void pc_p2_kogane_forget(BTeki*);
const char* pc_p2_kogane_name(PelletView*);int pc_p2_kogane_source_id(PelletView*);
bool pc_p2_kogane_draw(BTeki*,Graphics&,const Matrix4f&,bool);
