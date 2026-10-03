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
 if(!ready())mState.campaign=campaign;e.clear();return true;
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
 mState=s;e.clear();return true;
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
}
bool pc_p2_original_progress_met(unsigned s){return p2original::originalProgress().met(s);}
bool pc_p2_original_progress_booted(unsigned s){return p2original::originalProgress().booted(s);}
bool pc_p2_original_progress_container(unsigned s){return p2original::originalProgress().container(s);}
bool pc_p2_original_progress_recruited(unsigned s,std::string& e){return p2original::originalProgress().recruited(s,e);}
bool pc_p2_original_progress_hello(unsigned s,std::string& e){return p2original::originalProgress().hello(s,e);}
bool pc_p2_original_progress_boot(unsigned s,std::string& e){return p2original::originalProgress().boot(s,e);}
bool pc_p2_original_progress_discover(unsigned s,std::string& e){return p2original::originalProgress().discover(s,e);}
