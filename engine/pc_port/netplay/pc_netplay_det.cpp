// Deterministic fixed-step mode switch for netplay M1 (issue #878).
//
// Engine-free TU: only the C library, env vars and argv. It is linked into
// pikmin_pc and into the engine-free pc_bbft_test / pc_sim_rng_test targets.

#include "netplay/pc_netplay_det.h"
#include "netplay/pc_sim_rng.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cerrno>

#if defined(__SSE__) || defined(__x86_64__) || defined(_M_X64) || defined(_M_IX86)
#include <xmmintrin.h>
#define PC_DET_HAVE_SSE_CSR 1
#endif
#if defined(__i386__) || defined(__x86_64__) || defined(_M_IX86) || defined(_M_X64)
#define PC_DET_HAVE_X87_CW 1
#endif
#if !defined(PC_DET_HAVE_X87_CW)
#include <cfenv>
#endif

// Netplay M4 lane B2 fix round 1 (issue #885, C5/E1): a resumed netplay
// campaign's stage start (pc_randomizer.cpp prints START_STAGE there, netplay
// sessions only). Weak: null where pc_randomizer.cpp is not linked.
#if defined(__GNUC__)
__attribute__((weak)) void pc_randomizer_netplay_stage_start(int day, int stage);
#else
void pc_randomizer_netplay_stage_start(int day, int stage);
#endif

namespace {

bool sDeterministic = false;
bool sUnthrottled   = false;
unsigned sTick      = 0;
// M5c lane C (issue #887): the last reseeded day and a reseed counter, read
// by the netplay session's campaign record (which day a checkpoint plays on
// from). Written only here, never read by the simulation.
int sLastReseedDay      = 0;
unsigned sReseedCount   = 0;

bool envIsOne(const char* name)
{
	const char* value = std::getenv(name);
	return value != nullptr && value[0] == '1' && value[1] == '\0';
}

// FNV-1a over raw bytes, the hash named by the M1 brief for the per-day seed.
unsigned fnv1aBytes(unsigned hash, const void* data, unsigned size)
{
	const unsigned char* bytes = static_cast<const unsigned char*>(data);
	for (unsigned i = 0; i < size; ++i) {
		hash ^= bytes[i];
		hash *= 16777619u;
	}
	return hash;
}

unsigned readU32Env(const char* name, unsigned fallback)
{
	const char* value = std::getenv(name);
	if (value == nullptr || *value == '\0') return fallback;
	// M1 det fix: fail loudly instead of silently falling back. strtoul
	// accepts a leading '-' (wraps) and saturates on overflow, so reject
	// both, plus trailing garbage and ERANGE.
	if (value[0] == '-') {
		std::fprintf(stderr, "[netplay-det] invalid %s='%s', using %u\n", name, value, fallback);
		return fallback;
	}
	errno     = 0;
	char* end = nullptr;
	const unsigned long parsed = std::strtoul(value, &end, 0);
	if (end == value || *end != '\0' || errno == ERANGE || parsed > 0xfffffffful) {
		std::fprintf(stderr, "[netplay-det] invalid %s='%s', using %u\n", name, value, fallback);
		return fallback;
	}
	return static_cast<unsigned>(parsed);
}

} // namespace

void pc_netplay_det_init(int argc, char** argv)
{
	// Re-readable so host tests can toggle modes in-process; production calls
	// this once from main() before the game starts.
	sDeterministic = envIsOne("PIKMIN_NETPLAY_DETERMINISTIC");
	for (int i = 1; i < argc; ++i) {
		if (argv[i] != nullptr && std::strcmp(argv[i], "--netplay-deterministic") == 0) {
			sDeterministic = true;
			break;
		}
	}
	sUnthrottled = sDeterministic && envIsOne("PIKMIN_NETPLAY_UNTHROTTLED");
	// M1 det fix: record the RNG owner thread (report section 2b.3: the sim
	// and cosmetic streams are main-thread-only). Production calls this from
	// main(); the host test calls it from its main thread too.
	pc_sim_rng_note_main_thread();
	if (sDeterministic) {
		std::printf("[netplay-det] deterministic fixed-step mode ON%s\n",
		    sUnthrottled ? " (unthrottled: one tick per loop, no vsync wait)" : "");
		std::fflush(stdout);
	}
}

bool pc_netplay_deterministic(void) { return sDeterministic; }

