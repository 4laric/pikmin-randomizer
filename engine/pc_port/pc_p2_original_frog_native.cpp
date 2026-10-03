#include "pc_p2_original_frog_native.h"
#include "pc_p2_frog.h"
#include "pc_p2_original_drop_engine.h"
#include "pc_p2_original_actor.h"
#include "teki.h"
#include "Pellet.h"
#include <cstdio>
#include <cstdlib>
#include "Generator.h"
#include "sysNew.h"
#include <set>
namespace p2original { namespace frog { namespace {
std::set<Native*>& instances(){static std::set<Native*> values;return values;}
struct Heap {int prior;Heap():prior(gsys->setHeap(SYSHEAP_App)){}~Heap(){gsys->setHeap(prior);}};
bool reject(std::string& e,const char* text){e=text;return false;}
int chassis(unsigned source){return source==18?TEKI_Frow:TEKI_Frog;}
}
struct Native::Impl final:Engine {
 Provider provider;explicit Impl():provider(*this){}
 bool prepare(const std::vector<CatalogRow>& rows,std::string& e)override {
  if(!gsys||!tekiMgr)return reject(e,"original frog managers unavailable");
  Heap heap;
  for(const auto& row:rows){int type=chassis(row.enemy.source);auto* shape=tekiMgr->getTekiShapeObject(type);
   if(!shape||!shape->mShape||!shape->mAnimMgr||!tekiMgr->getTekiParameters(type)||!tekiMgr->getStrategy(type))return reject(e,"original frog chassis not preloaded in early use-list");
   if(tekiMgr->getTekiParameters(type)->getI(TPI_CorpseType)!=TEKICORPSE_LeaveCorpse)return reject(e,"original frog chassis does not leave a view-backed corpse");
   const unsigned corpse=TekiMgr::getTypeId(type);
   if(!pelletMgr||!pelletMgr->getConfig(corpse))return reject(e,"original frog ordinary corpse config unavailable");
   if(!pc_p2_original_drop_resources(row,e))return false;
  }
  return pc_p2_frog_prepare_original(e);
 }
 bool reserve(unsigned count,std::string& e)override {
  if(!tekiMgr||tekiMgr->getMax()-tekiMgr->getSize()<int(count))return reject(e,"original frog actual native pool capacity insufficient");
  if(!pelletMgr||pelletMgr->getMax()-pelletMgr->getSize()<int(count))return reject(e,"original frog actual corpse pool capacity insufficient");return true;
 }
 bool allocate(const CatalogRow& row,Generator* generator,const Position& p,float facing,Creature*& out,std::string& e)override {
  Heap heap;Teki* actor=tekiMgr->newTeki(chassis(row.enemy.source));out=actor;
  if(!actor)return true; // Retail allocation failure consumes this placement.
  actor->mPersonality->reset();
  actor->mPersonality->mPosition.set(p.x,p.y,p.z);actor->mPersonality->mNestPosition.set(p.x,p.y,p.z);
  actor->mPersonality->mFaceDirection=facing;actor->reset();actor->startAI(0);
  actor->mGenerator=generator;actor->mFaceDirection=facing;actor->mSRT.r.set(0,facing,0);
  actor->mVelocity.set(0,0,0);actor->mRebirthDay=generator->mRespawnInterval;e.clear();return true;
 }
 bool attach(const CatalogRow& row,Creature* actor,unsigned ordinal,unsigned token,std::string& e)override {
  unsigned source=0,actualToken=0;InstanceIdentity identity;
  if(!originalActors().query(actor,source,actualToken,&identity)||source!=row.enemy.source||actualToken!=token||identity.generator!=row.enemy.uid||identity.ordinal!=ordinal)return reject(e,"original frog requires actual catalog registry association");
  return pc_p2_frog_bind_original(static_cast<BTeki*>(actor),source,token,e);
 }
 bool destroy(Creature* actor,std::string& e)override {
  auto* teki=static_cast<BTeki*>(actor);
  if(teki->mPellet){Pellet* corpse=teki->mPellet;teki->mPellet=nullptr;corpse->kill(false);}
  if(provider.owns(actor))actor->kill(false);e.clear();return true;
 }
};
Native::Native():m(new Impl){instances().insert(this);}
Native::~Native(){if(m->provider.size()){std::fprintf(stderr,"P2_ORIGINAL_FROG live provider destroyed\n");std::abort();}instances().erase(this);}
Provider& Native::provider(){return m->provider;}
void Native::retired(Creature* actor){m->provider.retired(actor);}
} }
void pc_p2_original_frog_forget(BTeki* actor){for(auto* n:p2original::frog::instances())n->retired(static_cast<Creature*>(actor));}
