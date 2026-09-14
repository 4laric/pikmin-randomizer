#pragma once
class BTeki;
class Creature;

// Family-owned aquatic source behavior for the batch-3 host: Catfish (Water
// Dumple, EnemyID 26) on the P1 TEKI_Namazu (30) placement vehicle
// (#167/#374/#407). Catfish ships no CatfishState.cpp: it forwards onInit/birth
// to the shared KochappyBase FSM (KochappyBase.cpp, kochappyState.cpp) with its
// own Catfish::Obj overrides. This port implements that inherited source FSM:
// Wait 0 -> Turn 2 -> Walk 3 -> Attack 4 (animation-event bite -> swallow) ->
// Flick 5, TurnToHome 6 -> GoHome 7, Dead 1. Source revision
// 632af93787b9c95b63f0c13be32b161375ce3a96; retail parms from
// experimental/pikmin2_aquatic_assets.py (GPVE01 rev 0).
//
// ATTACK / MOUTH ADAPTATION (recorded, not retail-faithful): the P2 Catfish
// owns a two-slot mouth (kamu1/kamu2, Catfish.cpp:83) that is not representable
// on the P1 host. The mouth swallow is resolved as an explicit capture inside
// the source attack sweep radius at the banked attack bite animation event
// (attack frame 17, event 2), then exactly one InteractKill at the banked
// swallow event (attack frame 75, event 3), mirroring the Armor port. Catfish
// ships no waitact1 clip (the KochappyBase Turn motion), so Turn reuses wait1.
// Target detection accepts the nearest Navi or Pikmin; the source view angle is
// treated as a full hemisphere because the Catfish general block does not
// override it. Turn rate, flick radius and shake values are P1-host values.
//
// Every hook is a no-op for unregistered actors; no other lane's module is
// modified.
void pc_p2_catfish_setup();
void pc_p2_catfish_reset();
void pc_p2_catfish_forget(BTeki*);
void pc_p2_catfish_update(BTeki*);
float pc_p2_catfish_param_f(const BTeki*, int idx, float fallback);
bool pc_p2_catfish_clip(const BTeki*, const char*& name, float& phase);
