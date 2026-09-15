#pragma once
enum PcPikminStat { PC_PIKI_DAMAGE, PC_PIKI_MOVEMENT, PC_PIKI_ATTACK_RATE };
bool pc_randomizer_color_stats();
float pc_randomizer_color_multiplier(int color, PcPikminStat stat);
int pc_randomizer_carry_strength(int color);
// Standalone file-IPC adapter. No game state is touched before validation.
bool pc_randomizer_init(int argc, char** argv);
bool pc_randomizer_enabled();
void pc_randomizer_update();
bool pc_randomizer_ready();
bool pc_randomizer_has(const char* name);
bool pc_randomizer_checked(const char* name);
void pc_randomizer_check(const char* name);
bool pc_randomizer_goal();
int pc_randomizer_repairs();
const char* pc_randomizer_save_root();
// Repeat the last safe diary day; never index past vanilla's 30-entry arrays.
int pc_randomizer_next_day(int day);

// Expanded schema-2 gameplay observations. Receipts never trigger these checks.
bool pc_randomizer_expanded();
int pc_randomizer_start_stage();
int pc_randomizer_start_color();
bool pc_randomizer_enemy_shuffle();
int pc_randomizer_enemy_type(int original, bool protectedSpawn);
bool pc_randomizer_spawn_slots();
bool pc_randomizer_group_slots();
// P2 enemy bridge: versioned roster bindings parsed from ENEMY_P2. The target
// token comes from lane 04 placement; 0 means the target is not bound.
bool pc_randomizer_p2_bridge();
unsigned pc_randomizer_p2_source(const char* target);
unsigned pc_randomizer_p2_binding_count();
bool pc_randomizer_p2_bound(unsigned source_id);
// Resolve a bound generator's spawn-slot uid (as returned by
// pc_randomizer_generator_id) to its ENEMY_P2 source id. 0 means the target is
// not bound. The ordinary spawn path keys its seed bindings on the spawn-slot
// uid, not Generator::_70.
unsigned pc_randomizer_p2_source_for_id(unsigned long generator_id);
unsigned pc_randomizer_generator_id(const void* generator);
void pc_randomizer_set_generator_id(const void* generator, unsigned uid);
// `sourceId70` is the generator's on-file id (Generator::_70); it is consulted
// only for the P2 enemy bridge when the (stage,file,offset) spawn-slot catalogue
// misses, via lane 04's p2-placement-slots.txt sidecar.
void pc_randomizer_bind_generator(const void* generator, int stage, const char* file, int offset, unsigned sourceId70 = 0);
// Room-preview bridge: parse an ENEMY_P2 seed for the room without starting a
// full randomizer session (which would otherwise hold the preview). Returns
// true when an ENEMY_P2 line was found; the normal full-session path is unneeded.
bool pc_randomizer_p2_room_bootstrap(const char* path);
// Lane 06 runtime association: a live P2-bound Teki (passed as its PelletView) ->
// source_id + generator uid, captured at bind/spawn time because the Teki's
// mGenerator is already nulled by dieSoon() when the corpse reaches the Onion.
// Called by the family bind path (or a fixture); the source id installed must be
// in the bindable roster (an unbindable id is rejected and logged, not fatal).
// generatorUid is the stable Generator::_70 id that names the actor instance
// across revisits and restarts. The binding is single-use and is also cleared by
// pc_randomizer_p2_forget_source() from the central Teki lifetime seam, so a
// recycled actor address can never inherit a P2 binding or credit the P1 proxy.
void pc_randomizer_p2_bind_source(const void* tekiview, unsigned sourceId, unsigned generatorUid);
unsigned pc_randomizer_p2_source_for(const void* tekiview);
unsigned pc_randomizer_p2_generator_for(const void* tekiview);
void pc_randomizer_p2_forget_source(const void* tekiview);
// Close and clear the process-wide ordinary delivery ledger (once-per-process
// handle), so the next stage/session reopens it fresh. Called from the central
// stage-boundary reset seam (pc_p2_reset_all_teki).
void pc_randomizer_p2_delivery_reset();
// Ordinary Onion/AP delivery of a P2 corpse: resolves the bound source and grants
// it exactly once through the durable ordinary receipt host (p1Proxy=false).
// Returns true when a bound P2 delivery was handled; callers use the return value
// so a bound P2 corpse is never ALSO credited to the P1-proxy bestiary check.
bool pc_randomizer_p2_corpse_delivered(const void* tekiview, int type, int stage, bool gameplay);
int pc_randomizer_enemy_for_generator(int original, bool protectedSpawn, const void* generator);
// Generated spawn connection: the P2 source identity bound to a live generator's
// placement target (0 when the generator is unbound). Ordinary generated targets
// resolve through the same slot uid the P1 slot layouts use.
unsigned pc_randomizer_p2_bound_source(const void* generator);
// Fail closed when a bound identity has no reviewed native actor host.
void pc_randomizer_bad_p2_host();
void pc_randomizer_bad_spawn_cache();
int pc_randomizer_field_capacity();
void pc_randomizer_observe_population(int activePikmin, bool gameplay);
bool pc_randomizer_collection_checks();
enum PcBenefit { PC_BENEFIT_DELIVERY, PC_BENEFIT_FLOWERS, PC_BENEFIT_HEAL, PC_BENEFIT_WHISTLE, PC_BENEFIT_PLUCK, PC_BENEFIT_BOMBS, PC_BENEFIT_BOMB_TRAP, PC_BENEFIT_PROGG, PC_BENEFIT_PRERELEASE };
bool pc_randomizer_benefit_pending(PcBenefit kind);
bool pc_randomizer_progg_traps();
bool pc_randomizer_prerelease_traps();
bool pc_randomizer_consume_benefit(PcBenefit kind);
float pc_randomizer_benefit_multiplier(PcBenefit kind);
float pc_randomizer_captain_movement_multiplier();
void pc_randomizer_observe_color_population(int color, int totalPikmin, bool gameplay);
void pc_randomizer_observe_total_population(int totalPikmin, bool gameplay);
void pc_randomizer_corpse_delivered(int type, int stage, bool gameplay);
void pc_randomizer_enemy_defeated(int type, int stage, bool healthDepleted, bool gameplay);
void pc_randomizer_observe_exploration(int stage, float dx, float dz, bool grounded, bool gameplay);

void pc_randomizer_validate_part_weight(int part, int minimum);

void pc_randomizer_observe_obstacle(int stage, int kind, float x, float z, bool complete, bool gameplay);

bool pc_randomizer_resumed();
bool pc_randomizer_load_campaign(void* destination);
void pc_randomizer_save_campaign(const void* source);

bool pc_randomizer_emperor_available();
void pc_randomizer_emperor_defeated();

// DeathLink. Casualties are how many living field Pikmin a pending link should
// take (0 when nothing is pending); mark each induced Pikmin before killing it,
// then consume the link once. Ordinary deaths are journaled for the runner.
int pc_randomizer_deathlink_casualties();
void pc_randomizer_deathlink_induce(const void* piki);
void pc_randomizer_deathlink_consume(int killed);
void pc_randomizer_observe_pikmin_death(const void* piki);
