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
int pc_randomizer_field_capacity();
void pc_randomizer_observe_population(int activePikmin, bool gameplay);
bool pc_randomizer_collection_checks();
void pc_randomizer_observe_total_population(int totalPikmin, bool gameplay);
void pc_randomizer_corpse_delivered(int type, int stage, bool gameplay);
void pc_randomizer_enemy_defeated(int type, int stage, bool healthDepleted, bool gameplay);
void pc_randomizer_observe_exploration(int stage, float dx, float dz, bool grounded, bool gameplay);

void pc_randomizer_validate_part_weight(int part, int minimum);

void pc_randomizer_observe_obstacle(int stage, int kind, float x, float z, bool complete, bool gameplay);
