#include "pc_p2_original_snow_native.h"
#include "pc_p2_enemy.h"
#include "pc_p2_kochappy_fsm.h"
#include "Collision.h"
#include "pc_p2_original_drop_engine.h"
#include "pc_p2_original_actor.h"
#include "teki.h"
#include "Pellet.h"
#include <cstdio>
#include <cstdlib>
#include "Generator.h"
#include "sysNew.h"
#include <set>
#include <map>
#include <cmath>
namespace {std::map<Creature*,unsigned> caveActors;bool cavePrepared=false;unsigned caveReserved=0,caveBorn=0;}
namespace p2original { namespace snow { namespace {
std::set<Native*>& instances(){static std::set<Native*> values;return values;}
struct Heap {int prior;Heap():prior(gsys->setHeap(SYSHEAP_App)){}~Heap(){gsys->setHeap(prior);}};
bool reject(std::string& e,const char* text){e=text;return false;}
int chassis(unsigned){return TEKI_Chappy;}
}
struct Native::Impl final:Engine {
 Provider provider;explicit Impl():provider(*this){}
 bool prepare(const std::vector<CatalogRow>& rows,std::string& e)override {
  if(!gsys||!tekiMgr)return reject(e,"original snow managers unavailable");
  Heap heap;
  for(const auto& row:rows){int type=chassis(row.enemy.source);auto* shape=tekiMgr->getTekiShapeObject(type);
   if(!shape||!shape->mShape||!shape->mAnimMgr||!tekiMgr->getTekiParameters(type)||!tekiMgr->getStrategy(type))return reject(e,"original snow chassis not preloaded in early use-list");
   if(tekiMgr->getTekiParameters(type)->getI(TPI_CorpseType)!=TEKICORPSE_LeaveCorpse)return reject(e,"original snow chassis does not leave a view-backed corpse");
   const unsigned corpse=TekiMgr::getTypeId(type);
   if(!pelletMgr||!pelletMgr->getConfig(corpse))return reject(e,"original snow ordinary corpse config unavailable");
   if(!pc_p2_original_drop_resources(row,e))return false;
  }
  return pc_p2_snow_prepare_original(e);
 }
 bool reserve(unsigned count,std::string& e)override {
  if(!tekiMgr||tekiMgr->getMax()-tekiMgr->getSize()<int(count))return reject(e,"original snow actual native pool capacity insufficient");
  if(!pelletMgr||pelletMgr->getMax()-pelletMgr->getSize()<int(count))return reject(e,"original snow actual corpse pool capacity insufficient");return true;
 }
 bool allocate(const CatalogRow& row,Generator* generator,const Position& p,float facing,Creature*& out,std::string& e)override {
  Heap heap;Teki* actor=tekiMgr->newTeki(chassis(row.enemy.source));out=actor;
  if(!actor)return true; // Retail allocation failure consumes this placement.
  actor->mPersonality->reset();
  actor->mPersonality->mPosition.set(p.x,p.y,p.z);actor->mPersonality->mNestPosition.set(p.x,p.y,p.z);
  actor->mPersonality->mFaceDirection=facing;actor->reset();actor->startAI(0);
  actor->mGenerator=generator;actor->mFaceDirection=facing;actor->mSRT.r.set(0,facing,0);
  actor->mVelocity.set(0,0,0);actor->mRebirthDay=generator->mRespawnInterval;
  auto* mouth=actor->mCollInfo?actor->mCollInfo->getSphere('slot'):nullptr;
  if(!mouth||mouth->getChildCount()<1)return reject(e,"original snow actual mouth capture collider missing");e.clear();return true;
 }
 bool attach(const CatalogRow& row,Creature* actor,unsigned ordinal,unsigned token,std::string& e)override {
  unsigned source=0,actualToken=0;InstanceIdentity identity;
  if(!originalActors().query(actor,source,actualToken,&identity)||source!=row.enemy.source||actualToken!=token||identity.generator!=row.enemy.uid||identity.ordinal!=ordinal)return reject(e,"original snow requires actual catalog registry association");
  if(!pc_p2_snow_bind_original(static_cast<BTeki*>(actor),token,e))return false;
  return pc_p2_kochappy_fsm_bind_original(static_cast<BTeki*>(actor),token,e);
 }
 bool destroy(Creature* actor,std::string& e)override {
  auto* teki=static_cast<BTeki*>(actor);
  if(teki->mPellet){Pellet* corpse=teki->mPellet;teki->mPellet=nullptr;corpse->kill(false);}
  if(provider.owns(actor))actor->kill(false);e.clear();return true;
 }
};
Native::Native():m(new Impl){instances().insert(this);}
Native::~Native(){if(m->provider.size()){std::fprintf(stderr,"P2_ORIGINAL_SNOW live provider destroyed\n");std::abort();}instances().erase(this);}
Provider& Native::provider(){return m->provider;}
void Native::retired(Creature* actor){m->provider.retired(actor);}
} }
void pc_p2_original_snow_resources_reset(){cavePrepared=false;caveReserved=caveBorn=0;}
void pc_p2_original_snow_forget(BTeki* actor){caveActors.erase(actor);for(auto* n:p2original::snow::instances())n->retired(static_cast<Creature*>(actor));}
bool pc_p2_original_snow_owned(const BTeki* actor){unsigned source=0;return actor&&pc_p2_original_actor_source(static_cast<const Creature*>(actor),source)&&source==45;}

