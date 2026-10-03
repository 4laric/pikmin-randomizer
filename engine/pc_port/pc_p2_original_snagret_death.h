#pragma once
#include <cmath>
namespace p2original { namespace bulblax_snagret {
// SnakeCrowState::StateDead KEYEVENT_3 at authored frame131 calls throwupItem;
// KEYEVENT_END at165 retires the actor. SnakeCrow's deathProcedure hook is empty.
// Only original SnakeCrow uses this policy; inherited AP/P1 paths are unchanged.
struct DeathItems {
 bool emitted=false;
 bool advance(bool original,float previousSeconds,float currentSeconds){
  constexpr float eventSeconds=131.0f/30.0f;
  constexpr float floatTolerance=0.0001f;
  if(!original||emitted||!std::isfinite(previousSeconds)||!std::isfinite(currentSeconds)
   ||previousSeconds<0||currentSeconds<previousSeconds)return false;
  if(previousSeconds<eventSeconds-floatTolerance&&currentSeconds>=eventSeconds-floatTolerance){emitted=true;return true;}
  return false;
 }
};
} }
