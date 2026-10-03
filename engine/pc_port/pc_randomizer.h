#pragma once
#include "pc_p2_surface_session.h"
#include "pc_p2_original_calendar.h"

#include "netplay/pc_netplay_randstate.h"
#include <cstddef>
#include <cstdint>
struct P2CaveCacheBanks;
const P2CaveCacheBanks& pc_randomizer_generated_cave_cache();
void pc_randomizer_generated_cave_cache_set(const P2CaveCacheBanks& banks);

// Seed-owned generated cave transport; absent for every historical seed.
bool pc_randomizer_generated_cave();
bool pc_randomizer_generated_cave_matches(uint64_t seed, const char* cave, int floor,
    const char* item, const char* host, const char* slot, const char* boundaryToken);
bool pc_randomizer_generated_cave_collected(uint64_t seed, const char* cave, int floor,
    const char* item, const char* host, const char* slot, const char* boundaryToken);
void pc_randomizer_generated_cave_delivery(uint64_t seed, const char* cave, int floor,
    const char* item, const char* host, const char* slot, const char* boundaryToken);
int pc_randomizer_generated_cave_bud_used(uint64_t seed, const char* cave, int floor,
    const char* slot, const char* boundaryToken);
void pc_randomizer_generated_cave_bud_input(uint64_t seed, const char* cave, int floor,
    const char* slot, const char* boundaryToken, unsigned used);
