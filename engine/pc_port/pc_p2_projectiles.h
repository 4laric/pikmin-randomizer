#pragma once

class BTeki;

// Additive projectile host seam (#413/#425, parent #169).
//
// Binds the isolated Cannon Stone lifecycle policy (`pc_p2_cannon_stone.*`,
// #406), Egg hazard/drop policy (`pc_p2_egg_hazard.*`, #410), Cannon Beetle
// fire FSM (`pc_p2_kabuto_cannon.*`, #424) and falling-Rock hazard
// (`pc_p2_rock_hazard.*`, #411) to the live P1 engine inside the private
// Pikipelago room preview. Homing selection uses the committed
// `P2ProjectileHostAdapter` (#412). Opt-in: a missing `p2-projectiles.txt` is a
// no-op, so ordinary P1 play and unconfigured rooms are untouched.
//
// Terrain convention: P2CannonStone positions are sphere CENTERS. P1
// `MapMgr::traceMove` accepts a sphere BASE and adds/subtracts the radius
// itself, so this host sends `base = center - (0, radius, 0)` and recovers
// `center = tracedBase + (0, radius, 0)`. Traces use the static map only
// (`ignoreDynColl = true`), matching the BombSarai (#244) adapter; P1 contact
// classification is a host approximation, not Pikmin 2 parity.
//
// This seam changes no shared semantics. It owns no saves, rewards, captain
// state, generic damage or actor lifetime: contacts are classified and logged,
// never applied to target health, and Egg drops are reported, never birthed.
// The Kabuto/Rkabuto fire FSM is host-driven through the committed policy with a
// configured mouth joint; the real per-species mouth matrix, animation bank and
// actor registration remain unimplemented and are reported as blockers.
void pc_p2_projectiles_setup();
void pc_p2_projectiles_update();
void pc_p2_projectiles_reset();
// Clear per-actor dedupe state so a recycled Teki pointer is never assumed live.
void pc_p2_projectiles_forget(BTeki* actor);
