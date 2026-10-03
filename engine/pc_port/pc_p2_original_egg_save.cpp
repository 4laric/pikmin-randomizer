#include "pc_p2_original_egg_save.h"
#include <charconv>
#include <cmath>
#include <iomanip>
#include <limits>
#include <locale>
#include <sstream>
namespace p2original { namespace egg { namespace {
bool fail(std::string& e,const char* why){e=why;return false;}
bool sha(const std::string& s){if(s.size()!=64)return false;for(char c:s)if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return false;return true;}
class Reader {
 const std::string& bytes;std::size_t pos=0;
 void whitespace(){while(pos<bytes.size()&&(bytes[pos]==' '||bytes[pos]=='\n'||bytes[pos]=='\r'||bytes[pos]=='\t'))++pos;}
public:
 explicit Reader(const std::string& s):bytes(s){}
 bool token(std::string& out){whitespace();const auto start=pos;while(pos<bytes.size()&&bytes[pos]!=' '&&bytes[pos]!='\n'&&bytes[pos]!='\r'&&bytes[pos]!='\t')++pos;if(start==pos||pos-start>128)return false;out=bytes.substr(start,pos-start);return true;}
 bool word(const char* wanted){std::string s;return token(s)&&s==wanted;}
 template<class T> bool integer(T& out){std::string s;if(!token(s)||s.empty()||s.size()>20)return false;T n=0;for(char c:s){if(c<'0'||c>'9')return false;const T d=T(c-'0');if(n>(std::numeric_limits<T>::max()-d)/10)return false;n=T(n*10+d);}out=n;return true;}
 bool boolean(bool& out){std::string s;if(!token(s)||(s!="0"&&s!="1"))return false;out=s=="1";return true;}
 bool real(float& out){std::string s;if(!token(s)||s.empty())return false;std::size_t i=0;if(s[i]=='-'||s[i]=='+')++i;unsigned digits=0;
  while(i<s.size()&&s[i]>='0'&&s[i]<='9'){++i;++digits;}if(i<s.size()&&s[i]=='.'){++i;while(i<s.size()&&s[i]>='0'&&s[i]<='9'){++i;++digits;}}if(!digits)return false;
  if(i<s.size()&&(s[i]=='e'||s[i]=='E')){++i;if(i<s.size()&&(s[i]=='-'||s[i]=='+'))++i;unsigned exponent=0;while(i<s.size()&&s[i]>='0'&&s[i]<='9'){++i;++exponent;}if(!exponent)return false;}if(i!=s.size())return false;
  float v=0;const char* first=s.data();if(*first=='+')++first;const auto parsed=std::from_chars(first,s.data()+s.size(),v,std::chars_format::general);if(parsed.ec!=std::errc{}||parsed.ptr!=s.data()+s.size()||!std::isfinite(v))return false;out=v;return true;
 }
 bool identity(p2originalresource::SourceIdentity& id){return token(id.fingerprint)&&sha(id.fingerprint)&&integer(id.uid)&&integer(id.ordinal)&&integer(id.epoch)&&integer(id.activation);}
 bool position(Position& p){return real(p.x)&&real(p.y)&&real(p.z);}
 bool done(){whitespace();return pos==bytes.size();}
};
void identity(std::ostream& out,const p2originalresource::SourceIdentity& id){out<<id.fingerprint<<' '<<id.uid<<' '<<id.ordinal<<' '<<id.epoch<<' '<<id.activation<<' ';}
void position(std::ostream& out,Position p){out<<p.x<<' '<<p.y<<' '<<p.z<<' ';}
} // namespace
bool encodeSnapshot(const Snapshot& s,const std::string& campaign,const SnapshotContext& context,std::string& bytes,std::string& e){
 if(!sha(campaign))return fail(e,"Egg checkpoint campaign requires full lowercase SHA256");
 if(!validateSnapshot(s,context,e))return false;
 std::ostringstream out;out.imbue(std::locale::classic());out<<std::setprecision(std::numeric_limits<float>::max_digits10);
 out<<"P2OE1 "<<campaign<<' ';identity(out,s.identity);out<<s.resourceFingerprint<<' '<<s.state<<' ';position(out,s.position);position(out,s.velocity);position(out,s.targetVelocity);position(out,s.scale);
 out<<s.facing<<' '<<s.health<<' '<<s.flickTimer<<' '<<s.sourceFrame<<' '<<s.stopped<<' '
  <<s.flags.leaveCarcass<<' '<<s.flags.damageAnimation<<' '<<s.flags.deathEffect<<' '<<s.flags.bitterImmune<<' '<<s.flags.constrained<<' '<<s.flags.invulnerable<<' '<<s.flags.cullable<<' '<<s.flags.living<<' '<<s.flags.lifeGauge<<' '
  <<s.dependent<<' '<<s.captured<<' '<<s.falling<<' '<<s.dropGroup<<' '<<s.contentsGenerated<<' '<<s.effectsEmitted<<' '<<s.killRequested<<' '<<s.hasParent<<' ';
 if(s.hasParent)identity(out,s.parentIdentity);
 out<<"end";const auto next=out.str();if(!out||next.size()>8192)return fail(e,"Egg checkpoint exceeds 8192 byte bound");bytes=next;e.clear();return true;
}
bool decodeSnapshot(const std::string& bytes,const std::string& campaign,const SnapshotContext& context,Snapshot& out,std::string& e){
 if(!sha(campaign))return fail(e,"Egg checkpoint expected campaign requires full lowercase SHA256");
 if(bytes.empty()||bytes.size()>8192)return fail(e,"Egg checkpoint byte bound invalid");
 Reader reader(bytes);Snapshot s;std::string actual;
 if(!reader.word("P2OE1")||!reader.token(actual)||!sha(actual)||actual!=campaign||!reader.identity(s.identity)||!reader.token(s.resourceFingerprint)||!sha(s.resourceFingerprint)||!reader.integer(s.state)
  ||!reader.position(s.position)||!reader.position(s.velocity)||!reader.position(s.targetVelocity)||!reader.position(s.scale)||!reader.real(s.facing)||!reader.real(s.health)||!reader.real(s.flickTimer)||!reader.real(s.sourceFrame)||!reader.boolean(s.stopped)
  ||!reader.boolean(s.flags.leaveCarcass)||!reader.boolean(s.flags.damageAnimation)||!reader.boolean(s.flags.deathEffect)||!reader.boolean(s.flags.bitterImmune)||!reader.boolean(s.flags.constrained)||!reader.boolean(s.flags.invulnerable)||!reader.boolean(s.flags.cullable)||!reader.boolean(s.flags.living)||!reader.boolean(s.flags.lifeGauge)
  ||!reader.boolean(s.dependent)||!reader.boolean(s.captured)||!reader.boolean(s.falling)||!reader.boolean(s.dropGroup)||!reader.boolean(s.contentsGenerated)||!reader.boolean(s.effectsEmitted)||!reader.boolean(s.killRequested)||!reader.boolean(s.hasParent))return fail(e,"Egg checkpoint typed fields invalid or truncated");
 if(s.hasParent&&!reader.identity(s.parentIdentity))return fail(e,"Egg checkpoint parent incarnation invalid");
 if(!reader.word("end")||!reader.done())return fail(e,"Egg checkpoint missing end or trailing bytes");
 if(!validateSnapshot(s,context,e))return false;
 out=std::move(s);e.clear();return true;
}
} }
