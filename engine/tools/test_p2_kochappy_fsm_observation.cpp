#include "pc_p2_kochappy_fsm.h"
#include <cstdio>
#include <limits>
#define CHECK(x) do {if(!(x)){std::fprintf(stderr,"FSM observation check failed: %s line%d\n",#x,__LINE__);return 1;}}while(false)
int main(){
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
