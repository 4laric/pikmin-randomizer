#include "pc_p2_original_calendar.h"
#include <iostream>
#include <stdexcept>
static unsigned checks=0;static void check(bool ok){++checks;if(!ok)throw std::runtime_error("original calendar control "+std::to_string(checks));}
int main(){
 const std::string campaign(64,'a'),source(64,'b');std::ostringstream out;out<<"P2_SOURCE_CALENDAR 1 "<<campaign<<' '<<source<<" 4\n";
 for(const char* course:{"tutorial","forest","yakushima","last"}){
  out<<course<<" 6\n";for(const char* name:{"defaultgen.txt","plantsgen.txt","initgen.txt","nonloop/0-9.txt","loop/30-39.txt","day/0.txt"})out<<name<<' '<<source<<" 1 "<<p2original::originalSourceCatalogUid(std::string(course)+"/"+name+"#0")<<" 0 piki\n";
  // Declared expiry deliberately differs from the filename; this is source authority.
  out<<"1 nonloop/0-9.txt 0 9 7\n1 loop/30-39.txt 30 39 45\n";
 }out<<"END\n";const auto bytes=out.str();std::string error;p2original::SourceCalendar calendar;
 check(calendar.read(bytes,campaign,source,error));p2original::CalendarState flags;std::vector<p2original::CalendarLoad> plan;
 check(calendar.plan("tutorial",0,flags,plan,error));check(plan.size()==5&&plan[2].member->name=="initgen.txt"&&plan[3].expiry==7&&plan.back().member->name=="day/0.txt");
 flags.visited=true;flags.nonloopLoaded=1;check(calendar.plan("tutorial",0,flags,plan,error));check(plan.size()==3);
 flags.nonloopLoaded=0;check(calendar.plan("tutorial",30,flags,plan,error));check(plan.size()==4&&plan[2].expiry==45);check(calendar.plan("tutorial",60,flags,plan,error));check(plan[2].expiry==75);
 flags.loopLoaded=1;check(calendar.plan("tutorial",60,flags,plan,error));check(plan.size()==3);check(p2original::SourceCalendar::advanceLoopFlags(61,flags.loopLoaded));check(flags.loopLoaded==1);check(p2original::SourceCalendar::advanceLoopFlags(90,flags.loopLoaded));check(!flags.loopLoaded);
 flags.nonloopLoaded=2;const auto old=plan;check(!calendar.plan("tutorial",0,flags,plan,error));check(plan.size()==old.size());
 check(!calendar.read(bytes,std::string(64,'c'),source,error));check(calendar.campaign()==campaign);
 for(std::size_t n=0;n<bytes.size()-1;++n){check(!calendar.read(bytes.substr(0,n),campaign,source,error));check(calendar.campaign()==campaign);}
 std::string key,sha;auto* row=calendar.source(p2original::originalSourceCatalogUid("tutorial/initgen.txt#0"),&key,&sha);check(row&&row->kind=="piki"&&key=="tutorial/initgen.txt#0"&&sha==source);
 auto corrupt=bytes;const auto at=corrupt.find(" 0 piki");corrupt.replace(at+1,1,"1");check(!calendar.read(corrupt,campaign,source,error));
 std::cout<<"PASS original source calendar "<<checks<<" controls (planning only)\n";
}
