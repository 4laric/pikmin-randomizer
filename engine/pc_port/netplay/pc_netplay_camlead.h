#pragma once
// Netplay M5c lane A (issue #887): the instant ("lead") camera.
//
// In a lockstep session the presentation pass renders the local captain's
// camera with the local camera controls applied on the frame they are
// sampled, instead of `delay` + 1 frames later when the synced input reaches
// the sim camera. Design and maths: pc_netplay_camlead_core.h.
//
// Contract:
//   - presentation only: the lead camera is a separate Camera object that
//     only the presentation pass renders with (and the local input sampler
//     reads its yaw from, see pc_netplay_camlead_control_camera). The sim
//     camera objects are byte-for-byte what they would be without the lead:
//     the prediction runs on a snapshot of the sim camera and restores it,
//     with the camera sounds muted, and gfx.mCamera is put back to the sim
//     camera at the end of the presentation pass;
//   - netplay only: every entry point is inert until the lockstep session
//     calls pc_netplay_camlead_session_begin, which only netplay builds do;
//   - opt-out: PIKMIN_NETPLAY_CAMERA_LEAD=0 renders the sim camera, exactly
//     as before, and the yaw sampler reads that sim camera;
//   - joiner fixes, session-wide (lead on or off) unless
//     PIKMIN_NETPLAY_JOINER_OWN_CAMERA=0: this peer's own pad samples the
//     camera this peer presents for its own captain (the joiner used to
//     sample P1's camera), and every local free-camera drag turns this
//     peer's own captain's camera (the joiner's used to turn P1's). Both
//     switches at 0 give exactly the pre-M5c live input stream.
// Diagnostics: PIKMIN_NETPLAY_CAMERA_TRACE=1 logs one `[netplay] camlead`
// line per presented frame; PIKMIN_NETPLAY_CAMERA_SHOT=<dir>:<f1>,<f2>,...
// writes the presented frame at those GekkoNet frames as BMP files;
// PIKMIN_NETPLAY_TEST_CAMERA_DRAG=<frame>:<amount>,... adds a mouse
// free-camera drag (pc_window_add_camera_drag) before those frames' ticks;
// PIKMIN_NETPLAY_TEST_CAMLEAD_KEY_SKEW=<n> (negative control, issue #965)
// files every noted local input n frames off its landing frame, so the
// summary's key_mismatch must go non-zero. Presentation-only (not in the
// config hash); logged once at session start when set.

#include "netplay/pc_netplay_gekko_input.h"

#include <cstdint>

// ---- Session side (pc_netplay_session.cpp, netplay builds) ----
// Session configured: arms the lead for `localRole` (0 host/P1, 1
// joiner/P2) unless PIKMIN_NETPLAY_CAMERA_LEAD=0. Logs one line.
void pc_netplay_camlead_session_begin(int localRole);
// Session stopped: logs the summary line and disarms everything.
void pc_netplay_camlead_session_end(void);
// A local input was submitted for GekkoNet frame `frame` (submit + delay).
void pc_netplay_camlead_note_local_input(uint64_t frame, const PcNetplayInput& in);
// The Advance of GekkoNet frame `frame` carries this peer's input `wire`
// (16 bytes): if a local input was noted for `frame`, it must encode to
// the same bytes, else `key_mismatch` counts it (integration check that
// every submit path notes the frame its input lands on). Presentation-only.
void pc_netplay_camlead_check_applied(uint64_t frame, const uint8_t* wire);
// The Advance of GekkoNet frame `frame` is about to run its tick.
void pc_netplay_camlead_begin_frame(uint64_t frame);
// True while the session has the lead armed (env on).
bool pc_netplay_camlead_armed(void);

#if defined(PIKI_PC_PORT) && defined(__cplusplus)
class Camera;
class Graphics;
class PcamCamera;
class PcamCameraManager;

// ---- Engine side ----
// Presentation pass, det single view: `simView` is the local captain's sim
// camera, already updated for this frame's aspect. Returns the camera to
// render with: the lead camera while a correction is active, else simView.
Camera* pc_netplay_camlead_view(int localPlayer, Camera* simView);
// End of the presentation pass: puts gfx.mCamera back to the sim camera,
// logs the trace line, and drops the correction when no view was presented.
void pc_netplay_camlead_end_presentation(Graphics& gfx);
// Local control-yaw sampler (navi.cpp): the camera whose yaw pad `pad`
// submits. In a session, for this peer's own pad: the lead camera while it is
// presented, else this peer's own captain's sim camera. Otherwise `cam`
// (also for the joiner with PIKMIN_NETPLAY_JOINER_OWN_CAMERA=0).
Camera* pc_netplay_camlead_control_camera(int pad, Camera* cam);
// PcamCameraManager::update, right after the sim camera's own update and
// before its vibration events: records the posture the sim camera shows.
void pc_netplay_camlead_note_sim_update(PcamCameraManager* mgr);
// PcamCamera::makeCurrentPosition (every startCamera ends there): the sim
// camera was snapped, so a stale correction must not carry over.
void pc_netplay_camlead_note_snap(PcamCamera* cam);
// True while the lead runs its prediction on the sim camera: camera sounds
// are muted (they play when the sim applies the input).
bool pc_netplay_camlead_predicting(void);
// Free-camera drag routing (PcamCamera::control) for camera `cam`: -1 keeps
// the per-slot routing (no session, or PIKMIN_NETPLAY_JOINER_OWN_CAMERA=0);
// 1: `cam` is this peer's own captain's camera (the one its camera manager
// runs, whatever that camera targets) and takes every local drag; 0: it is
// the other captain's camera, never shown on this PC, and takes none.
int pc_netplay_camlead_drag_route(const PcamCamera* cam);
#endif