bool pc_netplay_unthrottled(void) { return sDeterministic && sUnthrottled; }

void pc_netplay_det_force_on(void)
{
	sDeterministic = true;
	sUnthrottled   = sUnthrottled || envIsOne("PIKMIN_NETPLAY_UNTHROTTLED");
	pc_sim_rng_note_main_thread();
	std::printf("[netplay-det] deterministic fixed-step mode ON (forced by netplay)%s\n",
	    sUnthrottled ? " (unthrottled: as fast as the session allows)" : "");
	std::fflush(stdout);
}

unsigned pc_netplay_tick(void) { return sTick; }

void pc_netplay_on_tick_begin(void)
{
	++sTick;
	if (!sDeterministic) return;
	// Pin the FP environment every tick: third-party DLLs (GL ICDs, audio,
	// SDL) may change it on our thread. MXCSR 0x1F80 is round-to-nearest
	// with flush-to-zero and denormals-are-zero masked as on reset; the x87
	// word below is 64-bit mantissa, round-to-nearest, all exceptions masked.
#if defined(PC_DET_HAVE_SSE_CSR)
	_mm_setcsr(0x1F80);
#endif
#if defined(PC_DET_HAVE_X87_CW)
	// 0x037F: exception masks 0-5 set, precision bits 8-9 = 11b (64-bit),
	// rounding bits 10-11 = 00b (nearest). _controlfp() would be the CRT
	// spelling, but the repo's include/Dolphin/float.h shadows the system
	// <float.h> on this build's include path, so set the word directly.
	{
		const unsigned short cw = 0x037Fu;
		__asm__ volatile("fldcw %0" : : "m"(cw));
	}
#else
	std::fesetround(FE_TONEAREST);
#endif
}

float pc_netplay_fixed_dt(int frameClamp)
{
	// M1 det fix: mirror PcFrameScheduler::deltaForClamp exactly (kept as a
	// local mirror, not a call, so this TU stays engine-free and linkable
	// into the host tests). Callers pass gsys->mFrameRate, the current tick
	// rate, instead of hard-coding the 30 Hz clamp.
	if (frameClamp == 0) return 1.0f / 120.0f;
	if (frameClamp == 1) return 1.0f / 60.0f;
	if (frameClamp == 2) return 1.0f / 30.0f;
	return float(frameClamp) / 60.0f;
}

void pc_netplay_det_reseed_for_new_day(int dayIndex, int stageId)
{
	if (!sDeterministic) return;
	const unsigned sessionSeed = readU32Env("PIKMIN_NETPLAY_SEED", 0);
	// FNV-1a/32: offset basis 2166136261, prime 16777619, over the session
	// seed, day index and stage id as little-endian u32 words. Both peers
	// compute the same words from the same save, so both streams match.
	unsigned hash = 2166136261u;
	const unsigned words[3]
	    = { sessionSeed, static_cast<unsigned>(dayIndex), static_cast<unsigned>(stageId) };
	hash = fnv1aBytes(hash, words, sizeof(words));
	pc_sim_srand(hash);
	// Cosmetic stream: same hash with a fixed odd-xor so menu/draw-only draws
	// never alias the sim stream, even for seed 0 / day 1 / stage 0.
	pc_cosmetic_srand(hash ^ 0x9E3779B9u);
	// Slice lane (issue #880): annotate the day-boundary tick so single and
	// pair runs can quote the exact tick where the next day's stage loads.
	// Log-only; the RNG sequence and timing are untouched.
	std::printf("[netplay-det] reseed day=%d stage=%d sessionSeed=%u hash=0x%08x tick=%u\n", dayIndex,
	    stageId, sessionSeed, hash, sTick);
	std::fflush(stdout);
	// B2 fix round 1: log-only, after the reseed (RNG and timing untouched).
	if (pc_randomizer_netplay_stage_start != nullptr) pc_randomizer_netplay_stage_start(dayIndex, stageId);
	sLastReseedDay = dayIndex;
	++sReseedCount;
}

int pc_netplay_det_last_reseed_day(void) { return sLastReseedDay; }
unsigned pc_netplay_det_reseed_count(void) { return sReseedCount; }

const char* pc_netplay_det_profile_path(void)
{
	static const char* path = [] {
		const char* value = std::getenv("PIKMIN_NETPLAY_PROFILE_LOG");
		return (value != nullptr && *value != '\0') ? value : nullptr;
	}();
	return path;
}
