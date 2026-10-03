#include "pc_p2_original_onyon_lineage.h"
#include <limits>
#include <tuple>
#include <utility>
namespace p2originalonyon {
namespace {
bool fail(std::string& e,const char* text){e=text;return false;}
bool hex(const std::string& s){if(s.size()!=64)return false;for(char c:s)if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return false;return true;}
bool key(const std::string& s){if(s.empty()||s.size()>2048)return false;for(unsigned char c:s)if(c<32||c==127)return false;return true;}
bool stateValid(const MemberBodyState& s){return s.species<3&&s.maturity<3&&(!s.wild||s.wasWild);}
bool causeValid(const SeedCause& c){
 if((c.kind!=CauseKind::Corpse&&c.kind!=CauseKind::Number)||!hex(c.catalogFingerprint)||!c.sourceUid||c.sourceType>65535||!c.activation)return false;
 if(c.kind==CauseKind::Corpse)return c.ordinal<10&&c.epoch&&c.sourceType!=55&&!c.numericChildSlot&&c.ancestry==AncestryKind::None&&!c.emissionOrdinal&&!c.member;
 // Match resource ChildIdentity rather than inventing a child UID/epoch or
 // reinterpreting the parent source type as the emitted member's kind.
 if(c.numericChildSlot>1)return false;
 if(c.ancestry==AncestryKind::None)return !c.emissionOrdinal&&!c.member;
 if(c.numericChildSlot||c.emissionOrdinal)return false;
 return (c.ancestry==AncestryKind::TamagoMushi&&c.member<10)||
        (c.ancestry==AncestryKind::ShijimiChou&&c.member<5);
}
auto causeTuple(const SeedCause& c){return std::tie(c.kind,c.catalogFingerprint,c.sourceUid,c.sourceType,c.ordinal,c.epoch,c.activation,c.numericChildSlot,c.ancestry,c.emissionOrdinal,c.member);}
}
bool Root::operator==(const Root& b)const{return std::tie(sessionFingerprint,sourceSha,sourceKey,sourceUid,species,incarnation)==std::tie(b.sessionFingerprint,b.sourceSha,b.sourceKey,b.sourceUid,b.species,b.incarnation);}
bool SeedCause::operator==(const SeedCause& b)const{return causeTuple(*this)==causeTuple(b);}
bool SeedCause::operator<(const SeedCause& b)const{return causeTuple(*this)<causeTuple(b);}
bool Lineage::AuthoredKey::operator<(const AuthoredKey& b)const{return std::tie(catalog,key,uid,attempt,activation)<std::tie(b.catalog,b.key,b.uid,b.attempt,b.activation);}
Lineage::Lineage(std::string session):mSession(std::move(session)){}
bool Lineage::rootValid(const Root& r)const{return hex(mSession)&&r.sessionFingerprint==mSession&&hex(r.sourceSha)&&key(r.sourceKey)&&r.species<3&&r.incarnation;}
bool Lineage::preflightReward(const Root& r,const SeedCause& c,std::uint32_t count,RewardPlan& out,std::string& e)const{
 if(!rootValid(r)||!causeValid(c)||!count||count>memberLimit-mMembers.size())return fail(e,"invalid source reward root/cause/count or member capacity exhausted");
 if(mRewards.count(c))return fail(e,"source reward cause already committed");
 RewardPlan candidate{r,c,count,mNextSerial};out=std::move(candidate);e.clear();return true;
}
bool Lineage::commitReward(const RewardPlan& plan,std::string& e){
 RewardPlan observed;if(!preflightReward(plan.root,plan.cause,plan.count,observed,e))return false;
 if(plan.firstSerial!=observed.firstSerial)return fail(e,"source reward plan is stale");
 // Prepare all allocating nodes privately, then merge without allocation.
 std::map<std::uint64_t,MemberRecord> members;
 for(std::uint32_t i=0;i<plan.count;++i){const auto serial=plan.firstSerial+i;MemberRecord r;r.serial=serial;r.sessionFingerprint=mSession;r.origin=OnyonEmission{plan.root,serial,plan.cause,i};r.state.species=plan.root.species;members.emplace(serial,std::move(r));}
 std::map<SeedCause,std::uint32_t> rewards;rewards.emplace(plan.cause,plan.count);
 mMembers.merge(members);mRewards.merge(rewards);mNextSerial+=plan.count;e.clear();return true;
}
bool Lineage::nextPending(const Root& root,std::uint64_t& out,std::string& e)const{
 if(!rootValid(root))return fail(e,"pending source Onion root invalid");
 for(const auto& m:mMembers){const auto* emitted=std::get_if<OnyonEmission>(&m.second.origin);if(m.second.location==Location::Pending&&emitted&&emitted->root==root){out=m.first;e.clear();return true;}}
 return fail(e,"source Onion has no pending member");
}
bool Lineage::attach(std::uint64_t serial,const void* p,bool head,std::uint64_t& out,std::string& e){
 auto& bindings=head?mHeads:mBodies;
 if(!p||mHeads.count(p)||mBodies.count(p)||bindings.size()>=(head?liveHeadLimit:liveBodyLimit)||mNextHandle==std::numeric_limits<std::uint64_t>::max())return fail(e,"null/duplicate source pointer or physical binding capacity exhausted");
 bindings.emplace(p,Binding{serial,mNextHandle});out=mNextHandle++;e.clear();return true;
}
bool Lineage::bindPendingHead(std::uint64_t serial,const Root& root,const void* p,std::uint64_t& h,std::string& e){
 auto m=mMembers.find(serial);if(m==mMembers.end()||m->second.location!=Location::Pending||!rootValid(root))return fail(e,"source pending head selection invalid");
 const auto* emission=std::get_if<OnyonEmission>(&m->second.origin);if(!emission||!(emission->root==root))return fail(e,"pending source Onion incarnation mismatch");
 if(!attach(serial,p,true,h,e))return false;
 m->second.location=Location::Head;return true;
}
bool Lineage::storePending(std::uint64_t serial,const Root& root,std::string& e){
 auto m=mMembers.find(serial);if(m==mMembers.end()||m->second.location!=Location::Pending||!rootValid(root))return fail(e,"pending source store selection invalid");
 const auto* emission=std::get_if<OnyonEmission>(&m->second.origin);if(!emission||!(emission->root==root))return fail(e,"pending source store root mismatch");
 Root receiver=root; m->second.receiverRoot=std::move(receiver);m->second.hasReceiver=true;m->second.location=Location::Stored;e.clear();return true;
}
bool Lineage::adoptAuthored(const std::string& currentSession,const OriginalPikiBody& authored,std::uint8_t maturity,const void* body,std::uint64_t& serial,std::uint64_t& h,std::string& e){
 const auto& a=authored.origin;MemberBodyState state{authored.state.species,maturity,authored.state.wild,authored.state.wasWild};
 AuthoredKey k{a.catalogFingerprint,a.sourceKey,a.recordUid,a.attempt,a.activation};
 if(!hex(mSession)||currentSession!=mSession||!hex(a.catalogFingerprint)||!key(a.sourceKey)||!a.recordUid||!a.activation||!stateValid(state)||mMembers.size()>=memberLimit||mAuthored.count(k))return fail(e,"invalid or already adopted canonical authored source body");
 MemberRecord r;r.serial=mNextSerial;r.sessionFingerprint=mSession;r.origin=authored;r.state=state;r.location=Location::Body;
 auto added=mMembers.emplace(r.serial,std::move(r));
 try{
  auto origin=mAuthored.emplace(k,mNextSerial);
  try{if(!attach(mNextSerial,body,false,h,e)){mAuthored.erase(origin.first);mMembers.erase(added.first);return false;}}
  catch(...){mAuthored.erase(origin.first);throw;}
 }catch(...){mMembers.erase(added.first);throw;}
 serial=mNextSerial++;return true;
}
bool Lineage::headToBody(const void* head,std::uint64_t hh,const void* body,std::uint64_t& bh,std::string& e){
 auto p=mHeads.find(head);if(p==mHeads.end()||!hh||p->second.handle!=hh)return fail(e,"stale source head conversion");
 auto m=mMembers.find(p->second.serial);if(m==mMembers.end()||m->second.location!=Location::Head)return fail(e,"source head member unavailable");
 if(!attach(m->first,body,false,bh,e))return false;
 m->second.location=Location::Body;mHeads.erase(p);return true;
}
bool Lineage::depositBody(const void* body,std::uint64_t h,const Root& root,std::string& e){
 auto p=mBodies.find(body);if(p==mBodies.end()||!h||p->second.handle!=h)return fail(e,"stale source body deposit");
 auto m=mMembers.find(p->second.serial);if(m==mMembers.end()||m->second.location!=Location::Body||!rootValid(root)||root.species!=m->second.state.species)return fail(e,"source body deposit receiver unavailable or wrong color");
 Root receiver=root;m->second.receiverRoot=std::move(receiver);m->second.hasReceiver=true;m->second.location=Location::Stored;mBodies.erase(p);e.clear();return true;
}
StockResult Lineage::peekStored(std::uint8_t species,MemberRecord& out,std::string& e)const{
 if(!hex(mSession)||species>=3){e="source stock session/species invalid";return StockResult::Unavailable;}
 if(mUnknown[species]){e="inherited count-only source stock has no member provenance";return StockResult::Unavailable;}
 const MemberRecord* selected=nullptr;
 for(const auto& m:mMembers){const auto& r=m.second;if(r.location==Location::Stored&&r.state.species==species&&(!selected||r.state.maturity>selected->state.maturity))selected=&r;}
 if(!selected){e.clear();return StockResult::Empty;}out=*selected;e.clear();return StockResult::Present;
}
bool Lineage::withdrawStored(std::uint64_t serial,const Root& root,const void* born,std::uint64_t& h,std::string& e){
 if(!rootValid(root))return fail(e,"source stock withdrawal receiver invalid");
 MemberRecord selected;if(peekStored(root.species,selected,e)!=StockResult::Present)return false;
 if(selected.serial!=serial)return fail(e,"source stock withdrawal selection is stale");
 auto m=mMembers.find(serial);Root receiver=root;
 if(!attach(serial,born,false,h,e))return false;
 m->second.receiverRoot=std::move(receiver);m->second.hasReceiver=true;m->second.location=Location::Body;return true;
}
bool Lineage::storedCounts(std::uint8_t species,std::array<std::uint64_t,3>& out)const noexcept{
 if(!hex(mSession)||species>=3||mUnknown[species])return false;
 std::array<std::uint64_t,3> counts{};
 for(const auto& member:mMembers){const auto& r=member.second;
  if(r.location==Location::Stored&&r.state.species==species){if(r.state.maturity>=3)return false;++counts[r.state.maturity];}
 }
 out=counts;return true;
}
bool Lineage::updateBody(const void* body,std::uint64_t h,const MemberBodyState& state,std::string& e){
 auto p=mBodies.find(body);if(p==mBodies.end()||!h||p->second.handle!=h)return fail(e,"stale source body update");
 auto m=mMembers.find(p->second.serial);if(m==mMembers.end()||!stateValid(state)||state.species!=m->second.state.species||(m->second.state.wasWild&&!state.wasWild))return fail(e,"invalid source body color/maturity/wild history");
 m->second.state=state;e.clear();return true;
}
bool Lineage::retire(std::map<const void*,Binding>& bindings,const void* p,std::uint64_t h,std::string& e){
 auto b=bindings.find(p);
 if(b==bindings.end()){e.clear();return true;}
 if(!h||b->second.handle!=h)return fail(e,"stale source death/retirement");
 auto m=mMembers.find(b->second.serial);if(m==mMembers.end())return fail(e,"source retirement member unavailable");
 m->second.location=Location::Dead;bindings.erase(b);e.clear();return true;
}
bool Lineage::retireHead(const void* p,std::uint64_t h,std::string& e){return retire(mHeads,p,h,e);}
bool Lineage::retireBody(const void* p,std::uint64_t h,std::string& e){return retire(mBodies,p,h,e);}
QueryResult Lineage::query(const std::map<const void*,Binding>& bindings,const void* p,const std::string& currentSession,MemberRecord& out,std::uint64_t& h,std::string& e)const{
 auto b=bindings.find(p);if(b==bindings.end()){e.clear();return QueryResult::Missing;}
 auto m=mMembers.find(b->second.serial);if(currentSession!=mSession||!hex(mSession)||m==mMembers.end()){e="labelled source member/session unavailable";return QueryResult::Unavailable;}
 MemberRecord candidate=m->second;out=std::move(candidate);h=b->second.handle;e.clear();return QueryResult::Present;
}
QueryResult Lineage::queryHead(const void* p,const std::string& s,MemberRecord& r,std::uint64_t& h,std::string& e)const{return query(mHeads,p,s,r,h,e);}
QueryResult Lineage::queryBody(const void* p,const std::string& s,MemberRecord& r,std::uint64_t& h,std::string& e)const{return query(mBodies,p,s,r,h,e);}
bool Lineage::ownsBody(const void* p)const noexcept{return mBodies.find(p)!=mBodies.end();}
bool Lineage::ownsHead(const void* p)const noexcept{return mHeads.find(p)!=mHeads.end();}
bool Lineage::bodyHandle(const void* p,std::uint64_t& out)const noexcept{
 auto b=mBodies.find(p);if(b==mBodies.end())return false;out=b->second.handle;return true;
}
void Lineage::retireSceneBodies() noexcept{
 for(const auto& b:mBodies){auto m=mMembers.find(b.second.serial);if(m!=mMembers.end())m->second.location=Location::Dead;}
 mBodies.clear();
}
bool Lineage::markUnknownStock(std::uint8_t species,std::uint64_t count,std::string& e){
 if(!hex(mSession)||species>=3||!count||count>std::numeric_limits<std::uint64_t>::max()-mUnknown[species])return fail(e,"invalid/overflowed unknown source stock marker");
 mUnknown[species]+=count;e.clear();return true;
}
Report Lineage::report()const{Report r;r.sessionFingerprint=mSession;r.liveHeads=mHeads.size();r.liveBodies=mBodies.size();for(const auto& m:mMembers)r.members.push_back(m.second);for(unsigned i=0;i<3;++i)r.unknownStock[i]=mUnknown[i];return r;}
bool Lineage::courseUnload(std::string& e)const{
 if(!mHeads.empty()||!mBodies.empty())return fail(e,"source course still owns living physical member graph");
 return preflightCourseFinish(e);
}
bool Lineage::preflightCourseFinish(std::string& e)const{
 if(!mHeads.empty())return fail(e,"source course still owns living source HEAD graph before provider disposal");
 for(const auto& m:mMembers)if(m.second.location==Location::Pending)return fail(e,"source course still owns pending Onion reward members");
 e.clear();return true;
}
bool Lineage::newSession(const std::string& s,std::string& e){
 if(!hex(s))return fail(e,"new source lineage session fingerprint invalid");
 if(!courseUnload(e))return false;
 std::string candidate=s;mSession.swap(candidate);mMembers.clear();mRewards.clear();mAuthored.clear();mNextSerial=1;
 // Do not rewind RAM handles: old pointers/handles stay stale across sessions.
 for(auto& c:mUnknown)c=0;
 e.clear();return true;
}
}
