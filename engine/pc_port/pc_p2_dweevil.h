#pragma once
// Pikmin 2 lane-22 dweevil family sidecar runtime (#170, child #447).
//
// Opt-in static treasure capture/drop simulation for FireOtakara (59),
// WaterOtakara (60), GasOtakara (61) and ElecOtakara (62). Gated on
// p2-dweevil-native.txt: absent file means inert, malformed file fails closed.
// Actor-local only: generic damage/physics, pellet ownership, receivers and
// rewards are untouched. Policy mirrors pc_p2_dweevil_policy.h, which mirrors
// experimental/pikmin2_elemental_behavior.py.
void pc_p2_dweevil_setup();
void pc_p2_dweevil_reset();
void pc_p2_dweevil_update();
unsigned long pc_p2_dweevil_behavior_tick();
