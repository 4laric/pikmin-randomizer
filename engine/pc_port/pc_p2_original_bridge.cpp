#include <sstream>
#include "pc_p2_original_bridge.h"
#include "netplay/pc_netplay_sha256.h"
#include <cmath>
#include <cstring>
#include <fstream>
#include <set>
namespace p2original {
namespace {
bool fail(std::string& e,const char* why){e=why;return false;}
void word(std::vector<std::uint8_t>& b,std::uint32_t v){for(int i=0;i<4;++i)b.push_back(std::uint8_t(v>>(8*i)));}
std::uint32_t word(const std::vector<std::uint8_t>& b,std::size_t at){std::uint32_t v=0;for(int i=0;i<4;++i)v|=std::uint32_t(b[at+i])<<(8*i);return v;}
void number(std::vector<std::uint8_t>& b,float f){std::uint32_t v;std::memcpy(&v,&f,4);word(b,v);}
float number(const std::vector<std::uint8_t>& b,std::size_t at){auto v=word(b,at);float f;std::memcpy(&f,&v,4);return f;}
}
int bridgeStageCount(int type){return type==0||type==1?6:type==2?15:0;}
bool validateBridge(const BridgeRecord& r,std::string& e){
 if(r.sourceKey.empty()||r.sourceKey.size()>2048||r.sourceSha.size()!=64)return fail(e,"invalid bridge source identity");
 for(char c:r.sourceSha)if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return fail(e,"invalid bridge source hash");
 auto slash=r.sourceKey.find('/'),hash=r.sourceKey.rfind('#');
 if(slash==std::string::npos||hash==std::string::npos||slash==0||hash<=slash+1||hash+1==r.sourceKey.size())return fail(e,"invalid bridge source key");
 for(std::size_t i=0;i<r.sourceKey.size();++i){char c=r.sourceKey[i];if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='/'||c=='.'||c=='_'||c=='-'||c=='#'))return fail(e,"invalid bridge key character");if(i>hash&&(c<'0'||c>'9'))return fail(e,"invalid bridge index");}
 unsigned char digest[32];pc_netplay_sha::sha256(r.sourceKey.data(),r.sourceKey.size(),digest);
 if(r.uid!=(0x52000000u|(unsigned(digest[0])<<16)|(unsigned(digest[1])<<8)|digest[2]))return fail(e,"bridge UID/source mismatch");
 if(!bridgeStageCount(r.type)||!std::isfinite(r.stageLife)||r.stageLife<=0)return fail(e,"unsupported bridge type/life");
 if(r.reserved!=3||r.resurrectionDays!=0||r.dayLimit< -1)return fail(e,"unsupported bridge cache/schedule");
 for(unsigned i=0;i<3;++i)if(!std::isfinite(r.position[i])||!std::isfinite(r.offset[i])||!std::isfinite(r.position[i]+r.offset[i])||!std::isfinite(r.rotation[i]))return fail(e,"nonfinite bridge placement");
 e.clear();return true;
}
std::string bridgeDigest(const BridgeRecord& r){
 std::vector<std::uint8_t> bytes(r.sourceSha.begin(),r.sourceSha.end());bytes.push_back(':');bytes.insert(bytes.end(),r.sourceKey.begin(),r.sourceKey.end());
 word(bytes,r.uid);word(bytes,r.reserved);word(bytes,std::uint32_t(r.resurrectionDays));word(bytes,std::uint32_t(r.dayLimit));word(bytes,r.type);number(bytes,r.stageLife);
 for(const auto* a:{&r.position,&r.offset,&r.rotation})for(float f:*a)number(bytes,f);
 unsigned char digest[32];pc_netplay_sha::sha256(bytes.data(),bytes.size(),digest);std::string out;const char* hex="0123456789abcdef";for(auto c:digest){out+=hex[c>>4];out+=hex[c&15];}return out;
}
static bool parseBridgesStream(std::istream& in,std::vector<BridgeRecord>& out,std::string& e){
 std::string magic;unsigned count=0;if(!(in>>magic>>count)||magic!="P2_ORIGINAL_BRIDGE_1"||count>4096)return fail(e,"invalid bridge manifest");
 std::vector<BridgeRecord> next;std::set<unsigned> seen;std::set<std::string> keys;
 for(unsigned i=0;i<count;++i){BridgeRecord r;std::string object,local;if(!(in>>r.uid>>r.sourceKey>>r.sourceSha>>object>>local>>r.reserved>>r.resurrectionDays>>r.dayLimit>>r.type>>r.stageLife))return fail(e,"truncated bridge source");
  for(auto* a:{&r.position,&r.offset,&r.rotation})for(float& f:*a)if(!(in>>f))return fail(e,"truncated bridge placement");
  if(object!="0002"||local!="0001"||!validateBridge(r,e))return fail(e,"unsupported bridge source");if(!seen.insert(r.uid).second||!keys.insert(r.sourceKey).second)return fail(e,"duplicate bridge source");next.push_back(r);
 }
 if(in>>magic)return fail(e,"trailing bridge source");out.swap(next);e.clear();return true;
}
bool readBridges(const std::string& path,std::vector<BridgeRecord>& out,std::string& e){std::ifstream input(path);return parseBridgesStream(input,out,e);}
bool parseBridges(const std::string& bytes,std::vector<BridgeRecord>& out,std::string& e){
 if(bytes.empty()||bytes.size()>4*1024*1024)return fail(e,"original typed item input bound invalid");std::istringstream input(bytes);return parseBridgesStream(input,out,e);
}
BridgeState bridgeInitial(const BridgeRecord& r){BridgeState s;for(int i=0;i<bridgeStageCount(r.type);++i)s.health[i]=r.stageLife;return s;}
bool bridgeStateValid(const BridgeRecord& r,const BridgeState& s,std::string& e){
 if(!validateBridge(r,e))return false;int count=bridgeStageCount(r.type);
 if(s.stage<0||s.stage>count||s.extensionTicks>40||(s.stage==count&&s.extensionTicks))return fail(e,"invalid bridge stage/delay");
 // Breaking an earlier built section retains partial work in later sections.
 for(int i=0;i<15;++i){float h=s.health[i];if(!std::isfinite(h)||h>r.stageLife||(i>=count&&h!=0)||(i<s.stage&&h>=r.stageLife)||(i==s.stage&&i<count&&s.extensionTicks!=0&&h>0))return fail(e,"invalid bridge stage health");}
 e.clear();return true;
}
bool bridgeAttack(const BridgeRecord& r,BridgeState& s,float damage){
 if(!std::isfinite(damage)||damage<=0)return false;if(s.extensionTicks)return true;if(s.stage==bridgeStageCount(r.type))return false;
 if(!std::isfinite(s.health[s.stage]-damage))return false;s.health[s.stage]-=damage;if(s.health[s.stage]<=0)s.extensionTicks=40;return true;
}
bool bridgeTick(const BridgeRecord&,BridgeState& s){if(!s.extensionTicks)return false;if(--s.extensionTicks)return false;++s.stage;return true;}
bool bridgeBreak(const BridgeRecord& r,BridgeState& s,float damage){
 if(s.extensionTicks||s.stage==0||!std::isfinite(damage)||damage<=0)return false;
 int i=s.stage-1;float next=s.health[i]+damage;if(!std::isfinite(next))return false;s.health[i]=next;if(s.health[i]>=r.stageLife){s.health[i]=r.stageLife;--s.stage;}return false; // retail returns false even after changing geometry
}
bool bridgeExport(const BridgeRecord& r,const BridgeState& s,std::vector<std::uint8_t>& out,std::string& e){
 if(!bridgeStateValid(r,s,e))return false;std::vector<std::uint8_t> b={'B','S','0','1'};auto d=bridgeDigest(r);b.insert(b.end(),d.begin(),d.end());word(b,s.stage);word(b,s.extensionTicks);for(float f:s.health)number(b,f);unsigned char checksum[32];pc_netplay_sha::sha256(b.data(),b.size(),checksum);b.insert(b.end(),checksum,checksum+32);out.swap(b);return true;
}
bool bridgeImport(const BridgeRecord& r,const std::vector<std::uint8_t>& b,BridgeState& out,std::string& e){
 if(b.size()!=168||std::memcmp(b.data(),"BS01",4))return fail(e,"invalid bridge snapshot envelope");unsigned char checksum[32];pc_netplay_sha::sha256(b.data(),136,checksum);if(std::memcmp(checksum,b.data()+136,32))return fail(e,"bridge snapshot checksum mismatch");auto digest=bridgeDigest(r);if(std::memcmp(digest.data(),b.data()+4,64))return fail(e,"bridge snapshot source mismatch");BridgeState s;s.stage=int(word(b,68));s.extensionTicks=word(b,72);for(int i=0;i<15;++i)s.health[i]=number(b,76+4*i);if(!bridgeStateValid(r,s,e))return false;out=s;e.clear();return true;
}
std::array<float,3> bridgeStagePosition(const BridgeRecord& r,int stage){
 float first=r.type==1?12.5f:42.5f;float z=(stage>0?(stage-1)*20.0f+first:-20.0f)-10.0f;float yaw=r.rotation[1]*0.017453292519943295f;
 return {r.position[0]+r.offset[0]+std::sin(yaw)*z,r.position[1]+r.offset[1]+(stage>=1&&r.type==1?(stage-1)*8.0f:0),r.position[2]+r.offset[2]+std::cos(yaw)*z};
}
}
