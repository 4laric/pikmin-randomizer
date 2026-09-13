#pragma once
#include "pc_p2_material_srt.h"
class Shape;
class Graphics;
namespace p2material {
// Two-stage diffuse + specular-raster * normal-texture addition. Retains host
// lighting; this is not a replacement for the source game's lighting rig.
bool drawSpecular(Shape&,Graphics&,unsigned material,unsigned texture,const Sample&,bool enabled=true);
}
