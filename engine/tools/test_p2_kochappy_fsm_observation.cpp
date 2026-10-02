#include "pc_p2_kochappy_fsm.h"
#include "pc_kochappy_gather_input.h"
#include <cstdio>
#include <limits>
#define CHECK(x) do {if(!(x)){std::fprintf(stderr,"FSM observation check failed: %s line%d\n",#x,__LINE__);return 1;}}while(false)
int main(){
 using G=PcKochappyGatherInput;
 CHECK(pc_kochappy_gather_input(240,100,90,.1f,.65f)==G::Walk); // actual stalled target outside coverage
 CHECK(pc_kochappy_gather_input(145,100,90,.1f,.65f)==G::Cursor);
 CHECK(pc_kochappy_gather_input(145.01f,100,90,.1f,.65f)==G::Walk);
 CHECK(pc_kochappy_gather_input(0,100,90,.1f,.65f)==G::Cursor);
 CHECK(pc_kochappy_gather_input(200,150,120,.1f,.65f)==G::Cursor); // loaded radii, no hardcoded90
 CHECK(pc_kochappy_gather_input(240,100,90,.1f,65.f/74.f)==G::Refuse);
 CHECK(pc_kochappy_gather_input(240,100,90,22.f/74.f,.65f)==G::Refuse);
 CHECK(pc_kochappy_gather_input(240,100,90,.1f,.2f)==G::Refuse);
 CHECK(pc_kochappy_gather_input(-1,100,90,.1f,.65f)==G::Refuse);
 CHECK(pc_kochappy_gather_input(240,20,90,.1f,.65f)==G::Refuse);
 CHECK(pc_kochappy_gather_input(240,100,0,.1f,.65f)==G::Refuse);
 const float nan=std::numeric_limits<float>::quiet_NaN();
 for(int i=0;i<5;++i){float v[5]={240,100,90,.1f,.65f};v[i]=nan;
  CHECK(pc_kochappy_gather_input(v[0],v[1],v[2],v[3],v[4])==G::Refuse);}
 PcKochappyFsmSnapshot paused;paused.available=true;paused.stunPaused=true;paused.state=3;paused.stateTime=.75f;paused.attackFired=true;
 CHECK(pc_kochappy_overlay_preserved(paused,paused));
 for(int i=0;i<8;++i){auto bad=paused;
  switch(i){case 0:bad.available=false;break;case 1:bad.stunPaused=false;break;case 2:bad.state=4;break;
   case 3:bad.stateTime+=.01f;break;case 4:bad.attackFired=false;break;case 5:bad.swallowFired=true;break;
   case 6:bad.flickFired=true;break;case 7:bad.terminal=true;break;}
  CHECK(!pc_kochappy_overlay_preserved(paused,bad));
 }
 auto now=paused;now.stunPaused=false;
 CHECK(!pc_kochappy_clock_resumed(paused,now));
 now.stateTime+=.01f;CHECK(pc_kochappy_clock_resumed(paused,now));
 now.stateTime=0;now.state=4;CHECK(pc_kochappy_clock_resumed(paused,now)); // natural transition resets clock
 now.terminal=true;CHECK(!pc_kochappy_clock_resumed(paused,now));
 now=paused;now.stateTime=std::numeric_limits<float>::quiet_NaN();
 CHECK(!pc_kochappy_overlay_preserved(paused,now));CHECK(!pc_kochappy_clock_resumed(paused,now));
 now=paused;now.available=false;CHECK(!pc_kochappy_clock_resumed(paused,now));
 std::puts("P2_KOCHAPPY_FSM_OBSERVATION_POLICY_PASS actual_FSM_runtime=unexecuted");
}
