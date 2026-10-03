#include "pc_p2_original_barrel_native.h"
#include "pc_p2_surface_water_drain.h"
#include "pc_p2_surface_water.h"
#include "BuildingItem.h"
#include "CreatureNode.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "MapMgr.h"
#include "GameCoreSection.h"
#include "Interactions.h"
#include "pc_p2_white.h"
#include "pc_p2_purple.h"
#include "Stream.h"
#include "gameflow.h"
#include "sysNew.h"
#include "netplay/pc_netplay_sha256.h"
#include <map>
#include <set>
#include <fstream>
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
namespace {
using namespace p2original;
constexpr unsigned type=0x70326261,version=0x42413031; // p2ba / BA01; source barl
std::map<unsigned,BarrelRecord> records;
std::map<const Generator*,unsigned> generators;
bool admitted=false;
struct Clip {std::vector<Shape*> shapes;std::vector<float> frames;float duration=0;};
Clip waitClip,deadClip;
class SourceBarrel;
std::vector<SourceBarrel*> bodies;
std::vector<SourceBarrel*> allocations; // PC malloc bodies survive App-heap reset.
std::vector<SourceBarrel*> pendingRetirement;
std::map<unsigned,SourceBarrel*> carriers; // No physical node; typed native cache only.
std::string waterCourse,waterSha;
[[noreturn]] void die(const char* why){std::fprintf(stderr,"P2_ORIGINAL_BARREL_FAIL %s\n",why);std::fflush(nullptr);std::abort();}
const BarrelRecord& row(unsigned uid){auto i=records.find(uid);if(i==records.end())die("barrel source identity absent");return i->second;}
Shape* pose(const Clip& clip,float frame){auto at=std::upper_bound(clip.frames.begin(),clip.frames.end(),frame);size_t index=at==clip.frames.begin()?0:size_t(at-clip.frames.begin()-1);return clip.shapes.at(index);}
class SourceBarrel final:public BuildingItem {
public:
 unsigned uid;BarrelState state;float idleFrame=0;ObjCollInfo sphere;CreatureNode* node=nullptr;CreatureNode* allocatedNode=nullptr;
 explicit SourceBarrel(unsigned id):BuildingItem(OBJTYPE_SluiceSoft,new BuildingItemProp,nullptr,nullptr),uid(id){mNumStages=1;mCurrStage=0;mWayPoint=nullptr;mMaxHealth=row(id).life;state.health=mMaxHealth;}
 ~SourceBarrel(){delete allocatedNode;delete static_cast<BuildingItemProp*>(mProps);}
 bool isAlive()override{return state.phase==BarrelPhase::Normal;}
 bool isCompleted()override{return state.phase!=BarrelPhase::Normal;}
 f32 getBoundingSphereRadius()override{return 43;}
 f32 getiMass()override{return 0;}
 void startAI(int)override{
  mSRT.s.set(1,1,1);mSRT.r.set(0,0,0);mFaceDirection=0;mCollisionRadius=43;mHealth=state.health;
  // Authored coll.txt is one joint0 sphere radius43. 'gate' only routes the
  // native work AI collision message; source barl identity remains unchanged.
  sphere.mId.setID('gate');sphere.mCode.setID('____');sphere.mJointIndex=-1;sphere.mRadius=43;
  mCollInfo=&mBuildCollision;mBuildCollision.initInfoTree(&sphere,mBuildParts,mBuildPartIDs);auto* p=mCollInfo->getSphere('gate');if(!p)die("barrel native sphere missing");p->mIsUpdateActive=false;p->mIsStickEnabled=false;p->mCentre=mSRT.t;p->mRadius=43;
  mItemShape=pose(waitClip,0);mSeContext=&mBuildSFX;mSeContext->setContext(this,JACEVENT_Build);disableAICulling();
 }
 bool stimulate(immut Interaction& interaction)override{
  auto* attack=dynamic_cast<const InteractAttack*>(&interaction);
  if(!attack||!attack->mOwner||attack->mOwner->mObjType==OBJTYPE_Navi)return false;
  auto before=state.phase;if(!barrelDamage(state,attack->mDamage))return false;mHealth=state.health;
  if(before!=state.phase){mCurrStage=1;if(mSeContext)mSeContext->releaseEvent();std::printf("P2_ORIGINAL_BARREL_DEATH uid=%u health=%.6f pending_source_clip=1\n",uid,state.health);}
  return true;
 }
 void doAnimation()override{
  if(state.phase==BarrelPhase::Normal){idleFrame=0;mItemShape=pose(waitClip,0);return;} // retail idle anim speed0
  if(barrelAnimate(state,gsys->getFrameTime(),deadClip.duration)){
   mItemShape=pose(deadClip,state.animationFrame);finishDrain();pendingRetirement.push_back(this);return;
  }
  mItemShape=pose(deadClip,state.animationFrame);
 }
 void finishDrain(){
  int box=pc_p2_surface_water_box(mSRT.t,43);
  if(box>=0)pc_p2_surface_water_start_down(waterCourse,waterSha,box);
  std::printf("P2_ORIGINAL_BARREL_RETIRED uid=%u source_water_box=%d source_body_radius=43\n",uid,box);
 }
 void update()override{
  if(GameCoreSection::inPause())return;
  mGrid.updateGrid(mSRT.t);mGrid.updateAIGrid(mSRT.t,false);
  if(mSeContext)mSeContext->update();mHealth=state.health;
  // ObjectMgr calls update, not doAnimation separately. Tick the source clip
  // explicitly without inheriting P1 wall physics or its SimpleAI machine.
  if(!mIsFrozen)doAnimation();
 }
 void refresh(Graphics& g)override{ItemCreature::refresh(g);}
 void refresh2d(Graphics&)override{}
 void doKill()override{if(node){node->del();node=nullptr;}mCollInfo=nullptr;bodies.erase(std::remove(bodies.begin(),bodies.end(),this),bodies.end());pendingRetirement.erase(std::remove(pendingRetirement.begin(),pendingRetirement.end(),this),pendingRetirement.end());if(mSeContext)mSeContext->releaseEvent();mLifeGauge.countOff();}
 void doSave(RandomAccessStream& s)override{std::vector<std::uint8_t> bytes;std::string e;if(!barrelExport(row(uid),state,deadClip.duration,bytes,e)||s.getPending()<int(bytes.size()))die("barrel creature cache invalid/full");for(auto v:bytes)s.writeByte(v);}
 void doLoad(RandomAccessStream& s)override{std::string e;BarrelState next;if(!readState(s,next,e))die(e.c_str());restore(next);}
 bool readState(RandomAccessStream& s,BarrelState& out,std::string& e){if(s.getPending()<112){e="truncated barrel cache";return false;}std::vector<std::uint8_t> bytes(112);for(auto& v:bytes)v=s.readByte();return barrelImport(row(uid),bytes,deadClip.duration,out,e);}
 void restore(const BarrelState& next){state=next;mHealth=state.health;mCurrStage=state.phase==BarrelPhase::Normal?0:1;mItemShape=pose(state.phase==BarrelPhase::Normal?waitClip:deadClip,state.animationFrame);}
};
GenObject* make(){return new GenObjectOriginalBarrel;}
bool readGeometry(std::string& e){
 std::ifstream in("assets/p2-original/barrel/barrel-bank.txt");std::string magic;if(!(in>>magic)||magic!="P2_ORIGINAL_BARREL_GEOMETRY_1"){e="barrel source pose-bank absent";return false;}
 Clip* clips[]={&waitClip,&deadClip};const char* names[]={"wait","dead"};
 for(int c=0;c<2;++c){std::string name;unsigned count=0;float duration=0;if(!(in>>name>>count>>duration)||name!=names[c]||count<2||count>64||!std::isfinite(duration)||duration<=0||duration>10000){e="invalid barrel clip header";return false;}Clip next;next.duration=duration;for(unsigned i=0;i<count;++i){float f;if(!(in>>f)||!std::isfinite(f)||f<0||f>(c?duration:duration-1)||(!next.frames.empty()&&f<=next.frames.back())){e="invalid barrel source pose frames";return false;}next.frames.push_back(f);}if(next.frames.front()!=0||next.frames.back()!=(c?duration:duration-1)){e="barrel terminal pose absent";return false;}for(unsigned i=0;i<count;++i){char path[128];std::snprintf(path,sizeof(path),"p2-original/barrel/%s_%02u.mod",names[c],i);Shape* shape=gameflow.loadShape(path,false);if(!shape){e="barrel source pose mesh absent";return false;}next.shapes.push_back(shape);}*clips[c]=std::move(next);}
 if(in>>magic){e="trailing barrel geometry manifest";return false;}return true;
}
void cache(GenObjectOriginalBarrel& o,RandomAccessStream& s,bool write){unsigned char b[104]{};if(write){auto d=barrelDigest(row(o.uid));std::memcpy(b,"BAC1",4);std::memcpy(b+4,d.data(),64);for(int i=0;i<4;++i)b[68+i]=static_cast<unsigned char>(o.uid>>(i*8));pc_netplay_sha::sha256(b,72,b+72);}if(s.getPending()<104)die("barrel generator cache truncated/full");if(write){for(auto v:b)s.writeByte(v);return;}for(auto& v:b)v=s.readByte();unsigned char checksum[32];pc_netplay_sha::sha256(b,72,checksum);if(std::memcmp(b,"BAC1",4)||std::memcmp(checksum,b+72,32))die("barrel generator cache invalid");unsigned id=0;for(int i=0;i<4;++i)id|=unsigned(b[68+i])<<(i*8);auto d=barrelDigest(row(id));if(std::memcmp(d.data(),b+4,64))die("barrel generator source mismatch");o.uid=id;}
}
bool pc_p2_original_barrel_install(const std::vector<p2original::BarrelRecord>& list,std::string& e){if(!records.empty()||!bodies.empty()||!generators.empty()||list.empty()||list.size()>4096){e="barrel authority installed/incomplete";return false;}std::map<unsigned,p2original::BarrelRecord> next;for(const auto& r:list)if(!p2original::validateBarrel(r,e)||!next.emplace(r.uid,r).second){e="invalid/duplicate barrel source";return false;}records.swap(next);return true;}
void pc_p2_original_barrel_finish_updates(){
 auto pending=std::move(pendingRetirement);pendingRetirement.clear();
 for(auto* b:pending){auto* g=b->mGenerator;b->kill(false);
  // Actual death bookkeeping runs once above. Retain only an unlinked source
  // cache carrier so GeneratorCache can write the retired typed state.
  if(g){g->mLatestSpawnCreature=b;g->mAliveCount=0;b->mGenerator=g;carriers[b->uid]=b;}
 }
}
void pc_p2_original_barrel_before_teardown(){
 auto physical=bodies;
 for(auto* b:physical){auto* g=b->mGenerator;b->mGenerator=nullptr;b->kill(false);if(g&&g->mLatestSpawnCreature==b)g->mLatestSpawnCreature=nullptr;}
 pendingRetirement.clear();
 for(auto* b:allocations){b->mSearchContext.exit();auto* g=b->mGenerator;if(g&&g->mLatestSpawnCreature==b)g->mLatestSpawnCreature=nullptr;b->mGenerator=nullptr;}
 carriers.clear();
}
void pc_p2_original_barrel_unload(){if(!bodies.empty()||!pendingRetirement.empty()||!carriers.empty())die("barrel live teardown required before unload");for(auto* b:allocations)delete b;allocations.clear();admitted=false;records.clear();generators.clear();bodies.clear();pendingRetirement.clear();carriers.clear();waitClip={};deadClip={};waterCourse.clear();waterSha.clear();}
void pc_p2_original_barrel_register(){auto* f=GenObjectFactory::factory;if(!f)die("barrel factory absent");for(int i=0;i<f->mSpawnerCount;++i)if(f->mSpawnerInfo[i].mID==type)return;if(f->mSpawnerCount>=f->mMaxSpawners)die("barrel factory capacity");f->registerMember(type,make,"original P2 barrel",version);}
GenObjectOriginalBarrel::GenObjectOriginalBarrel():GenObject(type,"original P2 barrel"){}
void GenObjectOriginalBarrel::doRead(RandomAccessStream& s){if(mVersion!=version)die("barrel adapter version mismatch");if(!Generator::ramMode){uid=unsigned(s.readInt());row(uid);}}
void GenObjectOriginalBarrel::doWrite(RandomAccessStream& s){if(!Generator::ramMode){row(uid);s.writeInt(int(uid));}}
void GenObjectOriginalBarrel::ramLoadParameters(RandomAccessStream& s){cache(*this,s,false);}
void GenObjectOriginalBarrel::ramSaveParameters(RandomAccessStream& s){cache(*this,s,true);}
void GenObjectOriginalBarrel::updateUseList(Generator*,int){row(uid);}
bool pc_p2_original_barrel_preflight(const std::vector<Generator*>& list,std::string& e){
 if(admitted||!bodies.empty()||records.empty()||list.size()!=records.size()||!itemMgr||!itemMgr->mMeltingPotMgr||!gsys||!mapMgr){e="barrel full inventory/managers absent";return false;}
 p2water::DrainSnapshot water;if(!pc_p2_surface_water_snapshot(water)){e="barrel original source water not admitted";return false;}
 std::set<unsigned> seen;std::map<const Generator*,unsigned> next;
 for(auto* g:list){auto* o=g?dynamic_cast<GenObjectOriginalBarrel*>(g->mGenObject):nullptr;if(!o||!records.count(o->uid)||!seen.insert(o->uid).second){e="unknown/duplicate barrel generator";return false;}const auto& r=row(o->uid);if(r.sourceKey.substr(0,r.sourceKey.find('/'))!=water.course||g->mCarryOverFlags!=r.reserved||g->mRespawnInterval!=r.resurrectionDays||g->mDayLimit!=r.dayLimit){e="barrel source metadata/water course mismatch";return false;}next.emplace(g,r.uid);}
 if(!readGeometry(e))return false;
 for(const auto& a:next){auto* g=const_cast<Generator*>(a.first);const auto& r=row(a.second);g->mGenPosition.set(r.position[0],r.position[1],r.position[2]);g->mGenOffset.set(r.offset[0],r.offset[1],r.offset[2]);g->_70=r.uid;}
 waterCourse=water.course;waterSha=water.sourceSha;generators.swap(next);admitted=true;e.clear();return true;
}
Creature* GenObjectOriginalBarrel::birth(BirthInfo& info){if(!admitted||!info.mGenerator||info.mGenerator->mGenObject!=this||!generators.count(info.mGenerator)||generators.at(info.mGenerator)!=uid)die("barrel birth without complete source admission");for(auto* b:bodies)if(b->uid==uid)die("duplicate physical barrel");const auto& r=row(uid);int heap=gsys->setHeap(SYSHEAP_App);auto* b=new SourceBarrel(uid);allocations.push_back(b);Vector3f p(r.position[0]+r.offset[0],r.position[1]+r.offset[1],r.position[2]+r.offset[2]);b->init(p);b->mGenerator=info.mGenerator;b->startAI(0);b->node=new CreatureNode;b->allocatedNode=b->node;b->node->mCreature=b;itemMgr->mMeltingPotMgr->mRootNode.add(b->node);bodies.push_back(b);gsys->setHeap(heap);std::printf("P2_ORIGINAL_BARREL_BIRTH uid=%u health=4000 authored_radius=43 source_rotation_ignored=1 retail_geometry=1\n",uid);return b;}
bool pc_p2_original_barrel_owned(const Creature* c){return std::find(bodies.begin(),bodies.end(),c)!=bodies.end();}
float pc_p2_original_barrel_work_damage(Piki* p){if(!p||!pikiMgr||!pikiMgr->mPikiParms)die("barrel Pikmin source damage absent");if(pc_p2_is_white(p))return pc_p2_white_attack();if(pc_p2_is_purple(p))return pc_p2_purple_attack();auto& a=pikiMgr->mPikiParms->mPikiParms;return p->mColor==Red?a.mRedAttackPower():p->mColor==Blue?a.mBlueAttackPower():a.mYellowAttackPower();}
bool pc_p2_original_barrel_snapshot(const Creature* c,p2original::BarrelState& s,std::string& id){auto read=[&](SourceBarrel* b){if(b!=c)return false;s=b->state;const auto& r=row(b->uid);id=r.sourceSha+":"+r.sourceKey;return true;};for(auto* b:bodies)if(read(b))return true;for(auto& a:carriers)if(read(a.second))return true;return false;}
bool pc_p2_original_barrel_generator_init(Generator* g,bool& handled,std::string& e){auto* o=g?dynamic_cast<GenObjectOriginalBarrel*>(g->mGenObject):nullptr;handled=o!=nullptr;if(!handled)return true;if(!admitted||!generators.count(g)||generators.at(g)!=o->uid){e="barrel init without admission";return false;}g->mAliveCount=0;g->mLatestSpawnCreature=nullptr;if(g->isExpired()||Generator::ramMode)return true;BirthInfo info;info.mGenerator=g;g->mLatestSpawnCreature=o->birth(info);g->mAliveCount=1;return true;}
bool pc_p2_original_barrel_generator_load(Generator* g,RandomAccessStream& stream,bool& handled,std::string& e){
 auto* o=g?dynamic_cast<GenObjectOriginalBarrel*>(g->mGenObject):nullptr;handled=o!=nullptr;if(!handled)return true;
 if(!admitted||!generators.count(g)||generators.at(g)!=o->uid||g->mLatestSpawnCreature){e="barrel load without fresh admitted generator";return false;}
 if(stream.getPending()<112){e="truncated barrel creature cache";return false;}std::vector<std::uint8_t> bytes(112);for(auto& v:bytes)v=stream.readByte();p2original::BarrelState next;if(!p2original::barrelImport(row(o->uid),bytes,deadClip.duration,next,e))return false;
 if(g->isExpired()){g->mAliveCount=0;return true;}
 if(next.phase==p2original::BarrelPhase::Retired){
  // Cold restore has no physical birth/death callback, calendar mutation or RNG.
  const auto& r=row(o->uid);int heap=gsys->setHeap(SYSHEAP_App);auto* b=new SourceBarrel(o->uid);allocations.push_back(b);b->mSRT.t.set(r.position[0]+r.offset[0],r.position[1]+r.offset[1],r.position[2]+r.offset[2]);b->mGenerator=g;b->restore(next);b->finishDrain();g->mLatestSpawnCreature=b;g->mAliveCount=0;carriers[b->uid]=b;gsys->setHeap(heap);return true;
 }
 BirthInfo info;info.mGenerator=g;auto* b=static_cast<SourceBarrel*>(o->birth(info));g->mLatestSpawnCreature=b;g->mAliveCount=1;b->restore(next);return true;
}
