#pragma once
#include "pc_p2_shijimi_effect.h"
#include <memory>
class Graphics;
namespace p2original { namespace shijimi {
struct EffectColors { unsigned char r=255,g=255,b=255,a=255; };
class NativeDownEffects {
public:
 explicit NativeDownEffects(DownEffects::Clipping actualSceneClipping);
 ~NativeDownEffects();
 bool load(const std::string& privateBank,std::string&);
 bool create(std::uint64_t,Position,Color,std::uint32_t particleServiceSeed,std::string&);
 bool follow(std::uint64_t,Position,std::string&);
 bool fade(std::uint64_t,std::string&);
 bool tick(float seconds,std::string&);
 void draw(Graphics&,EffectColors globalPrimary,EffectColors globalEnvironment);
 std::size_t particles()const;
private:
 struct Impl;std::unique_ptr<Impl> m;
};
} }
// Ordinary native manager simulation advances detached effects exactly once.
void pc_p2_shijimi_effect_tick_all(float seconds);
