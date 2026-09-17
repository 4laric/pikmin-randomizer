#pragma once
#include <cstring>
// Native M1/M2 flora conversion + scenery policy (#697, issue #697).
//
// M1: P1-side Candypop/Pelplant conversion execution (swallow-to-sprout,
// arrival/receiver wiring points). M2: prop-flora scenery registration.
// Engine-free and dependency-free: this header uses no engine types, so the
// guarded fixture can compile and run it standalone. Shared-engine hook
// points (arrival callbacks, receiver routing, visual binding) are declared
// as narrow seams for #171 owner + #186 hook review; this module never
// touches shared files.
//
// Source rules (read-only research refs, verified by #663):
// - Pom.h:37-39,73: getEnemyTypeID returns mPomID (B=3 R=4 Y=5 P=6 W=7 Q=8,
//   base=82); Pom.cpp:280-322 shotPikmin: one sprout per stuck Pikmin times
//   mShotMultiplier, own-colour slot refund except RandPom; PomState
//   Open/Swing/Shot transitions on key events.
// - Reference predicate experimental/pikmin2_flora_assets.py
//   reference_conversion: Pelplant pellet sizes 1/5/10/20 yield the same;
//   every bud lifetime slots ip01=5, queen multiplier ip13=9.
// - Prop flora: single-clip convention (plantsMgr.h:36-39); general parms
//   repurposed as LOD/floor volumes (plantsMgr.cpp:18-21,46-48).

namespace p2flora {

enum Species {
    Pelplant = 0,
    BluePom = 1,
    RedPom = 2,
    YellowPom = 3,
    BlackPom = 4,
    WhitePom = 5,
    RandPom = 6,
    SpeciesCount = 7,
};

inline bool isCandypop(Species species)
{
    return species >= BluePom && species <= RandPom;
}

inline bool isQueen(Species species) { return species == RandPom; }

// Lifetime conversion slots per bud (proper ip01=5 for ordinary buds,
// ip11=1 for the queen). Mirrors the reference predicate exactly, including
// the queen budget.
inline int lifetimeSlots(Species species)
{
    if (!isCandypop(species)) return 0;
    return isQueen(species) ? 1 : 5;
}

// Sprout multiplier (proper ip13=9 for the queen, 1 otherwise).
inline int shotMultiplier(Species species)
{
    return isQueen(species) ? 9 : 1;
}

struct ConvertRequest {
    Species species;
    int swallowed;   // Pikmin swallowed during the open window (>= 0)
    bool ownColour;  // swallowed Pikmin match the bud colour
};

struct ConvertResult {
    bool ok;
    int sprouts;    // sprouts birthed by shotPikmin
    int slotsUsed;  // lifetime slots consumed (non-queen only)
    bool refund;    // own-colour slot refunded (non-queen only)
};

inline ConvertResult convertSwallow(ConvertRequest request)
{
    ConvertResult out = {false, 0, 0, false};
    if (request.species < 0 || request.species >= SpeciesCount) return out;
    if (request.swallowed < 0) return out;
    if (request.species == Pelplant) {
        const int size = request.swallowed;
        if (size != 1 && size != 5 && size != 10 && size != 20) return out;
        out.ok = true;
        out.sprouts = size;
        return out;
    }
    if (!isCandypop(request.species)) return out;
    if (request.swallowed > lifetimeSlots(request.species)) return out;
    out.ok = true;
    out.sprouts = request.swallowed * shotMultiplier(request.species);
    if (!isQueen(request.species)) {
        out.slotsUsed = request.swallowed;
        out.refund = request.ownColour && request.swallowed > 0;
    }
    return out;
    // Note: the queen is also budget-checked above (ip11=1), matching the
    // reference predicate; only slotsUsed/refund stay queen-exempt.
}

// Bounded per-bud lifetime converter: enforces the slot budget across shots.
struct Converter {
    Species species;
    int slotsLeft;
    explicit Converter(Species kind = BluePom)
        : species(kind), slotsLeft(lifetimeSlots(kind))
    {
    }
    int shotsLeftForTest() const { return slotsLeft; }
    ConvertResult shot(int swallowed, bool ownColour)
    {
        ConvertResult out = {false, 0, 0, false};
        if (!isCandypop(species) || swallowed < 0) return out;
        if (!isQueen(species) && swallowed > slotsLeft) return out;
        out = convertSwallow({species, swallowed, ownColour});
        if (out.ok && !isQueen(species)) {
            slotsLeft -= swallowed;
            if (out.refund) slotsLeft += 1;
        }
        return out;
    }
};

// M2: prop-flora scenery registration record. Visual binding itself stays a
// #186-reviewed engine seam; this registry only records which prop identity
// occupies which scenery slot, so double-registration fails closed.
struct ScenerySlot {
    const char *identity;
    int slot;
    bool occupied;
};

class SceneryRegistry {
public:
    static const int kMaxSlots = 8;

    SceneryRegistry() : count_(0)
    {
        for (int i = 0; i < kMaxSlots; ++i) slots_[i].occupied = false;
    }

    // Returns the slot index, or -1 when the identity is unknown/empty, the
    // registry is full, or the identity is already registered.
    int registerProp(const char *identity, int slot)
    {
        if (!identity || !identity[0] || slot < 0) return -1;
        for (int i = 0; i < count_; ++i) {
            if (slots_[i].occupied
                && std::strcmp(slots_[i].identity, identity) == 0) return -1;
            if (slots_[i].occupied && slots_[i].slot == slot) return -1;
        }
        if (count_ >= kMaxSlots) return -1;
        slots_[count_].identity = identity;
        slots_[count_].slot = slot;
        slots_[count_].occupied = true;
        ++count_;
        return count_ - 1;
    }

    int findProp(const char *identity) const
    {
        if (!identity) return -1;
        for (int i = 0; i < count_; ++i) {
            if (slots_[i].occupied
                && std::strcmp(slots_[i].identity, identity) == 0) return i;
        }
        return -1;
    }

    int count() const { return count_; }

private:
    ScenerySlot slots_[kMaxSlots];
    int count_;
};

// Shared-engine hook seams (M1 arrival/receiver wiring, M2 visual binding).
// Declared for #171 owner + #186 hook review; intentionally unimplemented
// here so no shared file is touched by this slice.
struct EngineHooks {
    // Called when swallowed Pikmin arrive at the bud mouth (Pom.cpp:184
    // collisionCallback equivalent). Return false to refuse the swallow.
    bool (*admitSwallow)(Species species, int pikiKind);
    // Called to route each birthed sprout to a receiver (ItemPikihead
    // birth equivalent, Pom.cpp:307). Return false when unreceived.
    bool (*receiveSprout)(Species species, int sproutIndex);
    // Called to bind a registered prop to its scenery visual.
    bool (*bindScenery)(const char *identity, int slot);
};

} // namespace p2flora
