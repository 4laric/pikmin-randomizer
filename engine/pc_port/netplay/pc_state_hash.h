#pragma once
// Curated per-tick simulation hash for the netplay determinism harness
// (issue #878). Every later netplay milestone uses this to prove, or
// disprove, that the game is deterministic.
//
// Log format (PIKMIN_STATE_HASH_LOG=<file>): after every tick, one text line:
//   <tick> <total> <navi> <piki> <teki> <item> <world> <rng> <rand>
// <tick> is the 1-based tick count in decimal; every other column is a 64-bit
// hash printed as 16 lowercase hex digits.
//
// Exactly what is hashed (stable simulation data only, never pointers):
//   navi:  per Navi in manager order: mNaviID; position (mSRT.t xyz),
//     rotation (mSRT.r xyz), velocity (mVelocity xyz), drive
//     (mTargetVelocity xyz) as float bits; mFaceDirection bits; mHealth
//     bits; current state id (mCurrState->getID(), -1 when null).
//   piki:  per Piki in manager order: mColor, mHappa, P2 species flags
//     (purple/white/bulbmin); position, rotation, velocity, drive bits;
//     mFaceDirection bits; mHealth bits; current state id (-1 when null).
//   teki:  per Teki in manager order: mTekiType; position, rotation,
//     velocity, drive bits; mFaceDirection bits; mHealth bits; mStateID.
//   item:  per itemMgr object in manager order: mObjType; position,
//     rotation, velocity, drive bits; mFaceDirection bits; GoalItem extras
//     (mObjType == OBJTYPE_Goal, via static_cast, never dynamic_cast):
//     mOnionColour and mHeldPikis[3]; then per pelletMgr Pellet in order:
//     config pellet id + pellet type (0 when no config), position,
//     rotation, velocity bits, mFaceDirection bits, current state id
//     (getCurrState()->getID(), -1 when null), legacy getState(), carrier
//     count; then per bossMgr Boss in order: current/next state id,
//     current life bits, position, rotation, velocity bits,
//     mFaceDirection bits. Onion/container counts per colour are covered
//     twice on purpose: once via the GoalItem objects above, once via
//     itemMgr->getContainer(c) for each Piki colour (0 when that colour
//     has no Onion).
//   world: gameflow.mWorldClock.mTimeOfDay bits and mCurrentDay, plus
//     playerState counters (living/born/dead/plucked, 0 when null).
//   rng:   pc_sim_rng_state() when the m1-det lane's weak symbol resolves,
//     else 0. (Wall-clock rand() is NOT hashed; it is expected to diverge
//     until the det lane lands.)
//   rand:  pc_randomizer_hash() when the M4a lane's weak symbol resolves
//     (the sim-visible randomizer POD: ready, repairs, unlocks, flarlic,
//     emperor, DeathLinks, checks, stat tiers, benefit receipts/consumption),
//     else 0. With the netplay stream both peers apply snapshots at the
//     same tick, so this column stays identical; with the stream disabled
//     and divergent state.txt schedules it is the first column to differ.
//     Gapfix C (issue #885): while co-op is active (pc_coop_active() and
//     the co-op randomizer branch has run), the co-op policy's sim state
//     (pc_coop_policy_state_hash: reset key, tick, round-robin cursors, HP
//     samples, and the bomb trap / Progg / nectar cooldowns) is mixed in
//     as one more u64 after pc_randomizer_hash(). Single-captain play
//     mixes nothing, so its column is byte-identical to before.
//   total: FNV-1a 64 over the seven sub-hashes in the order above.
// A null manager (title screen, loading) contributes a sub-hash of 0: each
// sub-hash returns literal 0 (not the FNV offset) when its managers are
// absent. Additionally, naviMgr == nullptr is treated as "no live stage":
// exitStage reliably nulls naviMgr while pikiMgr/itemMgr/pelletMgr may
// still point at the released stage, so when naviMgr is null the navi,
// piki, teki and item sub-hashes are all 0 instead of walking stale
// objects.
// Mixing uses FNV-1a 64 throughout.
//
// Runtime behaviour:
//   PIKMIN_STATE_HASH_LOG=<file>: write one line per tick (buffered; the
//     buffer is flushed every 300 ticks and on exit).
//   PIKMIN_NETPLAY_EXIT_AFTER_TICKS=<n>: after tick n is hashed, flush every
//     log, push an SDL_QUIT event so the main loop breaks and the process
//     returns through the normal "[PC Port] Game exited normally." path,
//     and stop hashing further ticks. If the loop has not exited within a
//     few more ticks, exit directly with code 0 as a fallback (flushing
//     again first).
//   PIKMIN_NETPLAY_TEST_PREROLL_RAND=<n>: before the first tick, call rand()
//     n times, and pc_sim_rand() n times when the weak symbol resolves.
//   With none of these set, pc_state_hash_tick_end() returns immediately:
//     no managers are walked, no hashes are computed, no files are opened,
//     no log lines are printed, the RNG sequence is unchanged. (The tick
//     counter is not bumped either; nothing consumes it on this path.)

#include <cstdint>

// argv capture must happen before the first tick (pc_main calls it at
// startup); env vars are read lazily on the first tick end.
void pc_state_hash_notify_argv(int argc, char** argv);

// Menu-dwell simulation: call once, before the first tick's simulation.
// Called by pc_input_log_tick(); do not call directly.
void pc_state_hash_before_first_tick(void);

// Per-tick hook: call after app->idle() returns.
void pc_state_hash_tick_end(void);

// Flush the hash log, if any.
void pc_state_hash_flush(void);

// Current 1-based tick count (0 before the first tick end).
uint64_t pc_state_hash_tick(void);

// Netplay M3 lockstep (issue #880): Save-event checksums and desync dumps.
// pc_state_hash_set_netplay_capture(true) makes pc_state_hash_tick_end()
// compute and remember the sub-hashes every tick even when no hash log file
// is open (the switch-off path is untouched: with capture off and no log,
// tick_end still returns before walking any manager).
// pc_state_hash_current() returns the last computed total, the seven
// sub-hashes (navi, piki, teki, item, world, rng, rand) and the tick that
// produced them; false when nothing has been computed yet.
void pc_state_hash_set_netplay_capture(bool on);
bool pc_state_hash_current(uint64_t* total, uint64_t subs[7], uint64_t* tick);
