#include "pc_p2_original_manifest.h"
#include "netplay/pc_netplay_sha256.h"
#include <cstring>
#include <limits>
namespace p2original { namespace {
bool fail(std::string& e,const char* s){e=s;return false;}
std::string hash(const std::string& b){unsigned char h[32];pc_netplay_sha::sha256(b.data(),b.size(),h);return std::string(reinterpret_cast<char*>(h),32);}
void put(std::string& b,unsigned n){for(unsigned i=0;i<4;++i)b.push_back(char(n>>(8*i)));}
void real(std::string& b,float f){unsigned n;static_assert(sizeof(n)==sizeof(f));std::memcpy(&n,&f,4);put(b,n);}
void string(std::string& b,const std::string& s){put(b,unsigned(s.size()));b+=s;}
struct Reader {
 const std::string& b;size_t p=0;bool ok=true;
 unsigned integer(){if(b.size()-p<4){ok=false;return 0;}unsigned n=0;for(unsigned i=0;i<4;++i)n|=unsigned(static_cast<unsigned char>(b[p++]))<<(8*i);return n;}
 float number(){unsigned n=integer();float f;std::memcpy(&f,&n,4);return f;}
 std::string text(unsigned max){unsigned n=integer();if(!ok||n>max||n>b.size()-p){ok=false;return {};}auto s=b.substr(p,n);p+=n;return s;}
};
bool validate(const SourceManifest& m,const std::string& course,std::string& e){
 if(m.rows.size()!=m.literal.size())return fail(e,"original manifest source/state count mismatch");
 Catalog catalog;if(!catalog.install(m.fingerprint,m.rows,[](const CatalogRow&,std::string&){return true;},e))return false;
 std::set<unsigned> seen;
 for(const auto& row:m.rows)if(row.course!=course||row.enemy.deathCount)return fail(e,"original manifest course or source death count invalid");
 for(const auto& s:m.literal){auto* row=catalog.find(s.uid);std::string encoded;
  if(!row||s.count!=row->enemy.count||s.deathCount||s.dayNum||s.epoch||s.activation||!seen.insert(s.uid).second||!encodeOriginalState(m.fingerprint,s,encoded,e))
   return fail(e,"original manifest contains invalid literal lifecycle state");
 }
 e.clear();return true;
}
}
bool writeSourceManifest(const SourceManifest& m,const std::string& course,std::string& out,std::string& e){
 if(!validate(m,course,e))return false;
 std::string b="P2OC1";string(b,m.fingerprint);put(b,unsigned(m.rows.size()));
 std::map<unsigned,GeneratorState> states;for(const auto& s:m.literal)states.emplace(s.uid,s);
 for(const auto& row:m.rows){const auto& x=row.enemy;const auto& s=states.at(x.uid);
  string(b,row.course);string(b,row.member);put(b,row.index);
  put(b,x.source);put(b,x.uid);put(b,x.birthType);put(b,x.count);put(b,x.spawnType);
  for(float f:{x.position.x,x.position.y,x.position.z,x.offset.x,x.offset.y,x.offset.z,x.directionDegrees,x.appearRadius,x.enemySize})real(b,f);
  put(b,unsigned(x.treasureCode));put(b,x.pelletColor);put(b,x.pelletSize);put(b,x.pelletMinimum);put(b,x.pelletMaximum);real(b,x.pelletProbability);
  string(b,x.generatorVersion);put(b,unsigned(x.generatorTail.size()));for(const auto& t:x.generatorTail)string(b,t);
  put(b,s.reserved);put(b,unsigned(s.resurrectionDays));put(b,unsigned(s.dayLimit));
 }
 if(b.size()>4*1024*1024-32)return fail(e,"original manifest exceeds private sidecar bound");
 b+=hash(b);out.swap(b);e.clear();return true;
}
bool readSourceManifest(const std::string& bytes,const std::string& course,SourceManifest& out,std::string& e){
 if(bytes.size()<45||bytes.size()>4*1024*1024||bytes.substr(0,5)!="P2OC1")return fail(e,"original manifest envelope invalid");
 std::string payload=bytes.substr(0,bytes.size()-32);
 if(hash(payload)!=bytes.substr(bytes.size()-32))return fail(e,"original manifest checksum mismatch");
 Reader r{payload};r.p=5;SourceManifest next;next.fingerprint=r.text(64);unsigned count=r.integer();
 if(!r.ok||!count||count>65536)return fail(e,"original manifest count invalid");
 for(unsigned i=0;i<count&&r.ok;++i){CatalogRow row;auto& x=row.enemy;
  row.course=r.text(255);row.member=r.text(2048);row.index=r.integer();row.sourceKey=row.course+"/"+row.member+"#"+std::to_string(row.index);
  x.source=r.integer();x.uid=r.integer();x.birthType=r.integer();x.count=r.integer();x.spawnType=r.integer();
  x.position={r.number(),r.number(),r.number()};x.offset={r.number(),r.number(),r.number()};x.directionDegrees=r.number();x.appearRadius=r.number();x.enemySize=r.number();
  const unsigned treasure=r.integer();x.treasureCode=treasure<=unsigned(std::numeric_limits<int>::max())?int(treasure):int(std::int64_t(treasure)-0x100000000LL);
  x.pelletColor=r.integer();x.pelletSize=r.integer();x.pelletMinimum=r.integer();x.pelletMaximum=r.integer();x.pelletProbability=r.number();
  x.generatorVersion=r.text(4);unsigned tails=r.integer();if(tails>4096)return fail(e,"original manifest opaque tail bound exceeded");
  for(unsigned t=0;t<tails&&r.ok;++t)x.generatorTail.push_back(r.text(4096));
  GeneratorState s;s.uid=x.uid;s.count=x.count;s.reserved=r.integer();
  const unsigned respawn=r.integer(),limit=r.integer();
  s.resurrectionDays=respawn<=unsigned(std::numeric_limits<int>::max())?int(respawn):int(std::int64_t(respawn)-0x100000000LL);
  s.dayLimit=limit<=unsigned(std::numeric_limits<int>::max())?int(limit):int(std::int64_t(limit)-0x100000000LL);
  next.rows.push_back(std::move(row));next.literal.push_back(s);
 }
 if(!r.ok||r.p!=payload.size())return fail(e,"original manifest truncated or has trailing source data");
 if(!validate(next,course,e))return false;
 out=std::move(next);e.clear();return true;
}
}
