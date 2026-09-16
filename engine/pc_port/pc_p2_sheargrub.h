#pragma once
class BTeki;
class PelletView;
class Graphics;
struct Matrix4f;
void pc_p2_sheargrub_setup();
void pc_p2_sheargrub_reset();
void pc_p2_sheargrub_forget(BTeki*);
bool pc_p2_sheargrub_draw(BTeki*,Graphics&,const Matrix4f&,bool corpse=false);
const char* pc_p2_sheargrub_name(PelletView*);
bool pc_p2_sheargrub_receipt(PelletView*,unsigned& generator,int& value);
