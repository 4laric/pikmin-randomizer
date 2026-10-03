#include "pc_midday_audio_fence.h"
#define SDL_MAIN_HANDLED
#include <SDL.h>
#include <atomic>
#include <thread>
#include <cstdlib>
#include <iostream>
#include <cstring>
using namespace pc_midday;
std::atomic<unsigned> callbacks{0};int checks=0;
void check(bool ok){++checks;if(!ok){std::cerr<<"audio fence check failed "<<checks<<": "<<SDL_GetError()<<"\n";std::exit(1);}}
void callback(void*,Uint8* p,int n){std::memset(p,0,size_t(n));callbacks.fetch_add(1);}
int main(){
 SDL_SetMainReady();SDL_setenv("SDL_AUDIODRIVER","dummy",1);check(SDL_Init(SDL_INIT_AUDIO)==0);std::string e;
 AudioConstructionFence noDevice;check(!noDevice.begin(e));check(!resumeConstructionAudioDevice(e));check(!pc_midday_audio_command_suppressed());
 SDL_AudioSpec wanted{};wanted.freq=48000;wanted.format=AUDIO_S16SYS;wanted.channels=2;wanted.samples=256;wanted.callback=callback;
 auto device=SDL_OpenAudioDevice(nullptr,0,&wanted,nullptr,0);check(device!=0);check(registerConstructionAudioDevice(device,e));SDL_PauseAudioDevice(device,0);
 for(unsigned i=0;i<100&&!callbacks.load();++i)SDL_Delay(2);
 check(callbacks.load()>0);
 AudioConstructionFence guard;check(guard.begin(e));check(guard.held()&&SDL_GetAudioDeviceStatus(device)==SDL_AUDIO_PAUSED);
 check(!resumeConstructionAudioDevice(e));auto stopped=callbacks.load();SDL_Delay(30);check(callbacks.load()==stopped);auto commands=suppressedAudioConstructionCommands();check(pc_midday_audio_command_suppressed()&&suppressedAudioConstructionCommands()==commands+1);
 AudioConstructionFence nested;check(!nested.begin(e));check(!unregisterConstructionAudioDevice(e));
 bool wrongBegin=true,wrongRelease=true;std::thread worker([&]{std::string error;AudioConstructionFence foreign;wrongBegin=foreign.begin(error);wrongRelease=guard.release(false,error);});worker.join();check(!wrongBegin&&!wrongRelease&&guard.held());
 check(guard.release(false,e));check(!guard.held()&&!pc_midday_audio_command_suppressed());for(unsigned i=0;i<100&&callbacks.load()==stopped;++i)SDL_Delay(2);check(callbacks.load()>stopped);
 // Existing paused state is preserved, including destructor rollback.
 SDL_PauseAudioDevice(device,1);{AudioConstructionFence paused;check(paused.begin(e));}check(SDL_GetAudioDeviceStatus(device)==SDL_AUDIO_PAUSED);
 SDL_PauseAudioDevice(device,0);check(guard.begin(e));check(guard.release(true,e)&&SDL_GetAudioDeviceStatus(device)==SDL_AUDIO_PAUSED);
 bool foreignResume=true;std::thread resumeWorker([&]{std::string x;foreignResume=resumeConstructionAudioDevice(x);});resumeWorker.join();check(!foreignResume);
 stopped=callbacks.load();check(resumeConstructionAudioDevice(e));for(unsigned i=0;i<100&&callbacks.load()==stopped;++i)SDL_Delay(2);check(callbacks.load()>stopped&&SDL_GetAudioDeviceStatus(device)==SDL_AUDIO_PLAYING);check(!resumeConstructionAudioDevice(e));
 check(unregisterConstructionAudioDevice(e));check(!guard.begin(e));SDL_CloseAudioDevice(device);SDL_Quit();std::cout<<checks<<" actual SDL construction audio fence controls PASS\n";return 0;
}
