#pragma once
#include <cstdint>

// Lane 12 engine-free second-captain roster (#130).
//
// NaviMgr owns one Navi per captain slot. The only state that cannot be read
// straight off a Navi is the *selection* state: which slot is currently
// controlled and which slots are down. This helper owns exactly that, with no
// engine dependency, so NaviMgr::getActiveNavi()/getAliveOrima()/
// getDeadOrima()/informOrimaDead() can stay thin delegators and the standalone
// policy test can exercise the selection rules under g++.
//
// Single-captain safety: with count == 1, reset() leaves activeIndex() == 0,
// no slot is dead, and active()/firstAlive() always return 0. Nothing here
// changes the one-Navi path until a second Navi actually exists.
//
// Source basis (native/pikmin2-research, include/Game/Navi.h): Navi::mNaviIndex,
// GET_OTHER_NAVI(navi) == 1 - mNaviIndex, NaviMgr::getActiveNavi,
// getAliveOrima, getDeadOrima, informOrimaDead, mDeadNavis, mNaviDeadFlags[2].
class P2CaptainRoster {
public:
    static constexpr int kSlots = 2;

    // GET_OTHER_NAVI equivalent: the other captain index, or -1 if invalid.
    static int otherIndex(int index)
    {
        return index == 0 ? 1 : (index == 1 ? 0 : -1);
    }

    // A slot index is usable when it is non-negative, inside the live count and
    // inside this helper's fixed two-slot capacity.
    static bool validIndex(int index, int count)
    {
        return index >= 0 && index < count && index < kSlots;
    }

    void reset()
    {
        mActiveIndex = 0;
        mDeadMask    = 0;
    }

    int activeIndex() const { return mActiveIndex; }
    void setActiveIndex(int index) { mActiveIndex = index; }

    bool isDead(int index) const
    {
        return index >= 0 && index < kSlots && (mDeadMask & (1u << index)) != 0;
    }
    void markDead(int index)
    {
        if (index >= 0 && index < kSlots) mDeadMask |= (1u << index);
    }
    void markAlive(int index)
    {
        if (index >= 0 && index < kSlots) mDeadMask &= ~(1u << index);
    }

    int firstAlive(int count) const
    {
        for (int i = 0; i < count && i < kSlots; ++i) {
            if (!isDead(i)) return i;
        }
        return -1;
    }
    int firstDead(int count) const
    {
        for (int i = 0; i < count && i < kSlots; ++i) {
            if (isDead(i)) return i;
        }
        return -1;
    }

    // The controllable index: the current active slot if it is still valid and
    // alive, otherwise the first alive slot, otherwise -1.
    int active(int count) const
    {
        if (validIndex(mActiveIndex, count) && !isDead(mActiveIndex)) return mActiveIndex;
        return firstAlive(count);
    }

private:
    int mActiveIndex          = 0;
    std::uint32_t mDeadMask   = 0;
};
