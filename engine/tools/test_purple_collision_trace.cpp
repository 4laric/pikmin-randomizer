#include "pc_purple_collision_trace.h"
#include "pc_purple_sdl_axis_policy.h"
#include <cstdlib>
#include <cstdio>
#include <limits>
#include <initializer_list>
static void check(bool ok, const char* why) { if (!ok) { std::fprintf(stderr,"FAIL %s\n",why);std::exit(1); } }
int main() {
    int captain=0, partner=0;
    for(int axis:{-8,8})check(pcPurpleSdlPulseSampleAxis(axis,8)==0,"exact default dead-zone boundary suppressed");
    for(int axis:{-9,9})check(pcPurpleSdlPulseSampleAxis(axis,8)==axis,"outside default boundary preserved");
    check(pcPurpleSdlPulseSampleAxis(-6,8)==0 && pcPurpleSdlPulseSampleAxis(64,8)==64,
        "captured command -6,64 samples actual 0,64");
    check(pcPurpleSdlPulseSampleAxis(-6,0)==-6,"zero dead-zone preserves captured minor axis");
    for(int deadZone:{0,3,8,12,64,127})for(int axis=-74;axis<=74;++axis) {
        const int sdlAxis=axis*256;
        const int sampled=std::abs(sdlAxis)>deadZone*256 ? sdlAxis/256 : 0;
        check(pcPurpleSdlPulseSampleAxis(axis,deadZone)==sampled,"native-unit model matches actual SDL sampling equation");
    }
    check(pcPurpleCollisionAcquisitionMode("sdl_acquire"),"direct acquisition mode captures typed evidence");
    check(pcPurpleCollisionAcquisitionMode("sdl_dayend"),"ordinary dayend acquisition captures typed evidence");
    const char* unrelatedModes[]={nullptr,"","sdl_health","sdl_resume","ordinary","sdl_acquire_extra"};
    for(const char* mode:unrelatedModes)
        check(!pcPurpleCollisionAcquisitionMode(mode),"unrelated modes remain inert");
    PcPurpleCollisionTraceWindow trace;
    check(!trace.take(&captain,true),"default inactive");
    trace.begin(false,true,&captain,1); check(!trace.take(&captain,true),"explicit flag required");
    trace.begin(true,false,&captain,2); check(!trace.take(&captain,true),"active pulse required");
    trace.begin(true,true,nullptr,3); check(!trace.take(nullptr,true),"actual captain required");
    trace.begin(true,true,&captain,4);
    check(!trace.take(&partner,true),"foreign actor refused");
    check(!trace.take(&captain,false),"unchanged force not logged");
    for(unsigned i=0;i<16;++i)check(trace.take(&captain,true),"per-tick capacity");
    trace.begin(true,true,&captain,4);check(!trace.take(&captain,true),"same tick cannot reset budget");
    trace.begin(true,true,&captain,5);check(trace.take(&captain,true),"new tick resets only per-tick count");
    trace.begin(true,true,&captain,3);check(!trace.take(&captain,true),"backward tick refused");
    check(trace.tick()==5,"backward tick cannot replace captured history");
    trace.begin(true,true,&captain,3);check(!trace.take(&captain,true),"repeated backward tick refused");
    for(unsigned tick=6;tick<150;++tick) { trace.begin(true,true,&captain,tick);for(unsigned i=0;i<16;++i)trace.take(&captain,true); }
    check(trace.sequence()==2048,"whole-process log bound");
    trace.begin(true,true,&captain,200);check(!trace.take(&captain,true),"global limit cannot reset");
    PcPurpleCollisionClosure closure;
    PcPurpleQueuedForce a{.00812473707f,0,.0027200568f},b{.0162494704f,0,.00544011313f};
    auto arm=[&](unsigned tick) { closure.begin(true,&captain,tick,tick+100,{}); };
    arm(1);closure.record(&captain,101,true,{},a);closure.record(&captain,101,true,a,b);
    check(closure.matches(&captain,1,101,b),"actual two-write collision closes exactly");
    check(!closure.matches(&partner,1,101,b),"foreign captain cannot consume evidence");
    check(!closure.matches(&captain,2,101,b),"stale fixture tick refused");
    check(!closure.matches(&captain,1,102,b),"stale authoritative tick refused");
    check(!closure.matches(&captain,1,101,a),"unexplained final force refused");
    arm(2);check(!closure.matches(&captain,2,102,{}),"empty trace is not provenance");
    closure.record(&captain,102,false,{},a);check(!closure.matches(&captain,2,102,a),"unowned or unsupported partner refused");
    arm(3);closure.record(&captain,103,true,a,b);check(!closure.matches(&captain,3,103,b),"intervening unobserved force refused");
    arm(4);closure.record(&captain,0,true,{},a);check(!closure.matches(&captain,4,104,a),"non-authoritative write refused");
    arm(5);closure.record(&captain,104,true,{},a);check(!closure.matches(&captain,5,105,a),"wrong write tick refused");
    arm(6);closure.record(&partner,106,true,{},a);check(!closure.matches(&captain,6,106,a),"foreign actor write not evidence");
    arm(7);PcPurpleQueuedForce last{};
    for(unsigned i=0;i<17;++i) { PcPurpleQueuedForce next{float(i+1),0,0};closure.record(&captain,107,true,last,next);last=next; }
    check(!closure.matches(&captain,7,107,last),"overflow cannot certify incomplete trace");
    arm(8);closure.record(&captain,108,true,{},a);arm(8);
    closure.record(&captain,108,true,{},a);check(!closure.matches(&captain,8,108,a),"same tick cannot reset closure");
    arm(9);closure.record(&captain,109,true,{},a);arm(8);
    check(!closure.matches(&captain,9,109,a),"backward context invalidates closure");
    closure.begin(false,&captain,10,110,{});closure.record(&captain,110,true,{},a);
    check(!closure.watches(&captain)&&!closure.matches(&captain,10,110,a),"ordinary inactive context inert");
    closure.begin(true,&captain,11,111,a);closure.record(&captain,111,true,a,b);
    check(!closure.matches(&captain,11,111,b),"unproven queued input force refused");
    arm(12);closure.record(&captain,112,true,{}, {std::numeric_limits<float>::quiet_NaN(),0,0});
    check(!closure.matches(&captain,12,112,a),"nonfinite force refused");
    closure.beginIdle(true,&captain,13,112,{});closure.record(&captain,113,true,{},a);
    closure.beginIdle(true,&captain,14,113,a);closure.record(&captain,114,true,{},b);
    check(closure.matches(&captain,14,114,b),"previous proven queue consumed then fresh owned collision qualifies");
    closure.beginIdle(true,&captain,15,114,b);closure.record(&captain,115,true,b,a);
    check(!closure.matches(&captain,15,115,a),"uncleared preceding queue refused");
    closure.beginIdle(true,&captain,16,115,a);closure.record(&captain,116,true,{},b);
    check(!closure.matches(&captain,16,116,b),"unproven initial queue cannot qualify fresh collision");
    closure.beginIdle(true,&captain,17,116,{});closure.record(&captain,117,true,{},a);
    closure.beginIdle(true,&captain,19,117,a);closure.record(&captain,118,true,{},b);
    check(!closure.matches(&captain,19,118,b),"skipped fixture tick cannot reuse initial queue");
    std::puts("Purple collision trace controls PASS");
}
