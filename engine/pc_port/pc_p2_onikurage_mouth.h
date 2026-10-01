// Bounded host policy for the Greater Spotted Jellyfloat (OniKurage, ID 72)
// captain mouth slots.
//
// Transcribed from US GPVE01 rev 0 native/pikmin2-research
// src/plugProjectNishimuraU/OniKurage.cpp:
//   initMouthSlots (251), suckNavi (597), updateCollPartOffset (651),
//   isFinishNaviSuck (681), isNaviSucked (701), flickStickNavi (714),
//   escapeCheckNavi (753).
//
// The PC host has no P2 MouthSlots/MouthCollPart, no animated `Proom` joint,
// no `InteractSuikomi_Test`/`InteractSarai` and no `InteractFlick`/`InteractBomb`
// stimulus. This module is therefore dependency-free: it owns the two captain
// mouth slots and returns the source decisions (capture, rest-offset arrival,
// flick/bomb release, bitter escape) for the native adapter to apply to a
// `Navi`. Pikmin suction stays on the shared `pc_p2_kurage_receiver`, because
// OniKurage's Pikmin loop (OniKurage.cpp:562) is Kurage's loop verbatim.
//
// Port adaptations (all approximate the missing engine seams):
//   * Slot identity is an opaque host `target` id, not a `Navi*`.
//   * `capture()` folds `suckNavi`'s free-slot search and `InteractSarai`
//     success into one bounded admission; the host performs the attachment.
//   * `advanceDefaultOffset()` replaces `updateCollPartOffset`'s animated
//     world-matrix read with the source's own interpolate/approach math.
//   * `flick()` returns the `InteractFlick`(FLICK_BACKWARD_ANGLE) and
//     `InteractBomb` decisions with the horizontal separation direction; the
//     host applies them to the captured Navi.
#ifndef PC_P2_ONIKURAGE_MOUTH_H
#define PC_P2_ONIKURAGE_MOUTH_H

#include <array>
#include <cstdint>

namespace p2onikurage {

constexpr int kMouthSlotCount = 2;

// OniKurage.cpp:16-17.
inline constexpr float kDefaultKamuJointOffset[kMouthSlotCount] = { 7.5f, -7.5f };
inline constexpr float kFlickKamuJointOffset[kMouthSlotCount] = { 10.0f, -10.0f };
inline constexpr float kRestOffsetY = -20.0f;   // updateCollPartOffset approach target
inline constexpr float kFlickOffsetY = -50.0f;  // flickStickNavi(false)
inline constexpr float kCheckOffsetY = -75.0f;  // flickStickNavi(true)
inline constexpr float kDefaultInterpolate = 0.2f; // offset.x interpolation factor
inline constexpr float kDefaultApproachY = 7.5f;   // offset.y approach step
inline constexpr float kFlickApproachX = 1.0f;     // flickStickNavi x approach step
inline constexpr float kFlickApproachY = 10.0f;    // flickStickNavi y approach step
inline constexpr float kFlickSeparation = 50.0f;   // source `sep *= 50.0f`
inline constexpr float kOffsetTolerance = 1.0f;    // all source |delta| < 1.0f tests

struct MouthOffset { float x = 0.0f, y = 0.0f, z = 0.0f; };

enum class Event : std::uint8_t {
    None,
    MouthReady,     // updateCollPartOffset reached the rest pose (sound + rumble)
    EscapeReleased, // escapeCheckNavi(): Navi left the mouth without bitterness
    EnemyDied,      // escapeCheckNavi(): bittered Navi escape zeroes enemy health
};

// flickStickNavi() always applies InteractFlick *and* InteractBomb in the same
// frame, so the release decision is a small result rather than one enum.
struct FlickResult {
    bool applied = false; // offset reached the flick/check target this call
    bool flick = false;   // InteractFlick(this, 0, 0, FLICK_BACKWARD_ANGLE)
    bool bomb = false;    // InteractBomb(this, attackDamage, horizontalSeparation)
    float dirX = 0.0f;    // normalised (naviPos - enemyPos) * 50, y = 0
    float dirZ = 0.0f;
};

struct Slot {
    bool occupied = false;
    int target = -1;       // opaque host Navi identity
    bool observed = false;  // source mSuckedNavis[i] bookkeeping
    MouthOffset offset;
};

class MouthSlots {
public:
    void reset();

    // suckNavi(): place a captain in the first free slot. `eligible` is the
    // host geometry decision; a successful capture is the bounded stand-in for
    // a successful `InteractSarai` stimulus.
    bool capture(int target, bool eligible);

    // updateCollPartOffset(): advance the slot's stored offset toward the rest
    // pose with the source interpolation/approach factors. Returns MouthReady
    // on the frame it first settles. A no-op for empty/unknown slots.
    Event advanceDefaultOffset(int slot);

    bool isNaviSucked() const;
    // isFinishNaviSuck(): every occupied slot sits at the default joint offset.
    bool isFinishNaviSuck() const;
    int occupiedCount() const;
    const std::array<Slot, kMouthSlotCount>& slots() const { return mSlots; }
    void setOffset(int slot, const MouthOffset& offset);

    // flickStickNavi(check): advance toward `cFlickKamuJointOffset`/y=-50 (or
    // `cDefaultKamuJointOffset`/y=-75 when `check`), then release with the
    // explicit Flick + Bomb branches. `naviX/naviZ` and `enemyX/enemyZ` mirror
    // `sep = naviPos - mPosition; sep.y = 0; sep.normalise(); sep *= 50`.
    FlickResult flick(int slot, bool check, float naviX, float naviZ,
                      float enemyX, float enemyZ);

    // escapeCheckNavi(): host passes whether the slot currently holds a stuck
    // creature. `bittered` reproduces the source `mHealth = 0.0f` escalation.
    Event escapeCheck(int slot, bool slotOccupied, bool bittered);

    // onDeath()/onKill(): release every captured captain. Returns the count.
    int onDeath();

private:
    std::array<Slot, kMouthSlotCount> mSlots{};
};

// Source approach() (move toward target by at most step).
inline float approach(float current, float target, float step)
{
    if (current < target) { current += step; if (current > target) current = target; }
    else if (current > target) { current -= step; if (current < target) current = target; }
    return current;
}

// Source interpolate() (linear blend).
inline float interpolate(float current, float target, float factor)
{
    return current + (target - current) * factor;
}

} // namespace p2onikurage

#endif
