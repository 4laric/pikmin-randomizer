#include "pc_p2_original_onyon_lineage.h"
#include <cstdio>
#include <limits>
using namespace p2originalonyon;
namespace {
Root root(const std::string& session,unsigned course=0,unsigned color=0){return Root{session,std::string(64,'b'),"course"+std::to_string(course)+"/onion#0",course,static_cast<std::uint8_t>(color),1};}
SeedCause cause(unsigned uid=1){SeedCause c;c.catalogFingerprint=std::string(64,'c');c.sourceUid=uid;c.sourceType=26;c.epoch=1;c.activation=1;return c;}
bool emissionSame(const MemberOrigin& a,const MemberOrigin& b){
 const auto* x=std::get_if<OnyonEmission>(&a);const auto* y=std::get_if<OnyonEmission>(&b);
 return x&&y&&x->root==y->root&&x->memberSerial==y->memberSerial&&x->cause==y->cause&&x->seedOrdinal==y->seedOrdinal;
}
bool authoredSame(const MemberOrigin& o,const OriginalPikiBody& b){const auto* a=std::get_if<OriginalPikiBody>(&o);return a&&a->origin.sourceKey==b.origin.sourceKey&&a->origin.recordUid==b.origin.recordUid&&a->origin.attempt==b.origin.attempt&&a->origin.activation==b.origin.activation&&a->origin.catalogFingerprint==b.origin.catalogFingerprint&&a->state.species==b.state.species&&a->state.wild==b.state.wild&&a->state.wasWild==b.state.wasWild;}
}
int main(){
 unsigned checks=0,failures=0;auto check=[&](bool b,const char* name){++checks;if(!b){++failures;std::printf("FAIL %s\n",name);}};
 const std::string session(64,'a'),otherSession(64,'d');std::string e;auto r=root(session);auto c=cause();Lineage l(session);
 RewardPlan p;check(l.preflightReward(r,c,12,p,e)&&p.firstSerial==1&&l.report().members.empty(),"reward preflight read-only");
 check(l.commitReward(p,e)&&l.report().members.size()==12,"commit exact12 pending members");
 check(!l.commitReward(p,e)&&l.report().members.size()==12,"duplicate reward range denied");
 auto other=root(session,1);RewardPlan sentinel;sentinel.count=999;
 check(!l.preflightReward(other,c,12,sentinel,e)&&sentinel.count==999,"same corpse cannot pay another Onion");
 auto invalid=r;invalid.sessionFingerprint=otherSession;
 check(!l.preflightReward(invalid,cause(2),1,sentinel,e)&&sentinel.count==999,"crosssession reward denied atomically");
 invalid=r;invalid.sourceSha="x";check(!l.preflightReward(invalid,cause(2),1,sentinel,e),"invalid sourceSHA denied");
 invalid=r;invalid.species=3;check(!l.preflightReward(invalid,cause(2),1,sentinel,e),"nonRGB root denied");
 invalid=r;invalid.incarnation=0;check(!l.preflightReward(invalid,cause(2),1,sentinel,e),"missing actual root incarnation denied");
 invalid=r;invalid.sourceKey="bad\nkey";check(!l.preflightReward(invalid,cause(2),1,sentinel,e),"unbounded source key characters denied");
 auto bad=cause(2);bad.activation=0;check(!l.preflightReward(r,bad,1,sentinel,e),"full cause activation required");
 bad=cause(2);bad.sourceType=55;check(!l.preflightReward(r,bad,1,sentinel,e),"Withering corpse denied");
 bad=cause(2);bad.ancestry=static_cast<AncestryKind>(3);check(!l.preflightReward(r,bad,1,sentinel,e),"untyped child ancestry denied");
 auto number=cause(2);number.kind=CauseKind::Number;number.sourceType=0;number.numericChildSlot=0;number.ancestry=AncestryKind::TamagoMushi;number.emissionOrdinal=0;number.member=2;number.epoch=0;
 RewardPlan numbered;check(l.preflightReward(other,number,1,numbered,e)&&l.commitReward(numbered,e),"typed68 numeric child reward");
 const auto genuineNumber=l.report().members[12];
 check(std::get<OnyonEmission>(genuineNumber.origin).cause==number&&std::get<OnyonEmission>(genuineNumber.origin).cause.sourceType==0,"retain actual Egg root separately from emitted68 ancestry");
 auto child=number;child.member=3;RewardPlan childPlan;
 check(l.preflightReward(other,child,1,childPlan,e),"distinct genuine emitted member");
 auto competing=cause(3);RewardPlan competingPlan;check(l.preflightReward(other,competing,1,competingPlan,e)&&l.commitReward(competingPlan,e),"interleaved reward commit");
 check(!l.commitReward(childPlan,e),"stale unreserved range refused");
 auto butterfly=number;butterfly.sourceUid=4;butterfly.sourceType=66;butterfly.ancestry=AncestryKind::ShijimiChou;
 check(l.preflightReward(other,butterfly,1,p,e)&&l.commitReward(p,e),"typed77 ancestry accepted");
 auto producerBoundary=number;producerBoundary.member=9;
 check(l.preflightReward(other,producerBoundary,1,p,e)&&l.commitReward(p,e),"genuine Egg parent Mitite member9 slot0 emission0");
 producerBoundary=butterfly;producerBoundary.member=4;
 check(l.preflightReward(other,producerBoundary,1,p,e)&&l.commitReward(p,e),"genuine Plant parent Spectralid member4 slot0 emission0");
 producerBoundary=number;producerBoundary.member=10;
 check(!l.preflightReward(other,producerBoundary,1,sentinel,e),"Mitite member10 boundary rejected");
 producerBoundary=butterfly;producerBoundary.member=5;
 check(!l.preflightReward(other,producerBoundary,1,sentinel,e),"Spectralid member5 boundary rejected");
 producerBoundary=number;producerBoundary.numericChildSlot=1;
 check(!l.preflightReward(other,producerBoundary,1,sentinel,e),"emitted member childslot1 rejected");
 producerBoundary=number;producerBoundary.numericChildSlot=4;
 check(!l.preflightReward(other,producerBoundary,1,sentinel,e),"invented emitted member childslot4 rejected");
 producerBoundary=number;producerBoundary.emissionOrdinal=1;
 check(!l.preflightReward(other,producerBoundary,1,sentinel,e),"emission ordinal1 rejected");
 producerBoundary=number;producerBoundary.ancestry=static_cast<AncestryKind>(69);
 check(!l.preflightReward(other,producerBoundary,1,sentinel,e),"unknown emission kind rejected");
 auto directNumber=cause(5);directNumber.kind=CauseKind::Number;directNumber.sourceType=0;directNumber.epoch=0;
 check(l.preflightReward(other,directNumber,1,p,e)&&l.commitReward(p,e),"direct genuine resource childslot0 epoch0");
 directNumber.numericChildSlot=1;
 check(l.preflightReward(other,directNumber,1,p,e)&&l.commitReward(p,e),"direct genuine resource childslot1 distinct");
 directNumber.numericChildSlot=2;
 check(!l.preflightReward(other,directNumber,1,sentinel,e),"resource childslot2 rejected");
 producerBoundary=cause(6);producerBoundary.numericChildSlot=1;
 check(!l.preflightReward(other,producerBoundary,1,sentinel,e),"corpse cannot carry numeric childslot");
 producerBoundary=number;producerBoundary.kind=CauseKind::Corpse;producerBoundary.sourceType=68;producerBoundary.epoch=1;
 check(!l.preflightReward(other,producerBoundary,1,sentinel,e),"corpse cannot carry resource ancestry");
 std::uint64_t pending=999,h=999,bh=999;int head=0,body=0,ordinary=0;
 check(l.nextPending(r,pending,e)&&pending==1,"first pending member selected");
 check(!l.bindPendingHead(pending,r,nullptr,h,e)&&h==999,"null HEAD allocation unchanged");
 auto reborn=r;reborn.incarnation=2;
 check(!l.bindPendingHead(pending,reborn,&head,h,e)&&h==999,"root reincarnation not substituted");
 check(l.bindPendingHead(pending,r,&head,h,e)&&l.report().liveHeads==1,"actual HEAD bind");
 MemberRecord seedRecord;std::uint64_t queryHandle=0;
 check(l.queryHead(&head,session,seedRecord,queryHandle,e)==QueryResult::Present&&queryHandle==h&&seedRecord.state.maturity==0&&!seedRecord.state.wild&&!seedRecord.state.wasWild,"generated seed Leaf nonwild");
 auto origin=seedRecord.origin;MemberRecord untouched;untouched.serial=999;queryHandle=999;
 check(l.queryHead(&head,otherSession,untouched,queryHandle,e)==QueryResult::Unavailable&&untouched.serial==999&&queryHandle==999,"labelled wrongsession HEAD no ordinary fallback");
 check(l.ownsHead(&head)&&!l.ownsHead(nullptr),"unavailable HEAD query preserves native ownership discriminator");
 check(l.queryBody(&ordinary,session,untouched,queryHandle,e)==QueryResult::Missing&&untouched.serial==999&&queryHandle==999,"ordinary body unaffected");
 check(!l.headToBody(&head,h+1,&body,bh,e)&&bh==999,"stale HEAD handle denied");
 check(!l.headToBody(&head,h,nullptr,bh,e)&&bh==999&&l.report().liveHeads==1,"null BODY allocation retains HEAD");
 check(l.headToBody(&head,h,&body,bh,e)&&l.report().liveHeads==0&&l.report().liveBodies==1,"HEAD->BODY before head retirement");
 check(!l.ownsHead(&head),"successful conversion retires persistent HEAD discriminator");
 check(l.retireHead(&head,h,e)&&l.report().liveBodies==1,"postconversion head cleanup harmless");
 MemberRecord bodyRecord;check(l.queryBody(&body,session,bodyRecord,queryHandle,e)==QueryResult::Present&&emissionSame(bodyRecord.origin,origin),"BODY preserves full seed cause and serial");
 check(l.queryBody(&body,otherSession,untouched,queryHandle,e)==QueryResult::Unavailable,"labelled BODY wrong session unavailable");
 auto wrongColor=root(session,2,1);check(!l.depositBody(&body,bh,wrongColor,e)&&l.report().liveBodies==1,"wrongcolor deposit denied atomically");
 MemberBodyState flower{0,2,false,false};check(l.updateBody(&body,bh,flower,e),"actual maturity update");
 check(!l.updateBody(&body,bh,MemberBodyState{1,2,false,false},e),"mutable body cannot change original species");
 check(l.depositBody(&body,bh,other,e)&&l.report().liveBodies==0,"actual crosscourse sameRGB deposit");
 check(l.retireBody(&body,bh,e),"postdeposit native body kill cleanup harmless");
 MemberRecord stored;check(l.peekStored(0,stored,e)==StockResult::Present&&stored.serial==1&&stored.state.maturity==2&&emissionSame(stored.origin,origin)&&stored.receiverRoot==other,"global stock retains birth origin and actual receiver");
 std::array<std::uint64_t,3> counts{99,99,99};
 check(l.storedCounts(0,counts)&&counts[0]==0&&counts[1]==0&&counts[2]==1,"typed stock count exposes actual retained maturity distribution");
 std::uint64_t wh=999;check(!l.withdrawStored(stored.serial,other,nullptr,wh,e)&&wh==999,"failed withdrawal allocation no transition");
 check(l.withdrawStored(stored.serial,r,&body,wh,e)&&wh!=bh,"successful withdrawal preserves serial");
 check(l.queryBody(&body,session,bodyRecord,queryHandle,e)==QueryResult::Present&&bodyRecord.serial==1&&bodyRecord.state.maturity==2&&emissionSame(bodyRecord.origin,origin),"withdrawn origin and maturity unchanged");
 check(!l.retireBody(&body,bh,e),"recycled pointer old handle refused");
 check(l.retireBody(&body,wh,e),"BODY death history retained");
 check(l.retireBody(&body,wh,e),"duplicate native death cleanup harmless");
 check(!l.withdrawStored(1,r,&body,wh,e),"dead member cannot revive as stock");
 check(!l.commitReward(numbered,e),"retired/dead history still prevents reward replay");
 check(!l.courseUnload(e)&&!l.newSession(otherSession,e),"pending members block course/session reset");

 // Full canonical GenPiki identity is preserved, never replaced by an emission.
 Lineage authored(session);OriginalPikiBody a;a.origin={"course/generator#1",123,2,7,std::string(64,'e')};a.state={0,true,true};
 std::uint64_t as=0,ah=0;check(authored.adoptAuthored(session,a,2,&body,as,ah,e),"canonical authored body adoption");
 check(!authored.adoptAuthored(session,a,0,&ordinary,pending,h,e),"duplicate authored logical member denied");
 check(!authored.updateBody(&body,ah,MemberBodyState{0,2,false,false},e),"wasWild history cannot be erased");
 check(authored.updateBody(&body,ah,MemberBodyState{0,2,false,true},e),"recruitment clears only wild");
 check(authored.depositBody(&body,ah,r,e)&&authored.peekStored(0,stored,e)==StockResult::Present&&authoredSame(stored.origin,a)&&stored.state.wasWild&&!stored.state.wild,"authored stock retains immutable origin and current flags");
 check(authored.withdrawStored(as,other,&body,ah,e)&&authored.queryBody(&body,session,bodyRecord,queryHandle,e)==QueryResult::Present&&authoredSame(bodyRecord.origin,a)&&bodyRecord.state.maturity==2,"authored withdrawal no emission forgery");
 check(authored.retireBody(&body,ah,e)&&authored.courseUnload(e),"course unload preserves stored/dead history");
 check(!authored.adoptAuthored(session,a,2,&body,as,ah,e),"course unload does not permit duplicate authored birth");
 check(!authored.adoptAuthored(otherSession,a,2,&body,as,ah,e),"crosssession canonical adoption refused");
 check(authored.newSession(otherSession,e)&&authored.report().members.empty(),"explicit safe new session clears history");

 // Global serials and historical roots are not capped at four course actors.
 Lineage courses(session);std::uint64_t prior=0;bool many=true;
 for(unsigned i=0;i<8;++i){auto courseRoot=root(session,i);RewardPlan range;if(!courses.preflightReward(courseRoot,cause(100+i),1,range,e)||!courses.commitReward(range,e)||!courses.nextPending(courseRoot,pending,e)||pending<=prior||!courses.storePending(pending,courseRoot,e)||!courses.courseUnload(e)){many=false;break;}prior=pending;}
 check(many&&courses.report().members.size()==8,"more than4 course Onion roots retain lineage");
 check(courses.peekStored(0,stored,e)==StockResult::Present&&stored.serial==1,"withinmaturity FIFO deliberate policy");
 check(!courses.withdrawStored(2,r,&body,h,e),"stale nonFIFO selection refused");
 check(courses.markUnknownStock(0,3,e)&&courses.peekStored(0,stored,e)==StockResult::Unavailable,"unknown count-only stock never fabricated");
 counts={99,99,99};check(!courses.storedCounts(0,counts)&&counts[0]==99&&counts[1]==99&&counts[2]==99,"unknown stock counts refuse with output unchanged");
 check(!courses.withdrawStored(1,r,&body,h,e),"unknown stock cannot fallback to ordinary withdrawal");
 check(courses.report().unknownStock[0]==3&&courses.report().members.size()==8,"unknown marker not an invented member");
 check(courses.markUnknownStock(1,std::numeric_limits<std::uint64_t>::max(),e)&&!courses.markUnknownStock(1,1,e),"unknown count overflow refused");
 check(!courses.markUnknownStock(3,1,e),"unknown stock RGB bounded");

 // Independently bounded live pools; native wrappers enforce combined field100.
 Lineage pools(session);check(pools.preflightReward(r,cause(500),201,p,e)&&pools.commitReward(p,e),"pool test reward range");
 int heads[201]={},bodies[101]={};std::uint64_t headHandles[201]={},bodyHandles[101]={};bool poolsOk=true;
 for(unsigned i=0;i<100;++i)if(!pools.bindPendingHead(i+1,r,&heads[i],headHandles[i],e)||!pools.headToBody(&heads[i],headHandles[i],&bodies[i],bodyHandles[i],e))poolsOk=false;
 for(unsigned i=100;i<200;++i)if(!pools.bindPendingHead(i+1,r,&heads[i],headHandles[i],e))poolsOk=false;
 check(poolsOk&&pools.report().liveHeads==100&&pools.report().liveBodies==100,"separate HEAD and BODY bounds");
 h=999;check(!pools.bindPendingHead(201,r,&heads[200],h,e)&&h==999,"101st live HEAD refused");
 check(!pools.headToBody(&heads[100],headHandles[100],&bodies[100],h,e)&&h==999,"101st live BODY refuses retaining HEAD");
 check(pools.retireBody(&bodies[0],bodyHandles[0],e)&&pools.headToBody(&heads[100],headHandles[100],&bodies[0],h,e)&&h!=bodyHandles[0],"death frees pointer with fresh handle");
 check(!pools.retireBody(&bodies[0],bodyHandles[0],e),"reused pointer rejects stale death");
 check(pools.bindPendingHead(201,r,&heads[100],h,e),"transferred HEAD pointer can be reused for next member");
 check(!pools.retireHead(&heads[100],headHandles[100],e),"reused HEAD pointer rejects stale handle");
 Lineage capacity(session);check(capacity.preflightReward(r,cause(600),memberLimit,p,e)&&capacity.commitReward(p,e),"retained member capacity accepted exactly");
 sentinel.count=999;check(!capacity.preflightReward(r,cause(601),1,sentinel,e)&&sentinel.count==999,"65537th retained member refused atomically");
 Lineage invalidSession("bad");check(!invalidSession.preflightReward(r,c,1,p,e),"invalid configured session refuses births");
 check(l.sessionFingerprint()==session&&authored.sessionFingerprint()==otherSession,"readonly constanttime strong session getter");
 static_assert(noexcept(l.ownsBody(nullptr)),"ownsBody must be noexcept");
 static_assert(noexcept(l.bodyHandle(nullptr,h)),"bodyHandle must be noexcept");
 static_assert(noexcept(l.retireSceneBodies()),"scene retirement must be noexcept");
 // Scene disposal occurs after the party observer. It only retires BODY
 // pointers/history and cannot manufacture a deposit or retire pending/HEAD.
 Lineage scene(session);check(scene.preflightReward(r,cause(900),4,p,e)&&scene.commitReward(p,e),"scene teardown members prepared");
 int sceneHead=0,sceneBody=0;std::uint64_t sh=0,sb=0;
 check(scene.bindPendingHead(1,r,&sceneHead,sh,e)&&scene.headToBody(&sceneHead,sh,&sceneBody,sb,e),"scene BODY bound");
 check(scene.bindPendingHead(2,r,&sceneHead,sh,e)&&scene.storePending(3,r,e),"scene retains separate HEAD and stock");
 std::uint64_t observedHandle=999;
 check(scene.ownsBody(&sceneBody)&&scene.bodyHandle(&sceneBody,observedHandle)&&observedHandle==sb,"persistent nonallocating body label and handle");
 check(!scene.ownsBody(&ordinary)&&!scene.bodyHandle(&ordinary,observedHandle)&&observedHandle==sb,"missing reader output unchanged");
 check(scene.queryBody(&sceneBody,otherSession,untouched,queryHandle,e)==QueryResult::Unavailable&&scene.ownsBody(&sceneBody)&&scene.bodyHandle(&sceneBody,observedHandle)&&observedHandle==sb,"wrongsession query preserves persistent owned label");
 const auto beforeScene=scene.report();scene.retireSceneBodies();const auto afterScene=scene.report();
 check(!scene.ownsBody(&sceneBody)&&afterScene.liveBodies==0&&afterScene.liveHeads==1&&afterScene.members.size()==4,"scene retirement only clears BODY bindings");
 check(afterScene.members[0].location==Location::Dead&&emissionSame(afterScene.members[0].origin,beforeScene.members[0].origin)&&afterScene.members[1].location==Location::Head&&afterScene.members[2].location==Location::Stored&&afterScene.members[3].location==Location::Pending,"scene preserves immutable origin HEAD stock pending without deposit");
 observedHandle=999;check(!scene.bodyHandle(&sceneBody,observedHandle)&&observedHandle==999,"retired body handle reader unchanged");
 check(!scene.courseUnload(e)&&!scene.newSession(otherSession,e),"scene BODY teardown cannot bypass HEAD/pending guard");
 check(scene.retireBody(&sceneBody,sb,e),"postscene native body cleanup harmless");
 check(!scene.commitReward(p,e),"scene dead history prevents source reward replay");
 // Course preflight must hold providers before graph disposal, while preserving
 // BODYs for the later Party observer. It does not resolve current authority.
 Lineage finish(session);check(finish.preflightCourseFinish(e),"empty lineage early course guard succeeds");
 check(finish.preflightReward(r,cause(950),1,p,e)&&finish.commitReward(p,e),"early guard pending reward prepared");
 const auto pendingBefore=finish.report();
 check(!finish.preflightCourseFinish(e)&&finish.report().members[0].location==Location::Pending&&finish.report().members.size()==pendingBefore.members.size(),"early guard rejects pending without transition");
 check(finish.bindPendingHead(1,r,&sceneHead,sh,e),"early guard HEAD prepared");
 check(!finish.preflightCourseFinish(e)&&finish.ownsHead(&sceneHead),"early guard refuses persistent live HEAD without tag removal");
 check(finish.queryHead(&sceneHead,otherSession,untouched,queryHandle,e)==QueryResult::Unavailable&&!finish.preflightCourseFinish(e)&&finish.ownsHead(&sceneHead),"unavailable session cannot bypass early HEAD guard");
 check(finish.headToBody(&sceneHead,sh,&sceneBody,sb,e),"early guard BODY transition prepared");
 check(finish.preflightCourseFinish(e)&&finish.ownsBody(&sceneBody)&&!finish.courseUnload(e),"early guard permits live BODY but full unload still refuses");
 check(finish.queryBody(&sceneBody,session,bodyRecord,queryHandle,e)==QueryResult::Present&&bodyRecord.location==Location::Body,"BODY remains readable for Party observer");
 check(finish.depositBody(&sceneBody,sb,r,e)&&finish.preflightCourseFinish(e)&&finish.peekStored(0,stored,e)==StockResult::Present,"stored stock survives read-only early guard");
 const auto storedBefore=finish.report();
 check(finish.preflightCourseFinish(e)&&emissionSame(finish.report().members[0].origin,storedBefore.members[0].origin)&&finish.report().members[0].location==Location::Stored,"early guard preserves stored immutable history");
 std::printf("original_onyon_lineage checks=%u failures=%u engine=0 native_authentication=caller codec=0\n",checks,failures);return failures?1:0;
}
