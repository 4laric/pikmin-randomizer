#pragma once
#include "pc_p2_original_catalog.h"
#include "pc_p2_retail_cave_context.h"
class Creature;
namespace p2retail {
using HeldDropHandler=std::function<bool(Creature*,const p2original::CatalogRow&,std::string&)>;
inline HeldDropHandler& heldDropHandler(){static HeldDropHandler handler;return handler;}
inline bool drop(Creature* actor,const p2original::CatalogRow& row,std::string& error){
 const auto* cave=descriptor(row.course);const auto* floor=cave?definition(*cave,row.caveFloor):nullptr;
 if(!actor||!floor||row.caveRow>=floor->rows.size()){error="retail cave drop source missing";return false;}
 if(floor->rows[row.caveRow].heldTreasure.empty()){error.clear();return true;}
 if(!heldDropHandler()){error="retail cave held drop provider absent";return false;}
 return heldDropHandler()(actor,row,error);
}
}
