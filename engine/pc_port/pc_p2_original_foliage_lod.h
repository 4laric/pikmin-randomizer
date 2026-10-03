#pragma once
#include "pc_p2_original_group.h"
#include <cmath>
namespace p2original { namespace foliage {
// Retail Plants::Obj uses fp10 radius / fp11 height for these cylinders.
inline bool cylinderSource(unsigned source) {
 return source==51||source==52||source==80||source==88||source==90;
}
struct Cylinder { Position bottom; float height=0,radius=0; };
inline Cylinder sourceCylinder(unsigned source,const Position& position,float facing,float radius,float height) {
 Cylinder c{position,height,radius};
 if(source==88){c.bottom.x-=50*std::sin(facing);c.bottom.z-=50*std::cos(facing);}
 return c;
}
// Sys::Cylinder::culled: endpoint signed distances plus perpendicular radial
// support. Exact tangency is excluded. Camera plane normals are unit vectors;
// clamp tiny normalization roundoff so a near-vertical plane cannot produce NaN.
inline bool cylinderPlaneVisible(const Cylinder& c,float nx,float ny,float nz,float offset) {
 const float support=c.radius*std::sqrt(std::fmax(0.f,1.f-ny*ny));
 const float bottom=nx*c.bottom.x+ny*c.bottom.y+nz*c.bottom.z-offset;
 return bottom+support>0.f||bottom+ny*c.height+support>0.f;
}
} }
