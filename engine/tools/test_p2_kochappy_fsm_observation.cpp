#include "pc_p2_kochappy_fsm.h"
#include "pc_kochappy_gather_input.h"
#include <cstdio>
#include <initializer_list>
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
 double spans[4]={300,40,80,1};
 CHECK(pc_kochappy_route_reentry(spans,4,3)==1); // closest future point3 excluded
 CHECK(pc_kochappy_route_reentry(spans,4,0)==-1);
 CHECK(pc_kochappy_route_reentry(nullptr,4,3)==-1);
 CHECK(pc_kochappy_route_reentry(spans,4,5)==-1);
 CHECK(pc_kochappy_route_reentry(spans,129,3)==-1);
 spans[0]=512;CHECK(pc_kochappy_route_reentry(spans,4,1)==-1);
 spans[0]=511.999;CHECK(pc_kochappy_route_reentry(spans,4,1)==0);
 spans[0]=-1;CHECK(pc_kochappy_route_reentry(spans,4,3)==-1);
 spans[0]=std::numeric_limits<double>::infinity();CHECK(pc_kochappy_route_reentry(spans,4,3)==-1);
 spans[0]=300;spans[2]=nan;CHECK(pc_kochappy_route_reentry(spans,4,3)==-1);
 PcKochappyReentryProgress progress;
 CHECK(!progress.begin(0,0));CHECK(!progress.begin(30,30));
 CHECK(progress.begin(30,8)&&progress.retainedNext==30);
 CHECK(!progress.mayBegin(8)&&!progress.mayBegin(30));
 CHECK(progress.begin(31,9));CHECK(progress.begin(32,10));CHECK(progress.begin(33,11));
 CHECK(!progress.begin(34,12)&&progress.count==4); // finite total reentry budget
 using C=PcKochappyCatchupInput;
 PcKochappyRouteCatchup catchup;
 CHECK(!catchup.begin(-1)&&!catchup.begin(128));
 CHECK(catchup.begin(29)&&!catchup.begin(30));
 CHECK(catchup.observe(true,200,145,160)==C::Hold);
 CHECK(catchup.observe(true,145,145,0)==C::Hold);
 CHECK(catchup.observe(true,145,145,0)==C::Hold);
 CHECK(catchup.observe(true,145,145,0)==C::Continue&&!catchup.active);
 CHECK(catchup.observe(true,0,145,0)==C::Refuse); // no invented visited boundary
 CHECK(catchup.begin(0)); // legitimate replay after separately guarded reentry
 CHECK(catchup.observe(true,100,145,2)==C::Hold); // native residual motion remains observed
 CHECK(catchup.observe(false,100,145,0)==C::Refuse);
 for(int field=0;field<3;++field){PcKochappyRouteCatchup invalid;CHECK(invalid.begin(0));
  float v[3]={200,145,0};v[field]=nan;
  CHECK(invalid.observe(true,v[0],v[1],v[2])==C::Refuse);
 }
 for(float limit:{0.f,-1.f,512.f}){PcKochappyRouteCatchup invalid;CHECK(invalid.begin(0));
  CHECK(invalid.observe(true,200,limit,0)==C::Refuse);}
 PcKochappyRouteCatchup stalled;CHECK(stalled.begin(1));
 for(int i=0;i<90;++i)CHECK(stalled.observe(true,200,145,0)==C::Hold);
 CHECK(stalled.observe(true,200,145,0)==C::Refuse);
 PcKochappyRouteCatchup improving;CHECK(improving.begin(1));
 for(int i=0;i<179;++i)CHECK(improving.observe(true,1000.f-i*2,145,0)==C::Hold);
 CHECK(improving.observe(true,642,145,0)==C::Refuse); // hard180 even with progress
 PcKochappyRouteCatchup unstable;CHECK(unstable.begin(1));
 CHECK(unstable.observe(true,140,145,0)==C::Hold);
 CHECK(unstable.observe(true,146,145,0)==C::Hold&&unstable.stable==0);
 CHECK(unstable.observe(true,140,145,0)==C::Hold);
 CHECK(unstable.observe(true,140,145,0)==C::Hold);
 CHECK(unstable.observe(true,140,145,0)==C::Continue);
 // A native Formation slot may be 181 units from the captain. Completion
 // concerns its own target's 30-unit flat walking rest zone, not recruitment.
 PcKochappyRouteCatchup formation;CHECK(formation.begin(1));
 CHECK(formation.observe(true,40,30,0)==C::Hold);
 CHECK(formation.observe(true,30,30,0)==C::Hold);
 CHECK(formation.observe(true,30.001f,30,0)==C::Hold&&formation.stable==0);
 CHECK(formation.observe(true,30,30,0)==C::Hold);
 CHECK(formation.observe(true,29,30,0)==C::Hold);
 CHECK(formation.observe(true,28,30,0)==C::Continue);
 PcKochappyRouteCatchup formationStalled;CHECK(formationStalled.begin(1));
 for(int i=0;i<90;++i)CHECK(formationStalled.observe(true,35,30,0)==C::Hold);
 CHECK(formationStalled.observe(true,35,30,0)==C::Refuse);
 // Modern neutral Crowd completion is strictly below60 and actually Formed.
 const float crowdLimit=std::nextafter(60.f,0.f);
 PcKochappyRouteCatchup crowd;CHECK(crowd.begin(0));
 CHECK(crowd.observe(true,crowdLimit,crowdLimit,0,false)==C::Hold&&crowd.stable==0);
 CHECK(crowd.observe(true,crowdLimit,crowdLimit,0,true)==C::Hold&&crowd.stable==1);
 CHECK(crowd.observe(true,60.f,crowdLimit,0,true)==C::Hold&&crowd.stable==0);
 CHECK(crowd.observe(true,59.f,crowdLimit,0,true)==C::Hold);
 CHECK(crowd.observe(true,59.f,crowdLimit,0,false)==C::Hold&&crowd.stable==0);
 CHECK(crowd.observe(true,crowdLimit,crowdLimit,0,true)==C::Hold);
 CHECK(crowd.observe(true,59.f,crowdLimit,0,true)==C::Hold);
 CHECK(crowd.observe(true,59.f,crowdLimit,0,true)==C::Continue);
 PcKochappyCrowdObservation owned;
 owned.actionOwner=owned.plateOwner=owned.slotsAvailable=owned.occupantOwner=owned.listenerOwner=owned.finiteGeometry=owned.neutral=true;
 owned.state=1;owned.slot=19;owned.used=20;owned.capacity=110;
 CHECK(owned.valid()&&owned.settled());
 auto initial=owned;initial.state=0;CHECK(initial.valid()&&!initial.settled());
 for(int i=0;i<16;++i){if(i==6||i==7)continue;auto bad=owned;
  switch(i){case 0:bad.actionOwner=false;break;case 1:bad.plateOwner=false;break;
   case 2:bad.slotsAvailable=false;break;case 3:bad.occupantOwner=false;break;
   case 4:bad.listenerOwner=false;break;case 5:bad.finiteGeometry=false;break;
   case 6:bad.tripping=true;break;case 7:bad.route=true;break;case 8:bad.state=2;break;
   case 9:bad.state=-1;break;case 10:bad.slot=-1;break;case 11:bad.slot=20;break;
   case 12:bad.used=111;break;case 13:bad.capacity=0;break;case 14:bad.used=0;break;
   case 15:bad.slot=110;break;}
  CHECK(!bad.valid()&&!bad.settled());
 }
 for(int i=0;i<2;++i){auto transient=owned;if(i==0)transient.tripping=true;else transient.route=true;
  CHECK(transient.valid()&&!transient.settled());
  PcKochappyRouteCatchup wait;CHECK(wait.begin(0));
  CHECK(wait.observe(true,59,crowdLimit,0,true)==C::Hold&&wait.stable==1);
  CHECK(wait.observe(true,59,crowdLimit,0,transient.settled())==C::Hold&&wait.stable==0);
 }
 auto nonneutral=owned;nonneutral.neutral=false;CHECK(nonneutral.valid()&&!nonneutral.settled());
 // Actual input is consumed on the following native idle. Do not infer
 // readiness from issuing a neutral command before observing neutral state.
 PcKochappyRouteCatchup neutralCadence;CHECK(neutralCadence.begin(0));
 auto previousInput=owned;previousInput.neutral=false;
 CHECK(neutralCadence.observe(true,10,crowdLimit,0,previousInput.settled())==C::Hold&&neutralCadence.stable==0);
 for(int i=0;i<2;++i)CHECK(neutralCadence.observe(true,10,crowdLimit,0,owned.settled())==C::Hold);
 CHECK(neutralCadence.observe(true,10,crowdLimit,0,owned.settled())==C::Continue);
 PcKochappyRouteCatchup selfPreventing;CHECK(selfPreventing.begin(0));
 for(int i=0;i<90;++i)CHECK(selfPreventing.observe(true,10,crowdLimit,0,previousInput.settled())==C::Hold);
 CHECK(selfPreventing.observe(true,10,crowdLimit,0,previousInput.settled())==C::Refuse);
 PcKochappyRouteCatchup slopeBlocked;CHECK(slopeBlocked.begin(0));
 for(int i=0;i<90;++i)CHECK(slopeBlocked.observe(true,173,crowdLimit,0,owned.settled())==C::Hold);
 CHECK(slopeBlocked.observe(true,173,crowdLimit,0,owned.settled())==C::Refuse); // neutral does not waive real lag
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
