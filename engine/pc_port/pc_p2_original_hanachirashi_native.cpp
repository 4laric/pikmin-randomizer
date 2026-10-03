#include "pc_p2_original_hanachirashi_native.h"
#include "pc_p2_original_actor.h"
#include "pc_p2_original_drop_engine.h"
#include "pc_p2_hanachirashi.h"
#include "pc_p2_batch3.h"
#include "pc_p2_body_coll.h"

#include "teki.h"
#include "TekiPersonality.h"
#include "Pellet.h"
#include "Generator.h"
#include "sysNew.h"
#include <set>
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <cmath>
namespace p2original { namespace hanachirashi {
namespace {
std::set<Native*>& natives(){static std::set<Native*> owners;return owners;}
bool refuse(std::string& e,const char* s){e=s;return false;}
bool& geometryRegistered(){static bool registered=false;return registered;}
bool originalItemGeometry(BTeki* actor,Vector3f& position,Vector3f& treasureVelocity,std::string& error){
 unsigned source=0;
 if(!actor||!pc_p2_original_actor_source(actor,source)||source!=55)return refuse(error,"source55 item geometry actor identity mismatch");
 // Hanachirashi::getThrowupItemPosition uses the real root, never getCentre.
 position=actor->getPosition();position.y+=500.0f;
 // Only the held treasure branch uses this velocity. Common number pellets
 // retain throwOriginalItems' original 150/200/250 velocity RNG.
 treasureVelocity.set(0.0f,0.0f,0.0f);
 if(!std::isfinite(position.x)||!std::isfinite(position.y)||!std::isfinite(position.z))return refuse(error,"source55 item geometry root is nonfinite");
 error.clear();return true;
}
struct Heap {int previous;Heap():previous(gsys->setHeap(SYSHEAP_App)){}~Heap(){gsys->setHeap(previous);}};
}
struct Native::Impl final:Engine {
 Provider provider;
 Impl():provider(*this){}
 bool resources(const CatalogRow& row,std::string& e)override{
  if(!geometryRegistered())return refuse(e,"original Hanachirashi prebirth drop geometry registration failed");
  if(!gsys||!tekiMgr)return refuse(e,"original Hanachirashi native managers unavailable");
  const int type=nativeType(row.enemy.source);auto* shape=tekiMgr->getTekiShapeObject(type);
  if(!tekiMgr->hasModel(type)||!shape||!shape->mShape||!shape->mAnimMgr||!tekiMgr->getTekiParameters(type)||!tekiMgr->getStrategy(type))return refuse(e,"Hanachirashi chassis model/animation/parameters/strategy not preloaded");
  Heap heap;
  // Retail Hanachirashi::onInit disables EB_LeaveCarcass. Source55 has
  // no carryable corpse and must not require its borrowed Mar pellet config.
  // Source55 binds its own nine authored joint colliders after visual birth.
  return pc_p2_original_drop_resources(row,e)&&pc_p2_batch3_original_resources(row.enemy.source,e)&&pc_p2_hanachirashi_original_resources(row.enemy.source,e);
 }
 bool reserve(const std::vector<CatalogRow>& rows,unsigned count,std::string& e)override{
  if(!tekiMgr||tekiMgr->getMax()-tekiMgr->getSize()<int(count))return refuse(e,"original Hanachirashi real actor pool capacity insufficient");
  unsigned pellets=0;for(const auto& row:rows)if(species(row.enemy.source))pellets+=(row.enemy.count-row.enemy.deathCount)*(row.enemy.pelletProbability>0?std::max(row.enemy.pelletMinimum,row.enemy.pelletMaximum):0);
  if(!pelletMgr||pelletMgr->getMax()-pelletMgr->getSize()<int(pellets))return refuse(e,"original Hanachirashi number-drop pellet pool capacity insufficient");
  e.clear();return true;
 }
 bool allocate(Host& host,const Position& p,float facing,std::string& e)override{
  Heap heap;Teki* actor=tekiMgr->newTeki(nativeType(host.row.enemy.source));
  if(!actor){e.clear();return true;}host.actor=actor;
  // Personality is only neutral chassis initialization, never original data.
  // All original common fields remain in host.row and the original registry.
  actor->mPersonality->reset();actor->mPersonality->mPosition.set(p.x,p.y,p.z);
  actor->mPersonality->mNestPosition.set(p.x,p.y,p.z);actor->mPersonality->mFaceDirection=facing;
  actor->mGenerator=host.generator;actor->reset();
  actor->mSRT.r.set(0,facing,0);actor->mSRT.s.set(1,1,1);actor->mFaceDirection=facing;
  // Original GenObjectOriginalEnemy has no P1 mGenType. Respawn belongs to
  // the original lifecycle; its literal interval is mirrored on Generator.
  actor->mRebirthDay=host.generator->mRespawnInterval;
  // Bind before any frame can run the borrowed Hanachirashi AI. reset initializes
  // the real chassis animation/collider; its strategy startAI is unnecessary.
  if(!pc_p2_batch3_original_birth(actor,host.row.enemy.source,e))return false;
  if(!pc_p2_hanachirashi_original_birth(actor,host.row.enemy.source,host.row.enemy.uid,host.ordinal,e))return false;
  e.clear();return true;
 }
 bool bind(Host& host,std::string& e)override{
  unsigned source=0,token=0;InstanceIdentity identity;
  if(!originalActors().query(host.actor,source,token,&identity)||source!=host.row.enemy.source||token!=host.token||identity.generator!=host.row.enemy.uid||identity.ordinal!=host.ordinal||identity.catalog.empty())return refuse(e,"Hanachirashi original identity was not registered before bind");
  return pc_p2_hanachirashi_original_registry(static_cast<BTeki*>(host.actor),host.token,e);
 }
 bool cleanup(Host& host,std::string& e)override{
  // Copy in Provider::release makes recursive native forget safe. The
  // central kill funnel releases mouths, visual/collider state and registry.
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
Native::Native():m(std::make_unique<Impl>()){
 // Install before the first provider preflight can call drop_resources.
 if(natives().empty())geometryRegistered()=pc_p2_original_drop_register_geometry(55,originalItemGeometry);
 natives().insert(this);
}
Native::~Native(){
 natives().erase(this);
 if(natives().empty()&&geometryRegistered()){pc_p2_original_drop_unregister_geometry(55);geometryRegistered()=false;}
}
Provider& Native::provider(){return m->provider;}
void Native::retired(Creature* actor){m->provider.retired(actor);}
} }
void pc_p2_original_hanachirashi_forget(BTeki* actor){for(auto* n:p2original::hanachirashi::natives())n->retired(actor);}
bool pc_p2_original_hanachirashi_admitted(){for(auto* n:p2original::hanachirashi::natives())if(n->provider().prepared())return true;return false;}
