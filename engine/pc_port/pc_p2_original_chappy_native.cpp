#include "pc_p2_original_chappy_native.h"
#include "pc_p2_chappy.h"
#include "pc_p2_chappy_policy.h"
#include "pc_p2_original_drop_engine.h"
#include "teki.h"
#include "TekiPersonality.h"
#include "Generator.h"
#include "Pellet.h"
#include "sysNew.h"
#include <cstdio>
#include <cstdlib>
namespace p2original { namespace chappy {
namespace {
std::set<Native*>& instances(){static std::set<Native*> n;return n;}
bool fail(std::string& e,const char* why){e=why;return false;}
struct Heap {int previous;Heap():previous(gsys->setHeap(SYSHEAP_App)){}~Heap(){gsys->setHeap(previous);}};
}
Native::Native():mProvider(*this){instances().insert(this);}
Native::~Native(){
 // Course must unload while managers/banks still exist. Never recycle an
 // actor silently or leave a native callback pointing at a destroyed owner.
 if(mProvider.size()){std::fprintf(stderr,"P2_ORIGINAL_CHAPPY live provider destroyed\n");std::abort();}
 instances().erase(this);
}
bool Native::resources(const std::set<unsigned>& sources,std::string& e){
 if(!gsys||!tekiMgr||!pelletMgr)return fail(e,"original Chappy managers unavailable");
 Heap heap;
 for(unsigned source:sources){const auto* spec=p2chappy::speciesForSource(source);
  if(!spec)return fail(e,"original Chappy concrete profile missing");
  auto* shape=tekiMgr->getTekiShapeObject(spec->host);
  if(!tekiMgr->hasModel(spec->host)||!shape||!shape->mShape||!shape->mAnimMgr
   ||!tekiMgr->getTekiParameters(spec->host)||!tekiMgr->getStrategy(spec->host))return fail(e,"original Chappy chassis use-list/shape/animation/parameters unavailable");
  // The ordinary corpse remains a real PelletView, not a synthetic receipt.
  const unsigned id=TekiMgr::getTypeId(spec->host);
  // A real enemy corpse is a PelletView: initPellet(view, config) deliberately
  // has no standalone PelletShapeObject. Its physical dead bank is checked by
  // prepare_original below; only ordinary number drops use pcEnsureShape.
  if(!pelletMgr->getConfig(id)
   ||tekiMgr->getTekiParameters(spec->host)->getI(TPI_CorpseType)!=TEKICORPSE_LeaveCorpse)
   return fail(e,"original Chappy ordinary PelletView corpse config unavailable");
 }
 return pc_p2_chappy_prepare_original(sources,e);
}
bool Native::commonResources(const CatalogRow& row,std::string& e){return pc_p2_original_drop_resources(row,e);}
bool Native::reserve(unsigned count,std::string& e){
 if(!tekiMgr||count>unsigned(tekiMgr->getMax()-tekiMgr->getSize()))return fail(e,"original Chappy actual actor pool insufficient");
 if(!pelletMgr||count>unsigned(pelletMgr->getMax()-pelletMgr->getSize()))return fail(e,"original Chappy actual corpse pool insufficient");
 e.clear();return true;
}
bool Native::allocate(Host& h,const Position& p,float facing,std::string& e){
 if(!gsys||!tekiMgr)return fail(e,"original Chappy managers lost before birth");
 const auto* spec=p2chappy::speciesForSource(h.row.enemy.source);if(!spec)return fail(e,"original Chappy source profile lost");
 Heap heap;Teki* actor=tekiMgr->newTeki(spec->host);
 if(!actor){e.clear();return true;} // Retail null allocation is not an omitted row.
 h.actor=actor;
 actor->mPersonality->reset(); // Neutral chassis; source drops stay in catalog.
 actor->mPersonality->mPosition.set(p.x,p.y,p.z);
 actor->mPersonality->mNestPosition.set(p.x,p.y,p.z);
 actor->mPersonality->mFaceDirection=facing;
 actor->reset();actor->startAI(0);
 actor->mGenerator=h.generator;actor->mSRT.r.set(0,facing,0);
 // Genuine original generators have no P1 GenType. Their typed original
 // lifecycle owns respawn; only mirror the compatibility observation here.
 actor->mRebirthDay=h.generator->mRespawnInterval;
 e.clear();return true;
}
bool Native::bind(Host& h,std::string& e){
 unsigned source=0,token=0;InstanceIdentity id;
 if(!originalActors().query(h.actor,source,token,&id)||source!=h.row.enemy.source||token!=h.token
   ||id.generator!=h.row.enemy.uid||id.ordinal!=h.ordinal)return fail(e,"original Chappy registry identity disagrees with physical birth");
 if(!pc_p2_chappy_bind_original(static_cast<BTeki*>(h.actor),h.token,source))return fail(e,"original Chappy concrete FSM bind failed");
 std::printf("P2_ORIGINAL_CHAPPY_BIRTH source=%u uid=%u ordinal=%u token=%u epoch=%llu activation=%llu\n",source,id.generator,id.ordinal,token,(unsigned long long)id.epoch,(unsigned long long)id.activation);
 e.clear();return true;
}
bool Native::cleanup(Host& h,std::string& e){
 auto* actor=static_cast<BTeki*>(h.actor);
 // Kill owned corpse first: its real PelletView teardown retires the actor.
 if(actor->mPellet){Pellet* corpse=actor->mPellet;actor->mPellet=nullptr;corpse->kill(false);}
 if(mProvider.owns(h.actor))actor->kill(false);
 e.clear();return true;
}
} }
void pc_p2_original_chappy_retired(BTeki* actor){
 for(auto* n:p2original::chappy::instances())n->retired(static_cast<Creature*>(actor));
}
