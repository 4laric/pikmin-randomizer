#pragma once
#include <cstdint>
#include <string>
#include <vector>
namespace p2watage {
struct Vec { float x=0,y=0,z=0; };
struct Particle {
 Vec position,velocity; float life=0,moment=1,drag=1,scale=1,alpha=0;
 int age=-1; std::uint16_t angle=0; std::int16_t spin=0;
};
struct Burst { Vec origin; std::uint32_t seed=0; std::vector<Particle> particles; };
// Only the audited GPVE01 PID 0x1e4 resource is admitted. Raw legal bytes stay
// private. This is not a general JPAC implementation or a P1 effect alias.
class Effect {
public:
 bool load(const std::string& directory,std::string& error);
 bool ready()const{return mReady;}
 bool touch(Vec origin,std::uint32_t seed,std::string& error);
 bool tick(float seconds,std::string& error);
 void clear(){mBursts.clear();mRemainder=0;}
 const std::vector<Burst>& bursts()const{return mBursts;}
 const std::vector<unsigned char>& texture()const{return mTexture;}
 std::size_t particles()const;
 unsigned emissions()const{return mEmissions;}
 static void fields(Particle&,std::uint32_t& seed,unsigned mask=7);
private:
 bool mReady=false; float mRemainder=0; unsigned mEmissions=0;
 std::vector<unsigned char> mResource,mTexture;
 std::vector<Burst> mBursts;
};
}
