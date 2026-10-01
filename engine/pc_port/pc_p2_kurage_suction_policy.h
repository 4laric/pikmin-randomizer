// Engine-free decisions for the Jellyfloat (Kurage 57 / OniKurage 72) suction
// and stomach, owner playtest 2026-09-30 (#960).
//
// 1. Who can be sucked. Source Kurage::suckPikmin / OniKurage::suckPikmin take
//    every live Pikmin under the bell that is not already stuck to the body
//    (Kurage.cpp:498-526; the stimulus is InteractSuikomi_Test). The first
//    port cut gated admission on P1 Piki::mayIstick(), which is true only for a
//    Pikmin that is mid-throw or in attack/carry mode. A Pikmin standing or
//    following the captain under the bell therefore never entered the suction
//    and the body "just hovered". The eligibility below is the P1 state set in
//    which taking control of a Pikmin is safe (its action is abandoned by the
//    captain seam, the receiver then owns its velocity).
// 2. Where it is held. The source stomach is the `suck` collision part on the
//    Proom joint, so a captured Pikmin ends inside the bell at that joint, not
//    under the body origin (see pc_p2_kurage_proom.h).
#pragma once

#include <cmath>

namespace p2kuragesuck {

// include/PikiState.h ids (asserted against the engine header in
// pc_p2_kurage_own_host.cpp).
constexpr int kStateNormal = 0;
constexpr int kStateFlying = 14;   // in the air after a throw: never taken
constexpr int kStatePush = 20;
constexpr int kStatePushPiki = 21;
constexpr int kStateEmotion = 31;

// A Pikmin the suction may take control of. `mayIstick` keeps every Pikmin the
// old gate admitted (attack/carry mode) that is not mid-throw.
inline bool stateSuckable(int pikiState)
{
    return pikiState == kStateNormal || pikiState == kStatePush || pikiState == kStatePushPiki
        || pikiState == kStateEmotion;
}

inline bool pikiSuckable(bool alive, bool stuckToSomething, int pikiState, bool mayIstick)
{
    if (!alive || stuckToSomething) return false;
    if (pikiState == kStateFlying) return false;
    return stateSuckable(pikiState) || mayIstick;
}

// Deterministic resting offset (body frame, XZ only) of the n-th Pikmin held in
// one stomach: a golden-angle ring of radius `ringFraction * radius`, so ten
// Pikmin do not stack on one point. The stomach part is a sphere; the ring stays
// inside it.
struct HoldOffset { float x = 0.0f, y = 0.0f, z = 0.0f; };
inline HoldOffset holdOffset(int index, float radius, float ringFraction = 0.45f)
{
    constexpr float kGolden = 2.39996323f;
    const float angle = float(index) * kGolden;
    const float r = radius * ringFraction * (index == 0 ? 0.0f : 1.0f);
    HoldOffset o;
    o.x = std::cos(angle) * r;
    o.z = std::sin(angle) * r;
    o.y = 0.0f;
    return o;
}

} // namespace p2kuragesuck
