// External engineering action driver; no actor position or cargo route mutation.
#include "pc_p2_economy.h"
static void floorThreeHaul(Navi* n) {
    static int ticks=0,state=0,repairs=0,initialPokos=0,maxAttached=0,deliveredAt=0;
    static Pellet* cargo=nullptr;
    static bool northSeam=false,southSeam=false;
    ++ticks;n->mNeutralTime=0;require(ticks<6000,"floor3 native hauling timed out");
    if(ticks<90)return;
    if(state==0){
        require(pc_p2_preview_ready() && !pc_p2_preview_cargo_free_ready() && pc_p2_preview_goal(),"floor3 cargo/Pod readiness");
        require(pc_p2_cave_floor()==3 && pc_p2_cave_is_beasts(),"floor3 diagnostic entry missing");
        FILE* entry=std::fopen("p2-floor3-boundary.txt","r");require(entry,"floor3 token missing");
        char token[65],extra;require(std::fscanf(entry,"%64s",token)==1 && std::fscanf(entry," %c",&extra)==EOF,"floor3 token malformed");std::fclose(entry);
        require(pc_p2_cave_boundary_token()==token,"floor3 token differs");
        require(!pc_p2_cave_checkpoint(false) && !pc_p2_cave_exit_after_checkpoint(),"floor3 cargo checkpoint enabled");
        cargo=pc_p2_preview_treasure();require(cargo && cargo->mGenerator && cargo->mGenerator->_70==63000,"floor3 cargo generator");
        require(pc_p2_preview_cargo_count()==1 && cargo->mConfig->mCarryMinPikis()==12 && cargo->mConfig->mCarryMaxPikis()==20,"floor3 cargo settings");
        const Vector3f pos=cargo->mGenerator->getPos();
        require(std::fabs(pos.x+85)<.1f && std::fabs(pos.y)<.1f && std::fabs(pos.z+960)<.1f,"floor3 source cargo position");
        Iterator enemies(tekiMgr);CI_LOOP(enemies)require(!static_cast<Teki*>(*enemies)->isAlive(),"floor3 unexpected enemy");
        Iterator bosses(bossMgr);CI_LOOP(bosses)require(!static_cast<Boss*>(*bosses)->isAlive(),"floor3 unexpected boss");
        repairs=playerState->getCurrParts();initialPokos=pc_p2_preview_pokos();require(initialPokos==0 || initialPokos==150,"floor3 unexpected initial economy");
        n->mKontroller=new FixtureController();for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f);
        int count=0;Iterator pikis(pikiMgr);CI_LOOP(pikis){Piki* p=static_cast<Piki*>(*pikis);if(!p->isAlive())continue;
            require(p->mColor==Red && !pc_p2_is_purple(p),"floor3 expected Red carriers");
            p->mActiveAction->abandon(nullptr);p->mActiveAction->mCurrActionIdx=PikiAction::Transport;
            p->mActiveAction->mChildActions[PikiAction::Transport].initialise(cargo);p->mMode=PikiMode::TransportMode;++count;}
        require(count==20,"floor3 expected twenty carriers");
        std::printf("P2_FLOOR3_HAUL_READY token=%s generator=63000 value=150 weight=12 slots=20 initial_pokos=%d x=%.3f y=%.3f z=%.3f\n",token,initialPokos,pos.x,pos.y,pos.z);
        std::puts("P2_FLOOR3_HAUL_ASSIGNED carriers=20 native_transport=1 positions_unchanged=1");state=1;
    }
    require(playerState->getCurrParts()==repairs,"floor3 hauling changed repairs");
    if(state==1){
        int attached=0;Iterator pikis(pikiMgr);CI_LOOP(pikis){Piki* p=static_cast<Piki*>(*pikis);if(p->isAlive() && p->getStickObject()==cargo)++attached;}
        if(attached>maxAttached)maxAttached=attached;
        require(attached<=20,"floor3 cargo slot overflow");
        if(ticks%30==0)std::printf("P2_FLOOR3_HAUL_POINT x=%.3f y=%.3f z=%.3f attached=%d ground=%.3f\n",cargo->mSRT.t.x,cargo->mSRT.t.y,cargo->mSRT.t.z,attached,mapMgr->getMinY(cargo->mSRT.t.x,cargo->mSRT.t.z,true));
        if(cargo->mSRT.t.z>=-510 && !northSeam){northSeam=true;std::puts("P2_FLOOR3_HAUL_SEAM north");}
        if(cargo->mSRT.t.z>=-340 && !southSeam){require(northSeam,"floor3 seam order");southSeam=true;std::puts("P2_FLOOR3_HAUL_SEAM south");}
        // Follow the moving cargo to keep ordinary simulation active.
        combatDestination=Vector3f(-85,0,std::min(-280.f,cargo->mSRT.t.z+80.f));
        float dx=n->mSRT.t.x-combatDestination.x,dz=n->mSRT.t.z-combatDestination.z;combatWalking=dx*dx+dz*dz>60*60;
        if(FILE* receipt=std::fopen("treasure-receipt.txt","r")){
            std::fclose(receipt);combatWalking=false;
            require(northSeam && southSeam && maxAttached>=12,"floor3 cargo did not cross seams with carriers");
            require(pc_p2_preview_pokos()==150,"floor3 wrong delivered value");
            require(pc_p2_preview_deliver(cargo) && pc_p2_preview_pokos()==150,"floor3 duplicate credit");
            P2Economy reopened;reopened.load("p2-economy.txt");
            require(reopened.total()==150 && reopened.count()==1 && !reopened.credit("treasure:forest_1:floor3:treasure:dia_c_green:0",150),"floor3 economy reopen differs");
            std::printf("P2_FLOOR3_HAUL_DELIVERED max_attached=%d seams=2 duplicate_credit=0 reopened_receipts=1 pokos=150 repairs_unchanged=1\n",maxAttached);
            state=2;deliveredAt=ticks;
        }
    }else if(state==2 && ticks-deliveredAt>=120){
        require(!pc_p2_cave_checkpoint(false) && !pc_p2_cave_exit_after_checkpoint(),"floor3 hauling enabled descent");
        capture("floor3-haul-final.ppm");
        std::puts("PASS P2_FLOOR3_HAUL cargo=1 value=150 seeds=0 repairs_unchanged=1 descent=disabled");std::fflush(stdout);std::_Exit(0);
    }
    std::fflush(stdout);
}
