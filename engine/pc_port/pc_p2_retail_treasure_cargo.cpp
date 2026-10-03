#include "pc_p2_retail_treasure_cargo.h"
#include "pc_p2_retail_treasure_bank.h"
#include "pc_p2_retail_treasure_policy.h"
#include "pc_p2_retail_treasure_engine.h"
#include "Pellet.h"
#include "PelletView.h"
#include "Shape.h"
#include "Graphics.h"
#include "Camera.h"
#include "Texture.h"
#include "Stream.h"
#include "system.h"
#include <cstdio>
#include <cstdlib>

bool pc_randomizer_original_input(const std::string&,std::string&,std::string&);
std::string pc_randomizer_original_campaign();
std::string pc_randomizer_campaign_treasure_source();
#if defined(__GNUC__)
extern void pc_p2_equipment_reconcile_courses() __attribute__((weak));
#endif
// Narrow native pool initialization seam; no numbered-pellet config lookup.
struct P2RetailTreasureNativeBody {
    static void init(Pellet* actor,PelletView* view,PelletConfig* profile){actor->initPellet(view,profile);}
};
namespace {
using namespace p2retailtreasure;
p2retailcargo::Config config;AssetBank bank;p2treasure::Catalog catalog;
std::map<std::string,Shape*> shapes;bool ready=false,rollingBack=false,tearingDown=false;
struct Record {p2retail::BirthIdentity birth;std::string id;Pellet* actor=nullptr;PelletConfig* profile=nullptr;};
std::map<std::string,Record> records;
bool fail(std::string& error,const char* message){error=message;return false;}
[[noreturn]] void reject(const char* message){std::fprintf(stderr,"P2 retail cargo: %s\n",message);std::abort();}
bool same(const p2retail::Snapshot& a,const p2retail::Snapshot& b){
    return a.scene==b.scene&&a.cave==b.cave&&a.source==b.source&&a.sourceSha256==b.sourceSha256
        &&a.catalogSha256==b.catalogSha256&&a.floor==b.floor&&a.maxFloor==b.maxFloor&&a.story==b.story&&a.inCave==b.inCave;
}
bool current(const p2retailcargo::Config& c){
    p2retail::Snapshot actual;
    return c.context&&c.births&&c.placement&&pc_p2_retail_treasure_session_matches(c.floor.scene)
        &&c.context(c.floor.scene,actual)&&same(actual,c.floor);
}
bool current(){return ready&&!rollingBack&&!tearingDown&&current(config)&&p2treasurestate::state.source()==bank.identity;}
struct TeardownScope {TeardownScope(){tearingDown=true;}~TeardownScope(){tearingDown=false;}};
class ModelStream final:public RamStream {
public:
    ModelStream(std::string& bytes):RamStream(bytes.data(),int(bytes.size())){}
    void read(void* destination,int size)override {
        if(size<0||mPosition<0||size>mLength-mPosition)reject("verified model parser exceeded source buffer");
        RamStream::read(destination,size);
    }
};
struct HeapScope {int old;HeapScope():old(gsys->setHeap(SYSHEAP_App)){}~HeapScope(){gsys->setHeap(old);}};
struct ShapeScope {
    Shape* previous;immut char* base1;immut char* base2;
    ShapeScope(Shape* shape):previous(gsys->mCurrentShape),base1(gsys->mTextureBase1),base2(gsys->mTextureBase2){
        gsys->mCurrentShape=shape;gsys->setTextureBase("","");
    }
    ~ShapeScope(){gsys->mCurrentShape=previous;gsys->setTextureBase(base1,base2);}
};
class View final:public PelletView {
public:
    View(Shape* shape,const OriginalProfile& profile,Record* record):shape(shape),profile(profile),record(record){}
    void viewKill()override {record->actor=nullptr;record->profile=nullptr;mPellet=nullptr;}
    void viewDraw(Graphics& gfx,immut Matrix4f& transform)override {
        if(!mPellet||!gfx.mCamera)return;
        gfx.useMatrix(Matrix4f::ident,0);shape->updateAnim(gfx,transform,nullptr,mPellet);shape->drawshape(gfx,*gfx.mCamera,nullptr);
    }
    float viewGetBottomRadius()override{return profile.radius;}
    float viewGetHeight()override{return profile.height;}
    Shape* shape;OriginalProfile profile;Record* record;
};
const p2treasure::Entry* source(const p2retail::BirthIdentity& birth,std::string& error){
    if(!current()) {fail(error,"cargo lost selected prepared floor");return nullptr;}
    const auto* cave=p2retail::descriptor(config.floor.cave);p2retail::BirthIdentity expected;
    if(!cave||!config.births->expectedBirth(*cave,config.floor.floor,config.floor.scene,birth.row,birth.ordinal,expected,error))return nullptr;
    const auto* entry=looseSource(catalog,*cave,config.floor.floor,birth,config.floor.scene,config.floor,expected);
    if(!entry)fail(error,"cargo lacks independently issued literal loose source");return entry;
}
bool completed(Pellet* actor,Suckable* receiver,std::string& error){
    if(!current()||!pc_p2_original_pod_completed(actor,receiver,config.floor.scene))return fail(error,"cargo has no native completed Pod suction");
    Record* owned=nullptr;
    for(auto& item:records)if(item.second.actor==actor){owned=&item.second;break;}
    if(!owned||actor->mConfig!=owned->profile)return fail(error,"completed cargo original body binding changed");
    const auto* entry=source(owned->birth,error);
    if(!entry||entry->id!=owned->id||actor->mConfig->mCarryMinPikis()!=entry->strength
       ||actor->mConfig->mCarryMaxPikis()!=entry->slots)return fail(error,"completed cargo source profile changed");
    const auto receipt=p2treasurestate::state.credit(catalog,entry->id,entry->value);
    if(receipt==p2treasurestate::Credit::Invalid)return fail(error,"canonical cargo receipt refused");
#if defined(__GNUC__)
    if(receipt==p2treasurestate::Credit::Added&&pc_p2_equipment_reconcile_courses)pc_p2_equipment_reconcile_courses();
#endif
    std::printf("P2_RETAIL_TREASURE_RECEIPT id=%s value=%d new=%d native_suction_completed=1 seeds=0\n",entry->id.c_str(),entry->value,int(receipt==p2treasurestate::Credit::Added));
    error.clear();return true; // Pod owner kills after callback, never here.
}
void clear(){records.clear();shapes.clear();bank={};catalog={};config={};ready=false;}
}
bool pc_p2_retail_treasure_cargo_preflight(const p2retailcargo::Config& c,std::string& error){
    if(tearingDown)return fail(error,"cargo preflight during receiver teardown");
    if(ready)return same(config.floor,c.floor)&&current()?true:fail(error,"cargo floor must retire before another preflight");
    if(rollingBack||!records.empty()||!current(c)||!gsys||!pelletMgr)return fail(error,"cargo preflight lacks exclusive authenticated floor/resources");
    std::string master;AssetBank next;p2treasure::Catalog nextCatalog;
    if(!pc_randomizer_original_input("p2-treasure-placements.txt",master,error)
       ||!verifyAssetBank(master,pc_randomizer_original_campaign(),pc_randomizer_original_input,nextCatalog,next,error))return false;
    if(next.identity!=pc_randomizer_campaign_treasure_source()||next.identity!=p2treasurestate::state.source())return fail(error,"cargo bank differs from selected treasury source");
    std::map<std::string,Shape*> nextShapes;HeapScope heap;
    for(const auto& row:next.rows){
        const std::string role="assets/dataDir/courses/pikmin2treasures/"+row.id+".mod";std::string bytes;
        if(!pc_randomizer_original_input(role,bytes,error)||p2treasureplacements::hash(bytes)!=row.modelHash)return fail(error,"cargo model selected bytes changed");
        ModelStream stream(bytes);auto* shape=new Shape;ShapeScope shapeScope(shape);
        shape->mName=StdSystem::stringDup(role.c_str());shape->read(stream);
        shape->resolveTextureNames();shape->initialise();shape->initIni(true);shape->optimize();
        for(int i=0;i<shape->mTexAttrCount;++i)if(shape->mTexAttrList[i].mTexture)shape->mTexAttrList[i].mTexture->attach();
        nextShapes.emplace(row.id,shape);
    }
    config=c;bank=std::move(next);catalog=std::move(nextCatalog);shapes=std::move(nextShapes);ready=true;error.clear();return true;
}
bool pc_p2_retail_treasure_cargo_birth(const p2retail::BirthIdentity& birth,Pellet*& out,std::string& error){
    const auto* entry=source(birth,error);if(!entry)return false;
    if(records.count(birth.instance)||p2treasurestate::state.seen(catalog,entry->id))return fail(error,"cargo incarnation exists or requires typed consumed binding");
    const AssetRow* asset=nullptr;for(const auto& row:bank.rows)if(row.id==entry->id){asset=&row;break;}
    if(!asset)return fail(error,"literal loose source asset is outside selected bank");
    Vector3f position;float yaw=0;
    if(!config.placement(config.floor.scene,birth.row,birth.ordinal,position,yaw,error))return false;
    for(float value:{position.x,position.y,position.z,yaw})if(!std::isfinite(value))return fail(error,"literal cargo placement invalid");
    HeapScope heap;
    auto* profile=new PelletConfig;profile->mModelId.setID('p2tr');profile->mPelletId.setID('p2tr');
    profile->mPelletType.mValue=PELTYPE_Corpse;profile->mPelletColor.mValue=PELCOLOR_NULL;
    profile->mCarryMinPikis.mValue=entry->strength;profile->mCarryMaxPikis.mValue=entry->slots;
    profile->mMatchingOnyonSeeds.mValue=0;profile->mNonMatchingOnyonSeeds.mValue=0;
    profile->mAnimSoundID.mValue=-1;profile->mBounceSoundID.mValue=-1;profile->mPelletScale.mValue=1;
    profile->mCarryInfoHeight.mValue=asset->profile.height;
    auto* actor=static_cast<Pellet*>(pelletMgr->birth());if(!actor)return fail(error,"native original cargo pool exhausted");
    auto inserted=records.emplace(birth.instance,Record{birth,entry->id,actor,profile});
    auto* view=new View(shapes.at(entry->id),asset->profile,&inserted.first->second);view->mPellet=actor;
    P2RetailTreasureNativeBody::init(actor,view,profile);actor->mGenerator=nullptr;actor->init(position);actor->mFaceDirection=yaw;actor->startAI(TRUE);
    if(!pc_p2_original_pod_bind_cargo(actor,birth,config.floor.scene,completed,error)){
        actor->kill(false);records.erase(inserted.first);return false;
    }
    out=actor;error.clear();return true;
}
bool pc_p2_retail_treasure_cargo_absent(const p2retail::BirthIdentity& birth,const std::string& receipt,std::string& error){
    const auto* entry=source(birth,error);
    if(!entry||entry->id!=receipt||!p2treasurestate::state.seen(catalog,receipt))return fail(error,"cargo consumed binding has no canonical source receipt");
    const auto owned=records.find(birth.instance);
    if(owned!=records.end()&&owned->second.actor)return fail(error,"consumed source still has a native cargo actor");
    error.clear();return true;
}
bool pc_p2_retail_treasure_cargo_carry_radius(Pellet* actor,float& radius){
    for(const auto& item:records)if(item.second.actor==actor){
        if(!current()||!actor||actor->mConfig!=item.second.profile)reject("owned cargo carry circle lost source authority");
        for(const auto& row:bank.rows)if(row.id==item.second.id){radius=row.profile.carryRadius;return true;}
        reject("owned cargo carry circle has no original profile");
    }
    return false;
}
bool pc_p2_retail_treasure_cargo_abort_prepared(std::string& error){
    return pc_p2_retail_treasure_cargo_abort_prepared([](std::string& e){return pc_p2_original_pod_abort_prepared(config.floor.scene,e);},error);
}
bool pc_p2_retail_treasure_cargo_abort_prepared(p2retailcargo::PodTeardown teardown,std::string& error){
    if(!current())return fail(error,"cargo rollback has no selected floor");
    if(!teardown||!pc_p2_original_pod_can_abort_prepared(config.floor.scene))
        return fail(error,"cargo rollback has no uncommitted matching receiver");
    TeardownScope transaction;
    if(!teardown(error))return false;
    if(pc_p2_original_pod_owned())return fail(error,"receiver owner did not finish provisional teardown");
    rollingBack=true;for(auto& item:records)if(item.second.actor)item.second.actor->kill(false);rollingBack=false;
    clear();error.clear();return true;
}
bool pc_p2_retail_treasure_cargo_release_collected(std::string& error){
    return pc_p2_retail_treasure_cargo_release_collected([](std::string& e){return pc_p2_original_pod_release(e);},error);
}
bool pc_p2_retail_treasure_cargo_can_release_collected(std::string& error){
    if(!current())return fail(error,"cargo release has no selected floor");
    for(const auto& item:records)if(!p2treasurestate::state.seen(catalog,item.second.id))return fail(error,"uncollected original cargo needs actual graph retention/restore");
    p2originalpod::Snapshot receiver;
    if(!pc_p2_original_pod_snapshot(config.floor.scene,receiver)||!receiver.committed||!same(receiver.floor,config.floor))
        return fail(error,"cargo release has no committed matching receiver");
    if(pc_p2_original_pod_pending()||!receiver.pending.empty())return fail(error,"receiver still owns unfinished cargo or a transaction");
    error.clear();return true;
}
bool pc_p2_retail_treasure_cargo_release_collected(p2retailcargo::PodTeardown teardown,std::string& error){
    if(!teardown)return fail(error,"cargo release has no receiver teardown operation");
    if(!pc_p2_retail_treasure_cargo_can_release_collected(error))return false;
    TeardownScope transaction;
    if(!teardown(error))return false;
    if(pc_p2_original_pod_owned())return fail(error,"receiver owner did not finish collected teardown");
    rollingBack=true;for(auto& item:records)if(item.second.actor)item.second.actor->kill(false);rollingBack=false;
    clear();error.clear();return true;
}
