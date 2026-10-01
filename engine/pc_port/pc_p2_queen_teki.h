#pragma once
class BTeki;
class Creature;
class Graphics;
class Matrix4f;
class PelletView;
// Empress Bulblax (Queen, enemy 30) OWN binding (#256): a seeded campaign
// actor on the P1 TEKI_Swallow vehicle, driven by the source FSM in
// pc_p2_queen_own.h; larvae (Baby, 31) are real P1 teki driven by the source
// Baby FSM. See pc_p2_queen_teki.cpp for the adaptation notes.
void pc_p2_queen_teki_setup();
void pc_p2_queen_teki_tick(BTeki*);
// Once per game frame outside the teki update loop: births queued larvae.
void pc_p2_queen_teki_frame();
void pc_p2_queen_teki_forget(BTeki*);
void pc_p2_queen_teki_reset();
bool pc_p2_queen_teki_is_bound(const BTeki*);
bool pc_p2_queen_teki_draw(BTeki*, Graphics&, const Matrix4f&, bool corpse = false);
// Bound Queen/larva: the P1 strategy is suppressed (the source FSM drives it).
bool pc_p2_queen_teki_suppress_ai(const BTeki*);
// BTeki::interact seam for InteractAttack (Queen::damageCallBack / Baby
// default). Returns -1 when the actor is not bound (caller continues), 0 when
// the hit is refused, 1 when it was stored.
int pc_p2_queen_teki_attack(BTeki*, Creature* owner, float damage);
// Queen::ignoreAtari (rolling: captains and enemies pass through).
bool pc_p2_queen_teki_ignore_atari(BTeki*, Creature* target);
// Larvae leave no carcass (Baby.cpp onInit disables EB_LeaveCarcass).
int pc_p2_queen_teki_corpse_type(BTeki*, int fallback);
// Draw-cull sphere (BTeki::drawDefault): the actor origin and the drawn P2
// body's radius. False when the actor is not a bound Queen/larva.
bool pc_p2_queen_teki_cull_bounds(const BTeki*, float* radius);
// Queen carcass grab radius (the host TPF_CorpseSize is Spotty-sized).
float pc_p2_queen_teki_corpse_radius(BTeki*, float fallback);
// Read-only FSM probe for the autoplay bot: state id (Queen.h StateID),
// face direction and home. False when the actor is not a live bound Queen.
bool pc_p2_queen_teki_probe(const BTeki*, int* state, float* faceDir, float* homeX, float* homeZ);
// Read-only lifecycle probes.
bool pc_p2_queen_teki_dead_key_seen();
unsigned long pc_p2_queen_teki_behavior_tick();
int pc_p2_queen_teki_attached_count(const BTeki*);
// Parameter-override seam (include/teki.h BTeki::getParameterF).
float pc_p2_queen_teki_param_f(const BTeki*, int idx, float fallback);
// Room-preview Pod corpse receipt + title name.
bool pc_p2_queen_teki_receipt(PelletView*, unsigned& generator);
const char* pc_p2_queen_teki_name(PelletView*);
