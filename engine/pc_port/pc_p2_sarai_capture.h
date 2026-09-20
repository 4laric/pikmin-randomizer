// Swooping Snitchbug (Sarai, enemy ID 23) mouth capture/attachment receiver,
// dependency-free policy. Transcribed from US GPVE01 rev 0
// native/pikmin2-research:
//   src/plugProjectNishimuraU/Sarai.cpp (initMouthSlots, fallMeckGround,
//                                       flickStickTarget, catchTarget,
//                                       getCatchTargetNum, getStickPikminNum)
//   include/Game/Entities/Sarai.h (parms, mouth-clamp geometry)
//
// This header owns no engine objects and performs no I/O. Hosts supply the
// per-candidate facts read from the live Pikmin manager and consume the
// returned admission/selection/drop decisions. It composes
// pc_p2_sarai_policy.h for the shared parms/constants.
//
// Semantics:
//   * catchTarget() -> EnemyFunc::eatPikmin(this, nullptr): only living
//     Pikmin that are not already mouth-stuck, not already stuck to this
//     Sarai (body latch), and inside the mouth slot radius (15.0f) are
//     admitted, nearest-first, up to the two free slots. The captured Pikmin
//     are CARRIED, never swallowed: the P2 Sarai holds them on its mouth and
//     later drops them in FallMeck.
//   * fallMeckGround(): every mouth-stuck creature receives InteractFallMeck
//     (general mAttackDamage) plus a downward setVelocity(-fp41 fallMeck speed
//     200). This is the drop/damage receiver.
//   * flickStickTarget(): every mouth-stuck creature receives InteractFlick
//     (knockback 10, damage 0) and detaches harmlessly. This is the escape
//     (Flick/Damage entry) receiver.
//
// The actual stick-to-mouth binding stays in pc_p2_sarai_capture_bridge.*.
#ifndef PC_P2_SARAI_CAPTURE_H
#define PC_P2_SARAI_CAPTURE_H

#include <cmath>
#include "pc_p2_sarai_policy.h"

namespace p2sarai {

using p2sarai::kMouthRadius;
using p2sarai::kMouthSlots;

// Sarai.cpp flickStickTarget(): InteractFlick(knockback 10, damage 0).
constexpr float kFlickKnockback = 10.0f;
constexpr float kFlickDamage = 0.0f;

// General mAttackDamage default applied by fallMeckGround()'s InteractFallMeck.
// The Demon/Sarai family shares the P2 enemyparm attack damage (10).
constexpr float kFallMeckDamage = 10.0f;

// Slot index sentinel returned when a Pikmin is not captured in a mouth slot.
constexpr int kNoSlot = -1;

// Sarai.cpp getAttackableTarget()/catchTarget() eligibility filter for one
// candidate Pikmin. Distance/angle geometry is left to the host (which owns the
// live mouth centres); this decides the source admission predicates only.
struct MouthCandidate {
    bool alive = true;
    bool isPikmin = true;
    bool stuckToMouth = false;   // already stuck to any mouth
    bool stickerIsSelf = false;  // mSticker == this Sarai (body-latched)
    bool withinMouthRadius = true; // distance <= slot radius (15.0f)
};

// EnemyFunc::eatPikmin candidate test (matches getAttackableTarget's
// isAlive/isPikmin/!isStickToMouth/mSticker filter, plus the mouth radius).
inline bool captureEligible(const MouthCandidate& candidate)
{
    return candidate.alive && candidate.isPikmin && !candidate.stuckToMouth
        && !candidate.stickerIsSelf && candidate.withinMouthRadius;
}

// Nearest-first selection for the two mouth slots, mirroring a CandidateMgr
// pass that picks the closest eligible candidate and repeats. Writes up to
// kMouthSlots chosen indices into `chosen` and returns the number chosen.
// `sqrDistXZ` is per-candidate squared XZ distance to the Sarai position.
inline int selectMouthCaptures(const MouthCandidate* candidates, int count,
                               const float* sqrDistXZ, int* chosen)
{
    if (!candidates || !sqrDistXZ || !chosen || count < 0 || count > 64) return 0;
    bool used[64] = {false};
    int picked = 0;
    for (int slot = 0; slot < kMouthSlots; ++slot) {
        int best = -1;
        float bestDist = 0.0f;
        for (int i = 0; i < count; ++i) {
            if (used[i] || !captureEligible(candidates[i]) || !std::isfinite(sqrDistXZ[i])
                || sqrDistXZ[i] < 0.0f) {
                continue;
            }
            if (best < 0 || sqrDistXZ[i] < bestDist) {
                bestDist = sqrDistXZ[i];
                best = i;
            }
        }
        if (best < 0) break;
        used[best] = true;
        chosen[picked++] = best;
    }
    return picked;
}

// fallMeckGround(): released captives receive a downward velocity of -fp41.
// Parms::fallMeckSpeed (fp41) defaults to 200.0f.
inline float fallMeckReleaseVelocity(float fallMeckSpeed)
{
    return std::isfinite(fallMeckSpeed) && fallMeckSpeed >= 0.0f ? -fallMeckSpeed : -200.0f;
}

// fallMeckGround(): damage applied through the release interaction.
inline float fallMeckDamage(float attackDamage)
{
    return std::isfinite(attackDamage) && attackDamage >= 0.0f ? attackDamage : kFallMeckDamage;
}

} // namespace p2sarai

#endif
