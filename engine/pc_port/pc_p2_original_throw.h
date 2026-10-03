#pragma once
#include "pc_p2_original_throw_policy.h"
class Piki;
// Caller owns a currently live, throwable body. Only canonical, recruited RGB
// originals with matching runtime species select the P2 trajectory; -1 is P1.
int pc_p2_original_rgb_throw_species(const Piki*);
