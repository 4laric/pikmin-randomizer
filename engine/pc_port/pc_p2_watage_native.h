#pragma once
#include "pc_p2_watage_effect.h"
#include <memory>
class Graphics;
namespace p2watage {
struct DrawStats { unsigned batches=0,quads=0,culled=0; };
// One owner per native scene; no pointer into the plant is retained by bursts.
class NativeEffect {
public:
 NativeEffect();~NativeEffect();
 bool load(std::string&);
 bool touch(Vec position,std::string&);
 bool tick(float seconds,std::string&);
 void draw(Graphics&);
 bool cameraControl(Graphics&,std::string&);
 std::size_t particles()const;
 unsigned emissions()const;
 DrawStats draws()const;
private:
 struct Impl;std::unique_ptr<Impl> m;
};
}
// Called once by the ordinary Teki manager simulation update, including after
// the last plant has retired. Rendering never advances the particle clock.
void pc_p2_watage_tick_all(float seconds);
