#pragma once
#include <cstdint>
#include <limits>

struct P2GroinkHandle {
    std::uintptr_t address = 0;
    std::uint64_t generation = 0;
};

// One host-owned registration slot. Address is opaque and never dereferenced.
// Keep this guard alive across scene resets; handles are scoped to this guard.
class P2GroinkLifetime {
public:
    P2GroinkLifetime() = default;
    P2GroinkLifetime(const P2GroinkLifetime&) = delete;
    P2GroinkLifetime& operator=(const P2GroinkLifetime&) = delete;
    P2GroinkHandle attach(std::uintptr_t address) {
        if (!address || current_.generation || pending_) return {};
        const auto serial=next();
        if (!serial) return {};
        current_={address,serial}; return current_;
    }
    bool accepts(P2GroinkHandle handle) const {
        return handle.address && handle.generation &&
            handle.address==current_.address && handle.generation==current_.generation;
    }
    // Revoke before any external pellet-kill/allocation callback. A ticket is
    // authority to finish this one birth attempt, never to access the old actor.
    std::uint64_t beginRevival(P2GroinkHandle handle) {
        if (!accepts(handle)||pending_) return 0;
        current_={}; pending_=next(); return pending_;
    }
    P2GroinkHandle finishRevival(std::uint64_t ticket, std::uintptr_t initializedAddress) {
        if (!ticket || ticket!=pending_) return {};
        pending_=0;
        // Null records failed allocation and consumes the attempt.
        return initializedAddress ? attach(initializedAddress) : P2GroinkHandle{};
    }
    bool detach(P2GroinkHandle handle) {
        if (!accepts(handle)) return false;
        current_={}; return true;
    }
    void reset() { current_={}; pending_=0; } // Never rewind serial numbers.
private:
    std::uint64_t next() {
        if (serial_==std::numeric_limits<std::uint64_t>::max()) return 0;
        return ++serial_;
    }
    P2GroinkHandle current_{};
    std::uint64_t pending_=0, serial_=0;
};
