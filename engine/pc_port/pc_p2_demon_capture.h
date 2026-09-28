#pragma once
#include <cmath>
#include <cstddef>

struct P2DemonCaptain {
    bool alive = true, stuckToMouth = false;
    float angleRadians = 0, distanceSquaredXZ = 0;
};
struct P2DemonTargetInput {
    float homeDistanceSquaredXZ = 0, territoryRadius = 0;
    float viewAngleDegrees = 0, sightRadius = 0;
};
struct P2DemonSelection {
    bool valid = false, found = false;
    std::size_t index = 0;
};
class P2DemonTargetGate {
public:
    bool reset(float value=0) {
        if (!std::isfinite(value)||value<0||value>1.0e6f) return false;
        timer_=value; return true;
    }
    float timer() const { return timer_; }
    P2DemonSelection step(float delta, const P2DemonTargetInput& input,
                         const P2DemonCaptain* captains, std::size_t count, bool active=true) {
        P2DemonSelection out;
        if (!active) { out.valid=true; return out; }
        if (!nonnegative(delta)||delta>0.25f||!nonnegative(input.homeDistanceSquaredXZ)||
            !nonnegative(input.territoryRadius)||!nonnegative(input.sightRadius)||
            !nonnegative(input.viewAngleDegrees)||count>64||(count&&!captains)) return out;
        for (std::size_t i=0;i<count;++i)
            if (!nonnegative(captains[i].distanceSquaredXZ)||!std::isfinite(captains[i].angleRadians)||
                std::fabs(captains[i].angleRadians)>6.28318530718f) return out;
        out.valid=true;
        timer_+=delta; // Source increments per query, not automatically per rendered frame.
        if (!(timer_>3)||!(input.homeDistanceSquaredXZ<input.territoryRadius*input.territoryRadius)) return out;
        for (std::size_t i=0;i<count;++i) {
            const auto& c=captains[i];
            if (c.alive&&!c.stuckToMouth&&std::fabs(c.angleRadians)<=input.viewAngleDegrees*0.017453292519943295f&&
                c.distanceSquaredXZ<input.sightRadius*input.sightRadius) {
                out.found=true; out.index=i; break;
            }
        }
        return out;
    }
private:
    static bool nonnegative(float x) { return std::isfinite(x)&&x>=0&&x<=1.0e12f; }
    float timer_=0;
};

struct P2DemonGrabCheck { bool valid=false, attempt=false; };
// Per live candidate/slot pair, before InteractSarai. This never means accepted
// attachment. Host must re-read occupancy after each stimulate call.
inline P2DemonGrabCheck p2_demon_grab_check(bool alive, bool stuckToMouth,
    bool slotOccupied, float distanceSquared3D, float slotRadius) {
    if (!std::isfinite(distanceSquared3D)||distanceSquared3D<0||distanceSquared3D>1.0e12f||
        !std::isfinite(slotRadius)||slotRadius<0||slotRadius>1.0e6f) return {};
    return {true,alive&&!stuckToMouth&&!slotOccupied&&std::sqrt(distanceSquared3D)<slotRadius};
}
