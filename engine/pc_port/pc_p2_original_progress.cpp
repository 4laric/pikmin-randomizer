#include "pc_p2_original_progress.h"
#include "netplay/pc_netplay_sha256.h"
namespace p2original {namespace {
bool fail(std::string& e,const char* s){e=s;return false;}
bool fingerprint(const std::string& f){if(f.size()!=64)return false;for(char c:f)if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return false;return true;}
bool valid(const ProgressState& s){return fingerprint(s.campaign)&&s.met<32&&s.boot<8&&s.container<32;}
std::string hash(const std::string& b){unsigned char h[32];pc_netplay_sha::sha256(b.data(),b.size(),h);return std::string(reinterpret_cast<char*>(h),32);}
}
bool Progress::initialize(const std::string& campaign,std::string& e){
 if(!fingerprint(campaign))return fail(e,"original progression campaign binding invalid");
 if(ready()&&mState.campaign!=campaign)return fail(e,"original progression belongs to another campaign");
 if(!ready()){mState.campaign=campaign;mContext.campaign=campaign;}e.clear();return true;
}
bool Progress::met(unsigned species)const{return species==5||(ready()&&species<5&&(mState.met&(1u<<species)));}
bool Progress::booted(unsigned species)const{return ready()&&species<3&&(mState.boot&(1u<<species));}
bool Progress::container(unsigned species)const{return ready()&&species<5&&(mState.container&(1u<<species));}
bool Progress::recruited(unsigned species,std::string& e){
 if(!ready()||species>2)return fail(e,"original wild recruitment requires RGB campaign body");
 if(!booted(species)){
  mState.container|=1u<<species;mState.boot|=1u<<species;
  if(species!=1)mState.met|=1u<<species;
 }
 e.clear();return true;
}
bool Progress::hello(unsigned species,std::string& e){
 if(!ready()||species>4)return fail(e,"original first-met event species invalid");
 mState.met|=1u<<species;mState.container|=1u<<species;e.clear();return true;
}
bool Progress::boot(unsigned species,std::string& e){
 if(!ready()||species>2)return fail(e,"original container boot event must be RGB");
 mState.boot|=1u<<species;e.clear();return true;
}
bool Progress::discover(unsigned species,std::string& e){
 if(!ready()||species>4)return fail(e,"original container discovery event species invalid");
 mState.container|=1u<<species;e.clear();return true;
}
bool Progress::restore(const ProgressState& s,std::string& e){
 if(!valid(s)||(ready()&&mState.campaign!=s.campaign))return fail(e,"original selected progress state invalid or cross-campaign");
 mState=s;if(mContext.campaign.empty())mContext.campaign=s.campaign;e.clear();return true;
}
bool Progress::encode(std::string& out,std::string& e)const{
 if(!valid(mState))return fail(e,"original progression not initialized");
 std::string b="P2PR1";b+=mState.campaign;b+=char(mState.met);b+=char(mState.boot);b+=char(mState.container);b+=hash(b);out.swap(b);e.clear();return true;
}
bool Progress::decode(const std::string& bytes,const std::string& campaign,std::string& e){
 if(bytes.size()!=104||bytes.substr(0,5)!="P2PR1"||bytes.substr(5,64)!=campaign||hash(bytes.substr(0,72))!=bytes.substr(72))return fail(e,"original persisted progression binding/checksum invalid");
 ProgressState s;s.campaign=campaign;s.met=static_cast<unsigned char>(bytes[69]);s.boot=static_cast<unsigned char>(bytes[70]);s.container=static_cast<unsigned char>(bytes[71]);return restore(s,e);
}
Progress& originalProgress(){static Progress p;return p;}
bool Progress::nextDay(std::string& e){
 if(!ready()||mContext.day==0xffffffffu)return fail(e,"original source day unavailable/exhausted");
 ++mContext.day;e.clear();return true;
}
bool Progress::reunite(std::string& e){if(!ready())return fail(e,"original captain reunion requires campaign");mContext.reunited=true;e.clear();return true;}
bool Progress::captainAllowed(unsigned captain,bool wasWild)const{
 if(!ready()||captain>1)return false;
 if(mContext.story&&mContext.day==0&&!mContext.reunited)return captain==0?wasWild:!wasWild;
 return true;
}
bool Progress::restoreContext(const ProgressContext& c,std::string& e){
 if(!ready()||c.campaign!=mState.campaign)return fail(e,"original source context campaign mismatch");
 mContext=c;e.clear();return true;
}
bool Progress::encodeContext(std::string& out,std::string& e)const{
 if(!ready()||mContext.campaign!=mState.campaign)return fail(e,"original source context not initialized");
 std::string b="P2CT1";b+=mContext.campaign;for(unsigned i=0;i<4;++i)b+=char(mContext.day>>(8*i));b+=char(unsigned(mContext.reunited)|(unsigned(mContext.story)<<1));b+=hash(b);out.swap(b);e.clear();return true;
}
bool Progress::decodeContext(const std::string& b,const std::string& campaign,std::string& e){
 if(b.size()!=106||b.substr(0,5)!="P2CT1"||b.substr(5,64)!=campaign||hash(b.substr(0,74))!=b.substr(74)||static_cast<unsigned char>(b[73])>3)return fail(e,"original source context binding/checksum invalid");
 ProgressContext c;c.campaign=campaign;for(unsigned i=0;i<4;++i)c.day|=std::uint32_t(static_cast<unsigned char>(b[69+i]))<<(8*i);c.reunited=b[73]&1;c.story=b[73]&2;return restoreContext(c,e);
}
}
bool pc_p2_original_progress_met(unsigned s){return p2original::originalProgress().met(s);}
bool pc_p2_original_progress_booted(unsigned s){return p2original::originalProgress().booted(s);}
bool pc_p2_original_progress_container(unsigned s){return p2original::originalProgress().container(s);}
bool pc_p2_original_progress_recruited(unsigned s,std::string& e){return p2original::originalProgress().recruited(s,e);}
bool pc_p2_original_progress_hello(unsigned s,std::string& e){return p2original::originalProgress().hello(s,e);}
bool pc_p2_original_progress_boot(unsigned s,std::string& e){return p2original::originalProgress().boot(s,e);}
bool pc_p2_original_progress_discover(unsigned s,std::string& e){return p2original::originalProgress().discover(s,e);}
bool pc_p2_original_progress_captain_allowed(unsigned captain,bool wasWild){return p2original::originalProgress().captainAllowed(captain,wasWild);}
bool pc_p2_original_progress_reunite(std::string& e){return p2original::originalProgress().reunite(e);}
bool pc_p2_original_progress_next_day(std::string& e){return p2original::originalProgress().nextDay(e);}
