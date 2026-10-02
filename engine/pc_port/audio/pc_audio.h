#ifndef PC_AUDIO_H
#define PC_AUDIO_H

#include "types.h"
#include "audio/pc_instrument_bank.h"
#include <memory>
#include "Dolphin/ai.h"

#ifdef __cplusplus
extern "C" {
#endif

// Initialization & Teardown
bool pc_audio_init(void);
// Transient BBFT pause; never changes persisted mixer volumes.
void pc_audio_set_bbft_held(bool held);
void pc_audio_shutdown(void);
bool pc_audio_play_stx(const char* path);
void pc_audio_stop_stream(void);
// Baja el stream a silencio en `fadeFrames` fotogramas de 60 Hz y lo apaga.
// 0 equivale a pc_audio_stop_stream().
void pc_audio_fade_stream(u32 fadeFrames);
bool pc_audio_load_wave_bank(const char* path);
bool pc_audio_play_sequence(u32 sequence);
void pc_audio_stop_sequence(void);
bool pc_audio_play_sequence_track(u8 track, u32 sequence);
bool pc_audio_sequence_track_active(u8 track);
void pc_audio_stop_sequence_track(u8 track);
void pc_audio_fade_sequence_track(u8 track, float volume, u32 fadeFrames);
bool pc_audio_write_sequence_port(u8 track, u8 port, u16 value);
void pc_audio_set_sequence_layers(u16 enabledMask, float volume, u32 fadeFrames);
void pc_audio_fade_sequence(float volume, u32 fadeFrames);

enum PCAudioBus {
    PC_AUDIO_BUS_STREAM = 0,
    PC_AUDIO_BUS_BGM = 1,
    PC_AUDIO_BUS_SE = 2,
    PC_AUDIO_BUS_DMA = 3,
    PC_AUDIO_BUS_COUNT = 4,
};

typedef struct PCAudioMetrics {
    u32 sampleRate;
    u32 deviceBufferFrames;
    u64 callbacks;
    u64 mixedFrames;
    u32 peakActiveVoices;
    u32 voiceSteals;
    u32 voiceRejects;
    u32 dmaUnderruns;
    u32 clips;
    u64 limitedFrames;
    u64 bgmTicks;
    u64 bossTicks;
    u64 seTicks;
    u64 eventTicks;
} PCAudioMetrics;

int pc_audio_play_wave(u32 waveSystem, u32 archive, u32 waveIndex,
                       float volume, float pan, bool looping);
int pc_audio_play_wave_ex(u32 waveSystem, u32 archive, u32 waveIndex,
                          float volume, float pan, bool looping,
                          PCAudioBus bus, u8 priority);
int pc_audio_play_note(u32 virtualBank, u32 program, u8 key, u8 velocity,
                       u32 waveScene, float volume, float pan,
                       PCAudioBus bus, u8 priority, float trackPitch,
                       u8 cutoff = 127, float fxMix = 0.0f,
                       float dolby = 0.0f,
                       std::shared_ptr<const std::vector<PCInstrumentOscillator>> envelope = {});
void pc_audio_stop_wave(int voice);
void pc_audio_update_wave(int voice, float volume, float pan, float pitch,
                          u8 cutoff = 127, float fxMix = 0.0f,
                          float dolby = 0.0f);
// Starts a linear release measured in output sample frames. A value of zero
// has the same immediate-stop semantics as pc_audio_stop_wave().
void pc_audio_release_wave(int voice, u32 releaseFrames, u16 releaseParam = 0);
void pc_audio_report_levels(void);
void pc_audio_set_bus_volume(PCAudioBus bus, float volume);
void pc_audio_stop_bus(PCAudioBus bus);
void pc_audio_set_stereo(bool stereo);
bool pc_audio_send_system_se(u16 id, bool stop);
bool pc_audio_send_orima_se(u16 id, bool stop, bool pikiSound);
bool pc_audio_write_se_port(u8 track, u8 port, u16 value);
// Like pc_audio_write_se_port, but through a command queue (the original's Jal_SendCmdQueue): the value waits until
// the child's script has taken the previous one from that port, so two cues raised in the same frame both arrive.
// Drops the new value when the queue (16 deep) is full.
bool pc_audio_queue_se_port(u8 track, u8 port, u16 value);
void pc_audio_set_se_track_volume(u8 track, float volume);
void pc_audio_set_se_track_paused(u8 track, bool paused);
bool pc_audio_send_event_action(u8 event, u8 slot, u16 command, bool stop);
// Called when an event action reports that it has finished, so the caller can
// free the slot it was occupying.
void pc_audio_set_event_action_finished_hook(void (*hook)(u8 event, u8 slot));
void pc_audio_set_event_mix(u8 event, float volume, float pan);
void pc_audio_set_events_paused(bool paused);
u32 pc_audio_wave_count(void);
u32 pc_audio_get_active_voice_count(void);
u32 pc_audio_get_clip_count(void);
void pc_audio_get_metrics(PCAudioMetrics* metrics);
void pc_audio_reset_metrics(void);

// AI Subsystem Emulation
AIDCallback pc_audio_register_dma_callback(AIDCallback callback);
void pc_audio_start_dma(u32 start_addr, u32 length);
void pc_audio_stop_dma(void);
u32  pc_audio_get_dma_bytes_left(void);


// Netplay audio trace (issue #1030). Env-gated by PIKMIN_NETPLAY_AUDIO_TRACE=1;
// every call is a no-op (one cached flag test) when it is off, and nothing in
// here is read by the simulation. Counters feed a once-a-second summary line
// ("[audio-trace] sec ...") that compares sequencer / mixer / stream advance
// against wall time; events are logged immediately.
enum PCAudioTraceCounter {
    PCAT_GSYNC = 0,        // Jac_Gsync (once per sim tick / loop turn)
    PCAT_MOVIE_FRAME,      // Jac_DemoFrame (movie sound frame)
    PCAT_SE_UPDATE,        // SeSystem::update (listener update)
    PCAT_SE_UPDATE_AUTH,   // ... of which in the authoritative sim pass
    PCAT_FORMATION_CALL,   // Jac_Orima_Formation calls (per captain per tick)
    PCAT_FORMATION_START,  // gaya/charge sound start edges
    PCAT_FORMATION_STOP,   // gaya/charge sound stop edges
    PCAT_ORIMA_SE,         // Jac_PlayOrimaSe calls
    PCAT_ORIMA_SE_DROPPED, // ... suppressed (not the local captain's)
    PCAT_POLL,             // pc_window_poll_events audio pumps
    PCAT_EVENT_PLAY,       // Jac_PlayEventAction calls (positional gameplay sounds)
    PCAT_EVENT_FAIL,       // ... with no active event
    PCAT_SYSTEM_SE,        // Jac_PlaySystemSe calls
    PCAT_SE_CLOSED,        // SeSystem::update returns early (system closed)
    PCAT_SEJAM_NOTE,       // note-ons of the persistent SE sequence that got a voice
    PCAT_SEJAM_NOVOICE,    // ... that did not
    PCAT_MOVIE_FRAME_FWD,  // movie frames forwarded to the demo cue cursor (Jac_DemoFrame)
    PCAT_DEMO_CUE,         // demo sound cues written to the demo SE track
    PCAT_COUNT
};
bool pc_audio_trace_enabled(void);
void pc_audio_trace_count(int counter);
// One cinematic frame request (MoviePlayer::sndFrameMovie): which movie, which frame it is on, and whether it
// drives the demo cue cursor (the movie that started the demo audio) or only runs alongside it. Trace only.
void pc_audio_trace_movie_frame(int movieIndex, int frame, int forwarded);
void pc_audio_trace_event(const char* fmt, ...);
void pc_audio_trace_state(int demo, int flags, int scene);
void pc_audio_trace_listener(int authoritativePass, int localPlayer, float lx, float ly, float lz,
                             float cx, float cy, float cz);

// Audio Tick (Simulates AI Hardware Interrupts)
void pc_audio_tick(void);

#ifdef __cplusplus
}
#endif

#endif // PC_AUDIO_H
