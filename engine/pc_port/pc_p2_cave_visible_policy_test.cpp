#include "pc_p2_cave_visible_policy.h"
#include <cstdio>
#include <cstdlib>
#include <limits>
static void check(bool value,const char* name){if(!value){std::fprintf(stderr,"FAIL %s\n",name);std::exit(1);}}
int main(){
    P2CaveVisibleBoundary b; b.present=b.ready=true;b.scene=1;b.seed=20;b.cave="forest_1";b.token="owned";b.radius=80;
    P2CaveVisibleInput input;
    check(!input.sample(b,0,0,0,true,true,true),"initial held input waits for release");
    input.sample(b,0,0,0,false,false,true);
    check(!input.sample(b,0,41,0,true,true,true),"vertical platform refuses");
    check(!input.sample(b,81,0,0,true,true,true),"distant captain refuses");
    check(!input.sample(b,0,0,0,true,true,false),"unsafe captain refuses");
    auto paused=b;paused.ready=false;
    check(!input.sample(paused,0,0,0,true,true,true),"provider not ready refuses");
    check(input.sample(b,0,0,0,true,true,true),"ordinary click activates");input.accepted();
    input.sample(b,0,0,0,false,false,true);
    check(!input.sample(b,0,0,0,true,true,true),"repeat click in same actor refuses");
    input.sample(b,101,0,0,false,false,true);
    check(input.sample(b,0,0,0,true,true,true),"leave release reentry activates");input.accepted();
    check(!input.sample(P2CaveVisibleBoundary{},0,0,0,false,false,true),"load gap refuses without clearing scene");
    auto next=b;next.scene=2;next.floor=1;next.returning=true;
    check(!input.sample(next,0,0,0,true,true,true),"held input across scene refuses");
    input.sample(next,0,0,0,false,false,true);
    check(!input.sample(next,0,0,0,true,true,true),"arrival inside actor waits for departure");
    input.sample(next,101,0,0,false,false,true);
    check(input.sample(next,0,0,0,true,true,true),"arrival depart and return activates");
    auto stale=next;stale.token="foreign";
    check(!next.same(stale),"foreign token differs");stale=next;stale.seed++;check(!next.same(stale),"foreign seed differs");
    stale=next;stale.x=std::numeric_limits<float>::quiet_NaN();check(!stale.valid(),"nan invalid");
    check(!next.near(0,std::numeric_limits<float>::infinity(),0),"nonfinite captain refuses");
    std::puts("P2_CAVE_VISIBLE_POLICY PASS");
}
