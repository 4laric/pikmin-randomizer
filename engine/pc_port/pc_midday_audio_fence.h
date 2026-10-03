#pragma once
#include <cstdint>
#include <string>
namespace pc_midday {
// Called only from the actual audio init/shutdown device lifecycle. No engine
// state is claimed quiescent until the real SDL device reaches PAUSED.
bool registerConstructionAudioDevice(uint32_t,std::string&);
bool unregisterConstructionAudioDevice(std::string&);
// Only after complete logical audio/world publication, by the original owner.
// This physical transition does not itself prove world restoration complete.
bool resumeConstructionAudioDevice(std::string&);
class AudioConstructionFence {
 bool held_=false;
public:
 AudioConstructionFence()=default;
 AudioConstructionFence(const AudioConstructionFence&)=delete;
 AudioConstructionFence& operator=(const AudioConstructionFence&)=delete;
 ~AudioConstructionFence();
 bool begin(std::string&);
 // keepPaused=true only after logical audio staging/whole-world publication.
 // This barrier alone does not capture or restore JAM/event/wave/DMA state.
 bool release(bool keepPaused,std::string&);
 bool held()const{return held_;}
};
uint64_t suppressedAudioConstructionCommands();
}
// Source audio mutators call this before touching queues/caches/JAM/voices/DMA.
// It is inert outside the actual device fence and safe on the callback thread.
bool pc_midday_audio_command_suppressed();
