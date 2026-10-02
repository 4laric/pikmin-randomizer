#pragma once
// Netplay M4 gap-fix lane S (issue #885): long blocking loads must not drop
// the session. Engine-free, header-only policy pieces of the load guard that
// pc_netplay_session.cpp drives, so the host-run test links nothing else.
//
// The problem. GekkoNet's disconnect check is a wall-clock idle timer on the
// receiving side (MessageSystem::HandleTooFarBehindActors: now minus the
// last datagram received from that peer, of any type, against the timeout).
// A peer blocked inside one Advance tick (a synchronous stage load, or the
// presentation pass specialising TEV programs: 65 of them took ~16 s under
// load in integ-m4) sends nothing, so its peer drops it after 15 s, and the
// blocked peer then reads the peer's Disconnect messages and drops too. The
// failure needs one peer to be silent for more than the timeout while the
// other keeps polling: a one-sided stall, or two stalls of unequal length or
// at different times. Two equal stalls at the same moment usually survive
// even without the guard, because GekkoNet stamps last_received_message
// with the time a datagram is processed, so each peer drains the other's
// queued datagrams right after its own block (lane S runs N3/N7).
//
// The guard has two parts; each can be switched off on its own.
//
// (a) Main-thread keep-alive network poll. The long loops call
//     pc_netplay_load_keepalive(site) between their steps: after each TEV
//     program is created (pc_gfx.cpp), on every DVDOpen/DVDRead (stage and
//     archive I/O, dvd_stubs.cpp), at the stage-load hook, and while the
//     day-end save waits for its card I/O or writes its checkpoint. Inside an
//     Advance tick, at most once per kKeepAliveIntervalMs, it calls
//     gekko_network_poll only: receive, ack, resend unacked inputs and the
//     500 ms NetworkHealth. It deliberately does NOT pump the bulk channel
//     (the bulk channel has no idle timer and resends until acked, and its
//     consumers run between ticks; see loadguard_pump). It never produces or
//     consumes an Advance, submits no input and touches no sim state, so the
//     simulation cannot change: it is the same GekkoNet poll the B2 day-end
//     save barrier already runs inside its save tick. The loading peer keeps
//     talking, so neither peer's idle timer runs, and a real peer loss is
//     still detected after the normal timeout. It cannot split one single
//     long step (one huge read, CPU work between two call sites).
//
// (b) Load-window timeout extension. Every stage load runs inside the same
//     Advance frame F on both peers (the sim is identical), so each peer
//     raises its own GekkoNet disconnect timeout to the load timeout (default
//     60 s) when the load starts, without any message, and restores the
//     normal timeout once its own Advance of frame F + kLoadWindowFrames has
//     run. That Advance needs the peer's input for that frame, which the peer
//     submitted only after completing its Advance of frame
//     F + kLoadWindowFrames - delay - 1 >= F + 21 (delay <= 8; a submit with
//     index s lands on frame s + delay and is made after s Advances), so the
//     peer is demonstrably out of its load and inputs flow again when the
//     timeout drops back. This covers a single un-pumpable block (one huge
//     read, a driver stall) that (a) cannot split. Costs: a peer that dies
//     inside a load window is detected after the load timeout, not the
//     normal one; and a B1 HOLD that freezes the session less than
//     kLoadWindowFrames after a stage load keeps the window open for the
//     whole hold (no Advance runs to close it), so during that hold a dead
//     peer is also reported after the load timeout (60 s). Both peers keep
//     polling in a hold, so a live peer is never dropped by it.
//
// The B2 day-end save barrier (pc_netplay_save_barrier) waits inside the
// save tick for the peer, which may still be up to `delay` frames behind in
// a long tick of its own. With the guard on, the barrier lets GekkoNet
// decide peer death (it abandons the day as soon as GekkoNet reports the
// peer disconnected: the normal timeout, or the load timeout in a window)
// and otherwise waits up to barrier_deadline_ms() (the load timeout, 60 s by
// default), which only ends a wait for a peer that keeps polling but never
// arrives. With the guard off it keeps B2's fixed 10 s.
//
// Rollback (not used today: lockstep, no runahead). The window, the stage
// load count and the stall targeting are keyed to frames that run once on
// both peers, so the session skips them for rolling-back or running-ahead
// Advances (a resimulated stage load neither opens nor extends a window, and
// the window closes only on a first execution); the keep-alive still polls
// in those ticks.
//
// (c) (pre-warming the TEV programs in the handshake) was rejected: the
// programs a stage needs are only known once its materials draw, and it does
// nothing for stage I/O. The binary shader cache already warms later runs.

#include <stddef.h>
#include <stdint.h>
#include <string.h>

#include <string>

