#pragma once
#include "pc_p2_bud_live_floor.h"
// Strong native functions from the actual c482 OriginalSession producer.
// No weak/default implementation or descriptor-as-card fallback is provided.
bool pc_randomizer_original_session();
std::string pc_randomizer_original_campaign();
std::string pc_randomizer_session_fingerprint();
bool pc_randomizer_original_input(const std::string&,std::string&,std::string&);
std::uint64_t pc_randomizer_original_selection_revision()noexcept;
namespace p2budorigin {
class NativeDonorReader {
public:
 virtual ~NativeDonorReader()=default;
 // Actual canonical GenPiki/BudConversion/party storage lookup while alive.
 // Party UID0 needs its own persisted party key, never a fabricated GenPiki row.
 virtual bool query(const Piki*,Donor&,std::string&)const=0;
};
// Concrete session adapter: selected OriginalSession inputs are read by the
// real native producer; floor/party readers are the source-owning native APIs.
// selectedCard is optional ONLY for newgame. Supply the actual native card
// Authority before first SAVE adoption/cold restore. No fake Proof is issued.
class NativeLiveAuthority final:public Authority {
 const LiveFloorReader& floor;const NativeDonorReader& donors;const Authority* selectedCard;
 bool selectedContext(Creation& out,std::string& e)const{
  const auto* live=liveCreation();if(!live||!live->valid()){e="actual original native floor selection is absent";return false;}
  Creation next=*live;std::string bytes;
  if(!pc_randomizer_original_session()||pc_randomizer_original_campaign()!=next.campaign||pc_randomizer_session_fingerprint()!=next.session
     ||!pc_randomizer_original_input("p2-original/calendar.p2sc",bytes,e)){e="actual authenticated OriginalSession/floor pairing refused";return false;}
  live=liveCreation();if(!live||!(*live==next)){e="native selection changed during immutable input read";return false;}out=std::move(next);e.clear();return true;
 }
public:
 NativeLiveAuthority(const LiveFloorReader& f,const NativeDonorReader& d,const Authority* card=nullptr):floor(f),donors(d),selectedCard(card){}
 const Creation* liveCreation()const noexcept override{
  const auto* facts=floor.current();const auto revision=pc_randomizer_original_selection_revision();
  return facts&&facts->valid()&&revision&&facts->sessionRevision==revision?facts:nullptr;
 }
 bool creation(Creation& out,std::string& e)const override{return selectedContext(out,e);}
 bool context(std::string& campaign,std::string& session,std::string& e)const override{Creation created;if(!selectedContext(created,e))return false;campaign=std::move(created.campaign);session=std::move(created.session);return true;}
 bool bud(const Pom* pom,unsigned token,const p2original::InstanceIdentity& id,FloorIdentity& out,std::string& e)const override{
  Creation actual;FloorIdentity native;if(!selectedContext(actual,e)||!floor.expectedBud(pom,token,id,native,e))return false;
  if(!valid(native)||native.campaign!=actual.campaign||native.session!=actual.session||native.cave!=actual.cave||native.floor!=actual.floor||native.visit!=actual.visit||native.sourceSha!=actual.sourceSha||native.catalogSha!=actual.catalogSha||native.layoutSha!=actual.layoutSha||native.epoch!=actual.epoch){e="actual source6 census disagrees with owned floor";return false;}
  const auto* current=liveCreation();if(!current||!(*current==actual)){e="native floor changed during source6 lookup";return false;}out=std::move(native);return true;
 }
 bool donor(const Piki* p,Donor& out,std::string& e)const override{Creation actual;Donor native;if(!p||!selectedContext(actual,e)||!donors.query(p,native,e)||!valid(native)||native.campaign!=actual.campaign)return false;const auto* current=liveCreation();if(!current||!(*current==actual))return false;out=std::move(native);return true;}
 bool record(const Record& r,std::string& e)const override{Creation actual;if(!selectedContext(actual,e)||r.identity.floor.campaign!=actual.campaign||r.identity.floor.session!=actual.session||!floor.emitted(r,e))return false;const auto* current=liveCreation();return current&&*current==actual;}
 bool carried(const Snapshot& s,const std::vector<BodyBinding>& b,std::string& e)const override{Creation actual;return selectedContext(actual,e)&&floor.carried(s,b,e);}
 bool receive(const Snapshot& s,const std::vector<BodyBinding>& b,std::string& e)const override{Creation actual;return selectedContext(actual,e)&&floor.receive(s,b,e);}
 bool selected(p2originalcheckpoint::Proof& p,std::string& e)const override{if(!selectedCard){e="no actual selected native card exists";return false;}return selectedCard->selected(p,e);}
 bool stillCurrent(const p2originalcheckpoint::Proof& p)const noexcept override{return selectedCard&&selectedCard->stillCurrent(p)&&liveCreation();}
 bool saved(const Snapshot& s,const p2originalcheckpoint::Proof& p,std::string& e)const override{if(!selectedCard){e="selected native card reader required";return false;}return selectedCard->saved(s,p,e);}
};
}
