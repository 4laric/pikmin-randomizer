#pragma once

#include "pc_p2_kabuto_cannon.h"
#include "pc_p2_kabuto_events.h"
#include "pc_p2_kabuto_muzzle.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <memory>

// Generation-keyed, fixed-capacity per-actor binding table for the Cannon Beetle
// lane (lane 20, #169 / #424 / #425). This is the per-actor lifetime foundation
// the host needs before it can bind a real Kabuto/Rkabuto/Fkabuto actor: it owns,
// per bound actor, the shared attachment `Instance` (identity token), the sampled
// attack-clock event adapter (#431), the moving-muzzle provider and the Cannon
// Beetle fire FSM, so a host tick can drive
//
//   sampled attack clock -> P2KabutoEvent -> fire FSM -> moving muzzle -> Stone
//
// entirely in binding-local state. It is engine-free and adds no shared hook; the
// clip/joint indices are bank-local, so the `Instance` and the muzzle always share
// one immutable bank.
//
// Lifetime / generation rules (same contract as `p2attach::Instance` and the
// `P2GroinkStrikeTracker` bound):
//   * `bind` mints a fresh 64-bit generation handle; callers advance/release by
//     handle, never by the raw actor identity. A handle is valid exactly while its
//     slot lives.
//   * `release`/`reset` tombstone the slot, so a stale handle can never read or
//     fire again. A recycled actor identity receives a *new* handle, so a handle
//     held from the previous owner can never reach the new one.
//   * capacity is fixed and bounded; binding past it fails closed (returns 0).
//     An unknown handle, invalid bank, or unresolved species clip/joint also fails
//     closed rather than silently degrading.
//
// The FSM is started (surfaced -> Wait, Fkabuto -> FixStay) at bind. The host
// starts each attack motion with `beginAttack` (species-appropriate Attack/
// FixAttack transition) when its own behavior chooses to attack; `advance` then
// consumes the shared clock's authored KEYEVENT_2 into exactly one Stone birth and
// handles the one-shot End. Host health/target/flick facts are supplied per tick.

// Opaque generation handle. 0 is never a valid handle.
using P2KabutoBindingToken = std::uint64_t;

struct P2KabutoAdvanceOut {
    bool accepted = false;   // the tick was valid and applied to this binding
    int events = 0;          // adapter events delivered to the FSM this tick
    bool key2 = false;       // a KEYEVENT_2 crossing was seen
    bool end = false;        // the one-shot attack motion ended
    P2KabutoAction action = P2KabutoAction::None; // last FSM action for the tick
    bool fired = false;      // a Stone birth was produced this tick
    P2KabutoStoneBirth birth; // valid iff `fired`
};

class P2KabutoBindingTable {
public:
    static constexpr std::size_t kCapacity = 8;
    static constexpr int kMaxEvents = 4; // Key2 + End per advance

    // Bind an actor identity token to a species over `bank`. Returns a fresh
    // generation handle (>0), or 0 if `bank` is null/invalid, the species clip or
    // mouth joint cannot be resolved against it, or the table is at capacity.
    P2KabutoBindingToken bind(std::uint64_t identity, P2KabutoSpecies species,
                              std::shared_ptr<const p2attach::Bank> bank);

    // Reconfigure a live handle for a new species/bank in place. The handle stays
    // the same on success (same owner); validation happens before the old state is
    // dropped. Returns 0 and invalidates the handle on failure.
    P2KabutoBindingToken rebind(P2KabutoBindingToken token, P2KabutoSpecies species,
                                std::shared_ptr<const p2attach::Bank> bank);

    // Drop a live handle. Returns false for an unknown/stale handle.
    bool release(P2KabutoBindingToken token);
    void reset();

    bool bound(P2KabutoBindingToken token) const { return find(token) != nullptr; }
    std::size_t size() const;
    bool full() const { return size() >= kCapacity; }

    // Start one attack motion for a live binding: move the species-appropriate
    // FSM into Attack/FixAttack and start the sampled attack clock sized to the
    // resolved source clip with its KEYEVENT_2 frame. Idempotent while an attack
    // is already running. Fails closed on an unknown token.
    bool beginAttack(P2KabutoBindingToken token);

    // Drive one host tick. On a KEYEVENT_2 the muzzle is sampled through the bound
    // `Instance` and the pending FireStone is consumed into exactly one
    // `P2KabutoStoneBirth`; the one-shot End is consumed in the same call. `tick`
    // must be non-decreasing per handle and `sourceFrameDelta` non-negative/finite.
    // A no-op tick (no attack running) returns accepted=true with zero events.
    bool advance(P2KabutoBindingToken token, const p2attach::Affine& owner,
                 double sourceFrameDelta, std::uint64_t tick, float faceDir,
                 const P2KabutoHostState& host, P2KabutoAdvanceOut& out);

    P2KabutoPhase phase(P2KabutoBindingToken token) const;
    bool attackActive(P2KabutoBindingToken token) const;
    std::uint64_t identity(P2KabutoBindingToken token) const;
    const P2KabutoMouthBinding* mouthBinding(P2KabutoBindingToken token) const;

private:
    struct Entry {
        bool used = false;
        P2KabutoBindingToken token = 0;
        std::uint64_t identity = 0;
        P2KabutoSpecies species = P2KabutoSpecies::Kabuto;
        std::shared_ptr<const p2attach::Bank> bank;
        p2attach::Instance instance;
        p2attach::Token attachToken = 0;
        P2KabutoEventAdapter adapter;
        P2KabutoMuzzle muzzle;
        P2KabutoMouthBinding mouth;
        P2KabutoCannon cannon;
        bool attackActive = false;
        std::uint64_t lastTick = 0;
        bool sampled = false;

        // `p2attach::Instance` is non-copyable/non-assignable, so a slot is reset
        // field-by-field rather than by assignment.
        void clear()
        {
            used = false;
            token = 0;
            identity = 0;
            species = P2KabutoSpecies::Kabuto;
            bank.reset();
            instance.reset();
            attachToken = 0;
            adapter = P2KabutoEventAdapter{};
            muzzle = P2KabutoMuzzle{};
            mouth = P2KabutoMouthBinding{};
            cannon = P2KabutoCannon{};
            attackActive = false;
            lastTick = 0;
            sampled = false;
        }
    };

    Entry* find(P2KabutoBindingToken token);
    const Entry* find(P2KabutoBindingToken token) const;
    static P2KabutoBindingToken fresh();

    std::array<Entry, kCapacity> mEntries;
};
