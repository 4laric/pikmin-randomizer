#pragma once
class BTeki;
class Creature;

// Family-owned aquatic source behavior: Jigumo / Hermit Crawmad (EnemyID 63,
// aquatic family #167) on the P1 TEKI_Chappy (3) placement vehicle, generator
// 374003 (#407). The source owns a PanHouse/nest (Jigumo.cpp:73) and runs the
// fourteen-state Jigumo FSM (jigumoState.cpp:16): Wait 0 -> Appear 1 -> Hide 2
// -> Dead 3 -> Attack 4 -> Miss 5 -> Return 6 -> Carry 7 -> Flick 8 -> Eat 9
// -> Search 10 -> SAttack 11 -> SMiss 12. Source revision
// 632af93787b9c95b63f0c13be32b161375ce3a96; retail parms from
// experimental/pikmin2_aquatic_assets.py (GPVE01 rev 0).
//
// BOUNDED SLICE: nest wait/hide, emerge, search, lunge attack on the nearest
// Pikmin/Navi, bite -> carrier -> eat, flick and dead. The source bite is
// resolved as an explicit capture at the banked bite event frame and exactly
// one InteractKill at the banked swallow frame, mirroring the Catfish/Armor
// ports. Every hook is a no-op for unregistered actors; no other lane is
// modified.
void pc_p2_jigumo_setup();
void pc_p2_jigumo_reset();
void pc_p2_jigumo_forget(BTeki*);
void pc_p2_jigumo_update(BTeki*);
float pc_p2_jigumo_param_f(const BTeki*, int idx, float fallback);
bool pc_p2_jigumo_clip(const BTeki*, const char*& name, float& phase);
