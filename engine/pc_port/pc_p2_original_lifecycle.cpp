#include "pc_p2_original_lifecycle.h"
#include "netplay/pc_netplay_sha256.h"
#include <limits>
#include <algorithm>
namespace p2original {namespace {
bool fail(std::string& e,const char* s){e=s;return false;}
bool fingerprintValid(const std::string& f){if(f.size()!=64)return false;for(char c:f)if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return false;return true;}
bool valid(const GeneratorState& s){return (s.uid&0xff000000u)==0x52000000u&&s.count<=10&&s.reserved<=65535&&s.deathCount<=s.count&&s.dayNum<=32767&&s.resurrectionDays>=-32768&&s.resurrectionDays<=32767&&s.dayLimit>=-32768&&s.dayLimit<=32767&&((s.epoch&&s.activation)||!s.deathCount);}
void put(std::string& b,std::uint64_t n,unsigned width){for(unsigned i=0;i<width;++i)b.push_back(char((n>>(8*i))&255));}
std::uint64_t get(const std::string& b,unsigned& p,unsigned width){std::uint64_t n=0;for(unsigned i=0;i<width;++i)n|=std::uint64_t(static_cast<unsigned char>(b[p++]))<<(8*i);return n;}
int signed16(std::uint64_t n){return n<32768?int(n):int(n)-65536;}
std::string checksum(const std::string& b){unsigned char out[32];pc_netplay_sha::sha256(b.data(),b.size(),out);return std::string(reinterpret_cast<char*>(out),32);}
}
bool decideOriginalGeneration(const GeneratorState& state,unsigned day,bool disc,GenerationDecision& out,std::string& error){
 if(!valid(state)||day>32767)return fail(error,"invalid original generator state/day");
 GenerationDecision next;next.next=state;
 if(state.dayLimit!=-1&&std::int64_t(state.dayLimit)<std::int64_t(day)){next.expired=true;out=next;error.clear();return true;}
 if(disc){next.next.deathCount=0;next.next.dayNum=day;next.resetDeaths=true;}
 else if(!(state.reserved&4)){out=next;error.clear();return true;}
 else {
  // P2 adds unsigned mDayNum to signed resurrectionDays, then compares the
  // signed 32-bit result. Express its wrapping arithmetic without host UB.
  const std::uint32_t sum=std::uint32_t(state.dayNum)+std::uint32_t(state.resurrectionDays);
  const std::int64_t deadline=sum<0x80000000u?std::int64_t(sum):std::int64_t(sum)-0x100000000LL;
  if(std::int64_t(day)>=deadline){next.next.dayNum=day;next.next.deathCount=0;next.resetDeaths=true;}
 }
 if(!state.epoch)next.next.epoch=1;
 else if(next.resetDeaths){if(state.epoch==std::numeric_limits<std::uint64_t>::max())return fail(error,"original respawn epoch exhausted");next.next.epoch=state.epoch+1;}
 next.generate=true;next.remaining=next.next.count-next.next.deathCount;out=next;error.clear();return true;
}
bool beginOriginalActivation(const GeneratorState& state,GeneratorState& out,std::string& error){
 if(!valid(state)||state.activation==std::numeric_limits<std::uint64_t>::max())return fail(error,"invalid/exhausted original course activation");
 auto next=state;++next.activation;out=next;error.clear();return true;
}
bool originalDeath(const GeneratorState& state,GeneratorState& out,std::string& error){
 if(!valid(state)||!state.epoch||!state.activation||state.deathCount>=state.count)return fail(error,"original death requires born nonexhausted group");
 auto next=state;++next.deathCount;out=next;error.clear();return true;
}
bool encodeOriginalState(const std::string& fingerprint,const GeneratorState& state,std::string& out,std::string& error){
 if(!fingerprintValid(fingerprint)||!valid(state))return fail(error,"invalid original native cache binding/state");
 std::string b="OGC2";b+=fingerprint;put(b,state.uid,4);put(b,state.count,2);put(b,state.reserved,2);put(b,state.deathCount,2);put(b,state.dayNum,2);put(b,std::uint16_t(state.resurrectionDays),2);put(b,std::uint16_t(state.dayLimit),2);put(b,state.epoch,8);put(b,state.activation,8);b+=checksum(b);out.swap(b);error.clear();return true;
}
bool decodeOriginalState(const std::string& fingerprint,unsigned uid,unsigned count,const std::string& bytes,GeneratorState& out,std::string& error){
 if(!fingerprintValid(fingerprint)||bytes.size()!=132||bytes.compare(0,4,"OGC2")||bytes.compare(4,64,fingerprint)||bytes.substr(100)!=checksum(bytes.substr(0,100)))return fail(error,"original cache version/checksum/catalog mismatch");
 unsigned p=68;GeneratorState s;s.uid=unsigned(get(bytes,p,4));s.count=unsigned(get(bytes,p,2));s.reserved=unsigned(get(bytes,p,2));s.deathCount=unsigned(get(bytes,p,2));s.dayNum=unsigned(get(bytes,p,2));s.resurrectionDays=signed16(get(bytes,p,2));s.dayLimit=signed16(get(bytes,p,2));s.epoch=get(bytes,p,8);s.activation=get(bytes,p,8);
 if(!valid(s)||s.uid!=uid||s.count!=count)return fail(error,"original cache source/counter mismatch");
 out=s;error.clear();return true;
}
bool IncarnationFrontier::initialize(const std::string& campaign,std::string& e){
 if(!fingerprintValid(campaign)||(!mCampaign.empty()&&mCampaign!=campaign))return fail(e,"original incarnation campaign mismatch");
 mCampaign=campaign;e.clear();return true;
}
bool IncarnationFrontier::activate(const GeneratorState& source,unsigned day,bool disc,GenerationDecision& out,std::string& e){
 if(mCampaign.empty())return fail(e,"original incarnation campaign unavailable");
 auto seed=source;auto found=mMarks.find(seed.uid);
 if(found!=mMarks.end()){
  // Disc keeps its literal counter reset while obtaining a fresh respawn ID.
  if(disc&&!seed.epoch)seed.epoch=found->second.first;
  seed.activation=std::max(seed.activation,found->second.second);
 }
 GenerationDecision next;
 if(!decideOriginalGeneration(seed,day,disc,next,e))return false;
 if(next.expired){out=next;e.clear();return true;}
 if(!next.generate)return fail(e,"original saved-creature payload loader is not implemented");
 GeneratorState activated;if(!beginOriginalActivation(next.next,activated,e))return false;
 if(found==mMarks.end()&&mMarks.size()>=65536)return fail(e,"original incarnation frontier capacity exhausted");
 auto& mark=mMarks[seed.uid];mark.first=std::max(mark.first,activated.epoch);mark.second=activated.activation;
 next.next=activated;out=next;e.clear();return true;
}
bool IncarnationFrontier::encode(std::string& out,std::string& e)const{
 if(!fingerprintValid(mCampaign))return fail(e,"original incarnation campaign unavailable");
 std::string b="P2IF1";b+=mCampaign;put(b,mMarks.size(),4);
 for(const auto& entry:mMarks){put(b,entry.first,4);put(b,entry.second.first,8);put(b,entry.second.second,8);}
 b+=checksum(b);out.swap(b);e.clear();return true;
}
bool IncarnationFrontier::nextActivation(unsigned uid,std::uint64_t& out,std::string& e){
 if(mCampaign.empty()||(uid&0xff000000u)!=0x52000000u)return fail(e,"original typed incarnation source/campaign invalid");
 auto found=mMarks.find(uid);
 if(found==mMarks.end()&&mMarks.size()>=65536)return fail(e,"original incarnation frontier capacity exhausted");
 const auto previous=found==mMarks.end()?0:found->second.second;
 if(previous==std::numeric_limits<std::uint64_t>::max())return fail(e,"original typed incarnation exhausted");
 auto& mark=mMarks[uid];mark.first=std::max(mark.first,std::uint64_t(1));mark.second=previous+1;
 out=mark.second;e.clear();return true;
}
bool IncarnationFrontier::decode(const std::string& campaign,const std::string& b,std::string& e){
 if(!fingerprintValid(campaign)||(!mCampaign.empty()&&mCampaign!=campaign)||b.size()<105||b.size()>105+20*65536||b.substr(0,5)!="P2IF1"||b.substr(5,64)!=campaign||b.substr(b.size()-32)!=checksum(b.substr(0,b.size()-32)))return fail(e,"original incarnation envelope invalid");
 unsigned p=69,count=unsigned(get(b,p,4));if(count>65536||b.size()!=105+20*size_t(count))return fail(e,"original incarnation count invalid");
 auto next=mMarks;unsigned previous=0;
 for(unsigned i=0;i<count;++i){unsigned uid=unsigned(get(b,p,4));auto epoch=get(b,p,8),activation=get(b,p,8);
  if((uid&0xff000000u)!=0x52000000u||!epoch||!activation||(i&&uid<=previous))return fail(e,"original incarnation mark invalid or duplicated");
  previous=uid;auto& mark=next[uid];mark.first=std::max(mark.first,epoch);mark.second=std::max(mark.second,activation);
 }
 if(next.size()>65536)return fail(e,"original incarnation merged capacity exhausted");
 mMarks.swap(next);mCampaign=campaign;e.clear();return true;
}
}
