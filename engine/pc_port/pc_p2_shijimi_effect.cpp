#include "pc_p2_shijimi_effect.h"
#include "netplay/pc_netplay_sha256.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>
namespace p2original { namespace shijimi {
namespace {
bool reject(std::string& e,const char* m){e=m;return false;}
float random(std::uint32_t& s){s=s*0x19660du+0x3c6ef35fu;std::uint32_t bits=(s>>9)|0x3f800000u;float f;std::memcpy(&f,&bits,4);return f-1;}
float zp(std::uint32_t& s){return 2*random(s)-1;}
float f32(const std::vector<unsigned char>& b,unsigned i){std::uint32_t bits=(std::uint32_t(b[i])<<24)|(unsigned(b[i+1])<<16)|(unsigned(b[i+2])<<8)|b[i+3];float f;std::memcpy(&f,&bits,4);return f;}
bool finite(Position p){return std::isfinite(p.x)&&std::isfinite(p.y)&&std::isfinite(p.z);}
bool read(const std::string& file,std::size_t size,const char* digest,std::vector<unsigned char>& out){
 std::ifstream in(file,std::ios::binary|std::ios::ate);if(!in||in.tellg()!=std::streamoff(size))return false;
 in.seekg(0);out.resize(size);if(!in.read(reinterpret_cast<char*>(out.data()),size))return false;
 std::uint8_t sha[32];pc_netplay_sha::sha256(out.data(),out.size(),sha);const char* hex="0123456789abcdef";
 for(unsigned i=0;i<32;++i)if(hex[sha[i]>>4]!=digest[2*i]||hex[sha[i]&15]!=digest[2*i+1])return false;
 return true;
}
void birth(DownEmitter& b,const std::vector<unsigned char>& r){
 // JPAVolumePoint consumes three ZH draws before init_p's lifetime draw.
 Position omni{random(b.seed)-.5f,random(b.seed)-.5f,random(b.seed)-.5f};
 float length=std::sqrt(omni.x*omni.x+omni.y*omni.y+omni.z*omni.z);
 EffectParticle p;p.position=b.origin;p.life=50*(1-f32(r,8+0x54)*random(b.seed));
 float speed=length>0?.2f/length:0;p.velocity={speed*omni.x,speed*omni.y,speed*omni.z};
 (void)zp(b.seed); // zero initial velocity ratio still consumes the draw
 p.moment=1-f32(r,8+0x64)*random(b.seed);(void)random(b.seed);
 constexpr unsigned esp=252;
 p.scaleOut=1+zp(b.seed)*f32(r,esp+0x24);
 p.waveRandom=1+zp(b.seed)*f32(r,esp+0x44);
 p.angle=std::uint16_t(int(f32(r,esp+0x4c)+f32(r,esp+0x50)*(random(b.seed)-.5f)));
 p.spin=std::int16_t(f32(r,esp+0x54)*(1+f32(r,esp+0x58)*zp(b.seed)));
 if(zp(b.seed)>=f32(r,esp+0x5c))p.spin=-p.spin;
 b.particles.insert(b.particles.begin(),p);++b.births;
}
void step(EffectParticle& p,const std::vector<unsigned char>& r){
 constexpr unsigned esp=252;
 // FLD gravity addType0 accumulates separately from the initial velocity.
 p.gravity.y-=.029999999329447746f;
 p.position.x+=p.moment*p.velocity.x;p.position.y+=p.moment*(p.velocity.y+p.gravity.y);p.position.z+=p.moment*p.velocity.z;
 const float time=p.age/p.life;
 p.scale=p.scaleOut*(1+1.5f*time); // scaleIn/Out timings0, outValue2.5
 float base=f32(r,esp+0x38),out=f32(r,esp+0x30),alpha=base;
 if(time>out)alpha=base+(time-out)*(f32(r,esp+0x3c)-base)/(1-out);
 // Alpha flick uses the source signed16 JMath table angle. Quantize to its
 // table frontier (2048 entries, index from the high11 bits of theta).
 int theta=int(p.waveRandom*p.age*16384*(1-f32(r,esp+0x40)));
 unsigned index=(std::uint16_t(theta)>>5);
 float wave=std::sin(float(index)*6.2831853071795864769f/2048);
 alpha*=1+f32(r,esp+0x48)*(wave-1)*.5f;
 p.alpha=float(static_cast<unsigned char>(255*std::max(0.f,std::min(1.f,alpha))))/255;
 p.angle=std::uint16_t(p.angle+p.spin);
}
}
bool DownEffects::load(const std::string& dir,std::string& e){
 if(!mEmitters.empty())return reject(e,"source77 Down resource reload with live emitters");
 mReady=false;
 std::array<std::vector<unsigned char>,3> resources;std::vector<unsigned char> texture;
 const char* names[]={"shijimi-0015.jpa","shijimi-0016.jpa","shijimi-0017.jpa"};
 const char* hashes[]={"c3168c19baa3e9757dd86c2b616de0a0fb36a0952f1d656728c5e4753a5c1506","e6d3ad4dce615f325b97fcd6840bd846aaeb300f9cf5638ec6f51e6dc735536f","1319bec150dbdafed6ce8bab9b523ad1c5cf7046ea67b8d6313e5100bad5084e"};
 for(unsigned i=0;i<3;++i)if(!read(dir+"/"+names[i],360,hashes[i],resources[i]))return reject(e,"source77 Down requires genuine GPVE01 21/22/23 bytes");
 if(!read(dir+"/IP2_stardust1_i.tex1",4160,"a58fb129361f1631d7619040f16318981bf35046d36fab740076b124a0b941f1",texture))return reject(e,"source77 Down requires genuine stardust texture");
 mResources=std::move(resources);mTexture=std::move(texture);mRemainder=0;mReady=true;e.clear();return true;
}
bool DownEffects::create(std::uint64_t id,Position pos,Color color,std::uint32_t seed,std::string& e){
 if(!mReady||!id||!finite(pos)||unsigned(color)>2)return reject(e,"source77 Down invalid unprepared emitter");
 // TSync create is idempotent while its emitter is still active.
 auto found=mEmitters.find(id);if(found!=mEmitters.end()){if(!found->second.emitting)return reject(e,"source77 Down restart requires a fresh emitter handle");return follow(id,pos,e);}
 DownEmitter b;b.origin=pos;b.resource=23-unsigned(color);b.seed=seed;mEmitters.emplace(id,std::move(b));e.clear();return true;
}
bool DownEffects::follow(std::uint64_t id,Position pos,std::string& e){auto i=mEmitters.find(id);if(i==mEmitters.end()||!finite(pos))return reject(e,"source77 Down lost actual emitter");i->second.origin=pos;e.clear();return true;}
bool DownEffects::fade(std::uint64_t id,std::string& e){auto i=mEmitters.find(id);if(i!=mEmitters.end())i->second.emitting=false;e.clear();return true;}
bool DownEffects::tick(float seconds,const Clipping& clipping,std::string& e){
 if(!mReady||!clipping||!std::isfinite(seconds)||seconds<0||seconds>2)return reject(e,"source77 Down invalid tick");
 mRemainder+=seconds*30;while(mRemainder>=1){mRemainder-=1;
  for(auto& pair:mEmitters){auto& b=pair.second;const auto& r=resource(b.resource);
   if(b.emitting){float count=.3499999940395355f*(1+0*zp(b.seed));b.count+=count;int n=int(b.count);b.count-=n;if(b.first&&count>0&&count<1)n=1;if(!b.clipped)for(int i=0;i<n;++i)birth(b,r);b.first=false;}
   // TSync/StaticClipping executeAfter runs after dynamics create. Previous
   // clipping blocks births; current actual scene clipping blocks drawing.
   b.clipped=clipping(pair.first,b.origin,30.f);
   for(auto& p:b.particles)if(++p.age<int(p.life))step(p,r);
   b.particles.erase(std::remove_if(b.particles.begin(),b.particles.end(),[](const EffectParticle& p){return p.age>=int(p.life);}),b.particles.end());
  }
  for(auto i=mEmitters.begin();i!=mEmitters.end();)if(!i->second.emitting&&i->second.particles.empty())i=mEmitters.erase(i);else ++i;
 }e.clear();return true;
}
std::size_t DownEffects::particles()const{std::size_t n=0;for(const auto& pair:mEmitters)n+=pair.second.particles.size();return n;}
} }
