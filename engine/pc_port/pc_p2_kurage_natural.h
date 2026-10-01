#pragma once
// rd-p2-kurage-natural (#832): engine-free reachability audit for the
// private-adapter Kurage (source id 57) natural-kill gate.
//
// The campaign binding for source 57 is `binding=private_adapter` with
// `type=0` (a generated P1 TEKI_Frog body vehicle).  This header encodes the
// P1 target-acquisition predicates a natural (unforced) kill depends on, so
// the lane can prove -- with a test rather than prose -- exactly where the
// chain stalls before it spends an engine run.
//
// Source anchors (native worktree, read-only):
//   src/plugPikiKando/piki.cpp:951            Piki::graspSituation target filter
//   src/plugPikiKando/aiAttack.cpp:297        ActAttack::exec airborne re-target
//   src/plugPikiNakata/tekiinteraction.cpp:41 InteractAttack::actTeki receiver
//
// Nothing in this module changes engine state; it is a pure predicate/verdict
// surface consumed by tools/p2_kurage_natural_test.cpp (engine-free) and
// tools/p2_kurage_natural_runtime.cpp (the guarded replacement-main fixture).
namespace p2kurage_natural {

// Facts a P1 FreeMode Pikmin's `graspSituation` evaluates when it scans the
// Teki manager for something to attack.
struct AcquisitionFacts {
    bool alive;
    bool visible;
    bool organic;
    bool stickTo; // already attached to some object (skip)
    bool flying;  // CF_IsFlying on the Teki
};

// Mirrors src/plugPikiKando/piki.cpp:951:
//   teki->isVisible() && teki->isAlive() && !teki->isFlying()
//   && teki->isOrganic() && !teki->isStickTo()
bool free_squad_acquires(const AcquisitionFacts& facts);

// Mirrors src/plugPikiKando/aiAttack.cpp:297 (ActAttack::exec), which abandons
// the current target while it is airborne unless the Pikmin is already stuck:
//   !mPiki->isStickTo() && (mOther.isFlying() || !mOther.isVisible())
bool attack_holds(bool pikiStickTo, bool targetFlying, bool targetVisible);

// InteractAttack::actTeki (src/plugPikiNakata/tekiinteraction.cpp:41-68) has
// family-local rejections for Hana/ElecBug/Kogane/Armor/Dangomushi/Snakejoint/
// LongLegs but none for Kurage, so a generated attack on source 57 is accepted
// by the receiver.  The natural-kill stall is therefore target acquisition,
// not the damage receiver.
bool damage_receiver_accepts(unsigned sourceId);

// Where the natural chain stops, in the order the brief enumerates it.
enum class Stall {
    None,
    NoEngagementFreeSquadSkipsFlying, // free squad never acquires the adapter
    NoEngagementFlyingRetarget,       // ActAttack drops it mid-approach
    NoDamageReceiver,                 // a family-local rejection swallowed hits
    NoDeath,
    NoCorpse,
    NoCarry,
    NoReceipt,
};

const char* stall_token(Stall stall);
// The exact source location that does not fire for this stall.
const char* stall_callsite(Stall stall);

struct Audit {
    bool damage_receiver_open;      // InteractAttack accepts source 57
    bool free_squad_acquires;       // a FreeMode squad can target the adapter
    bool grounded_only_by_injection;// adapter is airborne unless grounded
    Stall stall;
};

// The production adapter (`pc_port/pc_p2_kurage_teki.cpp`) keeps the bound
// source-57 actor grounded with the injected `groundAndSeal` concession
// (`finishFlying()` + seek) every tick; the source-faithful FSM path keeps it
// airborne.  `adapterAirborneWithoutInjection` states which is true on the run
// under audit.
Audit audit_private_adapter(bool adapterAirborneWithoutInjection,
                            bool groundedOnlyByInjection);

// Marker contract consumed by tools/p2_kurage_transport_test.cpp's natural-log
// checker for a future natural run (corpse -> carried -> delivered -> one
// onion:p2:57 receipt).
extern const char* const kNaturalCorpseMarker;
extern const char* const kNaturalCarryMarker;
extern const char* const kNaturalDeliveredMarker;

} // namespace p2kurage_natural
