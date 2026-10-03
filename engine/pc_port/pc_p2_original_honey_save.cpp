#include "pc_p2_original_honey_save.h"
#include "pc_p2_original_honey_bank_validation.h"
#include <iomanip>
#include <limits>
#include <set>
namespace p2originalresource { namespace honey { namespace {
bool fail(std::string& e){e="invalid original Honey save payload";return false;}
bool hash(const std::string& s){if(s.size()!=64)return false;for(char c:s)if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return false;return true;}
bool finite(P2EggVec3 p){return std::isfinite(p.x)&&std::isfinite(p.y)&&std::isfinite(p.z);}
bool validate(const std::vector<Snapshot>& rows,const std::string& campaign,const std::string& bank,const std::array<ReceiverClip,7>& clips,const EggContents& contents,std::string& e){
 if(rows.size()>4096||!hash(campaign)||!hash(bank))return fail(e);
 for(const auto& row:rows)if(!row.identity.ancestry.empty())return fail(e);
 const auto records=contents.snapshot();EggContents checked;if(!checked.restore(records,e))return false;
 std::map<std::pair<SourceIdentity,unsigned>,ChildOutcome> children;for(const auto& r:records){if(!r.complete)return fail(e);for(const auto& c:r.children)children.emplace(std::make_pair(c.identity.source,c.identity.slot),c);}
 std::set<std::pair<SourceIdentity,unsigned>> seen;unsigned live=0;
 for(const auto& row:rows){auto id=std::make_pair(row.identity.source,row.identity.slot);auto child=children.find(id);
  if(!hash(row.identity.source.fingerprint)||!seen.insert(id).second||child==children.end()||!child->second.born||!child->second.attempted||static_cast<int>(row.kind)<0||static_cast<int>(row.kind)>2||static_cast<int>(row.phase)<0||row.phase>Phase::Dead||!finite(row.position)||!finite(row.velocity))return fail(e);
  const ChildKind kinds[]={ChildKind::Nectar,ChildKind::Spicy,ChildKind::Bitter};if(child->second.kind!=kinds[static_cast<unsigned>(row.kind)]||child->second.consumed!=row.firstConsumption)return fail(e);
  if(row.phase==Phase::Shrink&&!row.firstConsumption)return fail(e);
  if(row.firstConsumption&&row.phase!=Phase::Shrink&&row.phase!=Phase::Dead)return fail(e);
  if(row.phase==Phase::Dead){if(!row.animation.empty())return fail(e);}else {if(++live>24)return fail(e);unsigned motion;ReceiverClock clock;if(!animationSnapshot(row.animation,bank,row.phase,clips,motion,clock,e))return false;}
 }
 for(const auto& entry:children){const auto& child=entry.second;if(child.born&&(child.kind==ChildKind::Nectar||child.kind==ChildKind::Spicy||child.kind==ChildKind::Bitter)&&!seen.count(entry.first))return fail(e);}
 e.clear();return true;
}
std::string hex(const std::string& bytes){if(bytes.empty())return "-";std::string s;for(unsigned char c:bytes){s+="0123456789abcdef"[c>>4];s+="0123456789abcdef"[c&15];}return s;}
bool unhex(const std::string& token,std::string& out){if(token=="-"){out.clear();return true;}if(token.size()>512||token.empty()||token.size()%2)return false;std::string s;auto nibble=[](char c){return c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:-1;};for(std::size_t i=0;i<token.size();i+=2){int a=nibble(token[i]),b=nibble(token[i+1]);if(a<0||b<0)return false;s+=char(a*16+b);}out=std::move(s);return true;}
template<class T>bool integer(std::istream& in,T& out){std::string s;if(!(in>>s)||s.empty()||(s.size()>1&&s[0]=='0'))return false;T value=0;for(char c:s){if(c<'0'||c>'9'||value>(std::numeric_limits<T>::max()-T(c-'0'))/10)return false;value=value*10+T(c-'0');}out=value;return true;}
bool number(std::istream& in,float& out){std::string s;if(!(in>>s)||s.size()>64)return false;std::size_t i=0;if(i<s.size()&&s[i]=='-')++i;auto digits=[&](){std::size_t start=i;while(i<s.size()&&s[i]>='0'&&s[i]<='9')++i;return i>start;};if(!digits())return false;if(i<s.size()&&s[i]=='.'){++i;if(!digits())return false;}if(i<s.size()&&(s[i]=='e'||s[i]=='E')){++i;if(i<s.size()&&(s[i]=='+'||s[i]=='-'))++i;if(!digits())return false;}if(i!=s.size())return false;std::istringstream parsed(s);parsed.imbue(std::locale::classic());return bool(parsed>>out)&&std::isfinite(out);}
} // namespace
bool encodeSnapshots(const std::vector<Snapshot>& rows,const std::string& campaign,const std::string& bank,const std::array<ReceiverClip,7>& clips,const EggContents& contents,std::string& out,std::string& e){
 if(!validate(rows,campaign,bank,clips,contents,e))return false;
 std::ostringstream s;s.imbue(std::locale::classic());s<<std::setprecision(std::numeric_limits<float>::max_digits10)<<"P2OHONEY1 "<<campaign<<' '<<bank<<' '<<rows.size()<<'\n';
 for(const auto& r:rows){const auto& id=r.identity;s<<id.source.fingerprint<<' '<<id.source.uid<<' '<<id.source.ordinal<<' '<<id.source.epoch<<' '<<id.source.activation<<' '<<id.slot<<' '<<static_cast<unsigned>(r.kind)<<' '<<static_cast<unsigned>(r.phase)<<' '<<unsigned(r.firstConsumption)<<' '<<unsigned(r.jiggling)<<' '<<r.position.x<<' '<<r.position.y<<' '<<r.position.z<<' '<<r.velocity.x<<' '<<r.velocity.y<<' '<<r.velocity.z<<' '<<hex(r.animation)<<'\n';if(s.tellp()>1048576)return fail(e);}
 std::string result=s.str();if(result.size()>1048576)return fail(e);out=std::move(result);e.clear();return true;
}
bool decodeSnapshots(const std::string& bytes,const std::string& campaign,const std::string& bank,const std::array<ReceiverClip,7>& clips,const EggContents& contents,std::vector<Snapshot>& out,std::string& e){
 if(bytes.size()>1048576)return fail(e);
 std::istringstream in(bytes);in.imbue(std::locale::classic());std::string magic,cp,bp;unsigned count;if(!(in>>magic>>cp>>bp)||magic!="P2OHONEY1"||cp!=campaign||bp!=bank||!integer(in,count)||count>4096)return fail(e);
 std::vector<Snapshot> rows;rows.reserve(count);for(unsigned i=0;i<count;++i){Snapshot r;unsigned kind,phase,first,jiggle;std::string animation;auto& id=r.identity;
  if(!(in>>id.source.fingerprint)||!hash(id.source.fingerprint)||!integer(in,id.source.uid)||!integer(in,id.source.ordinal)||!integer(in,id.source.epoch)||!integer(in,id.source.activation)||!integer(in,id.slot)||!integer(in,kind)||!integer(in,phase)||!integer(in,first)||!integer(in,jiggle)||kind>2||phase>5||first>1||jiggle>1||!number(in,r.position.x)||!number(in,r.position.y)||!number(in,r.position.z)||!number(in,r.velocity.x)||!number(in,r.velocity.y)||!number(in,r.velocity.z)||!(in>>animation)||!unhex(animation,r.animation))return fail(e);
  r.kind=static_cast<HoneyKind>(kind);r.phase=static_cast<Phase>(phase);r.firstConsumption=first!=0;r.jiggling=jiggle!=0;rows.push_back(std::move(r));}
 in>>std::ws;if(!in.eof()||!validate(rows,campaign,bank,clips,contents,e))return fail(e);out=std::move(rows);e.clear();return true;
}
} }
