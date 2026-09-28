#include "pc_p2_beasts_failure_policy.h"
#include <cassert>
#include <cstring>
#include <cstdio>
#include <initializer_list>
int main(){
    for(float health:{100.f,1.01f}){
        assert(!p2_beasts_failure_reason(true,3,health,true,false));
        assert(!p2_beasts_failure_reason(true,3,health,false,true));
        assert(std::strcmp(p2_beasts_failure_reason(true,3,health,false,false),"extinction")==0);
    }
    for(float health:{1.f,0.f,-1.f})for(bool piki:{false,true})for(bool sprout:{false,true})
        assert(std::strcmp(p2_beasts_failure_reason(true,3,health,piki,sprout),"knockout")==0);
    for(int floor:{0,1,2,4,5})assert(!p2_beasts_failure_reason(true,floor,0,false,false));
    assert(!p2_beasts_failure_reason(false,3,0,false,false));
    std::puts("PASS floor3 terminal policy: active/sprouts, extinction, knockout precedence, profile/floor guards");
}
