#pragma once
// Raging Long Legs (BigFoot 69) hurtbox and damage policy (#1018). Engine-free.
//
// Collision: the retail bigfoot/enemycoll.txt tree (pc_p2_bigfoot_tables.h kColl):
//   none  r225 root                  lfsp lhsp rfsp rhsp  r40 feet   `_t__` touch only
//   tama  r70  body (joint kosi)     `st__` STICKABLE
//   lft1..4 lht1..4 rft1..4 rht1..4  r5 leg tubes (makeTubeTree, BigFoot.cpp:647-656),
//                                    `_t__` touch only, EXCEPT lht1 which the retail
//                                    file codes `st__` (the top segment of the left
//                                    hind leg, hip to knee).
// CollPart::isStickable is `s***` (collinfo.cpp:806-809): a thrown or jumping Pikmin
// latches only onto a stickable part and bounces off the rest (pikiState.cpp:2336;
// aiAttack.cpp:285-290).
//
// Damage (US build), audited per source path:
//  * InteractAttack -> BigFoot::damageCallBack (BigFoot.cpp:202-214): only a Pikmin
//    that is stuck to the boss, with a part (isPiki && isStickTo && collpart). A
//    captain punch, a Pikmin on the ground and any other creature do nothing. P2 has
//    no partless ground melee (ActStickAttack sends the stuck part); P1's ground melee
//    (aiAttack.cpp:695, no part, not stuck) is therefore refused.
//  * InteractBomb -> EnemyBase::bombCallBack (enemyBase.cpp:2908-2912, BigFoot.h does
//    not override it): full damage, whoever set it off (bombState.cpp:146-165 hits
//    every teki whose cell sphere the blast reaches).
//  * InteractHipdrop -> EnemyBase::hipdropCallBack (enemyBase.cpp:2808): purple
//    stun damage (fp36 50). The port's purple hipdrop is not wired for BigFoot.
//  * InteractPress / earthquake: no damage (pressCallBack false; quake chance fp37 0).

#include "pc_p2_bigfoot_tables.h"

#include <cstring>

namespace p2bigfootcoll {

inline bool codeStickable(const char* code) { return code && code[0] == 's'; }

inline int nodeIndex(const char* id)
{
    for (int i = 0; i < p2bigfoot::kCollNodeCount; ++i)
        if (!std::strncmp(p2bigfoot::kColl[i].id, id, 4)) return i;
    return -1;
}

inline bool stickable(int node)
{
    return node >= 0 && node < p2bigfoot::kCollNodeCount && codeStickable(p2bigfoot::kColl[node].code);
}

inline int stickableCount()
{
    int n = 0;
    for (int i = 0; i < p2bigfoot::kCollNodeCount; ++i) n += stickable(i) ? 1 : 0;
    return n;
}

// The central body sphere (the owner's "central body" hurtbox).
inline bool body(int node) { return node >= 0 && node == nodeIndex("tama"); }

// Leg tube chains in retail order: lft, lht, rft, rht; each 1 -> 2 -> 3 -> 4.
// makeTubeTree: a node with a child is a tube to it, a leaf (x4) a sphere.
inline bool tubeStart(int node)
{
    if (node < 0 || node >= p2bigfoot::kCollNodeCount) return false;
    const char* id = p2bigfoot::kColl[node].id;
    return (id[0] == 'l' || id[0] == 'r') && (id[2] == 't') && id[3] >= '1' && id[3] <= '3';
}

enum class PikminHit { Accept, RefuseUnlatched, RefuseNonStickable };
// Verdict for a Pikmin-origin InteractAttack. `stickNode` is the tree node the
// Pikmin is stuck to (-1 when not stuck to this boss's tree).
inline PikminHit pikminHit(bool stuck, int stickNode)
{
    if (!stuck) return PikminHit::RefuseUnlatched;
    return stickable(stickNode) ? PikminHit::Accept : PikminHit::RefuseNonStickable;
}

// InteractAttack damage multiplier: Pikmin stuck to a stickable part 1, anything
// else 0 (captain punch, ground melee, other creatures).
inline float attackRate(bool fromPiki, bool stuck, int stickNode)
{
    if (!fromPiki) return 0.0f;
    return pikminHit(stuck, stickNode) == PikminHit::Accept ? 1.0f : 0.0f;
}

// InteractBomb damage multiplier: EnemyBase::bombCallBack adds the full damage in
// every state (InteractBomb::actEnemy only skips isBeforeAppearState, the
// lifecycle appear state, which BigFoot's FSM Stay is not).
inline float bombRate() { return 1.0f; }

} // namespace p2bigfootcoll
