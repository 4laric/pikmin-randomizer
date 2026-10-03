#include "pc_p2_retail_cave_placement.h"
#include "Vector.h"
namespace p2retail {
NativePlacementAuthority cargoPlacement(NativeFloor& floor){
 return [&floor](const SceneIdentity& scene,unsigned row,unsigned ordinal,Vector3f& out,float& yaw,std::string& error){
  Placement selected;if(!floor.placement(scene,row,ordinal,selected,error))return false;
  const Vector3f position(selected.x,selected.y,selected.z);
  const float radians=selected.yawDegrees*0.01745329251994329577f;
  out=position;yaw=radians;error.clear();return true;
 };
}
}
