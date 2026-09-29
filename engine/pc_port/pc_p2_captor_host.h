#pragma once
// Engine glue for pc_p2_captor_mouth.h (#886): how a P2 captor on a P1 host
// physically holds, swallows and releases Pikmin. Shared by the Jigumo,
// Snagret, UmiMushi, Armor and Uji modules; the decisions themselves live in
// the engine-free header so tools/p2_captor_mouth_test.cpp exercises them.
//
// Mechanism (the #884 Chappy pattern, pc_p2_chappy.cpp doEat/doSwallow): a
// captured Pikmin receives InteractSwallow(actor, hostSlotChild) and is stuck
// to a child of the P1 host's 'slot' mouth CollPart (P2 slot i -> host child
// i % host children). The P1 receiver puts it in PIKISTATE_Swallowed, where it
// follows the host part and cannot be whistled (navi.cpp:1526,1717 skip
// Swallowed). Every placement vehicle here (TEKI_Chappy, TEKI_KabekuiA/B/C)
// authors a 'slot' part: the P1 Chappy eats through it and TAIAbiteForKabekui
// swallows into it (TAIAattack.cpp:396-414). A host without one refuses the
// capture; InteractSwallow is never sent with a null part (the P1 receiver
// would kill outright, interactBattle.cpp:525-529).
#include "pc_p2_captor_mouth.h"
#include "pc_p2_white.h"
#include "teki.h"
#include "Collision.h"
#include "Interactions.h"
#include "Piki.h"
#include "PikiMgr.h"
#include <vector>

namespace p2captorhost {

inline p2captor::Vec3 vec(const Vector3f& v)
{
    return p2captor::Vec3{v.x, v.y, v.z};
}

// True while `p` is one of `actor`'s mouth stickers (the physical hold).
inline bool heldBy(BTeki* actor, Piki* p)
{
    if (!actor || !p) return false;
    for (Creature* c = actor->mStickListHead; c; c = c->mNextSticker) {
        if (c == p) return c->isStickToMouth() != 0;
    }
    return false;
}

inline int mouthStickerCount(BTeki* actor)
{
    int n = 0;
    for (Creature* c = actor ? actor->mStickListHead : nullptr; c; c = c->mNextSticker) {
        if (c->isPiki() && c->isStickToMouth()) ++n;
    }
    return n;
}

inline int pikiStickerCount(BTeki* actor)
{
    int n = 0;
    for (Creature* c = actor ? actor->mStickListHead : nullptr; c; c = c->mNextSticker) {
        if (c->isPiki()) ++n;
    }
    return n;
}

// Snapshot of pikiMgr in manager order, before any stimulate.
struct Scene {
    std::vector<Piki*> pikis;
    std::vector<p2captor::Prey> prey;
};

inline Scene snapshot(BTeki* actor)
{
    Scene s;
    if (!pikiMgr) return s;
    Iterator it(pikiMgr);
    CI_LOOP(it)
    {
        Piki* p = static_cast<Piki*>(*it);
        if (!p) continue;
        p2captor::Prey q{};
        q.pos = vec(p->getPosition());
        q.alive = p->isAlive();
        q.visible = p->isVisible();
        q.buried = p->isBuried();
        q.stuckToAnyMouth = p->isStickToMouth() != 0;
        q.stuckToSelf = p->getStickObject() == actor && !q.stuckToAnyMouth;
        q.stuckToAny = p->isStickTo();
        s.pikis.push_back(p);
        s.prey.push_back(q);
    }
    return s;
}

inline CollPart* hostMouth(BTeki* actor)
{
    return (actor && actor->mCollInfo) ? actor->mCollInfo->getSphere('slot') : nullptr;
}

inline int hostSlotCount(BTeki* actor)
{
    CollPart* m = hostMouth(actor);
    return m ? m->getChildCount() : 0;
}

// Revalidate the registry against the physical stick; fills `occupied`.
inline int validate(BTeki* actor, p2captor::Held<Piki>& held, int slots, bool* occupied)
{
    return held.validate(slots, occupied, [actor](Piki* p) { return heldBy(actor, p); });
}

// Stick prey `n` to P2 slot `slot` through the host mouth part. `motion` is
// the P1 receiver's motion switch (0 Esa, 1 Fall; the P1 Kabekui uses 1).
inline bool swallowInto(BTeki* actor, Scene& scene, int n, int slot, p2captor::Held<Piki>& held, int motion,
                        int* refusedNoHost)
{
    CollPart* mouth = hostMouth(actor);
    const int hostCount = mouth ? mouth->getChildCount() : 0;
    const int idx = p2chappymouth::hostPartIndex(slot, hostCount);
    CollPart* part = idx >= 0 ? mouth->getChildAt(idx) : nullptr;
    if (!part) {
        if (refusedNoHost) ++*refusedNoHost;
        return false;
    }
    Piki* piki = scene.pikis[n];
    if (!piki->stimulate(InteractSwallow(actor, part, motion))) return false;
    if (!heldBy(actor, piki)) return false;
    held.slot[slot] = piki;
    return true;
}

// Source swallowPikmin: kill every Pikmin still held; white ones feed the
// poison to this actor (eatWhitePikminCallBack; the port queues it as
// stored damage like pc_p2_chappy.cpp doSwallow).
inline int swallow(BTeki* actor, p2captor::Held<Piki>& held, int slots, float poison, int* whiteOut)
{
    int white = 0;
    const int killed = p2captor::swallow(
        held, slots, [actor](Piki* p) { return heldBy(actor, p); },
        [actor](Piki* p) { return p->stimulate(InteractKill(actor, 0)) != 0; },
        [](Piki* p) { return pc_p2_is_white(p); }, &white);
    if (white > 0) actor->mStoredDamage += poison * float(white);
    if (whiteOut) *whiteOut = white;
    return killed;
}

// Death / teardown: free every Pikmin in this actor's mouth without harm (the
// P1 PikiSwallowedState then returns it to Normal). Returns the count freed.
inline int release(BTeki* actor, p2captor::Held<Piki>& held)
{
    std::vector<Creature*> mouth;
    for (Creature* c = actor ? actor->mStickListHead : nullptr; c; c = c->mNextSticker) {
        if (c->isStickToMouth()) mouth.push_back(c);
    }
    for (Creature* c : mouth) c->endStickMouth();
    held.clear();
    return (int)mouth.size();
}

} // namespace p2captorhost
