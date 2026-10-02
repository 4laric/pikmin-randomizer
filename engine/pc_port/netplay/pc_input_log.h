#pragma once
// Input record/replay for the netplay determinism harness (issues #878, #879).
//
// File format (little-endian binary, "PKNI" v1/v2):
//   offset  size  field
//   0       4     magic: 'P' 'K' 'N' 'I' (0x50, 0x4B, 0x4E, 0x49)
//   4       2     version: u16, 1 or 2
//   6       2     pad count: u16, currently 4
//   8       2     record size: u16, bytes per tick (44 for v1, 56 for v2)
//   10      N*rec tick records, one per tick, tick index = file order
//
// Each v1 tick record holds the 4 pads in channel order, 11 bytes each
// (the M1 PADStatus fields). Each v2 tick record holds the 4 pads in
// channel order, 14 bytes each: the same 11 PADStatus bytes followed by
//   11      2     controlYaw: u16 LE, camera control yaw in 1/65536 turns
//   13      1     flags: u8, reserved, always 0
// every field serialised explicitly (never a raw struct memcpy, so the file
// is stable across compilers and struct layouts).
//
// Control yaw (issue #879): in netplay deterministic mode the camera yaw
// each player saw when they pushed the stick is part of that player's
// per-tick input. Quantisation is u16 in 1/65536 turns:
//   yaw = round(wrap(angle / 2pi) * 65536) & 0xFFFF
//   angle = yaw * 2pi / 65536   (0 .. 2pi, congruent mod 2pi)
// One LSB is ~0.0055 degrees, far below stick noise, while 16 bits keep
// the packet small (report section 2d budgets u16 yaw + u8 flags). The sim
// reconstructs sin/cos with the same sinf/cosf the rest of the engine uses
// (Matrix4f::makeRotate(angle) is sinf/cosf internally), so lane m2d can
// swap in a deterministic libm at that one point. The basis is always
// built from the quantised value, never from the live float, so record
// and replay compute bit-identical values.
//
// Flags byte: reserved, always 0. Side channels that are pure buttons
// (lock-on / charge edges) are neutralised in det mode rather than carried
// here; see the lockout table in the m2c handoff.
//
// Runtime behaviour:
//   PIKMIN_INPUT_RECORD=<file> (or --input-record <file>): before each tick's
//     simulation, append the 4 PADStatus records plus yaw/flags. Always
//     writes v2. The yaw is the pre-sim captured value (live camera,
//     quantised), so the file holds exactly what the sim will use.
//   PIKMIN_INPUT_REPLAY=<file> (or --input-replay <file>): on each tick,
//     overwrite the 4 pads with the recorded values for that tick index,
//     and feed the recorded yaw to the sim (v2) or capture the live camera
//     pre-sim (v1, as today). This happens after PADRead, so replay bypasses
//     local window-focus gating on purpose. Past the end of the file,
//     neutral pads are fed (all zeros; err kept connected (0) for pad 0,
//     no-controller (-1) for pads 1-3) and the yaw is the pre-sim live
//     capture. A replay that was explicitly requested but cannot be loaded
//     (missing file, truncated header, bad magic, unsupported version)
//     prints an error and exits the process with code 3, so a harness run
//     can never mistake an unreplayed session for a replay.
//   Record and replay may be combined: the record is written before the
//     tick's simulation from the replayed pads and the yaw the sim will use,
//     so recording a replayed v2 run reproduces the replay file byte-for-
//     byte. The replay is fully loaded into memory before the record file is
//     opened, so record and replay may name the same path for an identity
//     check.
//   Coverage is PADStatus plus yaw/flags: scripted overrides that take
//     precedence in ControllerMgr::updateController (pc_p2_input_script_
//     override and the autoplay bot that feeds it), mouse/cursor, window-
//     focus gating and edges derived elsewhere are NOT recorded or
//     replayed, except through the det-mode lockout (neutral). A fixture's
//     script override silently defeats a replay; keep it unset for
//     determinism runs.
//   With neither switch set, pc_input_log_tick() and pc_input_log_tick_end()
//     touch no files, print no log lines and leave the RNG sequence unchanged.
//     The per-tick yaw slots are still cleared every tick and the (possibly
//     null) capture hook still runs, so det mode without a record or replay
//     file gets a fresh yaw every tick instead of a stale one.
//
//   Only det-mode records replay bit-exactly. A non-det record still carries
//     the quantised yaw, but the sim used the unquantised camera angle that
//     tick, so replaying it in det mode can differ by up to half an LSB.
//
// Tick split: pc_input_log_tick() runs before the sim (after PADRead); it
// clears the yaw slots, loads the replay pads, runs the capture hook (which
// fills live yaw for slots without a replayed value), and performs the
// record write, so the recorded yaw is the quantised value the sim will use.
// pc_input_log_tick_end() runs after the sim and only advances the tick
// index (plus periodic flush).
//
// Yaw capture hook: engine code (Navi) registers a function that reads each
// local player's control camera pre-sim and stores the quantised yaw via
// pc_input_log_yaw_set. Slots already filled from a v2 replay are left
// alone. pc_input_log_tick calls the hook whenever it is set, including on
// ticks with no record or replay active, so det mode always starts the sim
// with fresh yaw. Register once during static init, before the first tick.

// Netplay M3 (issue #880): run the registered pre-sim capture hook now,
// without any record/replay logic. The lockstep session calls this after
// sampling the local pad so the submitted input carries the yaw the sim
// will use. No-op when no hook is registered.
void pc_input_log_capture_yaw(void);
// Netplay M3 fix (review B1): like capture_yaw, but clears sYawValid[0..3]
// first so the hook refills the local slot from the live camera. The plain
// capture skips slots already marked valid (replay hits), and the lockstep
// inject path marks slots 0/1 valid on every Advance, so without the clear
// the local yaw would freeze at the first injected value.
void pc_input_log_capture_yaw_fresh(void);

