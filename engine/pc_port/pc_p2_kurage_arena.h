#pragma once

class Graphics;
class Creature;
class CollPart;

void pc_p2_kurage_arena_reset();
bool pc_p2_kurage_arena_setup(const char* profilePath);
bool pc_p2_kurage_arena_update(float delta, bool ownerAlive);
// Retail attack.bca Player/event-clock path used by the live bounded host.
bool pc_p2_kurage_arena_begin_attack();
bool pc_p2_kurage_arena_tick_attack(float delta);
void pc_p2_kurage_arena_draw(Graphics& gfx);
Creature* pc_p2_kurage_arena_owner();
CollPart* pc_p2_kurage_arena_mouth();
int pc_p2_kurage_arena_scan_admit(float verticalOffset, float attackRadius, int maxAdmissions, bool admitEligible);
// Explicit test seam only; live hosts use begin_attack/tick_attack.
void pc_p2_kurage_arena_set_attack_frame(float frame);
bool pc_p2_kurage_arena_attack_pose_active();
