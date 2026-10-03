#include "pc_p2_original_piki_spawn.h"
#include <cmath>
#include <cstdio>
#include <limits>
#include <stdexcept>
#include <vector>
using namespace p2original;
namespace {
unsigned checks=0;
void check(bool x){++checks;if(!x)throw std::runtime_error("original Piki spawn control failed");}
struct Provider:PikiSpawnProvider{
    bool prepared=true;unsigned prepares=0,draws=0,births=0;std::uint32_t preparedUid=999;
    std::vector<char> order;std::vector<std::array<float,3>> positions;
    PikiBirthResult result=PikiBirthResult::Born;float draw=.25f;int failAt=-1;
    bool prepare(const PikiSpawnRecord& row,std::string& e)override{++prepares;preparedUid=row.uid;if(!prepared)e="preflight";return prepared;}
    float randomUnit()override{++draws;order.push_back('D');return draw;}
    PikiBirthResult birth(std::uint32_t attempt,const std::array<float,3>& p,bool,std::string& e)override{
        ++births;check(attempt==births-1);order.push_back('B');positions.push_back(p);
        if(int(attempt)==failAt){e="physical failure";return PikiBirthResult::Failed;}return result;
    }
};
PikiSpawnRecord record(){PikiSpawnRecord r;r.uid=1;r.count=3;r.species=1;r.position={{10,20,30}};r.offset={{1,2,3}};return r;}
void run(){
    std::string e;PikiSpawnProgress progress;progress.allowDebug=true;PikiSpawnResult out;auto r=record();
    Provider p;check(spawnOriginalPiki(r,progress,p,out,e));check(out.born==3&&out.attempts==3);check(p.order==std::vector<char>({'D','D','B','D','D','B','D','D','B'}));
    check(p.positions[0][1]==22);check(std::fabs(p.positions[0][0]-13.5f)<.0001f);check(std::fabs(p.positions[0][2]-33)<.0001f);
    auto zero=record();zero.uid=0;Provider zeroProvider;
    check(spawnOriginalPiki(zero,progress,zeroProvider,out,e));
    check(zeroProvider.preparedUid==0&&out.born==3);
    for(int species=0;species<=5;++species){
        r=record();r.species=species;r.wildParameter=1;Provider q;PikiSpawnProgress pg;
        check(spawnOriginalPiki(r,pg,q,out,e));check(q.draws==6);
        check(out.born==(species==5?0u:3u));check(out.policySkipped==(species==5?3u:0u));
        if(species==2)check(q.positions[0]==std::array<float,3>({11,22,33}));
        if(species<5){pg.met=std::uint8_t(1u<<species);Provider met;check(spawnOriginalPiki(r,pg,met,out,e));check(met.draws==6&&met.births==0&&out.policySkipped==3);}
        if(species<3){pg.met=0;pg.boot=std::uint8_t(1u<<species);Provider boot;check(spawnOriginalPiki(r,pg,boot,out,e));check(boot.draws==6&&boot.births==0);}
    }
    r=record();r.wildParameter=2;Provider disabled;PikiSpawnProgress noDebug;
    check(spawnOriginalPiki(r,noDebug,disabled,out,e));check(disabled.draws==6&&disabled.births==0);
    Provider full;full.result=PikiBirthResult::CapacitySkipped;check(spawnOriginalPiki(r,progress,full,out,e));check(out.capacitySkipped==3&&out.born==0&&full.draws==6);
    Provider fail;fail.failAt=1;check(!spawnOriginalPiki(r,progress,fail,out,e));check(out.attempts==2&&out.born==1&&fail.draws==4&&fail.births==2);
    Provider refuse;refuse.prepared=false;out.born=987;check(!spawnOriginalPiki(r,progress,refuse,out,e));check(refuse.draws==0&&refuse.births==0&&out.born==987);
    for(unsigned invalid=0;invalid<5;++invalid){
        auto bad=record();auto pg=progress;if(invalid==0)bad.species=6;if(invalid==1)pg.met=32;if(invalid==2)pg.boot=8;
        if(invalid==3)bad.position[1]=std::numeric_limits<float>::infinity();
        if(invalid==4)bad.count=65536;
        Provider q;check(!spawnOriginalPiki(bad,pg,q,out,e));check(q.prepares==0&&q.draws==0);
    }
    Provider nan;nan.draw=std::numeric_limits<float>::quiet_NaN();check(!spawnOriginalPiki(r,progress,nan,out,e));check(nan.draws==2&&nan.births==0&&out.attempts==1);
    r.count=0;Provider empty;check(spawnOriginalPiki(r,progress,empty,out,e));check(empty.prepares==1&&empty.draws==0&&out.attempts==0);
}
}
int main(){try{run();std::printf("PASS original Piki source spawn %u controls\n",checks);return 0;}catch(const std::exception& e){std::fprintf(stderr,"%s\n",e.what());return 1;}}
