#pragma once
#include "Interactions.h"
#include "Navi.h"

// P2 InteractBury damages captains without burying them (interactNavi.cpp:218).
// P1's generic bury receiver changes to NAVISTATE_Bury, so use its damage-only
// receiver instead. That receiver owns invulnerability/repeated-hit rejection,
// hurt-upgrade scaling, damage reactions and last-captain fatal-hit handling.
inline bool pc_p2_mamuta_hit_navi(Creature* owner, Navi* navi, float damage)
{
    if (!owner || !navi || !navi->isAlive() || !(damage > 0.0f)) return false;
    return navi->stimulate(InteractAttack(owner, nullptr, damage, false));
}
