#pragma once
// Opt-in P2 plant scenery policy actor (family #171, #448). Sidecar-gated and
// fail-closed: without p2-plant.txt the module is inert. It binds live P1
// Plant actors by generator id, applies the LOD/floor-offset sizing rule, and
// evaluates the Spectralid sentinel slot rule. The lane-15 pc_p2_qurione module
// exposes no spawn seam, so a reserved sentinel plant reports
// `P2_PLANT_SENTINEL_BLOCKED reason=no_qurione_seam` instead of spawning.
void pc_p2_plant_setup();
void pc_p2_plant_reset();
void pc_p2_plant_tick();
