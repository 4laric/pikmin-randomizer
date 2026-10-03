#include "pc_p2_original_armor_native.h"
#include "pc_p2_armor.h"
#include "pc_p2_armor_policy.h"
#include "pc_p2_original_drop_engine.h"
#include "teki.h"
#include "TekiPersonality.h"
#include "Generator.h"
#include "Pellet.h"
#include "sysNew.h"
#include <cstdio>
#include <cstdlib>
#include <algorithm>
namespace p2original { namespace armor {
namespace {
std::set<Native*>& instances(){static std::set<Native*> n;return n;}
bool fail(std::string& e,const char* why){e=why;return false;}
struct Heap {int previous;Heap():previous(gsys->setHeap(SYSHEAP_App)){}~Heap(){gsys->setHeap(previous);}};
}
Native::Native():mProvider(*this){instances().insert(this);}
Native::~Native(){
 // Course must unload while managers/banks still exist. Never recycle an
 // actor silently or leave a native callback pointing at a destroyed owner.
 if(mProvider.size()){std::fprintf(stderr,"P2_ORIGINAL_ARMOR live provider destroyed\n");std::abort();}
 instances().erase(this);
}
bool Native::resources(const std::set<unsigned>& sources,std::string& e){
 if(!gsys||!tekiMgr||!pelletMgr)return fail(e,"original Armor managers unavailable");
 Heap heap;
 if(sources!=std::set<unsigned>{15})return fail(e,"original Armor concrete profile missing");
 auto* shape=tekiMgr->getTekiShapeObject(TEKI_Chappy);
 if(!tekiMgr->hasModel(TEKI_Chappy)||!shape||!shape->mShape||!shape->mAnimMgr
  ||!tekiMgr->getTekiParameters(TEKI_Chappy)||!tekiMgr->getStrategy(TEKI_Chappy))return fail(e,"original Armor chassis use-list/shape/animation/parameters unavailable");
 const unsigned id=TekiMgr::getTypeId(TEKI_Chappy);
 // PelletView corpses intentionally have no standalone PelletShapeObject.
 // The required dead bank is checked by prepare_original below.
 if(!pelletMgr->getConfig(id)
  ||tekiMgr->getTekiParameters(TEKI_Chappy)->getI(TPI_CorpseType)!=TEKICORPSE_LeaveCorpse)return fail(e,"original Armor ordinary corpse config/type unavailable");
 return pc_p2_armor_prepare_original(sources,e);
}
bool Native::commonResources(const CatalogRow& row,std::string& e){return pc_p2_original_drop_resources(row,e);}
bool Native::reserve(const std::vector<CatalogRow>& rows,unsigned count,std::string& e){
 if(!tekiMgr||tekiMgr->getMax()-tekiMgr->getSize()<int(count))return fail(e,"original Armor actual actor pool insufficient");
 unsigned pellets=0;
 for(const auto& row:rows)pellets+=(row.enemy.count-row.enemy.deathCount)*(1+(row.enemy.pelletProbability>0?std::max(row.enemy.pelletMinimum,row.enemy.pelletMaximum):0));
 if(!pelletMgr||pelletMgr->getMax()-pelletMgr->getSize()<int(pellets))return fail(e,"original Armor actual corpse/drop pool insufficient");
 e.clear();return true;
}
bool Native::allocate(Host& h,const Position& p,float facing,std::string& e){
 if(!gsys||!tekiMgr)return fail(e,"original Armor managers lost before birth");
 if(h.row.enemy.source!=15)return fail(e,"original Armor source profile lost");
 Heap heap;Teki* actor=tekiMgr->newTeki(TEKI_Chappy);
 if(!actor){e.clear();return true;} // Retail null allocation is not an omitted row.
 h.actor=actor;
 actor->mPersonality->reset(); // Neutral chassis; source drops stay in catalog.
 actor->mPersonality->mPosition.set(p.x,p.y,p.z);
 actor->mPersonality->mNestPosition.set(p.x,p.y,p.z);
 actor->mPersonality->mFaceDirection=facing;
 actor->mGenerator=h.generator;actor->reset();
 actor->mSRT.r.set(0,facing,0);actor->mFaceDirection=facing;actor->mSRT.s.set(1,1,1);
 // Genuine original generators have no P1 GenType. Their typed original
 // lifecycle owns respawn; only mirror the compatibility observation here.
 actor->mRebirthDay=h.generator->mRespawnInterval;
 e.clear();return true;
}
bool Native::bind(Host& h,std::string& e){
 if(!gsys||!tekiMgr||!pelletMgr)return fail(e,"original Armor managers lost before bind");
 Heap heap;
 unsigned source=0,token=0;InstanceIdentity id;
 if(!originalActors().query(h.actor,source,token,&id)||source!=h.row.enemy.source||token!=h.token
   ||id.generator!=h.row.enemy.uid||id.ordinal!=h.ordinal||id.catalog.empty())return fail(e,"original Armor registry identity disagrees with physical birth");
 if(!pc_p2_armor_bind_original(static_cast<BTeki*>(h.actor),h.token,e))return fail(e,"original Armor concrete FSM bind failed");
 std::printf("P2_ORIGINAL_ARMOR_BIRTH source=%u uid=%u ordinal=%u token=%u epoch=%llu activation=%llu\n",source,id.generator,id.ordinal,token,(unsigned long long)id.epoch,(unsigned long long)id.activation);
 e.clear();return true;
}
bool Native::cleanup(Host& h,std::string& e){
 auto* actor=static_cast<BTeki*>(h.actor);
 // Kill owned corpse first: its real PelletView teardown retires the actor.
 if(actor->mPellet){Pellet* corpse=actor->mPellet;actor->mPellet=nullptr;
  const bool killsActor=corpse->mPelletView==static_cast<PelletView*>(actor);
  corpse->kill(false);if(killsActor){e.clear();return true;}
 }
 actor->kill(false);
 e.clear();return true;
}
} }
void pc_p2_original_armor_retired(BTeki* actor){
 for(auto* n:p2original::armor::instances())n->retired(static_cast<Creature*>(actor));
}

bool pc_p2_original_armor_admitted(){for(auto* n:p2original::armor::instances())if(n->provider().prepared())return true;return false;}
