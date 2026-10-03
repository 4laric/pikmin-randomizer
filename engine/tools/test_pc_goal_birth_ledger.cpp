#include "pc_goal_birth_ledger.h"
#include "pc_goal_population_accounting.h"
#include <cstdio>
#include <cstdlib>

static void check(bool ok,const char* why){if(!ok){std::fprintf(stderr,"FAIL %s\n",why);std::exit(1);}}
static PcGoalBirthLedger ready(){PcGoalBirthLedger l;l.begin();return l;}
int main(){
    PcGoalBirthLedger inert;
    inert.request(0,1,2,3,1,2,0,2);inert.birth(1,1,1,4,2,1,false);inert.refuse();
    check(!inert.armed && inert.complete && inert.eventCount==0,"ordinary unarmed inert");
    auto l=ready();l.request(10,1,2,0x31307270,1,2,0,2);
    check(!l.settled() && l.events[0].source==2 && l.events[0].model==0x31307270,"request not successful birth");
    l.birth(11,1,1,3,2,1,false);l.birth(12,1,1,0,1,0,true);
    check(l.settled() && l.emitted[1]==1 && l.stored[1]==1,"two real paths account separately");
    check(l.events[1].receipt==l.events[0].receipt && l.events[2].receipt==l.events[0].receipt,"source demand accounting closure");
    auto multi=ready();multi.request(2,1,2,3,1,1,0,1);multi.request(2,4,5,6,2,2,0,2);
    multi.birth(3,4,2,7,2,1,false);multi.birth(3,1,1,8,1,0,false);multi.birth(4,4,2,0,1,0,true);
    check(multi.settled() && multi.emitted[1]==1 && multi.emitted[2]==1 && multi.stored[2]==1,"distinct onions/colors");
    auto fifo=ready();fifo.request(1,1,2,3,1,1,0,1);fifo.request(2,1,4,5,1,2,1,3);
    fifo.birth(3,1,1,6,3,2,false);fifo.birth(4,1,1,7,2,1,false);fifo.birth(5,1,1,8,1,0,false);
    check(fifo.settled() && fifo.events[2].receipt==1 && fifo.events[3].receipt==2,"aggregate pending FIFO demand ledger");
    for(int failure=0;failure<10;++failure){
        auto bad=ready();bad.request(5,1,2,3,1,2,0,2);
        if(failure==0)bad.birth(6,1,1,4,1,0,false);
        if(failure==1)bad.birth(6,1,1,4,2,2,false);
        if(failure==2)bad.birth(6,1,2,4,2,1,false);
        if(failure==3)bad.birth(6,9,1,4,2,1,false);
        if(failure==4)bad.birth(4,1,1,4,2,1,false);
        if(failure==5)bad.birth(6,1,1,0,2,1,false);
        if(failure==6)bad.birth(6,1,1,4,2,1,true);
        if(failure==7)bad.request(6,1,3,4,1,1,0,1);
        if(failure==8)bad.bootBirth(6,1,1,4);
        if(failure==9)bad.refuse();
        check(!bad.complete && !bad.settled(),"unknown/incorrect/incomplete birth refuses");
        const auto old=bad.eventCount;bad.birth(7,1,1,4,2,1,false);
        check(!bad.complete && bad.eventCount==old,"failure sticky");
    }
    auto boot=ready();boot.bootBirth(5,1,0,2);
    check(boot.settled() && boot.bootEmitted[0]==1 && boot.emitted[0]==0,"boot separate from earned demand");
    auto overflow=ready();
    for(std::size_t i=0;i<PcGoalBirthLedger::Capacity;++i)overflow.bootBirth(i+1,1,1,i+2);
    overflow.bootBirth(200,1,1,500);
    check(!overflow.complete && overflow.eventCount==PcGoalBirthLedger::Capacity,"bounded overflow refuses");
    auto unknown=ready();unknown.birth(1,1,1,2,1,0,false);
    check(!unknown.complete,"birth without actual demand refuses");
    auto zero=ready();zero.request(1,1,2,3,1,0,0,0);
    check(zero.settled() && zero.emitted[1]==0 && zero.stored[1]==0,"zero demand is not a birth");
    auto rearmed=ready();rearmed.request(1,1,2,3,1,1,0,1);
    check(!rearmed.begin() && !rearmed.complete && rearmed.eventCount==1,"rearming cannot erase history");
    auto conversion=ready();conversion.violetConversion(10,1,2,3,4,1,2);
    check(conversion.settled() && conversion.conversionCount==1 && conversion.emitted[1]==0
        && conversion.conversions[0].inputSpecies==1 && conversion.conversions[0].inputMaturity==2,"replacement distinct from new birth");
    for(int failure=0;failure<6;++failure){
        auto bad=ready();bad.violetConversion(10,1,2,3,4,1,0);
        bad.violetConversion(failure==0?9:11,failure==1?0:1,failure==2?0:2,3,failure==3?3:4,
            failure==4?6:1,failure==5?3:0);
        check(!bad.complete && bad.conversionCount==1,"invalid replacement refuses");
    }
    auto world=ready();PcGoalPopulationCensus initial;initial.field[1][0]=20;
    PcGoalPopulationAccounting population;check(population.begin(initial,world),"initial full field stock sprouts census");
    world.request(1,1,2,3,1,2,0,2);world.birth(2,1,1,4,2,1,false);world.birth(3,1,1,0,1,0,true);
    world.violetConversion(4,5,6,7,8,1,0);
    PcGoalPopulationCensus acquiredCensus;acquiredCensus.field[1][0]=19;acquiredCensus.field[3][0]=1;
    acquiredCensus.heads[1][0]=1;acquiredCensus.stock[1][0]=1;
    check(population.closes(acquiredCensus,world,false),"actual emitted plus stored earned2 and replacement close22");
    check(!population.closes(acquiredCensus,world,true),"live heads and field cannot masquerade as stock-only save");
    PcGoalPopulationCensus saved;saved.stock[1][0]=21;saved.stock[3][0]=1;
    check(population.closes(saved,world,true),"saved22 complete successful earned births");
    auto wrong=saved;wrong.stock[1][0]=19;check(!population.closes(wrong,world,true),"strict20 cannot erase earned2");
    wrong=saved;wrong.stock[1][0]=22;check(!population.closes(wrong,world,true),"unearned extra actor refuses");
    auto pendingWorld=ready();PcGoalPopulationAccounting pendingPopulation;check(pendingPopulation.begin(initial,pendingWorld),"pending baseline");
    pendingWorld.request(1,1,2,3,1,2,0,2);pendingWorld.violetConversion(2,5,6,7,8,1,0);
    check(!pendingPopulation.closes(saved,pendingWorld,true),"requested seeds are not successful births");
    auto missing=world;missing.conversionCount=0;check(!population.closes(saved,missing,true),"typed actual1to1 conversion required");
    auto badInitial=initial;badInitial.heads[0][0]=1;PcGoalPopulationAccounting unsupported;
    check(!unsupported.begin(badInitial,ready()),"initial foreign sprout not ignored");
    badInitial=initial;badInitial.stock[2][0]=1;check(!unsupported.begin(badInitial,ready()),"initial unknown stock not ignored");
    std::puts("PC_GOAL_BIRTH_LEDGER_PASS");
}
