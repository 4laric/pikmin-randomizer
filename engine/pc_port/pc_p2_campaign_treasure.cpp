#include "pc_p2_campaign_treasure.h"
#include "pc_p2_campaign_treasure_config.h"
#include "pc_p2_white_treasure_policy.h"
#include "pc_randomizer.h"
#include "pc_bbft.h"
#include "pc_p2_cave_bud_actor.h"
#include "FlowController.h"
#include "Pellet.h"
#include "Generator.h"
#include "ItemMgr.h"
#include "GoalItem.h"
#include "PlayerState.h"
#include "Shape.h"
#include "Graphics.h"
#include "Camera.h"
#include "Texture.h"
#include "gameflow.h"
#include "system.h"
#include <cstdio>
#include <cstdlib>

// Campaign SAVE owner supplies selected bootstrap/card authority (#1229).
std::string pc_randomizer_campaign_treasure_source();
bool pc_randomizer_original_session();
bool pc_randomizer_original_input(const std::string&,std::string&,std::string&);
#if defined(__GNUC__)
extern void pc_p2_equipment_reconcile_courses() __attribute__((weak));
#endif

namespace {
void reconcileEquipment() {
#if defined(__GNUC__)
    if(pc_p2_equipment_reconcile_courses)pc_p2_equipment_reconcile_courses();
#endif
}
struct Bound {
    p2treasureplacements::Row row;
    const p2treasure::Entry* entry=nullptr;
    Pellet* actor=nullptr;GoalItem* receiver=nullptr;Shape* shape=nullptr;
};
p2treasure::Catalog catalog;
p2treasureplacements::Config config;
std::vector<Bound> actors;
Shape* podShape=nullptr;bool ready=false;int stage=-1;
[[noreturn]] void reject(const char* message) {
    std::fprintf(stderr,"P2 campaign treasure: %s\n",message);std::abort();
}
bool current() {
    return ready&&flowCont.mCurrentStage&&flowCont.mCurrentStage->mStageID==stage
        &&p2treasurestate::state.active()&&p2treasurestate::state.source()==config.source
        &&pc_randomizer_campaign_treasure_source()==config.source;
}
void textures(Shape* shape) {
    for(int i=0;i<shape->mTexAttrCount;++i)
        if(shape->mTexAttrList[i].mTexture)shape->mTexAttrList[i].mTexture->attach();
}
// Never copy intrusive Parameters/CoreNode links from shared native configs.
PelletConfig* privateConfig(PelletConfig* source,int weight,int slots) {
    auto* result=new PelletConfig;
#define COPY_VALUE(name) result->name.mValue=source->name.mValue
    COPY_VALUE(mPelletName);COPY_VALUE(mPelletType);COPY_VALUE(mPelletColor);
    COPY_VALUE(mUseDynamicMotion);COPY_VALUE(_A0);COPY_VALUE(_B0);COPY_VALUE(_C0);
    COPY_VALUE(mMatchingOnyonSeeds);COPY_VALUE(mNonMatchingOnyonSeeds);
    COPY_VALUE(mPelletScale);COPY_VALUE(mCarryInfoHeight);COPY_VALUE(mAnimSoundID);COPY_VALUE(mBounceSoundID);
#undef COPY_VALUE
    result->mModelId=source->mModelId;result->mPelletId=source->mPelletId;result->mUnusedId=source->mUnusedId;
    result->mRepairAnimJointIndex=source->mRepairAnimJointIndex;
    result->mCarryMinPikis.mValue=weight;result->mCarryMaxPikis.mValue=slots;return result;
}
Bound* bound(Pellet* pellet) {
    if(!current()||!pellet||!pellet->mGenerator)return nullptr;
    for(auto& actor:actors)if(pellet->mGenerator->_70==actor.row.cargo) {
        if(actor.actor!=pellet)reject("registered cargo pointer replaced");return &actor;
    }
    return nullptr;
}
void validate(const Bound& actor) {
    if(!actor.actor||!actor.actor->mGenerator||actor.actor->mGenerator->_70!=actor.row.cargo
       ||!actor.receiver||!actor.receiver->mGenerator||actor.receiver->mGenerator->_70!=actor.row.receiver
       ||!actor.actor->mConfig||actor.actor->mConfig->mCarryMinPikis()!=actor.entry->strength
       ||actor.actor->mConfig->mCarryMaxPikis()!=actor.entry->slots)reject("physical source/receiver/profile changed");
}
}
bool pc_p2_campaign_treasure_seen(const char* retailId) {
    if(!retailId||!p2treasure::safe_id(retailId))return false;
    if(std::string(retailId)=="dia_a_red"&&pc_randomizer_white_treasure_campaign()&&p2whitetreasure::ledger.delivered)return true;
    if(!p2treasurestate::state.active()||pc_randomizer_campaign_treasure_source()!=p2treasurestate::state.source())return false;
    static p2treasure::Catalog verified;
    static const bool loaded=[](){const char* path=std::getenv("PIKMIN_P2_TREASURE_CATALOG");
        return verified.load_retail(path&&path[0]?path:"p2-treasure-catalog.txt");}();
    return loaded&&p2treasurestate::state.seen(verified,retailId);
}
void pc_p2_campaign_treasure_setup() {
    ready=false;stage=-1;actors.clear();podShape=nullptr;
    // Only the campaign/card owner may activate and restore this source identity.
    // A catalog, model, environment variable or sidecar alone grants nothing.
    if(!p2treasurestate::state.active())return;
    if(pc_randomizer_campaign_treasure_source()!=p2treasurestate::state.source())reject("selected campaign source mismatch");
    if(pc_randomizer_original_session()) {
        std::string bytes,error,magic;
        if(!pc_randomizer_original_input("p2-treasure-placements.txt",bytes,error)
           ||p2treasureplacements::hash(bytes)!=p2treasurestate::state.source())reject("selected original treasury changed");
        std::istringstream descriptor(bytes);
        if(!(descriptor>>magic)||(magic!="P2_TREASURE_RETAIL_1"&&magic!="P2_TREASURE_HELD_1"))reject("selected original treasury provider unsupported");
        return; // Source-owned loose/held providers retain their actual actor lifecycle.
    }
    {std::ifstream descriptor("p2-treasure-placements.txt");std::string magic;
     if(descriptor>>magic&&magic=="P2_TREASURE_HELD_1")return;}
    if(pc_pikipelago_room_preview())reject("ordinary surface provider excludes preview");
    if(pc_p2_cave_bud_body_profile())return; // Cave owner retains floor actor lifecycle.
    const char* path=std::getenv("PIKMIN_P2_TREASURE_CATALOG");
    if(!catalog.load_retail(path?path:"p2-treasure-catalog.txt")
       ||!p2treasureplacements::read(catalog,config)||config.source!=p2treasurestate::state.source())reject("authenticated placements/catalog mismatch");
    if(!flowCont.mCurrentStage)reject("missing current stage");stage=flowCont.mCurrentStage->mStageID;
    const char* folders[]={"practice","stage1","stage2","stage3","last"};
    p2whitetreasure::Config white;
    const bool whiteEnabled=pc_randomizer_white_treasure_campaign();
    if(whiteEnabled&&!p2whitetreasure::read_config(white))reject("White source configuration changed");
    // Check the entire descriptor before mutating any actors. White dispatch
    // runs first, so an alias could otherwise credit its diamond for this row.
    for(const auto& row:config.rows)if(whiteEnabled) {
        if(row.id=="dia_a_red")reject("White owns the diamond physical provider");
        if(row.stage==white.stage&&row.cargo==white.cargo)reject("cargo identity overlaps White provider");
        if(row.stage==white.stage&&row.receiver==white.receiver&&config.podHash!=white.hashes[2])reject("shared White receiver model differs");
    }
    for(const auto& row:config.rows) {
        if(row.stage!=stage)continue;
        std::string generatorBytes;
        if(!p2treasureplacements::bounded(std::string("assets/dataDir/stages/")+folders[stage]+"/default.gen",4u*1024u*1024u,generatorBytes)
           ||p2treasureplacements::hash(generatorBytes)!=row.generatorHash)reject("physical generator source changed");
        Bound actor;actor.row=row;actor.entry=catalog.find(row.id);
        auto* receiver=itemMgr->getContainer(Red);
        if(!receiver||!receiver->mGenerator||receiver->mGenerator->_70!=row.receiver)reject("source receiver missing");
        actor.receiver=receiver;
        Iterator pellets(pelletMgr);CI_LOOP(pellets) {
            auto* pellet=static_cast<Pellet*>(*pellets);
            if(pellet->isAlive()&&pellet->mGenerator&&pellet->mGenerator->_70==row.cargo) {
                if(actor.actor)reject("duplicate live cargo identity");actor.actor=pellet;
            }
        }
        if(p2treasurestate::state.seen(catalog,row.id)) {
            if(actor.actor)actor.actor->kill(false);actor.actor=nullptr;
            std::printf("P2_TREASURE_RESTORED id=%s stage=%d cargo=%u consumed=1\n",row.id.c_str(),stage,row.cargo);
        } else {
            if(!actor.actor||!actor.actor->mConfig||actor.actor->mConfig->mModelId.mId!='pr05')reject("undelivered physical host missing");
            const std::string model="courses/pikmin2treasures/"+row.id+".mod";
            std::string bytes;
            if(!p2treasureplacements::bounded("assets/dataDir/"+model,32u*1024u*1024u,bytes)
               ||p2treasureplacements::hash(bytes)!=row.modelHash)reject("original treasure model mismatch");
            const int heap=gsys->setHeap(SYSHEAP_App);
            actor.actor->mConfig=privateConfig(actor.actor->mConfig,actor.entry->strength,actor.entry->slots);
            actor.shape=gameflow.loadShape(model.c_str(),true);if(!actor.shape)reject("treasure shape load failed");textures(actor.shape);
            gsys->setHeap(heap);
        }
        actors.push_back(actor);
    }
    if(actors.empty()){ready=true;reconcileEquipment();return;}
    std::string bytes;
    if(!p2treasureplacements::bounded("assets/dataDir/courses/pikmin2treasures/pod.mod",32u*1024u*1024u,bytes)
       ||p2treasureplacements::hash(bytes)!=config.podHash)reject("original receiver model mismatch");
    const int heap=gsys->setHeap(SYSHEAP_App);
    podShape=gameflow.loadShape("courses/pikmin2treasures/pod.mod",true);if(!podShape)reject("receiver shape load failed");textures(podShape);
    gsys->setHeap(heap);ready=true;reconcileEquipment();
    std::printf("P2_TREASURE_READY stage=%d physical_sources=%zu placement=%s\n",stage,actors.size(),config.source.c_str());
}
Suckable* pc_p2_campaign_treasure_goal(Pellet* pellet) {
    auto* actor=bound(pellet);if(!actor)return nullptr;validate(*actor);return actor->receiver;
}
bool pc_p2_campaign_treasure_deliver(Pellet* pellet) {
    auto* actor=bound(pellet);if(!actor)return false;validate(*actor);
    if(pellet->mTargetGoal!=static_cast<Suckable*>(actor->receiver))reject("native suction used wrong receiver");
    const int partsBefore=playerState->getCurrParts();
    const auto credit=p2treasurestate::state.credit(catalog,actor->row.id,actor->entry->value);
    if(credit==p2treasurestate::Credit::Invalid||playerState->getCurrParts()!=partsBefore)reject("receipt refused or P1 repairs changed");
    if(credit==p2treasurestate::Credit::Added)reconcileEquipment();
    std::printf("P2_TREASURE_RECEIPT id=%s value=%d new=%d stage=%d cargo=%u receiver=%u native_suction_completed=1 seeds=0\n",
        actor->row.id.c_str(),actor->entry->value,int(credit==p2treasurestate::Credit::Added),stage,actor->row.cargo,actor->row.receiver);
    std::fflush(stdout);return true;
}
bool pc_p2_campaign_treasure_draw(Pellet* pellet,Graphics& gfx,Matrix4f& matrix) {
    auto* actor=bound(pellet);if(!actor||!pellet->isAlive()||!actor->shape||p2treasurestate::state.seen(catalog,actor->row.id))return false;
    actor->shape->updateAnim(gfx,matrix,nullptr,pellet);actor->shape->drawshape(gfx,*gfx.mCamera,nullptr);return true;
}
bool pc_p2_campaign_treasure_is_pod(GoalItem* goal) {
    if(current())for(const auto& actor:actors)if(actor.receiver==goal)return true;return false;
}
bool pc_p2_campaign_treasure_draw_pod(GoalItem* goal,Graphics& gfx,Matrix4f&) {
    if(!pc_p2_campaign_treasure_is_pod(goal)||!podShape)return false;
    Matrix4f world,view;Vector3f position=goal->mSRT.t;position.y+=74;
    world.makeSRT(Vector3f(1,1,1),Vector3f(0,0,0),position);gfx.mCamera->mLookAtMtx.multiplyTo(world,view);
    podShape->updateAnim(gfx,view,nullptr,goal);podShape->drawshape(gfx,*gfx.mCamera,nullptr);return true;
}
