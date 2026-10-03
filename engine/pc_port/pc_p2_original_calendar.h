#pragma once
#include "pc_p2_original_source_uid.h"
#include "pc_p2_campaign_treasure_state.h"
#include <map>
#include <vector>
namespace p2original {
struct CalendarSource {unsigned uid=0,index=0;std::string kind;};
struct CalendarMember {std::string name,sha;std::vector<CalendarSource> sources;};
struct CalendarLimit {std::string member;unsigned minimum=0,maximum=0;int expiry=-1;};
struct CalendarCourse {std::map<std::string,CalendarMember> members;std::vector<CalendarLimit> nonloop,loop;};
struct CalendarState {bool visited=false;std::uint64_t nonloopLoaded=0,loopLoaded=0;};
struct CalendarLoad {const CalendarMember* member=nullptr;int expiry=-1;int category=0,index=-1;};
// Pure original load planning. Caller supplies authenticated actual cache flags;
// this never marks loads successful, births actors or advances source days.
class SourceCalendar {
 std::string mCampaign,mSourceSha;std::map<std::string,CalendarCourse> mCourses;
 static bool path(const std::string& s){
  if(s.empty()||s.size()>255||s.front()=='/'||s.back()=='/'||s.find("//")!=std::string::npos)return false;
  std::size_t start=0;for(std::size_t i=0;i<=s.size();++i){if(i==s.size()||s[i]=='/'){const auto p=s.substr(start,i-start);if(p=="."||p=="..")return false;start=i+1;}else if(!((s[i]>='a'&&s[i]<='z')||(s[i]>='A'&&s[i]<='Z')||(s[i]>='0'&&s[i]<='9')||s[i]=='_'||s[i]=='-'||s[i]=='.'))return false;}return true;
 }
 static bool flags(std::uint64_t bits,std::size_t count){return count==64||!(bits>>count);}
 static bool fail(std::string& e,const char* why){e=why;return false;}
public:
 const std::string& campaign()const{return mCampaign;}
 const std::string& sourceSha()const{return mSourceSha;}
 const std::map<std::string,CalendarCourse>& courses()const{return mCourses;}
 const CalendarSource* source(unsigned uid,std::string* key=nullptr,std::string* sha=nullptr)const{
  for(const auto& c:mCourses)for(const auto& member:c.second.members)for(const auto& s:member.second.sources)if(s.uid==uid){if(key)*key=c.first+"/"+member.first+"#"+std::to_string(s.index);if(sha)*sha=member.second.sha;return &s;}return nullptr;
 }
 bool read(const std::string& bytes,const std::string& campaign,const std::string& sourceSha,std::string& e){
  if(bytes.empty()||bytes.size()>16*1024*1024||!p2treasurestate::digest(campaign)||!p2treasurestate::digest(sourceSha))return fail(e,"original calendar bounds/identity invalid");
  std::istringstream in(bytes);std::string magic,version,course,name,extra;unsigned courses=0,total=0;SourceCalendar next;std::set<unsigned> uids;
  if(!(in>>magic>>version>>next.mCampaign>>next.mSourceSha>>courses)||magic!="P2_SOURCE_CALENDAR"||version!="1"||next.mCampaign!=campaign||next.mSourceSha!=sourceSha||courses!=4)return fail(e,"original calendar envelope mismatch");
  for(unsigned c=0;c<courses;++c){unsigned count=0;CalendarCourse value;
   if(!(in>>course>>count)||(course!="tutorial"&&course!="forest"&&course!="yakushima"&&course!="last")||next.mCourses.count(course)||count<1||count>4096)return fail(e,"original calendar course/member count invalid");
   for(unsigned m=0;m<count;++m){CalendarMember member;unsigned rows=0;
    if(!(in>>member.name>>member.sha>>rows)||!path(member.name)||member.name.size()<4||member.name.substr(member.name.size()-4)!=".txt"||!p2treasurestate::digest(member.sha)||rows>65536-total||value.members.count(member.name))return fail(e,"original calendar member invalid");
    for(unsigned r=0;r<rows;++r){CalendarSource s;if(!(in>>s.uid>>s.index>>s.kind)||s.index!=r||s.kind.empty()||s.kind.size()>16||s.kind.find_first_not_of("abcdefghijklmnopqrstuvwxyz0123456789_")!=std::string::npos||s.uid!=originalSourceCatalogUid(course+"/"+member.name+"#"+std::to_string(s.index))||!uids.insert(s.uid).second)return fail(e,"original calendar source identity invalid");member.sources.push_back(s);}
    total+=rows;value.members.emplace(member.name,std::move(member));
   }
   for(auto* limits:{&value.nonloop,&value.loop}){unsigned rows=0;if(!(in>>rows)||rows>64)return fail(e,"original calendar declaration count invalid");std::set<std::string> names;
    for(unsigned r=0;r<rows;++r){CalendarLimit limit;if(!(in>>limit.member>>limit.minimum>>limit.maximum>>limit.expiry)||limit.minimum>limit.maximum||limit.maximum>0x7fffffffu||limit.expiry< -1||!value.members.count(limit.member)||!names.insert(limit.member).second||limit.member.compare(0,limits==&value.nonloop?8:5,limits==&value.nonloop?"nonloop/":"loop/"))return fail(e,"original calendar declaration invalid");limits->push_back(limit);}
   }
   if(!value.members.count("defaultgen.txt"))return fail(e,"original calendar default member missing");next.mCourses.emplace(course,std::move(value));
  }
  if(!(in>>extra)||extra!="END"||(in>>extra))return fail(e,"original calendar trailing/truncated data");*this=std::move(next);e.clear();return true;
 }
 bool plan(const std::string& course,unsigned day,const CalendarState& state,std::vector<CalendarLoad>& out,std::string& e)const{
  auto found=mCourses.find(course);if(found==mCourses.end()||day>0x7fffffffu)return fail(e,"original calendar selected course/day invalid");const auto& c=found->second;
  if(!flags(state.nonloopLoaded,c.nonloop.size())||!flags(state.loopLoaded,c.loop.size()))return fail(e,"original calendar cache flag index invalid");std::vector<CalendarLoad> next;
  auto append=[&](const std::string& member,int expiry,int category,int index){auto m=c.members.find(member);if(m!=c.members.end())next.push_back({&m->second,expiry,category,index});};
  append("defaultgen.txt",-1,0,-1);append("plantsgen.txt",-1,1,-1);if(!state.visited)append("initgen.txt",-1,2,-1);
  for(int category=0;category<2;++category){const auto& limits=category?c.loop:c.nonloop;const auto loaded=category?state.loopLoaded:state.nonloopLoaded;
   for(std::size_t i=0;i<limits.size();++i){if(loaded&(std::uint64_t(1)<<i))continue;const auto& limit=limits[i];unsigned minimum=limit.minimum,maximum=limit.maximum,today=day;std::int64_t expiry=limit.expiry;
    if(category){if(day<30)continue;minimum%=30;maximum%=30;today%=30;expiry=expiry-30+std::int64_t(day/30)*30;}
    if(minimum<=today&&today<=maximum){if(expiry< -1||expiry>0x7fffffff)return fail(e,"original calendar effective expiry outside supported bound");append(limit.member,int(expiry),category+3,int(i));}
   }
  }
  append("day/"+std::to_string(day%30)+".txt",-1,5,-1);out.swap(next);e.clear();return true;
 }
 static bool advanceLoopFlags(unsigned nextDay,std::uint64_t& loaded){if(nextDay>0x7fffffffu)return false;if(nextDay%30==0)loaded=0;return true;}
};
}
