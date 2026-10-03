#include "pc_p2_original_catalog.h"
#include "netplay/pc_netplay_sha256.h"
#include <limits>
#include <set>
namespace p2original {
namespace {
bool fail(std::string& e,const char* s){e=s;return false;}
bool fingerprintValid(const std::string& s){if(s.size()!=64)return false;for(char c:s)if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return false;return true;}
bool componentValid(const std::string& s){if(s.empty()||s=="."||s==".."||s.size()>255)return false;for(unsigned char c:s)if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_'||c=='-'||c=='.'))return false;return true;}
bool memberValid(const std::string& s){if(s.empty()||s.size()>2048)return false;size_t begin=0;for(;;){auto end=s.find('/',begin);if(!componentValid(s.substr(begin,end==std::string::npos?end:end-begin)))return false;if(end==std::string::npos)return true;begin=end+1;}}
}
unsigned originalGeneratorUid(const std::string& key){unsigned char bytes[32];pc_netplay_sha::sha256(key.data(),key.size(),bytes);return 0x52000000u|(unsigned(bytes[0])<<16)|(unsigned(bytes[1])<<8)|bytes[2];}
bool Catalog::install(const std::string& fingerprint,const std::vector<CatalogRow>& rows,const Capability& capability,std::string& error){
 if(!mActors.empty()||!mGenerators.empty())return fail(error,"original catalog has live native bindings");
 if(!fingerprintValid(fingerprint)||rows.empty()||rows.size()>65536||!capability)return fail(error,"invalid original catalog envelope");
 std::string candidateFingerprint=fingerprint;
 std::map<unsigned,CatalogRow> candidate;std::set<std::string> keys;
 for(const auto& row:rows){
  if(!componentValid(row.course)||!memberValid(row.member)||row.index>65535||
     row.sourceKey!=row.course+"/"+row.member+"#"+std::to_string(row.index)||
     row.enemy.uid!=originalGeneratorUid(row.sourceKey)||row.enemy.source>65535||row.enemy.count>10||row.enemy.deathCount>row.enemy.count)
   return fail(error,"invalid original catalog row");
  if(!validateOriginalRecord(row.enemy,error))return false;
  if(!keys.insert(row.sourceKey).second||!candidate.emplace(row.enemy.uid,row).second)return fail(error,"duplicate original source key or generator UID");
  // Capability must inspect original source/version/tails/drop semantics;
  // a generic host selector is not an admission implementation.
  if(!capability(row,error))return false;
 }
 mRows.swap(candidate);mFingerprint.swap(candidateFingerprint);error.clear();return true;
}
const CatalogRow* Catalog::find(unsigned uid)const{auto i=mRows.find(uid);return i==mRows.end()?nullptr:&i->second;}
bool Catalog::bindGenerator(const void* pointer,unsigned uid,std::uint64_t& handle,std::string& e){
 if(!pointer||!find(uid)||mGenerators.count(pointer)||mNextHandle==std::numeric_limits<std::uint64_t>::max())return fail(e,"invalid or recycled original generator binding");
 for(const auto& g:mGenerators)if(g.second.uid==uid)return fail(e,"original generator UID already bound");
 auto next=mNextHandle;mGenerators.emplace(pointer,GeneratorBinding{uid,next});++mNextHandle;handle=next;e.clear();return true;
}
bool Catalog::generatorUid(const void* pointer,std::uint64_t handle,unsigned& uid)const{auto i=mGenerators.find(pointer);if(i==mGenerators.end()||!handle||i->second.handle!=handle)return false;uid=i->second.uid;return true;}
bool Catalog::forgetGenerator(const void* pointer,std::uint64_t handle){
 auto i=mGenerators.find(pointer);if(i==mGenerators.end()||!handle||i->second.handle!=handle)return false;
 for(const auto& actor:mActors)if(actor.second.identity.generator==i->second.uid)return false;
 mGenerators.erase(i);return true;
}
bool Catalog::bind(const void* actor,unsigned uid,unsigned ordinal,std::uint64_t epoch,std::uint64_t& handle,std::string& error){
 auto row=find(uid);
 bool generatorPresent=false;for(const auto& g:mGenerators)if(g.second.uid==uid){generatorPresent=true;break;}
 if(!generatorPresent)return fail(error,"original actor has no bound generator");
 if(!actor||!row||!epoch||ordinal>=row->enemy.count||mNextHandle==std::numeric_limits<std::uint64_t>::max())return fail(error,"invalid original instance binding");
 if(mActors.count(actor))return fail(error,"native actor address already bound");
 InstanceIdentity identity{mFingerprint,uid,ordinal,epoch};
 if(mUsed.size()>=1048576||mUsed.count(identity))return fail(error,"original instance identity already used or session capacity exhausted");
 const auto next=mNextHandle;
 auto used=mUsed.insert(identity);
 try{mActors.emplace(actor,Binding{next,identity});}catch(...){mUsed.erase(used.first);throw;}
 ++mNextHandle;handle=next;error.clear();return true;
}
bool Catalog::lookup(const void* actor,std::uint64_t handle,InstanceIdentity& out)const{
 auto i=mActors.find(actor);if(i==mActors.end()||!handle||i->second.handle!=handle)return false;out=i->second.identity;return true;
}
bool Catalog::forget(const void* actor,std::uint64_t handle){auto i=mActors.find(actor);if(i==mActors.end()||!handle||i->second.handle!=handle)return false;mActors.erase(i);return true;}
}
