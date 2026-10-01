// Simulation vs cosmetic RNG for deterministic netplay, M1 (issue #878).
//
// Engine-free TU (see pc_netplay_det.cpp note).

#include "netplay/pc_sim_rng.h"
#include "netplay/pc_netplay_det.h"

#include <cstdio>
#include <thread>

namespace {

unsigned sSimState      = 1;
unsigned sCosmeticState = 0xC05E77u;

// Main-thread id recorded by pc_netplay_det_init (see pc_netplay_det.cpp).
// Report section 2b.3 requires the streams to be main-thread-only: the PC
// OSResumeThread spawns real std::threads, so a future RNG draw off the main
// thread would race silently. In det mode such a call logs once to stderr.
std::thread::id sMainThreadId;
bool sMainThreadRecorded = false;
bool sThreadWarned       = false;

void checkMainThread(const char* which)
{
	if (!pc_netplay_deterministic() || !sMainThreadRecorded || sThreadWarned) return;
	if (std::this_thread::get_id() == sMainThreadId) return;
	sThreadWarned = true;
	std::fprintf(stderr, "[netplay-det] %s called from a non-main thread; RNG streams are main-thread-only\n",
	    which);
}

// MSL-compatible LCG step shared by both streams.
unsigned lcgNext(unsigned& state)
{
	state = state * 1103515245u + 12345u;
	return (state >> 16) & 0x7fffu;
}

} // namespace

void pc_sim_rng_note_main_thread(void)
{
	sMainThreadId       = std::this_thread::get_id();
	sMainThreadRecorded = true;
}

int pc_sim_rand(void)
{
	if (!pc_netplay_deterministic()) return std::rand();
	checkMainThread("pc_sim_rand");
	return static_cast<int>(lcgNext(sSimState));
}

void pc_sim_srand(unsigned seed) { sSimState = seed; }

unsigned pc_sim_rng_state(void) { return sSimState; }

void pc_sim_rng_set_state(unsigned state) { sSimState = state; }

int pc_cosmetic_rand(void)
{
	if (!pc_netplay_deterministic()) return std::rand();
	checkMainThread("pc_cosmetic_rand");
	return static_cast<int>(lcgNext(sCosmeticState));
}

void pc_cosmetic_srand(unsigned seed) { sCosmeticState = seed; }

unsigned pc_cosmetic_rng_state(void) { return sCosmeticState; }

void pc_cosmetic_rng_set_state(unsigned state) { sCosmeticState = state; }
