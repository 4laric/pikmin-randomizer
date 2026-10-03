#pragma once
#include "pc_p2_original_calendar.h"
#include "netplay/pc_netplay_sha256.h"
#include <array>
namespace p2original {
// Only the actual course loader commits these flags after every source birth
// and cached physical restore succeeds. Native-card authentication is external.
class CalendarLedger {
 std::string mCampaign;
 unsigned mDay=0;
 std::array<CalendarState,4> mStates{};
 static int slot(const std::string& course){int i=0;for(const char* c:{"tutorial","forest","yakushima","last"}){if(course==c)return i;++i;}return -1;}
 static bool fail(std::string& e,const char* message){e=message;return false;}
 static void put(std::string& b,std::uint64_t n,unsigned width){for(unsigned i=0;i<width;++i)b+=char(n>>(8*i));}
 static std::uint64_t get(const std::string& b,std::size_t& p,unsigned width){std::uint64_t n=0;for(unsigned i=0;i<width;++i)n|=std::uint64_t(static_cast<unsigned char>(b[p++]))<<(8*i);return n;}
 static std::string hash(const std::string& b){unsigned char sha[32];pc_netplay_sha::sha256(b.data(),b.size(),sha);return std::string(reinterpret_cast<const char*>(sha),32);}
public:
 static constexpr std::size_t Bytes=173;
 const std::string& campaign()const{return mCampaign;}
 unsigned day()const{return mDay;}
 bool initialize(const std::string& campaign,unsigned day,std::string& e){
  if(!p2treasurestate::digest(campaign)||day>0x7fffffffu)return fail(e,"original calendar state identity/day invalid");
  if(!mCampaign.empty()&&(mCampaign!=campaign||mDay!=day))return fail(e,"original calendar state cannot replace selected session");
  if(mCampaign.empty()){mCampaign=campaign;mDay=day;mStates={};}e.clear();return true;
 }
 bool state(const std::string& course,CalendarState& out,std::string& e)const{
  const int i=slot(course);if(mCampaign.empty()||i<0)return fail(e,"original calendar state course unavailable");out=mStates[i];e.clear();return true;
 }
 bool commit(const std::string& course,const std::vector<CalendarLoad>& loads,std::string& e){
  const int i=slot(course);if(mCampaign.empty()||i<0)return fail(e,"original calendar commit outside selected session");
  auto next=mStates[i];std::set<std::string> members;
  for(const auto& load:loads){
   if(!load.member||!members.insert(load.member->name).second||load.category<0||load.category>5||load.expiry< -1)
    return fail(e,"original calendar successful-load proof invalid");
   if(load.category==3||load.category==4){
    if(load.index<0||load.index>=64)return fail(e,"original calendar successful declaration index invalid");
    auto& flags=load.category==3?next.nonloopLoaded:next.loopLoaded;flags|=std::uint64_t(1)<<load.index;
   }else if(load.index!=-1)return fail(e,"original calendar ordinary-member index invalid");
  }
  next.visited=true;mStates[i]=next;e.clear();return true;
 }
 bool advance(unsigned nextDay,std::string& e){
  if(mCampaign.empty()||mDay==0x7fffffffu||nextDay!=mDay+1)return fail(e,"original calendar day event is not the next source day");
  auto next=mStates;for(auto& state:next)if(!SourceCalendar::advanceLoopFlags(nextDay,state.loopLoaded))return fail(e,"original loop calendar reset failed");
  mStates=next;mDay=nextDay;e.clear();return true;
 }
 bool encode(std::string& out,std::string& e)const{
  if(!p2treasurestate::digest(mCampaign)||mDay>0x7fffffffu)return fail(e,"original calendar state is unbound");
  std::string b="P2CL1";b+=mCampaign;put(b,mDay,4);
  for(const auto& state:mStates){b+=char(state.visited);put(b,state.nonloopLoaded,8);put(b,state.loopLoaded,8);}
  b+=hash(b);out.swap(b);e.clear();return true;
 }
 bool decode(const std::string& campaign,unsigned day,const std::string& bytes,std::string& e){
  if(bytes.size()!=Bytes||bytes.substr(0,5)!="P2CL1"||bytes.substr(5,64)!=campaign||!p2treasurestate::digest(campaign)
   ||hash(bytes.substr(0,Bytes-32))!=bytes.substr(Bytes-32))return fail(e,"original calendar checkpoint envelope mismatch");
  CalendarLedger next;next.mCampaign=campaign;std::size_t p=69;next.mDay=unsigned(get(bytes,p,4));
  if(next.mDay!=day||day>0x7fffffffu)return fail(e,"original calendar checkpoint source day mismatch");
  for(auto& state:next.mStates){const unsigned visited=unsigned(get(bytes,p,1));if(visited>1)return fail(e,"original calendar visited flag invalid");state.visited=visited!=0;state.nonloopLoaded=get(bytes,p,8);state.loopLoaded=get(bytes,p,8);}
  *this=std::move(next);e.clear();return true;
 }
};
}
