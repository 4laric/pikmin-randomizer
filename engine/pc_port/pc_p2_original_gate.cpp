#include <sstream>
#include "pc_p2_original_gate.h"
#include "netplay/pc_netplay_sha256.h"
#include <cmath>
#include <fstream>
#include <set>
#include <cstring>
namespace p2original {
namespace {bool fail(std::string& e,const char* s){e=s;return false;}}
bool validateGate(const GateRecord& r,std::string& e){
 if(r.sourceKey.empty()||r.sourceKey.size()>2048||r.sourceSha.size()!=64)return fail(e,"invalid original gate source identity");
 for(char c:r.sourceSha)if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return fail(e,"invalid gate source hash");
 auto slash=r.sourceKey.find('/'),hash=r.sourceKey.rfind('#');
 if(slash==std::string::npos||hash==std::string::npos||slash==0||hash<=slash+1||hash+1==r.sourceKey.size())return fail(e,"invalid gate source key");
 for(std::size_t i=0;i<r.sourceKey.size();++i){char c=r.sourceKey[i];if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='/'||c=='.'||c=='_'||c=='-'||c=='#'))return fail(e,"invalid gate key character");if(i>hash&&(c<'0'||c>'9'))return fail(e,"invalid gate record index");}
 unsigned char bytes[32];pc_netplay_sha::sha256(r.sourceKey.data(),r.sourceKey.size(),bytes);
 auto uid=0x52000000u|(unsigned(bytes[0])<<16)|(unsigned(bytes[1])<<8)|bytes[2];
 if(r.uid!=uid)return fail(e,"gate UID/source key mismatch");
 if(r.color<0||r.color>1||!std::isfinite(r.segmentLife)||r.segmentLife<=0||!std::isfinite(r.segmentLife*3))return fail(e,"unsupported original gate color/life");
 if(r.resurrectionDays<0||r.dayLimit< -1)return fail(e,"invalid original gate tail/schedule");
 if(r.reserved!=3||r.resurrectionDays!=0)return fail(e,"gate nondefault cache/respawn schedule requires a separate provider");
 for(unsigned i=0;i<3;++i)if(!std::isfinite(r.position[i])||!std::isfinite(r.offset[i])||!std::isfinite(r.position[i]+r.offset[i])||!std::isfinite(r.rotation[i]))return fail(e,"nonfinite original gate transform");
 // Retail factory consumes only angle.y; x/z are authored metadata, never discarded.
 e.clear();return true;
}
std::string gateDigest(const GateRecord& r){
 std::string bytes=r.sourceSha+":"+r.sourceKey;
 auto word=[&](std::uint32_t v){for(unsigned i=0;i<4;++i)bytes.push_back(char(v>>(8*i)));};
 word(r.uid);word(r.reserved);word(std::uint32_t(r.resurrectionDays));word(std::uint32_t(r.dayLimit));word(std::uint32_t(r.color));{std::uint32_t v;std::memcpy(&v,&r.segmentLife,4);word(v);}
 for(const auto* a:{&r.position,&r.offset,&r.rotation})for(float f:*a){std::uint32_t v;static_assert(sizeof(v)==sizeof(f),"IEEE float width");std::memcpy(&v,&f,4);word(v);}
 unsigned char digest[32];pc_netplay_sha::sha256(bytes.data(),bytes.size(),digest);
 std::string result;const char* hex="0123456789abcdef";for(unsigned char c:digest){result.push_back(hex[c>>4]);result.push_back(hex[c&15]);}return result;
}
static bool parseGatesStream(std::istream& in,std::vector<GateRecord>& out,std::string& e){
 std::string magic;unsigned n=0;
 if(!(in>>magic>>n)||magic!="P2_ORIGINAL_GATE_1"||!n||n>4096)return fail(e,"invalid original gate manifest envelope");
 std::vector<GateRecord> rows;std::set<unsigned> uids;std::set<std::string> keys;
 for(unsigned i=0;i<n;++i){GateRecord r;std::string object,local;
  if(!(in>>r.uid>>r.sourceKey>>r.sourceSha>>object>>local>>r.reserved>>r.resurrectionDays>>r.dayLimit>>r.segmentLife>>r.color))return fail(e,"truncated original gate identity/tail");
  for(float& x:r.position)if(!(in>>x))return fail(e,"truncated gate position");
  for(float& x:r.offset)if(!(in>>x))return fail(e,"truncated gate offset");
  for(float& x:r.rotation)if(!(in>>x))return fail(e,"truncated gate rotation");
  if(object!="0002"||local!="0002"||!validateGate(r,e))return fail(e,"unsupported or invalid original gate source version/tail");
  if(!uids.insert(r.uid).second||!keys.insert(r.sourceKey).second)return fail(e,"duplicate original gate identity");rows.push_back(r);
 }
 if(in>>magic)return fail(e,"trailing original gate manifest data");
 out.swap(rows);e.clear();return true;
}
bool readGates(const std::string& path,std::vector<GateRecord>& out,std::string& e){std::ifstream input(path);return parseGatesStream(input,out,e);}
bool parseGates(const std::string& bytes,std::vector<GateRecord>& out,std::string& e){
 if(bytes.empty()||bytes.size()>4*1024*1024)return fail(e,"original typed item input bound invalid");std::istringstream input(bytes);return parseGatesStream(input,out,e);
}
}
