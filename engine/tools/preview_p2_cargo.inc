// Include after preview fixture's require/capture helpers. Integration calls
// verifyCargoReceipts() at a safe floor boundary; no transport is simulated here.
#include "pc_p2_cargo.h"
#include "Generator.h"
#include "Suckable.h"
#include <fstream>
#include <set>
struct CargoTransportProbe : ActTransport {
    static bool print(ActTransport* action) {
        auto state=&CargoTransportProbe::mState;auto path=&CargoTransportProbe::mPathIndex;
        auto goal=&CargoTransportProbe::mGoal;
        Suckable* receiver=action->*goal;if(!receiver)return false;Vector3f position=receiver->getGoalPos();
        std::printf("P2_CARGO_ROUTE state=%d path=%d goal=%.2f,%.2f,%.2f\n",action->*state,action->*path,position.x,position.y,position.z);
        auto refs=&CargoTransportProbe::mSplineControlPts;auto next=&CargoTransportProbe::mNextPathIndex;
        auto direction=&CargoTransportProbe::mMoveDir;
        std::printf("P2_CARGO_SPLINE next=%d direction=%.3f,%.3f,%.3f",action->*next,(action->*direction).x,(action->*direction).y,(action->*direction).z);
        for(auto& point:action->*refs)std::printf(" ref=%.2f,%.2f,%.2f",point.x,point.y,point.z);
        std::puts("");
        return true;
    }
};
static void verifyCargoReceipts() {
    std::ifstream in("p2-cargo.txt");auto specs=p2ReadCargo(in);
    require(pc_p2_preview_cargo_count()==int(specs.size()),"cargo registry count");
    std::set<PelletConfig*> configs;std::set<Shape*> shapes;
    const int before=pc_p2_preview_pokos(),repairs=playerState->getCurrParts();int value=0;
    for(size_t i=0;i<specs.size();++i) {
        Pellet* actor=pc_p2_preview_cargo_at(int(i));require(actor && actor->mGenerator,"cargo actor identity");
        require(actor->mGenerator->_70==specs[i].generator,"cargo generator binding");
        require(actor->mConfig->mCarryMinPikis()==specs[i].weight && actor->mConfig->mCarryMaxPikis()==specs[i].slots,"cargo per-actor weights");
        require(configs.insert(actor->mConfig).second,"cargo config shared between actors");
        require(shapes.insert(pc_p2_preview_cargo_shape(actor)).second && pc_p2_preview_cargo_shape(actor),"cargo model shared/missing");
        PelletConfig* global=pelletMgr->getConfig(actor->mConfig->mModelId.mId);
        require(global && global!=actor->mConfig,"cargo mutates shared global config");
        // Constructor-owned intrusive parameter links must all remain in this clone.
        int nodes=0;for(BaseParm* node=actor->mConfig->mFirstParm;node;node=node->mNext) {
            uintptr_t address=reinterpret_cast<uintptr_t>(node),base=reinterpret_cast<uintptr_t>(actor->mConfig);
            require(address>=base && address<base+sizeof(PelletConfig),"cargo parameter link points outside clone");
            require(++nodes<32,"cargo parameter chain cycle");
        }
        require(nodes>10,"cargo incomplete parameter chain");
        require(pc_p2_preview_deliver(actor),"cargo delivery not handled");value+=specs[i].value;
    }
    require(pc_p2_preview_pokos()==before+value,"cargo receipt total");
    for(int i=0;i<pc_p2_preview_cargo_count();++i)require(pc_p2_preview_deliver(pc_p2_preview_cargo_at(i)),"repeat cargo not handled");
    require(pc_p2_preview_pokos()==before+value && playerState->getCurrParts()==repairs,"duplicate cargo credit or P1 repairs");
    std::printf("P2_CARGO_FIXTURE_PASS count=%zu added=%d duplicate_credit=0 repairs_unchanged=1 private_configs=1\n",specs.size(),value);
}
// Optional independent real transport check for the second floor-1 treasure
// or sole floor-2 Atlas. Synthetic Purple identity supplies Atlas lifting power.
// Assigns real transport AI; cargo positions and receipt hooks are unchanged.
static bool cargoCarryFixture(Navi* n) {
    static bool requested=[](){FILE* f=std::fopen("p2-cargo-carry.txt","r");if(!f)return false;std::fclose(f);return true;}();
    if(!requested)return false;
    static int frames=0,before=0,value=0,repairs=0;static Pellet* target=nullptr;
    ++frames;if(frames<90)return true;
    if(frames==90) {
        require(pc_p2_preview_cargo_count()>0,"cargo missing");
        const int index=pc_p2_preview_cargo_count()>1?1:0;target=pc_p2_preview_cargo_at(index);
        std::ifstream in("p2-cargo.txt");auto specs=p2ReadCargo(in);value=specs[index].value;
        // Isolate hauling geometry from the newly populated combat encounters.
        // Real enemy combat is covered separately; these removals grant no credit.
        Iterator enemies(tekiMgr);CI_LOOP(enemies){Teki* enemy=static_cast<Teki*>(*enemies);if(enemy && enemy->isAlive())enemy->kill(false);}
        std::puts("P2_CARGO_FIXTURE_ENEMIES_REMOVED no_receipt_credit");
        before=pc_p2_preview_pokos();repairs=playerState->getCurrParts();int count=0;
        Iterator p(pikiMgr);CI_LOOP(p){Piki* v=static_cast<Piki*>(*p);if(!v->isAlive())continue;
            if(specs[index].weight>20 && count<10)pc_p2_make_purple(v);
            v->mActiveAction->abandon(nullptr);v->mActiveAction->mCurrActionIdx=PikiAction::Transport;
            v->mActiveAction->mChildActions[PikiAction::Transport].initialise(target);v->mMode=PikiMode::TransportMode;++count;
        }
        require(count>=5,"too few carriers for second cargo");
        // Keep the idle test captain out of the cargo's approach to the Pod.
        n->resetPosition(Vector3f(240,mapMgr->getMinY(240,210,true),210));
        std::printf("P2_CARGO_CARRY_START generator=%u weight=%d carriers=%d\n",target->mGenerator->_70,target->mConfig->mCarryMinPikis(),count);
    }
    if(frames%300==0){
        std::printf("P2_CARGO_CARRY_PROGRESS x=%.2f y=%.2f z=%.2f strength=%d\n",target->mSRT.t.x,target->mSRT.t.y,target->mSRT.t.z,target->mCarrierCounter);
        std::printf("P2_CARGO_VELOCITY carry=%.3f,%.3f,%.3f actual=%.3f,%.3f,%.3f volatile=%.3f,%.3f,%.3f ground=%d\n",target->mCarryDirection.x,target->mCarryDirection.y,target->mCarryDirection.z,target->mVelocity.x,target->mVelocity.y,target->mVelocity.z,target->mVolatileVelocity.x,target->mVolatileVelocity.y,target->mVolatileVelocity.z,target->onGround());
        std::printf("P2_CARGO_PHYSICS fixing=%d fixed=%d centre=%.2f bottom=%.2f dt=%.4f",target->isCreatureFlag(CF_AllowFixPosition),target->isCreatureFlag(CF_IsPositionFixed),target->getCentreSize(),target->getBottomRadius(),gsys->getFrameTime());
        if(target->mGroundTriangle)std::printf(" normal=%.3f,%.3f,%.3f",target->mGroundTriangle->mTriangle.mNormal.x,target->mGroundTriangle->mTriangle.mNormal.y,target->mGroundTriangle->mTriangle.mNormal.z);
        std::puts("");
        capture("p2-cargo-progress.ppm");
        Iterator carriers(pikiMgr);CI_LOOP(carriers){Piki* p=static_cast<Piki*>(*carriers);if(p->isAlive() && p->isStickTo() && p->mActiveAction->mCurrActionIdx==PikiAction::Transport && CargoTransportProbe::print(static_cast<ActTransport*>(p->mActiveAction->getCurrAction())))break;}
    }
    if(!target->isAlive()) {
        require(pc_p2_preview_pokos()==before+value && playerState->getCurrParts()==repairs,"second cargo actual delivery accounting");
        capture("p2-cargo-carry.ppm");std::puts("PASS P2 second cargo actual native transport and Pod delivery");std::fflush(stdout);std::_Exit(0);
    }
    require(frames<(target->mConfig->mCarryMinPikis()>20?9000:6000),"cargo transport timeout");return true;
}
