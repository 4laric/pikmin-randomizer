#pragma once
#include "pc_p2_retail_cave_native.h"
namespace p2retail {
// Same signature as the actual cargo PlacementAuthority; no caller pose copy.
using NativePlacementAuthority=std::function<bool(const SceneIdentity&,unsigned,unsigned,Vector3f&,float&,std::string&)>;
// Borrowed floor must outlive every cargo callback, including partial release.
NativePlacementAuthority cargoPlacement(NativeFloor&);
}
