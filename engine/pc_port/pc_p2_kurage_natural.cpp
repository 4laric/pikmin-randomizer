#include "pc_p2_kurage_natural.h"

namespace p2kurage_natural {

const char* const kNaturalCorpseMarker = "P2_KURAGE57_CORPSE pellet=1";
const char* const kNaturalCarryMarker = "P2_KURAGE57_CARRY";
const char* const kNaturalDeliveredMarker = "P2_KURAGE57_DELIVERED_TO_GOAL";

bool free_squad_acquires(const AcquisitionFacts& facts)
{
    // src/plugPikiKando/piki.cpp:951, verbatim predicate.
    return facts.visible && facts.alive && !facts.flying && facts.organic && !facts.stickTo;
}

bool attack_holds(bool pikiStickTo, bool targetFlying, bool targetVisible)
{
    // src/plugPikiKando/aiAttack.cpp:297: the abandon branch fires only when the
    // Pikmin is not stuck and the target is airborne or invisible.
    const bool abandons = !pikiStickTo && (targetFlying || !targetVisible);
    return !abandons;
}

bool damage_receiver_accepts(unsigned sourceId)
{
    // The family-local InteractAttack rejections live in
    // src/plugPikiNakata/tekiinteraction.cpp:44-60 as the predicates
    // pc_p2_hana_rejects_attack, pc_p2_elecbug_attacked, pc_p2_kogane_attacked,
    // pc_p2_armor_receiver_rejects, pc_p2_dangomushi_invulnerable,
    // pc_p2_snakejoint_invulnerable and pc_p2_long_legs_receiver_rejects.
    // This pin only encodes the two source ids verified in this lane's family
    // install (Kogane 9, ElecBug 28) plus the open default; every other id --
    // including source 57 -- has no Kurage rejection and is accepted.
    switch (sourceId) {
    case 9:  // Kogane -- pc_p2_kogane_attacked
    case 28: // ElecBug -- pc_p2_elecbug_attacked
        return false;
    default:
        return true;
    }
}

const char* stall_token(Stall stall)
{
    switch (stall) {
    case Stall::None: return "none";
    case Stall::NoEngagementFreeSquadSkipsFlying: return "no_engagement_free_squad_skips_flying";
    case Stall::NoEngagementFlyingRetarget: return "no_engagement_flying_retarget";
    case Stall::NoDamageReceiver: return "no_damage_receiver";
    case Stall::NoDeath: return "no_death";
    case Stall::NoCorpse: return "no_corpse";
    case Stall::NoCarry: return "no_carry";
    case Stall::NoReceipt: return "no_receipt";
    }
    return "unknown";
}

const char* stall_callsite(Stall stall)
{
    switch (stall) {
    case Stall::None: return "none";
    case Stall::NoEngagementFreeSquadSkipsFlying:
        return "src/plugPikiKando/piki.cpp:951 (graspSituation skips isFlying())";
    case Stall::NoEngagementFlyingRetarget:
        return "src/plugPikiKando/aiAttack.cpp:297 (ActAttack abandons airborne target)";
    case Stall::NoDamageReceiver:
        return "src/plugPikiNakata/tekiinteraction.cpp:41 (InteractAttack::actTeki)";
    case Stall::NoDeath:
        return "src/plugPikiNakata/tekibteki.cpp:873 (BTeki::makeDamaged)";
    case Stall::NoCorpse:
        return "pc_port/pc_p2_kurage_teki.cpp:427 (mPellet corpse registration)";
    case Stall::NoCarry:
        return "pc_port/pc_p2_kurage_teki.cpp:203 (corpseTail FreeMode carry)";
    case Stall::NoReceipt:
        return "pc_port/pc_p2_kurage_teki.cpp:620 (pc_p2_kurage_receipt)";
    }
    return "unknown";
}

Audit audit_private_adapter(bool adapterAirborneWithoutInjection,
                            bool groundedOnlyByInjection)
{
    Audit audit{};
    audit.damage_receiver_open = damage_receiver_accepts(57);
    // A FreeMode squad evaluates the adapter as it is on the field.  If the
    // adapter is airborne unless something grounds it, the squad skips it.
    audit.free_squad_acquires =
        free_squad_acquires(AcquisitionFacts{ true, true, true, false,
                                              adapterAirborneWithoutInjection });
    audit.grounded_only_by_injection = groundedOnlyByInjection;
    if (!audit.damage_receiver_open) {
        audit.stall = Stall::NoDamageReceiver;
    } else if (adapterAirborneWithoutInjection && groundedOnlyByInjection) {
        // The only path that makes the adapter targetable is the injected
        // groundAndSeal concession, which the natural gate must not cite.
        audit.stall = Stall::NoEngagementFreeSquadSkipsFlying;
    } else if (!audit.free_squad_acquires) {
        audit.stall = Stall::NoEngagementFlyingRetarget;
    } else {
        audit.stall = Stall::None;
    }
    return audit;
}

} // namespace p2kurage_natural
