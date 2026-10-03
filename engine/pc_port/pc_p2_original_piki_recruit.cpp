#include "pc_p2_original_piki_recruit.h"
#include "pc_p2_original_piki_origin.h"
#include "pc_p2_source_body.h"
#include "pc_p2_original_progress.h"
#include <thread>
namespace {
std::string selectedCampaign,admittedCatalog;
std::thread::id owner;
bool fail(std::string& e,const char* s){e=s;return false;}
bool inspect(Piki* p,unsigned captain,bool movie,bool nativeEligible,
             PcP2SourceBody& body,bool& source,std::string& e){
 if(!selectedCampaign.empty()&&owner!=std::this_thread::get_id())
  return fail(e,"original recruitment requires the admitted game thread");
 if(!p)return fail(e,"null recruitment body");
 const auto kind=pc_p2_source_body_query(p,body);
 if(kind==PcP2SourceBodyKind::Unavailable)return fail(e,"original typed body discriminator unavailable");
 source=kind!=PcP2SourceBodyKind::None;
 if(!source){
  OriginalPikiOrigin legacy;
  if(pc_p2_original_piki_origin_query(p,legacy))
   return fail(e,"original recruitment body flags unavailable");
  e.clear();return true; // Ordinary P1 state/events are unchanged.
 }
 const auto& progress=p2original::originalProgress();
 if(selectedCampaign.empty()||admittedCatalog.empty()
    ||progress.snapshot().campaign!=selectedCampaign
    ||pc_p2_original_piki_catalog_fingerprint()!=admittedCatalog
    ||!pc_p2_source_body_admitted(body,selectedCampaign,admittedCatalog,e))
  return fail(e,"original recruitment campaign/catalog authority mismatch");
 if(!nativeEligible||!progress.captainAllowed(captain,body.state.wasWild))
  return fail(e,"original source body cannot join this captain");
 if(body.state.wild&&(movie||body.state.species>2))
  return fail(e,"original wild recruitment requires inactive-movie RGB body");
 e.clear();return true;
}
}
bool pc_p2_original_piki_recruit_bind(const std::string& campaign,
 const std::string& catalog,std::string& e){
 const auto& progress=p2original::originalProgress();
 if(!progress.ready()||progress.snapshot().campaign!=campaign
    ||catalog.empty()||pc_p2_original_piki_catalog_fingerprint()!=catalog)
  return fail(e,"original recruitment pair does not match installed authorities");
 if(!selectedCampaign.empty()&&(selectedCampaign!=campaign||admittedCatalog!=catalog
     ||owner!=std::this_thread::get_id()))
  return fail(e,"original recruitment pair already bound");
 // All allocating preparation precedes publication of either binding string.
 std::string nextCampaign=campaign,nextCatalog=catalog;
 selectedCampaign.swap(nextCampaign);admittedCatalog.swap(nextCatalog);
 owner=std::this_thread::get_id();e.clear();return true;
}
void pc_p2_original_piki_recruit_unbind() noexcept {
 selectedCampaign.clear();admittedCatalog.clear();owner=std::thread::id{};
}
bool pc_p2_original_piki_recruit_allowed(Piki* p,unsigned captain,bool movie,
 bool nativeEligible,std::string& e){
 PcP2SourceBody body;bool source=false;
 return inspect(p,captain,movie,nativeEligible,body,source,e);
}
bool pc_p2_original_piki_recruit_accepted(Piki* p,unsigned captain,bool movie,
 bool nativeEligible,std::string& e){
 PcP2SourceBody body;bool source=false;
 if(!inspect(p,captain,movie,nativeEligible,body,source,e))return false;
 if(!source||!body.state.wild)return true;
 auto& progress=p2original::originalProgress();
 const auto before=progress.snapshot();
 if(!progress.recruited(body.state.species,e))return false;
 // The native game thread has no intervening callbacks between these writes.
 // Still restore progression if the canonical body rejects the commit.
 if(!pc_p2_source_body_recruited(p)){
  std::string rollback;
  if(!progress.restore(before,rollback))return fail(e,"original recruitment rollback refused");
  return fail(e,"original canonical body rejected recruitment");
 }
 e.clear();return true; // Red first-met belongs to the separate hello event.
}

bool pc_p2_original_piki_contact_owner_allowed(Piki* p,int playerId,unsigned captain,
 bool versus,std::string& e){
 if(playerId==-1||(playerId>=0&&unsigned(playerId)==captain)){e.clear();return true;}
 if(versus)return fail(e,"versus contact retains native player ownership");
 PcP2SourceBody body;bool source=false;
 if(!inspect(p,captain,false,true,body,source,e))return false;
 if(!source)return fail(e,"ordinary contact retains native player ownership");
 return true; // Commit still rechecks actual movie/callable state before writes.
}

bool pc_p2_original_piki_recruit_pair_ready() noexcept {
 const auto& progress=p2original::originalProgress();
 return !selectedCampaign.empty()&&!admittedCatalog.empty()
     &&owner==std::this_thread::get_id()&&progress.ready()
     &&progress.snapshot().campaign==selectedCampaign
     &&pc_p2_original_piki_catalog_fingerprint()==admittedCatalog;
}
