#include "pc_p2_campaign_checkpoint_state.h"
#include <iostream>
#include <stdexcept>
#include <sstream>
static unsigned checks=0;
static void check(bool ok){++checks;if(!ok)throw std::runtime_error("campaign carrier control "+std::to_string(checks));}
static p2treasure::Catalog catalog(){
 p2treasure::Catalog c;
 for(int i=0;i<201;++i){p2treasure::Entry e;e.id="source_"+std::to_string(i);e.kind="otakara";e.classification=p2treasure::Classification::Campaign;e.unique=true;e.dictionary=i+1;e.index=i;e.value=50;e.strength=1;e.slots=3;c.entries.push_back(e);}return c;
}
static std::string wire(const P2CampaignCheckpointState& s){std::ostringstream out;s.write(out);return out.str();}
int main(){
 const std::string campaign(64,'a'),source(64,'b');std::string error;
 p2original::Progress progress;check(progress.initialize(campaign,error));check(progress.recruited(1,error));check(progress.hello(1,error));check(progress.reunite(error));check(progress.nextDay(error));
 p2original::IncarnationFrontier frontier;check(frontier.initialize(campaign,error));
 p2original::GeneratorState generator;generator.uid=0x5200007b;generator.count=2;generator.reserved=15;
 p2original::GenerationDecision decision;check(frontier.activate(generator,1,true,decision,error));
 P2CampaignCheckpointState state;state.present=true;state.original=campaign;
 check(progress.encode(state.progress,error));check(progress.encodeContext(state.context,error));check(frontier.encode(state.frontier,error));
 p2original::CalendarLedger calendar;check(calendar.initialize(campaign,progress.context().day,error));check(calendar.encode(state.calendar,error));
 auto c=catalog();p2treasurestate::State ledger;check(ledger.bind(source));check(ledger.credit(c,"source_200",50)==p2treasurestate::Credit::Added);state.treasure=p2treasurestate::encode(ledger.snapshot());
 check(state.matches(campaign,source,&c));const auto encoded=wire(state);
 P2CampaignCheckpointState resumed;std::istringstream input(encoded);check(resumed.read(input,&c,source));check(wire(resumed)==encoded);check(resumed.matches(campaign,source,&c));
 check(!resumed.matches(std::string(64,'c'),source,&c));check(!resumed.matches(campaign,std::string(64,'c'),&c));check(!resumed.matches("",source,&c));check(!resumed.matches(campaign,"",&c));
 // Every incomplete record leaves the previously selected snapshot untouched.
 for(std::size_t n=0;n<encoded.size();++n){std::istringstream truncated(encoded.substr(0,n));auto old=resumed;check(!resumed.read(truncated,&c,source));check(wire(resumed)==wire(old));}
 auto bad=state;bad.context=std::string(106,'x');check(!bad.valid(&c,source));bad=state;bad.original=std::string(64,'c');check(!bad.valid(&c,source));bad=state;bad.frontier[70]^=1;check(!bad.valid(&c,source));
 bad=state;bad.treasure.back()='A';std::istringstream broken(wire(bad));check(!resumed.read(broken,&c,source));check(wire(resumed)==encoded);
 bad=state;bad.present=false;check(!bad.valid(&c,source));bad=state;bad.original.clear();check(!bad.valid(&c,source));
 auto originalOnly=state;originalOnly.treasure.clear();check(originalOnly.matches(campaign,""));check(!originalOnly.matches(campaign,source,&c));
 auto treasureOnly=state;treasureOnly.original.clear();treasureOnly.progress.clear();treasureOnly.context.clear();treasureOnly.frontier.clear();treasureOnly.calendar.clear();check(treasureOnly.matches("",source,&c));
 auto oldOriginal=encoded;oldOriginal.replace(oldOriginal.find("CAMPAIGN_STATE 2"),16,"CAMPAIGN_STATE 1");std::istringstream oldSource(oldOriginal);check(!resumed.read(oldSource,&c,source));check(wire(resumed)==encoded);
 auto oldTreasure=wire(treasureOnly);oldTreasure.replace(oldTreasure.find("CAMPAIGN_STATE 2"),16,"CAMPAIGN_STATE 1");std::istringstream legacy(oldTreasure);P2CampaignCheckpointState legacyState;check(legacyState.read(legacy,&c,source));check(legacyState.matches("",source,&c));
 auto wrongDay=state;p2original::CalendarLedger otherCalendar;check(otherCalendar.initialize(campaign,0,error));check(otherCalendar.encode(wrongDay.calendar,error));check(!wrongDay.valid(&c,source));
 auto missingCalendar=state;missingCalendar.calendar.clear();check(!missingCalendar.valid(&c,source));
 P2CampaignCheckpointState absent;check(absent.matches("",""));check(wire(absent).empty());check(!absent.matches(campaign,""));absent.present=true;check(!absent.valid());
 std::string bytes="preserved";check(!P2CampaignCheckpointState::unhex("AA",1,1,bytes));check(bytes=="preserved");check(!P2CampaignCheckpointState::unhex(std::string(211,'a'),105,105,bytes));check(bytes=="preserved");
 // Adoption can roll scalar receipts back; incarnation identity stays monotonic.
 p2original::Progress adopted;check(adopted.decode(resumed.progress,campaign,error));check(adopted.decodeContext(resumed.context,campaign,error));check(adopted.context().day==1&&adopted.context().reunited&&adopted.met(1));
 p2original::GeneratorState next=decision.next;check(frontier.activate(next,1,false,decision,error));const auto activation=decision.next.activation;check(frontier.decode(campaign,resumed.frontier,error));check(frontier.activate(next,1,false,decision,error));check(decision.next.activation>activation);
 std::cout<<"PASS coherent campaign checkpoint carrier "<<checks<<" controls (codec only)\n";
}
