#include "pc_p2_original_drop_engine.h"
#include "pc_p2_original_drop.h"
#include "pc_p2_original_actor.h"
#include "pc_p2_campaign_treasure_held.h"
#include "pc_p2_retail_cave_drop.h"
#include "pc_p2_original_foliage.h"
#include "Pellet.h"
#include "teki.h"
#include "netplay/pc_sim_rng.h"
#include <cstdio>
#include <cstdlib>
#include <set>
#include <map>
#include <cmath>
struct P2OriginalDropAccess {static bool ready(unsigned id){return pelletMgr&&pelletMgr->getConfig(id)&&pelletMgr->getShapeObject(id);}};
namespace {
int sizeIndex(unsigned size){return size==1?NUMPEL_OnePellet:size==5?NUMPEL_FivePellet:size==10?NUMPEL_TenPellet:NUMPEL_TwentyPellet;}
std::set<unsigned> droppedTokens;
std::map<unsigned,PcOriginalDropGeometry> geometry;
[[noreturn]] void failure(const std::string& e){std::fprintf(stderr,"P2_ORIGINAL_DROP_FAIL %s\n",e.c_str());std::abort();}
}
bool pc_p2_original_drop_host_ready(){return pelletMgr&&pelletMgr->getConfig('pr05')&&pelletMgr->pcEnsureShape('pr05');}
bool pc_p2_original_drop_register_geometry(unsigned source,PcOriginalDropGeometry callback){
 if(!callback||source>255||geometry.count(source))return false;
 geometry.emplace(source,std::move(callback));return true;
}
void pc_p2_original_drop_unregister_geometry(unsigned source){geometry.erase(source);}
bool pc_p2_original_drop_resources(const p2original::CatalogRow& row,std::string& e){
 if(row.sourceForm==p2original::SourceForm::CaveTekiInfo){
  const auto* cave=p2retail::descriptor(row.course);const auto* floor=cave?p2retail::definition(*cave,row.caveFloor):nullptr;
  if(!floor||row.caveRow>=floor->rows.size()){e="retail cave drop descriptor missing";return false;}
  if(!floor->rows[row.caveRow].heldTreasure.empty()&&!p2retail::heldDropHandler()){
   e="retail cave held drop provider unavailable";return false;
  }
  e.clear();return true; // No GenEnemy number-pellet parameters exist in TekiInfo.
 }
 if(!p2original::validateOriginalDrop(row.enemy,e))return false;
 // Invulnerable source Plants never execute a death/drop path. Preserve
 // literal common fields without demanding unused number-pellet assets.
 if(p2original::foliage::supported(row.enemy.source)){e.clear();return true;}
 if(row.enemy.source==55&&!geometry.count(55)){e="source55 original item throw geometry unavailable";return false;}
 if(row.enemy.treasureCode&&!pc_p2_campaign_treasure_held_resources(row,e))return false;
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
 if(p2original::foliage::supported(source))return true;
 if(droppedTokens.count(token))return true;
 const auto* row=p2original::originalActors().find(identity.generator);std::string e;
 if(row&&row->sourceForm==p2original::SourceForm::CaveTekiInfo){
  if(!p2retail::drop(static_cast<Creature*>(actor),*row,e))failure(e);
  droppedTokens.insert(token);return true;
 }
 if(!row||!pc_p2_original_drop_resources(*row,e))failure(e);
 if(droppedTokens.size()>=1048576)failure("original drop session token capacity exhausted");
 Vector3f position=actor->getCentre(),treasureVelocity(0,200,0);
 const auto transform=geometry.find(source);
 if(transform!=geometry.end()&&!transform->second(actor,position,treasureVelocity,e))failure(e);
 for(float v:{position.x,position.y,position.z,treasureVelocity.x,treasureVelocity.y,treasureVelocity.z})if(!std::isfinite(v))failure("original item throw transform invalid");
 droppedTokens.insert(token); // Latch before physical callbacks, no P1 fallback.
 p2original::DropIO io;io.draw=[](float& value,std::string&){value=pc_sim_randf(1.0f);return true;};
 io.treasure=[&](int code,std::string& error){
  if(code!=row->enemy.treasureCode){error="literal held treasure code changed";return false;}
  return pc_p2_campaign_treasure_held_spawn(actor,*row,identity,position,treasureVelocity,error);
 };
 io.number=[&](unsigned size,unsigned color,void*& out,std::string&){
  Pellet* pellet=pelletMgr->newNumberPellet(int(color),sizeIndex(size));out=pellet;
  if(pellet){pellet->init(position);pellet->mFaceDirection=actor->getDirection();pellet->startAI(FALSE);}
  return true;
 };
 io.velocity=[](void* pointer,const p2original::Position& velocity,std::string&){static_cast<Pellet*>(pointer)->mVelocity.set(velocity.x,velocity.y,velocity.z);return true;};
 if(!p2original::throwOriginalItems(row->enemy,io,e))failure(e);
 return true;
}