namespace pc_netplay_loadguard {

// Keep-alive call sites (pc_netplay_load_keepalive's argument).
enum Site {
	kSiteShader    = 1, // a specialised TEV program was created (pc_gfx.cpp)
	kSiteDvd       = 2, // DVDOpen / DVDRead (dvd_stubs.cpp)
	kSiteStageLoad = 3, // GameFlow::softReset (the N3 stage-load hook)
	kSiteStall     = 4, // between two slices of the test stall injector
	kSiteSave      = 5, // day-end save: card I/O wait, checkpoint write (fix round 1)
	kSiteCount     = 6, // per-site counters are indexed 0..kSiteCount-1
};

inline const char* site_name(int site)
{
	switch (site) {
	case kSiteShader: return "tev";
	case kSiteDvd: return "dvd";
	case kSiteStageLoad: return "load";
	case kSiteStall: return "stall";
	case kSiteSave: return "save";
	default: return "other";
	}
}

// Minimum wall time between two keep-alive pumps inside one tick. GekkoNet
// resends unacked inputs every 200 ms and sends NetworkHealth every 500 ms,
// so 50 ms keeps every one of its timers on schedule while a load that opens
// hundreds of files costs only a clock read per call.
constexpr double kKeepAliveIntervalMs = 50.0;
// Default GekkoNet disconnect timeout inside a load window.
constexpr unsigned kDefaultLoadDisconnectMs = 60000;
// Frames after the stage-load frame at which the window closes (see (b)).
constexpr uint32_t kLoadWindowFrames = 30;
// A tick that takes longer than this is logged with its keep-alive figures.
constexpr double kLongTickMs = 2000.0;
// B2's fixed day-end save barrier wait, kept when the guard is off.
constexpr unsigned kBarrierLegacyMs = 10000;

// Fix round 1 (MJ1): the longest the day-end save barrier waits for a peer
// that GekkoNet still reports connected. Guard off: B2's fixed 10 s. Guard
// on: the load timeout (never below the 10 s it replaces), i.e. the same
// bound a single slow step gets inside a load window; a dead or hung peer
// ends the wait earlier through GekkoNet's own disconnect.
inline unsigned barrier_deadline_ms(bool guard, unsigned loadMs)
{
	if (!guard) return kBarrierLegacyMs;
	return loadMs < kBarrierLegacyMs ? kBarrierLegacyMs : loadMs;
}

// Rate limit for the keep-alive pump.
class KeepAliveGate {
public:
	explicit KeepAliveGate(double intervalMs = kKeepAliveIntervalMs) : mIntervalMs(intervalMs) {}
	void reset() { mHave = false; mLastMs = 0; }
	// A pump is due when none ran yet or the interval has elapsed.
	bool due(double nowMs) const { return !mHave || nowMs - mLastMs >= mIntervalMs; }
	void pumped(double nowMs)
	{
		mHave   = true;
		mLastMs = nowMs;
	}
	double interval_ms() const { return mIntervalMs; }

private:
	double mIntervalMs;
	bool mHave    = false;
	double mLastMs = 0;
};

// The deterministic, frame-keyed disconnect-timeout extension of (b).
class LoadWindow {
public:
	void configure(bool enabled, unsigned normalMs, unsigned loadMs, uint32_t frames = kLoadWindowFrames)
	{
		mEnabled  = enabled;
		mNormalMs = normalMs;
		// Never shorter than the normal timeout: the window only ever widens.
		mLoadMs = loadMs < normalMs ? normalMs : loadMs;
		mFrames = frames;
		mOpen   = false;
		mOpenFrame = mCloseFrame = 0;
	}
	bool enabled() const { return mEnabled; }
	unsigned normal_ms() const { return mNormalMs; }
	unsigned load_ms() const { return mLoadMs; }
	bool is_open() const { return mOpen; }
	uint32_t open_frame() const { return mOpenFrame; }
	uint32_t close_frame() const { return mCloseFrame; }

	// A stage load started inside the Advance of `frame`. Returns true when
	// the caller must raise the GekkoNet timeout to load_ms() now (false when
	// disabled or already raised; a load inside an open window only moves
	// its close frame later).
	bool open(uint32_t frame)
	{
		if (!mEnabled) return false;
		mOpenFrame  = frame;
		mCloseFrame = frame + mFrames;
		if (mOpen) return false;
		mOpen = true;
		return true;
	}

