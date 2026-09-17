// Focused fail-closed test for the Jac_NoteDemoSkipped legacy stub (#704).
//
// Links against the REAL pc_port/dolphin_stubs/audio_stubs.cpp object built in
// the default (PIKMIN_NATIVE_JAUDIO=OFF) config. All pc_audio_* externals the
// stub object needs are defined here as no-ops, except pc_audio_fade_stream,
// which records calls so the test can observe whether a finishing demo kept
// or suppressed its stream carry. No engine, SDL, display or audio device is
// touched; the stubbed pc_audio layer never executes.
//
// Build (from the native worktree, MinGW g++, same flags as the stub TU):
//   g++ <stub TU flags> -c tools/p2_note_demo_skip_stub_test.cpp -o <out>/test.o
//   g++ <out>/test.o <build>/audio_stubs.cpp.obj -o <out>/p2_note_demo_skip_stub_test.exe
//
// Cases (fail-closed; any deviation exits 1):
//   1. StartDemo(1) + FinishDemo (no skip) keeps the carry: no stream fade.
//   2. StartDemo(1) + NoteDemoSkipped + FinishDemo suppresses the carry:
//      exactly one stream fade (mirrors pikidemo.c clearing 0x20 on skip).
//   3. The skip flag is consumed: a later StartDemo(1) + FinishDemo without a
//      new skip keeps the carry again (no leak into the next demo).
#include <cstdio>

#include "jaudio/pikidemo.h"
#include "audio/pc_audio.h"

namespace {
int gFadeStreamCalls = 0;
unsigned gLastFadeFrames = 0;
} // namespace

extern "C" {

bool pc_audio_init(void) { return false; }
void pc_audio_fade_stream(u32 fadeFrames) {
    ++gFadeStreamCalls;
    gLastFadeFrames = fadeFrames;
}
bool pc_audio_load_wave_bank(const char* path) { (void)path; return false; }
bool pc_audio_play_sequence(u32 sequence) { (void)sequence; return false; }
void pc_audio_stop_sequence(void) {}
bool pc_audio_play_sequence_track(u8 track, u32 sequence) {
    (void)track; (void)sequence; return false;
}
bool pc_audio_sequence_track_active(u8 track) { (void)track; return false; }
void pc_audio_stop_sequence_track(u8 track) { (void)track; }
void pc_audio_fade_sequence_track(u8 track, float volume, u32 fadeFrames) {
    (void)track; (void)volume; (void)fadeFrames;
}
bool pc_audio_write_sequence_port(u8 track, u8 port, u16 value) {
    (void)track; (void)port; (void)value; return false;
}
void pc_audio_set_sequence_layers(u16 enabledMask, float volume, u32 fadeFrames) {
    (void)enabledMask; (void)volume; (void)fadeFrames;
}
void pc_audio_fade_sequence(float volume, u32 fadeFrames) {
    (void)volume; (void)fadeFrames;
}
int pc_audio_play_note(u32 virtualBank, u32 program, u8 key, u8 velocity,
                       u32 waveScene, float volume, float pan, PCAudioBus bus,
                       u8 priority, float trackPitch, u8 cutoff, float fxMix,
                       float dolby,
                       std::shared_ptr<const std::vector<PCInstrumentOscillator>> envelope) {
    (void)virtualBank; (void)program; (void)key; (void)velocity;
    (void)waveScene; (void)volume; (void)pan; (void)bus; (void)priority;
    (void)trackPitch; (void)cutoff; (void)fxMix; (void)dolby; (void)envelope;
    return 0;
}
void pc_audio_stop_wave(int voice) { (void)voice; }
void pc_audio_release_wave(int voice, u32 releaseFrames, u16 releaseParam) {
    (void)voice; (void)releaseFrames; (void)releaseParam;
}
void pc_audio_set_bus_volume(PCAudioBus bus, float volume) {
    (void)bus; (void)volume;
}
void pc_audio_stop_bus(PCAudioBus bus) { (void)bus; }
void pc_audio_set_stereo(bool stereo) { (void)stereo; }
bool pc_audio_send_system_se(u16 id, bool stop) { (void)id; (void)stop; return false; }
bool pc_audio_send_orima_se(u16 id, bool stop, bool pikiSound) {
    (void)id; (void)stop; (void)pikiSound; return false;
}
bool pc_audio_write_se_port(u8 track, u8 port, u16 value) {
    (void)track; (void)port; (void)value; return false;
}
void pc_audio_set_se_track_volume(u8 track, float volume) {
    (void)track; (void)volume;
}
void pc_audio_set_se_track_paused(u8 track, bool paused) {
    (void)track; (void)paused;
}
bool pc_audio_send_event_action(u8 event, u8 slot, u16 command, bool stop) {
    (void)event; (void)slot; (void)command; (void)stop; return false;
}
void pc_audio_set_event_action_finished_hook(void (*hook)(u8 event, u8 slot)) {
    (void)hook;
}
void pc_audio_set_event_mix(u8 event, float volume, float pan) {
    (void)event; (void)volume; (void)pan;
}
void pc_audio_set_events_paused(bool paused) { (void)paused; }
AIDCallback pc_audio_register_dma_callback(AIDCallback callback) {
    (void)callback; return 0;
}
void pc_audio_start_dma(u32 start_addr, u32 length) {
    (void)start_addr; (void)length;
}
void pc_audio_stop_dma(void) {}
u32 pc_audio_get_dma_bytes_left(void) { return 0; }
bool pc_audio_play_stx(const char* path) { (void)path; return false; }

} // extern "C"

int main() {
    int failures = 0;
    const auto check = [&](bool ok, const char* name) {
        std::printf("%s NOTE_DEMO_SKIP_STUB %s fade_calls=%d\n",
                    ok ? "PASS" : "FAIL", name, gFadeStreamCalls);
        std::fflush(stdout);
        if (!ok) ++failures;
    };
    // Case 1: cinema 1 arms the carry; finishing unwatched keeps it.
    Jac_StartDemo(1);
    Jac_FinishDemo();
    check(gFadeStreamCalls == 0, "carry-kept-without-skip");
    // Case 2: skipping suppresses the carry on finish.
    gFadeStreamCalls = 0;
    Jac_StartDemo(1);
    Jac_NoteDemoSkipped();
    Jac_FinishDemo();
    check(gFadeStreamCalls == 1, "skip-suppresses-carry-on-finish");
    // Case 3: the skip flag is consumed by the finish above.
    gFadeStreamCalls = 0;
    Jac_StartDemo(1);
    Jac_FinishDemo();
    check(gFadeStreamCalls == 0, "skip-flag-consumed");
    if (failures == 0) {
        std::printf("PASS P2_NOTE_DEMO_SKIP_STUB\n");
    } else {
        std::printf("FAIL P2_NOTE_DEMO_SKIP_STUB failures=%d\n", failures);
    }
    std::fflush(stdout);
    return failures == 0 ? 0 : 1;
}
