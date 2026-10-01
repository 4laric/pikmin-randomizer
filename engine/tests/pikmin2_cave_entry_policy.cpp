#include "pc_p2_cave_entry_policy.h"
#include <cassert>
#include <cstdio>
int main(){
    const std::string old(32,'a'),token(64,'b');
    assert(p2_cave_entry_profile("P2_CAVE_ENTRY_1",1,old)==P2CaveEntryProfile::Tutorial);
    assert(p2_cave_entry_profile("P2_CAVE_ENTRY_1",2,old)==P2CaveEntryProfile::Tutorial);
    assert(p2_cave_entry_profile("P2_BEASTS_ENTRY_1",2,token)==P2CaveEntryProfile::BeastsFloor2);
    assert(p2_cave_entry_profile("P2_BEASTS_FLOOR3_ENTRY_1",3,token)==P2CaveEntryProfile::BeastsFloor3);
    assert(p2_cave_entry_profile("P2_BEASTS_FLOOR4_ENTRY_1",4,token)==P2CaveEntryProfile::BeastsFloor4);
    for(int floor:{0,1,2,3,5})assert(p2_cave_entry_profile("P2_BEASTS_FLOOR4_ENTRY_1",floor,token)==P2CaveEntryProfile::Invalid);
    for(const std::string& invalid:{old,std::string(63,'a'),std::string(65,'a'),std::string(64,'A'),std::string(64,'g')})
        assert(p2_cave_entry_profile("P2_BEASTS_FLOOR4_ENTRY_1",4,invalid)==P2CaveEntryProfile::Invalid);
    for(const char* version:{"P2_CAVE_ENTRY_1","P2_BEASTS_ENTRY_1","P2_BEASTS_FLOOR3_ENTRY_1"}){
        for(int floor:{0,4,5})assert(p2_cave_entry_profile(version,floor,token)==P2CaveEntryProfile::Invalid);
        for(const std::string& invalid:{std::string(),std::string(63,'a'),std::string(65,'a'),std::string(64,'A'),std::string(64,'g')})
            assert(p2_cave_entry_profile(version,3,invalid)==P2CaveEntryProfile::Invalid);
    }
    assert(p2_cave_entry_profile("P2_CAVE_ENTRY_1",3,old)==P2CaveEntryProfile::Invalid);
    assert(p2_cave_entry_profile("P2_BEASTS_ENTRY_1",3,token)==P2CaveEntryProfile::Invalid);
    assert(p2_cave_entry_profile("P2_BEASTS_FLOOR3_ENTRY_1",2,token)==P2CaveEntryProfile::Invalid);
    assert(p2_cave_entry_profile("P2_BEASTS_FLOOR3_ENTRY_1",3,old)==P2CaveEntryProfile::Invalid);
    assert(p2_cave_entry_profile("unknown",3,token)==P2CaveEntryProfile::Invalid);
    std::puts("PASS cave entry profiles: tutorial1/2, Beasts2/3/4, wrong-floor and token rejection");
}
