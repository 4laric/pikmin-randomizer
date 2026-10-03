#include "pc_p2_original_pod.h"
#include "pc_p2_original_pod_registry.h"
#include "pc_p2_original_pod_input.h"
#include "Suckable.h"
#include "Pellet.h"
#include "PelletState.h"
#include "DynParticle.h"
#include "CreatureNode.h"
#include "Collision.h"
#include "Graphics.h"
#include "Camera.h"
#include "Texture.h"
#include "Route.h"
#include "Shape.h"
#include "Stream.h"
#include "system.h"
#include "sysNew.h"
#include "netplay/pc_netplay_sha256.h"
#include <cmath>
#include <map>
#include <cstdio>
#include <cstdlib>

namespace {
using namespace p2originalpod;
struct HeapScope {int previous;HeapScope():previous(gsys->setHeap(SYSHEAP_App)){}~HeapScope(){gsys->setHeap(previous);}};
struct ShapeScope {
 Shape* previous;immut char* base1;immut char* base2;
 ShapeScope(Shape* shape):previous(gsys->mCurrentShape),base1(gsys->mTextureBase1),base2(gsys->mTextureBase2){
  gsys->mCurrentShape=shape;gsys->setTextureBase("","");
 }
 ~ShapeScope(){gsys->mCurrentShape=previous;gsys->setTextureBase(base1,base2);}
};
bool reject(std::string& e,const char* s){e=s;return false;}
void fail(const char* s){std::fprintf(stderr,"P2_ORIGINAL_POD refusal: %s\n",s);std::fflush(nullptr);std::abort();}
bool same(const p2retail::Snapshot& a,const p2retail::Snapshot& b){
 return a.scene==b.scene&&a.cave==b.cave&&a.floor==b.floor&&a.maxFloor==b.maxFloor
  &&a.source==b.source&&a.sourceSha256==b.sourceSha256&&a.catalogSha256==b.catalogSha256
  &&a.story==b.story&&a.inCave==b.inCave;
}
bool source(const p2retail::Snapshot& f){
 const auto* c=p2retail::descriptor(f.cave);
 return c&&p2retail::definition(*c,f.floor)&&f.inCave&&f.story
  &&f.source==c->source&&f.sourceSha256==c->sourceSha256
  &&f.catalogSha256==c->catalogSha256&&f.maxFloor==c->maxFloor
  &&!f.scene.seed.empty()&&!f.scene.visit.empty()&&f.scene.serial&&p2retail::hex64(f.scene.layoutSha256);
}
class ModelStream final:public RamStream {
public:
 ModelStream(std::string& bytes):RamStream(bytes.data(),int(bytes.size())){}
 void read(void* destination,int size)override{
  if(size<0||mPosition<0||size>mLength-mPosition)fail("pod_verified_model_parser_bounds");
  RamStream::read(destination,size);
 }
};
class Pod final:public Suckable {
public:
 Pod(CreatureProp* prop,Shape* shape,const Config& c,int route)
  :Suckable(OBJTYPE_P2Pod,prop),bank(shape),waypoint(route){
  ItemCreature::init(Vector3f(c.x,c.y,c.z));mSRT.r.set(0,c.yaw,0);mSRT.s.set(1,1,1);
  mHealth=1;disableGravity();setCreatureFlag(CF_DisableAutoFaceDir);
  // Original pod/texts.szs coll.txt: four joint spheres flattened into the
  // exact model bind pose. Static presentation and collision share that pose.
  const float radius[]={31,22,10,13};
  const Vector3f offset[]={Vector3f(-.0012467411f,14.3038835f,24.6685720f),
   Vector3f(.000694147f,3.47091705f,22.7589036f),Vector3f(0,-2,10),
   Vector3f(-.0024818517f,21.1975895f,25.8838155f)};
  ObjCollInfo* nodes[4];
  for(unsigned i=0;i<4;++i){nodes[i]=new ObjCollInfo;nodes[i]->mId.setID('pod0'+i);
   nodes[i]->mCode.setID('____');nodes[i]->mJointIndex=-1;nodes[i]->mRadius=radius[i];
   nodes[i]->mCentrePosition=offset[i];if(i)nodes[0]->add(nodes[i]);}
  mCollInfo=new CollInfo(4);mCollInfo->initInfoTree(nodes[0]);
  for(unsigned i=0;i<4;++i){auto* p=mCollInfo->getSphere('pod0'+i);p->mIsUpdateActive=false;
   p->mRadius=radius[i];p->mJointMatrix.makeIdentity();
   p->mCentre.set(c.x+offset[i].x*std::cos(c.yaw)+offset[i].z*std::sin(c.yaw),
    c.y+offset[i].y,c.z-offset[i].x*std::sin(c.yaw)+offset[i].z*std::cos(c.yaw));}
  update();
 }
 Vector3f getGoalPos()override{return mSRT.t;}
 f32 getGoalPosRadius()override{return 31.0f;} // Native route arrival uses source bounding radius.
 Vector3f getSuckPos()override{return mSRT.t+Vector3f(0,95,0);} // Onyon::getSuckPos, non-Ufo.
 int getRouteIndex()override{return waypoint;}
 f32 getiMass()override{return 0;}
 f32 getSize()override{return 31;}
 bool needShadow()override{return false;}
 bool isAlive()override{return live;}
 bool isVisible()override{return live;}
 bool isAtari()override{return live;}
 // Cargo crosses the solid body to its source goal point; captains/Pikmin
 // still collide with the original static sphere tree through the manager.
 bool ignoreAtari(Creature* c)override{return c&&c->mObjType==OBJTYPE_Pellet;}
 bool stimulate(immut Interaction&)override{return false;}
 void startAI(int)override{}
 void doAI()override{}
 void doAnimation()override{}
 void update()override{mVelocity.set(0,0,0);mVolatileVelocity.set(0,0,0);
  mGrid.updateGrid(mSRT.t);mGrid.updateAIGrid(mSRT.t,false);}
 void refresh(Graphics& gfx)override{
  if(!live||!gfx.mCamera)return;Matrix4f root,view;root.makeSRT(mSRT.s,mSRT.r,mSRT.t);
  gfx.mCamera->mLookAtMtx.multiplyTo(root,view);gfx.useMatrix(Matrix4f::ident,0);
  bank->updateAnim(gfx,view,nullptr,this);bank->drawshape(gfx,*gfx.mCamera,nullptr);
 }
 // No arrival-time rewards. P1 UfoPart's early suckMe must never reach this.
 void suckMe(Pellet*)override{}
 void finishSuck(Pellet*)override{}
 Shape* bank;int waypoint;bool live=false; // Prepared bodies are not observable gameplay.
};
using Phase=p2originalpod::CargoPhase;
using Cargo=p2originalpod::CargoBinding;
Config config;ContextProvider contextProvider;Shape* shape=nullptr;Pod* pod=nullptr;
CreatureNode* node=nullptr;MeltingPotMgr* manager=nullptr;
p2originalpod::Ownership ownership;
auto& cargo=ownership.live;
auto& lostCargo=ownership.lost;
bool prepared=false,committed=false,everSucked=false,retaining=false;Pellet* completing=nullptr;
struct RetainScope {RetainScope(){retaining=true;}~RetainScope(){retaining=false;}};
bool current(p2retail::Snapshot* out=nullptr){
 p2retail::Snapshot actual;
 if(!prepared||!contextProvider||!contextProvider(config.floor.scene,actual)||!source(actual)||!same(actual,config.floor))return false;
 if(out)*out=actual;return true;
}
bool quiet(const Vector3f& v){
 return std::isfinite(v.x)&&std::isfinite(v.y)&&std::isfinite(v.z)
  &&std::fabs(v.x)<=.01f&&std::fabs(v.y)<=.01f&&std::fabs(v.z)<=.01f;
}
bool moving(Pellet* actor,const Cargo& c){
 if(c.phase==Phase::Completed)return false;
 if(c.phase!=Phase::Bound)return true;
 if(!actor||!actor->isAlive()||actor->getState()!=PELSTATE_Normal
  ||actor->mCarrierCounter>0||actor->getPickOffset()!=0||!actor->onGround()
  ||!quiet(actor->mVelocity)||!quiet(actor->mVolatileVelocity)
  ||!quiet(actor->mAngularVelocity)||!quiet(actor->mAngularMomentum)
  ||!quiet(actor->mAngularImpulseAccum))return true;
 unsigned count=0;
 for(auto* particle=actor->mParticleList;particle;particle=particle->mNextParticle){
  if(++count>actor->mParticleCount||!quiet(particle->mWorldVelocity))return true;
 }
 return count!=actor->mParticleCount;
}
void clear(){
 if(pod)pod->live=false;if(node){node->del();node->mCreature=nullptr;}
 pod=nullptr;node=nullptr;manager=nullptr;shape=nullptr;cargo.clear();lostCargo.clear();contextProvider={};
 config={};prepared=committed=everSucked=false;completing=nullptr;
 // App-heap resources share the floor lifetime, never free borrowed textures.
}
}

