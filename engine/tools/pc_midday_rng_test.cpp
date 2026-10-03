#include "netplay/pc_sim_rng.h"
#include "netplay/pc_netplay_det.h"
#include <iostream>
#include <stdexcept>
#include <thread>
#include <vector>
#include <cstring>
int n=0;
void check(bool b,const char* w){++n;if(!b)throw std::runtime_error(w);}
int main(int argc,char** argv){try{
    char executable[]="profile-test";char* args[]={executable};pc_netplay_det_init(1,args);
    std::string e;PcSimRngCheckpoint saved;
    if(argc>1&&std::strcmp(argv[1],"legacy")==0){
        std::srand(123);int a=std::rand(),b=std::rand();std::srand(123);
        check(pc_sim_rand()==a&&pc_cosmetic_rand()==b,"default libc values/call order");
        check(!pc_sim_rng_begin_offline(1,2,e),"late conversion refused");
        std::srand(77);const float expectedFloat=10.0f*(float(std::rand())/float(RAND_MAX));std::srand(77);
        check(pc_sim_rng_denominator()==float(RAND_MAX)&&pc_sim_randf(10)==expectedFloat,"legacy float shaping and one libc draw preserved");
        saved.simState=777;check(!pc_sim_rng_capture(saved,e)&&saved.simState==777,"legacy export refuses without mutation");
    }else{
        bool netplay=argc>1&&std::strcmp(argv[1],"netplay")==0;
        if(netplay){pc_netplay_det_force_on();pc_sim_srand(7);pc_cosmetic_srand(9);check(!pc_sim_rng_begin_offline(7,9,e),"netplay cannot switch offline");}
        else{check(pc_sim_rng_begin_offline(7,9,e),"portable bootstrap");check(!pc_sim_rng_begin_offline(7,9,e),"duplicate bootstrap refused");}
        const float denominator=netplay?float(RAND_MAX):32767.0f;
        pc_sim_rng_set_state(7);pc_cosmetic_rng_set_state(9);
        unsigned sim=7,cos=9;sim=sim*1103515245u+12345u;cos=cos*1103515245u+12345u;
        check(pc_sim_rng_denominator()==denominator,"explicit profile denominator");
        const float expectedSim=10.0f*(float((sim>>16)&0x7fffu)/denominator);
        const float expectedCos=10.0f*(float((cos>>16)&0x7fffu)/denominator);
        check(pc_sim_randf(10)==expectedSim&&pc_cosmetic_randf(10)==expectedCos,"both profile float shapers exact one-draw values");
        check(expectedSim>=0&&expectedSim<=10&&expectedCos>=0&&expectedCos<=10,"float shaper bounded physical magnitude");
        if(!netplay){pc_sim_rng_set_state(7);pc_cosmetic_rng_set_state(9);float highest=0;for(int i=0;i<1024;++i){float value=pc_sim_randf(10);if(value>highest)highest=value;}check(highest>9.5f&&highest<=10,"portable full-scale floats independent of libc RAND_MAX");pc_sim_rng_set_state(7);pc_cosmetic_rng_set_state(9);pc_sim_randf(10);pc_cosmetic_randf(10);}
check(pc_sim_rng_capture(saved,e),"typed RNG capture");
        check(saved.profile==(netplay?2u:1u)&&saved.simDraws==1&&saved.cosmeticDraws==1,"profile and both stream counts");
        std::vector<int> expected;for(int i=0;i<20;++i){expected.push_back(pc_sim_rand());expected.push_back(pc_cosmetic_rand());}
        check(!pc_sim_rng_apply(saved,e),"apply outside staged suppression refused");
        check(pc_sim_rng_constructor_suppression(true,e),"constructor fence");
        const auto before=pc_sim_rng_state(),cosBefore=pc_cosmetic_rng_state();
        for(int i=0;i<20;++i){pc_sim_rand();pc_cosmetic_rand();pc_sim_srand(999);pc_cosmetic_srand(999);}
        check(before==pc_sim_rng_state()&&cosBefore==pc_cosmetic_rng_state(),"constructor draws/seeds do not advance saved streams");
        PcSimRngCheckpoint untouched;untouched.simState=888;check(!pc_sim_rng_capture(untouched,e)&&untouched.simState==888,"capture during staging refuses atomically");
        for(int fault=0;fault<4;++fault){auto bad=saved;if(fault==0)bad.version=2;if(fault==1)bad.profile=99;if(fault==2)bad.simDraws=UINT64_MAX;if(fault==3)bad.cosmeticDraws=UINT64_MAX;
            check(!pc_sim_rng_apply(bad,e)&&pc_sim_rng_state()==before&&pc_cosmetic_rng_state()==cosBefore,"malformed checkpoint does not partially change streams");}
        bool foreignApplied=true;std::thread foreign([&]{std::string err;foreignApplied=pc_sim_rng_apply(saved,err);});foreign.join();check(!foreignApplied,"foreign-thread apply refuses");
        check(pc_sim_rng_apply(saved,e),"both named stream states restored");
        check(pc_sim_rng_constructor_suppression(false,e),"constructor fence ends");
        std::vector<int> actual;for(int i=0;i<20;++i){actual.push_back(pc_sim_rand());actual.push_back(pc_cosmetic_rand());}
        check(actual==expected,"future simulation and cosmetic draws equal checkpoint continuation");
        auto same=saved;check(pc_sim_rng_capture(same,e)&&same.simDraws==21&&same.cosmeticDraws==21,"restored counters continue");
        std::thread wrong([]{pc_sim_rand();});wrong.join();
        check(!pc_sim_rng_capture(same,e),"non-owner draw disables checkpoint instead of silently persisting raced state");
    }
    std::cout<<"PASS "<<n<<" actual RNG profile controls\n";return 0;
}catch(const std::exception& x){std::cerr<<"FAIL "<<n<<": "<<x.what()<<"\n";return 1;}}
