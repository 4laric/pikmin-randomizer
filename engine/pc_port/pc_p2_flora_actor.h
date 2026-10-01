#pragma once
class BTeki;
class Pellet;
// Opt-in P2 Pellet Posy (Pelplant, source ID 0) release/capture receptor.
// Sidecar-gated and fail-closed: without p2-flora-pelplant.txt the module is
// inert and P1 Palm behaviour is untouched. The visuals come from the existing
// P1 Palm actor; this module enforces the P2 source policy (full-only
// vulnerability, dead-state pellet release), observes the release and the
// Pikmin capture, and records the delivered pellet as an exactly-once ordinary
// Onion/AP receipt through the shared pc_p2_receipt.h provider.
void pc_p2_flora_setup();
void pc_p2_flora_reset();
void pc_p2_flora_forget(BTeki*);
void pc_p2_flora_tick();
bool pc_p2_flora_receipt(Pellet*);
int pc_p2_flora_onion_receipts();
int pc_p2_flora_onion_duplicates();
