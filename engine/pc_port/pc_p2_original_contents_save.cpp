#include "pc_p2_original_contents_save.h"
#include <cmath>
#include <charconv>
#include <iomanip>
#include <limits>
#include <locale>
#include <sstream>
namespace p2originalresource { namespace {
constexpr std::size_t maxBytes=1024*1024,maxRecords=4096;
bool fail(std::string& e,const char* s){e=s;return false;}
bool sha(const std::string& s){if(s.size()!=64)return false;for(char c:s)if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return false;return true;}
class Reader {
 const std::string& bytes;std::size_t pos=0;
public:
 explicit Reader(const std::string& s):bytes(s){}
 bool token(std::string& out){while(pos<bytes.size()&&(bytes[pos]==' '||bytes[pos]=='\n'||bytes[pos]=='\r'||bytes[pos]=='\t'))++pos;
  const std::size_t start=pos;while(pos<bytes.size()&&bytes[pos]!=' '&&bytes[pos]!='\n'&&bytes[pos]!='\r'&&bytes[pos]!='\t')++pos;
  if(start==pos||pos-start>128)return false;
  out=bytes.substr(start,pos-start);return true;
 }
 bool word(const char* wanted){std::string s;return token(s)&&s==wanted;}
 template<class T> bool integer(T& out){std::string s;if(!token(s)||s.empty()||s.size()>20)return false;T n=0;
  for(char c:s){if(c<'0'||c>'9')return false;const T digit=T(c-'0');if(n>(std::numeric_limits<T>::max()-digit)/10)return false;n=T(n*10+digit);}
  out=n;return true;
 }
 bool boolean(bool& out){std::string s;if(!token(s)||(s!="0"&&s!="1"))return false;out=s=="1";return true;}
 bool real(float& out){std::string s;if(!token(s)||s.empty())return false;
  // Decimal floating syntax only; stream extensions (hex, NaN, Inf) forbidden.
  std::size_t i=0;if(s[i]=='-'||s[i]=='+')++i;unsigned digits=0;
  while(i<s.size()&&s[i]>='0'&&s[i]<='9'){++i;++digits;}
  if(i<s.size()&&s[i]=='.'){++i;while(i<s.size()&&s[i]>='0'&&s[i]<='9'){++i;++digits;}}
  if(!digits)return false;
  if(i<s.size()&&(s[i]=='e'||s[i]=='E')){++i;if(i<s.size()&&(s[i]=='-'||s[i]=='+'))++i;unsigned exponentDigits=0;while(i<s.size()&&s[i]>='0'&&s[i]<='9'){++i;++exponentDigits;}if(!exponentDigits)return false;}
  if(i!=s.size())return false;
  float v=0;const char* first=s.data();if(*first=='+')++first;
  const auto parsed=std::from_chars(first,s.data()+s.size(),v,std::chars_format::general);
  if(parsed.ec!=std::errc{}||parsed.ptr!=s.data()+s.size()||!std::isfinite(v))return false;
  out=v;return true;
 }
 bool done(){while(pos<bytes.size()&&(bytes[pos]==' '||bytes[pos]=='\n'||bytes[pos]=='\r'||bytes[pos]=='\t'))++pos;return pos==bytes.size();}
};
bool restored(const std::vector<ContentsRecord>& records,std::string& e){
 if(records.size()>maxRecords)return fail(e,"Egg contents record count exceeds 4096");
 EggContents temporary;return temporary.restore(records,e);
}
}
bool encodeContents(const std::vector<ContentsRecord>& rows,const std::string& campaign,std::string& out,std::string& e){
 if(!sha(campaign))return fail(e,"Egg contents campaign requires full lowercase SHA256");
 if(!restored(rows,e))return false;
 std::ostringstream stream;stream.imbue(std::locale::classic());stream<<std::setprecision(std::numeric_limits<float>::max_digits10);
 stream<<"P2_EGG_CONTENTS 1\ncampaign "<<campaign<<"\nrecords "<<rows.size()<<'\n';
 for(const auto& r:rows){stream<<"record "<<r.source.fingerprint<<' '<<r.source.uid<<' '<<r.source.ordinal<<' '<<r.source.epoch<<' '<<r.source.activation<<' '<<static_cast<unsigned>(r.type)<<" 1 "<<r.children.size()<<'\n';
  for(const auto& child:r.children){stream<<"child "<<child.identity.slot<<' '<<static_cast<unsigned>(child.kind)<<' '
   <<child.position.x<<' '<<child.position.y<<' '<<child.position.z<<' '<<child.velocity.x<<' '<<child.velocity.y<<' '<<child.velocity.z<<' '<<child.facing<<' '
   <<child.pelletColor<<' '<<child.mititeCount<<' '<<(child.attempted?1:0)<<' '<<(child.born?1:0)<<' '<<(child.consumed?1:0)<<'\n';}
  if(stream.tellp()>static_cast<std::streamoff>(maxBytes))return fail(e,"Egg contents encoding exceeds 1MiB");
 }
 stream<<"end\n";std::string bytes=stream.str();if(bytes.size()>maxBytes)return fail(e,"Egg contents encoding exceeds 1MiB");
 out=std::move(bytes);e.clear();return true;
}
bool decodeContents(const std::string& bytes,const std::string& campaign,std::vector<ContentsRecord>& out,std::string& e){
 if(!sha(campaign))return fail(e,"Egg contents expected campaign requires full lowercase SHA256");
 if(bytes.empty()||bytes.size()>maxBytes)return fail(e,"Egg contents byte envelope exceeds 1MiB or is empty");
 Reader reader(bytes);unsigned version=0,count=0;std::string actual;
 if(!reader.word("P2_EGG_CONTENTS")||!reader.integer(version)||version!=1||!reader.word("campaign")||!reader.token(actual)||!sha(actual)||actual!=campaign||!reader.word("records")||!reader.integer(count)||count>maxRecords)return fail(e,"Egg contents version/campaign/record header invalid");
 std::vector<ContentsRecord> next;next.reserve(count);
 for(unsigned i=0;i<count;++i){ContentsRecord record;unsigned drop=0,children=0;
  if(!reader.word("record")||!reader.token(record.source.fingerprint)||!sha(record.source.fingerprint)||!reader.integer(record.source.uid)||!reader.integer(record.source.ordinal)
   ||!reader.integer(record.source.epoch)||!reader.integer(record.source.activation)||!reader.integer(drop)||drop>6||!reader.boolean(record.complete)||!record.complete||!reader.integer(children)||children>2)return fail(e,"Egg contents typed source record invalid or truncated");
  record.type=static_cast<P2EggDropType>(drop);record.children.reserve(children);
  for(unsigned j=0;j<children;++j){ChildOutcome child;child.identity.source=record.source;unsigned kind=0,color=0,mitites=0;
   if(!reader.word("child")||!reader.integer(child.identity.slot)||!reader.integer(kind)||kind>5
    ||!reader.real(child.position.x)||!reader.real(child.position.y)||!reader.real(child.position.z)||!reader.real(child.velocity.x)||!reader.real(child.velocity.y)||!reader.real(child.velocity.z)||!reader.real(child.facing)
    ||!reader.integer(color)||color>2||!reader.integer(mitites)||mitites>10||!reader.boolean(child.attempted)||!reader.boolean(child.born)||!reader.boolean(child.consumed))return fail(e,"Egg contents child fields invalid or truncated");
   child.kind=static_cast<ChildKind>(kind);child.pelletColor=int(color);child.mititeCount=int(mitites);record.children.push_back(child);
  }
  next.push_back(std::move(record));
 }
 if(!reader.word("end")||!reader.done())return fail(e,"Egg contents missing end marker or trailing data");
 if(!restored(next,e))return false;
 out=std::move(next);e.clear();return true;
}
}
