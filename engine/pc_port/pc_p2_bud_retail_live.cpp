#include "pc_p2_bud_retail_live.h"
#include "pc_p2_bud_native_live.h"
#include "Pom.h"
#include "gameflow.h"
#include "MoviePlayer.h"
namespace p2budorigin {namespace {
bool refuse(std::string& e,const char* m){e=m;return false;}
FloorIdentity origin(const p2retail::Snapshot& floor,const p2retail::BirthIdentity& birth,const Creation& live){
 return {live.campaign,live.session,floor.cave,floor.scene.visit,floor.sourceSha256,floor.catalogSha256,floor.scene.layoutSha256,birth.instance,floor.floor,birth.row,birth.ordinal,birth.epoch,birth.activation};
}
bool source6(const p2retail::Snapshot& floor,const p2retail::BirthIdentity& birth,const p2original::InstanceIdentity& supplied){
 const auto* cave=p2retail::descriptor(floor.cave);const auto* def=cave?p2retail::definition(*cave,floor.floor):nullptr;
 const auto* row=p2original::originalActors().find(supplied.generator);
 return def&&birth.row<def->rows.size()&&def->rows[birth.row].sourceId==6&&row&&row->enemy.source==6&&row->sourceForm==p2original::SourceForm::CaveTekiInfo
  &&row->course==floor.cave&&row->member==floor.source&&row->caveFloor==floor.floor&&row->caveRow==birth.row&&row->caveSourceSha256==floor.sourceSha256
  &&supplied.catalog==floor.scene.layoutSha256&&birth.ordinal==supplied.ordinal&&birth.epoch==supplied.epoch&&birth.activation==supplied.activation;
}
}
bool RetailLiveFloorReader::initialize(std::string& e){
 if(bound)return refuse(e,"retail live reader already owns an installation");
 p2retail::Snapshot actual;std::uint64_t epoch=0;p2retail::FloorPhase phase;
 if(!native.bindingFacts(actual,epoch,phase,e)||!pc_randomizer_original_session())return false;
 Creation next{pc_randomizer_original_campaign(),pc_randomizer_session_fingerprint(),actual.cave,actual.scene.visit,actual.sourceSha256,actual.catalogSha256,actual.scene.layoutSha256,actual.floor,epoch,actual.scene.serial,pc_randomizer_original_selection_revision()};
 next.phase=phase==p2retail::FloorPhase::Committed?CreationPhase::Committed:CreationPhase::Installing;
 if(!next.valid()||!native.bindingCurrent(actual.scene,epoch))return refuse(e,"actual original session/retail installation differs");
 physical=std::move(actual);facts=std::move(next);bound=true;return true;
}
const Creation* RetailLiveFloorReader::current()const noexcept{
 if(!bound||!native.bindingCurrent(physical.scene,facts.epoch)||facts.sessionRevision!=pc_randomizer_original_selection_revision())return nullptr;
 const auto phase=native.phase();if(phase!=p2retail::FloorPhase::Installing&&phase!=p2retail::FloorPhase::Committed)return nullptr;
 facts.phase=phase==p2retail::FloorPhase::Committed?CreationPhase::Committed:CreationPhase::Installing;
 // Named native fields, not a caller permission flag. This agrees with the
 // existing native randomizer gameplay tick and adds explicit day-end refusal.
 facts.gameActive=phase==p2retail::FloorPhase::Committed&&gameflow.mMoviePlayer&&!gameflow.mMoviePlayer->mIsActive&&!gameflow.mPauseAll&&!gameflow.mIsUIOverlayActive&&!gameflow.mIsDayEndActive;
 return &facts;
}
bool RetailLiveFloorReader::expectedBud(const Pom* pom,unsigned token,const p2original::InstanceIdentity& id,FloorIdentity& out,std::string& e)const{
 const auto* live=current();if(!live||live->phase!=CreationPhase::Committed)return refuse(e,"source6 output requires committed native floor");
 p2retail::BirthIdentity birth;p2retail::Snapshot floor;
 if(!native.expectedSourceBirth(static_cast<const Creature*>(pom),token,id,birth,floor,e)||!source6(floor,birth,id))return refuse(e,"actual committed source6 birth differs");
 auto next=origin(floor,birth,*live);if(!valid(next)||!current())return refuse(e,"source6 owned floor changed");out=std::move(next);return true;
}
bool RetailLiveFloorReader::emitted(const Record& record,std::string& e)const{
 const auto* live=current();if(!live||live->phase!=CreationPhase::Committed)return refuse(e,"actual committed output floor unavailable");
 if(record.identity.floor.cave!=physical.cave||record.identity.floor.floor!=physical.floor||record.identity.floor.epoch!=facts.epoch||record.identity.floor.visit!=physical.scene.visit||record.identity.floor.layoutSha!=physical.scene.layoutSha256)
  return travel&&travel->retained(record,e); // real destination party/graph owner
 p2retail::BirthIdentity birth;p2retail::Snapshot floor;
 if(!native.knownSourceBirth(record.identity.bud,birth,floor,e)||!source6(floor,birth,record.identity.bud)||!(origin(floor,birth,*live)==record.identity.floor))return refuse(e,"successful output actual parent census differs");
 return current()!=nullptr;
}
bool RetailLiveFloorReader::carried(const Snapshot& s,const std::vector<BodyBinding>& b,std::string& e)const{return current()&&travel&&travel->carried(s,b,e);}
bool RetailLiveFloorReader::receive(const Snapshot& s,const std::vector<BodyBinding>& b,std::string& e)const{return current()&&travel&&travel->receive(s,b,e);}
}
