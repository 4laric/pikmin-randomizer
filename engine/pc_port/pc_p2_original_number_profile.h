#pragma once
#include <cstdint>

// Literal original P2 numeric resources, independent of corpse, Pelplant and
// native config IDs. Metadata only: no birth, render, animation or SAVE proof.
namespace p2originalnumber {
enum class Size : std::uint8_t { One=1, Five=5 };
enum class Color : std::uint8_t { Blue=0, Red=1, Yellow=2 };
enum class Dynamics : std::uint8_t { Never, Lod };
struct Profile {
 Size size;
 unsigned carryMin,carryMax,matchingYield,nonmatchingYield;
 float radius,pickRadius,height,inertiaScaling;
 unsigned particleCount;
 float particleSize,friction;
 Dynamics dynamics;
 const char* configName;
 const char* modelMember;
 const char* configSha256;
 const char* modelSha256;
};
// Borrowed immutable process-lifetime literals. Unsupported sizes return null.
const Profile* profile(unsigned number) noexcept;
const Profile* profile(Size) noexcept;
bool validColor(Color) noexcept;
// Actual matching receiver color selects the literal Onion yield. Invalid
// size/color leaves out unchanged; native callers authenticate the receiver.
bool yield(Size,Color pelletColor,Color receiverColor,unsigned& out) noexcept;
}
