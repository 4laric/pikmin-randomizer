#pragma once
// Opt-in P2 Candypop Bud actor (family #171, #448). Sidecar-gated and
// fail-closed: without p2-pom.txt the module is inert. This bounded slice owns
// the source policy (budget/refund/close/sprouts/Queen cycle/base rejection)
// as a module-local actor anchored at sidecar positions; it does not spawn or
// drive the engine Pom FSM, and visual proxy draw is deferred (see
// docs/PIKMIN2_POM_NATIVE.md).
void pc_p2_pom_setup();
void pc_p2_pom_reset();
void pc_p2_pom_tick();
