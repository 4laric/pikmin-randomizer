// Isolated compile candidate for the frozen host (#245): proves the
// lane-owned Fuefuki binding seam composes with the native pc_port
// registration seam (pc_p2_enemy.h) without symbol or type collisions.
// Compile-only (object output); not linked into any shared binary.
#include "pc_p2_enemy.h"
#include "pc_p2_fuefuki_binding.h"

// Reference the seam entry points without calling them, and instantiate
// the lane binding type against the frozen host include tree.
void (*const pc_p2_fuefuki_seam_ref_setup)()                       = &pc_p2_snow_setup;
void (*const pc_p2_fuefuki_seam_ref_forget)(BTeki*)                = &pc_p2_snow_forget;
const char* (*const pc_p2_fuefuki_seam_ref_name)(PelletView*)      = &pc_p2_enemy_name;

P2FuefukiBinding* pc_p2_fuefuki_seam_compile_check(P2FuefukiBinding* binding)
{
    return binding;
}
