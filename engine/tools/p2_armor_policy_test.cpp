#include "pc_p2_armor_policy.h"

#include <cmath>
#include <cstdio>
#include <cstring>

// Standalone checks for the Cloaking Burrow-nit (Armor, EnemyID 15) source policy (#1014): the retail
// collision tree (only `dmg1` stickable), the attack cone, the bite sweep of the kamujnt mouth joint
// (Armor.cpp:232-261, ArmorState.cpp:586-589), the captain hit and the damage predicates.
// Build: g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_armor_policy_test.cpp -o armor_policy_test

#undef assert
#define assert(condition) do { if (!(condition)) { std::printf("FAIL line %d: %s\n", __LINE__, #condition); return __LINE__; } } while (false)

using namespace p2armor;
namespace T = p2armortables;

static Vec3 local(float x, float y, float z) { return Vec3{x, y, z}; }

// The mouth at source frame k, in body-local model space (scale 1).
static Vec3 mouthAt(int k)
{
    float m[3] = {0.0f, 0.0f, 0.0f};
    mouthCentre(clipIndex("attack2"), float(k), m);
    return Vec3{m[0], m[1], m[2]};
}

// Does the bite ever reach a Pikmin standing at `p` (body-local, feet at y 0) during frames 18..26?
static bool sweepReaches(const Vec3& p)
{
    for (int k = 18; k <= 26; ++k) {
        if (!inBiteWindow(float(k))) return false;
        if (mouthHit(mouthAt(k), p)) return true;
    }
    return false;
}

// The retired port approximation: one fixed slot on the facing axis at z 37.5 (half the 75 reach).
static bool legacyReaches(const Vec3& p)
{
    return mouthHit(Vec3{0.0f, 0.0f, 37.5f}, p);
}

