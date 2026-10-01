#include "pc_p2_economy.h"
#include <fstream>
static void bothAssign(Pellet* cargo){
    int count=0;Iterator all(pikiMgr);CI_LOOP(all){Piki* p=static_cast<Piki*>(*all);if(!p->isAlive())continue;
        require(p->mColor==Red && !pc_p2_is_purple(p),"both crew invalid");
        if(p->getStickObject()){
            std::printf("P2_BOTH_EXISTING_ATTACHMENT same_target=%d mode=%d action=%d\n",int(p->getStickObject()==cargo),int(p->mMode),int(p->mActiveAction->mCurrActionIdx));
            require(p->getStickObject()==cargo && p->mMode==PikiMode::TransportMode && p->mActiveAction->mCurrActionIdx==PikiAction::Transport,"both unexpected attachment");++count;continue;
        }
        p->mActiveAction->abandon(nullptr);p->mActiveAction->mCurrActionIdx=PikiAction::Transport;
        p->mActiveAction->mChildActions[PikiAction::Transport].initialise(cargo);p->mMode=PikiMode::TransportMode;++count;}
    require(count==20,"both twenty surviving carriers");
}
static void bothHaul(Navi* n){
    static int ticks=0,state=0,index=0,repairs=0,deliveredAt=0,goal=0,maxAttached=0;
    static Pellet* cargos[2]={nullptr,nullptr};
    ++ticks;n->mNeutralTime=0;require(ticks<10000,"both haul timed out");if(ticks<90)return;
    if(state==0){
        require(pc_p2_preview_ready() && pc_p2_preview_cargo_count()==2 && pc_p2_preview_goal(),"both native setup");
        require(pc_p2_cave_floor()==3 && pc_p2_cave_is_beasts() && !pc_p2_cave_checkpoint(false),"both diagnostic profile");
        for(int i=0;i<2;i++){Pellet* p=pc_p2_preview_cargo_at(i);require(p && p->mGenerator,"both cargo missing");
            if(p->mGenerator->_70==63000)cargos[0]=p;else if(p->mGenerator->_70==63001)cargos[1]=p;else require(false,"both unknown generator");}
        require(cargos[0] && cargos[1] && cargos[0]!=cargos[1] && cargos[0]->mConfig!=cargos[1]->mConfig,"both config alias");
        require(cargos[0]->mConfig->mCarryMinPikis()==12 && cargos[0]->mConfig->mCarryMaxPikis()==20 && cargos[1]->mConfig->mCarryMinPikis()==15 && cargos[1]->mConfig->mCarryMaxPikis()==25,"both settings");
        require(std::fabs(cargos[0]->mSRT.t.x+85)<.1f && std::fabs(cargos[0]->mSRT.t.y)<.1f && std::fabs(cargos[0]->mSRT.t.z+960)<.1f,"green actual source anchor");
        require(std::fabs(cargos[1]->mSRT.t.x-175)<.1f && std::fabs(cargos[1]->mSRT.t.y-20.5f)<.1f && std::fabs(cargos[1]->mSRT.t.z+55)<.1f,"donut actual source anchor");
        Iterator enemies(tekiMgr);CI_LOOP(enemies)require(!static_cast<Teki*>(*enemies)->isAlive(),"both unexpected enemy");
        Iterator bosses(bossMgr);CI_LOOP(bosses)require(!static_cast<Boss*>(*bosses)->isAlive(),"both unexpected boss");
        repairs=playerState->getCurrParts();require(pc_p2_preview_pokos()==0 || pc_p2_preview_pokos()==150,"both initial total");
        n->mKontroller=new FixtureController();for(int f=0;f<DEMOFLAG_COUNT;f++)playerState->mDemoFlags.setFlagOnly(f);
        bothAssign(cargos[0]);std::puts("P2_BOTH_READY cargo=2 configs_distinct=1 survivors=20");state=1;
    }
    require(playerState->getCurrParts()==repairs,"both repairs changed");
    if(state==1){
        // Receipt detection precedes any cargo dereference: native delivery kills it.
        bool complete=false;
        if(index==0){if(FILE* f=std::fopen("treasure-receipt.txt","r")){std::fclose(f);complete=true;}}
        else complete=pc_p2_preview_pokos()==380;
        if(complete){
            require(maxAttached>=(index==0?12:15),"both insufficient actual hauling");
            P2Economy reopened;reopened.load("p2-economy.txt");
            const char* id=index==0?"treasure:forest_1:floor3:treasure:dia_c_green:0":"treasure:forest_1:floor3:treasure:donutswhite:0";
            require(reopened.total()==(index==0?150:380) && reopened.count()==size_t(index+1) && !reopened.credit(id,index==0?150:230),"both duplicate/reopen failed");
            std::printf("P2_BOTH_DELIVERED index=%d total=%d duplicate_credit=0\n",index,reopened.total());
            cargos[index]=nullptr;combatWalking=false;deliveredAt=ticks;state=index==0?2:4;
            if(index==0){std::ifstream in("p2-economy.txt",std::ios::binary);std::ofstream out("partial-economy.txt",std::ios::binary);out<<in.rdbuf();require(in.good() && out.good(),"partial ledger copy");}
        }else{
            Pellet* cargo=cargos[index];int attached=0;Iterator all(pikiMgr);CI_LOOP(all){Piki* p=static_cast<Piki*>(*all);if(p->isAlive() && p->getStickObject()==cargo)++attached;}
            if(attached>maxAttached)maxAttached=attached;
            if(ticks%30==0)std::printf("P2_BOTH_POINT index=%d x=%.3f y=%.3f z=%.3f attached=%d\n",index,cargo->mSRT.t.x,cargo->mSRT.t.y,cargo->mSRT.t.z,attached);
            combatDestination=index==0?Vector3f(-85,0,std::min(-280.f,cargo->mSRT.t.z+80)):Vector3f(cargo->mSRT.t.x,0,cargo->mSRT.t.z+60);
            float dx=n->mSRT.t.x-combatDestination.x,dz=n->mSRT.t.z-combatDestination.z;combatWalking=dx*dx+dz*dz>60*60;
        }
    }else if(state==2 && ticks-deliveredAt>=120){
        int alive=0;Iterator all(pikiMgr);CI_LOOP(all){Piki* p=static_cast<Piki*>(*all);if(!p->isAlive())continue;require(!p->getStickObject(),"green crew not detached");p->changeMode(PikiMode::FormationMode,n);++alive;}
        require(alive==20,"both lost carriers after green");state=3;goal=0;
    }else if(state==3){
        const Vector3f goals[]={Vector3f(-85,0,-120),Vector3f(-85,0,85),Vector3f(150,0,0),Vector3f(150,0,-55),Vector3f(175,0,-55)};
        combatDestination=goals[goal];float dx=n->mSRT.t.x-combatDestination.x,dz=n->mSRT.t.z-combatDestination.z;combatWalking=dx*dx+dz*dz>15*15;
        if(!combatWalking){std::printf("P2_BOTH_WALK goal=%d x=%.3f y=%.3f z=%.3f\n",goal,n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z);if(++goal==5){
            bothAssign(cargos[1]);index=1;maxAttached=0;state=1;std::puts("P2_BOTH_APPROACH goals=5 survivors=20");}}
    }else if(state==4 && ticks-deliveredAt>=120){
        require(!pc_p2_cave_checkpoint(false) && !pc_p2_cave_exit_after_checkpoint(),"both enabled descent");
        P2Economy reopened;reopened.load("p2-economy.txt");require(reopened.total()==380 && reopened.count()==2 && !reopened.credit("treasure:forest_1:floor3:treasure:dia_c_green:0",150) && !reopened.credit("treasure:forest_1:floor3:treasure:donutswhite:0",230),"both final duplicate ledger");
        capture("both-haul-final.ppm");std::puts("PASS P2_BOTH_HAUL cargo=2 pokos=380 receipts=2 repairs_unchanged=1 descent=disabled");std::fflush(stdout);std::_Exit(0);
    }
    std::fflush(stdout);
}
