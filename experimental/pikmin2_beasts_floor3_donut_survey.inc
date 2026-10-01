// External engineering action driver; no actor position or cargo route mutation.
#include "pc_p2_economy.h"
static void floorThreeDonut(Navi* n) {
    static int ticks=0,state=0,repairs=0,initialPokos=0,maxAttached=0,deliveredAt=0;
    static Pellet* cargo=nullptr;
    static bool westRoute=false,podApproach=false;
    ++ticks;n->mNeutralTime=0;require(ticks<6000,"floor3 native hauling timed out");
    if(ticks<90)return;
    if(state==0){
        require(pc_p2_preview_ready() && !pc_p2_preview_cargo_free_ready() && pc_p2_preview_goal(),"floor3 cargo/Pod readiness");
        require(pc_p2_cave_floor()==3 && pc_p2_cave_is_beasts(),"floor3 diagnostic entry missing");
        FILE* entry=std::fopen("p2-floor3-boundary.txt","r");require(entry,"floor3 token missing");
        char token[65],extra;require(std::fscanf(entry,"%64s",token)==1 && std::fscanf(entry," %c",&extra)==EOF,"floor3 token malformed");std::fclose(entry);
        require(pc_p2_cave_boundary_token()==token,"floor3 token differs");
        require(!pc_p2_cave_checkpoint(false) && !pc_p2_cave_exit_after_checkpoint(),"floor3 cargo checkpoint enabled");
        cargo=pc_p2_preview_treasure();require(cargo && cargo->mGenerator && cargo->mGenerator->_70==63001,"floor3 cargo generator");
        require(pc_p2_preview_cargo_count()==1 && cargo->mConfig->mCarryMinPikis()==15 && cargo->mConfig->mCarryMaxPikis()==25,"floor3 cargo settings");
        const Vector3f pos=cargo->mGenerator->getPos();
        require(std::fabs(pos.x-175)<.1f && std::fabs(pos.y-20.5f)<.1f && std::fabs(pos.z+55)<.1f,"floor3 source cargo position");
        std::printf("P2_FLOOR3_DONUT_PHYSICS bottom_radius=%.3f cylinder_height=%.3f center_size=%.3f config_scale=%.3f carry_height=%.3f\n",cargo->getBottomRadius(),cargo->getCylinderHeight(),cargo->getCentreSize(),cargo->mConfig->mPelletScale(),cargo->mConfig->mCarryInfoHeight());
        Iterator enemies(tekiMgr);CI_LOOP(enemies)require(!static_cast<Teki*>(*enemies)->isAlive(),"floor3 unexpected enemy");
        Iterator bosses(bossMgr);CI_LOOP(bosses)require(!static_cast<Boss*>(*bosses)->isAlive(),"floor3 unexpected boss");
        repairs=playerState->getCurrParts();initialPokos=pc_p2_preview_pokos();require(initialPokos==0 || initialPokos==230,"floor3 unexpected initial economy");
        n->mKontroller=new FixtureController();for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f);
        int count=0;Iterator pikis(pikiMgr);CI_LOOP(pikis){Piki* p=static_cast<Piki*>(*pikis);if(!p->isAlive())continue;
            require(p->mColor==Red && !pc_p2_is_purple(p),"floor3 expected Red carriers");
            p->mActiveAction->abandon(nullptr);p->mActiveAction->mCurrActionIdx=PikiAction::Transport;
            p->mActiveAction->mChildActions[PikiAction::Transport].initialise(cargo);p->mMode=PikiMode::TransportMode;++count;}
        std::printf("P2_FLOOR3_DONUT_INITIAL alive=%d\n",count);
        if(count!=20){Iterator debug(pikiMgr);CI_LOOP(debug){Piki* p=static_cast<Piki*>(*debug);std::printf("P2_FLOOR3_DONUT_INITIAL_PIKI alive=%d x=%.3f y=%.3f z=%.3f state=%d\n",int(p->isAlive()),p->mSRT.t.x,p->mSRT.t.y,p->mSRT.t.z,p->getState());}}
        require(count==20,"floor3 expected twenty carriers");
        std::printf("P2_FLOOR3_DONUT_READY token=%s generator=63001 value=230 weight=15 slots=25 initial_pokos=%d x=%.3f y=%.3f z=%.3f\n",token,initialPokos,pos.x,pos.y,pos.z);
        std::puts("P2_FLOOR3_DONUT_ASSIGNED carriers=20 native_transport=1 positions_unchanged=1");state=1;
    }
    require(playerState->getCurrParts()==repairs,"floor3 hauling changed repairs");
    if(state==1){
        int attached=0;Iterator pikis(pikiMgr);CI_LOOP(pikis){Piki* p=static_cast<Piki*>(*pikis);if(p->isAlive() && p->getStickObject()==cargo)++attached;}
        if(attached>maxAttached)maxAttached=attached;
        require(attached<=20,"floor3 cargo slot overflow");
        if(ticks%30==0)std::printf("P2_FLOOR3_DONUT_POINT x=%.3f y=%.3f z=%.3f attached=%d ground=%.3f\n",cargo->mSRT.t.x,cargo->mSRT.t.y,cargo->mSRT.t.z,attached,mapMgr->getMinY(cargo->mSRT.t.x,cargo->mSRT.t.z,true));
        if(cargo->mSRT.t.x<=0 && !westRoute){westRoute=true;std::puts("P2_FLOOR3_DONUT_ROUTE west");}
        if(cargo->mSRT.t.z<=-200 && !podApproach){require(westRoute,"donut route order");podApproach=true;std::puts("P2_FLOOR3_DONUT_ROUTE pod_approach");}
        // Follow the moving cargo to keep ordinary simulation active.
        combatDestination=Vector3f(cargo->mSRT.t.x,0,cargo->mSRT.t.z+60.f);
        float dx=n->mSRT.t.x-combatDestination.x,dz=n->mSRT.t.z-combatDestination.z;combatWalking=dx*dx+dz*dz>60*60;
        if(FILE* receipt=std::fopen("treasure-receipt.txt","r")){
            std::fclose(receipt);combatWalking=false;
            require(westRoute && podApproach && maxAttached>=15,"donut cargo did not traverse block room with carriers");
            require(pc_p2_preview_pokos()==230,"floor3 wrong delivered value");
            require(pc_p2_preview_deliver(cargo) && pc_p2_preview_pokos()==230,"floor3 duplicate credit");
            P2Economy reopened;reopened.load("p2-economy.txt");
            require(reopened.total()==230 && reopened.count()==1 && !reopened.credit("treasure:forest_1:floor3:treasure:donutswhite:0",230),"floor3 economy reopen differs");
            std::printf("P2_FLOOR3_DONUT_DELIVERED max_attached=%d blockroom_route=1 duplicate_credit=0 reopened_receipts=1 pokos=230 repairs_unchanged=1\n",maxAttached);
            state=2;deliveredAt=ticks;
        }
    }else if(state==2 && ticks-deliveredAt>=120){
        require(!pc_p2_cave_checkpoint(false) && !pc_p2_cave_exit_after_checkpoint(),"floor3 hauling enabled descent");
        capture("floor3-donut-final.ppm");
        std::puts("PASS P2_FLOOR3_DONUT cargo=1 value=230 seeds=0 repairs_unchanged=1 descent=disabled");std::fflush(stdout);std::_Exit(0);
    }
    std::fflush(stdout);
}
