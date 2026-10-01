#pragma once

#include <array>

enum class P2KurageVariant { Lesser, Greater };
enum class P2KurageCaptureKind { Empty, Pikmin, Captain };
enum class P2KurageEvent { None, Captured, Released, Killed };

struct P2KurageSlot {
    P2KurageCaptureKind kind = P2KurageCaptureKind::Empty;
    int target = -1;
    float stomachTime = 0.0f;
};

// Source-backed capture/lifecycle contract. This module intentionally has no
// Creature or renderer dependency; the native adapter supplies eligibility,
// attachment and release callbacks when integrating it into an actor.
class P2KurageCapturePolicy {
public:
    explicit P2KurageCapturePolicy(P2KurageVariant variant, float killTime = 16.0f);

    void reset();
    P2KurageEvent capturePikmin(int target, bool eligible);
    P2KurageEvent captureCaptain(int target, bool eligible);
    P2KurageEvent update(float delta, bool ownerAlive, bool bittered);
    P2KurageEvent interrupt(int target);
    P2KurageEvent onDeath();
    const std::array<P2KurageSlot, 10>& slots() const { return mSlots; }

private:
    int freeSlot(P2KurageCaptureKind kind) const;
    P2KurageEvent releaseSlot(int index, bool killed);

    P2KurageVariant mVariant;
    float mKillTime;
    // Source mMaxSuckPiki defaults to ten. Greater's captain path has two
    // mouth slots, while Pikmin stomach entries use the full bounded table.
    std::array<P2KurageSlot, 10> mSlots;
};
