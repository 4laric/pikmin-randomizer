#pragma once
#include <string>
namespace p2pose {struct Pose;}
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
bool pc_p2_kochappy_geometry(BTeki*,p2pose::Pose&,std::string& clip,float& frame,bool& corpse);
// First registered Kochappy actor, used as the lane-11 Mother Bulbmin
// stand-in. Null when no Kochappy actor is registered.
BTeki* pc_p2_kochappy_first_registered();
