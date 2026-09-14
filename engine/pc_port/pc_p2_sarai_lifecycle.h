#pragma once
// Lane-owned, dependency-free capture lifecycle for the Swooping Snitchbug
// (Sarai, enemy ID 23).
//
// Sarai ID 23 inherits the Demon ID 32 mouth-stick captor, so the lane must not
// invent a second captain framework. This header is only the lane's explicit,
// engine-free transcription of the contract the shared P1/P2 captor bridge
// already implements (pc_port/pc_p2_demon_bridge.{h,cpp}):
//   * one live binding per owner: owner generation token, selected mouth slot,
//      the stick object/part the captain is attached to, and revoked authority;
//   * pc_demon_forced_release / pc_demon_release / pc_demon_owner_lost /
//     pc_demon_scene_exit all end in the same detach that clears the captain
//     stick pointers and the owner's authority;
//   * the shared escape window (P2DemonEscapeWindow) accumulates directional
//     D-pad down edges while the captain is still attached and transfers that
//     count into the source animation speed / escape roll.
//
// It owns no engine object and never performs the real attachment: the host
// still calls pc_demon_capture / pc_demon_forced_release / pc_demon_release /
// pc_demon_owner_lost unchanged. The model exists so the host bookkeeping and
// the standalone lifecycle test share one detach contract, and so the shared
// bridge/state files stay untouched.
#include <cstdint>
#include <utility>
#include "pc_p2_demon_escape.h"

namespace p2sarai {

// The shared captor escape window is reused verbatim; the lane does not fork it.
using EscapeWindow = P2DemonEscapeWindow;
using EscapeStep = P2DemonEscapeStep;

class CaptureLifecycle {
public:
    void reset()
    {
        mBound = false;
        mCaptain = 0;
        mOwnerToken = 0;
        mStickObject = 0;
        mStickPart = kNoSlot;
        mEscape.reset();
    }

    // Mirrors pc_demon_capture()'s preconditions: one live binding only, a
    // non-zero owner generation and a valid 0/1 mouth slot. A refusal leaves the
    // existing binding untouched so a second captor cannot steal the mouth.
    bool capture(std::uint64_t captain, std::uint64_t ownerToken, unsigned slot)
    {
        if (mBound || !captain || !ownerToken || slot >= 2) return false;
        mCaptain = captain;
        mOwnerToken = ownerToken;
        mStickObject = ownerToken;
        mStickPart = slot;
        mBound = true;
        mEscape.reset();
        return true;
    }

    bool occupied() const { return mBound; }
    bool authority(std::uint64_t ownerToken) const { return mBound && mOwnerToken == ownerToken; }
    std::uint64_t captain() const { return mCaptain; }
    std::uint64_t stickObject() const { return mBound ? mStickObject : 0; }
    unsigned stickPart() const { return mBound ? mStickPart : kNoSlot; }

    // Shared escape window driven by the production pc_demon_escape_tick() call.
    // Only an attached captain accumulates edges; the count transfers into the
    // source animation speed and, once the window passes, an escape. A successful
    // escape detaches, clearing the stick pointers and the owner authority.
    template <class Random>
    EscapeStep escapeTick(bool attached, bool directionalDownEdge, Random&& random)
    {
        if (!mBound) return EscapeStep{};
        EscapeStep step = mEscape.step(attached, directionalDownEdge, std::forward<Random>(random));
        if (step.escape) detach();
        return step;
    }

    // The shared bridge detaches the captain itself (voluntary escape / owner
    // loss); the lane observes that and clears its binding.
    bool observeDetached() { return detach(); }

    // pc_demon_forced_release(): interruption / FallMeck Key3. Refuses a captain
    // that is not the bound one; on success clears pointers and authority.
    bool interrupt(std::uint64_t captain)
    {
        if (!mBound || mCaptain != captain) return false;
        return detach();
    }

    // pc_demon_release(): grounded release without damage.
    bool release(std::uint64_t captain)
    {
        if (!mBound || mCaptain != captain) return false;
        return detach();
    }

    // pc_demon_owner_lost(): only the owner's own generation token revokes, so a
    // stale token is inert.
    bool ownerLost(std::uint64_t ownerToken)
    {
        if (!mBound || mOwnerToken != ownerToken) return false;
        return detach();
    }

    // pc_demon_scene_exit(): unconditional detach while the links are still live.
    bool sceneExit() { return detach(); }

    // Idempotent detach. Returns whether a live binding was actually revoked.
    bool detach()
    {
        if (!mBound) return false;
        reset();
        return true;
    }

private:
    static constexpr unsigned kNoSlot = 0xffffffffu;
    bool mBound = false;
    std::uint64_t mCaptain = 0;
    std::uint64_t mOwnerToken = 0;
    std::uint64_t mStickObject = 0;
    unsigned mStickPart = kNoSlot;
    EscapeWindow mEscape;
};

} // namespace p2sarai
