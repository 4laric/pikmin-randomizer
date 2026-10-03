#include <sstream>
#include "pc_p2_original_onyon.h"
#include "netplay/pc_netplay_sha256.h"
#include <cmath>
#include <fstream>
#include <set>
#include <cstring>
#include <sstream>
namespace p2original {
namespace {bool fail(std::string& e,const char* s){e=s;return false;}}
bool validateOnyon(const OnyonRecord& r,std::string& e){
 if(r.sourceKey.empty()||r.sourceKey.size()>2048||r.sourceSha.size()!=64)return fail(e,"invalid original onyn source identity");
 for(char c:r.sourceSha)if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return fail(e,"invalid onyn source hash");
 auto slash=r.sourceKey.find('/'),hash=r.sourceKey.rfind('#');
 if(slash==std::string::npos||hash==std::string::npos||slash==0||hash<=slash+1||hash+1==r.sourceKey.size())return fail(e,"invalid onyn source key");
 for(std::size_t i=0;i<r.sourceKey.size();++i){char c=r.sourceKey[i];if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='/'||c=='.'||c=='_'||c=='-'||c=='#'))return fail(e,"invalid onyn key character");if(i>hash&&(c<'0'||c>'9'))return fail(e,"invalid onyn record index");}
 unsigned char bytes[32];pc_netplay_sha::sha256(r.sourceKey.data(),r.sourceKey.size(),bytes);
 auto uid=0x52000000u|(unsigned(bytes[0])<<16)|(unsigned(bytes[1])<<8)|bytes[2];
 if(r.uid!=uid)return fail(e,"onyn UID/source key mismatch");
 if((r.index<0||r.index>2)&&r.index!=4)return fail(e,"unsupported original onyn index (pod has no native provider)");
 if(r.afterBoot<0||r.afterBoot>1||r.resurrectionDays<0||r.dayLimit< -1)return fail(e,"invalid original onyn tail/schedule");
 if(r.reserved!=0||r.resurrectionDays!=0)return fail(e,"onyn nondefault cache/respawn schedule requires a separate provider");
 for(unsigned i=0;i<3;++i)if(!std::isfinite(r.position[i])||!std::isfinite(r.offset[i])||!std::isfinite(r.position[i]+r.offset[i])||!std::isfinite(r.rotation[i]))return fail(e,"nonfinite original onyn transform");
 // Retail factory consumes only angle.y; x/z are authored metadata, never discarded.
 e.clear();return true;
}
bool onyonEligible(const OnyonRecord& r,std::uint8_t containers){return r.index==4||bool(containers&(1u<<r.index))==bool(r.afterBoot);}
std::string onyonDigest(const OnyonRecord& r){
 std::string bytes=r.sourceSha+":"+r.sourceKey;
 auto word=[&](std::uint32_t v){for(unsigned i=0;i<4;++i)bytes.push_back(char(v>>(8*i)));};
 word(r.uid);word(r.reserved);word(std::uint32_t(r.resurrectionDays));word(std::uint32_t(r.dayLimit));word(std::uint32_t(r.index));word(std::uint32_t(r.afterBoot));
 for(const auto* a:{&r.position,&r.offset,&r.rotation})for(float f:*a){std::uint32_t v;static_assert(sizeof(v)==sizeof(f),"IEEE float width");std::memcpy(&v,&f,4);word(v);}
 unsigned char digest[32];pc_netplay_sha::sha256(bytes.data(),bytes.size(),digest);
 std::string result;const char* hex="0123456789abcdef";for(unsigned char c:digest){result.push_back(hex[c>>4]);result.push_back(hex[c&15]);}return result;
}
bool readOnyonsFromBytes(const std::string& bytes,std::vector<OnyonRecord>& out,std::string& e){
 if(bytes.empty()||bytes.size()>4u*1024u*1024u)return fail(e,"empty or oversized original onyn manifest");
 std::istringstream in(bytes);std::string magic;unsigned n=0;
 if(!(in>>magic>>n)||magic!="P2_ORIGINAL_ONYON_1"||!n||n>4096)return fail(e,"invalid original onyn manifest envelope");
 std::vector<OnyonRecord> rows;std::set<unsigned> uids;std::set<std::string> keys;
 for(unsigned i=0;i<n;++i){OnyonRecord r;std::string object,local;
  if(!(in>>r.uid>>r.sourceKey>>r.sourceSha>>object>>local>>r.reserved>>r.resurrectionDays>>r.dayLimit>>r.index>>r.afterBoot))return fail(e,"truncated original onyn identity/tail");
  for(float& x:r.position)if(!(in>>x))return fail(e,"truncated onyn position");
  for(float& x:r.offset)if(!(in>>x))return fail(e,"truncated onyn offset");
  for(float& x:r.rotation)if(!(in>>x))return fail(e,"truncated onyn rotation");
  if(object!="0002"||local!="0001"||!validateOnyon(r,e))return fail(e,"unsupported or invalid original onyn source version/tail");
  if(!uids.insert(r.uid).second||!keys.insert(r.sourceKey).second)return fail(e,"duplicate original onyn identity");rows.push_back(r);
 }
 if(in>>magic)return fail(e,"trailing original onyn manifest data");
 out.swap(rows);e.clear();return true;
}
bool readOnyons(const std::string& path,std::vector<OnyonRecord>& out,std::string& e){
 std::ifstream in(path,std::ios::binary);if(!in)return fail(e,"original onyn manifest unavailable");
 std::string bytes;char buffer[4096];
 while(in.read(buffer,sizeof(buffer))||in.gcount()){
  const auto size=static_cast<std::size_t>(in.gcount());
  if(size>4u*1024u*1024u-bytes.size())return fail(e,"oversized original onyn manifest");
  bytes.append(buffer,size);
 }
 if(!in.eof())return fail(e,"original onyn manifest read failed");
 return readOnyonsFromBytes(bytes,out,e);
}
bool parseOnyons(const std::string& bytes,std::vector<OnyonRecord>& out,std::string& e){return readOnyonsFromBytes(bytes,out,e);}

}
