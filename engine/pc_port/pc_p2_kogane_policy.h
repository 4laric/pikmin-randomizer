#pragma once
#include "pc_p2_animation.h"
#include <map>
#include <set>
#include <string>
#include <limits>
namespace p2kogane {
struct Config{int karada=-1;std::map<std::uint32_t,int> ids;std::map<std::uint32_t,int> treasures;std::vector<p2animation::Clip> clips;};
inline bool read(std::istream& in,Config& out){
 Config c;std::string s;int count;
 if(!(in>>s)||s!="P2_KOGANE_NATIVE_1"||!(in>>s>>c.karada)||s!="karada"||c.karada<0||c.karada>64||!(in>>s>>count)||s!="actors"||count<1||count>100)return false;
 for(int i=0;i<count;++i){unsigned long long id;int species;if(!(in>>id>>species)||id>0xffffffffULL||species<9||species>11||!c.ids.emplace(std::uint32_t(id),species).second)return false;}
 // Optional per-generator treasure section: zero or more `treasure <generator>
 // <pellet_value>` tokens between the actors and the first clip. The P1 host has
 // no P2 treasure item, so pellet_value (1 or 5) selects a stand-in number pellet
 // for that generator's first flip (createTreasureItem, Kogane.cpp:386-414).
 // Absent means the audited table applies; every generator must be a declared
 // actor and no duplicate is allowed.
 if(!(in>>s))return false;
 while(s=="treasure"){unsigned long long generator;int value;
  if(!(in>>generator>>value)||generator<1||generator>0xffffffffULL||(value!=1&&value!=5)||!c.ids.count(std::uint32_t(generator))||!c.treasures.emplace(std::uint32_t(generator),value).second)return false;
  if(!(in>>s))return false;
 }
 std::set<std::string> seen;
 for(int n=0;n<3;++n){p2animation::Clip clip;clip.name=s;if(!(in>>clip.count>>clip.duration)||!seen.insert(clip.name).second||(clip.name!="move"&&clip.name!="wait"&&clip.name!="damage")||clip.count<2||clip.count>24||clip.duration<1||clip.duration>10000)return false;
 for(int i=0;i<clip.count;++i){int f;if(!(in>>f)||f<0||f>=clip.duration||(i&&f<=clip.frames.back()))return false;clip.frames.push_back(f);}
 if(clip.frames.front()!=0||clip.frames.back()!=clip.duration-1)return false;c.clips.push_back(clip);if(n<2&&!(in>>s))return false;}
 if(in>>s)return false;out=c;return true;
}
inline int karada(int id){return id==9?60:id==10?100:id==11?15:-1;}

// rd-p2-kogane-engagement (#835): engine-free engagement contract for the
// finite flip/drop/escape species. Every predicate mirrors a production
// callsite (cited); nothing here changes behavior. Kogane is never hostile,
// killable or corpse-producing through this path: registered contact flips,
// unregistered contact follows the host damage path.
//
// Traced player-directed contact path (verified at native a76341272):
//   Navi::throwPiki (navi.cpp:2969) + PIKISTATE_Flying transit
//     -> ballistic flight under Piki physics
//     -> Piki::collisionCallback Teki branch (piki.cpp:2079): organic Teki in
//        FormationMode switches the Pikmin to AttackMode, OR the landed Pikmin
//        acquires the beetle via graspSituation (piki.cpp:951: visible, alive,
//        not flying, organic; a grounded Chappy-proxy beetle qualifies)
//     -> ActJumpAttack stick-attack, state 5 (aiAttack.cpp:708): the stuck
//        Pikmin issues InteractAttack via stickObj->stimulate (holds while
//        stuck, aiAttack.cpp:297)
//     -> BTeki::stimulate (tekibteki.cpp:842): actCommon (interactBattle.
//        cpp:437, visible gate) then actTeki
//     -> InteractAttack::actTeki (tekiinteraction.cpp:46):
//        pc_p2_kogane_attacked flips a registered beetle and takes no attack
//        damage; unregistered actors fall through to the host damage path.
//        InteractPress (tekiinteraction.cpp:124 -> pc_p2_kogane_pressed) is the
//        injected fixture path only, never runtime acceptance.
// No production callsite is missing: the InteractAttack hook is committed in
// the integration base, so this lane adds no family behavior change and no
// shared-file edit. The predicates below pin that contract for tests.
namespace engagement {
// Source constants (Koganemushi.cpp/Wealthy.cpp/Fart.cpp, KoganeState.cpp).
inline constexpr int kMaxFlips = 3;        // terminal press count; third drop escapes
inline constexpr int kDropFrame = 7;       // createItem event frame of the 50-frame damage clip
inline constexpr int kDamageClipFrames = 50;
inline constexpr int kTickHz = 30;         // P1 host tick rate used by doFlip/doDrop timing
// doFlip (pc_p2_kogane.cpp:202): 7/50 of the source clip scaled to host ticks.
inline constexpr float kDropDelaySec =
    float(kDropFrame) / float(kDamageClipFrames) * (float(kDamageClipFrames) / float(kTickHz));
// doFlip (pc_p2_kogane.cpp:203): further presses held for the full damage clip.
inline constexpr float kRecoverSec = float(kDamageClipFrames) / float(kTickHz);

inline bool isSourceId(int id) { return id >= 9 && id <= 11; }

enum class ContactOutcome {
    Flip,               // registered, live, settled beetle: one flip + frame-7 drop scheduled
    SwallowedRecovering,// contact during the damage-clip recovery window (doFlip:199)
    SwallowedDropPending,// contact while a flip drop is still pending (doFlip:199)
    TerminalEscaped,    // flips already at cap: burrowed/fled, no corpse, no receipt
    HostDamagePath,     // unregistered actor: falls through to host damage handling
    DeadNoEffect,       // dead actor: doFlip swallows via mDeadState (doFlip:199)
};

struct FlipState {
    bool registered = false; // family actors map hit (pc_p2_kogane_source_id >= 0)
    bool dead = false;       // BTeki mDeadState != 0
    bool escaped = false;    // terminal burrow/flee already taken
    int flips = 0;           // press count so far (source mFlipCount)
    bool dropPending = false;// dropTimer >= 0
    bool recovering = false; // recoverTimer > 0
};

inline ContactOutcome contactOutcome(const FlipState& s)
{
    if (!s.registered) return ContactOutcome::HostDamagePath;
    if (s.dead) return ContactOutcome::DeadNoEffect;
    // Setup restores escaped beetles at the cap without re-spawning drops
    // (pc_p2_kogane.cpp:300-309); update escapes on the third drop
    // (pc_p2_kogane.cpp:398-405). Either way the cap is terminal.
    if (s.escaped || s.flips >= kMaxFlips) return ContactOutcome::TerminalEscaped;
    if (s.dropPending) return ContactOutcome::SwallowedDropPending;
    if (s.recovering) return ContactOutcome::SwallowedRecovering;
    return ContactOutcome::Flip;
}

// Ordinary Onion ledger key (pc_p2_kogane.cpp:174-179): exactly-once per
// (seed, "enemy:<id>", "<generator>", "flip<N>"), granted only for flip
// outcomes 1..3. A fourth contact has no encounter key: the cap above makes
// it TerminalEscaped, so it can never re-arm a receipt.
inline std::string receiptIdentity(int id) { return "enemy:" + std::to_string(id); }
inline std::string receiptEncounter(int flip) { return "flip" + std::to_string(flip); }
inline bool receiptEncounterValid(int flip) { return flip >= 1 && flip <= kMaxFlips; }

// Restart merge (pc_p2_kogane.cpp:96-100,215,296-299): in-process snapshot
// and on-disk sidecar keep the maximum flip count per generator, so a
// reset+setup cycle within or across processes can never farm drops again.
inline int mergeRestoredFlips(int existing, int incoming)
{
    return incoming > existing ? incoming : existing;
}

// Free-squad acquisition predicate (piki.cpp:951): a grounded, visible, live,
// organic Teki that nothing is stuck to is acquirable. The registered beetle
// (Chappy proxy) satisfies every term, so normal contact needs no injection.
struct AcquisitionFacts {
    bool visible = false;
    bool alive = false;
    bool flying = false;
    bool organic = false;
    bool targetStuckTo = false; // teki->isStickTo(): the target stuck to something
};
inline bool freeSquadAcquires(const AcquisitionFacts& f)
{
    return f.visible && f.alive && !f.flying && f.organic && !f.targetStuckTo;
}

// ActAttack airborne hold (aiAttack.cpp:297): the attack abandons only when
// the Pikmin is not stuck and the target is airborne or invisible.
inline bool attackHolds(bool pikiStuckTo, bool targetFlying, bool targetVisible)
{
    return !(!pikiStuckTo && (targetFlying || !targetVisible));
}

// Direct-collision attack branch (piki.cpp:2079): a FormationMode Pikmin that
// is not pressed and may C-stick-attack switches to AttackMode on contact
// with a live organic Teki/Boss.
struct CollisionFacts {
    bool doCStickAttack = false;
    bool colliderIsTekiOrBoss = false;
    bool colliderOrganic = false;
    bool formationMode = false;
    bool pressedState = false;
};
inline bool collisionAttacks(const CollisionFacts& f)
{
    return f.doCStickAttack && f.colliderIsTekiOrBoss && f.colliderOrganic
        && f.formationMode && !f.pressedState;
}
} // namespace engagement
}