bool pc_p2_original_pod_preflight(const p2originalpod::Config& c,ContextProvider provider,std::string& e){
 if(prepared)return reject(e,"pod_already_prepared");
 if(!gsys||!itemMgr||!itemMgr->mMeltingPotMgr||!routeMgr||!provider||!c.births||!c.input||!source(c.floor)
  ||c.baseGenType!=7||!std::isfinite(c.x)||!std::isfinite(c.y)||!std::isfinite(c.z)||!std::isfinite(c.yaw))return reject(e,"pod_source_or_managers");
 p2retail::Snapshot actual;if(!provider(c.floor.scene,actual)||!same(actual,c.floor))return reject(e,"pod_unverified_scene");
 auto* wp=routeMgr->findNearestWayPoint('test',Vector3f(c.x,c.y,c.z),false);
 if(!wp||!routeMgr->getWayPoint('test',wp->mIndex))return reject(e,"pod_route_missing");
 std::string modelBytes,provenance;
 if(!selectedResource(c.input,c.model,convertedModelSha256,modelBytes,e)
  ||!selectedResource(c.input,c.sourceArchive,archiveSha256,provenance,e)
  ||!selectedResource(c.input,c.sourceModel,originalModelSha256,provenance,e)
  ||!selectedResource(c.input,c.sourceCollision,originalCollisionSha256,provenance,e)
  ||!selectedResource(c.input,c.sourceTexts,originalTextsSha256,provenance,e))return false;
 HeapScope heap;ModelStream stream(modelBytes);Shape* loaded=new Shape;ShapeScope scope(loaded);
 loaded->mName=StdSystem::stringDup(c.model.c_str());loaded->read(stream);
 loaded->resolveTextureNames();loaded->initialise();loaded->initIni(true);loaded->optimize();
 if(!loaded||loaded->mJointCount!=1)return reject(e,"pod_converted_model_missing");
 for(int i=0;i<loaded->mTexAttrCount;++i)if(loaded->mTexAttrList[i].mTexture)loaded->mTexAttrList[i].mTexture->attach();
 config=c;contextProvider=std::move(provider);shape=loaded;prepared=true;e.clear();return true;
}
bool pc_p2_original_pod_birth(const Config& c,ContextProvider provider,std::string& e){
 if(!prepared&&!pc_p2_original_pod_preflight(c,std::move(provider),e))return false;
 if(pod||!same(c.floor,config.floor)||c.unit!=config.unit||c.slot!=config.slot||c.baseGenType!=config.baseGenType
  ||c.x!=config.x||c.y!=config.y||c.z!=config.z||c.yaw!=config.yaw||c.model!=config.model
  ||c.sourceArchive!=config.sourceArchive||c.sourceModel!=config.sourceModel||c.sourceCollision!=config.sourceCollision
  ||c.sourceTexts!=config.sourceTexts
  ||c.births!=config.births||!current())return reject(e,"pod_prepared_identity");
 auto* wp=routeMgr->findNearestWayPoint('test',Vector3f(c.x,c.y,c.z),false);if(!wp)return reject(e,"pod_route_changed");
 HeapScope heap;auto* prop=new CreatureProp;prop->mCreatureProps.mFriction.mValue=.1f;
 pod=new Pod(prop,shape,c,wp->mIndex);node=new CreatureNode;node->mCreature=pod;
 manager=itemMgr->mMeltingPotMgr;manager->mRootNode.add(node);
 std::printf("P2_ORIGINAL_POD_BORN cave=%s floor=%u type=3 bank=1 basegen=7 unit=%u slot=%u source=%s static_pose=1\n",
  c.floor.cave.c_str(),c.floor.floor,c.unit,c.slot,archive);e.clear();return true;
}
bool pc_p2_original_pod_commit_floor(const p2retail::SceneIdentity& scene,std::string& e){
 if(committed||!pod||!(scene==config.floor.scene)||!current())return reject(e,"pod_commit_identity");
 committed=true;pod->live=true;e.clear();return true;
}
bool pc_p2_original_pod_abort_prepared(const p2retail::SceneIdentity& scene,std::string& e){
 if(!prepared||!(scene==config.floor.scene)||committed||everSucked||completing)return reject(e,"pod_abort_after_observable_floor");
 clear();e.clear();return true;
}
bool pc_p2_original_pod_context(Suckable* receiver,const p2retail::SceneIdentity& scene,p2retail::Snapshot& out){
 return committed&&pod&&receiver==pod&&pod->live&&scene==config.floor.scene&&current(&out);
}
bool pc_p2_original_pod_owned(){return prepared;}
bool pc_p2_original_pod_can_abort_prepared(const p2retail::SceneIdentity& scene){
 return prepared&&scene==config.floor.scene&&!committed&&!everSucked&&!completing&&!retaining&&current();
}
Suckable* pc_p2_original_pod_goal(const p2retail::SceneIdentity& scene){p2retail::Snapshot out;return pc_p2_original_pod_context(pod,scene,out)?pod:nullptr;}
bool pc_p2_original_pod_bind_cargo(Pellet* p,const p2retail::BirthIdentity& birth,const p2retail::SceneIdentity& scene,CompletedCallback callback,std::string& e){
 if(!pod||!current()||!(scene==config.floor.scene)||!p||!p->isAlive()||!p->mConfig||!birth.epoch||!birth.activation||birth.instance.empty()||!callback||cargo.count(p)||completing||retaining)return reject(e,"pod_cargo_identity");
 if(p->getState()!=PELSTATE_Normal&&p->getState()!=PELSTATE_Appear)return reject(e,"pod_cargo_already_in_other_lifecycle");
 const auto* c=p2retail::descriptor(config.floor.cave);const auto* f=c?p2retail::definition(*c,config.floor.floor):nullptr;
 if(!f||birth.row>=f->rows.size()||birth.ordinal>=f->rows[birth.row].minimum()
  ||birth.instance!=p2retail::instanceKey(*c,config.floor.floor,f->rows[birth.row],birth.ordinal))return reject(e,"pod_cargo_original_incarnation");
 p2retail::BirthIdentity expected;
 if(!config.births->expectedBirth(*c,config.floor.floor,scene,birth.row,birth.ordinal,expected,e)
  ||!(birth==expected))return reject(e,"pod_cargo_unverified_epoch_activation");
 for(const auto& row:cargo)if(row.second.birth.instance==birth.instance)return reject(e,"pod_duplicate_cargo_incarnation");
 for(const auto& lost:lostCargo)if(lost.scene==scene&&lost.birth.instance==birth.instance)return reject(e,"pod_lost_original_cargo_requires_recovery");
 cargo.emplace(p,Cargo{birth,scene,std::move(callback),Phase::Bound});e.clear();return true;
}
bool pc_p2_original_pod_owns(const Pellet* p){return ownership.owns(p);}
Suckable* pc_p2_original_pod_goal_for(Pellet* p){auto it=cargo.find(p);return it!=cargo.end()&&it->second.phase!=Phase::Completed&&it->second.phase!=Phase::Lost?pc_p2_original_pod_goal(it->second.scene):nullptr;}
bool pc_p2_original_pod_completed(Pellet* p,Suckable* receiver,const p2retail::SceneIdentity& scene){
 auto it=cargo.find(p);p2retail::Snapshot out;
 return completing==p&&it!=cargo.end()&&it->second.phase==Phase::Sucking&&it->second.scene==scene
  &&p->getState()==PELSTATE_Goal&&p->mTargetGoal==receiver&&pc_p2_original_pod_context(receiver,scene,out);
}
unsigned pc_p2_original_pod_pending(){unsigned n=static_cast<unsigned>(lostCargo.size())+((completing||retaining)?1:0);for(const auto& row:cargo)if(moving(row.first,row.second))++n;return n;}
bool pc_p2_original_pod_snapshot(const p2retail::SceneIdentity& scene,p2originalpod::Snapshot& out){
 if(!pod||!committed||completing||!(scene==config.floor.scene)||!current())return false;
 p2originalpod::Snapshot capture;capture.floor=config.floor;capture.unit=config.unit;capture.slot=config.slot;capture.committed=true;
 for(const auto& row:cargo)if(row.second.phase!=Phase::Completed)capture.pending.push_back({row.second.birth,static_cast<unsigned>(row.second.phase),moving(row.first,row.second)});
 for(const auto& lost:lostCargo)capture.pending.push_back({lost.birth,static_cast<unsigned>(Phase::Lost),true});
 out=std::move(capture);return true;
}
bool pc_p2_original_pod_release(std::string& e){
 if(completing||retaining||pc_p2_original_pod_pending())return reject(e,"pod_pending_transaction");
 for(const auto& row:cargo)if(row.second.phase!=Phase::Completed)return reject(e,"pod_uncollected_cargo_requires_owner_retention");
 clear();e.clear();return true;
}
bool pc_p2_original_pod_release_uncollected(const p2retail::SceneIdentity& scene,RetainUncollected retain,std::string& e){
 if(!pod||!committed||completing||retaining||!(scene==config.floor.scene)||!retain||!current())return reject(e,"pod_boundary_identity");
 if(pc_p2_original_pod_pending())return reject(e,"pod_pending_transaction");
 std::vector<UncollectedCargo> loose;
 for(const auto& row:cargo)if(row.second.phase!=Phase::Completed){
  const auto* c=p2retail::descriptor(config.floor.cave);p2retail::BirthIdentity expected;
  if(!c||!config.births->expectedBirth(*c,config.floor.floor,scene,row.second.birth.row,row.second.birth.ordinal,expected,e)
   ||!(expected==row.second.birth))return reject(e,"pod_boundary_origin_changed");
  loose.push_back({row.first,row.second.birth});
 }
 // No state is changed on a failed capture. The callback must retain/verify,
 // not retire/rebind actors or grant any consumed/seen/Poko receipt.
 bool retained=false;{RetainScope scope;retained=retain(config.floor,loose,e);}
 if(!retained)return false;
 unsigned unfinished=0;for(const auto& row:cargo)if(row.second.phase!=Phase::Completed)++unfinished;
 if(!current()||pc_p2_original_pod_pending()||loose.size()!=unfinished)return reject(e,"pod_boundary_changed_during_retention");
 for(const auto& row:loose){auto it=cargo.find(row.actor);
  if(it==cargo.end()||!(it->second.birth==row.birth))return reject(e,"pod_boundary_binding_changed");}
 for(const auto& row:loose)if(row.actor->mTargetGoal==pod)row.actor->mTargetGoal=nullptr;
 clear();e.clear();return true;
}
void P2OriginalPodNativeSeam::begin(Pellet* p){
 auto it=cargo.find(p);if(it==cargo.end())return;
 Suckable* receiver=pc_p2_original_pod_goal_for(p);
 if(retaining||!receiver||it->second.phase!=Phase::Bound||p->mTargetGoal!=receiver)fail("pod_stale_or_duplicate_suction");
 it->second.phase=Phase::Sucking;everSucked=true;
}
bool P2OriginalPodNativeSeam::done(Pellet* p,const PelletGoalState& state){
 auto it=cargo.find(p);if(it==cargo.end())return false;
 Suckable* receiver=pc_p2_original_pod_goal_for(p);
 if(completing||retaining||it->second.phase!=Phase::Sucking||p->getState()!=PELSTATE_Goal||!p->isAlive()
  ||p->mCurrentState!=&state||!std::isfinite(state.mSuckProgress)||state.mSuckProgress<1
  ||state.mWaitTimer>0||state.mIsFirstMove||state.mTargetIsShip
  ||!receiver||p->mTargetGoal!=receiver)fail("pod_unverified_completed_suction");
 completing=p;std::string e;auto callback=it->second.callback;bool ok=callback(p,pod,e);completing=nullptr;
 if(!ok)fail(e.empty()?"canonical_pod_receipt_failed":e.c_str());
 it=cargo.find(p);if(it==cargo.end()||it->second.phase!=Phase::Sucking)fail("pod_callback_retired_cargo_before_native_completion");
 it->second.phase=Phase::Completed;
 std::printf("P2_ORIGINAL_POD_SUCK_DONE cave=%s floor=%u instance=%s epoch=%llu\n",config.floor.cave.c_str(),config.floor.floor,it->second.birth.instance.c_str(),static_cast<unsigned long long>(it->second.birth.epoch));
 return true;
}
void P2OriginalPodNativeSeam::cleanup(Pellet* p){auto it=cargo.find(p);if(it!=cargo.end()&&it->second.phase==Phase::Sucking)it->second.phase=Phase::Bound;}
void pc_p2_original_pod_forget_pellet(Pellet* p){
 // Revoke the native pool-address claim even on loss. The identity tombstone
 // still blocks unload/SAVE, while an unrelated recycled Pellet is unowned.
 ownership.forget(p);
}
