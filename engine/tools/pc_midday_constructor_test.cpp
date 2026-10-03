#include "pc_midday_constructor.h"
#include "pc_randomizer.h"
#include "netplay/pc_netplay_randstate.h"
#define SDL_MAIN_HANDLED
#include <SDL.h>
#include <atomic>
#include <thread>
#include <cstdlib>
#include <iostream>
#include <filesystem>
#include <fstream>
#include <cstring>
#ifdef _WIN32
#include <process.h>
#else
#include <unistd.h>
#endif
using namespace pc_midday;
std::atomic<unsigned> callbacks{0};int checks=0;
void check(bool ok){++checks;if(!ok){std::cerr<<"constructor50 check "<<checks<<" failed\n";std::exit(1);}}
void callback(void*,Uint8*p,int n){std::memset(p,0,size_t(n));callbacks.fetch_add(1);}
bool same(const PcSimRngCheckpoint&a,const PcSimRngCheckpoint&b){return a.version==b.version&&a.profile==b.profile&&a.simState==b.simState&&a.cosmeticState==b.cosmeticState&&a.simDraws==b.simDraws&&a.cosmeticDraws==b.cosmeticDraws;}
int main(int argc,char**argv){
 check(argc==2);namespace fs=std::filesystem;
#ifdef _WIN32
 auto pid=_getpid();
#else
 auto pid=getpid();
#endif
 auto root=fs::path(argv[1])/("constructor50-"+std::to_string(pid));check(!fs::exists(root));fs::create_directories(root/"sess"/"runs"/"fixture");fs::create_directories(root/"sess"/"campaign");auto run=root/"sess"/"runs"/"fixture";
 const std::string token(64,'1'),fingerprint(64,'2');
 {std::ofstream f(run/"bootstrap.txt");f<<"PIKMIN_RANDOMIZER 9\nSESSION "<<token<<"\nFINGERPRINT "<<fingerprint<<"\nPROFILE foh-day2\nCATALOG gameplay-checks-v9\nPLACEMENT identity-v1\nGOAL emperor25\nDAYS repeat-day29-v1\nCOLOR red\nCHECKSET 6\nENEMIES 0\nBENEFITS 1\nDEATHLINK 1\nEND\n";check(bool(f));}
 std::string seed=(run/"bootstrap.txt").string();char program[]="constructor50",flag[]="--randomizer-seed";char*args[]={program,flag,seed.data()};check(pc_randomizer_init(3,args));pc_randstate::PcRandState net;check(pc_randomizer_get_net_state(&net));net.ready=1;net.gen=1;check(pc_randomizer_apply_net_state(net)&&pc_randomizer_ready());
 SDL_SetMainReady();SDL_setenv("SDL_AUDIODRIVER","dummy",1);check(SDL_Init(SDL_INIT_AUDIO)==0);std::string e;
 SDL_AudioSpec spec{};spec.freq=48000;spec.format=AUDIO_S16SYS;spec.channels=2;spec.samples=256;spec.callback=callback;
 auto device=SDL_OpenAudioDevice(nullptr,0,&spec,nullptr,0);check(device!=0&&registerConstructionAudioDevice(device,e));SDL_PauseAudioDevice(device,0);
 pc_sim_rng_note_main_thread();ConstructorFence noProfile;check(!noProfile.begin(e));check(pc_sim_rng_begin_offline(123,456,e));PcSimRngCheckpoint before;check(pc_sim_rng_capture(before,e));
#if defined(PIKI_USE_JAUDIO) && PIKI_USE_JAUDIO
 // Portable RNG does not make native JAudio construction eligible. A failed
 // begin must leave all actual device, RNG and reward writer state untouched.
 ConstructorFence unsupported;auto rewardsBefore=suppressedConstructionRewards();
 check(!unsupported.begin(e)&&e=="native JAudio construction fence is not implemented");
 check(!unsupported.held()&&SDL_GetAudioDeviceStatus(device)==SDL_AUDIO_PLAYING);
 PcSimRngCheckpoint unchanged;check(pc_sim_rng_capture(unchanged,e)&&same(before,unchanged));
 check(!pc_midday_construction_rewards_suppressed()&&!pc_midday_audio_command_suppressed());
 check(suppressedConstructionRewards()==rewardsBefore);
 auto running=callbacks.load();for(unsigned i=0;i<100&&callbacks.load()==running;++i)SDL_Delay(2);check(callbacks.load()>running);
 check(!unsupported.applySavedRng(before,e)&&!unsupported.finish(false,e));
 check(pc_sim_rng_capture(unchanged,e)&&same(before,unchanged));
 const char*normalCheck="Pikmin: Positron Generator";pc_randomizer_check(normalCheck);
 check(pc_randomizer_checked(normalCheck)&&fs::exists(run/"checks.txt")&&suppressedConstructionRewards()==rewardsBefore);
 SDL_PauseAudioDevice(device,1);
 check(!unsupported.begin(e)&&!unsupported.held()&&SDL_GetAudioDeviceStatus(device)==SDL_AUDIO_PAUSED);
 check(pc_sim_rng_capture(unchanged,e)&&same(before,unchanged)&&!pc_midday_construction_rewards_suppressed());
 check(unregisterConstructionAudioDevice(e));SDL_CloseAudioDevice(device);SDL_Quit();
 std::cout<<checks<<" actual device/RNG/reward native JAudio refusal controls PASS\n";return 0;
#endif
 ConstructorFence fence;check(fence.begin(e));check(fence.held()&&SDL_GetAudioDeviceStatus(device)==SDL_AUDIO_PAUSED);auto n=callbacks.load();SDL_Delay(25);check(callbacks.load()==n);
 auto rewards=suppressedConstructionRewards();const char*name="Pikmin: Positron Generator";pc_randomizer_check(name);check(suppressedConstructionRewards()==rewards+1&&!pc_randomizer_checked(name)&&!fs::exists(run/"checks.txt"));
 int first=pc_sim_rand(),cosmetic=pc_cosmetic_rand();for(int i=0;i<8;++i)check(pc_sim_rand()==first&&pc_cosmetic_rand()==cosmetic);pc_sim_srand(999);pc_cosmetic_srand(888);check(pc_sim_rng_state()==before.simState&&pc_cosmetic_rng_state()==before.cosmeticState);
 ConstructorFence nested;check(!nested.begin(e));bool foreignBegin=true,foreignFinish=true;std::thread t([&]{std::string x;ConstructorFence other;foreignBegin=other.begin(x);foreignFinish=fence.finish(false,x);});t.join();check(!foreignBegin&&!foreignFinish&&fence.held());check(!fence.finish(true,e));
 auto saved=before;saved.simState=998;saved.cosmeticState=997;saved.simDraws=20;saved.cosmeticDraws=10;check(fence.applySavedRng(saved,e));check(fence.finish(false,e));PcSimRngCheckpoint after;check(pc_sim_rng_capture(after,e)&&same(before,after));check(SDL_GetAudioDeviceStatus(device)==SDL_AUDIO_PLAYING&&!pc_midday_construction_rewards_suppressed());
 // The exact same production check now journals normally after abort release.
 pc_randomizer_check(name);check(pc_randomizer_checked(name)&&fs::exists(run/"checks.txt"));
 {ConstructorFence temporary;check(temporary.begin(e));check(temporary.applySavedRng(saved,e));}check(pc_sim_rng_capture(after,e)&&same(before,after));
 check(fence.begin(e));auto invalid=saved;invalid.profile=2;check(!fence.applySavedRng(invalid,e));check(fence.applySavedRng(saved,e));check(fence.finish(true,e));check(SDL_GetAudioDeviceStatus(device)==SDL_AUDIO_PAUSED);check(pc_sim_rng_capture(after,e)&&same(saved,after));
 check(unregisterConstructionAudioDevice(e));SDL_CloseAudioDevice(device);SDL_Quit();std::cout<<checks<<" actual SDL/RNG/production randomizer writer constructor controls PASS\n";return 0;
}
