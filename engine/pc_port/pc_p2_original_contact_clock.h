#pragma once
#include <cmath>
#include <cstdint>
namespace p2original {
// Retail Navi::formationable/updateKaisanDisable: frame count, not seconds.
// Saved original captain payloads must restore this explicitly; no inference
// from P1 state or wild flags. Native ordinary captains never set this clock.
class ContactClock {
 std::uint8_t remaining=0;
public:
 unsigned frames() const noexcept {return remaining;}
 bool formationable() const noexcept {return remaining==0;}
 void reset() noexcept {remaining=0;}
 void disband() noexcept {remaining=60;}
 bool restore(unsigned frames) noexcept {
  if(frames>60)return false;
  remaining=static_cast<std::uint8_t>(frames);return true;
 }
 bool update(float x,float y,float z) noexcept {
  if(!std::isfinite(x)||!std::isfinite(y)||!std::isfinite(z))return false;
  // Source qLength() = sqrtf(x*x+y*y+z*z), strict >20 boundary.
  const float speed=std::sqrt(x*x+y*y+z*z);
  if(!std::isfinite(speed))return false;
  if(remaining&&speed>20.0f)--remaining;
  return true;
 }
};
}
