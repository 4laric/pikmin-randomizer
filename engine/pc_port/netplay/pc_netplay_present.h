#pragma once

// Netplay M2b two-pass frame: authoritative sim pass + local presentation pass
// (issue #879).
//
// All behaviour is opt-in: unless deterministic mode is on
// (pc_netplay_deterministic()), every helper below is inert and the game
// behaves exactly as before.
//
// Pass driver (see PlugPikiApp::idle):
//   - det mode: authoritative pass (SimCamera + null GX, sim blocks run) then
//     presentation pass (real camera + real GL, sim blocks skipped) in one
//     logical tick.
//   - non-det: single pass, exactly as today.
//   - pc_netplay_present_set_skip_presentation(true) runs authoritative only,
//     for future rollback resimulation (m3 lane hook).

#if defined(PIKI_PC_PORT) && !defined(PC_NETPLAY_PRESENT_HOST)
class Camera;
class Graphics;
class Matrix4f;
#endif

#ifdef __cplusplus
extern "C" {
#endif

// Future rollback hook: when true, det ticks run the authoritative pass only.
void pc_netplay_present_set_skip_presentation(int skip);
int pc_netplay_present_skip_presentation(void);

// True when the two-pass frame is active this tick (det mode, engine up).
// Safe to call from engine code (returns 0 when the switch is off).
int pc_netplay_present_two_pass_active(void);

// True when this pass may write sim state: single-pass mode, or the
// authoritative pass of a two-pass tick. The presentation pass must only
// read sim state and write view state. (Engine-free: host builds only ever
// run single-pass, so this is 1 there unless det+presentation were entered,
// which host code cannot do.)
int pc_netplay_present_sim_side(void);

// True only inside the authoritative pass of a two-pass tick: the SimCamera
// is installed and the null-GX flag is on. Replaces ad-hoc null-flag reads
// as the "am I in the sim pass" signal.
int pc_netplay_present_sim_pass(void);

// Null-GX backend flag (authoritative pass): GL-issuing submission is
// skipped. Counts attempts (skipped calls) and real GL issued while active.
// All GL in this architecture goes through pc_gfx.cpp (the GX stubs are
// CPU-side shims; OGLGraphics is not instantiated -- System builds a
// DGXGraphics), and every raw GL call in that TU expands through a counting
// macro (or the cached-uniform wrappers) into pc_gfx_count_real_gl(), so the
// real-GL counter is a live measurement at a single choke point, not true by
// construction. Steady-state replays must show null_gl 0. Uploads happen in
// presentation, never in the authoritative pass: display lists are skipped at
// entry (the presentation pass parses/uploads/caches on first draw) and
// texture inits return before any GL without recording signatures.
void pc_netplay_present_set_null_gx(int on);
int pc_netplay_present_null_active(void);
// GL calls issued while null was active (acceptance: 0 in auth passes).
unsigned long long pc_netplay_present_null_gl_calls(void);
// Submissions/uploads/presents skipped while null was active (diagnostic).
unsigned long long pc_netplay_present_null_attempted(void);
void pc_netplay_present_note_attempt(void);
void pc_netplay_present_note_real(void);
void pc_netplay_present_reset_counters(void);

// Local player's view: PIKMIN_NETPLAY_LOCAL_PLAYER=0|1, default 0. Cached;
// reset the cache (tests only).
int pc_netplay_present_local_player(void);
void pc_netplay_present_reset_local_player(void);
// Netplay role default (host = 0, joiner = 1), set by the session before the
// first stage. An explicit PIKMIN_NETPLAY_LOCAL_PLAYER still wins.
void pc_netplay_present_set_local_player_default(int player);

// Presentation matrix save/restore accounting (diagnostic).
unsigned long long pc_netplay_present_saved_shapes(void);

#ifdef __cplusplus
}
#endif

#if defined(PIKI_PC_PORT) && !defined(PC_NETPLAY_PRESENT_HOST) && defined(__cplusplus)
// Engine side (defined in pc_netplay_present.cpp, uses Camera/Graphics).
// SimCamera: identity lookAt/inverse (world-space pose) with a fixed
// session-constant projection (16:9, default gameplay FOV/clip). It never
// reads the live camera: FOV/near follow zoom and first-person state, so a
// copy would differ between peers and between LOCAL_PLAYER 0/1.
Camera* pc_netplay_present_sim_camera(void);
void pc_netplay_present_begin_authoritative(Graphics& gfx);
void pc_netplay_present_end_authoritative(Graphics& gfx);
void pc_netplay_present_begin_presentation(Graphics& gfx);
void pc_netplay_present_end_presentation(Graphics& gfx);
// Called from BaseShape::updateAnim in the presentation pass: records the
// sim pointer once per shape per presentation pass so end_presentation can
// restore it. Returns true if the shape was newly saved.
bool pc_netplay_present_save_shape_ptr(void* shape, void* savedPtr);
// Internal iteration for shapeBase.cpp restore (engine only).
size_t pc_netplay_present_saved_count(void);
void* pc_netplay_present_saved_shape_at(size_t i, void** outSaved);
void pc_netplay_present_clear_saved(void);
// Restores BaseShape::mAnimMatrices for every shape saved this presentation
// pass (defined in shapeBase.cpp).
void pc_netplay_present_restore_all_shapes(void);
#endif
