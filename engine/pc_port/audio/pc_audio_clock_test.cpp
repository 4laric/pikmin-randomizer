// Host test for the sequencer clock guard (issue #1030): a main-thread stall
// must not be replayed as a burst of music, normal frames must pass through.
//
// Uses the check()/failures pattern (never bare assert(): Release builds
// define NDEBUG, which compiles assert() out).
#include <cmath>
#include <cstdint>
#include <cstdio>

#include "audio/pc_audio_clock.h"

static int failures = 0;

static void check(bool condition, const char* message)
{
	if (!condition) {
		std::fprintf(stderr, "FAIL: %s\n", message);
		++failures;
	}
}

static bool near(double a, double b) { return std::fabs(a - b) < 1e-6; }

int main()
{
	const uint64_t freq = 10000000; // SDL_GetPerformanceFrequency on Windows

	// A normal 30 Hz frame, a 10 fps frame and a 4 fps frame pass through.
	double dropped = 0.0;
	check(near(pc_audio_seq_elapsed(1000 + freq / 30, 1000, freq, &dropped), 1.0 / 30.0), "30 Hz frame is uncapped");
	check(near(pc_audio_seq_elapsed(1000 + freq / 10, 1000, freq, &dropped), 0.1), "10 fps frame is uncapped");
	check(near(pc_audio_seq_elapsed(1000 + freq / 4, 1000, freq, &dropped), 0.25), "the cap itself passes through");
	check(near(dropped, 0.0), "nothing dropped below the cap");

	// A 1.84 s stall (the traced first-cinematic stall) advances by the cap and
	// reports the rest as dropped, not queued.
	const uint64_t stall = static_cast<uint64_t>(1.84 * static_cast<double>(freq));
	const double advanced = pc_audio_seq_elapsed(1000 + stall, 1000, freq, &dropped);
	check(near(advanced, kPcAudioMaxSeqAdvanceSeconds), "a 1.84 s stall advances by the cap only");
	check(std::fabs(dropped - (1.84 - kPcAudioMaxSeqAdvanceSeconds)) < 1e-6, "the rest of the stall is reported dropped");
	check(pc_audio_seq_elapsed(1000 + stall, 1000, freq) == kPcAudioMaxSeqAdvanceSeconds, "dropped pointer is optional");

	// Degenerate inputs advance nothing.
	check(pc_audio_seq_elapsed(5000, 0, freq) == 0.0, "no previous counter: nothing");
	check(pc_audio_seq_elapsed(5000, 1000, 0) == 0.0, "zero frequency: nothing");
	check(pc_audio_seq_elapsed(1000, 5000, freq) == 0.0, "counter went backwards: nothing");
	check(pc_audio_seq_elapsed(1000, 1000, freq) == 0.0, "same counter: nothing");

	if (failures != 0) {
		std::fprintf(stderr, "pc_audio_clock_test: %d failure(s)\n", failures);
		return 1;
	}
	std::printf("pc_audio_clock_test: ok\n");
	return 0;
}
