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
// Opt-in source flight-lifecycle authority (pc_p2_kurage_fsm.h). When enabled
// the host's vertical motion and state come from the FSM instead of the sine
// preview path, and the source Attack state autonomously drives the suction
// admission scan.
void pc_p2_kurage_arena_fsm_enable(bool enable);
bool pc_p2_kurage_arena_fsm_enabled();
int pc_p2_kurage_arena_fsm_state();
float pc_p2_kurage_arena_fsm_altitude();
// Host-side owner facts for the source bitter/zero-health pause gates.  The
// fixture owns the health model until a full Kurage health/bitter host lands.
void pc_p2_kurage_arena_set_owner_facts(bool hasHealth, bool bittered);
int pc_p2_kurage_arena_auto_admissions();
// Greater Spotted Jellyfloat (OniKurage, id 72).  Default is Lesser (Kurage,
// id 57).  The shared Fsm is reconstructed with the selected variant, which
// switches the pitch numerics and enables the OniKurage Drop state.
void pc_p2_kurage_arena_set_greater(bool greater);
int pc_p2_kurage_arena_fsm_variant();
// Captain-held facts for the OniKurage Drop route.  Real captain capture is
// lane 12 provider work; this is an explicitly labelled host seam until a
// Navi attachment exists.
void pc_p2_kurage_arena_set_captain_held(bool held);
// Lane-12 consumer path: compose the live captain with P2CaptainPolicy (lane 12
// #130) and the OniKurage mouth-slot policy.  The policy owns identity and
// ownership; this host owns the family-local capture/release and the bounded
// Navi attachment while held.
class P2CaptainPolicy;
class Navi;
void pc_p2_kurage_arena_set_captain_target(P2CaptainPolicy* policy, int captain, Navi* navi);
int pc_p2_kurage_arena_captain_occupied();
bool pc_p2_kurage_arena_captain_captured();
