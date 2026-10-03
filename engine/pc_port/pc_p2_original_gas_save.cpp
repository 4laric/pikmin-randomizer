#include "pc_p2_original_gas_save.h"
#include <cmath>
#include <iomanip>
#include <limits>
#include <locale>
#include <sstream>
namespace p2original { namespace gas { namespace {
bool fail(std::string& e,const char* why){e=why;return false;}
bool link(const std::string& s){
 if(s.size()>2048)return false;
 for(unsigned char c:s)if(c<=32||c>=127)return false;
 return true;
}
bool valid(const Snapshot& s,std::string& e){
 const auto& id=s.identity;
 if(id.catalog.size()!=64||!id.generator||id.ordinal>=10||!id.activation)return fail(e,"Gas checkpoint source identity invalid");
 for(char c:id.catalog)if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return fail(e,"Gas checkpoint catalog hash invalid");
 for(float v:{s.position.x,s.position.y,s.position.z,s.facing,s.health,s.timer,s.sourceFrame})if(!std::isfinite(v))return fail(e,"Gas checkpoint nonfinite field");
 const bool dead=s.state==State::Dead,attack=s.state==State::Attack;
 if((!dead&&!attack&&s.state!=State::Wait)||s.health<0||s.timer<0||s.sourceFrame<0||s.sourceFrame>=4
   ||s.motion!=(attack?1u:0u)||(!attack&&(s.sourceFrame!=0||s.finishMotion))||s.generatorDeathCommitted!=dead
   ||(dead&&(s.health!=0||s.living))||!link(s.bridge)||!link(s.gate)||(!s.bridge.empty()&&!s.gate.empty())
   ||(s.checkLinks&&(!s.bridge.empty()||!s.gate.empty())))return fail(e,"Gas checkpoint state invalid");
 return true;
}
} // namespace
bool encodeSnapshot(const Snapshot& s,std::string& bytes,std::string& e){
 if(!valid(s,e))return false;
 std::ostringstream out;out.imbue(std::locale::classic());out<<std::setprecision(std::numeric_limits<float>::max_digits10);
 out<<"P2OG1 "<<s.identity.catalog<<' '<<s.identity.generator<<' '<<s.identity.ordinal<<' '<<s.identity.epoch<<' '<<s.identity.activation<<' '
    <<static_cast<int>(s.state)<<' '<<s.position.x<<' '<<s.position.y<<' '<<s.position.z<<' '<<s.facing<<' '<<s.health<<' '<<s.timer<<' '<<s.sourceFrame<<' '
    <<s.motion<<' '<<s.finishMotion<<' '<<s.checkLinks<<' '<<s.living<<' '<<s.generatorDeathCommitted<<' '
    <<std::quoted(s.bridge)<<' '<<std::quoted(s.gate);
 if(!out||out.str().size()>8192)return fail(e,"Gas checkpoint exceeds bound");
 bytes=out.str();e.clear();return true;
}
bool decodeSnapshot(const std::string& bytes,Snapshot& s,std::string& e){
 if(bytes.empty()||bytes.size()>8192)return fail(e,"Gas checkpoint byte bound invalid");
 // Reject control characters and sign-prefixed integer wraparound before parse.
 for(unsigned char c:bytes)if(c<32||c>=127)return fail(e,"Gas checkpoint byte invalid");
 std::istringstream in(bytes);in.imbue(std::locale::classic());Snapshot next;std::string version;int state=0,finish=0,check=0,living=0,death=0;
 if(!(in>>version)||version!="P2OG1")return fail(e,"Gas checkpoint version invalid");
 auto uintField=[&in](auto& value){std::string word;if(!(in>>word)||word.empty()||word.find_first_not_of("0123456789")!=std::string::npos)return false;std::istringstream n(word);n.imbue(std::locale::classic());return bool(n>>value)&&n.peek()==std::char_traits<char>::eof();};
 if(!(in>>next.identity.catalog)||!uintField(next.identity.generator)||!uintField(next.identity.ordinal)||!uintField(next.identity.epoch)||!uintField(next.identity.activation)
   ||!(in>>state>>next.position.x>>next.position.y>>next.position.z>>next.facing>>next.health>>next.timer>>next.sourceFrame)
   ||!uintField(next.motion)||!(in>>finish>>check>>living>>death>>std::quoted(next.bridge)>>std::quoted(next.gate)))return fail(e,"Gas checkpoint fields invalid");
 if((finish!=0&&finish!=1)||(check!=0&&check!=1)||(living!=0&&living!=1)||(death!=0&&death!=1))return fail(e,"Gas checkpoint bool invalid");
 next.state=static_cast<State>(state);next.finishMotion=finish;next.checkLinks=check;next.living=living;next.generatorDeathCommitted=death;
 in>>std::ws;if(!in.eof()||!valid(next,e))return fail(e,"Gas checkpoint trailing bytes or invariant invalid");
 s=std::move(next);e.clear();return true;
}
} }
