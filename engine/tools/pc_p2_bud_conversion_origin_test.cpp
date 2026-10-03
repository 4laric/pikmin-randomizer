#include "pc_p2_bud_conversion_origin.h"
#include "pc_p2_bud_conversion_producer.h"
#include "pc_p2_bud_live_floor.h"
#include "pc_p2_bud_native_live.h"
#include "pc_p2_source_body.h"
#include "pc_p2_original_piki_recruit.h"
#include "pc_p2_original_progress.h"
#include "pc_p2_original_source_uid.h"
#include <cstdio>
#include <cstdlib>
#include <new>
// Opaque pointers are pure-control identities, never dereferenced/native actors.
class Pom {}; class Piki {}; class PikiHeadItem {};
bool pc_p2_cave_campaign_party_associate_birth(Piki*,const char*,std::uint32_t,std::uint32_t,std::uint64_t,const char*){return true;}
bool pc_p2_cave_campaign_survivor_permit(const std::string&,std::uint32_t,std::uint32_t,std::uint64_t,const std::string&,std::uint64_t*,std::uint8_t[32]){return false;}
bool pc_p2_cave_campaign_survivor_body(const std::string&,std::uint32_t,std::uint32_t,std::uint64_t,const std::string&,OriginalPikiBodyState&,std::uint64_t*,std::uint8_t[32]){return false;}
// Explicit mock native session producer for wrapper sequencing only.
static bool nativeSelected=true,inputValid=true;static std::uint64_t nativeRevision=12;
static std::string nativeCampaign(64,'a'),nativeSession(64,'b');
bool pc_randomizer_original_session(){return nativeSelected;}
std::string pc_randomizer_original_campaign(){return nativeCampaign;}
std::string pc_randomizer_session_fingerprint(){return nativeSession;}
bool pc_randomizer_original_input(const std::string& role,std::string& out,std::string&){if(role!="p2-original/calendar.p2sc"||!inputValid)return false;out="mock immutable selected input";return true;}
std::uint64_t pc_randomizer_original_selection_revision()noexcept{return nativeRevision;}
static bool denyAllocation=false;
void* operator new(std::size_t n){if(denyAllocation)throw std::bad_alloc();if(void* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void operator delete(void* p)noexcept{std::free(p);}
void operator delete(void* p,std::size_t)noexcept{std::free(p);}
using namespace p2budorigin;
static int checks=0;
static void check(bool ok,const char* what){++checks;if(!ok){std::fprintf(stderr,"FAIL %d: %s\n",checks,what);std::exit(1);}}
static std::string hash(char c){return std::string(64,c);}
static unsigned headColour(const PikiHeadItem*)noexcept{return 3;}
static unsigned failures=0;
static void fatal(const char*)noexcept{++failures;}
struct MockAuthority final:Authority {
 p2originalcheckpoint::Proof proof;bool current=true,allow=true;mutable unsigned recordReads=0;unsigned donorSpecies=1;std::string donorKey="party:1";Creation live;bool liveActive=false;
 MockAuthority(){proof.generation=1;proof.sha[0]=42;}
 bool selected(p2originalcheckpoint::Proof& out,std::string&)const override{out=proof;return current;}
 bool context(std::string& c,std::string& s,std::string&)const override{c=hash('a');s=hash('b');return allow;}
 bool bud(const Pom*,unsigned,const p2original::InstanceIdentity&,FloorIdentity& f,std::string&)const override{f={hash('a'),hash('b'),"forest_1","visit:1",hash('c'),hash('d'),hash('e'),"bud:1",1,2,0,1,7};return allow;}
 bool donor(const Piki*,Donor& d,std::string&)const override{d={DonorKind::Party,hash('a'),donorKey,donorSpecies};return allow;}
 bool record(const Record&,std::string&)const override{++recordReads;return allow;}
 bool stillCurrent(const p2originalcheckpoint::Proof& p)const noexcept override{return current&&p==proof;}
 bool saved(const Snapshot&,const p2originalcheckpoint::Proof& p,std::string&)const override{return allow&&p==proof;}
 bool creation(Creation& out,std::string&)const override{if(!liveActive)return false;out=live;return true;}
 const Creation* liveCreation()const noexcept override{return liveActive?&live:nullptr;}
 bool carried(const Snapshot&,const std::vector<BodyBinding>&,std::string&)const override{return allow;}
 bool receive(const Snapshot&,const std::vector<BodyBinding>&,std::string&)const override{return allow;}
};
struct MockFloor final:LiveFloorReader,NativeDonorReader {
 MockAuthority& a;explicit MockFloor(MockAuthority& owner):a(owner){}
 const Creation* current()const noexcept override{return a.liveCreation();}
 bool expectedBud(const Pom* p,unsigned t,const p2original::InstanceIdentity& i,FloorIdentity& f,std::string& e)const override{return a.bud(p,t,i,f,e);}
 bool emitted(const Record& r,std::string& e)const override{return a.record(r,e);}
 bool carried(const Snapshot& s,const std::vector<BodyBinding>& b,std::string& e)const override{return a.carried(s,b,e);}
 bool receive(const Snapshot& s,const std::vector<BodyBinding>& b,std::string& e)const override{return a.receive(s,b,e);}
 bool query(const Piki* p,Donor& d,std::string& e)const override{return a.donor(p,d,e);}
};
struct MockOnyon final:PcP2SourceOnyonReader {
 Piki* actor=nullptr;std::uint64_t serial=7;bool ready=true,permit=true;unsigned forgets=0,exits=0;
 bool owned(const Piki* p)const noexcept override{return actor==p&&p;}
 bool lifetime(const Piki*,std::uint64_t& out)const noexcept override{if(!serial)return false;out=serial;return true;}
 bool query(const Piki*,std::uint64_t n,PcP2SourceOnyonRoot& out,OriginalPikiBodyState& state)const override{if(!ready||n!=serial)return false;out={hash('a'),hash('b'),hash('c'),"onyon:actual:1",0,1,11};state={1,false,false};return true;}
 bool admitted(const Piki* p,std::uint64_t n,const PcP2SourceOnyonRoot& r,const std::string& campaign,std::string&)const override{return permit&&p==actor&&n==serial&&r.campaign==campaign;}
 bool recruited(Piki* p,std::uint64_t n)override{return p==actor&&n==serial&&ready;}
 void forget(Piki* p)noexcept override{++forgets;if(p==actor)actor=nullptr;}
 void sceneExit()noexcept override{++exits;actor=nullptr;}
};
int main(){
 MockAuthority a;Registry r;std::string e;Pom pom;Piki donor,body;PikiHeadItem head,head2;
 p2original::InstanceIdentity bud{hash('f'),19,0,1,9};
 check(r.bind(a,a.proof,e),"bind explicit mock selected proof (not native acceptance)");
 Snapshot empty;check(r.snapshot(empty,e)&&empty.emissions.empty(),"empty bound snapshot has context");
 std::string emptyBytes;check(encodeSnapshot(empty,emptyBytes,e),"empty family canonical framing");
 PendingEmission p;check(r.prepare(&pom,1,bud,&donor,3,false,p,e)&&p.ordinal()==1,"reserve first head before donor consumption");
 Record untouched;check(!r.head(&head,untouched),"reservation does not publish head");
 Snapshot before;check(r.snapshot(before,e)&&before.emissions.empty(),"reservation has no durable donor tombstone");
 const char* reason=nullptr;denyAllocation=true;bool adopted=r.adopt(std::move(p),&head,1,3,false,reason);denyAllocation=false;
 check(adopted&&!reason,"head callback adoption allocates nothing");
 Record first;check(r.head(&head,first)&&first.identity.emission==1,"physical head has typed identity");
 auto forged=first;forged.donor.logical="party:forged";check(!r.admitted(forged,e),"valid but foreign donor payload is not a live registry record");
 std::string bytes;check(encode(first,bytes,e),"record codec");Record decoded;check(decode(bytes,decoded,e)&&decoded.identity==first.identity,"record roundtrip");
 auto sentinel=decoded;check(!decode(bytes+"x",decoded,e)&&decoded.identity==sentinel.identity,"trailing bytes leave output unchanged");
 check(!decode(bytes.substr(0,bytes.size()-1),decoded,e),"missing canonical newline refused");
 Record bad=first;bad.species=1;check(!encode(bad,bytes,e),"source6 cannot silently become RGB");
 bad=first;bad.refunded=true;check(!encode(bad,bytes,e),"refund must agree actual donor colour");
 bad=first;bad.donor.kind=DonorKind(4);check(!encode(bad,bytes,e),"unknown donor kind refused");
 bad=first;bad.identity.floor.activation=0;check(!encode(bad,bytes,e),"zero floor activation refused");
 bad=first;bad.identity.bud.generator=0;check(!encode(bad,bytes,e),"actual bud UID required");
 PendingEmission replay;check(!r.prepare(&pom,1,bud,&donor,3,false,replay,e),"consumed canonical donor cannot replay");
 PendingEmission transfer;check(!r.prepareTransfer(&head,1,transfer,e),"wrong physical colour cannot pluck");
 check(r.prepareTransfer(&head,3,transfer,e),"typed head transfer preallocates");
 denyAllocation=true;bool bound=r.adoptBody(std::move(transfer),&body,reason);denyAllocation=false;
 check(bound&&!reason,"body adoption allocates nothing");Record savedBody;check(!r.head(&head,savedBody)&&r.body(&body,savedBody)&&savedBody.identity==first.identity,"Head-to-pluck Body preserves full identity");
 r.forget(&head);check(r.body(&body,savedBody),"old head kill cannot retire transferred body");
 Snapshot live;auto reads=a.recordReads;check(r.snapshot(live,e)&&a.recordReads>reads,"snapshot rechecks each live selected family record");
 std::string ledger;check(encodeSnapshot(live,ledger,e),"body ledger codec");Snapshot roundtrip;check(decodeSnapshot(ledger,roundtrip,e)&&roundtrip.emissions[0].lifecycle==Lifecycle::Body,"body lifecycle roundtrip");
 auto gap=live;gap.emissions[0].record.identity.emission=2;check(!encodeSnapshot(gap,bytes,e),"emission gaps refused");
 auto duplicate=live;duplicate.emissions.push_back(duplicate.emissions[0]);check(!encodeSnapshot(duplicate,bytes,e),"duplicate identity/donor refused");
 a.allow=false;Snapshot unchanged=live;check(!r.snapshot(unchanged,e)&&unchanged.emissions.size()==1,"refused family leaves snapshot unchanged");a.allow=true;
 a.current=false;check(r.body(&body,savedBody),"expired authority retains typed label");check(!r.admitted(savedBody,e),"expired label cannot fall back to ordinary admission");a.current=true;
 PendingEmission refund;a.donorSpecies=3;a.donorKey="party:2";check(r.prepare(&pom,1,bud,&donor,3,true,refund,e)&&refund.ordinal()==2,"same-colour refund reserves real second emission");
 check(!r.adopt(std::move(refund),&head2,1,3,true,reason)&&refund.ready(),"wrong core ordinal preserves reservation");
 check(r.adopt(std::move(refund),&head2,2,3,true,reason)&&r.head(&head2,decoded)&&decoded.refunded,"refunded conversion still emits actual head");
 check(r.snapshot(live,e)&&live.emissions.size()==2,"refunded output is in durable history");
 a.proof.generation=2;a.proof.sha[0]=43;check(!r.snapshot(unchanged,e),"old proof invalid after SAVE");
 check(r.adoptSelected(a,live,a.proof,e)&&r.snapshot(unchanged,e),"real-owner selected family proof refresh retains live graph");
 auto changed=live;changed.emissions[0].lifecycle=Lifecycle::Retired;check(!r.adoptSelected(a,changed,a.proof,e),"SAVE refresh rejects changed graph");
 Registry restored;check(!restored.restore(a,live,a.proof,{},{{first.identity,&body}},e),"restore requires every saved head");
 check(!restored.restore(a,live,a.proof,{{live.emissions[1].record.identity,&head2}},{{first.identity,reinterpret_cast<Piki*>(&head2)}},e),"same physical root cannot be both head and body");
 check(restored.restore(a,live,a.proof,{{decoded.identity,&head2}},{{first.identity,&body}},e),"complete provisional bindings restore atomically");
 check(restored.body(&body,savedBody)&&restored.head(&head2,decoded),"fresh mapping preserves source identity");
 check(!restored.restore(a,live,a.proof,{{decoded.identity,&head2}},{{first.identity,&body}},e),"cannot restore over live registry");
 restored.sceneExit();check(!restored.body(&body,savedBody)&&!restored.head(&head2,decoded),"scene exit removes stale native pointers");
 check(restored.bind(a,a.proof,e),"same campaign scene may rebind proof");
 PendingEmission oldDonor;check(!restored.prepare(&pom,1,bud,&donor,3,true,oldDonor,e),"scene exit preserves donor tombstone");
 Registry older;check(older.restore(a,live,a.proof,{{live.emissions[1].record.identity,&head2}},{{first.identity,&body}},e),"authenticated selected older graph can restore in new provisional world");
 // Two pre-consumption reservations cannot overwrite another committed output.
 Registry race;check(race.bind(a,a.proof,e),"race test owner");PendingEmission p1,p2;a.donorSpecies=1;a.donorKey="party:3";
 check(race.prepare(&pom,1,bud,&donor,3,false,p1,e),"reservation one");a.donorKey="party:4";check(race.prepare(&pom,1,bud,&donor,3,false,p2,e),"reservation two before first commit");
 check(race.adopt(std::move(p1),&head,1,3,false,reason),"first output commit");check(!race.adopt(std::move(p2),&head2,1,3,false,reason),"stale preallocated state cannot erase committed graph");
 // Live capacity is enforced BEFORE producer consumes a donor.
 Registry capacity;check(capacity.bind(a,a.proof,e),"capacity owner");PikiHeadItem heads[101];
 for(unsigned i=0;i<100;++i){a.donorKey="party:capacity:"+std::to_string(i);PendingEmission next;check(capacity.prepare(&pom,1,bud,&donor,3,false,next,e)&&capacity.adopt(std::move(next),&heads[i],i+1,3,false,reason),"100 literal live slots");}
 a.donorKey="party:capacity:100";PendingEmission excess;check(!capacity.prepare(&pom,1,bud,&donor,3,false,excess,e),"101st reservation refused before consumption");
 Registry callback;check(callback.bind(a,a.proof,e),"real-ABI adapter owner");Producer producer(callback,a,headColour,fatal);std::string receipt,oldReceipt;
 a.donorKey="party:callback";check(Producer::snapshotCallback(&pom,bud,1,&donor,receipt,&producer),"snapshot callback reserves before donor consumption");oldReceipt=receipt;
 check(Producer::snapshotCallback(&pom,bud,1,&donor,receipt,&producer)&&receipt!=oldReceipt,"capacity retry replaces stale reversible reservation");
 denyAllocation=true;Producer::headCallback(&pom,bud,1,1,&head,false,receipt,&producer);denyAllocation=false;
 check(!failures&&callback.head(&head,decoded),"actual callback ABI adopts without allocation");
 denyAllocation=true;Producer::headCallback(&pom,bud,1,1,&head2,false,oldReceipt,&producer);denyAllocation=false;
 check(failures==1&&!callback.head(&head2,decoded),"old local receipt cannot replay or silently gain ownership");
 // Native converted-donor kill occurs synchronously BEFORE output callback.
 PendingEmission move;check(callback.prepareTransfer(&head,3,move,e)&&callback.adoptBody(std::move(move),&body,reason),"converted donor body");
 a.donorSpecies=3;a.donorKey="conversion:callback";
 check(Producer::snapshotCallback(&pom,bud,1,&body,receipt,&producer),"converted donor reservation includes pending retirement");
 callback.forget(&body);
 denyAllocation=true;Producer::headCallback(&pom,bud,1,2,&head2,true,receipt,&producer);denyAllocation=false;
 check(failures==1&&callback.head(&head2,decoded)&&decoded.refunded&&!callback.body(&body,savedBody),"native kill-before-output and refund preserve new head ownership");
 check(callback.snapshot(live,e)&&live.emissions[0].lifecycle==Lifecycle::Retired&&live.emissions[1].lifecycle==Lifecycle::Head,"donor terminal and output live states both persisted");
 producer.cancel();check(callback.head(&head2,decoded),"cancel never erases committed output");
 PendingEmission finalTransfer;check(callback.prepareTransfer(&head2,3,finalTransfer,e)&&callback.adoptBody(std::move(finalTransfer),&body,reason),"plucked converted body for common typed census");
 registry().swap(callback);PcP2SourceBody typed;check(pc_p2_source_body_query(&body,typed)==PcP2SourceBodyKind::BudConversion&&typed.state.species==3&&!typed.state.wild&&!typed.state.wasWild,"converted body is a distinct nonwild discriminator");
 Piki ordinary;auto prior=typed;check(pc_p2_source_body_query(&ordinary,typed)==PcP2SourceBodyKind::None&&typed.kind==prior.kind,"ordinary body stays unlabelled and output unchanged");
 const auto genCatalog=hash('7');const std::string key="tutorial/defaultgen.txt#5";
 check(pc_p2_original_piki_origin_install(genCatalog,{{key,p2original::originalSourceCatalogUid(key),1,1}},e),"independent immutable GenPiki catalog");
 check(p2original::originalProgress().initialize(hash('a'),e)&&pc_p2_original_piki_recruit_bind(hash('a'),genCatalog,e),"explicit distinct campaign/GenPiki authority pair");
 check(pc_p2_original_piki_recruit_allowed(&body,1,false,true,e),"source day0 nonwild converted body permits Louie");
 check(!pc_p2_original_piki_recruit_allowed(&body,0,false,true,e),"source day0 nonwild converted body excludes Olimar before reunion");
 check(pc_p2_original_piki_contact_owner_allowed(&body,0,1,false,e),"common source discriminator permits canonically accepted contact despite P1 colour owner");
 check(!pc_p2_original_piki_contact_owner_allowed(&body,0,1,true,e),"VS ordinary ownership remains strict");
 auto progress=p2original::originalProgress().snapshot();check(pc_p2_original_piki_recruit_accepted(&body,1,false,true,e)&&p2original::originalProgress().snapshot().met==progress.met,"converted recruitment cannot fabricate RGB first-met");
 a.current=false;check(pc_p2_source_body_query(&body,typed)==PcP2SourceBodyKind::BudConversion&&!pc_p2_original_piki_recruit_allowed(&body,1,false,true,e),"expired converted proof remains labelled but refuses native event");a.current=true;
 check(!pc_p2_source_body_admitted(typed,hash('c'),genCatalog,e),"foreign campaign refused independently of GenPiki catalog");
 registry().sceneExit();check(pc_p2_source_body_query(&body,typed)==PcP2SourceBodyKind::None,"common scene teardown forgets old pool address");
 Registry fresh;a.live={hash('a'),hash('b'),"forest_1","visit:1",hash('c'),hash('d'),hash('e'),1,1,100,12};a.liveActive=true;
 const auto oldProof=a.proof;a.proof={};check(!fresh.bind(a,a.proof,e),"newgame has no fabricated selected card");
 check(fresh.bindLive(a,e),"live installed-floor authority binds before first SAVE");
 a.donorKey="party:fresh";a.donorSpecies=1;PendingEmission premature;check(!fresh.prepare(&pom,1,bud,&donor,3,false,premature,e),"Installing permits registration but cannot emit");
 a.live.phase=CreationPhase::Committed;check(!fresh.prepare(&pom,1,bud,&donor,3,false,premature,e),"Committed floor waits actual game-active before emission");a.live.gameActive=true;
 a.donorKey="party:fresh";a.donorSpecies=1;PendingEmission liveEmission;check(fresh.prepare(&pom,1,bud,&donor,3,false,liveEmission,e),"fresh live source6 reservation without card");
 denyAllocation=true;bool newHead=fresh.adopt(std::move(liveEmission),&head,1,3,false,reason);denyAllocation=false;check(newHead,"fresh live callback remains nonallocating");
 check(fresh.snapshot(live,e),"fresh live family can be captured for FIRST SAVE");
 a.live.gameActive=false;check(fresh.snapshot(unchanged,e),"paused committed floor may capture first SAVE without emission");a.live.gameActive=true;
 ++a.live.nativeSerial;check(!fresh.admitted(live.emissions[0].record,e),"recycled floor serial refuses old authority");--a.live.nativeSerial;
 ++a.live.sessionRevision;check(!fresh.snapshot(unchanged,e),"new native selection lifetime refuses old live binding");--a.live.sessionRevision;
 Registry noProof;check(!noProof.restore(a,live,a.proof,{{live.emissions[0].record.identity,&head}}, {},e),"fresh live authority never substitutes for cold proof");
 a.proof=oldProof;a.proof.generation=3;check(fresh.adoptSelected(a,live,a.proof,e),"actual first successful SAVE transitions live authority to selected card");
 a.liveActive=false;check(fresh.snapshot(unchanged,e),"selected proof mode no longer requires live-creation stamp");
 a.liveActive=true;PendingEmission travelPluck;check(fresh.prepareTransfer(&head,3,travelPluck,e)&&fresh.adoptBody(std::move(travelPluck),&body,reason),"real-pluck-only body before RAM travel");
 Carry carry;const auto carriedId=live.emissions[0].record.identity;
 const std::vector<BodyBinding> departing{{carriedId,&body}};
 a.allow=false;check(!fresh.detachCarry(departing,carry,e)&&!carry.ready()&&fresh.body(&body,savedBody),"refused actual transition keeps old body associations");a.allow=true;
 check(fresh.detachCarry(departing,carry,e)&&carry.ready()&&!fresh.body(&body,savedBody),"actual carry escrow forgets old pointer without losing logical identity");
 fresh.sceneExit();check(!fresh.bindLive(a,e),"old source cannot reopen outstanding carried identities");
 Registry destination;Piki arrived;const std::vector<BodyBinding> arriving{{carriedId,&arrived}};check(!destination.receiveCarry(a,carry,arriving,e)&&carry.ready(),"same native serial cannot masquerade as fresh destination");
 ++a.live.nativeSerial;check(!destination.receiveCarry(a,carry,{},e)&&carry.ready(),"partial carried mapping leaves ticket recoverable");
 auto foreignId=carriedId;++foreignId.emission;check(!destination.receiveCarry(a,carry,{{foreignId,&arrived}},e),"foreign mapped source identity refused");
 check(destination.receiveCarry(a,carry,arriving,e)&&!carry.ready()&&destination.body(&arrived,savedBody)&&savedBody.identity==carriedId,"new physical body adopts SAME conversion identity without emission or cold proof");
 check(destination.snapshot(live,e)&&live.emissions.size()==1&&live.emissions[0].lifecycle==Lifecycle::Body,"whole donor/terminal ledger survives RAM travel");
 check(!destination.receiveCarry(a,carry,{{carriedId,&body}},e),"consumed travel ticket cannot replay");
 check(fresh.bindLive(a,e),"retired source registry may reopen only after destination consumes escrow");
 MockFloor floorReader(a);NativeLiveAuthority native(floorReader,floorReader);Registry strongSession;
 nativeSelected=false;check(!strongSession.bindLive(native,e),"native adapter refuses unauthenticated session");nativeSelected=true;
 nativeCampaign=hash('c');check(!strongSession.bindLive(native,e),"native adapter rejects actual campaign mismatch");nativeCampaign=hash('a');
 nativeSession=hash('c');check(!strongSession.bindLive(native,e),"native adapter rejects immutable session SHA mismatch");nativeSession=hash('b');
 inputValid=false;check(!strongSession.bindLive(native,e),"changed selected immutable input refuses before registration");inputValid=true;
 ++nativeRevision;check(!strongSession.bindLive(native,e),"actual selected session revision differs from floor owner");--nativeRevision;
 check(strongSession.bindLive(native,e),"concrete adapter uses native selection and owned creation instead of mock card");
 p2originalcheckpoint::Proof cannotFake;check(!native.selected(cannotFake,e)&&!cannotFake.valid(),"native live adapter does not issue fake selected proof");
 a.donorKey="party:native-adapter";PendingEmission nativePending;check(strongSession.prepare(&pom,1,bud,&donor,3,false,nativePending,e),"native adapter source6/donor pairing");
 ++nativeRevision;denyAllocation=true;bool rejected=!strongSession.adopt(std::move(nativePending),&head,1,3,false,reason);denyAllocation=false;check(rejected,"nonallocating native selection revision guard rejects final callback");--nativeRevision;
 Registry neverSaved;a.proof={};a.donorKey="party:unsaved-carry";check(neverSaved.bindLive(a,e),"RAM source may exist without selected card");
 PendingEmission unsaved,pluckUnsaved;check(neverSaved.prepare(&pom,1,bud,&donor,3,false,unsaved,e)&&neverSaved.adopt(std::move(unsaved),&head,1,3,false,reason)&&neverSaved.prepareTransfer(&head,3,pluckUnsaved,e)&&neverSaved.adoptBody(std::move(pluckUnsaved),&body,reason),"live original conversion and pluck before first SAVE");
 Record unsavedRecord;check(neverSaved.body(&body,unsavedRecord),"unsaved actual typed body");
 Carry ram;const std::vector<BodyBinding> from{{unsavedRecord.identity,&body}},to{{unsavedRecord.identity,&arrived}};
 check(neverSaved.detachCarry(from,ram,e),"actual committed RAM owner can escrow before first saved-card proof");++a.live.nativeSerial;
 Registry ramDestination;check(ramDestination.receiveCarry(a,ram,to,e)&&ramDestination.body(&arrived,savedBody)&&savedBody.identity==unsavedRecord.identity,"RAM destination retains exact unsaved origin; no fake card/activation/emission");
 MockOnyon onyon,foreignReader;Piki emitted;
 check(pc_p2_source_body_install_onyon_reader(onyon),"install actual producer-owned reader");
 check(!pc_p2_source_body_install_onyon_reader(foreignReader),"reader cannot be replaced while identities may exist");
 onyon.actor=&emitted;PcP2SourceBody external;external.kind=PcP2SourceBodyKind::GenPiki;
 onyon.ready=false;check(pc_p2_source_body_query(&emitted,external)==PcP2SourceBodyKind::Unavailable&&external.kind==PcP2SourceBodyKind::GenPiki,"tag without adopted state never ordinary fallback or output mutation");onyon.ready=true;
 onyon.serial=0;check(pc_p2_source_body_query(&emitted,external)==PcP2SourceBodyKind::Unavailable,"actual lifetime missing refuses owned tag");onyon.serial=7;
 check(pc_p2_source_body_query(&emitted,external)==PcP2SourceBodyKind::OnyonEmission,"typed Onyon body distinct from GenPiki and Bud");
 check(pc_p2_source_body_admitted(external,hash('a'),hash('d'),e),"actual reader owns campaign admission");
 ++onyon.serial;check(!pc_p2_source_body_admitted(external,hash('a'),hash('d'),e),"same address new lifetime rejects old read-view");--onyon.serial;
 check(!pc_p2_source_body_admitted(external,hash('f'),hash('d'),e),"foreign campaign rejected by actual producer");
 check(pc_p2_source_body_recruited(&emitted),"recruit dispatch uses exact current native lifetime");
 registry().swap(ramDestination);onyon.actor=&arrived;check(pc_p2_source_body_query(&arrived,external)==PcP2SourceBodyKind::Unavailable,"overlapping Bud and Onyon tags refuse");
 onyon.actor=&emitted;pc_p2_source_body_forget_external(&emitted);check(onyon.forgets==1&&pc_p2_source_body_query(&emitted,external)==PcP2SourceBodyKind::None,"pool/kill forget removes actual producer association");
 onyon.actor=&emitted;pc_p2_source_body_scene_exit_external();check(onyon.exits==1&&pc_p2_source_body_query(&emitted,external)==PcP2SourceBodyKind::None,"scene exit forgets external tags before reuse");
 std::printf("BUD_ORIGIN_CONTROLS PASS %d (mock proof/opaque actors only)\n",checks);return 0;
}
