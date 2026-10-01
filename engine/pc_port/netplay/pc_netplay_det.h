#pragma once

// Deterministic fixed-step mode switch for netplay M1 (issue #878).
//
// All behaviour here is opt-in: unless --netplay-deterministic is passed on
// the command line or PIKMIN_NETPLAY_DETERMINISTIC=1 is set, every function
// below is inert and the game behaves exactly as before.
//
// Interface contract (harness lane m1-harness calls this API; keep the fixed
// names and signatures stable):
//   pc_netplay_det_init      call once from main(), before the game starts
//   pc_netplay_deterministic true if --netplay-deterministic or env = 1
//   pc_netplay_unthrottled   det mode only: PIKMIN_NETPLAY_UNTHROTTLED=1
//   pc_netplay_tick          logical ticks executed so far (app->idle calls)
//   pc_netplay_on_tick_begin called by System::run right before app->idle()
//
// The additive helpers below (fixed_dt / reseed_for_new_day / profile_path)
// are M1-internal; they are not part of the harness contract.

void pc_netplay_det_init(int argc, char** argv); // call once from main(), before the game starts
bool pc_netplay_deterministic(void);            // true if --netplay-deterministic or PIKMIN_NETPLAY_DETERMINISTIC=1
bool pc_netplay_unthrottled(void);              // det mode only: PIKMIN_NETPLAY_UNTHROTTLED=1
unsigned pc_netplay_tick(void);                 // logical ticks executed so far (app->idle calls), in any mode
void pc_netplay_on_tick_begin(void);            // called by System::run right before app->idle()

// Netplay M3 (issue #880): force deterministic mode on at runtime. The
// netplay session calls this once when its switch is set; plain
// --netplay-deterministic / env parsing in pc_netplay_det_init is unchanged.
void pc_netplay_det_force_on(void);

// Logical tick period in seconds for a setFrameClamp value: 1/30 at clamp 2,
// 1/60 at clamp 1, 1/120 at clamp 0 (mirrors PcFrameScheduler::deltaForClamp).
float pc_netplay_fixed_dt(int frameClamp);

// Reseed both RNG streams for a new GameCoreSection (day). No-op unless
// deterministic mode is on. The seed is FNV-1a over PIKMIN_NETPLAY_SEED (u32
// env var, defaults to 0), the day index and the stage id; see the .cpp.
void pc_netplay_det_reseed_for_new_day(int dayIndex, int stageId);
// M5c lane C (issue #887): the day index of the last reseed (0 = none yet)
// and how many reseeds ran. Log/record only; the simulation never reads them.
int pc_netplay_det_last_reseed_day(void);
unsigned pc_netplay_det_reseed_count(void);

// PIKMIN_NETPLAY_PROFILE_LOG value, or nullptr when unset/empty. Cached.
const char* pc_netplay_det_profile_path(void);
// M3 fix (review M4): periodic world-sim / whole-tick cost report, every 600
// ticks when PIKMIN_NETPLAY_PROFILE_LOG is set. System::run calls this on
// the normal path; the lockstep session calls it per Advance so the netplay
// path reports too. No-op when the env gate is unset.
void pc_netplay_det_profile_note_tick(void);
