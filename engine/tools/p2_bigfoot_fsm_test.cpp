#include "pc_p2_bigfoot_fsm.h"
#include "pc_p2_bigfoot_coll.h"
#include "pc_p2_bigfoot_skin.h"
#include "pc_p2_bigfoot_tables.h"

// Release builds pass -DNDEBUG; force assertions on so this gate is not vacuous.
#undef NDEBUG
#include <cassert>
#include <cmath>
#include <cstdio>
#include <cstring>

// Engine-free gate for the Raging Long Legs brain (#1018). Source:
// BigFootState.cpp, BigFoot.cpp, IKSystemMgr.cpp, enemyAction.cpp isStartFlick,
// retail bigfoot/enemyparm.txt, enemyanimmgr.txt and enemycoll.txt.

namespace {
using S = P2LongLegsState;

float flatGround(void*, float, float) { return 0.0f; }

P2BigFootInput base()
{
    P2BigFootInput in;
    in.health = 10000.0f;
    in.roll[0] = in.roll[1] = in.roll[2] = in.roll[3] = 0.5f;
    in.ground = flatGround;
    return in;
}

struct Trace {
    int ticks = 0;
    bool landKey2 = false;
    bool flick = false;
    float flickKnock = 0.0f, flickDamage = -1.0f;
    int pressTicks = 0;
    int lifted = 0, planted = 0;
    P2BigFootOutput last;
};

// Runs until `target` is entered; -1 on timeout.
int runUntil(P2BigFootFsm& fsm, const P2BigFootInput& in, S target, int limit, Trace* t = nullptr)
{
    P2BigFootOutput out;
    for (int i = 1; i <= limit; ++i) {
        fsm.update(in, out);
        if (t) {
            ++t->ticks;
            t->landKey2 |= out.landKey2;
            if (out.flickStuck) {
                t->flick = true;
                t->flickKnock = out.flickKnockback;
                t->flickDamage = out.flickDamage;
            }
            for (int l = 0; l < p2ik::kLegCount; ++l) t->pressTicks += fsm.footPressing(l) ? 1 : 0;
            for (int l = 0; l < p2ik::kLegCount; ++l) {
                t->lifted += (out.lifted >> l) & 1;
                t->planted += (out.planted >> l) & 1;
            }
            t->last = out;
        }
        if (out.entered && fsm.state() == target) return i;
    }
    return -1;
}

void awake(P2BigFootFsm& fsm)
{
    fsm.reset(P2BigFootParms(), p2ik::V3(100.0f, 0.0f, 200.0f), 0.0f);
    P2BigFootInput in = base();
    in.wake = true;
    P2BigFootOutput out;
    fsm.update(in, out);
    assert(fsm.state() == S::Land);
    in.wake = false;
    assert(runUntil(fsm, in, S::Wait, 200) > 0);
}
} // namespace

