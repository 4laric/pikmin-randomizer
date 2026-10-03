#pragma once
#include "pc_midday_audio_fence.h"
#include "netplay/pc_sim_rng.h"
#include "pc_midday_constructor_rewards.h"
#include <thread>
namespace pc_midday {
// Physical audio/RNG/reward barriers only. The scene owner must separately stop
// input/game updates and build an isolated unpublished world. No bool here proves
// those obligations or complete actor/global/resource coverage.
class ConstructorFence {
 AudioConstructionFence audio_;
 PcSimRngCheckpoint before_;
 std::thread::id owner_;
 bool held_=false,applied_=false;
public:
 ConstructorFence()=default;
 ConstructorFence(const ConstructorFence&)=delete;
 ConstructorFence&operator=(const ConstructorFence&)=delete;
 ~ConstructorFence();
 bool begin(std::string&);
 bool applySavedRng(const PcSimRngCheckpoint&,std::string&);
 // On abort discard staged roots before finish(false). On publication all other
 // world/audio fields must already be installed; finish(true) keeps SDL paused.
 bool finish(bool published,std::string&);
 bool held()const{return held_;}
};
}
