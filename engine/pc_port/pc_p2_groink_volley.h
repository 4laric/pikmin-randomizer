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
    struct Emission { bool valid = false; std::size_t count = 0; };
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

private:
    std::array<P2GroinkPolicy, kCapacity> mNodes{};
    std::array<bool, kCapacity> mPrimary{};
    std::array<std::size_t, kCapacity> mActive{}, mInactive{};
    std::array<Terminal, kCapacity> mTerminals{};
    std::size_t mActiveCount = 0, mInactiveCount = 0, mTerminalCount = 0;
};
