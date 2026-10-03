#include "pc_p2_original_wisp_save.h"
#include <iomanip>
#include <limits>
#include <locale>
#include <sstream>
namespace p2original { namespace wisp { namespace {
bool fail(std::string& e,const char* why){e=why;return false;}
bool hash(const std::string& s){return s.size()==64&&s.find_first_not_of("0123456789abcdef")==std::string::npos;}
bool valid(const Snapshot& s,const std::string& campaign,const Initial& initial,int duration,const std::vector<Key>& keys,std::string& e){
 if(!hash(campaign)||!hash(s.identity.catalog)||!hash(s.cargo.fingerprint)||s.identity.ordinal>=10)return fail(e,"Wisp checkpoint campaign/source identity invalid");
 if(!std::isfinite(initial.fly)||!std::isfinite(initial.slide)||duration<1)return fail(e,"Wisp checkpoint source context invalid");
 int previous=-1;for(const auto& k:keys){if(k.frame<0||k.frame>=duration||k.frame<previous||k.type<0||k.type>2)return fail(e,"Wisp checkpoint authored key context invalid");previous=k.frame;}
 return validateSnapshot(s,initial,duration,keys,e);
}
struct Reader {
 std::istringstream in;
 explicit Reader(const std::string& bytes):in(bytes){in.imbue(std::locale::classic());}
 template<class T> bool number(T& value){std::string word;if(!(in>>word)||word.empty()||word.find_first_not_of("0123456789")!=std::string::npos)return false;std::istringstream field(word);field.imbue(std::locale::classic());return bool(field>>value)&&field.peek()==std::char_traits<char>::eof();}
 bool flag(bool& value){std::string word;if(!(in>>word)||(word!="0"&&word!="1"))return false;value=word=="1";return true;}
 bool position(Position& p){return bool(in>>p.x>>p.y>>p.z);}
 bool identity(InstanceIdentity& i){return bool(in>>i.catalog)&&number(i.generator)&&number(i.ordinal)&&number(i.epoch)&&number(i.activation);}
 bool cargo(p2originalresource::SourceIdentity& i){return bool(in>>i.fingerprint)&&number(i.uid)&&number(i.ordinal)&&number(i.epoch)&&number(i.activation);}
};
} // namespace
bool encodeSnapshot(const Snapshot& s,const std::string& campaign,const Initial& initial,int duration,const std::vector<Key>& keys,std::string& bytes,std::string& e){
 if(!valid(s,campaign,initial,duration,keys,e))return false;
 std::ostringstream out;out.imbue(std::locale::classic());out<<std::setprecision(std::numeric_limits<float>::max_digits10);
 out<<"P2OW1 "<<campaign<<' '<<s.identity.catalog<<' '<<s.identity.generator<<' '<<s.identity.ordinal<<' '<<s.identity.epoch<<' '<<s.identity.activation<<' '<<unsigned(s.state)<<' '<<s.spawnIndex<<' '<<s.motion;
 for(const auto& p:{s.spawn[0],s.spawn[1],s.position,s.velocity,s.targetVelocity})out<<' '<<p.x<<' '<<p.y<<' '<<p.z;
 out<<' '<<s.facing<<' '<<s.pitch<<' '<<s.timer<<' '<<s.scale<<' '<<s.atari<<' '<<s.hidden<<' '<<s.cullable<<' '<<s.alive<<' '<<s.dead<<' '<<s.clock.frame<<' '<<s.clock.next<<' '<<s.clock.completed<<' '<<s.clock.stopped;
 out<<' '<<s.cargo.fingerprint<<' '<<s.cargo.uid<<' '<<s.cargo.ordinal<<' '<<s.cargo.epoch<<' '<<s.cargo.activation<<' '<<s.cargoSlot<<' '<<s.eggBorn<<' '<<s.released;
 if(!out||out.str().size()>8192)return fail(e,"Wisp checkpoint exceeds byte bound");
 bytes=out.str();e.clear();return true;
}
bool decodeSnapshot(const std::string& bytes,const std::string& campaign,const Initial& initial,int duration,const std::vector<Key>& keys,Snapshot& result,std::string& e){
 if(bytes.empty()||bytes.size()>8192)return fail(e,"Wisp checkpoint byte bound invalid");
 for(unsigned char c:bytes)if(c<32||c>=127)return fail(e,"Wisp checkpoint byte invalid");
 Reader r(bytes);Snapshot s;std::string version,savedCampaign;unsigned state=0;
 if(!(r.in>>version>>savedCampaign)||version!="P2OW1"||!hash(campaign)||savedCampaign!=campaign||!r.identity(s.identity)||!r.number(state)||!r.number(s.spawnIndex)||!r.number(s.motion))return fail(e,"Wisp checkpoint header/campaign invalid");
 s.state=static_cast<State>(state);
 if(!r.position(s.spawn[0])||!r.position(s.spawn[1])||!r.position(s.position)||!r.position(s.velocity)||!r.position(s.targetVelocity)||!(r.in>>s.facing>>s.pitch>>s.timer>>s.scale)||!r.flag(s.atari)||!r.flag(s.hidden)||!r.flag(s.cullable)||!r.flag(s.alive)||!r.flag(s.dead)||!(r.in>>s.clock.frame)||!r.number(s.clock.next)||!r.flag(s.clock.completed)||!r.flag(s.clock.stopped)||!r.cargo(s.cargo)||!r.number(s.cargoSlot)||!r.flag(s.eggBorn)||!r.flag(s.released))return fail(e,"Wisp checkpoint fields invalid");
 r.in>>std::ws;if(!r.in.eof())return fail(e,"Wisp checkpoint trailing fields");
 if(!valid(s,campaign,initial,duration,keys,e))return false;
 result=std::move(s);e.clear();return true;
}
} }
