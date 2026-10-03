#include "pc_p2_watage_effect.h"
#include "netplay/pc_netplay_sha256.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iterator>
namespace p2watage {
namespace {
bool reject(std::string& e,const char* s){e=s;return false;}
float random(std::uint32_t& s){s=s*0x19660du+0x3c6ef35fu;auto bits=(s>>9)|0x3f800000u;float f;std::memcpy(&f,&bits,4);return f-1;}
float zp(std::uint32_t& s){return 2*random(s)-1;}
float zh(std::uint32_t& s){return random(s)-.5f;}
float length(Vec v){return std::sqrt(v.x*v.x+v.y*v.y+v.z*v.z);}
Vec mul(Vec v,float s){return {v.x*s,v.y*s,v.z*s};}
Vec add(Vec a,Vec b){return {a.x+b.x,a.y+b.y,a.z+b.z};}
Vec normalized(Vec v){float l=length(v);return l>0?mul(v,1/l):Vec{};}
float f32(const std::vector<unsigned char>& b,unsigned i){std::uint32_t v=(std::uint32_t(b[i])<<24)|(unsigned(b[i+1])<<16)|(unsigned(b[i+2])<<8)|b[i+3];float f;std::memcpy(&f,&v,4);return f;}
bool read(const std::string& path,std::size_t size,const char* digest,std::vector<unsigned char>& out){
 std::ifstream in(path,std::ios::binary|std::ios::ate);if(!in||in.tellg()!=std::streamoff(size))return false;
 in.seekg(0);out.resize(size);if(!in.read(reinterpret_cast<char*>(out.data()),size))return false;
 std::uint8_t sha[32];pc_netplay_sha::sha256(out.data(),out.size(),sha);const char* hex="0123456789abcdef";
 for(unsigned i=0;i<32;++i)if(hex[sha[i]>>4]!=digest[i*2]||hex[sha[i]&15]!=digest[i*2+1])return false;return true;
}
}
bool Effect::load(const std::string& dir,std::string& e){
 if(!mBursts.empty())return reject(e,"Watage reload with live emitters");mReady=false;mResource.clear();mTexture.clear();
 if(!read(dir+"/watage-01e4.jpa",496,"e94cd58a680c0cb2b04d1e3a88be0338bb0cea7cbf70ec0f1cefea17456aac6d",mResource)
  ||!read(dir+"/IP2_watage2_ia.tex1",1088,"c5e7489de8993f0fffc977d3fc60e143dc06ceced4e8ddd7cf30df60cf114775",mTexture))
  return reject(e,"Watage requires genuine GPVE01 JPA0x1e4 and IP2_watage2_ia bytes");
 mReady=true;e.clear();return true;
}
void Effect::fields(Particle& p,std::uint32_t& seed,unsigned mask){
 // JPAFieldBlock::calc: Drag multiplies accumulated drag, Random adds only
 // on age0/cycle4, Air adds normalized authored direction and caps type1.
 // Resource::calcField traverses the source block array in reverse order.
 if(mask&4){p.velocity=add(p.velocity,mul(normalized({-.25f,.39990234375f,0}),.029999999329447746f));float l=length(p.velocity);if(l>9)p.velocity=mul(p.velocity,9/l);}
 if((mask&2)&&p.age%4==0){Vec r{zh(seed),zh(seed),zh(seed)};p.velocity=add(p.velocity,mul(r,.6000000238418579f));}
 if(mask&1)p.drag*=.9850000143051147f;
}
bool Effect::touch(Vec origin,std::uint32_t seed,std::string& e){
 if(!mReady)return reject(e,"Watage emitter resource not admitted");
 if(!std::isfinite(origin.x)||!std::isfinite(origin.y)||!std::isfinite(origin.z))return reject(e,"Watage nonfinite origin");
 // Finite private pool; refuse rather than steal another actor's emitter.
 if(mBursts.size()>=64)return reject(e,"Watage emitter pool exhausted");
 Burst b;b.origin=origin;b.seed=seed;
 const auto& r=mResource;const unsigned bem=8,esp=388;
 int count=int(f32(r,bem+0x4c)*(1+f32(r,bem+0x50)*zp(b.seed)));
 for(int i=0;i<count;++i){
  Particle p;p.life=200*(1-f32(r,bem+0x54)*random(b.seed));
  // JPAVolumeSphere, unfixed density, zero sweep: theta0, radial min1.
  b.seed=b.seed*0x19660du+0x3c6ef35fu;auto phi=std::int16_t(b.seed>>16)>>1;
  b.seed=b.seed*0x19660du+0x3c6ef35fu;random(b.seed);
  const float a=float(phi)*6.283185307179586f/65536;
  Vec local{0,-10*std::sin(a)*.8f,10*std::cos(a)};p.position=add(origin,add(local,{0,85,0}));
  Vec omni=normalized(local);
  // Source direction is +Y. JPAGetYZRotateMtx maps its localZ to it.
  const float spread=f32(r,bem+0x44)*32767*zp(b.seed)*6.283185307179586f/65536;
  b.seed=b.seed*0x19660du+0x3c6ef35fu;float theta=float(std::int16_t(b.seed>>16))*6.283185307179586f/65536;
  Vec directed{std::cos(theta)*std::sin(spread)*.4f,std::cos(spread)*.4f,-std::sin(theta)*std::sin(spread)*.4f};
  float ratio=1+zp(b.seed)*f32(r,bem+0x48);p.velocity=mul(add(omni,directed),ratio);p.velocity.y*=.8f;
  p.moment=1-f32(r,bem+0x64)*random(b.seed);random(b.seed); // base colour loop offset random
  p.scale=1+zp(b.seed)*f32(r,esp+0x24);
  p.angle=std::uint16_t(int(f32(r,esp+0x4c)+f32(r,esp+0x50)*zh(b.seed)));
  p.spin=std::int16_t(f32(r,esp+0x54)*(1+f32(r,esp+0x58)*zp(b.seed)));if(zp(b.seed)>=f32(r,esp+0x5c))p.spin=-p.spin;
  b.particles.push_back(p);
 }
 mBursts.push_back(std::move(b));++mEmissions;e.clear();return true;
}
bool Effect::tick(float seconds,std::string& e){
 if(!std::isfinite(seconds)||seconds<0||seconds>2)return reject(e,"Watage invalid frame time");
 mRemainder+=seconds*30;while(mRemainder>=1){mRemainder-=1;
  for(auto& b:mBursts){for(auto& p:b.particles){if(++p.age>=int(p.life))continue;fields(p,b.seed);
    p.position=add(p.position,mul(p.velocity,p.moment*p.drag));p.angle=std::uint16_t(p.angle+p.spin);
    float time=p.age/p.life;p.alpha=time<.0137f?.825f*time/.0137f:time>.9f?.825f*(1-time)/.1f:.825f;
   }
   b.particles.erase(std::remove_if(b.particles.begin(),b.particles.end(),[](const Particle& p){return p.age>=int(p.life);}),b.particles.end());
  }
  mBursts.erase(std::remove_if(mBursts.begin(),mBursts.end(),[](const Burst& b){return b.particles.empty();}),mBursts.end());
 }e.clear();return true;
}
std::size_t Effect::particles()const{std::size_t n=0;for(const auto& b:mBursts)n+=b.particles.size();return n;}
}