	// The Advance of `frame` completed. Returns true when the window closes
	// now: the caller restores normal_ms().
	bool after_advance(uint32_t frame)
	{
		if (!mOpen || frame < mCloseFrame) return false;
		mOpen = false;
		return true;
	}

private:
	bool mEnabled      = false;
	unsigned mNormalMs = 15000;
	unsigned mLoadMs   = kDefaultLoadDisconnectMs;
	uint32_t mFrames   = kLoadWindowFrames;
	bool mOpen         = false;
	uint32_t mOpenFrame  = 0;
	uint32_t mCloseFrame = 0;
};

// ---- Opt-in test stall injector (netplay builds, test only) ----
//
//   PIKMIN_NETPLAY_TEST_STALL_MS=<ms>        total stall (1..600000); unset = off
//   PIKMIN_NETPLAY_TEST_STALL_AT=<where>     load (default; the first stage load
//                                            in the session) | load:<n> (the nth)
//                                            | shader (right after the first TEV
//                                            program created in the session, the
//                                            real integ-m4 stall site)
//                                            | tick:<n> (inside the Advance of
//                                            hash tick n, before the sim runs)
//   PIKMIN_NETPLAY_TEST_STALL_ROLE=<who>     host | join | both (default), so the
//                                            same env can be given to both peers
//   PIKMIN_NETPLAY_TEST_STALL_SLICE_MS=<ms>  slice length (default 250, the
//                                            per-program TEV cost measured under
//                                            load); 0 = one uninterrupted block
//
// The stall is wall-clock only (it touches no sim state, RNG or hash) and
// runs inside an Advance tick, exactly where the real stalls block the main
// loop. Between two slices it calls the same keep-alive entry the real long
// loops call, so a sliced stall is a long loop of slow steps (a TEV loop, or
// a slow stage load's reads) and slice 0 is a single un-pumpable block.
enum class StallAt { Load, Shader, Tick };

enum StallRole {
	kStallHost = 1,
	kStallJoin = 2,
	kStallBoth = 3,
};

struct StallPlan {
	bool enabled     = false;
	unsigned totalMs = 0;
	StallAt at       = StallAt::Load;
	uint64_t index   = 1; // load:<n> (1-based) or tick:<n>
	int roles        = kStallBoth;
	unsigned sliceMs = 250;
};

// Strict decimal parse (no sign, no spaces, no trailing text).
inline bool parse_decimal(const char* s, uint64_t maxValue, uint64_t* out)
{
	if (s == nullptr || *s == '\0') return false;
	uint64_t v = 0;
	for (const char* p = s; *p != '\0'; ++p) {
		if (*p < '0' || *p > '9') return false;
		v = v * 10 + (uint64_t)(*p - '0');
		if (v > maxValue) return false;
	}
	*out = v;
	return true;
}

// Parses the four variables (nullptr = unset). ms == nullptr leaves the
// injector off and returns true. Returns false with *err set on any bad
// value, in which case the injector stays off.
inline bool parse_stall_plan(const char* ms, const char* at, const char* role, const char* slice, StallPlan* out,
                             std::string* err)
{
	StallPlan p;
	*out = p;
	if (ms == nullptr) return true;
	uint64_t v = 0;
	if (!parse_decimal(ms, 600000, &v) || v == 0) {
		if (err) *err = "PIKMIN_NETPLAY_TEST_STALL_MS wants 1..600000";
		return false;
	}
	p.totalMs = (unsigned)v;
	if (at != nullptr) {
		if (strcmp(at, "load") == 0) {
			p.at    = StallAt::Load;
			p.index = 1;
		} else if (strcmp(at, "shader") == 0) {
			p.at    = StallAt::Shader;
			p.index = 1;
		} else if (strncmp(at, "load:", 5) == 0) {
			if (!parse_decimal(at + 5, 1000000, &v) || v == 0) {
				if (err) *err = "PIKMIN_NETPLAY_TEST_STALL_AT load:<n> wants n >= 1";
				return false;
			}
			p.at    = StallAt::Load;
			p.index = v;
		} else if (strncmp(at, "tick:", 5) == 0) {
			if (!parse_decimal(at + 5, 100000000, &v) || v == 0) {
				if (err) *err = "PIKMIN_NETPLAY_TEST_STALL_AT tick:<n> wants n >= 1";
				return false;
			}
			p.at    = StallAt::Tick;
			p.index = v;
		} else {
			if (err) *err = "PIKMIN_NETPLAY_TEST_STALL_AT wants load | load:<n> | shader | tick:<n>";
			return false;
		}
	}
	if (role != nullptr) {
		if (strcmp(role, "host") == 0) p.roles = kStallHost;
		else if (strcmp(role, "join") == 0) p.roles = kStallJoin;
		else if (strcmp(role, "both") == 0) p.roles = kStallBoth;
		else {
			if (err) *err = "PIKMIN_NETPLAY_TEST_STALL_ROLE wants host | join | both";
			return false;
		}
	}
	if (slice != nullptr) {
		if (!parse_decimal(slice, 60000, &v)) {
			if (err) *err = "PIKMIN_NETPLAY_TEST_STALL_SLICE_MS wants 0..60000";
			return false;
		}
		p.sliceMs = (unsigned)v;
	}
	p.enabled = true;
	*out      = p;
	return true;
}

// True when the plan stalls this peer.
inline bool stall_applies_to(const StallPlan& p, bool isHost)
{
	if (!p.enabled) return false;
	return (p.roles & (isHost ? kStallHost : kStallJoin)) != 0;
}

// Length of slice `i` (0-based) of the plan; 0 once the total is spent. A
// slice length of 0 (or one not shorter than the total) is a single block.
inline unsigned stall_slice_ms(const StallPlan& p, unsigned i)
{
	if (!p.enabled || p.totalMs == 0) return 0;
	if (p.sliceMs == 0 || p.sliceMs >= p.totalMs) return i == 0 ? p.totalMs : 0;
	const uint64_t start = (uint64_t)i * p.sliceMs;
	if (start >= p.totalMs) return 0;
	const uint64_t left = p.totalMs - start;
	return left < p.sliceMs ? (unsigned)left : p.sliceMs;
}

inline const char* stall_role_name(int roles)
{
	return roles == kStallHost ? "host" : roles == kStallJoin ? "join" : "both";
}

} // namespace pc_netplay_loadguard
