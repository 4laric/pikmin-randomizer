#include "pc_p2_original_bulblax_snagret_native.h"
#include "pc_p2_original_drop_engine.h"
#include "pc_p2_chappy.h"
#include "pc_p2_snakejoint.h"
#include "pc_p2_batch3.h"
#include "teki.h"
#include "TekiPersonality.h"
#include "Pellet.h"
#include "Generator.h"
#include "sysNew.h"
#include <algorithm>
#include <set>
namespace p2original { namespace bulblax_snagret {
namespace {
std::set<Native*>& natives(){static std::set<Native*> owners;return owners;}
bool refuse(std::string& e,const char* s){e=s;return false;}
struct Heap {int previous;Heap():previous(gsys->setHeap(SYSHEAP_App)){}~Heap(){gsys->setHeap(previous);}};
}
struct Native::Impl final:Engine {
 Provider provider;
 Impl():provider(*this){}
 bool resources(const CatalogRow& row,std::string& e)override{
  if(!gsys||!tekiMgr||!pelletMgr)return refuse(e,"original Bulblax/Snagret managers unavailable");
  const int type=nativeType(row.enemy.source);auto* shape=tekiMgr->getTekiShapeObject(type);
  if(!tekiMgr->hasModel(type)||!shape||!shape->mShape||!shape->mAnimMgr||!tekiMgr->getTekiParameters(type)||!tekiMgr->getStrategy(type))return refuse(e,"Bulblax/Snagret physical chassis unavailable");
  Heap heap;
  // Real PelletView corpse uses the actor's dead bank, not a standalone shape.
  if(!pelletMgr->getConfig(TekiMgr::getTypeId(type))||tekiMgr->getTekiParameters(type)->getI(TPI_CorpseType)!=TEKICORPSE_LeaveCorpse)return refuse(e,"original Bulblax/Snagret physical corpse config unavailable");
  if(!pc_p2_original_drop_resources(row,e))return false;
  if(row.enemy.source==33)return pc_p2_chappy_prepare_original({33},e);
  return pc_p2_batch3_original_resources(34,e)&&pc_p2_snakejoint_original_resources(e);
 }
 bool reserve(const std::vector<CatalogRow>& rows,unsigned count,std::string& e)override{
  if(!tekiMgr||tekiMgr->getMax()-tekiMgr->getSize()<int(count))return refuse(e,"original Bulblax/Snagret actor pool capacity insufficient");
  unsigned pellets=0;for(const auto& row:rows)pellets+=(row.enemy.count-row.enemy.deathCount)*(1+(row.enemy.treasureCode?1:0)+(row.enemy.pelletProbability>0?std::max(row.enemy.pelletMinimum,row.enemy.pelletMaximum):0));
  if(!pelletMgr||pelletMgr->getMax()-pelletMgr->getSize()<int(pellets))return refuse(e,"original Bulblax/Snagret corpse/drop pool capacity insufficient");
  e.clear();return true;
 }
 bool allocate(Host& host,const Position& p,float facing,std::string& e)override{
  if(!gsys||!tekiMgr)return refuse(e,"original Bulblax/Snagret managers lost before birth");
  Heap heap;Teki* actor=tekiMgr->newTeki(nativeType(host.row.enemy.source));
  if(!actor){e.clear();return true;}host.actor=actor;
  actor->mPersonality->reset();actor->mPersonality->mPosition.set(p.x,p.y,p.z);
  actor->mPersonality->mNestPosition.set(p.x,p.y,p.z);actor->mPersonality->mFaceDirection=facing;
  actor->mGenerator=host.generator;actor->reset();
  actor->mSRT.r.set(0,facing,0);actor->mSRT.s.set(1,1,1);actor->mFaceDirection=facing;
  // Original generator has no P1 GenType. Never call getRebirthDay().
  actor->mRebirthDay=host.generator->mRespawnInterval;
  e.clear();return true;
 }
 bool bind(Host& host,std::string& e)override{
  unsigned source=0,token=0;InstanceIdentity identity;
  if(!originalActors().query(host.actor,source,token,&identity)||source!=host.row.enemy.source||token!=host.token||identity.generator!=host.row.enemy.uid||identity.ordinal!=host.ordinal||identity.catalog.empty())return refuse(e,"Bulblax/Snagret original identity was not registered before bind");
  auto* actor=static_cast<BTeki*>(host.actor);
  if(source==33){if(!pc_p2_chappy_bind_original(actor,token,source))return refuse(e,"original Fiery Bulblax concrete FSM bind failed");return true;}
  return pc_p2_batch3_original_birth(actor,source,e)&&pc_p2_snakejoint_bind_original(actor,token,e);
 }
 bool cleanup(Host& host,std::string& e)override{
  if(host.actor){auto* actor=static_cast<BTeki*>(host.actor);
   if(actor->mPellet){Pellet* corpse=actor->mPellet;actor->mPellet=nullptr;
    const bool killsActor=corpse->mPelletView==static_cast<PelletView*>(actor);
    corpse->kill(false);if(killsActor){e.clear();return true;}
   }
   actor->kill(false);
  }
  e.clear();return true;
 }
};
Native::Native():m(std::make_unique<Impl>()){natives().insert(this);}
Native::~Native(){natives().erase(this);}
Provider& Native::provider(){return m->provider;}
void Native::retired(Creature* actor){m->provider.retired(actor);}
} }
void pc_p2_original_bulblax_snagret_forget(BTeki* actor){for(auto* n:p2original::bulblax_snagret::natives())n->retired(actor);}
bool pc_p2_original_bulblax_snagret_admitted(){for(auto* n:p2original::bulblax_snagret::natives())if(n->provider().prepared())return true;return false;}
