#pragma once
class BTeki;
class Creature;

// Family-owned aquatic source behavior for the batch-3 Chappy placement
// vehicle: Toady Bloyster (UmiMushi, EnemyID 71) on the P1 TEKI_Chappy (3)
// host (#167/#374/#407). UmiMushi ships a dedicated shared FSM
// (UmiMushiState.cpp, registered at umiMushiState.cpp:18): Wait 0 -> Walk 1 ->
// Find 2 -> Search 3 -> Turn 4 -> Flick 5 -> Attack 6 -> Eat 7, Dead 8,
// Lost 9. Obj::onInit starts the FSM in Walk (umiMushi.cpp:141). Attack marks
// the tongue active at animation key event 3, eats Pikmin while active, then
// enters Eat and swallows (EnemyFunc::swallowPikmin) at the Eat animation end.
// Source revision 632af93787b9c95b63f0c13be32b161375ce3a96; retail parms from
// experimental/pikmin2_aquatic_assets.py (GPVE01 rev 0, UmiMushi DISC_PARMS).
//
// ATTACK / TONGUE ADAPTATION (recorded, not retail-faithful): the source
// seven-slot tongue (kamu_joint1..7, radius 30) is not representable on the P1
// host. The tongue capture is resolved as an explicit nearest-Pikmin capture
// inside the source fp22=170 attack hit radius at the banked attack1 bite event
// (frame 39, event 3), then exactly one InteractKill at the banked Eat swallow
// (eat1 animation end), mirroring the Catfish/Armor port.
//
// BOUNDED GAPS (recorded, not retail-faithful): no P2 water box (mWaterBox /
// Hamon sea height / dive/splash presentation), no shared UmiMushi::Mgr
// base (100) exclusion or Blind (101) half-scale/health/parameter split, no
// mid-boss BGM phase staging, and no eye/weak joint callbacks or material
// texture animation (umimusi_model1.btk). Target selection is a single active
// Navi; the two-player nearest-Navi branch, the source view-angle gate and the
// mouth-slot geometry test are port adaptations.
//
// Every hook is a no-op for unregistered actors; no other lane's module is
// modified.
void pc_p2_umimushi_setup();
void pc_p2_umimushi_reset();
void pc_p2_umimushi_forget(BTeki*);
void pc_p2_umimushi_update(BTeki*);
float pc_p2_umimushi_param_f(const BTeki*, int idx, float fallback);
bool pc_p2_umimushi_clip(const BTeki*, const char*& name, float& phase);
