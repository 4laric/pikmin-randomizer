#pragma once
class BTeki;
class Pellet;
// Opt-in P2 Pellet Posy (Pelplant, source ID 0) release/capture receptor.
// Sidecar-gated and fail-closed: without p2-flora-pelplant.txt the module is
// inert and P1 Palm behaviour is untouched. The visuals come from the existing
// P1 Palm actor; this module only enforces the P2 source policy (full-only
// vulnerability, dead-state pellet release) and observes the release and the
// Pikmin capture. Onion-side seed accounting is deliberately not implemented.
void pc_p2_flora_setup();
void pc_p2_flora_reset();
void pc_p2_flora_forget(BTeki*);
void pc_p2_flora_tick();
bool pc_p2_flora_receipt(Pellet*);
