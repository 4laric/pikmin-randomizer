#pragma once
class BTeki;
class PelletView;
class Graphics;
class Teki;
struct Matrix4f;
void pc_p2_dwarf_orange_setup();
void pc_p2_dwarf_orange_campaign_setup();
void pc_p2_dwarf_orange_reset();
void pc_p2_dwarf_orange_forget(BTeki*);
float pc_p2_dwarf_orange_max_health(const BTeki*,float fallback);
const char* pc_p2_dwarf_orange_name(PelletView*);
bool pc_p2_dwarf_orange_registered(const BTeki*);
bool pc_p2_dwarf_orange_generated();
void pc_p2_dwarf_orange_bind(Teki*,unsigned identity);
bool pc_p2_dwarf_orange_draw(BTeki*,Graphics&,const Matrix4f&,bool corpse=false);
