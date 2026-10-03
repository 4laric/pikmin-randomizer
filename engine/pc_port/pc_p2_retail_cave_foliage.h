#pragma once
#include "pc_p2_retail_cave_native.h"
namespace p2original { namespace foliage {class Native;} }
namespace p2retail {
// Borrowed native leaf must outlive the floor and every partial allocation.
bool bindFoliage(NativeFloor&,p2original::foliage::Native&,std::string&);
}
