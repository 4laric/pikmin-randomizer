#include "pc_p2_kurage.h"

#include <cmath>

P2KurageCapturePolicy::P2KurageCapturePolicy(P2KurageVariant variant, float killTime)
    : mVariant(variant), mKillTime(killTime)
{
    reset();
}

void P2KurageCapturePolicy::reset()
{
    mSlots = {};
    for (P2KurageSlot& slot : mSlots) slot.target = -1;
}

int P2KurageCapturePolicy::freeSlot(P2KurageCaptureKind kind) const
{
    if (kind == P2KurageCaptureKind::Captain && mVariant != P2KurageVariant::Greater) return -1;
    const int limit = kind == P2KurageCaptureKind::Captain ? 2 : static_cast<int>(mSlots.size());
    for (int i = 0; i < limit; ++i) {
        if (mSlots[i].kind == P2KurageCaptureKind::Empty) return i;
    }
    return -1;
}

P2KurageEvent P2KurageCapturePolicy::capturePikmin(int target, bool eligible)
{
    if (!eligible || target < 0) return P2KurageEvent::None;
    const int index = freeSlot(P2KurageCaptureKind::Pikmin);
    if (index < 0) return P2KurageEvent::None;
    mSlots[index] = { P2KurageCaptureKind::Pikmin, target, 0.0f };
    return P2KurageEvent::Captured;
}

P2KurageEvent P2KurageCapturePolicy::captureCaptain(int target, bool eligible)
{
    if (mVariant != P2KurageVariant::Greater || !eligible || target < 0) return P2KurageEvent::None;
    const int index = freeSlot(P2KurageCaptureKind::Captain);
    if (index < 0) return P2KurageEvent::None;
    mSlots[index] = { P2KurageCaptureKind::Captain, target, 0.0f };
    return P2KurageEvent::Captured;
}

P2KurageEvent P2KurageCapturePolicy::releaseSlot(int index, bool killed)
{
    if (index < 0 || index >= static_cast<int>(mSlots.size())
        || mSlots[index].kind == P2KurageCaptureKind::Empty) return P2KurageEvent::None;
    mSlots[index] = {};
    mSlots[index].target = -1;
    return killed ? P2KurageEvent::Killed : P2KurageEvent::Released;
}

P2KurageEvent P2KurageCapturePolicy::interrupt(int target)
{
    for (int i = 0; i < static_cast<int>(mSlots.size()); ++i) {
        if (mSlots[i].target == target) return releaseSlot(i, false);
    }
    return P2KurageEvent::None;
}

P2KurageEvent P2KurageCapturePolicy::update(float delta, bool ownerAlive, bool bittered)
{
    if (!std::isfinite(delta) || delta < 0.0f) return P2KurageEvent::None;
    P2KurageEvent event = P2KurageEvent::None;
    for (int i = 0; i < static_cast<int>(mSlots.size()); ++i) {
        P2KurageSlot& slot = mSlots[i];
        if (slot.kind == P2KurageCaptureKind::Empty) continue;
        if (!ownerAlive) {
            if (event == P2KurageEvent::None) event = releaseSlot(i, false);
            else releaseSlot(i, false);
            continue;
        }
        if (slot.kind == P2KurageCaptureKind::Pikmin && !bittered) {
            slot.stomachTime += delta;
            if (slot.stomachTime >= mKillTime) {
                if (event == P2KurageEvent::None) event = releaseSlot(i, true);
                else releaseSlot(i, true);
            }
        }
    }
    return event;
}

P2KurageEvent P2KurageCapturePolicy::onDeath()
{
    P2KurageEvent event = P2KurageEvent::None;
    for (int i = 0; i < static_cast<int>(mSlots.size()); ++i) {
        if (event == P2KurageEvent::None) event = releaseSlot(i, false);
        else releaseSlot(i, false);
    }
    return event;
}
