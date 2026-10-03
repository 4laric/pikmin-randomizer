#include "pc_midday_constructor.h"
#include <exception>
namespace pc_midday {
bool ConstructorFence::begin(std::string&e){
 if(held_||construction_detail::rewardsBlocked.load()){e="constructor fence already held";return false;}
 // RNG owner check happens before acquiring callback ownership. Only explicit
 // bootstrap-selected portable offline sessions are eligible for this feature.
 PcSimRngCheckpoint before;
 if(!pc_sim_rng_capture(before,e))return false;
 if(before.profile!=1){e="constructor fence requires portable offline RNG";return false;}
 if(!audio_.begin(e))return false;
 if(!pc_sim_rng_constructor_suppression(true,e)){
  std::string cleanup;if(!audio_.release(false,cleanup))std::terminate();return false;
 }
 before_=before;owner_=std::this_thread::get_id();held_=true;applied_=false;
 construction_detail::rewardsBlocked.store(true);e.clear();return true;
}
bool ConstructorFence::applySavedRng(const PcSimRngCheckpoint&saved,std::string&e){
 if(!held_||owner_!=std::this_thread::get_id()){e="saved RNG apply requires constructor owner";return false;}
 if(saved.profile!=1){e="saved RNG is not portable offline";return false;}
 if(!pc_sim_rng_apply(saved,e))return false;
 applied_=true;e.clear();return true;
}
bool ConstructorFence::finish(bool published,std::string&e){
 if(!held_||owner_!=std::this_thread::get_id()){e="constructor release requires actual owner";return false;}
 if(published&&!applied_){e="publication has not staged saved RNG";return false;}
 if(!published&&!pc_sim_rng_apply(before_,e))return false;
 if(!pc_sim_rng_constructor_suppression(false,e))return false;
 if(!audio_.release(published,e)){
  // Do not reopen reward writers after a violated callback lifecycle. The caller
  // must abandon the stopped engine; destructor failure is explicit fail-closed.
  std::string cleanup;pc_sim_rng_constructor_suppression(true,cleanup);return false;
 }
 construction_detail::rewardsBlocked.store(false);held_=false;applied_=false;e.clear();return true;
}
ConstructorFence::~ConstructorFence(){if(held_){std::string e;if(!finish(false,e))std::terminate();}}
}
