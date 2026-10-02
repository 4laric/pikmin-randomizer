#pragma once

// Netplay audio ownership (issue #1030).
//
// A netplay session runs both captains' simulation on both PCs, so every
// captain-owned sound that is NOT positional (the whistle, footsteps, the
// C-stick charge / swarm sound, the captain's voice, the Pikmin voices that
// captain triggers) would play on both machines: the joiner heard the host's
// whistle and the host heard the joiner's charge, and the two captains' calls
// also fought over the single charge-sound state (captain 1's idle stick
// stopped what captain 2's active stick had just started, every tick, which
// is what made the charge sound stutter "sped up").
//
// Audio is local output, never sim state: nothing the simulation reads
// depends on whether one of these calls reaches the mixer, so dropping the
// other peer's captain's global sounds cannot desynchronise anything. The
// positional sounds (SeContext events) are untouched: the listener already
// follows the local presentation camera (GameCoreSection::draw), so the other
// captain's positional sounds are heard from where that captain really is.
//
// The captain code (Navi) marks which captain it is running with a
// PcAudioSource scope. Anything outside a scope is unattributed and always
// audible. Outside a deterministic netplay session (single player, local
// split-screen co-op) every sound is audible, exactly as before.
// PIKMIN_NETPLAY_AUDIO_LEGACY=1 restores the old behaviour for A/B traces.
//
// "In a session" means a host or join switch is set: a deterministic replay of a recorded input log
// (run_replay, an M1 .pkni) runs the same two-pass frame with one human watching both captains and no partner PC,
// so nothing is muted there.

#if defined(PIKI_PC_PORT) && defined(__cplusplus)

#include <cstdlib>

#include "netplay/pc_netplay_present.h"

// Declared in netplay/pc_netplay_session.h with C++ linkage and defined only in netplay builds (the session TU),
// so it is referenced weakly: the default build and the host tests link without it.
__attribute__((weak)) bool pc_netplay_session_active(void);

inline int& pc_audio_source_captain_slot()
{
	static int sSourceCaptain = -1;
	return sSourceCaptain;
}

// RAII: the captain (0 = Olimar, 1 = Louie) whose code is running.
class PcAudioSource {
public:
	explicit PcAudioSource(int captain)
	    : mPrevious(pc_audio_source_captain_slot())
	{
		pc_audio_source_captain_slot() = captain;
	}
	~PcAudioSource() { pc_audio_source_captain_slot() = mPrevious; }
	PcAudioSource(const PcAudioSource&)            = delete;
	PcAudioSource& operator=(const PcAudioSource&) = delete;

private:
	int mPrevious;
};

inline bool pc_audio_in_netplay_session()
{
	return pc_netplay_session_active != nullptr && pc_netplay_session_active();
}

inline bool pc_audio_legacy_ownership()
{
	static const bool legacy = [] {
		const char* v = std::getenv("PIKMIN_NETPLAY_AUDIO_LEGACY");
		return v != nullptr && v[0] != '\0' && v[0] != '0';
	}();
	return legacy;
}

// True when a captain-owned, non-positional sound raised right now should
// reach this PC's mixer.
inline bool pc_audio_source_audible()
{
	const int source = pc_audio_source_captain_slot();
	if (source < 0 || !pc_netplay_present_two_pass_active() || !pc_audio_in_netplay_session()
	    || pc_audio_legacy_ownership()) {
		return true;
	}
	return source == pc_netplay_present_local_player();
}

#endif
