#pragma once

// Engine-facing BigTreasure elemental receiver apply (#246). Resolves the
// source stimulus for a running element and applies it to a live Piki/Navi
// through the shared P2 receivers (InteractFire / InteractGas / InteractBubble /
// InteractDenki in interactBattle.cpp / navi.cpp). Used by the ordinary update
// (pc_p2_hardlanes.cpp), which owns the per-attack handled set that rate-limits
// re-application; the standalone engine-free test uses
// pc_p2_bigtreasure_receiver.h only (this header is engine-facing and is not
// compiled by the engine-free test). The private real-GL runtime fixture does
// not reference this header today.
//
// The interaction owner is nullptr: the four elemental receivers never read
// mOwner (their actPiki/actNavi either transit state or subtract a magnitude),
// and the boss has no real P1 creature actor. Navi fallback mirrors the source
// non-flick branch (InteractAttack with zero damage) chosen deterministically;
// the source flick/attack 50/50 roll (FIRE 0.33 / GAS 0.67 / WATER 1.0 /
// ELEC 0.5) is left to the host randWeightFloat input.

#include "pc_p2_bigtreasure_receiver.h"
#include "pc_p2_species.h"

#include "Interactions.h"
#include "Navi.h"
#include "Piki.h"

#include <cstdio>

inline bool pc_p2_bigtreasure_stimulate_piki(int weapon, const P2BigTreasureVec3& origin,
                                             float attackDamage, Piki* piki)
{
    if (!piki) {
        return false;
    }
    const P2BigTreasureVec3 target{ piki->mSRT.t.x, piki->mSRT.t.y, piki->mSRT.t.z };
    const P2BigTreasureReceiverHit hit =
        p2_bigtreasure_receiver_resolve(weapon, origin, attackDamage, target);
    bool accepted = false;
    switch (hit.stimulus) {
    case P2BigTreasureReceiverStimulus::Fire: {
        InteractFire stimulus(nullptr, hit.damage);
        accepted = piki->stimulate(stimulus);
        break;
    }
    case P2BigTreasureReceiverStimulus::Gas: {
        InteractGas stimulus(nullptr, hit.damage);
        accepted = piki->stimulate(stimulus);
        break;
    }
    case P2BigTreasureReceiverStimulus::Water: {
        InteractBubble stimulus(nullptr, hit.damage);
        accepted = piki->stimulate(stimulus);
        break;
    }
    case P2BigTreasureReceiverStimulus::Elec: {
        Vector3f dir(hit.direction.x, hit.direction.y, hit.direction.z);
        InteractDenki stimulus(nullptr, hit.damage, &dir);
        accepted = piki->stimulate(stimulus);
        break;
    }
    case P2BigTreasureReceiverStimulus::None:
        return false;
    }
    std::printf("P2_BIGTREASURE_RECV weapon=%s target=piki species=%d accepted=%d\n",
                p2_bigtreasure_receiver_stimulus_name(hit.stimulus),
                pc_p2_species(piki), accepted ? 1 : 0);
    return accepted;
}

inline bool pc_p2_bigtreasure_stimulate_navi(int weapon, const P2BigTreasureVec3& origin,
                                             float attackDamage, Navi* navi)
{
    if (!navi) {
        return false;
    }
    const P2BigTreasureVec3 target{ navi->mSRT.t.x, navi->mSRT.t.y, navi->mSRT.t.z };
    const P2BigTreasureReceiverHit hit =
        p2_bigtreasure_receiver_resolve(weapon, origin, attackDamage, target);
    bool accepted = false;
    switch (hit.stimulus) {
    case P2BigTreasureReceiverStimulus::Fire: {
        InteractFire stimulus(nullptr, hit.damage);
        accepted = navi->stimulate(stimulus);
        if (!accepted) {
            InteractAttack fallback(nullptr, nullptr, 0.0f, false);
            navi->stimulate(fallback);
        }
        break;
    }
    case P2BigTreasureReceiverStimulus::Gas: {
        // Lane-10 blocker: this port's InteractGas has no actNavi, so the base
        // Interaction::actNavi returns true and the source flick/attack fallback
        // (BigTreasureAttack.cpp:226-233) never runs on captains. The source
        // InteractGas::actNavi (interactNavi.cpp:209-212) is a stub returning
        // false, which is what makes that fallback reachable in retail. Until
        // lane 10/11 ports it, a gas hit on a Navi is a no-op here.
        InteractGas stimulus(nullptr, hit.damage);
        accepted = navi->stimulate(stimulus);
        break;
    }
    case P2BigTreasureReceiverStimulus::Water: {
        InteractBubble stimulus(nullptr, hit.damage);
        accepted = navi->stimulate(stimulus);
        if (!accepted) {
            InteractAttack fallback(nullptr, nullptr, 0.0f, false);
            navi->stimulate(fallback);
        }
        break;
    }
    case P2BigTreasureReceiverStimulus::Elec: {
        Vector3f dir(hit.direction.x, hit.direction.y, hit.direction.z);
        InteractDenki stimulus(nullptr, hit.damage, &dir);
        accepted = navi->stimulate(stimulus);
        if (!accepted) {
            InteractAttack fallback(nullptr, nullptr, 0.0f, false);
            navi->stimulate(fallback);
        }
        break;
    }
    case P2BigTreasureReceiverStimulus::None:
        return false;
    }
    std::printf("P2_BIGTREASURE_RECV weapon=%s target=navi accepted=%d\n",
                p2_bigtreasure_receiver_stimulus_name(hit.stimulus), accepted ? 1 : 0);
    return accepted;
}
