#pragma once
#include "pc_p2_original_piki_origin.h"
#include "pc_p2_original_piki_spawn.h"
#include <array>
#include <string>
// Physical GenPiki construction seam. The caller still owns whole-course
// admission/progress/order; this does not install a startup provider.
// On Born, ownership is the live PikiMgr pool. On refusal/CapacitySkipped,
// output is unchanged. No floor correction or placement RNG is performed.
p2original::PikiBirthResult pc_p2_original_piki_physical_birth(
 const OriginalPikiBody&,const std::array<float,3>& position,Piki*& out,
 std::string& error);