int main()
{
    // Tables: retail skeleton, clip lengths and the collision tree.
    assert(p2bigfoot::kJointCount == 15 && !std::strcmp(p2bigfoot::kJointNames[0], "kosi"));
    assert(P2BigFootFsm::clipFrames(P2BigFootFsm::ClipLanding) == 70);
    assert(P2BigFootFsm::clipFrames(P2BigFootFsm::ClipWait) == 76);
    assert(P2BigFootFsm::clipFrames(P2BigFootFsm::ClipFlick) == 70);
    assert(P2BigFootFsm::clipFrames(P2BigFootFsm::ClipDead) == 300);
    {
        p2ik::M34 j[P2BigFootFsm::kJoints];
        P2BigFootFsm::clipJoints(P2BigFootFsm::ClipLanding, 0.0f, j);
        assert(j[0].m[1][3] > 1500.0f); // the drop-in starts ~1560 units up
        P2BigFootFsm::clipJoints(P2BigFootFsm::ClipWait, 0.0f, j);
        assert(std::fabs(j[0].m[1][3] - 179.5f) < 1.0f);
    }
    for (int l = 0; l < p2ik::kLegCount; ++l) {
        const int foot = p2bigfootcoll::nodeIndex(P2BigFootFsm::kFootNode[l]);
        assert(foot >= 0 && p2bigfoot::kColl[foot].joint == P2BigFootFsm::kLegJoint[l][2]);
    }

    // Hurtbox policy: the body and the retail lht1 tube are the only stickable parts.
    {
        namespace C = p2bigfootcoll;
        assert(C::stickableCount() == 2);
        assert(C::stickable(C::nodeIndex("tama")) && C::body(C::nodeIndex("tama")));
        assert(C::stickable(C::nodeIndex("lht1")));
        for (const char* id : {"lfsp", "lhsp", "rfsp", "rhsp", "lft1", "lft4", "rht2", "none"})
            assert(!C::stickable(C::nodeIndex(id)));
        assert(C::attackRate(true, true, C::nodeIndex("tama")) == 1.0f);
        assert(C::attackRate(true, false, -1) == 0.0f);                     // ground melee
        assert(C::attackRate(true, true, C::nodeIndex("rfsp")) == 0.0f);    // stuck on a foot (defence in depth)
        assert(C::attackRate(false, false, C::nodeIndex("tama")) == 0.0f);  // captain punch
        assert(C::bombRate() == 1.0f);
        assert(C::tubeStart(C::nodeIndex("lft1")) && C::tubeStart(C::nodeIndex("lft3")));
        assert(!C::tubeStart(C::nodeIndex("lft4")) && !C::tubeStart(C::nodeIndex("tama")));
    }

    // isStartFlick with the retail tiers (ip01..ip07 = 70/50, 80/60, 90/70, 100).
    {
        P2BigFootParms p;
        assert(!P2BigFootFsm::isStartFlickFor(p, 0, 70.0f) && P2BigFootFsm::isStartFlickFor(p, 0, 71.0f));
        assert(!P2BigFootFsm::isStartFlickFor(p, 55, 80.0f) && P2BigFootFsm::isStartFlickFor(p, 55, 81.0f));
        assert(!P2BigFootFsm::isStartFlickFor(p, 65, 90.0f) && P2BigFootFsm::isStartFlickFor(p, 65, 91.0f));
        assert(!P2BigFootFsm::isStartFlickFor(p, 80, 100.0f) && P2BigFootFsm::isStartFlickFor(p, 80, 101.0f));
        // A crowd of Pikmin standing near it is not a flick (the old port flicked on proximity).
        assert(!P2BigFootFsm::isStartFlickFor(p, 0, 0.0f));
    }

    // Stay: hidden, clip parked; nothing but the wake radius drops it in.
    {
        P2BigFootFsm fsm;
        fsm.reset(P2BigFootParms(), p2ik::V3(0.0f, 0.0f, 0.0f), 0.0f);
        P2BigFootInput in = base();
        in.stuck = 3; // Pikmin around a dormant Long Legs do not wake it by themselves
        P2BigFootOutput out;
        for (int i = 0; i < 90; ++i) fsm.update(in, out);
        assert(fsm.state() == S::Stay && out.hidden && fsm.frame() == 0 && !fsm.ikActive());
        in.hits = 0;
        in.wake = true;
        fsm.update(in, out);
        assert(fsm.state() == S::Land && out.entered && !out.hidden);
        in.wake = false;
        Trace t;
        const int n = runUntil(fsm, in, S::Wait, 200, &t);
        std::printf("land: ticks=%d state=%s\n", n, P2LongLegsFsm::stateName(fsm.state()));
        assert(n > 60 && n < 75);       // the 70-frame landing clip runs to its end
        assert(t.landKey2 && !t.last.bitterImmune);
        assert(fsm.ikActive());         // StateLand::cleanup startProgramedIK
        assert(t.pressTicks == 0);      // no foot press while landing
    }

    // Wait -> Walk after 5 s (finishMotion then the wait clip's END); Walk chases
    // the Pikmin with real IK strides, presses with descending feet, and returns
    // to Wait after mFlickWalkTimeMax (5 + 0.5 * 10 = 10 s at roll 0.5).
    {
        P2BigFootFsm fsm;
        awake(fsm);
        assert(std::fabs(fsm.walkTimeMax() - 10.0f) < 1.0e-4f);
        P2BigFootInput in = base();
        in.walkPikiFound = true;
        in.walkPiki = p2ik::V3(100.0f, 0.0f, 600.0f);
        const int n = runUntil(fsm, in, S::Walk, 400);
        assert(n >= 150 && n <= 150 + 80);
        const p2ik::V3 start = fsm.position();
        Trace t;
        const int w = runUntil(fsm, in, S::Wait, 30 * 20, &t);
        assert(w > 0);
        const float moved = std::sqrt((fsm.position().x - start.x) * (fsm.position().x - start.x)
                                      + (fsm.position().z - start.z) * (fsm.position().z - start.z));
        std::printf("walk: ticks=%d moved=%.1f lifted=%d planted=%d press_ticks=%d cycles=%d\n", w, moved,
                    t.lifted, t.planted, t.pressTicks, fsm.ik().cycles());
        assert(w >= 300);               // walked at least the 10 s timer
        assert(moved > 100.0f);         // the body followed the IK centre toward the Pikmin
        assert(t.lifted >= 4 && t.planted >= 4 && t.pressTicks > 0);
        assert(!fsm.enraged());
    }

    // Flick: 71 accumulated hits -> Flick; key 2 (frame 35) shakes with the disc
    // knockback 400 / damage 0 and clears the counter; END -> an ENRAGED Walk
    // with the post-shake timer (2.5 + 0.5 * 5 = 5 s), enraged IK parameters;
    // the rampage walk ends in Wait with the rage cleared.
    {
        P2BigFootFsm fsm;
        awake(fsm);
        P2BigFootInput in = base();
        in.hits = 71;
        in.stuck = 10;
        P2BigFootOutput out;
        fsm.update(in, out);
        in.hits = 0;
        assert(runUntil(fsm, in, S::Flick, 120) > 0);
        in.stuck = 0;
        Trace t;
        assert(runUntil(fsm, in, S::Walk, 120, &t) > 0);
        assert(t.flick && t.flickKnock == 400.0f && t.flickDamage == 0.0f);
        assert(fsm.flickTimer() == 0.0f);
        assert(fsm.enraged() && t.last.enraged);
        assert(std::fabs(t.last.chosenSeconds - 5.0f) < 1.0e-4f);
        assert(fsm.ikParms().bottomJointMoveSpeed == 4.0f && fsm.ikParms().heightOffset == 110.0f);
        Trace r;
        const p2ik::V3 start = fsm.position();
        assert(runUntil(fsm, in, S::Wait, 30 * 12, &r) > 0);
        std::printf("rampage: ticks=%d lifted=%d planted=%d press_ticks=%d\n", r.ticks, r.lifted, r.planted,
                    r.pressTicks);
        assert(r.ticks >= 150 && r.pressTicks > 0 && r.planted >= 4);
        assert(!fsm.enraged() && fsm.ikParms().bottomJointMoveSpeed == 1.4f);
        (void)start;
    }

    // Landing straight into a Flick when the counter is already over the tier.
    {
        P2BigFootFsm fsm;
        fsm.reset(P2BigFootParms(), p2ik::V3(), 0.0f);
        P2BigFootInput in = base();
        in.wake = true;
        P2BigFootOutput out;
        fsm.update(in, out);
        in.wake = false;
        in.hits = 80;
        fsm.update(in, out);
        in.hits = 0;
        assert(runUntil(fsm, in, S::Flick, 200) > 0);
    }

    // Death: Walk exits at once; key 2 at frame 85 (throw-up + Mitites), END at 300.
    {
        P2BigFootFsm fsm;
        awake(fsm);
        P2BigFootInput in = base();
        assert(runUntil(fsm, in, S::Walk, 400) > 0);
        in.health = 0.0f;
        P2BigFootOutput out;
        fsm.update(in, out);
        assert(fsm.state() == S::Dead && out.entered);
        int key2 = -1, end = -1, key2Count = 0;
        for (int i = 1; i <= 640; ++i) {
            fsm.update(in, out);
            if (out.deadKey2) { key2 = i; ++key2Count; }
            if (out.deadEnd && end < 0) end = i;
        }
        assert(key2 >= 84 && key2 <= 86 && end >= 299 && end <= 301);
        assert(key2Count == 1); // no additional groups during terminal frames
    }

    // Skin: rigid and envelope draw matrices reproduce the J3D maths.
    {
        const char* text =
            "P2_BIGFOOT_SKIN_1\njoints 2\n"
            "i 0 1 0 0 0 0 1 0 0 0 0 1 0\n"
            "i 1 1 0 0 -10 0 1 0 0 0 0 1 0\n"
            "draws 2\nd 0 r 0\nd 1 e 2 0 0.5 1 0.5\n"
            "positions 2\n0 1 2 3\n1 10 0 0\n"
            "normals 1\n1 0 1 0\nend\n";
        p2bigfootskin::Skin skin;
        std::string error;
        assert(skin.parse(text, &error));
        p2ik::M34 joints[2];
        joints[1].m[0][3] = 10.0f;  // joint 1 bind at x=10
        std::vector<p2ik::V3> pos, nrm;
        skin.evaluate(joints, pos, nrm);
        assert(pos.size() == 2 && std::fabs(pos[0].x - 1.0f) < 1e-5f && std::fabs(pos[1].x - 10.0f) < 1e-5f);
        joints[1].m[1][3] = 4.0f;   // lift joint 1: the half-weighted vertex rises half as far
        skin.evaluate(joints, pos, nrm);
        assert(std::fabs(pos[1].y - 2.0f) < 1e-5f && std::fabs(nrm[0].y - 1.0f) < 1e-5f);
        assert(!skin.parse("P2_BIGFOOT_SKIN_1\njoints 0\n", &error));
    }

    std::printf("p2_bigfoot_fsm_test: ok\n");
    return 0;
}
