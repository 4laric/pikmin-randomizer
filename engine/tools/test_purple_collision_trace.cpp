#include "pc_purple_collision_trace.h"
#include <cstdlib>
#include <cstdio>
static void check(bool ok, const char* why) { if (!ok) { std::fprintf(stderr,"FAIL %s\n",why);std::exit(1); } }
int main() {
    int captain=0, partner=0;
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
    std::puts("Purple collision trace controls PASS");
}