namespace {bool caveRefuse(std::string& e,const char* text){e=text;return false;}}
bool pc_p2_snow_prepare_cave(std::string& e){
 if(!caveActors.empty())return caveRefuse(e,"Snow cave resource preparation with live actors");
 caveReserved=caveBorn=0;
 if(!gsys||!tekiMgr||!pelletMgr)return caveRefuse(e,"Snow cave native managers absent");
 const int type=TEKI_Chappy;auto* shape=tekiMgr->getTekiShapeObject(type);
 if(!shape||!shape->mShape||!shape->mAnimMgr||!tekiMgr->getTekiParameters(type)||!tekiMgr->getStrategy(type)
 ||tekiMgr->getTekiParameters(type)->getI(TPI_CorpseType)!=TEKICORPSE_LeaveCorpse
 ||!pelletMgr->getConfig(TekiMgr::getTypeId(type)))return caveRefuse(e,"Snow cave chassis/corpse resources not preloaded");
 p2original::snow::Heap heap;cavePrepared=pc_p2_snow_prepare_original(e);return cavePrepared;
}
bool pc_p2_snow_reserve_cave(unsigned count,std::string& e){
 if(!cavePrepared||!caveActors.empty()||caveReserved||!count||count>100||!tekiMgr||!pelletMgr
 ||tekiMgr->getMax()-tekiMgr->getSize()<int(count)||pelletMgr->getMax()-pelletMgr->getSize()<int(count))return caveRefuse(e,"Snow cave whole-roster native capacity unavailable");
 caveReserved=count;caveBorn=0;e.clear();return true;
}
bool pc_p2_snow_birth_cave(Generator* generator,const Vector3f& p,float facing,Creature*& out,std::string& e){
 out=nullptr;
 if(!cavePrepared||!caveReserved||caveBorn>=caveReserved||!generator||!tekiMgr||!pelletMgr||!std::isfinite(p.x)||!std::isfinite(p.y)||!std::isfinite(p.z)||!std::isfinite(facing))return caveRefuse(e,"Snow cave generator/transform invalid");
 if(tekiMgr->getMax()<=tekiMgr->getSize()||pelletMgr->getMax()<=pelletMgr->getSize())return caveRefuse(e,"Snow cave actor/corpse native pool full");
 p2original::snow::Heap heap;Teki* actor=tekiMgr->newTeki(TEKI_Chappy);out=actor;
 if(!actor)return caveRefuse(e,"Snow cave native allocation failed");
 if(!caveActors.emplace(actor,0).second)return caveRefuse(e,"Snow cave native address already owned");
 ++caveBorn;
 actor->mPersonality->reset();actor->mPersonality->mPosition=p;actor->mPersonality->mNestPosition=p;
 actor->mPersonality->mFaceDirection=facing;actor->reset();actor->startAI(0);
 actor->mGenerator=generator;actor->mFaceDirection=facing;actor->mSRT.r.set(0,facing,0);actor->mVelocity.set(0,0,0);
 auto* mouth=actor->mCollInfo?actor->mCollInfo->getSphere('slot'):nullptr;
 if(!mouth||mouth->getChildCount()<1)return caveRefuse(e,"Snow cave physical mouth collider unavailable");
 e.clear();return true;
}
bool pc_p2_snow_bind_cave(Creature* actor,unsigned token,std::string& e){
 auto i=caveActors.find(actor);unsigned source=0,actual=0;p2original::InstanceIdentity identity;
 if(i==caveActors.end()||i->second||!token||!p2original::originalActors().query(actor,source,actual,&identity)
 ||source!=45||actual!=token||identity.catalog.empty()||!identity.generator||!identity.activation)return caveRefuse(e,"Snow cave authenticated source association absent");
 i->second=token;
 if(!pc_p2_snow_bind_original(static_cast<BTeki*>(actor),token,e))return false;
 return pc_p2_kochappy_fsm_bind_original(static_cast<BTeki*>(actor),token,e);
}
bool pc_p2_snow_release_cave(Creature* actor,unsigned token,std::string& e){
 auto i=caveActors.find(actor);if(i==caveActors.end()){e.clear();return true;}
 if(i->second!=token)return caveRefuse(e,"Snow cave release token mismatch");
 auto* teki=static_cast<BTeki*>(actor);if(teki->mPellet){auto* corpse=teki->mPellet;teki->mPellet=nullptr;corpse->kill(false);}
 actor->kill(false);caveActors.erase(actor);e.clear();return true;
}
