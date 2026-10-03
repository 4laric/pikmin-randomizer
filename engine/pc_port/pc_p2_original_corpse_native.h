#pragma once
#include "pc_p2_original_corpse_profile.h"
#include "pc_p2_original_corpse_ledger.h"
#include "pc_p2_original_corpse_death_policy.h"
#include <string>
class BTeki; class Pellet; class PelletView; class PelletConfig; class GoalItem;
struct Matrix4f; struct Vector3f;
// Provider callback: validates the literal profile and live native pellet manager.
// Provider still owns admission of its genuine dead animation/body bank.
bool pc_p2_original_corpse_resources(unsigned source,std::string& error);
// Producer must prove the actual Stone death boundary and call BEFORE dieSoon.
// Refuses nonoriginal actors, unknown causes and bodies already born. Only
// suppresses the normal corpse; carried cargo and Honey remain producer-owned.
bool pc_p2_original_corpse_set_death_cause(BTeki*,p2original::CorpseDeathCause,std::string& error);
// Only explicit original actors are routed. Unknown original profiles refuse;
// source55 has no corpse. P1/AP and preview-only actors retain their own path.
bool pc_p2_original_corpse_leaves(BTeki*,bool ordinary);
PelletConfig* pc_p2_original_corpse_config(PelletView*,PelletConfig* ordinary);
void pc_p2_original_corpse_born(Pellet*,PelletView*);
const p2original::CorpseProfile* pc_p2_original_corpse_profile(const Pellet*);
// Read-only full retained receipt before actual suction consumes it. False for
// unlabelled pellets, outputs unchanged; a stale source binding is a fault.
bool pc_p2_original_corpse_query(const Pellet*,p2original::CorpseRecord&);
void pc_p2_original_corpse_forget(Pellet*);
bool pc_p2_original_corpse_onion(Pellet*,GoalItem*,unsigned& grant);
void pc_p2_original_corpse_position(const Pellet*,Vector3f&,float direction);
void pc_p2_original_corpse_view_matrix(const Pellet*,Matrix4f&);
void pc_p2_original_corpse_collision(Pellet*);
// Explicit session boundary; refuse while actual native corpse bindings survive.
bool pc_p2_original_corpse_new_session(const std::string& catalog,std::string&);
// Call BEFORE source actor/provider release or App-heap reset. Physical corpse
// graphs cannot be restored yet: refuse unload while any body is still bound.
// Successful course unload preserves address-free receipts for ordinary reentry.
bool pc_p2_original_corpse_unload(std::string& error);
// SAVE owner authenticates this address-free receipt state together with stock.
bool pc_p2_original_corpse_snapshot(p2original::CorpseSnapshot&,std::string&);
