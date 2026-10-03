#include "pc_p2_original_sprout_native.h"
#include "pc_p2_original_onyon_native.h"
#include "pc_p2_source_body.h"
#include "pc_randomizer.h"
#include "GoalItem.h"
#include "PikiHeadItem.h"
#include "Piki.h"
#include "ItemMgr.h"
#include "BaseInf.h"
#include <memory>
#include <cstdio>
#include <cstdlib>
namespace {
using namespace p2originalonyon;
std::unique_ptr<Lineage> lineage;
std::string selectedCampaign;
[[noreturn]] void fault(const std::string& text){std::fprintf(stderr,"P2_ORIGINAL_SPROUT_FAIL %s\n",text.c_str());std::abort();}
bool fail(std::string& e,const char* text){e=text;return false;}
std::string session(){return pc_randomizer_original_session()?pc_randomizer_session_fingerprint():std::string();}
bool current(std::string& e){
 const auto selected=session();
 if(selected.size()!=64)return fail(e,"source lineage requires authenticated original campaign");
 if(!pc_p2_original_sprout_install_reader())return fail(e,"source lineage common reader installation refused");
 if(!lineage){selectedCampaign=pc_randomizer_original_campaign();lineage=std::make_unique<Lineage>(selected);}
 if(selectedCampaign!=pc_randomizer_original_campaign())return fail(e,"source lineage campaign authority changed");
 if(lineage->sessionFingerprint()!=selected)return fail(e,"source lineage belongs to another campaign; explicit new-session boundary required");
 return true;
}
bool owner(GoalItem* onion,Root& root,std::string& e){
 if(!current(e)||!pc_p2_original_onyon_root(onion,root,e))return false;
 return pc_p2_original_onyon_access(onion)||fail(e,"source lineage receiver is not booted");
}
bool selection(GoalItem* onion,const PcOriginalSproutOrigin& admitted,std::string& e){
 Root root;std::uint64_t serial=0;
 if(!owner(onion,root,e)||!lineage->nextPending(root,serial,e))return false;
 return (root==admitted.root&&serial==admitted.memberSerial)||fail(e,"source sprout pending selection changed");
}
QueryResult head(const PikiHeadItem* p,MemberRecord& r,std::uint64_t& h,std::string& e){
 if(!lineage){e.clear();return QueryResult::Missing;}
 MemberRecord candidate;std::uint64_t handle=0;const auto result=lineage->queryHead(p,session(),candidate,handle,e);
 if(result!=QueryResult::Present)return result;
 if(selectedCampaign!=pc_randomizer_original_campaign()){e="labelled source head campaign changed";return QueryResult::Unavailable;}
 r=std::move(candidate);h=handle;return QueryResult::Present;
}
}
bool pc_p2_original_sprout_new_session(std::string& e){
 if(!pc_randomizer_original_session())return fail(e,"source lineage new-session requires original campaign");
 if(!lineage)return current(e);
 const auto campaign=pc_randomizer_original_campaign();
 if(!lineage->newSession(session(),e))return false;
 selectedCampaign=campaign;return true;
}
bool pc_p2_original_sprout_reward(GoalItem* onion,const p2originalonyon::SeedCause& cause,unsigned count,std::string& e){
 p2originalonyon::Root root;p2originalonyon::RewardPlan plan;
 return owner(onion,root,e)&&lineage->preflightReward(root,cause,count,plan,e)&&lineage->commitReward(plan,e);
}
bool pc_p2_original_sprout_reward_prepare(GoalItem* onion,const p2originalonyon::SeedCause& cause,unsigned count,p2originalonyon::RewardPlan& out,std::string& e){
 p2originalonyon::Root root;return owner(onion,root,e)&&lineage->preflightReward(root,cause,count,out,e);
}
void pc_p2_original_sprout_reward_commit(GoalItem* onion,const p2originalonyon::RewardPlan& plan){
 p2originalonyon::Root root;std::string e;
 if(!owner(onion,root,e)||!(root==plan.root)||!lineage->commitReward(plan,e))fault("source reward lost actual receiver/plan: "+e);
}
bool pc_p2_original_sprout_owner(GoalItem* onion,PcOriginalSproutOrigin& out,std::string& e){
 PcOriginalSproutOrigin candidate;
 if(!owner(onion,candidate.root,e)||!lineage->nextPending(candidate.root,candidate.memberSerial,e))return false;
 if(!itemMgr||!itemMgr->getPikiHeadMgr()||itemMgr->getPikiHeadMgr()->getMax()<100)return fail(e,"source sprout requires admitted physical100-head pool");
 out=std::move(candidate);e.clear();return true;
}
void pc_p2_original_sprout_bind(PikiHeadItem* p,GoalItem* onion,const PcOriginalSproutOrigin& admitted){
 std::string e;std::uint64_t h=0;
 if(!selection(onion,admitted,e)||!lineage->bindPendingHead(admitted.memberSerial,admitted.root,p,h,e))fault(e);
}
void pc_p2_original_sprout_store(GoalItem* onion,const PcOriginalSproutOrigin& admitted){
 std::string e;if(!selection(onion,admitted,e)||!lineage->storePending(admitted.memberSerial,admitted.root,e))fault(e);
}
bool pc_p2_original_sprout_query(const PikiHeadItem* p,PcOriginalSproutOrigin& out){
 p2originalonyon::MemberRecord r;std::uint64_t h=0;std::string e;const auto result=head(p,r,h,e);
 if(result==p2originalonyon::QueryResult::Unavailable)fault(e);
 if(result==p2originalonyon::QueryResult::Missing)return false;
 const auto* emitted=std::get_if<p2originalonyon::OnyonEmission>(&r.origin);
 if(!emitted)fault("source head lacks typed emission origin");
 out={emitted->root,r.serial};return true;
}
bool pc_p2_original_sprout_owned(const PikiHeadItem* p){PcOriginalSproutOrigin r;return pc_p2_original_sprout_query(p,r);}
bool pc_p2_original_sprout_head_tag(const PikiHeadItem* p)noexcept{return lineage&&lineage->ownsHead(p);}
p2originalonyon::QueryResult pc_p2_original_sprout_head_query(const PikiHeadItem* p,p2originalonyon::MemberRecord& out,std::uint64_t& h,std::string& e){
 p2originalonyon::MemberRecord candidate;std::uint64_t handle=0;const auto result=head(p,candidate,handle,e);
 if(result!=p2originalonyon::QueryResult::Present)return result;
 if(!p||p->mSeedColor!=candidate.state.species||p->mFlowerStage<0||p->mFlowerStage>2){e="labelled source head physical color/maturity mismatch";return p2originalonyon::QueryResult::Unavailable;}
 candidate.state.maturity=static_cast<std::uint8_t>(p->mFlowerStage);out=std::move(candidate);h=handle;e.clear();return p2originalonyon::QueryResult::Present;
}
bool pc_p2_original_sprout_color(const PikiHeadItem* p,int color){
 PcOriginalSproutOrigin r;if(!pc_p2_original_sprout_query(p,r))return false;
 if(color!=r.root.species)fault("source sprout color disagrees with actual Onion");return true;
}
void pc_p2_original_sprout_to_body(PikiHeadItem* p,Piki* body){
 p2originalonyon::MemberRecord r;std::uint64_t h=0,bh=0;std::string e;
 if(head(p,r,h,e)!=p2originalonyon::QueryResult::Present||!body||body->mColor!=r.state.species||body->mHappa<0||body->mHappa>2)fault("source conversion lacks matching initialized body");
 if(!lineage->headToBody(p,h,body,bh,e))fault(e);
 r.state.maturity=static_cast<std::uint8_t>(body->mHappa);
 if(!lineage->updateBody(body,bh,r.state,e))fault(e);
}
void pc_p2_original_sprout_forget(PikiHeadItem* p){
 p2originalonyon::MemberRecord r;std::uint64_t h=0;std::string e;const auto result=head(p,r,h,e);
 if(result==p2originalonyon::QueryResult::Unavailable)fault(e);
 if(result==p2originalonyon::QueryResult::Present&&!lineage->retireHead(p,h,e))fault(e);
}
p2originalonyon::QueryResult pc_p2_original_sprout_body_query(const Piki* p,p2originalonyon::MemberRecord& out,std::uint64_t& h,std::string& e){
 using namespace p2originalonyon;
 if(!lineage){e.clear();return QueryResult::Missing;}
 MemberRecord candidate;std::uint64_t handle=0;const auto result=lineage->queryBody(p,session(),candidate,handle,e);
 if(result!=QueryResult::Present)return result;
 if(selectedCampaign!=pc_randomizer_original_campaign()){e="labelled source body campaign changed";return QueryResult::Unavailable;}
 if(!p||p->mColor!=candidate.state.species||p->mHappa<0||p->mHappa>2){e="labelled source body physical color/maturity mismatch";return QueryResult::Unavailable;}
 candidate.state.maturity=static_cast<std::uint8_t>(p->mHappa);out=std::move(candidate);h=handle;e.clear();return QueryResult::Present;
}
void pc_p2_original_sprout_body_forget(Piki* p){
 if(!lineage)return;
 p2originalonyon::MemberRecord r;std::uint64_t h=0;std::string e;const auto result=lineage->queryBody(p,session(),r,h,e);
 if(result==p2originalonyon::QueryResult::Unavailable)fault(e);
 if(result==p2originalonyon::QueryResult::Present&&!lineage->retireBody(p,h,e))fault(e);
}
bool pc_p2_original_sprout_body_owned(const Piki* p)noexcept{return lineage&&lineage->ownsBody(p);}
bool pc_p2_original_sprout_body_lifetime(const Piki* p,std::uint64_t& out)noexcept{return lineage&&lineage->bodyHandle(p,out);}
std::string pc_p2_original_sprout_campaign(){return selectedCampaign;}
bool pc_p2_original_sprout_body_recruited(Piki* p,std::uint64_t lifetime){
 p2originalonyon::MemberRecord r;std::uint64_t h=0;std::string e;
 if(pc_p2_original_sprout_body_query(p,r,h,e)!=p2originalonyon::QueryResult::Present||h!=lifetime)return false;
 r.state.wild=false;return lineage->updateBody(p,h,r.state,e);
}
void pc_p2_original_sprout_scene_exit()noexcept{
 if(!lineage)return;
 // This callback follows the Party observer and actual scene disposal. It
 // removes BODY pointers only; it does not invent stock or discard live HEADs.
 lineage->retireSceneBodies();
 std::string e;if(!lineage->courseUnload(e))fault(e);
}
bool pc_p2_original_sprout_deposit(GoalItem* onion,Piki* p,std::string& e){
 using namespace p2originalonyon;
 Root root;if(!owner(onion,root,e)||!p||p->mColor!=root.species||p->mHappa<0||p->mHappa>2)return fail(e,"source deposit actual receiver/body mismatch");
 MemberRecord r;std::uint64_t h=0;const auto result=pc_p2_original_sprout_body_query(p,r,h,e);
 if(result==QueryResult::Unavailable)return false;
 if(result==QueryResult::Missing){
  PcP2SourceBody common;const auto kind=pc_p2_source_body_query(p,common);
  if(kind==PcP2SourceBodyKind::Unavailable)return fail(e,"labelled source deposit ancestry is unavailable");
  if(kind==PcP2SourceBodyKind::BudConversion)return fail(e,"converted source stock continuation is not admitted by Onion lineage");
  if(kind==PcP2SourceBodyKind::OnyonEmission)return fail(e,"source body reader/lineage ownership disagree");
  OriginalPikiBody authored;std::uint64_t serial=0;
  if(!pc_p2_original_piki_body_query(p,authored))return lineage->markUnknownStock(root.species,1,e);
  if(!lineage->adoptAuthored(session(),authored,static_cast<std::uint8_t>(p->mHappa),p,serial,h,e))return false;
  r.state={authored.state.species,static_cast<std::uint8_t>(p->mHappa),authored.state.wild,authored.state.wasWild};
 }
 return lineage->updateBody(p,h,r.state,e)&&lineage->depositBody(p,h,root,e);
}
bool pc_p2_original_sprout_stock(GoalItem* onion,p2originalonyon::MemberRecord& out,std::string& e){
 p2originalonyon::Root root;p2originalonyon::MemberRecord selected;
 if(!owner(onion,root,e)||lineage->peekStored(root.species,selected,e)!=p2originalonyon::StockResult::Present)return false;
 std::array<std::uint64_t,3> known;
 if(!lineage->storedCounts(root.species,known))return fail(e,"source stock lineage is unavailable");
 for(unsigned maturity=0;maturity<3;++maturity){
  const auto actual=pikiInfMgr.mPikiCounts[root.species][maturity];
  if(actual<0||known[maturity]!=static_cast<std::uint64_t>(actual))
   return fail(e,"actual source stock contains count-only or mismatched member ancestry");
 }
 out=std::move(selected);e.clear();return true;
}
void pc_p2_original_sprout_withdraw(GoalItem* onion,Piki* p,const p2originalonyon::MemberRecord& selected){
 p2originalonyon::Root root;std::uint64_t h=0;std::string e;
 if(!owner(onion,root,e)||!p||p->mColor!=selected.state.species||p->mHappa!=selected.state.maturity||!lineage->withdrawStored(selected.serial,root,p,h,e))fault("source withdrawal lost allocation/selection proof: "+e);
}
bool pc_p2_original_sprout_preflight_course_finish(std::string& e){
 // Check persistent graph labels even if current campaign resolution is lost.
 // Do not initialize lineage or retire BODYs before the Party observer.
 if(!lineage){e.clear();return true;}
 return lineage->preflightCourseFinish(e);
}
bool pc_p2_original_sprout_unload(std::string& e){if(!lineage){e.clear();return true;}return lineage->courseUnload(e);}
