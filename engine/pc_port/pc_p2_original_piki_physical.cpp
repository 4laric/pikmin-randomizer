#include "pc_p2_original_piki_physical.h"
#include "pc_p2_original_piki_init.h"
#include "pc_p2_species.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "GameStat.h"
#include <cmath>
namespace {
using Result=p2original::PikiBirthResult;
void discard(Piki* p){
 // Disposal of a newly initialized owned actor must not leave a flower seed.
 p->setEraseKill();p->kill(false);
 pc_p2_original_piki_origin_forget(p);
}
}
Result pc_p2_original_piki_physical_birth(const OriginalPikiBody& source,
 const std::array<float,3>& position,Piki*& out,std::string& error){
 for(float value:position)if(!std::isfinite(value)){
  error="nonfinite original Piki birth position";return Result::Failed;
 }
 if(!pikiMgr||!pikiMgr->mPikiParms||pc_p2_original_piki_init_busy()||!pc_p2_original_piki_body_birth_admit(source)){
  error="original Piki source/manager admission failed";return Result::Failed;
 }
 // P1 mapPikis already includes mePikis (heads). Keep original P2 field cap;
 // the native manager may additionally refuse an unavailable physical slot.
 const int population=GameStat::mapPikis;
 if(population<0){error="invalid native Piki population";return Result::Failed;}
 if(population>=100){error.clear();return Result::CapacitySkipped;}
 auto* body=static_cast<Piki*>(pikiMgr->birthOriginalP2());
 if(!body){error.clear();return Result::CapacitySkipped;}
 if(body->mGenerator){
  // Original genPiki returns null from generate and owns no native Generator.
  // A stale/foreign generator pointer cannot become source personality.
  pikiMgr->kill(body);error="foreign generator in original Piki pool slot";return Result::Failed;
 }
 // Native GenObjectPiki registers once BEFORE init and the work->free transfer.
 const int baseColor=source.state.species<=P2SpeciesYellow?source.state.species:Red;
 GameStat::workPikis.inc(baseColor);GameStat::update();
 {
  PcOriginalPikiInitScope birth(body);
  if(!birth.valid()){
   // No init took place: retire only the just-born manager slot and registration.
   pikiMgr->kill(body);GameStat::workPikis.dec(baseColor);GameStat::update();
   error="nested original Piki birth scope";return Result::Failed;
  }
  body->init(nullptr);
  // init itself has no general partial-init rollback contract. Once it has
  // completed, this adapter owns and disposes every failed post-init phase.
  bool owned=true;
  const auto release=[&](){owned=false;discard(body);};
  try {
  body->resetPosition(Vector3f(position[0],position[1],position[2]));
  if(!pc_p2_set_species(body,source.state.species)){
   release();error="original Piki species initialization failed";return Result::Failed;
  }
  body->mHappa=Leaf;
  body->changeMode(PikiMode::FreeMode,nullptr);
  if(pc_p2_species(body)!=source.state.species||!body->isAlive()){
   release();error="original Piki physical species/state mismatch";return Result::Failed;
  }
  if(!pc_p2_original_piki_body_associate_birth(body,source)){
   release();error="original Piki canonical birth notification rejected";return Result::Failed;
  }
  owned=false;
  } catch(...) {if(owned)release();throw;}
 }
 out=body;error.clear();return Result::Born;
}
