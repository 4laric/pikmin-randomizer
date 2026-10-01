// Visual plan for the Anode Beetle (ElecBug 28) electric effects. Engine-free so
// the lifecycle is unit tested (tools/p2_elecbug_fx_test.cpp).
//
// Source (decomp ElecBug.cpp / efx/TDnkms.h, efx::TDnkmsEffect):
//   startChargeEffect (StateCharge::init, StateChildCharge::init)   TDnkmsHoudenB
//       "charge sparks" chasing the beetle.
//   startDischargeEffect(partner) (StateDischarge KEYEVENT_2, frame 8)
//       TDnkmsHoudenA glow on BOTH beetles + TDnkmsThunderA (zap electricity) and
//       TDnkmsThunderB (zap glow/sparks) synced to both positions = the arc.
//   fade() (finishPartnerAndEffect: Discharge/ChildDischarge cleanup, Reverse init,
//       no-partner Charge exits, onKill) ends every one of them.
// P1 has none of those assets, so stand-ins follow the Electric Dweevil plan
// (pc_p2_otakara_fxplan.h, native #63): EFF_Rocket_Biri (268), EFF_Spider_DeadBombSparks
// (189) and EFF_Spider_SmallSparks (190) at 2.5-3x, through p2attackfx.
#pragma once
#include <cmath>

namespace p2elecbugfx {

// Mirrors the State enum of pc_p2_elecbug.cpp (kept numeric to stay engine-free).
enum StateId { Charge = 4, Discharge = 5, ChildCharge = 6, ChildDischarge = 7 };

// Effects exist from the charge start until the link ends (fade()).
inline bool effectsLive(int state) {
    return state == Charge || state == Discharge || state == ChildCharge || state == ChildDischarge;
}
// HoudenB sparks: every charge/discharge tick window, refreshed every 3 ticks.
constexpr unsigned kHaloEvery = 3;
constexpr float kHaloScale = 2.5f;
// Thunder: only the discharging generator, from KEYEVENT_2 (frame 8) while it has a partner.
inline bool arcLive(int state, bool hasPartner, float stateTime) {
    return state == Discharge && hasPartner && stateTime >= 8.0f / 30.0f;
}
constexpr float kArcScale = 4.5f;
constexpr unsigned kBoltRgb = 0xFFF2A0; // pale lightning yellow
constexpr float kArcJitter = 9.0f;
constexpr float kPieceLength = 45.0f; // world units per layoutArc piece
constexpr int kMaxPieces = 7;         // 7 x 6 points x 2 strands stays under the generator cap
inline int arcPieces(float length) {
    int n = int(std::ceil(length / kPieceLength));
    return n < 1 ? 1 : (n > kMaxPieces ? kMaxPieces : n);
}

} // namespace p2elecbugfx
