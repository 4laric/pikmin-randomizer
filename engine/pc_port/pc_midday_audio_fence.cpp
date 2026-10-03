#include "pc_midday_audio_fence.h"
#include <SDL.h>
#include <atomic>
#include <mutex>
#include <thread>
#include <exception>
namespace {
std::mutex control;
SDL_AudioDeviceID device=0;
std::thread::id owner;
std::atomic<bool> active{false};
std::atomic<uint64_t> suppressed{0};
bool wasPlaying=false;
bool fail(std::string& e,const char* text){e=text;return false;}
bool onOwner(){return owner==std::this_thread::get_id();}
}
namespace pc_midday {
bool registerConstructionAudioDevice(uint32_t value,std::string& e){
 std::lock_guard<std::mutex> lock(control);
 if(active.load()||!value)return fail(e,"audio device registration during fence/without device");
 if(device&&(device!=value||!onOwner()))return fail(e,"audio device lifecycle ownership mismatch");
 if(SDL_GetAudioDeviceStatus(value)==SDL_AUDIO_STOPPED)return fail(e,"audio device is not an open SDL device");
 device=value;owner=std::this_thread::get_id();e.clear();return true;
}
bool unregisterConstructionAudioDevice(std::string& e){
 std::lock_guard<std::mutex> lock(control);
 if(active.load()||(device&&!onOwner()))return fail(e,"audio device cannot close during foreign/active fence");
 device=0;owner={};e.clear();return true;
}
bool resumeConstructionAudioDevice(std::string& e){
 std::lock_guard<std::mutex> lock(control);
 if(active.load()||!device||!onOwner())return fail(e,"audio resume requires original owner and no constructor fence");
 if(SDL_GetAudioDeviceStatus(device)!=SDL_AUDIO_PAUSED)return fail(e,"audio publication device is not actually paused");
 SDL_PauseAudioDevice(device,0);
 if(SDL_GetAudioDeviceStatus(device)!=SDL_AUDIO_PLAYING)return fail(e,"actual audio callback did not resume");
 e.clear();return true;
}
bool AudioConstructionFence::begin(std::string& e){
 std::lock_guard<std::mutex> lock(control);
#if defined(PIKI_USE_JAUDIO) && PIKI_USE_JAUDIO
 return fail(e,"native JAudio construction fence is not implemented");
#endif
 if(held_||active.load()||!device||!onOwner())return fail(e,"audio constructor fence requires one actual owner device");
 const auto before=SDL_GetAudioDeviceStatus(device);
 if(before!=SDL_AUDIO_PLAYING&&before!=SDL_AUDIO_PAUSED)return fail(e,"audio device not ready for quiescence");
 // Drain the last actual callback BEFORE suppression. Dropping a half-finished
 // normal callback would corrupt preexisting logical audio on an aborted stage.
 SDL_PauseAudioDevice(device,1);SDL_LockAudioDevice(device);
 if(SDL_GetAudioDeviceStatus(device)!=SDL_AUDIO_PAUSED){SDL_UnlockAudioDevice(device);return fail(e,"actual audio callback failed to quiesce");}
 wasPlaying=before==SDL_AUDIO_PLAYING;active.store(true);held_=true;
 SDL_UnlockAudioDevice(device);e.clear();return true;
}
bool AudioConstructionFence::release(bool keepPaused,std::string& e){
 std::lock_guard<std::mutex> lock(control);
 if(!held_||!active.load()||!device||!onOwner())return fail(e,"audio fence release requires actual owning guard");
 SDL_LockAudioDevice(device);
 if(SDL_GetAudioDeviceStatus(device)!=SDL_AUDIO_PAUSED){SDL_UnlockAudioDevice(device);return fail(e,"audio device resumed behind constructor fence");}
 active.store(false);held_=false;
 if(!keepPaused&&wasPlaying)SDL_PauseAudioDevice(device,0);
 SDL_UnlockAudioDevice(device);e.clear();return true;
}
AudioConstructionFence::~AudioConstructionFence(){if(held_){std::string e;if(!release(false,e))std::terminate();}}
uint64_t suppressedAudioConstructionCommands(){return suppressed.load();}
}
bool pc_midday_audio_command_suppressed(){if(!active.load())return false;suppressed.fetch_add(1);return true;}
