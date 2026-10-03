#pragma once
#include "pc_p2_original_shijimi_group.h"
#include <array>
#include <cstdint>
#include <map>
#include <functional>
#include <vector>
namespace p2original { namespace shijimi {
struct EffectParticle {
 Position position,velocity,gravity;
 float life=0,moment=1,scaleOut=1,scale=1,alpha=0,waveRandom=1;
 int age=-1;std::uint16_t angle=0;std::int16_t spin=0;
};
struct DownEmitter {
 Position origin;unsigned resource=0;std::uint32_t seed=0;
 bool first=true,emitting=true,clipped=false;float count=0;
 unsigned births=0;std::vector<EffectParticle> particles;
};
// Strictly the genuine GPVE01 TChouDown 21/22/23 resources. Emitter seeds
// belong to the particle service, independently of EnemyBase birth RNG.
class DownEffects {
public:
 bool load(const std::string& directory,std::string&);
 bool create(std::uint64_t handle,Position,Color,std::uint32_t seed,std::string&);
 bool follow(std::uint64_t handle,Position,std::string&);
 bool fade(std::uint64_t handle,std::string&);
 using Clipping=std::function<bool(std::uint64_t,Position,float)>;
 bool tick(float seconds,const Clipping& actualSceneClipping,std::string&);
 bool ready()const{return mReady;}
 std::size_t particles()const;
 const std::map<std::uint64_t,DownEmitter>& emitters()const{return mEmitters;}
 const std::vector<unsigned char>& texture()const{return mTexture;}
 const std::vector<unsigned char>& resource(unsigned id)const{return mResources.at(id-21);}
private:
 bool mReady=false;float mRemainder=0;
 std::array<std::vector<unsigned char>,3> mResources;
 std::vector<unsigned char> mTexture;std::map<std::uint64_t,DownEmitter> mEmitters;
};
} }
