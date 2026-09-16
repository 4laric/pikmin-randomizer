#include "pc_p2_motion_events.h"
#include <fstream>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
static void check(bool ok){if(!ok)throw std::runtime_error("event table check failed");}
static unsigned inspect(const p2retail::Table& table){
 unsigned count=0;
 for(const auto& motion:table.motions) for(const auto& event:motion.events){
  check(!p2retail::due(event,event.frame));check(!p2retail::due(event,event.frame+.999));
  check(p2retail::due(event,event.frame+1.));++count;
 }
 return count;
}
int main(int argc,char** argv){
 const std::string sha(64,'a');
 const std::string good="P2_RETAIL_EVENTS_1 "+sha+" 1\na.bca 10 2 "+sha+" 3\n0 0\n5 2\n9 1\n";
 std::istringstream input(good);check(inspect(p2retail::read(input))==3);
 for(const auto& bad:std::vector<std::string>{good+"junk",good.substr(0,good.size()-3),
       "P2_RETAIL_EVENTS_1 "+sha+" 257", "P2_RETAIL_EVENTS_1 bad 1",
       "P2_RETAIL_EVENTS_1 "+sha+" 1\na.bca 10 2 "+sha+" 1\n0 1\n",
       "P2_RETAIL_EVENTS_1 "+sha+" 1\na.bca 10 2 "+sha+" 1\n10 2\n"}){
  bool rejected=false;try{std::istringstream raw(bad);p2retail::read(raw);}catch(const std::runtime_error&){rejected=true;}
  check(rejected);
 }
 check(!p2retail::due({0,2},std::numeric_limits<double>::quiet_NaN()));
 for(int i=1;i<argc;++i){std::ifstream file(argv[i]);auto table=p2retail::read(file);
  std::cout<<table.motions.size()<<" clips "<<inspect(table)<<" events\n";}
 std::cout<<"PASS retail event tables\n";
}
