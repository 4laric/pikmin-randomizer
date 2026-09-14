#include "pc_p2_onikurage_mouth.h"

#include <cmath>

namespace p2onikurage {

void MouthSlots::reset()
{
    mSlots = {};
}

bool MouthSlots::capture(int target, bool eligible)
{
    if (!eligible || target < 0) return false;
    for (int i = 0; i < kMouthSlotCount; ++i) {
        if (mSlots[i].occupied) continue;
        mSlots[i] = {};
        mSlots[i].occupied = true;
        mSlots[i].target = target;
        mSlots[i].observed = true;
        return true;
    }
    return false;
}

Event MouthSlots::advanceDefaultOffset(int slot)
{
    if (slot < 0 || slot >= kMouthSlotCount) return Event::None;
    Slot& s = mSlots[slot];
    if (!s.occupied) return Event::None;
    const float restX = kDefaultKamuJointOffset[slot];
    const bool away = std::fabs(s.offset.x - restX) > kOffsetTolerance
        || std::fabs(20.0f + s.offset.y) > kOffsetTolerance
        || std::fabs(s.offset.z) > kOffsetTolerance;
    if (!away) return Event::None;
    s.offset.x = interpolate(s.offset.x, restX, kDefaultInterpolate);
    s.offset.y = approach(s.offset.y, kRestOffsetY, kDefaultApproachY);
    s.offset.z *= 0.8f;
    const bool settled = std::fabs(s.offset.x - restX) < kOffsetTolerance
        && std::fabs(20.0f + s.offset.y) < kOffsetTolerance
        && std::fabs(s.offset.z) < kOffsetTolerance;
    return settled ? Event::MouthReady : Event::None;
}

bool MouthSlots::isNaviSucked() const
{
    for (const Slot& s : mSlots) {
        if (s.occupied) return true;
    }
    return false;
}

bool MouthSlots::isFinishNaviSuck() const
{
    for (int i = 0; i < kMouthSlotCount; ++i) {
        const Slot& s = mSlots[i];
        if (!s.occupied) continue;
        if (std::fabs(s.offset.x - kDefaultKamuJointOffset[i]) > kOffsetTolerance
            || std::fabs(20.0f + s.offset.y) > kOffsetTolerance
            || std::fabs(s.offset.z) > kOffsetTolerance) {
            return false;
        }
    }
    return true;
}

int MouthSlots::occupiedCount() const
{
    int count = 0;
    for (const Slot& s : mSlots) {
        if (s.occupied) ++count;
    }
    return count;
}

void MouthSlots::setOffset(int slot, const MouthOffset& offset)
{
    if (slot < 0 || slot >= kMouthSlotCount) return;
    mSlots[slot].offset = offset;
}

FlickResult MouthSlots::flick(int slot, bool check, float naviX, float naviZ,
                              float enemyX, float enemyZ)
{
    FlickResult result;
    if (slot < 0 || slot >= kMouthSlotCount) return result;
    Slot& s = mSlots[slot];
    if (!s.occupied) return result;

    const float targetX = check ? kDefaultKamuJointOffset[slot] : kFlickKamuJointOffset[slot];
    const float targetY = check ? kCheckOffsetY : kFlickOffsetY;
    s.offset.x = approach(s.offset.x, targetX, kFlickApproachX);
    s.offset.y = approach(s.offset.y, targetY, kFlickApproachY);
    if (std::fabs(s.offset.x - targetX) >= kOffsetTolerance
        || std::fabs(s.offset.y - targetY) >= kOffsetTolerance) {
        return result;
    }

    // Release branch (`flickStickNavi`): InteractFlick then InteractBomb.
    float dx = naviX - enemyX;
    float dz = naviZ - enemyZ;
    const float length = std::sqrt(dx * dx + dz * dz);
    if (length > 1e-6f) {
        dx = dx / length * kFlickSeparation;
        dz = dz / length * kFlickSeparation;
    } else {
        dx = 0.0f;
        dz = 0.0f;
    }
    result.applied = true;
    result.flick = true;
    result.bomb = true;
    result.dirX = dx;
    result.dirZ = dz;
    // The host's Navi stimulus detaches the captain; drop the slot occupancy
    // while retaining the source mSuckedNavis[i] bookkeeping so escapeCheckNavi
    // still reports the release.
    s.occupied = false;
    return result;
}

Event MouthSlots::escapeCheck(int slot, bool slotOccupied, bool bittered)
{
    if (slot < 0 || slot >= kMouthSlotCount) return Event::None;
    Slot& s = mSlots[slot];
    if (slotOccupied) {
        if (!s.observed) {
            s.observed = true;
            s.occupied = true;
        }
        return Event::None;
    }
    if (s.observed) {
        s.observed = false;
        s.occupied = false;
        return bittered ? Event::EnemyDied : Event::EscapeReleased;
    }
    return Event::None;
}

int MouthSlots::onDeath()
{
    int released = 0;
    for (Slot& s : mSlots) {
        if (s.occupied || s.observed) ++released;
        s = {};
    }
    return released;
}

} // namespace p2onikurage