enum PcPikminStat { PC_PIKI_DAMAGE, PC_PIKI_MOVEMENT, PC_PIKI_ATTACK_RATE };
bool pc_randomizer_color_stats();
float pc_randomizer_color_multiplier(int color, PcPikminStat stat);
int pc_randomizer_carry_strength(int color);
// Standalone file-IPC adapter. No game state is touched before validation.
bool pc_randomizer_init(int argc, char** argv);
// Explicit authenticated bootstrap selections; empty for historical sessions.
std::string pc_randomizer_original_campaign();
bool pc_randomizer_original_session();
// Nonallocating current immutable selection identity. Zero before successful
// authenticated initialization and for ordinary/AP sessions. This is neither
// a native scene serial nor a selected card generation/proof.
std::uint64_t pc_randomizer_original_selection_revision() noexcept;
// Exact role membership in the retained authenticated selection. False before
// successful OriginalSession initialization; does not read or authenticate
// current file bytes. A selected role MUST still use original_input, and a
// failed read must never be treated as an absent optional role.
bool pc_randomizer_original_has_input(const std::string& relativeRole) noexcept;
const char* pc_randomizer_original_catalog_root();
bool pc_randomizer_original_calendar_plan(const std::string& course,const p2original::CalendarState& actualCacheFlags,std::vector<p2original::CalendarLoad>& out,std::string& error);
std::string pc_randomizer_campaign_treasure_source();
// Stable selected immutable descriptor fingerprint; never a process token.
std::string pc_randomizer_session_fingerprint();
// Reverify an explicitly selected immutable input at each actual native read.
bool pc_randomizer_original_input(const std::string& relativeRole, std::string& bytes, std::string& error);
bool pc_randomizer_enabled();
// SAVE1229 supplies this verified ORIGINAL_P2_CAMPAIGN bootstrap boundary.
// Terrain, typed engineering fixtures and AP seeds do not enable it.
bool pc_randomizer_original_session();
// Separate, versioned TheLynk AP contract. Physical checks and rewards differ.
bool pc_randomizer_thelynk();
bool pc_randomizer_thelynk_part(unsigned model, bool received);
void pc_randomizer_thelynk_collect(unsigned model);
void pc_randomizer_thelynk_squad(int color, int followers, bool gameplay);
int pc_randomizer_thelynk_bonus(int kind);
void pc_randomizer_thelynk_consume(int kind);
void pc_randomizer_update();
// Netplay M4 lane A external-state stream (issue #885). The sim-side apply
// validates a received snapshot and applies exactly what pc_randomizer_update
// would have applied from state.txt (repairs, unlocks, flarlic, checks, stat
// tiers, benefits, emperor, deathLinks, ready). Monotonicity violations fail
// closed, exactly like the file path. Returns false when the randomizer is
// disabled (no-op); otherwise applies and returns true.
bool pc_randomizer_apply_net_state(const pc_randstate::PcRandState& st);
// Fills the sim-visible payload of the current randomizer state (gen left 0;
// the caller stamps it). Returns false when disabled.
bool pc_randomizer_get_net_state(pc_randstate::PcRandState* out);
// Fix round 1 (M5): re-read state.txt on session activation and publish when
// the content is new or nothing was ever published. Host + stream only;
// no-op otherwise (client never reads the file after boot).
// M4 lane B1: returns false only on the stream host when this forced poll
// could not read and parse state.txt (the session then HOLDs from its first
// input); true otherwise. Also reads the runner's session.json ledger.
bool pc_randomizer_force_net_publish();
// ---- Netplay M4 lane B1 (issue #885) ----
// Confirmed-frame outbox flush: the host writes the queued external writes
// (checks.txt, benefits-used.txt, emperor.txt, deaths.txt, the P2 delivery
// ledger) with their historical format and durability; the client writes
// mirror-events.txt lines instead. Called once per Advance by the session
// and by the B2 save barrier before it writes. No-op outside outbox mode.
void pc_randomizer_outbox_flush(uint32_t frame);
// Host I/O side link liveness for the synchronized HOLD: state.txt readable,
// parsed, ready=1 and rewritten within 3 s. Always true in launcher sessions
// and when the randomizer is disabled.
bool pc_randomizer_link_live();
// Host RESUME snapshot: fresh state.txt read with a new generation. False
// when state.txt cannot be read right now (retry later).
bool pc_randomizer_resume_snapshot(pc_randstate::PcRandState* out);
// Client: one kBulkMirrorLedger payload (RECEIVED lines, deathsBase).
void pc_randomizer_mirror_ledger_receive(const uint8_t* data, size_t len, uint32_t frame);
// B2 writer API for the client mirror (no-op on the host / outside netplay).
// shaHex is the lowercase hex SHA-256 of the checkpoint (64 characters).
void pc_randomizer_mirror_save_result(uint32_t frame, unsigned long long gen, const char* shaHex);
void pc_randomizer_mirror_save_fail(uint32_t frame, unsigned long long gen);
#if PIKI_NETPLAY_BUILD
// TEST-ONLY (netplay builds): PIKMIN_NETPLAY_TEST_DEATHLINK_AS_ORDINARY=1.
bool pc_randomizer_test_deathlink_as_ordinary();
#endif
// Canonical 64-bit hash of the sim-visible randomizer state for the M1 state
// hash `rand` column. 0 when disabled.
uint64_t pc_randomizer_hash();
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
bool pc_randomizer_p2_proxy_tier();
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
// Dev console (#942): register a runtime generator under a synthetic dev
// target uid that is not in the spawn-slot catalogue. Only the dev console
// calls this; the seed's ENEMY_P2 line must already bind the uid.
void pc_randomizer_dev_set_generator_id(const void* generator, unsigned uid);
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
bool pc_randomizer_resolved_checks();
bool pc_randomizer_p2_corpse_delivered(const void* tekiview, int type, int stage, bool gameplay);
// Kill-based receipt for a bound P2 source that leaves no carcass (#1088: the
// source species never leaves a corpse, so its check is earned at the kill).
// Same resolved check, same `onion:p2:<source>:<stage>` identity and the same
// single-use binding as the corpse delivery (whichever runs first consumes it),
// so one actor earns its check exactly once. Ledger encounter "kill".
bool pc_randomizer_p2_killed(const void* tekiview, int type, int stage, bool gameplay);
// Read-only receipt query for the TEST-ONLY autoplay bot (bot-v2 gap 1):
// true once this process granted (or saw a durable duplicate of) the Onion
// corpse receipt for `generatorUid`. Never mutates the ledger.
bool pc_randomizer_p2_receipt_seen(unsigned generatorUid);
int pc_randomizer_enemy_for_generator(int original, bool protectedSpawn, const void* generator);
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
// Received maturity tier (0 leaf, 1 bud, 2 flower) for a native color: blue 0, red 1, yellow 2.
int pc_randomizer_maturity(int color);
// Playable day length scale from Progressive Day Length items; 1.0 when disabled.
float pc_randomizer_day_length_multiplier();
// Whistle Pluck item: -1 when the seed does not carry it (the Mods setting
// decides), otherwise 1 once received and 0 before.
int pc_randomizer_whistle_pluck();
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
// Netplay M4 lane B2 (issue #885). The day-end save barrier: active only in
// a netplay session with the external-state stream on; then memoryCard.cpp
// calls pc_randomizer_save_campaign_netplay (flush, local checkpoint, bulk
// SAVE_RESULT exchange) and uses its return value, the host's outcome, as
// !mDidSaveFail on both peers.
bool pc_randomizer_netplay_save_barrier_active();
bool pc_randomizer_save_campaign_netplay(const void* source, bool localCardOk);
// B2 fix round 1: after the agreed save, memoryCard.cpp reports a rewrite of
// this peer's game file (C12; false ends the session, exit 5) and the local
// options write (C3; logged, never sim-visible). The session calls
// pc_randomizer_netplay_barrier_abandoned just before a barrier exit 5/6
// (C2: the client retracts its unconfirmed checkpoint), and the netplay
// day reseed calls pc_randomizer_netplay_stage_start (C5: a resumed
// session's START_STAGE line).
void pc_randomizer_netplay_card_rewrite_result(bool ok);
void pc_randomizer_netplay_options_result(bool ok);
void pc_randomizer_netplay_barrier_abandoned();
void pc_randomizer_netplay_stage_start(int day, int stage);
// True in a netplay session with the external-state stream on (the outbox
// mode), i.e. whenever save outcomes are agreed rather than local. Unlike
// pc_randomizer_netplay_save_barrier_active it does not reference the
// session's barrier symbol, so card code reachable from engine-only targets
// can call it (fix round 1, C3: MemoryCard::didSaveFail).
bool pc_randomizer_netplay_agreed_saves();
// Newest valid checkpoint (loadCampaignCheckpoint rules) and the SHA-256 of
// its file; gen 0 and zeros = none. False when the randomizer is disabled.
bool pc_randomizer_checkpoint_info(uint64_t* gen, uint8_t sha[32]);
// Absolute derived campaign directory ("" when disabled).
const char* pc_randomizer_campaign_dir();
// Joiner: re-reads the campaign directory after the transfer phase wrote the
// host's files (same rules as a boot). True when a checkpoint is resumed.
bool pc_randomizer_adopt_checkpoint();

bool pc_randomizer_emperor_available();
void pc_randomizer_emperor_defeated();

// DeathLink. Casualties are how many living field Pikmin a pending link should
// take (0 when nothing is pending); mark each induced Pikmin before killing it,
// then consume the link once. Ordinary deaths are journaled for the runner.
int pc_randomizer_deathlink_casualties();
void pc_randomizer_deathlink_induce(const void* piki);
void pc_randomizer_deathlink_consume(int killed);
void pc_randomizer_observe_pikmin_death(const void* piki);

// Explicit ordinary-campaign Purple mode; no implicit preview/asset enable.
bool pc_randomizer_purple_campaign();
bool pc_randomizer_white_campaign();
bool pc_randomizer_white_treasure_campaign();
// Fingerprint-bound campaign choice; absent on legacy seeds means one captain.
bool pc_randomizer_second_captain();

const P2SurfaceSession& pc_randomizer_surface_session();
void pc_randomizer_surface_session_set(const P2SurfaceSession&);
std::uint64_t pc_randomizer_active_campaign_generation();
