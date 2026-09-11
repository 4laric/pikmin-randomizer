#include "port/audio_sink.h"
#include <SDL.h>
#include <vector>
#undef NDEBUG
#include <cassert>
#include <cstdio>
int main() {
    SDL_SetMainReady();
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    assert(PikiAudioSinkOpen(32000));
    std::vector<int16_t> pcm(64000, 1000);
    assert(PikiAudioSinkQueue(pcm.data(), 32000));
    // Holding an already paused device must not accidentally start it.
    PikiAudioSinkBBFTHold(1); PikiAudioSinkBBFTHold(0);
    SDL_Delay(80);
    assert(PikiAudioSinkQueuedFrames() == 32000);
    assert(PikiAudioSinkResume());
    SDL_Delay(80);
    PikiAudioSinkBBFTHold(1);
    const auto parked = PikiAudioSinkQueuedFrames();
    assert(parked < 32000 && parked > 0);
    SDL_Delay(80);
    assert(PikiAudioSinkQueuedFrames() == parked);
    PikiAudioSinkBBFTHold(0);
    SDL_Delay(80);
    assert(PikiAudioSinkQueuedFrames() < parked);
    PikiAudioSinkShutdown();
    std::puts("JAudio BBFT hold/resume test passed");
}
