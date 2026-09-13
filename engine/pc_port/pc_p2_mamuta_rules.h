#pragma once
// Opt-in P2 Miulin (Mamuta, enemy ID 54) bury semantics layered on bound P1 Miurin actors.
// Enabled only in the room preview with p2-mamuta-rules.txt = P2_MAMUTA_RULES_1 and only for
// actors bound by pc_p2_mamuta (generator in p2-mamuta-actors.txt, type TEKI_Miurin).
// Source contract: docs/PIKMIN2_MAMUTA_AUDIT.md; P2 receiver interactPiki.cpp:377-442 /
// interactNavi.cpp:218-226; attack event miulinState.cpp:264-330.
struct Creature;
struct Piki;
struct Navi;

void pc_p2_mamuta_rules_setup();
void pc_p2_mamuta_rules_reset();
bool pc_p2_mamuta_rules_enabled();

// Tri-state consults: -1 = not applicable (fall through to the unmodified P1 path),
// 0 = P2 receiver rejected, 1 = P2 receiver applied.
int pc_p2_mamuta_bury_piki(Creature* owner, Piki* piki);
int pc_p2_mamuta_bury_navi(Creature* owner, Navi* navi);
