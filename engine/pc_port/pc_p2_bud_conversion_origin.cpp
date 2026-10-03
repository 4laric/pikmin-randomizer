#include "pc_p2_bud_conversion_origin.h"
#include "pc_p2_bud_live_floor.h"
#include <sstream>
#include <tuple>
#include <thread>
#include <limits>
namespace p2budorigin {
bool Creation::valid()const noexcept{return p2originalcheckpoint::digest(campaign)&&p2originalcheckpoint::digest(session)&&p2originalcheckpoint::digest(sourceSha)&&p2originalcheckpoint::digest(catalogSha)&&p2originalcheckpoint::digest(layoutSha)&&!cave.empty()&&!visit.empty()&&floor>0&&floor<=105&&epoch&&nativeSerial&&sessionRevision&&(phase==CreationPhase::Installing||phase==CreationPhase::Committed);}
bool Creation::operator==(const Creation& b)const noexcept{return campaign==b.campaign&&session==b.session&&cave==b.cave&&visit==b.visit&&sourceSha==b.sourceSha&&catalogSha==b.catalogSha&&layoutSha==b.layoutSha&&floor==b.floor&&epoch==b.epoch&&nativeSerial==b.nativeSerial&&sessionRevision==b.sessionRevision;}
namespace {
auto key(const FloorIdentity& f){return std::tie(f.campaign,f.session,f.cave,f.visit,f.sourceSha,f.catalogSha,f.layoutSha,f.instance,f.floor,f.row,f.ordinal,f.epoch,f.activation);}
bool token(const std::string& s){if(s.empty()||s.size()>1024)return false;for(unsigned char c:s)if(c<=32||c>=127)return false;return true;}
bool fail(std::string& e,const char* s){e=s;return false;}
Identity budKey(Identity id){id.emission=0;return id;}
bool recordValid(const Record& r){return valid(r.identity)&&valid(r.donor)&&r.donor.campaign==r.identity.floor.campaign&&r.species==3&&r.refunded==(r.donor.species==3);}
bool sameRecord(const Record& a,const Record& b){return a.identity==b.identity&&!(a.donor<b.donor)&&!(b.donor<a.donor)&&a.donor.species==b.donor.species&&a.species==b.species&&a.refunded==b.refunded;}
template<class Map,class Pointer>bool rootAlias(const Map& map,Pointer p)noexcept{for(const auto& entry:map)if(static_cast<const void*>(entry.first)==static_cast<const void*>(p))return true;return false;}
}
bool FloorIdentity::operator==(const FloorIdentity& b)const{return key(*this)==key(b);}
bool Identity::operator==(const Identity& b)const{return floor==b.floor&&bud==b.bud&&emission==b.emission;}
bool Identity::operator<(const Identity& b)const{if(key(floor)!=key(b.floor))return key(floor)<key(b.floor);if(!(bud==b.bud))return bud<b.bud;return emission<b.emission;}
bool Donor::operator<(const Donor& b)const{return std::tie(kind,campaign,logical)<std::tie(b.kind,b.campaign,b.logical);}
bool valid(const FloorIdentity& f)noexcept{return p2originalcheckpoint::digest(f.campaign)&&p2originalcheckpoint::digest(f.session)&&p2originalcheckpoint::digest(f.sourceSha)&&p2originalcheckpoint::digest(f.catalogSha)&&p2originalcheckpoint::digest(f.layoutSha)&&token(f.cave)&&token(f.visit)&&token(f.instance)&&f.floor>0&&f.floor<=105&&f.row<10000&&f.ordinal<10000&&f.epoch&&f.activation;}
bool valid(const Identity& i)noexcept{return valid(i.floor)&&p2originalcheckpoint::digest(i.bud.catalog)&&i.bud.generator&&i.bud.ordinal<65536&&i.bud.epoch&&i.bud.activation&&i.emission;}
bool valid(const Donor& d)noexcept{return unsigned(d.kind)>=1&&unsigned(d.kind)<=3&&p2originalcheckpoint::digest(d.campaign)&&token(d.logical)&&d.species<=4;}
bool encode(const Record& r,std::string& out,std::string& e){
 if(!recordValid(r))return fail(e,"invalid typed bud conversion record");
 const auto& f=r.identity.floor;const auto& b=r.identity.bud;std::ostringstream o;
 o<<"BUD_ORIGIN_1 "<<f.campaign<<' '<<f.session<<' '<<f.cave<<' '<<f.visit<<' '<<f.sourceSha<<' '<<f.catalogSha<<' '<<f.layoutSha<<' '<<f.instance<<' '<<f.floor<<' '<<f.row<<' '<<f.ordinal<<' '<<f.epoch<<' '<<f.activation<<' '<<b.catalog<<' '<<b.generator<<' '<<b.ordinal<<' '<<b.epoch<<' '<<b.activation<<' '<<r.identity.emission<<' '<<unsigned(r.donor.kind)<<' '<<r.donor.campaign<<' '<<r.donor.logical<<' '<<r.donor.species<<' '<<r.species<<' '<<unsigned(r.refunded)<<'\n';
 auto next=o.str();if(next.size()>8192)return fail(e,"bud origin byte bound");out=std::move(next);e.clear();return true;
}
bool decode(const std::string& bytes,Record& out,std::string& e){
 if(bytes.empty()||bytes.size()>8192)return fail(e,"bud origin byte bound");
 std::istringstream in(bytes);Record r;auto& f=r.identity.floor;auto& b=r.identity.bud;std::string tag;unsigned kind=0,refund=2;
 if(!(in>>tag>>f.campaign>>f.session>>f.cave>>f.visit>>f.sourceSha>>f.catalogSha>>f.layoutSha>>f.instance>>f.floor>>f.row>>f.ordinal>>f.epoch>>f.activation>>b.catalog>>b.generator>>b.ordinal>>b.epoch>>b.activation>>r.identity.emission>>kind>>r.donor.campaign>>r.donor.logical>>r.donor.species>>r.species>>refund)||tag!="BUD_ORIGIN_1"||kind<1||kind>3||refund>1||(in>>tag))return fail(e,"bud origin framing");
 r.donor.kind=DonorKind(kind);r.refunded=refund!=0;std::string canonical;if(!encode(r,canonical,e)||canonical!=bytes)return fail(e,"bud origin noncanonical bytes");
 out=std::move(r);e.clear();return true;
}
namespace {
bool snapshotValid(const Snapshot& snap,std::string& e){
 if(!p2originalcheckpoint::digest(snap.campaign)||!p2originalcheckpoint::digest(snap.session)||snap.emissions.size()>20000)return fail(e,"bud ledger framing");
 std::set<Donor> donors;std::map<Identity,unsigned> last;Identity previous;bool havePrevious=false;unsigned live=0;
 for(const auto& entry:snap.emissions){const auto& id=entry.record.identity;unsigned life=unsigned(entry.lifecycle);
  if(!recordValid(entry.record)||id.floor.campaign!=snap.campaign||id.floor.session!=snap.session||life<1||life>3||(havePrevious&&!(previous<id))||!donors.insert(entry.record.donor).second)return fail(e,"bud ledger conflicting identity");
  unsigned& n=last[budKey(id)];if(id.emission!=n+1)return fail(e,"bud ledger emission gap");n=id.emission;
  if(entry.lifecycle!=Lifecycle::Retired&&++live>100)return fail(e,"bud live member capacity");
  previous=id;havePrevious=true;
 }return true;
}
}
bool encodeSnapshot(const Snapshot& snap,std::string& out,std::string& e){
 if(!snapshotValid(snap,e))return false;
 std::ostringstream o;o<<"BUD_LEDGER_1 "<<snap.campaign<<' '<<snap.session<<' '<<snap.emissions.size()<<'\n';
 for(const auto& entry:snap.emissions){std::string record;if(!encode(entry.record,record,e))return false;o<<unsigned(entry.lifecycle)<<'\n'<<record;}
 auto next=o.str();if(next.size()>1024*1024)return fail(e,"bud ledger byte bound");out=std::move(next);e.clear();return true;
}
bool decodeSnapshot(const std::string& bytes,Snapshot& out,std::string& e){
 if(bytes.empty()||bytes.size()>1024*1024)return fail(e,"bud ledger byte bound");
 std::istringstream in(bytes);Snapshot snap;std::string line,tag;unsigned count=0;
 if(!std::getline(in,line))return fail(e,"bud ledger header");
 std::istringstream header(line);
 if(!(header>>tag>>snap.campaign>>snap.session>>count)||tag!="BUD_LEDGER_1"||count>20000||(header>>tag))return fail(e,"bud ledger header");
 for(unsigned i=0;i<count;++i){Entry entry;unsigned life=0;if(!std::getline(in,line))return fail(e,"bud ledger lifecycle");std::istringstream stateLine(line);if(!(stateLine>>life)||life<1||life>3||(stateLine>>tag)||!std::getline(in,line)||!decode(line+'\n',entry.record,e))return fail(e,"bud ledger entry");entry.lifecycle=Lifecycle(life);snap.emissions.push_back(std::move(entry));}
 if(std::getline(in,line))return fail(e,"bud ledger trailing bytes");
 std::string canonical;
 if(!encodeSnapshot(snap,canonical,e)||canonical!=bytes)return fail(e,"bud ledger noncanonical bytes");
 out=std::move(snap);e.clear();return true;
}
struct Registry::State {
 std::string campaign,session;
 const Authority* authority=nullptr;p2originalcheckpoint::Proof proof;std::thread::id owner;
 Creation creation;bool live=false;
 bool escrow=false;
 std::uint64_t revision=0;
 std::map<Identity,Entry> history;std::map<Identity,unsigned> last;
 std::set<Donor> consumed;
 std::map<const PikiHeadItem*,Identity> heads;std::map<const Piki*,Identity> bodies;
 bool current()const noexcept{if(!authority||owner!=std::this_thread::get_id())return false;if(live){const auto* actual=authority->liveCreation();return actual&&creation==*actual&&actual->phase==CreationPhase::Committed;}return proof.valid()&&authority->stillCurrent(proof);}
 bool emitting()const noexcept{if(!current())return false;const auto* actual=authority->liveCreation();return !actual||actual->gameActive;}
};
struct PendingEmission::Impl {std::shared_ptr<Registry::State> old,next;std::uint64_t revision=0;Identity identity;bool body=false;};
struct Carry::Impl {std::shared_ptr<Registry::State> source;Snapshot snapshot;Creation creation;std::set<Identity> carried;};
Carry::Carry()=default;Carry::~Carry()=default;Carry::Carry(Carry&&)noexcept=default;Carry&Carry::operator=(Carry&&)noexcept=default;
bool Carry::ready()const noexcept{return bool(impl);}
PendingEmission::PendingEmission()=default;PendingEmission::~PendingEmission()=default;
PendingEmission::PendingEmission(PendingEmission&&)noexcept=default;PendingEmission&PendingEmission::operator=(PendingEmission&&)noexcept=default;
bool PendingEmission::ready()const noexcept{return bool(impl);}
unsigned PendingEmission::ordinal()const noexcept{return impl?impl->identity.emission:0;}
Registry::Registry():state(std::make_shared<State>()){}Registry::~Registry()=default;
bool Registry::bind(const Authority& a,const p2originalcheckpoint::Proof& p,std::string& e){
 if(state->escrow||!p.valid()||!state->heads.empty()||!state->bodies.empty())return fail(e,"bud registry bind requires selected proof and empty native scene");
 p2originalcheckpoint::Proof selected;if(!a.selected(selected,e)||!(selected==p)||!a.stillCurrent(p))return fail(e,"bud selected card changed");
 std::string campaign,session;if(!a.context(campaign,session,e)||!p2originalcheckpoint::digest(campaign)||!p2originalcheckpoint::digest(session))return fail(e,"bud selected source context refused");
 if(!state->history.empty()&&(state->campaign!=campaign||state->session!=session))return fail(e,"bud history requires separate campaign registry");
 auto next=std::make_shared<State>(*state);next->campaign=campaign;next->session=session;next->authority=&a;next->proof=p;next->live=false;next->owner=std::this_thread::get_id();++next->revision;state.swap(next);e.clear();return true;
}
bool Registry::bindLive(const Authority& a,std::string& e){
 if(state->escrow||!state->heads.empty()||!state->bodies.empty())return fail(e,"live bud bind requires empty native scene");
 Creation created;std::string campaign,session;
 if(!a.creation(created,e)||!created.valid()||!a.context(campaign,session,e)||campaign!=created.campaign||session!=created.session)return fail(e,"actual native session/floor creation refused");
 if(!state->history.empty()&&(state->campaign!=campaign||state->session!=session))return fail(e,"bud history requires separate campaign registry");
 const auto* actual=a.liveCreation();if(!actual||!(*actual==created))return fail(e,"native floor changed before live binding");
 auto next=std::make_shared<State>(*state);next->campaign=campaign;next->session=session;next->authority=&a;next->proof={};next->creation=std::move(created);next->live=true;next->owner=std::this_thread::get_id();++next->revision;
 actual=a.liveCreation();if(!actual||!(*actual==next->creation))return fail(e,"live native session/floor changed during binding");
 state.swap(next);e.clear();return true;
}
bool Registry::detachCarry(const std::vector<BodyBinding>& bodies,Carry& out,std::string& e){
 if(out.ready()||state->escrow||!state->current())return fail(e,"bud carried transition unavailable");
 const auto* creation=state->authority->liveCreation();if(!creation||!creation->valid()||creation->phase!=CreationPhase::Committed)return fail(e,"actual committed native source floor missing");
 Snapshot snap;if(!snapshot(snap,e)||!state->authority->carried(snap,bodies,e))return fail(e,"actual complete native carry disposition refused");
 auto ticket=std::make_unique<Carry::Impl>();ticket->creation=*creation;std::set<const Piki*> pointers;
 for(const auto& body:bodies){auto found=state->bodies.find(body.body);if(!body.body||found==state->bodies.end()||!(found->second==body.identity)||!pointers.insert(body.body).second||!ticket->carried.insert(body.identity).second)return fail(e,"carried body is not an exact unique live source member");}
 ticket->snapshot=snap;
 for(auto& entry:ticket->snapshot.emissions)if(!ticket->carried.count(entry.record.identity))entry.lifecycle=Lifecycle::Retired;
 auto next=std::make_shared<State>(*state);
 for(auto& entry:next->history)if(!ticket->carried.count(entry.first))entry.second.lifecycle=Lifecycle::Retired;
 next->heads.clear();next->bodies.clear();next->authority=nullptr;next->escrow=true;++next->revision;
 if(!state->current())return fail(e,"native source changed during carry reservation");
 ticket->source=next;state.swap(next);out.impl=std::move(ticket);e.clear();return true;
}
bool Registry::receiveCarry(const Authority& a,Carry& ticket,const std::vector<BodyBinding>& bodies,std::string& e){
 if(!ticket.impl||!ticket.impl->source->escrow||!state->history.empty()||!state->heads.empty()||!state->bodies.empty())return fail(e,"carry requires unclaimed complete ticket and empty destination");
 Creation created;std::string campaign,session;
 if(!a.creation(created,e)||!created.valid()||created.nativeSerial==ticket.impl->creation.nativeSerial||!a.context(campaign,session,e)||campaign!=ticket.impl->snapshot.campaign||session!=ticket.impl->snapshot.session||created.campaign!=campaign||created.session!=session||!a.receive(ticket.impl->snapshot,bodies,e))return fail(e,"actual new native destination carry authority refused");
 const auto* actual=a.liveCreation();if(!actual||!(*actual==created))return fail(e,"native destination changed");
 auto next=std::make_shared<State>();next->campaign=campaign;next->session=session;next->creation=created;next->live=true;next->authority=&a;next->owner=std::this_thread::get_id();next->revision=state->revision+1;
 for(const auto& entry:ticket.impl->snapshot.emissions){next->history.emplace(entry.record.identity,entry);next->consumed.insert(entry.record.donor);next->last[budKey(entry.record.identity)]=entry.record.identity.emission;}
 std::set<Identity> seen;
 for(const auto& body:bodies){if(!body.body||!ticket.impl->carried.count(body.identity)||!seen.insert(body.identity).second||!next->bodies.emplace(body.body,body.identity).second)return fail(e,"carry destination mapping is missing/duplicate/foreign");}
 if(seen!=ticket.impl->carried)return fail(e,"carry destination requires every live carried body");
 actual=a.liveCreation();if(!actual||!(*actual==created))return fail(e,"destination changed before carry adoption");
 // Publication is allocation-free after ALL destination validation/preparation.
 for(auto& entry:ticket.impl->source->history)entry.second.lifecycle=Lifecycle::Retired;
 ticket.impl->source->escrow=false;state.swap(next);ticket.impl.reset();e.clear();return true;
}
bool Registry::prepare(const Pom* pom,unsigned tokenValue,const p2original::InstanceIdentity& bud,const Piki* donor,unsigned species,bool refund,PendingEmission& out,std::string& e){
 if(out.ready()||!pom||!tokenValue||!donor||species!=3||!state->emitting()||state->history.size()>=20000)return fail(e,"bud output preparation unavailable");
 FloorIdentity floor;Donor d;if(!state->authority->bud(pom,tokenValue,bud,floor,e)||!valid(floor)||floor.campaign!=state->campaign||floor.session!=state->session||!state->authority->donor(donor,d,e)||!valid(d)||d.campaign!=floor.campaign||refund!=(d.species==3)||state->consumed.count(d))return fail(e,"bud source6 floor or live donor authority refused");
 Identity id{floor,bud,1};auto keyId=budKey(id);auto old=state->last.find(keyId);if(old!=state->last.end()){if(old->second==std::numeric_limits<unsigned>::max())return fail(e,"bud emission ordinal exhausted");id.emission=old->second+1;}
 if(!valid(id)||state->history.count(id))return fail(e,"bud emission identity reused");
 auto pending=std::make_unique<PendingEmission::Impl>();pending->old=state;pending->next=std::make_shared<State>(*state);pending->revision=state->revision;pending->identity=id;
 // Native kill will retire an existing converted donor before the head event.
 auto converted=state->bodies.find(donor);if(converted!=state->bodies.end()){
  pending->next->bodies.erase(donor);pending->next->history.at(converted->second).lifecycle=Lifecycle::Retired;++pending->revision;
 }
 if(state->heads.size()+state->bodies.size()-(converted!=state->bodies.end()?1:0)>=100)return fail(e,"bud live member capacity");
 pending->next->history.emplace(id,Entry{Record{id,d,species,refund},Lifecycle::Head});pending->next->consumed.insert(d);pending->next->last[keyId]=id.emission;pending->next->heads.emplace(nullptr,id);
 if(!state->emitting())return fail(e,"bud proof changed during output reservation");
 out.impl=std::move(pending);e.clear();return true;
}
bool Registry::adopt(PendingEmission&& p,PikiHeadItem* head,unsigned ordinal,unsigned actualSpecies,bool actualRefund,const char*& reason)noexcept{
 reason=nullptr;
 if(!p.impl||p.impl->body||!head||p.impl->old!=state||state->revision!=p.impl->revision||!state->emitting()||ordinal!=p.impl->identity.emission||actualSpecies!=3||actualRefund!=p.impl->next->history.find(p.impl->identity)->second.record.refunded||state->heads.count(head)||rootAlias(state->bodies,head)){reason="bud emitted head reservation/authority mismatch";return false;}
 auto node=p.impl->next->heads.extract(nullptr);if(node.empty()){reason="missing reserved head node";return false;}node.key()=head;p.impl->next->heads.insert(std::move(node));++p.impl->next->revision;state.swap(p.impl->next);p.impl.reset();return true;
}
bool Registry::head(const PikiHeadItem* p,Record& out)const{auto i=state->heads.find(p);if(i==state->heads.end())return false;Record next=state->history.at(i->second).record;out=std::move(next);return true;}
bool Registry::body(const Piki* p,Record& out)const{auto i=state->bodies.find(p);if(i==state->bodies.end())return false;Record next=state->history.at(i->second).record;out=std::move(next);return true;}
bool Registry::admitted(const Record& record,std::string& e)const{
 auto found=state->history.find(record.identity);
 if(found==state->history.end()||found->second.lifecycle==Lifecycle::Retired||!sameRecord(record,found->second.record))return fail(e,"bud record is not an exact live registry member");
 return state->current()&&state->authority->record(record,e)&&state->current();
}
bool Registry::prepareTransfer(PikiHeadItem* head,unsigned species,PendingEmission& out,std::string& e){
 auto found=state->heads.find(head);if(out.ready()||!head||found==state->heads.end()||!state->current()||state->history.at(found->second).record.species!=species)return fail(e,"typed head transfer refused");
 if(!admitted(state->history.at(found->second).record,e))return false;
 auto p=std::make_unique<PendingEmission::Impl>();p->old=state;p->next=std::make_shared<State>(*state);p->revision=state->revision;p->identity=found->second;p->body=true;
 p->next->heads.erase(head);p->next->bodies.emplace(nullptr,p->identity);p->next->history.at(p->identity).lifecycle=Lifecycle::Body;
 if(!state->current())return fail(e,"bud transfer selected card changed");
 out.impl=std::move(p);e.clear();return true;
}
bool Registry::adoptBody(PendingEmission&& p,Piki* body,const char*& reason)noexcept{
 reason=nullptr;
 if(!p.impl||!p.impl->body||!body||p.impl->old!=state||state->revision!=p.impl->revision||!state->current()||state->bodies.count(body)||rootAlias(state->heads,body)){reason="typed sprout/body reservation mismatch";return false;}
 auto node=p.impl->next->bodies.extract(nullptr);if(node.empty()){reason="missing reserved body node";return false;}node.key()=body;p.impl->next->bodies.insert(std::move(node));++p.impl->next->revision;state.swap(p.impl->next);p.impl.reset();return true;
}
void Registry::forget(const PikiHeadItem* p)noexcept{auto i=state->heads.find(p);if(i==state->heads.end())return;state->history.find(i->second)->second.lifecycle=Lifecycle::Retired;state->heads.erase(i);++state->revision;}
void Registry::forget(const Piki* p)noexcept{auto i=state->bodies.find(p);if(i==state->bodies.end())return;state->history.find(i->second)->second.lifecycle=Lifecycle::Retired;state->bodies.erase(i);++state->revision;}
void Registry::sceneExit()noexcept{for(const auto& h:state->heads)state->history.find(h.second)->second.lifecycle=Lifecycle::Retired;for(const auto& b:state->bodies)state->history.find(b.second)->second.lifecycle=Lifecycle::Retired;state->heads.clear();state->bodies.clear();state->authority=nullptr;++state->revision;}
bool Registry::snapshot(Snapshot& out,std::string& e)const{
 if(!state->current())return fail(e,"bud snapshot requires owned selected floor");
 Snapshot next;next.campaign=state->campaign;next.session=state->session;
 for(const auto& h:state->history){if(next.campaign.empty()){next.campaign=h.first.floor.campaign;next.session=h.first.floor.session;}if(next.campaign!=h.first.floor.campaign||next.session!=h.first.floor.session)return fail(e,"mixed bud history campaign/session");if(h.second.lifecycle!=Lifecycle::Retired&&!state->authority->record(h.second.record,e))return false;next.emissions.push_back(h.second);}
 if(!state->current())return fail(e,"bud snapshot selected card changed");
 out=std::move(next);e.clear();return true;
}
bool Registry::adoptSelected(const Authority& authority,const Snapshot& expected,const p2originalcheckpoint::Proof& proof,std::string& e){
 if(state->owner!=std::this_thread::get_id()||!proof.valid())return fail(e,"bud selected SAVE adoption owner");
 Snapshot live;live.campaign=state->campaign;live.session=state->session;
 for(const auto& entry:state->history)live.emissions.push_back(entry.second);
 std::string actualBytes,savedBytes;if(!encodeSnapshot(live,actualBytes,e)||!encodeSnapshot(expected,savedBytes,e)||actualBytes!=savedBytes)return fail(e,"bud selected SAVE changed live graph");
 p2originalcheckpoint::Proof current;std::string campaign,session;
 if(!authority.selected(current,e)||!(current==proof)||!authority.context(campaign,session,e)||campaign!=live.campaign||session!=live.session||!authority.saved(expected,proof,e)||!authority.stillCurrent(proof))return fail(e,"bud actual selected SAVE proof refused");
 auto next=std::make_shared<State>(*state);next->authority=&authority;next->proof=proof;next->live=false;++next->revision;
 if(!authority.stillCurrent(proof))return fail(e,"bud selected SAVE changed before adoption");
 state.swap(next);e.clear();return true;
}
bool Registry::restore(const Authority& authority,const Snapshot& snap,const p2originalcheckpoint::Proof& proof,const std::vector<HeadBinding>& heads,const std::vector<BodyBinding>& bodies,std::string& e){
 if(!state->history.empty()||!state->heads.empty()||!state->bodies.empty()||!p2originalcheckpoint::digest(snap.campaign)||!p2originalcheckpoint::digest(snap.session)||snap.emissions.size()>20000||!proof.valid())return fail(e,"bud provisional restore framing");
 if(!snapshotValid(snap,e))return false;
 p2originalcheckpoint::Proof selected;if(!authority.selected(selected,e)||!(selected==proof)||!authority.stillCurrent(proof)||!authority.saved(snap,proof,e))return fail(e,"bud selected family proof refused");
 std::string campaign,session;if(!authority.context(campaign,session,e)||campaign!=snap.campaign||session!=snap.session)return fail(e,"bud saved selected context mismatch");
 auto next=std::make_shared<State>();next->campaign=campaign;next->session=session;next->authority=&authority;next->proof=proof;next->owner=std::this_thread::get_id();next->revision=state->revision+1;
 Identity previous;bool havePrevious=false;
 for(const auto& entry:snap.emissions){const auto& id=entry.record.identity;unsigned life=unsigned(entry.lifecycle);if(!recordValid(entry.record)||id.floor.campaign!=snap.campaign||id.floor.session!=snap.session||life<1||life>3||(havePrevious&&!(previous<id))||!next->consumed.insert(entry.record.donor).second)return fail(e,"bud saved identity/history conflict");
  auto keyId=budKey(id);unsigned& last=next->last[keyId];if(id.emission!=last+1)return fail(e,"bud saved emission history gap");last=id.emission;next->history.emplace(id,entry);previous=id;havePrevious=true;
 }
 std::set<Identity> assigned;
 for(const auto& h:heads){auto entry=next->history.find(h.identity);if(!h.head||entry==next->history.end()||entry->second.lifecycle!=Lifecycle::Head||!assigned.insert(h.identity).second||!next->heads.emplace(h.head,h.identity).second)return fail(e,"bud saved head binding mismatch");}
 for(const auto& b:bodies){auto entry=next->history.find(b.identity);if(!b.body||rootAlias(next->heads,b.body)||entry==next->history.end()||entry->second.lifecycle!=Lifecycle::Body||!assigned.insert(b.identity).second||!next->bodies.emplace(b.body,b.identity).second)return fail(e,"bud saved body binding mismatch");}
 for(const auto& entry:next->history)if(entry.second.lifecycle!=Lifecycle::Retired&&!assigned.count(entry.first))return fail(e,"bud live saved member missing");
 if(!authority.stillCurrent(proof))return fail(e,"bud selected proof changed before registry publication");
 state.swap(next);e.clear();return true;
}
void Registry::swap(Registry& b)noexcept{state.swap(b.state);}
Registry& registry(){static Registry value;return value;}
}