int main()
{
    // ---- Retail collision tree -----------------------------------------------------------------
    assert(T::kNodeCount == 3);
    assert(std::strcmp(T::kNodes[NodeRoot].code, "____") == 0 && T::kNodes[NodeRoot].radius == 40.0f);
    assert(std::strcmp(T::kNodes[NodeDmg1].id, "dmg1") == 0 && std::strcmp(T::kNodes[NodeDmg1].code, "st__") == 0);
    assert(T::kNodes[NodeDmg1].radius == 17.5f && std::strcmp(T::kNodes[NodeDmg1].jointName, "headjnt") == 0);
    assert(std::strcmp(T::kNodes[NodeShell].code, "_t__") == 0 && T::kNodes[NodeShell].radius == 22.5f);
    assert(std::strcmp(T::kNodes[NodeShell].jointName, "kourajnt") == 0);
    assert(stickableCount() == 1);
    assert(codeStickable(T::kNodes[NodeDmg1].code));
    assert(!codeStickable(T::kNodes[NodeRoot].code) && !codeStickable(T::kNodes[NodeShell].code));

    // ---- Tables ----------------------------------------------------------------------------------
    assert(T::kClipCount == 10);
    assert(clipIndex("attack2") >= 0 && clipFrames(clipIndex("attack2")) == 40);
    assert(clipIndex("eat") >= 0 && clipFrames(clipIndex("eat")) == 65);
    assert(clipIndex("nope") == -1 && clipFrames(-1) == 0);
    {
        float c[3];
        assert(nodeCentre(clipIndex("move"), 0.0f, NodeDmg1, c));
        const float headZ = c[2];
        assert(nodeCentre(clipIndex("move"), 0.0f, NodeShell, c));
        assert(headZ > c[2]);  // the head sphere is ahead of the shell
        assert(!nodeCentre(-1, 0.0f, 0, c) && !nodeCentre(0, 0.0f, 3, c) && !mouthCentre(99, 0.0f, c));
        // interpolation halfway between two frames lies between them
        float a[3], b[3], h[3];
        mouthCentre(clipIndex("attack2"), 20.0f, a);
        mouthCentre(clipIndex("attack2"), 21.0f, b);
        mouthCentre(clipIndex("attack2"), 20.5f, h);
        assert(std::fabs(h[2] - 0.5f * (a[2] + b[2])) < 1.0e-3f);
        mouthCentre(clipIndex("attack2"), 99.0f, h);  // clamped to the last frame
        mouthCentre(clipIndex("attack2"), 39.0f, a);
        assert(h[2] == a[2]);
    }

    // ---- Bite window and sweep -------------------------------------------------------------------
    assert(!inBiteWindow(17.0f) && inBiteWindow(18.0f) && inBiteWindow(26.0f) && !inBiteWindow(27.0f));
    // The jaw rears up (frames 15-19), lunges (20-22) then pulls back: it is NOT at 37.5 ahead.
    assert(mouthAt(18).z < 40.0f && mouthAt(18).y > 20.0f);
    assert(mouthAt(21).z > 100.0f && mouthAt(22).z > 100.0f);
    {
        float peak = 0.0f;
        for (int k = 18; k <= 26; ++k) peak = std::fmax(peak, mouthAt(k).z);
        assert(peak > 120.0f);
    }
    // Decoys from the owner bug report: the old fixed slot skewered the Pikmin under the rearing head; the
    // real mouth never reaches it, nor either side nor behind, but it does reach the Pikmin the jaw slams.
    const Vec3 underHead = local(0.0f, 0.0f, 40.0f), sideR = local(50.0f, 0.0f, 5.0f), sideL = local(-50.0f, 0.0f, 5.0f),
               behind = local(0.0f, 0.0f, -45.0f), ahead = local(0.0f, 0.0f, 75.0f), far = local(0.0f, 0.0f, 140.0f);
    assert(legacyReaches(underHead));      // the bug
    assert(!sweepReaches(underHead));      // the fix
    assert(!sweepReaches(sideR) && !sweepReaches(sideL) && !sweepReaches(behind));
    assert(sweepReaches(ahead));           // the bait at the attack range is skewered
    assert(sweepReaches(far));             // where the jaw visibly lands
    assert(!legacyReaches(far));           // the old slot never reached it
    // Strict 3D radius: exactly 25 away is not a hit.
    assert(mouthHit(local(0.0f, 0.0f, 0.0f), local(24.9f, 0.0f, 0.0f)));
    assert(!mouthHit(local(0.0f, 0.0f, 0.0f), local(25.0f, 0.0f, 0.0f)));
    // Height counts: a Pikmin 30 above the jaw is not skewered.
    assert(!mouthHit(local(0.0f, 0.0f, 100.0f), local(0.0f, 30.0f, 100.0f)));

    // ---- Frame of reference ----------------------------------------------------------------------
    {
        float m[3] = {0.0f, 0.0f, 50.0f};
        Vec3 w = toWorld(local(10.0f, 0.0f, 20.0f), 0.0f, 1.0f, m);
        assert(std::fabs(w.x - 10.0f) < 1e-4f && std::fabs(w.z - 70.0f) < 1e-4f);
        w = toWorld(local(0.0f, 0.0f, 0.0f), Pi * 0.5f, 2.0f, m);  // facing +x, scale 2: 100 ahead
        assert(std::fabs(w.x - 100.0f) < 1e-3f && std::fabs(w.z) < 1e-3f);
        const Polar p = polar(local(0.0f, 0.0f, 0.0f), Pi * 0.5f, w);
        assert(std::fabs(p.angleDeg) < 1e-3f && std::fabs(p.distXZ - 100.0f) < 1e-3f);
        const Polar back = polar(local(0.0f, 0.0f, 0.0f), 0.0f, local(0.0f, 0.0f, -30.0f));
        assert(std::fabs(std::fabs(back.angleDeg) - 180.0f) < 1e-3f);
    }

    // ---- Attack start (isTargetAttackable, fp20 75 / fp21 15 degrees) -----------------------------------
    {
        const Vec3 o = local(0.0f, 0.0f, 0.0f);
        assert(attackable(o, 0.0f, local(0.0f, 0.0f, 70.0f)));
        assert(!attackable(o, 0.0f, local(0.0f, 0.0f, 76.0f)));
        const float r = 50.0f;
        assert(attackable(o, 0.0f, local(r * std::sin(10.0f * Pi / 180.0f), 0.0f, r * std::cos(10.0f * Pi / 180.0f))));
        // the old 45 degree gate would have started the bite on this one
        assert(!attackable(o, 0.0f, local(r * std::sin(30.0f * Pi / 180.0f), 0.0f, r * std::cos(30.0f * Pi / 180.0f))));
        assert(!attackable(o, 0.0f, local(0.0f, 0.0f, -40.0f)));
        assert(attackable(o, Pi, local(0.0f, 0.0f, -40.0f)));  // facing the other way
    }

    // ---- Captain hit (attackNavi, fp22 75 / fp23 15, strict, 3D) -----------------------------------------
    {
        const Vec3 o = local(0.0f, 0.0f, 0.0f);
        assert(naviHit(o, 0.0f, local(0.0f, 0.0f, 60.0f)));
        assert(!naviHit(o, 0.0f, local(0.0f, 0.0f, 75.0f)));
        assert(!naviHit(o, 0.0f, local(0.0f, 0.0f, -60.0f)));
        assert(!naviHit(o, 0.0f, local(40.0f, 0.0f, 40.0f)));           // 45 degrees off
        assert(!naviHit(o, 0.0f, local(0.0f, 60.0f, 50.0f)));           // 3D: 78 away
    }

    // ---- Damage predicates -------------------------------------------------------------------------
    {
        const std::uint32_t dmg1 = p2armorreceiver::DamagePartID;
        const std::uint32_t shll = p2armorreceiver::fourCC('s', 'h', 'l', 'l');
        const std::uint32_t root = p2armorreceiver::fourCC('r', 'o', 'o', 't');
        const std::uint32_t none = p2armorreceiver::fourCC('n', 'o', 'n', 'e');
        assert(partAccepts(false, dmg1));
        assert(!partAccepts(false, shll) && !partAccepts(false, root) && !partAccepts(false, none));
        assert(partAccepts(true, shll));  // Bittered takes damage anywhere
    }
    {
        // Captain punch: only when the head sphere is within reach and in the facing cone.
        const Vec3 head = local(0.0f, 7.0f, 8.0f);
        assert(punchReachesHead(local(0.0f, 0.0f, 40.0f), Pi, head, 17.5f, 20.0f));        // in front, facing it
        assert(!punchReachesHead(local(0.0f, 0.0f, -60.0f), 0.0f, head, 17.5f, 20.0f));    // behind the shell
        assert(!punchReachesHead(local(0.0f, 0.0f, 70.0f), Pi, head, 17.5f, 20.0f));       // too far
        assert(!punchReachesHead(local(0.0f, 0.0f, 40.0f), 0.0f, head, 17.5f, 20.0f));     // facing away
    }

    {
        // Idle homing and burrowing (#1063, ArmorState.cpp:220-274 and 461-500).
        // Nothing in view: Move goes GoHome (the bug: the port kept walking circles around home in Move).
        assert(moveNext(false, false, false, 5.0f, 400.0f) == ToGoHome);
        assert(moveNext(false, false, false, 0.0f, 400.0f) == ToGoHome);
        // A target: attack when attackable, go home beyond the territory, otherwise keep chasing.
        assert(moveNext(true, true, false, 10.0f, 400.0f) == ToAttack2);
        assert(moveNext(true, false, false, 450.0f, 400.0f) == ToGoHome);
        assert(moveNext(true, false, true, 100.0f, 400.0f) == ToAttack2);
        assert(moveNext(true, false, false, 100.0f, 400.0f) == KeepMoving);
        // GoHome: attack in range, dive inside the home radius (fp10 30), otherwise keep walking.
        assert(goHomeNext(true, 200.0f, 30.0f) == ToAttack2);
        assert(goHomeNext(false, 29.0f, 30.0f) == ToDive);
        assert(goHomeNext(false, 30.0f, 30.0f) == KeepMoving);
        assert(goHomeNext(false, 200.0f, 30.0f) == KeepMoving);
        // The old rule (verbatim): Move only went home past the territory radius, so an idle Armor at 100 never did.
        const bool oldIdleGoesHome = 100.0f > 400.0f;
        assert(!oldIdleGoesHome && moveNext(false, false, false, 100.0f, 400.0f) == ToGoHome);
    }

    std::puts("p2_armor_policy_test PASS");
    return 0;
}
