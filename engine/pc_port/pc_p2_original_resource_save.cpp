#include "pc_p2_original_resource_save.h"
#include <locale>
#include <sstream>
namespace p2originalresource { namespace {
constexpr std::size_t maxBytes=1048576,maxRecords=4096;
bool fail(std::string& e,const char* why){e=why;return false;}
bool sha(const std::string& s){if(s.size()!=64)return false;for(char c:s)if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return false;return true;}
template<class T> bool integer(std::istream& in,T& value){
 std::string token;if(!(in>>token)||token.empty()||token.find_first_not_of("0123456789")!=std::string::npos)return false;
 std::istringstream n(token);n.imbue(std::locale::classic());return bool(n>>value)&&n.peek()==std::char_traits<char>::eof();
}
}
bool encodeResources(const ResourceSnapshot& state,const std::string& campaign,const EggContents& graph,std::string& bytes,std::string& e){
 if(!sha(campaign)||state.completed.size()>maxRecords)return fail(e,"original resource card campaign/bound invalid");
 ResourceState check;if(!check.restore(state,graph,e))return false;
 std::ostringstream out;out.imbue(std::locale::classic());out<<"P2ORS1 "<<campaign<<' '<<state.version;
 for(auto n:state.sprayCounts)out<<' '<<n;
 for(auto n:state.berryCounts)out<<' '<<n;
 for(auto n:state.sprayUses)out<<' '<<n;
 for(auto b:state.sprayMade)out<<' '<<b;
 out<<' '<<state.completed.size();
 for(const auto& event:state.completed){const auto& id=event.child.source;
  out<<' '<<id.fingerprint<<' '<<id.uid<<' '<<id.ordinal<<' '<<id.epoch<<' '<<id.activation<<' '<<event.child.slot<<' '<<static_cast<unsigned>(event.kind)<<' '<<event.captain;
 }
 if(!out||out.str().size()>maxBytes)return fail(e,"original resource card byte bound exceeded");
 bytes=out.str();e.clear();return true;
}
bool decodeResources(const std::string& bytes,const std::string& expected,const EggContents& graph,ResourceSnapshot& state,std::string& e){
 if(bytes.empty()||bytes.size()>maxBytes||!sha(expected))return fail(e,"original resource card byte/campaign bound invalid");
 for(unsigned char c:bytes)if(c<32||c>=127)return fail(e,"original resource card byte invalid");
 std::istringstream in(bytes);in.imbue(std::locale::classic());std::string version,campaign;ResourceSnapshot next;
 if(!(in>>version>>campaign)||version!="P2ORS1"||campaign!=expected||!integer(in,next.version))return fail(e,"original resource card version/campaign mismatch");
 for(auto& n:next.sprayCounts)if(!integer(in,n))return fail(e,"original resource card spray count invalid");
 for(auto& n:next.berryCounts)if(!integer(in,n))return fail(e,"original resource card berry count invalid");
 for(auto& n:next.sprayUses)if(!integer(in,n))return fail(e,"original resource card spray use count invalid");
 for(auto& b:next.sprayMade){unsigned n;if(!integer(in,n)||n>1)return fail(e,"original resource card demo flag invalid");b=n!=0;}
 std::size_t count=0;if(!integer(in,count)||count>maxRecords)return fail(e,"original resource card record count invalid");
 for(std::size_t i=0;i<count;++i){SprayCompletion event;auto& id=event.child.source;unsigned kind=0;
  if(!(in>>id.fingerprint)||!sha(id.fingerprint)||!integer(in,id.uid)||!integer(in,id.ordinal)||!integer(in,id.epoch)||!integer(in,id.activation)||!integer(in,event.child.slot)||!integer(in,kind)||kind>2||!integer(in,event.captain))return fail(e,"original resource card receipt invalid");
  event.kind=static_cast<HoneyKind>(kind);next.completed.push_back(std::move(event));
 }
 in>>std::ws;if(!in.eof())return fail(e,"original resource card trailing bytes");
 ResourceState check;if(!check.restore(next,graph,e))return false;
 state=std::move(next);e.clear();return true;
}
}
