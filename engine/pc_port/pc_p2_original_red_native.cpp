#include "pc_p2_original_red_native.h"
#include "pc_p2_kochappy.h"
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
namespace p2original { namespace red { namespace {
std::set<Native*>& instances(){static std::set<Native*> values;return values;}
struct Heap {int prior;Heap():prior(gsys->setHeap(SYSHEAP_App)){}~Heap(){gsys->setHeap(prior);}};
bool reject(std::string& e,const char* text){e=text;return false;}
int chassis(unsigned){return TEKI_Chappy;}
}
struct Native::Impl final:Engine {
 Provider provider;explicit Impl():provider(*this){}
 bool prepare(const std::vector<CatalogRow>& rows,std::string& e)override {
  if(!gsys||!tekiMgr)return reject(e,"original red managers unavailable");
  Heap heap;
  for(const auto& row:rows){int type=chassis(row.enemy.source);auto* shape=tekiMgr->getTekiShapeObject(type);
   if(!shape||!shape->mShape||!shape->mAnimMgr||!tekiMgr->getTekiParameters(type)||!tekiMgr->getStrategy(type))return reject(e,"original red chassis not preloaded in early use-list");
   if(tekiMgr->getTekiParameters(type)->getI(TPI_CorpseType)!=TEKICORPSE_LeaveCorpse)return reject(e,"original red chassis does not leave a view-backed corpse");
   const unsigned corpse=TekiMgr::getTypeId(type);
   if(!pelletMgr||!pelletMgr->getConfig(corpse))return reject(e,"original red ordinary corpse config unavailable");
   if(!pc_p2_original_drop_resources(row,e))return false;
  }
  return pc_p2_kochappy_prepare_original(e);
 }
 bool reserve(unsigned count,std::string& e)override {
  if(!tekiMgr||tekiMgr->getMax()-tekiMgr->getSize()<int(count))return reject(e,"original red actual native pool capacity insufficient");
  if(!pelletMgr||pelletMgr->getMax()-pelletMgr->getSize()<int(count))return reject(e,"original red actual corpse pool capacity insufficient");return true;
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
  if(!mouth||mouth->getChildCount()<1)return reject(e,"original red actual mouth capture collider missing");e.clear();return true;
 }
 bool attach(const CatalogRow& row,Creature* actor,unsigned ordinal,unsigned token,std::string& e)override {
  unsigned source=0,actualToken=0;InstanceIdentity identity;
  if(!originalActors().query(actor,source,actualToken,&identity)||source!=row.enemy.source||actualToken!=token||identity.generator!=row.enemy.uid||identity.ordinal!=ordinal)return reject(e,"original red requires actual catalog registry association");
  if(!pc_p2_kochappy_bind_original(static_cast<BTeki*>(actor),token,e))return false;
  return pc_p2_kochappy_fsm_bind_original(static_cast<BTeki*>(actor),token,e);
 }
 bool destroy(Creature* actor,std::string& e)override {
  auto* teki=static_cast<BTeki*>(actor);
  if(teki->mPellet){Pellet* corpse=teki->mPellet;teki->mPellet=nullptr;corpse->kill(false);}
  if(provider.owns(actor))actor->kill(false);e.clear();return true;
 }
};
Native::Native():m(new Impl){instances().insert(this);}
Native::~Native(){if(m->provider.size()){std::fprintf(stderr,"P2_ORIGINAL_RED live provider destroyed\n");std::abort();}instances().erase(this);}
Provider& Native::provider(){return m->provider;}
void Native::retired(Creature* actor){m->provider.retired(actor);}
} }
void pc_p2_original_red_forget(BTeki* actor){for(auto* n:p2original::red::instances())n->retired(static_cast<Creature*>(actor));}
bool pc_p2_original_red_owned(const BTeki* actor){unsigned source=0;return actor&&pc_p2_original_actor_source(static_cast<const Creature*>(actor),source)&&source==1;}
