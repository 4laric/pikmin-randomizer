#include "pc_p2_original_drop_engine.h"
#include "pc_p2_original_drop.h"
#include "pc_p2_original_actor.h"
#include "Pellet.h"
#include "teki.h"
#include "netplay/pc_sim_rng.h"
#include <cstdio>
#include <cstdlib>
#include <set>
struct P2OriginalDropAccess {static bool ready(unsigned id){return pelletMgr&&pelletMgr->getConfig(id)&&pelletMgr->getShapeObject(id);}};
namespace {
int sizeIndex(unsigned size){return size==1?NUMPEL_OnePellet:size==5?NUMPEL_FivePellet:size==10?NUMPEL_TenPellet:NUMPEL_TwentyPellet;}
std::set<unsigned> droppedTokens;
[[noreturn]] void failure(const std::string& e){std::fprintf(stderr,"P2_ORIGINAL_DROP_FAIL %s\n",e.c_str());std::abort();}
}
bool pc_p2_original_drop_resources(const p2original::CatalogRow& row,std::string& e){
 if(!p2original::validateOriginalDrop(row.enemy,e))return false;
 if(row.enemy.treasureCode){e="original treasure birth/delivery provider is not implemented";return false;}
 if(!pelletMgr){e="original number pellet manager unavailable";return false;}
 const int size=sizeIndex(row.enemy.pelletSize);
 const unsigned first=row.enemy.pelletColor==3?0:row.enemy.pelletColor,last=row.enemy.pelletColor==3?2:first;
 for(unsigned color=first;color<=last;++color){
  unsigned id=0;for(unsigned i=0;i<12;++i)if(numberPellets[i].mPelletColor==int(color)&&numberPellets[i].mPelletType==size)id=numberPellets[i].mPelletID;
  if(!id||!P2OriginalDropAccess::ready(id)){e="original number pellet physical config/shape missing";return false;}
 }
 e.clear();return true;
}
bool pc_p2_original_spawn_items(BTeki* actor){
 if(!actor)return false;
 unsigned source=0,token=0;p2original::InstanceIdentity identity;
 if(!p2original::originalActors().query(static_cast<Creature*>(actor),source,token,&identity))return false;
 if(droppedTokens.count(token))return true;
 const auto* row=p2original::originalActors().find(identity.generator);std::string e;
 if(!row||!pc_p2_original_drop_resources(*row,e))failure(e);
 if(droppedTokens.size()>=1048576)failure("original drop session token capacity exhausted");
 droppedTokens.insert(token); // Latch before physical callbacks, no P1 fallback.
 const Vector3f position=actor->getCentre();
 p2original::DropIO io;io.draw=[](float& value,std::string&){value=pc_sim_randf(1.0f);return true;};
 io.number=[&](unsigned size,unsigned color,void*& out,std::string&){
  Pellet* pellet=pelletMgr->newNumberPellet(int(color),sizeIndex(size));out=pellet;
  if(pellet){pellet->init(position);pellet->mFaceDirection=actor->getDirection();pellet->startAI(FALSE);}
  return true;
 };
 io.velocity=[](void* pointer,const p2original::Position& velocity,std::string&){static_cast<Pellet*>(pointer)->mVelocity.set(velocity.x,velocity.y,velocity.z);return true;};
 if(!p2original::throwOriginalItems(row->enemy,io,e))failure(e);
 return true;
}
