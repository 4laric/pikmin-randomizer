#pragma once
#include <cstdint>
using u8=std::uint8_t;
struct C {u8 r=9,g=9,b=9,a=255;};
struct S {std::int16_t r=9,g=9,b=9,a=255;};
struct Reg {S mAnimatedColor;};
struct PVWTevInfo {Reg mTevColRegs[3];C mKonstColors[4];};
constexpr unsigned MATFLAG_PVW=1;
struct Material {unsigned mFlags=1;PVWTevInfo* mTevInfo=nullptr;};
class Graphics;
