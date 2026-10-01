#pragma once

#include <pc_p2_groink.h>
#include <array>
#include <cstddef>

// Source MiniHoudaiShotGunMgr subset: three simultaneous shells, six reusable
// nodes, FIFO active/inactive lists. No attack FSM, RNG, effects or receivers.
class P2GroinkVolley {
public:
    static constexpr std::size_t kCapacity = 6;
    static constexpr std::size_t kVolleySize = 3;
    struct Emission {
        bool valid = false;
        std::size_t count = 0;
        // Pool slots of the shells this call spawned, in emission order (slots[0] is the
        // primary shell that carries the camera/rumble flag).
        std::array<std::size_t, kVolleySize> slots{};
    };
    struct Terminal {
        std::size_t slot = 0;
        bool primary = false;
        P2GroinkTerminalStep step;
    };

    P2GroinkVolley() { reset(); }
    void reset();
    // Samples represent source random inputs in emission order. Only samples
    // for available nodes are consumed. Invalid attempted input rejects the
    // whole command without changing pool state (host validation contract).
    Emission emit(const P2GroinkMuzzle&, float speed,
                  const std::array<P2GroinkVec3, kVolleySize>& samples);
    // Host must provide a real trace; a refused trace recycles that shell with
    // an Invalid terminal, never silently advances through terrain. Invalid
    // tick/owner/null callback rejects before mutation. Call only on source ticks.
    bool update(const P2GroinkVec3& owner, float delta, P2GroinkTraceFn, void*);
    std::size_t activeCount() const { return mActiveCount; }
    P2GroinkShell shell(std::size_t slot) const;
    // Read after each update, before the next one. Emission does not erase a
    // previous tick's terminal receipts, even when its slots are reused.
    std::size_t terminalCount() const { return mTerminalCount; }
    const std::array<Terminal, kCapacity>& terminals() const { return mTerminals; }
    // Every shell that advanced in the last update, in source list order, with
    // its source y-10 receiver sweep (MiniHoudaiShotGun.cpp:151-248 runs the
    // sweep on EVERY update, not only on the terminal one). `terminal` marks
    // the recycled step, which alone also carries the splash test.
    struct Segment {
        std::size_t slot = 0;
        bool primary = false;
        bool terminal = false;
        P2GroinkVec3 start, end;
    };
    std::size_t segmentCount() const { return mSegmentCount; }
    const std::array<Segment, kCapacity>& segments() const { return mSegments; }

private:
    std::array<P2GroinkPolicy, kCapacity> mNodes{};
    std::array<bool, kCapacity> mPrimary{};
    std::array<std::size_t, kCapacity> mActive{}, mInactive{};
    std::array<Terminal, kCapacity> mTerminals{};
    std::array<Segment, kCapacity> mSegments{};
    std::size_t mActiveCount = 0, mInactiveCount = 0, mTerminalCount = 0, mSegmentCount = 0;
};
