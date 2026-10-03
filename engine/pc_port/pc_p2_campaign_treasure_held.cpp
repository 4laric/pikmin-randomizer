#include "pc_p2_campaign_treasure_held.h"
#include "pc_p2_campaign_treasure_held_config.h"
#include "pc_p2_original_actor.h"
#include "pc_p2_original_drop_engine.h"
#include "pc_p2_original_onyon_native.h"
#include "pc_randomizer.h"
#include "pc_bbft.h"
#include "Pellet.h"
#include "Generator.h"
#include "ItemMgr.h"
#include "UfoItem.h"
#include "PlayerState.h"
#include "Shape.h"
#include "Graphics.h"
#include "Camera.h"
#include "Texture.h"
#include "teki.h"
#include "gameflow.h"
#include "system.h"
#include <cstdio>
#include <cstdlib>
#include <cmath>

std::string pc_randomizer_campaign_treasure_source();
#if defined(__GNUC__)
extern void pc_p2_equipment_reconcile_courses() __attribute__((weak));
#endif
namespace {
void reconcileEquipment() {
#if defined(__GNUC__)
    if(pc_p2_equipment_reconcile_courses)pc_p2_equipment_reconcile_courses();
#endif
}
p2treasure::Catalog catalog;p2treasureheld::Config config;
std::map<std::string,Shape*> shapes;bool ready=false;
struct Release {std::string id;Pellet* actor=nullptr;PelletConfig* profile=nullptr;};
std::map<p2original::InstanceIdentity,Release> released;
[[noreturn]] void reject(const char* message) {std::fprintf(stderr,"P2 original held treasure: %s\n",message);std::abort();}
bool fail(std::string& error,const char* message){error=message;return false;}
bool selected() {
    return p2treasurestate::state.active()&&p2treasurestate::state.source()==config.identity
        &&pc_randomizer_campaign_treasure_source()==config.identity;
}
void textures(Shape* shape) {for(int i=0;i<shape->mTexAttrCount;++i)if(shape->mTexAttrList[i].mTexture)shape->mTexAttrList[i].mTexture->attach();}
bool ensure(std::string& error) {
    if(!p2treasurestate::state.active()||pc_randomizer_campaign_treasure_source()!=p2treasurestate::state.source())return fail(error,"held treasure lacks selected authenticated source");
    if(ready) {
        std::string bytes;
        if(!selected()||!p2treasureplacements::bounded("p2-treasure-placements.txt",p2treasureplacements::MaxBytes,bytes)
           ||p2treasureplacements::hash(bytes)!=config.identity)return fail(error,"held treasure source changed");
        error.clear();return true;
    }
    if(!p2treasureheld::load_verified(catalog,config)||config.identity!=p2treasurestate::state.source())return fail(error,"literal held source/catalog/model descriptor mismatch");
    // A real typed original ship is required; verify its literal manifest before
    // any enemy reservation or birth. The ship actor itself is born afterwards.
    // load_verified already parsed the exact hashed receiver buffer. Reopening
    // its path here would introduce an unauthenticated second source buffer.
    if(!gsys||!pc_p2_original_drop_host_ready())return fail(error,"held original receiver/physical host resources missing");
    const int heap=gsys->setHeap(SYSHEAP_App);
    for(const auto& row:config.rows) {
        const std::string path="courses/pikmin2treasures/"+row.id+".mod";
        Shape* shape=gameflow.loadShape(path.c_str(),true);
        if(!shape)reject("verified original treasure shape load failed");textures(shape);shapes.emplace(row.id,shape);
    }
    gsys->setHeap(heap);ready=true;reconcileEquipment();error.clear();return true;
}
UfoItem* receiver() {
    if(!ready||!selected()||!itemMgr)return nullptr;
    auto* ship=itemMgr->getUfo();std::string identity;
    if(!ship||!ship->mGenerator||ship->mGenerator->_70!=config.receiver
       ||!pc_p2_original_onyon_identity(ship,identity)||identity!=config.receiverIdentity)return nullptr;
    return ship;
}
Release* bound(Pellet* pellet) {
    if(!pellet)return nullptr;
    for(auto& record:released)if(record.second.actor==pellet) {
        if(!ready||!selected())reject("owned held cargo lost selected campaign authority");
        if(pellet->mConfig!=record.second.profile)reject("held cargo pool reused without retirement");
        return &record.second;
    }return nullptr;
}
PelletConfig* profile(PelletConfig* source,const p2treasure::Entry& entry) {
    auto* result=new PelletConfig;
#define COPY_VALUE(name) result->name.mValue=source->name.mValue
    COPY_VALUE(mPelletName);COPY_VALUE(mPelletType);COPY_VALUE(mPelletColor);
    COPY_VALUE(mUseDynamicMotion);COPY_VALUE(_A0);COPY_VALUE(_B0);COPY_VALUE(_C0);
    COPY_VALUE(mMatchingOnyonSeeds);COPY_VALUE(mNonMatchingOnyonSeeds);
    COPY_VALUE(mPelletScale);COPY_VALUE(mCarryInfoHeight);COPY_VALUE(mAnimSoundID);COPY_VALUE(mBounceSoundID);
#undef COPY_VALUE
    result->mModelId=source->mModelId;result->mPelletId=source->mPelletId;result->mUnusedId=source->mUnusedId;
    result->mRepairAnimJointIndex=source->mRepairAnimJointIndex;
    result->mCarryMinPikis.mValue=entry.strength;result->mCarryMaxPikis.mValue=entry.slots;return result;
}
}
bool pc_p2_campaign_treasure_held_resources(const p2original::CatalogRow& row,std::string& error) {
    if(!row.enemy.treasureCode)return true;
    if(!ensure(error))return false;
    if(!p2treasureheld::find(config,row))return fail(error,"literal enemy-held code/UID/source not bound");
    error.clear();return true;
}
bool pc_p2_campaign_treasure_held_spawn(BTeki* actor,const p2original::CatalogRow& row,const p2original::InstanceIdentity& identity,
                                     const Vector3f& position,const Vector3f& velocity,std::string& error) {
    if(!actor||!pc_p2_campaign_treasure_held_resources(row,error))return false;
    unsigned source=0,token=0;p2original::InstanceIdentity actual;
    if(!p2original::originalActors().query(static_cast<Creature*>(actor),source,token,&actual)||!(actual==identity)
       ||identity.catalog!=config.campaign||identity.generator!=row.enemy.uid||source!=row.enemy.source)return fail(error,"held drop lost literal incarnation authority");
    const auto* held=p2treasureheld::find(config,row);const auto* entry=catalog.find(held->id);
    for(float value:{position.x,position.y,position.z,velocity.x,velocity.y,velocity.z})if(!std::isfinite(value))return fail(error,"held source throw transform invalid");
    if(p2treasurestate::state.seen(catalog,held->id)||released.count(identity)){error.clear();return true;}
    if(released.size()>=65536)return fail(error,"held release incarnation capacity exhausted");
    auto* pellet=pelletMgr->newPellet('pr05',nullptr);
    if(!pellet)return fail(error,"physical held treasure pool birth refused");
    const int heap=gsys->setHeap(SYSHEAP_App);
    pellet->mConfig=profile(pellet->mConfig,*entry);gsys->setHeap(heap);
    pellet->mGenerator=nullptr; // Own typed release; never report another enemy death.
    pellet->init(position);pellet->mFaceDirection=actor->getDirection();pellet->startAI(FALSE);pellet->mVelocity=velocity;
    released.emplace(identity,Release{held->id,pellet,pellet->mConfig});
    std::printf("P2_ORIGINAL_HELD_RELEASE id=%s code=%d value=%d minimum=%d maximum=%d source=%u uid=%u ordinal=%u epoch=%llu activation=%llu token=%u physical=1 receipt=0\n",
        held->id.c_str(),held->code,entry->value,entry->strength,entry->slots,source,identity.generator,identity.ordinal,
        (unsigned long long)identity.epoch,(unsigned long long)identity.activation,token);
    error.clear();return true;
}
Suckable* pc_p2_campaign_treasure_held_goal(Pellet* pellet) {
    if(!bound(pellet))return nullptr;auto* ship=receiver();if(!ship)reject("literal ship receiver unavailable");return ship;
}
bool pc_p2_campaign_treasure_held_owns(Pellet* pellet) {return bound(pellet)!=nullptr;}
bool pc_p2_campaign_treasure_held_deliver(Pellet* pellet) {
    auto* held=bound(pellet);if(!held)return false;
    auto* ship=receiver();const auto* entry=catalog.find(held->id);
    if(!ship||pellet->mTargetGoal!=static_cast<Suckable*>(ship)||!entry
       ||pellet->mConfig->mCarryMinPikis()!=entry->strength||pellet->mConfig->mCarryMaxPikis()!=entry->slots)reject("completed held suction source/receiver/profile mismatch");
    const int partsBefore=playerState->getCurrParts();
    const auto result=p2treasurestate::state.credit(catalog,held->id,entry->value);
    if(result==p2treasurestate::Credit::Invalid||playerState->getCurrParts()!=partsBefore)reject("held receipt refused or P1 repair count changed");
    if(result==p2treasurestate::Credit::Added)reconcileEquipment();
    std::printf("P2_ORIGINAL_HELD_RECEIPT id=%s value=%d new=%d receiver=%u native_suction_completed=1 seeds=0\n",
        held->id.c_str(),entry->value,int(result==p2treasurestate::Credit::Added),config.receiver);std::fflush(stdout);return true;
}
bool pc_p2_campaign_treasure_held_draw(Pellet* pellet,Graphics& gfx,Matrix4f& matrix) {
    auto* held=bound(pellet);if(!held||!pellet->isAlive()||p2treasurestate::state.seen(catalog,held->id))return false;
    auto* shape=shapes.at(held->id);shape->updateAnim(gfx,matrix,nullptr,pellet);shape->drawshape(gfx,*gfx.mCamera,nullptr);return true;
}
bool pc_p2_campaign_treasure_held_draw_receiver(UfoItem* ship,Graphics& gfx,const Matrix4f& matrix) {
    // The held descriptor's legacy Pod asset is not the surface Ship model.
    // Original Ship presentation belongs to the typed Onyon source provider.
    return false;
}
void pc_p2_campaign_treasure_held_retire(Pellet* pellet) {
    for(auto& record:released)if(record.second.actor==pellet){record.second.actor=nullptr;record.second.profile=nullptr;}
}
unsigned pc_p2_campaign_treasure_held_pending() {
    unsigned count=0;
    for(const auto& record:released)if(!p2treasurestate::state.seen(catalog,record.second.id))++count;
    return count;
}
bool pc_p2_campaign_treasure_held_unload(std::string& error) {
    if(pc_p2_campaign_treasure_held_pending())return fail(error,"uncollected held physical graph has no authenticated cache restore");
    released.clear();shapes.clear();ready=false;catalog=p2treasure::Catalog{};config=p2treasureheld::Config{};
    error.clear();return true;
}
