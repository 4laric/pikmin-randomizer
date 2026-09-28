#pragma once
class BTeki;
class Creature;
class Piki;
class Teki;
struct InteractAttack;

// Family-owned ground-invertebrate source behavior: Cloaking Burrow-nit (Armor,
// EnemyID 15) on the batch-2 Chappy placement vehicle (#165/#407).
// Bridge-eating states are source-backed N/A for the arena (no ItemBridge);
// every hook is a no-op for unregistered actors.
void pc_p2_armor_setup();
void pc_p2_armor_reset();
void pc_p2_armor_forget(BTeki*);
void pc_p2_armor_forget_piki(Piki*);
void pc_p2_armor_update(BTeki*);
float pc_p2_armor_param_f(const BTeki*, int idx, float fallback);
bool pc_p2_armor_clip(const BTeki*, const char*& name, float& phase);

unsigned long pc_p2_armor_count();
bool pc_p2_armor_registered(BTeki*);
// Source Game/Armor.cpp damage receiver (:117-141): true when a registered
// Armor must reject this InteractAttack (not bittered and not the source 'dmg1'
// part). Returns false for unregistered actors so the shared hook is a no-op.
bool pc_p2_armor_receiver_rejects(Teki*, const InteractAttack*);
// Source isEvent(0, EB_Bittered) has no P1 host equivalent; the port admits it
// as an explicit flag for a host/fixture to raise. No other lane is affected.
void pc_p2_armor_set_bittered(BTeki*, bool);
// Source Obj::doStartStoneState (:147-162): flick every creature stuck to the
// mouth with InteractFlick(this, 0, 0, FLICK_BACKWARD_ANGLE). The P1 host has no
// petrification lifecycle, so pc_p2_armor_update fires this on the rising edge
// of TEKIOPT_Pressed (documented port analogue) and finish on the falling edge.
void pc_p2_armor_start_stone(BTeki*);
void pc_p2_armor_finish_stone(BTeki*);
