// Explicit resumable profiles; engine-free. State is serialized as named fields,
// never a memory image. Legacy default and existing main-thread MSL values remain.
#include "netplay/pc_sim_rng.h"
#include "netplay/pc_netplay_det.h"
#include <cstdio>
#include <thread>
#include <mutex>
#include <limits>
namespace {
std::mutex sMutex;
unsigned sSimState=1,sCosmeticState=0xC05E77u;
uint64_t sSimDraws=0,sCosmeticDraws=0;
std::thread::id sOwner;
bool sRecorded=false,sWarned=false,sLegacyDrawn=false,sPortable=false;
bool sSuppressed=false,sViolation=false;
unsigned next(unsigned& state){state=state*1103515245u+12345u;return(state>>16)&0x7fffu;}
uint32_t profile(){return pc_netplay_deterministic()?(sPortable?0u:2u):(sPortable?1u:0u);}
bool owner(){return sRecorded&&sOwner==std::this_thread::get_id();}
bool ready(std::string& e){
    if(!owner()){e="RNG checkpoint requires the recorded owner thread";return false;}
    if(!profile()){e="RNG profile is legacy or conflicting";return false;}
    if(sViolation){e="RNG profile observed a thread violation or draw overflow";return false;}
    return true;
}
int draw(bool cosmetic){
    std::lock_guard<std::mutex> lock(sMutex);
    if(!pc_netplay_deterministic()&&!sPortable){sLegacyDrawn=true;return std::rand();}
    if(!owner()){
        sViolation=true;
        if(!sWarned){sWarned=true;std::fprintf(stderr,"[checkpoint-rng] non-owner RNG draw; checkpoint disabled\n");}
        // Preserve existing netplay draw values, serialized to prevent a race.
        // New portable sessions fail closed rather than advance off-thread.
        if(sPortable||sSuppressed)return 0;
    }
    unsigned& state=cosmetic?sCosmeticState:sSimState;
    uint64_t& count=cosmetic?sCosmeticDraws:sSimDraws;
    if(sSuppressed){unsigned temporary=state;return static_cast<int>(next(temporary));}
    if(count==std::numeric_limits<uint64_t>::max()){sViolation=true;return 0;}
    ++count;return static_cast<int>(next(state));
}
void seed(bool cosmetic,unsigned value){
    std::lock_guard<std::mutex> lock(sMutex);
    if(sSuppressed){if(!owner())sViolation=true;return;}
    if(sPortable&&!owner()){sViolation=true;return;}
    (cosmetic?sCosmeticState:sSimState)=value;
    (cosmetic?sCosmeticDraws:sSimDraws)=0;
}
}
void pc_sim_rng_note_main_thread(){
    std::lock_guard<std::mutex> lock(sMutex);
    if(sRecorded&&!owner()){sViolation=true;return;}
    sOwner=std::this_thread::get_id();sRecorded=true;
}
int pc_sim_rand(){return draw(false);}
int pc_cosmetic_rand(){return draw(true);}
void pc_sim_srand(unsigned seedValue){seed(false,seedValue);}
void pc_cosmetic_srand(unsigned seedValue){seed(true,seedValue);}
void pc_sim_rng_set_state(unsigned value){seed(false,value);}
void pc_cosmetic_rng_set_state(unsigned value){seed(true,value);}
unsigned pc_sim_rng_state(){std::lock_guard<std::mutex> lock(sMutex);return sSimState;}
unsigned pc_cosmetic_rng_state(){std::lock_guard<std::mutex> lock(sMutex);return sCosmeticState;}
bool pc_sim_rng_begin_offline(unsigned sim,unsigned cosmetic,std::string& e){
    std::lock_guard<std::mutex> lock(sMutex);
    if(!owner()){e="portable RNG bootstrap requires recorded owner";return false;}
    if(sLegacyDrawn||sPortable||pc_netplay_deterministic()||sViolation||sSuppressed){e="portable RNG must start once before any legacy draw";return false;}
    sPortable=true;sSimState=sim;sCosmeticState=cosmetic;sSimDraws=sCosmeticDraws=0;e.clear();return true;
}
bool pc_sim_rng_capture(PcSimRngCheckpoint& out,std::string& e){
    std::lock_guard<std::mutex> lock(sMutex);
    if(!ready(e))return false;
    if(sSuppressed){e="RNG capture during constructor staging refused";return false;}
    if(sSimDraws==UINT64_MAX||sCosmeticDraws==UINT64_MAX){e="RNG draw counter exhausted";return false;}
    PcSimRngCheckpoint saved;saved.profile=profile();saved.simState=sSimState;saved.cosmeticState=sCosmeticState;saved.simDraws=sSimDraws;saved.cosmeticDraws=sCosmeticDraws;
    out=saved;e.clear();return true;
}
bool pc_sim_rng_constructor_suppression(bool enabled,std::string& e){
    std::lock_guard<std::mutex> lock(sMutex);
    if(!ready(e))return false;
    sSuppressed=enabled;e.clear();return true;
}
bool pc_sim_rng_apply(const PcSimRngCheckpoint& saved,std::string& e){
    std::lock_guard<std::mutex> lock(sMutex);
    if(!ready(e))return false;
    if(!sSuppressed){e="RNG apply requires constructor suppression";return false;}
    if(saved.version!=1||saved.profile!=profile()||saved.simDraws==UINT64_MAX||saved.cosmeticDraws==UINT64_MAX){e="RNG checkpoint version/profile/counter mismatch";return false;}
    sSimState=saved.simState;sCosmeticState=saved.cosmeticState;sSimDraws=saved.simDraws;sCosmeticDraws=saved.cosmeticDraws;e.clear();return true;
}

float pc_sim_rng_denominator(){
    std::lock_guard<std::mutex> lock(sMutex);
    return sPortable?32767.0f:float(RAND_MAX);
}