#include <cstddef>
#include <cstdint>
#include <vector>

struct PcInputPad {
	uint16_t button;
	int8_t stickX;
	int8_t stickY;
	int8_t substickX;
	int8_t substickY;
	uint8_t triggerLeft;
	uint8_t triggerRight;
	uint8_t analogA;
	uint8_t analogB;
	int8_t err;
	// v2 only; zero for v1 decodes.
	uint16_t controlYaw;
	uint8_t flags;
};

namespace pc_input_log {
constexpr uint8_t kMagic[4]       = { 'P', 'K', 'N', 'I' };
constexpr uint16_t kVersion       = 2;
constexpr uint16_t kPadCount      = 4;
constexpr size_t kPadBytes        = 14;
constexpr size_t kRecordBytes     = kPadCount * kPadBytes; // 56
constexpr size_t kHeaderBytes     = 10;
constexpr int8_t kErrConnected    = 0;
constexpr int8_t kErrNoController = -1;
// v1 compat (M1 files).
constexpr uint16_t kVersionV1     = 1;
constexpr size_t kPadBytesV1      = 11;
constexpr size_t kRecordBytesV1   = kPadCount * kPadBytesV1; // 44
// Yaw: 1/65536 turns per LSB.
constexpr float kYawTurnsToRad = 6.28318530717958647692f / 65536.0f;
// Flags: reserved, always zero.
constexpr uint8_t kFlagsNone = 0;
} // namespace pc_input_log

// Pure encode/decode API, v2 (no globals, no files; host-testable).
// Encodes 4 pads into exactly 56 bytes. Returns bytes written (56).
size_t pc_input_log_encode_tick(const PcInputPad pads[4], uint8_t out[56]);

// Decodes 4 pads from the first 56 bytes. Returns false when avail < 56.
bool pc_input_log_decode_tick(const uint8_t* data, size_t avail, PcInputPad pads[4]);

// v1 compat: 44-byte records; encode ignores controlYaw/flags, decode sets
// controlYaw = 0, flags = 0.
size_t pc_input_log_encode_tick_v1(const PcInputPad pads[4], uint8_t out[44]);
bool pc_input_log_decode_tick_v1(const uint8_t* data, size_t avail, PcInputPad pads[4]);

// Appends the 10-byte header to out (v2; use version/worker for v1).
void pc_input_log_write_header(std::vector<uint8_t>& out);
void pc_input_log_write_header_v1(std::vector<uint8_t>& out);

enum PcInputHeaderResult {
	PC_INPUT_HEADER_OK          = 0,
	PC_INPUT_HEADER_TRUNCATED   = 1,
	PC_INPUT_HEADER_BAD_MAGIC   = 2,
	PC_INPUT_HEADER_UNSUPPORTED = 3, // version, pad count or record size mismatch
};

// Validates the 10-byte header at data. Accepts v1 (1/4/44) and v2
// (2/4/56); version/padCount/recordSize are set only on
// PC_INPUT_HEADER_OK.
PcInputHeaderResult pc_input_log_read_header(const uint8_t* data, size_t len, uint16_t& version,
                                             uint16_t& padCount, uint16_t& recordSize);

// Yaw helpers (pure, host-testable). Uses the same sinf/cosf the engine's
// Matrix4f::makeRotate(angle) uses, so a deterministic libm swap covers
// both at once (lane m2d).
uint16_t pc_input_log_yaw_quantise(float angleRad);
float pc_input_log_yaw_to_angle(uint16_t yaw);
void pc_input_log_yaw_sincos(uint16_t yaw, float* sinYaw, float* cosYaw);

// Runtime API (engine). argv capture must happen before the first tick
// (pc_main calls it at startup); env vars are read lazily on the first tick.
void pc_input_log_notify_argv(int argc, char** argv);

// Per-tick hook: call after PADRead (after the hold check), before the sim.
void pc_input_log_tick(void);

// Yaw capture hook (see above). Null by default; the engine registers its
// pre-sim camera capture once before the first tick.
typedef void (*PcYawCaptureFn)(void);
void pc_input_log_set_yaw_capture_fn(PcYawCaptureFn fn);

// Post-tick hook: call after app->idle() returns, before/after the state
// hash. Writes the record for the tick that just simulated.
void pc_input_log_tick_end(void);

// Per-pad yaw for the current tick, for the sim (issue #879).
// Returns true and fills sin/cos when a yaw is set for this tick (v2 replay
// value pre-sim, or the pre-sim live capture); false when not set (switch
// off, or no Navi/camera at capture time). In det mode the sim must never
// read the camera on a miss: it uses the defined neutral basis (yaw 0)
// instead, so record and replay share one basis construction.
bool pc_netplay_control_yaw(int pad, float* sinYaw, float* cosYaw);

// Store the quantised pre-sim yaw for pad (called by the capture hook for
// slots without a replayed value, and never from the sim).
void pc_input_log_yaw_set(int pad, uint16_t yaw, uint8_t flags);
bool pc_input_log_yaw_valid(int pad);
uint16_t pc_input_log_yaw_raw(int pad);
uint8_t pc_input_log_yaw_flags(int pad);

// Whether record / replay is active this run (for the capture gate: capture
// the live yaw when det mode will use it, or when a record needs it,
// and do no extra work otherwise so the switch-off path is untouched).
bool pc_input_log_is_record_active(void);
bool pc_input_log_is_replay_active(void);

// Flush the record file, if any. Called every 300 ticks and on exit.

// Close the record file, if any. Called on the netplay exit path after the
// final flush.
void pc_input_log_close(void);
void pc_input_log_flush(void);
