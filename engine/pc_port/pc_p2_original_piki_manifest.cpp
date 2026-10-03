#include "pc_p2_original_piki_manifest.h"
#include "pc_p2_original_source_uid.h"
#include "netplay/pc_netplay_sha256.h"
#include <cmath>
#include <cstring>
#include <set>
#include <regex>
namespace p2original {namespace {
bool fail(std::string& e,const char* s){e=s;return false;}
bool fp(const std::string& s){if(s.size()!=64)return false;for(char c:s)if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return false;return true;}
std::string hash(const std::string& b,bool hex=false){unsigned char d[32];pc_netplay_sha::sha256(b.data(),b.size(),d);if(!hex)return std::string(reinterpret_cast<char*>(d),32);std::string out;for(auto c:d){out+="0123456789abcdef"[c>>4];out+="0123456789abcdef"[c&15];}return out;}
void put(std::string& b,unsigned n){for(unsigned i=0;i<4;++i)b+=char(n>>(8*i));}
void text(std::string& b,const std::string& s){put(b,unsigned(s.size()));b+=s;}
void real(std::string& b,float f){unsigned n;std::memcpy(&n,&f,4);put(b,n);}
struct Reader {const std::string& b;size_t p=0;bool ok=true;
 unsigned integer(){if(b.size()-p<4){ok=false;return 0;}unsigned n=0;for(unsigned i=0;i<4;++i)n|=unsigned(static_cast<unsigned char>(b[p++]))<<(8*i);return n;}
 int signedInteger(){auto n=integer();return n<=0x7fffffffu?int(n):int(std::int64_t(n)-0x100000000LL);}
 float number(){unsigned n=integer();float f;std::memcpy(&f,&n,4);return f;}
 std::string fixed(unsigned n){if(n>b.size()-p){ok=false;return {};}auto s=b.substr(p,n);p+=n;return s;}
 std::string string(unsigned limit){auto n=integer();if(!ok||n>limit){ok=false;return {};}return fixed(n);}
};
bool encodeRows(const std::vector<PikiSourceRecord>& rows,std::string& b,std::string& e){
 if(rows.empty()||rows.size()>65536)return fail(e,"original Piki manifest count invalid");
 std::set<unsigned> uids;std::string previous;
 for(const auto& row:rows){if(!validatePikiSource(row,e))return false;
  if((!previous.empty()&&row.sourceKey<=previous)||!uids.insert(row.spawn.uid).second)return fail(e,"original Piki manifest order/UID collision invalid");previous=row.sourceKey;
  text(b,row.sourceKey);b+=row.sourceSha;b+=row.recordVersion;b+=row.objectVersion;
  for(unsigned n:{row.spawn.uid,row.spawn.count,unsigned(row.spawn.species),unsigned(row.spawn.wildParameter),row.reserved,unsigned(row.resurrectionDays),unsigned(row.dayLimit)})put(b,n);
  for(float f:row.spawn.position)real(b,f);for(float f:row.spawn.offset)real(b,f);
 }
 return true;
}

}
bool validatePikiSource(const PikiSourceRecord& row,std::string& e){
 const auto& key=row.sourceKey;auto hashAt=key.rfind('#');
 if(key.find("/nonloop/")!=std::string::npos){
  static const std::regex calendar("^[a-z]+/nonloop/([0-9]+)-([0-9]+)\\.txt#[0-9]+$");std::smatch match;
  if(!std::regex_match(key,match,calendar))return fail(e,"original Piki calendar path invalid");unsigned begin=0,end=0;
  for(unsigned part=1;part<=2;++part){unsigned n=0;for(char c:match[part].str()){if(n>3276||(n==3276&&c>'7'))return fail(e,"original Piki calendar day outside bound");n=n*10+unsigned(c-'0');}if(part==1)begin=n;else end=n;}
  if(begin>end)return fail(e,"original Piki calendar range reversed");
 }
 if(key.empty()||key.size()>256||hashAt==std::string::npos||hashAt+1==key.size()||!fp(row.sourceSha))return fail(e,"original Piki source identity invalid");
 unsigned index=0;for(size_t i=hashAt+1;i<key.size();++i){if(key[i]<'0'||key[i]>'9')return fail(e,"original Piki source index invalid");index=index*10+unsigned(key[i]-'0');if(index>65535)return fail(e,"original Piki source index exceeds bound");}
 if(key.substr(hashAt+1)!=std::to_string(index))return fail(e,"original Piki source index not canonical");
 size_t begin=0;unsigned parts=0;for(size_t i=0;i<=hashAt;++i)if(i==hashAt||key[i]=='/'){
  auto component=key.substr(begin,i-begin);if(component.empty()||component=="."||component=="..")return fail(e,"original Piki source path invalid");
  for(char c:component)if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_'||c=='-'||c=='.'))return fail(e,"original Piki source path character invalid");
  begin=i+1;++parts;
 }
 if(parts<2||row.spawn.uid!=originalSourceCatalogUid(key)||row.spawn.count>65535||row.spawn.species<0||row.spawn.species>5||row.reserved>65535||row.resurrectionDays< -32768||row.resurrectionDays>32767||row.dayLimit< -32768||row.dayLimit>32767||row.objectVersion!="0001"||(row.recordVersion!="v0.1"&&row.recordVersion!="v0.2"&&row.recordVersion!="v0.3"))return fail(e,"original Piki literal version/common field invalid");
 for(unsigned i=0;i<3;++i)if(!std::isfinite(row.spawn.position[i])||!std::isfinite(row.spawn.offset[i])||!std::isfinite(row.spawn.position[i]+row.spawn.offset[i]))return fail(e,"original Piki transform invalid");
 e.clear();return true;
}
bool writePikiManifest(const PikiManifest& m,std::string& out,std::string& e){
 if(!fp(m.campaign))return fail(e,"original Piki campaign invalid");
 std::string rows;if(!encodeRows(m.rows,rows,e))return false;auto catalog=hash(rows,true);
 if(!m.catalog.empty()&&catalog!=m.catalog)return fail(e,"original Piki immutable catalog digest changed");
 std::string b="P2PK1";b+=m.campaign;b+=catalog;put(b,unsigned(m.rows.size()));b+=rows;
 if(b.size()>4*1024*1024-32)return fail(e,"original Piki manifest exceeds bound");b+=hash(b);out.swap(b);e.clear();return true;
}
bool readPikiManifest(const std::string& b,PikiManifest& out,std::string& e){
 if(b.size()<169||b.size()>4*1024*1024||b.substr(0,5)!="P2PK1"||hash(b.substr(0,b.size()-32))!=b.substr(b.size()-32))return fail(e,"original Piki manifest envelope invalid");
 std::string payload=b.substr(0,b.size()-32);Reader r{payload};r.p=5;PikiManifest next;next.campaign=r.fixed(64);next.catalog=r.fixed(64);unsigned count=r.integer();if(!r.ok||!count||count>65536)return fail(e,"original Piki manifest count invalid");
 for(unsigned i=0;i<count&&r.ok;++i){PikiSourceRecord row;row.sourceKey=r.string(256);row.sourceSha=r.fixed(64);row.recordVersion=r.fixed(4);row.objectVersion=r.fixed(4);
  row.spawn.uid=r.integer();row.spawn.count=r.integer();row.spawn.species=r.signedInteger();row.spawn.wildParameter=r.signedInteger();row.reserved=r.integer();row.resurrectionDays=r.signedInteger();row.dayLimit=r.signedInteger();for(float& f:row.spawn.position)f=r.number();for(float& f:row.spawn.offset)f=r.number();next.rows.push_back(row);
 }
 if(!r.ok||r.p!=payload.size())return fail(e,"original Piki manifest truncated/trailing bytes");
 std::string checked;if(!writePikiManifest(next,checked,e)||checked!=b)return fail(e,"original Piki manifest catalog binding invalid");out=std::move(next);e.clear();return true;
}
bool writePikiActive(const PikiManifest& m,const std::string& course,unsigned day,const std::vector<unsigned>& active,std::string& out,std::string& e){
 std::string atlas;if(!writePikiManifest(m,atlas,e)||!fp(m.catalog)||course.empty()||course.size()>32)return fail(e,"original active Piki authority invalid");
 for(char c:course)if(c<'a'||c>'z')return fail(e,"original active Piki course invalid");
 if(active.size()>m.rows.size())return fail(e,"original active Piki count invalid");
 std::string b="P2PA1";b+=m.campaign;b+=m.catalog;text(b,course);put(b,day);put(b,unsigned(active.size()));unsigned previous=0;
 for(unsigned uid:active){const PikiSourceRecord* found=nullptr;for(const auto& r:m.rows)if(r.spawn.uid==uid){found=&r;break;}
  if(!found||uid<=previous||found->sourceKey.compare(0,course.size()+1,course+"/"))return fail(e,"original active Piki source/order/course invalid");previous=uid;put(b,uid);
 }
 b+=hash(b);out.swap(b);e.clear();return true;
}
bool readPikiActive(const std::string& b,const PikiManifest& m,const std::string& course,unsigned day,std::vector<unsigned>& out,std::string& e){
 if(b.size()<177||b.size()>300000||b.substr(0,5)!="P2PA1"||hash(b.substr(0,b.size()-32))!=b.substr(b.size()-32))return fail(e,"original active Piki envelope invalid");
 std::string payload=b.substr(0,b.size()-32);Reader r{payload};r.p=5;
 if(r.fixed(64)!=m.campaign||r.fixed(64)!=m.catalog||r.string(32)!=course||r.integer()!=day)return fail(e,"original active Piki selected authority mismatch");
 unsigned count=r.integer();if(!r.ok||count>m.rows.size())return fail(e,"original active Piki count invalid");std::vector<unsigned> next;for(unsigned i=0;i<count&&r.ok;++i)next.push_back(r.integer());
 if(!r.ok||r.p!=payload.size())return fail(e,"original active Piki truncated/trailing data");std::string checked;
 if(!writePikiActive(m,course,day,next,checked,e)||checked!=b)return false;out.swap(next);e.clear();return true;
}
}
