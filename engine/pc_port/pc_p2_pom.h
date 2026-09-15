#pragma once
class BTeki;
// Opt-in P2 Candypop Bud actor (family #171, #448). Sidecar-gated and
// fail-closed: without p2-pom.txt the module is inert. Slice 1 owned the
// source policy (budget/refund/close/sprouts/Queen cycle/base rejection) as a
// module-local actor; slice 2 binds each bud to a live batch-2 Chappy placement
// vehicle (the batch-2 `flora` family host) so the bud is an ordinary spawned,
// drawn actor whose FSM drives the drawn pose:
//   * pc_p2_pom_tick() lazily resolves each sidecar generator to its live
//     TEKI_Chappy host and reports P2_POM_BIND;
//   * pc_p2_pom_clip() feeds the bud's current FSM-state clip/phase into the
//     batch-2 draw chain; pc_p2_pom_report_draw() records a P2_POM_DRAW only
//     once the batch-2 chain confirmed the clip was found in the bank;
//   * pc_p2_pom_forget() releases the host binding on despawn.
void pc_p2_pom_setup();
void pc_p2_pom_reset();
void pc_p2_pom_tick();
void pc_p2_pom_forget(BTeki*);
bool pc_p2_pom_clip(const BTeki*, const char*& name, float& phase);
void pc_p2_pom_report_draw(const BTeki*);
