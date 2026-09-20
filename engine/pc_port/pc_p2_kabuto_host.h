#pragma once

#include "pc_p2_kabuto_binding.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <memory>

// Generated-session Cannon Beetle family host (lane 20, #169 / #424 / #425).
//
// The generated-session dispatch (`genteki.cpp`, #454) hands a live spawned
// actor plus its `Generator` to `pc_p2_generated_bind`. This host is the family
// adapter for that path: it maps the ENEMY_P2 source identity (Kabuto 75 /
// Rkabuto 95 / Fkabuto 96) to the family species, owns one binding per actor
// (reusing `P2KabutoBindingTable` for the FSM, moving muzzle and Stone birth)
// and converts the actor's live `TekiAnimator` reading into the shared
// sampled-animation feed:
//
//   TekiAnimator(motion, counter, frameCount)
//     -> sourceFrameDelta -> P2KabutoEventAdapter
//     -> Kabuto fire FSM -> moving muzzle -> P2KabutoStoneBirth
//
// The P1 actor's own AI still owns behavior and locomotion; this host observes
// the actor's authored `TekiAnimator::Attack` motion. On attack entry it starts
// the family attack clock, and each tick feeds the clock the forward source
// frame delta implied by the live animation counter. A KEYEVENT_2 crossing (the
// authored source fire frame) births exactly one `P2KabutoStoneBirth` from the
// sampled mouth joint. When the live motion leaves Attack, any unfinished source
// clock is dropped so a later attack can never inherit the previous motion's
// fire. It is engine-free: the game bridge supplies actor identity and animator
// facts, and owns no shared hook.

// One live-animator reading. `motion` is `getCurrentMotionIndex()`,
// `counter` the `getCounter()` frame position, `frameCount` the
// `getFrameCount()` total, and `attackMotion` true while the actor is in the
// family's source attack motion.
struct P2KabutoHostAnimator {
    long motion = 0;
    long frameCount = 0;
    double counter = 0.0;
    bool attackMotion = false;
};

// Per-tick feed derived from two consecutive animator readings. `valid` is false
// when the readings cannot be used (non-finite/negative counter, < 2 frames).
struct P2KabutoHostFeed {
    bool valid = false;
    bool begin = false;   // entered the attack motion (start the source clock)
    bool restart = false; // attack counter wrapped/restarted (restart the clock)
    bool leave = false;   // left the attack motion (drop any unfinished clock)
    double sourceFrameDelta = 0.0;
};

class P2KabutoHost {
public:
    static constexpr std::size_t kCapacity = P2KabutoBindingTable::kCapacity;

    // Map an ENEMY_P2 source id to the family species. False for any identity
    // this family cannot host (75/95/96 are the only accepted values).
    static bool species_for_source(unsigned source, P2KabutoSpecies& out);

    // Bind or rebind `identity` (a stable per-actor id, e.g. the generator uid)
    // to `species` over `bank`. Returns a fresh generation handle (>0) or 0 on an
    // invalid bank, an unresolved species clip/joint, or capacity overflow.
    // Rebinding an already-bound identity reuses its handle in place.
    P2KabutoBindingToken bind(std::uint64_t identity, P2KabutoSpecies species,
                              std::shared_ptr<const p2attach::Bank> bank);
    bool release(std::uint64_t identity);
    void reset();

    bool bound(std::uint64_t identity) const;
    P2KabutoBindingToken token(std::uint64_t identity) const;
    P2KabutoSpecies species(std::uint64_t identity) const;
    P2KabutoPhase phase(std::uint64_t identity) const;
    std::size_t size() const;

    // Convert the previous/current live-animator readings into the feed against
    // the resolved source clip duration (source frames). Pure and engine-free.
    // The source-frame delta scales the live animation phase to the authored
    // source clip so the authored KEYEVENT_2 fires at the same proportional
    // point of the attack motion.
    static P2KabutoHostFeed feed(const P2KabutoHostAnimator& previous,
                                 const P2KabutoHostAnimator& current,
                                 int sourceDuration);

    // Advance one host tick from `animator`. Starts the family attack motion on
    // attack entry, forwards the derived source-frame delta to the bound
    // adapter, samples the moving muzzle on KEYEVENT_2 and fills `out.birth`.
    // `owner`/`faceDir` are the actor world transform/facing; `host` the
    // per-tick health/target snapshot. Returns false on an unknown handle, an
    // invalid reading, or a rejected advance.
    bool advance(std::uint64_t identity, const P2KabutoHostAnimator& animator,
                 const p2attach::Affine& owner, float faceDir,
                 const P2KabutoHostState& host, P2KabutoAdvanceOut& out);

    // Human-readable species name for logs (never null).
    static const char* species_name(P2KabutoSpecies species);

private:
    struct Entry {
        std::uint64_t identity = 0;
        P2KabutoBindingToken token = 0;
        P2KabutoSpecies speciesKind = P2KabutoSpecies::Kabuto;
        std::shared_ptr<const p2attach::Bank> bank;
        int sourceDuration = 0;
        P2KabutoHostAnimator last;
        bool sampled = false;
        std::uint64_t tick = 0;
    };

    Entry* find(std::uint64_t identity);
    const Entry* find(std::uint64_t identity) const;

    std::array<Entry, kCapacity> mEntries;
    P2KabutoBindingTable mTable;
};

class Teki;

// Generated-session bridge (line adaptation of the source `pc_p2_generated_bind`
// Kabuto arm, #424). `genteki.cpp` calls this at birth for a P2-bound actor;
// `pc_p2_enemy.cpp` owns the definition. Maps source 75/95/96 to the family
// species, loads the staged attachment bank once
// (`assets/p2-kabuto-attach.txt`) and binds `generatorId` into the process-wide
// host. Fails closed (false, no abort) for any other source, a wrong vehicle
// type, a missing bank or a refused bind. The per-actor tick, forget and reset
// ride inside `pc_p2_snow_update` / `pc_p2_snow_forget` / `pc_p2_snow_reset`,
// so no other translation unit needs a declaration.
bool pc_p2_kabuto_bind_dynamic(Teki* actor, unsigned generatorId, unsigned sourceId);
