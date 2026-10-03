// Isolated fixtures for pc_p2_umimushi_policy.h (#995: Bloyster skewer hold and tail weak spot).
// Build: g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_umimushi_policy_test.cpp -o p2_umimushi_policy_test
//
// Exercises the engine-free source policy: the retail collision tree (only `weak` is stickable),
// damageCallBack acceptance (stuck on a part / low partless at 0.03 / refused), the flick tiers,
// the real kamu_joint tongue tables (forward sweep, never behind the feet plane), the source
// `_length2` Navi test and the hit polar log.
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include "pc_p2_umimushi_policy.h"

using namespace p2umi;

static int gChecks = 0;
static void require(bool ok, const char* what)
{
    ++gChecks;
    if (!ok) {
        std::printf("FAIL p2_umimushi_policy_test: %s\n", what);
        std::fflush(stdout);
        std::_Exit(1);
    }
}
static bool near(float a, float b, float eps = 0.01f) { return std::fabs(a - b) <= eps; }

int main()
{
    namespace T = p2umitables;

    // ---- retail collision tree: only the tail bulb latches ----
    require(T::kNodeCount == 5, "five collision nodes");
    require(std::strcmp(T::kNodes[4].id, "weak") == 0 && T::kNodes[4].code[0] == 's', "weak is stickable (st__)");
    require(stickableCount() == 1, "weak is the only stickable part");
    for (int i = 0; i < 4; ++i) require(T::kNodes[i].code[0] != 's', "root/head/kuti/ketu are not stickable");
    require(near(T::kNodes[0].radius, 180.0f) && near(T::kNodes[1].radius, 80.0f) && near(T::kNodes[2].radius, 40.0f)
                && near(T::kNodes[3].radius, 25.0f) && near(T::kNodes[4].radius, 10.0f),
            "retail radii 180/80/40/25/10");
    require(near(T::kNodes[4].radius * TailScale, 14.0f), "tail bulb radius 10 x 1.4 = 14");

    // ---- tail bulb sits behind and above the body (rear, raised) ----
    {
        const int run = clipIndex("run1");
        require(run >= 0, "run1 clip tabled");
        float weak[3], ketu[3], kuti[3];
        require(nodeCentre(run, 0.0f, 4, weak) && nodeCentre(run, 0.0f, 3, ketu) && nodeCentre(run, 0.0f, 2, kuti),
                "node centres");
        require(weak[2] < -100.0f, "weak bulb is behind the root (z < -100)");
        require(weak[1] > 60.0f, "weak bulb is raised above the feet plane (y > 60)");
        require(kuti[2] > 50.0f, "mouth is ahead of the root");
        require(ketu[2] < -60.0f, "hip is behind the root");
    }

    // ---- sturn1 is tabled (the 26-track clip now converts) ----
    require(clipIndex("sturn1") >= 0 && clipFrames(clipIndex("sturn1")) == 40, "sturn1 tabled with 40 frames");

    // ---- real tongue: attack1 sweeps ahead of the body; no slot ever reaches behind the feet plane ----
    {
        const int attack = clipIndex("attack1");
        require(attack >= 0 && clipFrames(attack) == 80, "attack1 has 80 frames");
        float minZ = 1e9f, maxAbsX = 0.0f;
        for (int f = 39; f <= 66; ++f) {
            for (int slot = 0; slot < T::kKamuCount; ++slot) {
                float c[3];
                require(kamuCentre(attack, float(f), slot, c), "kamu table present for attack1");
                if (c[2] < minZ) minZ = c[2];
                if (std::fabs(c[0]) > maxAbsX) maxAbsX = std::fabs(c[0]);
            }
        }
        require(minZ > 0.0f, "no tongue slot is behind the feet plane while the tongue is active (frames 39-66)");
        require(maxAbsX > 100.0f, "the tongue sweeps sideways (not the old straight line on the facing axis)");
        float rest[3];
        require(!kamuCentre(clipIndex("run1"), 0.0f, 0, rest), "no tongue table outside attack1/eat1");
        require(kamuCentre(clipIndex("eat1"), 10.0f, 3, rest), "eat1 carries the held-Pikmin joints");
    }

    // ---- damageCallBack (umiMushi.cpp:467-492) ----
    {
        const Vec3 actor{0.0f, 0.0f, 0.0f};
        DamageAttacker piki;
        piki.present = true;
        piki.alive = true;
        piki.pos = Vec3{0.0f, 75.0f, -130.0f};
        // stuck to the tail with a part: full damage
        piki.hasCollPart = true;
        piki.stuck = true;
        require(damageAccept(actor, piki) == DamageStuck && damageRate(DamageStuck) == 1.0f, "stuck on a part = full damage");
        // a hit that carries a part from an unstuck attacker is refused (nothing but the bulb latches)
        piki.stuck = false;
        require(damageAccept(actor, piki) == DamageRefused && damageRate(DamageRefused) == 0.0f, "part without stick refused");
        // partless below y + 50: scaled by fp01 (0.03)
        piki.hasCollPart = false;
        piki.pos = Vec3{10.0f, 20.0f, 30.0f};
        require(damageAccept(actor, piki) == DamagePartless && near(damageRate(DamagePartless), 0.03f),
                "low partless hit = 0.03");
        // partless above y + 50: refused
        piki.pos.y = 60.0f;
        require(damageAccept(actor, piki) == DamageRefused, "high partless hit refused");
        // dead attacker / no owner refused
        piki.pos.y = 0.0f;
        piki.alive = false;
        require(damageAccept(actor, piki) == DamageRefused, "dead attacker refused");
        piki.alive = true;
        piki.present = false;
        require(damageAccept(actor, piki) == DamageRefused, "ownerless hit refused");
        // captain punch maps to "has a part" and a captain is never stuck: refused (as the source)
        require(sourceHasCollPart(false, true) && !sourceHasCollPart(false, false) && sourceHasCollPart(true, false),
                "captain punch carries a source part");
        DamageAttacker navi;
        navi.present = true;
        navi.alive = true;
        navi.hasCollPart = sourceHasCollPart(false, true);
        navi.stuck = false;
        navi.pos = Vec3{0.0f, 0.0f, 40.0f};
        require(damageAccept(actor, navi) == DamageRefused, "captain punch refused (source)");
    }

    // ---- flick tiers (general ip01..ip07 retail 10/3/13/6/16/9/20) ----
    require(flickThreshold(0) == 10 && flickThreshold(2) == 10, "tier A below 3 stuck");
    require(flickThreshold(3) == 13 && flickThreshold(5) == 13, "tier B 3..5 stuck");
    require(flickThreshold(6) == 16 && flickThreshold(8) == 16, "tier C 6..8 stuck");
    require(flickThreshold(9) == 20 && flickThreshold(30) == 20, "tier D 9+ stuck");
    require(!isStartFlick(10.0f, 1) && isStartFlick(10.6f, 1), "flick starts when the rounded timer exceeds the tier");
    require(!isStartFlick(0.0f, 0) && !isStartFlick(9.0f, 2), "no flick with an empty timer");
    require(near(flickStuckAngle(0.0f), Pi) && flickStuckAngle(Pi) < 1e-3f, "stuck Pikmin fly backwards");

    // ---- source Navi attack: `_length2` is SQUARED, so only ~5.5 units from a slot hits ----
    {
        const Vec3 slot{0.0f, 0.0f, 100.0f};
        require(naviHitBySlot(slot, Vec3{3.0f, 0.0f, 100.0f}, 30.0f), "captain 3 units from a slot is hit");
        require(!naviHitBySlot(slot, Vec3{10.0f, 0.0f, 100.0f}, 30.0f), "captain 10 units from a slot is not hit (squared test)");
        require(!naviHitBySlot(slot, Vec3{0.0f, 0.0f, -100.0f}, 30.0f), "captain behind the body is never hit");
    }

    // ---- lock-on aim: the arc must cross the raised bulb, not the feet ----
    {
        // quick tap (min throw height 80): the descending crossing of y=75 is at t = 0.778 of the 1.0 s flight
        const float quick = pinScale(75.0f, 80.0f, 550.0f, 0.5f);
        require(quick > 1.2f && quick < 1.35f, "quick throw: cursor pinned ~1.29x beyond the bulb");
        // full charge (height 100): the crossing is almost at the cursor point
        const float full = pinScale(75.0f, 100.0f, 550.0f, 0.5f);
        require(full > 0.98f && full < 1.06f, "full-charge throw: cursor pinned on the bulb");
        require(pinScale(10.0f, 80.0f, 550.0f, 0.5f) == 1.0f, "a target at launch height keeps the plain pin");
        require(pinScale(75.0f, 1.0f, 550.0f, 0.5f) == 1.0f || pinScale(75.0f, 1.0f, 550.0f, 0.5f) > 0.0f,
                "a too-low arc stays finite");
        require(pinScale(75.0f, 80.0f, 0.0f, 0.5f) == 1.0f, "no gravity parameter keeps the plain pin");
        // The pinned cursor at 1.29x makes the arc's descending crossing land within the bulb radius.
        const float k = pinScale(75.0f, 80.0f, 550.0f, 0.5f);
        const float vSpeed = 550.0f * 0.5f * 0.5f + 80.0f / 0.5f;
        const float frac = 1.0f / k;                       // horizontal fraction at the crossing
        const float t = frac * 1.0f;                       // flight time 1.0 s
        const float y = 10.0f + vSpeed * t - 0.5f * 550.0f * t * t;
        require(std::fabs(y - 75.0f) < 1.0f, "the crossing height equals the bulb height");
    }

    // ---- before / after: the rear hitbox (#995) ----
    // Verbatim transcription of the pre-#995 port rules, run on the same scene. The scene is a captain and a
    // Pikmin directly BEHIND the body (angle 180 deg, 100 units); the new rules must not reach them.
    {
        const Vec3 actor{0.0f, 0.0f, 0.0f};
        const Vec3 behind{0.0f, 0.0f, -100.0f};
        const Vec3 ahead{0.0f, 0.0f, 100.0f};
        // pre-#995 isAttackStart fallback: any Pikmin inside the fp22 = 170 radius, any angle
        auto oldAttackStart = [&](const Vec3& q) { return std::hypot(q.x - actor.x, q.z - actor.z) < 170.0f; };
        // pre-#995 attackNearbyNavi (attack key 5): every captain inside 170 units, any angle
        auto oldNaviAttack = [&](const Vec3& q) { return std::hypot(q.x - actor.x, q.z - actor.z) < 170.0f; };
        require(oldAttackStart(behind), "old rule: a Pikmin behind the body starts the attack (the bug)");
        require(oldNaviAttack(behind), "old rule: a captain behind the body is hit (the bug)");
        const float cone = AttackHitAngleDeg * Pi / 180.0f;
        require(!withinCone(actor, 0.0f, behind, 170.0f, cone), "new rule: a Pikmin behind does not start the attack");
        require(withinCone(actor, 0.0f, ahead, 170.0f, cone), "new rule: a Pikmin ahead inside the cone starts it");
        require(!withinCone(actor, 0.0f, Vec3{100.0f, 0.0f, 20.0f}, 170.0f, cone), "new rule: a Pikmin at 79 deg does not");
        require(!withinCone(actor, 0.0f, Vec3{0.0f, 0.0f, 200.0f}, 170.0f, cone), "new rule: outside fp22 radius does not");
        // every tongue slot of every attack frame is ahead of the feet plane, so no slot can reach the rear
        const int attack = clipIndex("attack1");
        bool anyBehind = false;
        for (int f = 0; f < 80; ++f)
            for (int slot = 0; slot < T::kKamuCount; ++slot) {
                float c[3];
                kamuCentre(attack, float(f), slot, c);
                if (c[2] < 0.0f) anyBehind = true;
            }
        require(!anyBehind, "no tongue slot is ever behind the feet plane in attack1");
        require(!naviHitBySlot(Vec3{0.0f, 0.0f, 100.0f}, behind, SlotRadius), "new rule: the captain behind is not hit");
    }

    // ---- Toady shove reach (#1020): the flick radius follows the body scale, the Ranging Bloyster keeps 90 ----
    require(near(shakeRange(1.0f), 90.0f), "Ranging Bloyster keeps the source reach 90");
    require(near(shakeRange(0.5f), 45.0f), "Toady Bloyster reach is 45 (half-size body)");
    require(near(shakeRange(0.0f), 90.0f), "a missing scale keeps the source reach");
    {
        // the evidence scene: a Pikmin 70 units behind the Toady was flung by the old unscaled 90
        const Vec3 actor{0.0f, 0.0f, 0.0f};
        const Vec3 behind{0.0f, 0.0f, -70.0f};
        require(std::hypot(behind.x - actor.x, behind.z - actor.z) < 90.0f, "old reach reaches it");
        require(!(std::hypot(behind.x - actor.x, behind.z - actor.z) < shakeRange(0.5f)), "new Toady reach does not");
    }

    // Blind does not retain a targetNavi, so a lone captain must use the
    // source's separate acquisition branch. Exercise the actual selector.
    {
        struct Captain { Vec3 pos; bool alive = true, visible = true, held = false; };
        Captain rear{{0, 0, -10}}, front{{0, 0, 100}}, closer{{0, 0, 60}};
        Captain* roster[] = {nullptr, &rear, &front, &closer};
        const Vec3 actor{0, 0, 0};
        const float cone = AttackHitAngleDeg * Pi / 180.0f;
        auto eligible = [](Captain* n) { return n->alive && n->visible && !n->held; };
        auto position = [](Captain* n) { return n->pos; };
        auto select = [&](bool blind) {
            return blindAttackNavi<Captain>(blind, roster, actor, 0, 170, cone, eligible, position);
        };
        require(select(true) == &closer, "Blind chooses nearest captain inside cone, skips closer rear captain");
        require(select(false) == nullptr, "Ranging does not independently acquire captains for attack");
        closer.alive = false;
        require(select(true) == &front, "dead nearest captain does not mask living captain two");
        front.visible = false;
        require(select(true) == nullptr, "hidden captain is not acquired");
        front.visible = true; front.held = true;
        require(select(true) == nullptr, "mouth-held captain is not acquired");
        front.held = false; front.pos = Vec3{0, 0, 170};
        require(select(true) == nullptr, "radius boundary excluded");
        front.pos = Vec3{100, 0, 20};
        require(select(true) == nullptr, "side captain outside angle excluded");
        front.pos = Vec3{0, 200, 100};
        require(select(true) == &front, "source captain acquisition uses XZ separation");
        rear.pos = front.pos;
        require(select(true) == &rear, "equal distance preserves manager index order");
    }

    // ---- hit polar: straight ahead 0, directly behind 180 ----
    {
        const Vec3 actor{0.0f, 0.0f, 0.0f};
        const Polar ahead = polar(actor, 0.0f, Vec3{0.0f, 0.0f, 100.0f});
        require(near(ahead.angleDeg, 0.0f) && near(ahead.distXZ, 100.0f), "ahead = 0 deg");
        const Polar behind = polar(actor, 0.0f, Vec3{0.0f, 0.0f, -100.0f});
        require(near(std::fabs(behind.angleDeg), 180.0f, 0.1f), "behind = 180 deg");
        const Polar right = polar(actor, Pi * 0.5f, Vec3{100.0f, 0.0f, 0.0f});
        require(near(right.angleDeg, 0.0f), "facing +x: a point on +x is ahead");
    }

    // ---- the old proximity rule is gone: a Pikmin on the tail never makes the timer reach a tier alone ----
    require(!isStartFlick(0.0f, 4), "stuck Pikmin alone do not start a flick; damage accrues the timer");

    std::printf("p2_umimushi_policy_test OK (%d checks)\n", gChecks);
    return 0;
}
