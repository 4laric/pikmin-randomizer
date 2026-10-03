#include "pc_p2_retail_cave_foliage.h"
#include "pc_p2_original_foliage_native.h"
#include "Vector.h"
namespace p2retail {
bool bindFoliage(NativeFloor& floor,p2original::foliage::Native& native,std::string& error){
 auto* leaf=&native.provider();FamilyOps ops;
 ops.prepare=[leaf](const std::vector<p2original::CatalogRow>& rows,std::string& e){
  return leaf->cavePrepare(rows,e)&&leaf->caveReserve(rows,e);
 };
 ops.birth=[leaf](const p2original::CatalogRow& row,const Snapshot&,Generator* generator,unsigned ordinal,
                  const Vector3f& position,float yaw,Creature*& actor,bool& suppressed,std::string& e){
  suppressed=false;return leaf->caveBirth(row,generator,ordinal,{position.x,position.y,position.z},yaw,actor,e);
 };
 ops.bind=[leaf](const p2original::CatalogRow& row,Creature* actor,unsigned token,std::string& e){
  return leaf->bind(row,actor,token,e);
 };
 ops.release=[leaf](Creature* actor,unsigned token,std::string& e){return leaf->release(actor,token,e);};
 // Cave preflight with an empty roster revokes only unused admission/reservation
 // state after every actual host has released; native resource banks may cache.
 ops.cancel=[leaf](std::string& e){return leaf->cavePrepare({},e);};
 ops.retired=[](Creature*,std::string& e){e.clear();return true;}; // Native forget owns its host cleanup.
 return floor.familyGroup({47,91,92},std::move(ops),error);
}
}
