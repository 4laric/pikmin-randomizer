#include "pc_p2_original_barrel.h"
#include "pc_p2_original_bridge.h"
#include "netplay/pc_netplay_sha256.h"
#include <cmath>
#include <cstring>
#include <fstream>
#include <set>
namespace p2original {
namespace {
bool fail(std::string& e,const char* why){e=why;return false;}
// Only common source metadata validation is shared; barrel identity, factory,
// damage units and cache remain a separate barl provider.
BridgeRecord common(const BarrelRecord& r){BridgeRecord b;b.uid=r.uid;b.reserved=r.reserved;b.sourceKey=r.sourceKey;b.sourceSha=r.sourceSha;b.resurrectionDays=r.resurrectionDays;b.dayLimit=r.dayLimit;b.stageLife=r.life;b.position=r.position;b.offset=r.offset;b.rotation=r.rotation;return b;}
void word(std::vector<std::uint8_t>& b,std::uint32_t v){for(int i=0;i<4;++i)b.push_back(std::uint8_t(v>>(8*i)));}
std::uint32_t word(const std::vector<std::uint8_t>& b,size_t p){std::uint32_t v=0;for(int i=0;i<4;++i)v|=std::uint32_t(b[p+i])<<(i*8);return v;}
void number(std::vector<std::uint8_t>& b,float f){std::uint32_t w;std::memcpy(&w,&f,4);word(b,w);}
float number(const std::vector<std::uint8_t>& b,size_t p){auto w=word(b,p);float f;std::memcpy(&f,&w,4);return f;}
}
bool validateBarrel(const BarrelRecord& r,std::string& e){if(r.life!=4000)return fail(e,"barrel source life must be 4000");return validateBridge(common(r),e);}
std::string barrelDigest(const BarrelRecord& r){auto shared=bridgeDigest(common(r));std::string source="barl:0002:0000:"+shared;unsigned char digest[32];pc_netplay_sha::sha256(source.data(),source.size(),digest);const char* hex="0123456789abcdef";std::string out;for(auto c:digest){out+=hex[c>>4];out+=hex[c&15];}return out;}
bool readBarrels(const std::string& path,std::vector<BarrelRecord>& out,std::string& e){
 std::ifstream in(path);std::string magic;unsigned count=0;if(!(in>>magic>>count)||magic!="P2_ORIGINAL_BARREL_1"||count>4096)return fail(e,"invalid barrel source manifest");
 std::vector<BarrelRecord> next;std::set<unsigned> ids;std::set<std::string> keys;
 for(unsigned i=0;i<count;++i){BarrelRecord r;std::string outer,local;if(!(in>>r.uid>>r.sourceKey>>r.sourceSha>>outer>>local>>r.reserved>>r.resurrectionDays>>r.dayLimit>>r.life))return fail(e,"truncated barrel source");for(auto* a:{&r.position,&r.offset,&r.rotation})for(float& f:*a)if(!(in>>f))return fail(e,"truncated barrel placement");if(outer!="0002"||local!="0000"||!validateBarrel(r,e))return fail(e,"unsupported barrel source");if(!ids.insert(r.uid).second||!keys.insert(r.sourceKey).second)return fail(e,"duplicate barrel identity");next.push_back(r);}
 if(in>>magic)return fail(e,"trailing barrel source");out.swap(next);e.clear();return true;
}
bool barrelStateValid(const BarrelRecord& r,const BarrelState& s,float duration,std::string& e){
 if(!validateBarrel(r,e))return false;
 if(!std::isfinite(duration)||duration<=0||duration>10000||!std::isfinite(s.health)||s.health>r.life||!std::isfinite(s.animationFrame)||s.animationFrame<0||s.animationFrame>duration)return fail(e,"invalid barrel health/frame");
 switch(s.phase){case BarrelPhase::Normal:if(s.health<0||s.animationFrame!=0)return fail(e,"invalid normal barrel");break;case BarrelPhase::Dying:if(s.health>=0||s.animationFrame>=duration)return fail(e,"invalid pending barrel death");break;case BarrelPhase::Retired:if(s.health>=0||s.animationFrame!=duration)return fail(e,"invalid retired barrel");break;default:return fail(e,"invalid barrel phase");}
 e.clear();return true;
}
bool barrelDamage(BarrelState& s,float damage){if(s.phase!=BarrelPhase::Normal||!std::isfinite(damage)||damage<=0||!std::isfinite(s.health-damage))return false;s.health-=damage;if(s.health<0){s.phase=BarrelPhase::Dying;s.animationFrame=0;}return true;}
bool barrelAnimate(BarrelState& s,float dt,float duration){if(s.phase!=BarrelPhase::Dying||!std::isfinite(dt)||dt<=0||!std::isfinite(duration)||duration<=0)return false;s.animationFrame=std::fmin(duration,s.animationFrame+dt*30);if(s.animationFrame<duration)return false;s.phase=BarrelPhase::Retired;return true;}
bool barrelExport(const BarrelRecord& r,const BarrelState& s,float duration,std::vector<std::uint8_t>& out,std::string& e){if(!barrelStateValid(r,s,duration,e))return false;std::vector<std::uint8_t> b={'B','A','0','1'};auto d=barrelDigest(r);b.insert(b.end(),d.begin(),d.end());word(b,unsigned(s.phase));number(b,s.health);number(b,s.animationFrame);unsigned char sum[32];pc_netplay_sha::sha256(b.data(),b.size(),sum);b.insert(b.end(),sum,sum+32);out.swap(b);return true;}
bool barrelImport(const BarrelRecord& r,const std::vector<std::uint8_t>& b,float duration,BarrelState& out,std::string& e){if(b.size()!=112||std::memcmp(b.data(),"BA01",4))return fail(e,"invalid barrel snapshot envelope");unsigned char sum[32];pc_netplay_sha::sha256(b.data(),80,sum);if(std::memcmp(sum,b.data()+80,32))return fail(e,"barrel checksum mismatch");auto d=barrelDigest(r);if(std::memcmp(d.data(),b.data()+4,64))return fail(e,"barrel source mismatch");BarrelState next;next.phase=BarrelPhase(word(b,68));next.health=number(b,72);next.animationFrame=number(b,76);if(!barrelStateValid(r,next,duration,e))return false;out=next;e.clear();return true;}
}
