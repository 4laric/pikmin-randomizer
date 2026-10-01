#pragma once

// Sequencer clock guard (issue #1030).
//
// pc_audio_tick() advances the JAM sequencers (BGM, boss/demo track, the
// persistent SE sequence and the positional event sequence) by the wall-clock
// time since the previous call, but it only runs when the main thread gets
// there. A stall of the main thread (a shader compile on the first frame of a
// cinematic, a stage or movie load, a save) used to be paid back in full on
// the next call: the whole missed span of the song was replayed at once, so
// the music fast-forwarded in a burst of notes ("the cutscene music is fast").
// A trace of a netplay pair with a 1.8 s stall at the start of the first
// cinematic showed 631 BGM ticks in the next second against the normal 224
// (ratio 2.80).
//
// The span one call may advance a sequencer by is capped. Anything beyond the
// cap is dropped, not queued: the music simply resumes from where it was,
// which is also where the simulation is, since the simulation does not
// advance during the stall either. The cap is far above any normal frame
// (33 ms at 30 Hz, 100 ms at 10 fps), so single-frame hitches and slow
// machines still play in real time.

#include <cstdint>

constexpr double kPcAudioMaxSeqAdvanceSeconds = 0.25;

// Seconds a sequencer should advance by for the span [last, now] of a counter
// running at `frequency` Hz, capped at kPcAudioMaxSeqAdvanceSeconds. The part
// that was cut off is added to *droppedSeconds when it is non-null.
inline double pc_audio_seq_elapsed(uint64_t now, uint64_t last, uint64_t frequency, double* droppedSeconds = nullptr)
{
	if (last == 0 || frequency == 0 || now <= last) {
		return 0.0;
	}
	const double elapsed = static_cast<double>(now - last) / static_cast<double>(frequency);
	if (elapsed > kPcAudioMaxSeqAdvanceSeconds) {
		if (droppedSeconds != nullptr) {
			*droppedSeconds += elapsed - kPcAudioMaxSeqAdvanceSeconds;
		}
		return kPcAudioMaxSeqAdvanceSeconds;
	}
	return elapsed;
}
