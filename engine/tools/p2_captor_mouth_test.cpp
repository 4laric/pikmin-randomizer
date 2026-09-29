// Isolated fixtures for pc_p2_captor_mouth.h (#886 defect 3: captor mouth slots).
// Build: g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_captor_mouth_test.cpp -o p2_captor_mouth_test
//
// Exercises the real runtime decision code (p2captor::eat / eatAt, the
// Jigumo height condition, the Snagret facing boxes, the Held registry and
// swallow) against the source rules cited in the header. Each behavioural
// block also runs a verbatim engine-free transcription of the pre-#886 port
// logic (XZ-nearest capture of a raw Piki*, then InteractKill of that pointer
// "wherever it is") on the same scene and requires it to violate the rule,
// so the fixture fails on the old behaviour.
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <vector>
#include "pc_p2_captor_mouth.h"

using namespace p2captor;

static int gChecks = 0;
static void require(bool ok, const char* what)
{
    ++gChecks;
    if (!ok) {
        std::printf("FAIL p2_captor_mouth_test: %s\n", what);
        std::fflush(stdout);
        std::_Exit(1);
    }
}

namespace {

constexpr float PI_F = 3.14159265f;
constexpr unsigned kSlotSources[] = {63, 71, 101, 15, 13, 14};

Prey pikmin(const Vec3& pos)
{
    Prey p{};
    p.pos = pos;
    p.alive = true;
    p.visible = true;
    return p;
}

// ---- Pre-#886 port logic (transcribed) -------------------------------------
// pc_p2_{jigumo,snakejoint,umimushi,armor}.cpp nearestPiki(pos, ATTACK_RANGE):
// the XZ-nearest live Pikmin within the radius, no facing, no slot.
int legacyNearest(const std::vector<Prey>& prey, const Vec3& actor, float radius)
{
    int best = -1;
    float bestSq = radius * radius;
    for (int n = 0; n < (int)prey.size(); ++n) {
        if (!prey[n].alive) continue;
        const float dx = prey[n].pos.x - actor.x, dz = prey[n].pos.z - actor.z;
        const float d = dx * dx + dz * dz;
        if (d < bestSq) {
            bestSq = d;
            best = n;
        }
    }
    return best;
}
// Old capture ranges: Jigumo ATTACK_RANGE 200, UmiMushi fallback ATTACK_HIT
// 170, Armor ATTACK_RANGE 75, Snagret ATTACK_RANGE 220; Uji nearestFoe 60.
float legacyRange(unsigned source)
{
    switch (source) {
    case 63: return 200.0f;
    case 71:
    case 101: return 170.0f;
    case 15: return 75.0f;
    case 34:
    case 70: return 220.0f;
    default: return 60.0f;
    }
}

// Fake Pikmin for the registry / swallow fixtures.
struct Fake {
    bool alive = true;
    bool stuckHere = false; // one of THIS captor's mouth stickers
    bool white = false;
    int kills = 0;
};

// Old resolveKill: kill the stored pointer if it is alive, wherever it is.
int legacyResolveKill(Fake*& captured)
{
    int killed = 0;
    if (captured && captured->alive) {
        captured->alive = false;
        ++captured->kills;
        killed = 1;
    }
    captured = nullptr;
    return killed;
}

int newSwallow(Held<Fake>& held, int slots, int* white)
{
    return swallow(
        held, slots, [](Fake* p) { return p->alive && p->stuckHere; },
        [](Fake* p) {
            p->alive = false;
            ++p->kills;
            return true;
        },
        [](Fake* p) { return p->white; }, white);
}

// ---- T1: geometry invariants -------------------------------------------------
void testGeometry()
{
    for (unsigned src : kSlotSources) {
        const Geometry* g = geometryFor(src);
        require(g != nullptr, "every slot captor has a geometry row");
        require(g->slots >= 1 && g->slots <= MaxSlots, "slot count within bounds");
        for (int i = 0; i < g->slots; ++i) {
            const Vec3 l = slotLocal(*g, i);
            // Front-only: the slot sphere never reaches behind the feet plane.
            require(l.z - g->radius >= -1e-4f, "slot sphere in front of the feet plane");
        }
    }
    require(geometryFor(63)->slots == 1 && geometryFor(63)->radius == 25.0f, "Jigumo kamu_joint1 r=max(18,25)");
    require(geometryFor(63)->poison == 500.0f, "Jigumo retail fp05 poison 500");
    require(geometryFor(71)->slots == 7 && geometryFor(71)->radius == 30.0f, "UmiMushi 7 x r30");
    require(geometryFor(101)->slots == 7 && geometryFor(101)->radius == 25.0f, "Blind 7 x r25");
    require(geometryFor(71)->poison == 200.0f, "UmiMushi retail fp11 200");
    require(std::fabs(slotLocal(*geometryFor(71), 6).z - 170.0f) < 1e-3f, "tongue reaches fp22 170");
    require(std::fabs(slotLocal(*geometryFor(101), 6).z - 85.0f) < 1e-3f, "Blind tongue halved");
    require(geometryFor(15)->slots == 1 && geometryFor(15)->radius == 25.0f, "Armor kamujnt r25");
    require(geometryFor(15)->poison == 300.0f, "Armor retail fp01 300");
    require(geometryFor(13)->radius == 15.0f && geometryFor(14)->radius == 15.0f, "Uji kamujnt r15");
    require(geometryFor(34)->slots == 3 && geometryFor(70)->slots == 3, "Snagret 3 slots");
    require(geometryFor(34)->poison == 200.0f && geometryFor(70)->poison == 400.0f, "Snagret retail fp21");
    require(geometryFor(2) == nullptr, "Chappy family stays on pc_p2_chappy_mouth.h");
}

// ---- T2: a rear Pikmin is never captured (legacy captures it) -----------------
void testRearNeverCaptured()
{
    for (unsigned src : kSlotSources) {
        const Geometry& g = *geometryFor(src);
        for (int h = 0; h < 8; ++h) {
            const float heading = -PI_F + h * (PI_F / 4.0f);
            const Vec3 actor{100.0f, 5.0f, -40.0f};
            int newRear = 0, legacyRear = 0;
            // Grid over the half-space behind the feet plane.
            for (float lz = -60.0f; lz <= -0.5f; lz += 5.0f) {
                for (float lx = -60.0f; lx <= 60.0f; lx += 5.0f) {
                    for (float ly = -20.0f; ly <= 20.0f; ly += 10.0f) {
                        std::vector<Prey> prey{pikmin(localToWorld(actor, heading, Vec3{lx, ly, lz}))};
                        bool occupied[MaxSlots] = {};
                        newRear += eat(g, actor, heading, prey.data(), 1, occupied, defaultEligible,
                                       [](int, int) { return true; });
                        if (src == 63) {
                            bool occ2[MaxSlots] = {};
                            newRear += eat(g, actor, heading, prey.data(), 1, occ2, JigumoHeightCheck{actor.y},
                                           [](int, int) { return true; });
                        }
                        legacyRear += legacyNearest(prey, actor, legacyRange(src)) >= 0 ? 1 : 0;
                    }
                }
            }
            require(newRear == 0, "rear Pikmin never captured through the mouth slots");
            require(legacyRear > 0, "legacy XZ-nearest capture takes a rear Pikmin (old behaviour fails)");
        }
    }
}

// ---- T3: front capture, one Pikmin per slot, occupancy ------------------------
void testFrontCaptureAndCapacity()
{
    const Vec3 actor{0.0f, 0.0f, 0.0f};
    const float heading = 0.7f;
    for (unsigned src : kSlotSources) {
        const Geometry& g = *geometryFor(src);
        // One Pikmin on each slot plus two extras on slot 0.
        std::vector<Prey> prey;
        for (int i = 0; i < g.slots; ++i) prey.push_back(pikmin(slotWorld(g, i, actor, heading)));
        prey.push_back(pikmin(slotWorld(g, 0, actor, heading)));
        prey.push_back(pikmin(slotWorld(g, 0, actor, heading)));
        bool occupied[MaxSlots] = {};
        std::vector<int> slotOf(prey.size(), -1);
        const int n = eat(g, actor, heading, prey.data(), (int)prey.size(), occupied, defaultEligible,
                          [&](int p, int s) {
                              slotOf[p] = s;
                              return true;
                          });
        require(n == g.slots, "every slot takes exactly one Pikmin, no overflow");
        for (int i = 0; i < g.slots; ++i) require(occupied[i], "slot marked occupied");
        // A second pass with the same occupancy takes nobody.
        const int again = eat(g, actor, heading, prey.data(), (int)prey.size(), occupied, defaultEligible,
                              [](int, int) { return true; });
        require(again == 0, "occupied slots are not reused");
        // Receiver refusal leaves the slot free.
        bool occ3[MaxSlots] = {};
        const int refused = eat(g, actor, heading, prey.data(), (int)prey.size(), occ3, defaultEligible,
                                [](int, int) { return false; });
        require(refused == 0 && !occ3[0], "refused swallow does not occupy the slot");
    }
    // Just outside / inside the Armor slot radius (3D, strict).
    {
        const Geometry& g = *geometryFor(15);
        const Vec3 slot = slotWorld(g, 0, actor, 0.0f);
        std::vector<Prey> in{pikmin(Vec3{slot.x + 24.9f, slot.y, slot.z})};
        std::vector<Prey> out{pikmin(Vec3{slot.x + 25.0f, slot.y, slot.z})};
        bool o1[MaxSlots] = {}, o2[MaxSlots] = {};
        require(eat(g, actor, 0.0f, in.data(), 1, o1, defaultEligible, [](int, int) { return true; }) == 1,
                "inside radius eaten");
        require(eat(g, actor, 0.0f, out.data(), 1, o2, defaultEligible, [](int, int) { return true; }) == 0,
                "radius is strict");
        // Legacy Armor took a Pikmin 70 units to the side of the feet.
        std::vector<Prey> side{pikmin(Vec3{70.0f, 0.0f, 0.0f})};
        bool o3[MaxSlots] = {};
        require(eat(g, actor, 0.0f, side.data(), 1, o3, defaultEligible, [](int, int) { return true; }) == 0,
                "side Pikmin out of the mouth is not eaten");
        require(legacyNearest(side, actor, legacyRange(15)) == 0, "legacy Armor ate it (old behaviour fails)");
    }
    // Eligibility: stuck in another mouth, dead, buried, stuck to self.
    {
        const Geometry& g = *geometryFor(63);
        const Vec3 slot = slotWorld(g, 0, actor, 0.0f);
        Prey a = pikmin(slot);
        a.stuckToAnyMouth = true;
        Prey b = pikmin(slot);
        b.alive = false;
        Prey c = pikmin(slot);
        c.buried = true;
        Prey d = pikmin(slot);
        d.stuckToSelf = true;
        std::vector<Prey> prey{a, b, c, d};
        bool occ[MaxSlots] = {};
        require(eat(g, actor, 0.0f, prey.data(), 4, occ, defaultEligible, [](int, int) { return true; }) == 0,
                "ineligible Pikmin are never eaten");
    }
}

// ---- T4: Jigumo Attack height condition --------------------------------------
void testJigumoHeight()
{
    const Geometry& g = *geometryFor(63);
    const Vec3 actor{0.0f, 10.0f, 0.0f};
    const Vec3 slot = slotWorld(g, 0, actor, 0.0f);
    std::vector<Prey> high{pikmin(Vec3{slot.x, actor.y + 15.0f, slot.z})};
    std::vector<Prey> ok{pikmin(Vec3{slot.x, actor.y + 5.0f, slot.z})};
    Prey stuck = pikmin(slot);
    stuck.stuckToAny = true;
    std::vector<Prey> latched{stuck};
    bool o1[MaxSlots] = {}, o2[MaxSlots] = {}, o3[MaxSlots] = {}, o4[MaxSlots] = {};
    require(eat(g, actor, 0.0f, high.data(), 1, o1, JigumoHeightCheck{actor.y}, [](int, int) { return true; }) == 0,
            "Attack height check rejects y > +10");
    require(eat(g, actor, 0.0f, high.data(), 1, o2, defaultEligible, [](int, int) { return true; }) == 1,
            "SAttack default condition keeps the 3D slot test");
    require(eat(g, actor, 0.0f, ok.data(), 1, o3, JigumoHeightCheck{actor.y}, [](int, int) { return true; }) == 1,
            "Attack height band accepts");
    require(eat(g, actor, 0.0f, latched.data(), 1, o4, JigumoHeightCheck{actor.y},
                [](int, int) { return true; }) == 0,
            "Attack height check rejects a stuck Pikmin");
}

// ---- T5: a whistled / freed Pikmin is not killed -----------------------------
void testFreedNotKilled()
{
    Fake a;
    Held<Fake> held;
    held.slot[0] = &a;
    a.stuckHere = true;
    // The Pikmin leaves the mouth before the swallow event (whistle, another
    // creature's flick, ...). The new swallow only kills what is still held.
    a.stuckHere = false;
    int white = -1;
    require(newSwallow(held, 1, &white) == 0 && a.alive && a.kills == 0, "freed Pikmin survives the swallow");
    require(white == 0 && held.count(1) == 0, "registry emptied by swallow");
    // Old logic: the stored raw pointer dies wherever it is.
    Fake b;
    Fake* captured = &b;
    require(legacyResolveKill(captured) == 1 && !b.alive, "legacy kills a Pikmin that left (old behaviour fails)");
    // Still-held Pikmin do die; white ones are counted for the poison.
    Fake c, d;
    c.stuckHere = d.stuckHere = true;
    d.white = true;
    Held<Fake> two;
    two.slot[0] = &c;
    two.slot[3] = &d;
    require(newSwallow(two, 7, &white) == 2 && !c.alive && !d.alive && white == 1, "held Pikmin swallowed, white counted");
    // validate() drops a stale entry before capture decisions.
    Fake e;
    Held<Fake> v;
    v.slot[0] = &e;
    bool occ[MaxSlots] = {};
    require(v.validate(1, occ, [](Fake* p) { return p->stuckHere; }) == 0 && !occ[0] && v.slot[0] == nullptr,
            "validate frees the slot of a Pikmin no longer held");
}

// ---- T6: a recycled Piki slot is not killed -----------------------------------
void testRecycledSlotNotKilled()
{
    // A is captured, then dies elsewhere (e.g. drowned). Creature::kill runs
    // the forget hook; the pool later re-births the same address as a fresh
    // Pikmin (PikiMgr::birth runs it again).
    Fake slotMemory;
    slotMemory.stuckHere = true;
    Held<Fake> held;
    held.slot[0] = &slotMemory;
    slotMemory.alive = false;
    slotMemory.stuckHere = false;
    require(held.forget(&slotMemory), "death-time forget clears the registration");
    slotMemory = Fake{}; // recycled: alive again, not in any mouth
    require(!held.forget(&slotMemory), "birth-time forget is idempotent");
    require(newSwallow(held, 1, nullptr) == 0 && slotMemory.alive, "recycled Pikmin is not killed");
    // Without any forget, the physical-hold check still protects it.
    Held<Fake> stale;
    stale.slot[0] = &slotMemory;
    require(newSwallow(stale, 1, nullptr) == 0 && slotMemory.alive, "hold check protects a recycled slot");
    // Old logic: the raw pointer names the recycled, live Pikmin and kills it.
    Fake* captured = &slotMemory;
    require(legacyResolveKill(captured) == 1 && !slotMemory.alive,
            "legacy kills the recycled Pikmin remotely (old behaviour fails)");
}

// ---- T7: Snagret facing boxes -------------------------------------------------
void testSnagretBoxes()
{
    const unsigned sources[] = {34, 70};
    for (unsigned src : sources) {
        const SnakeZones& z = snakeZonesFor(src);
        for (int h = 0; h < 8; ++h) {
            const float face = -PI_F + h * (PI_F / 4.0f);
            const Vec3 actor{-30.0f, 0.0f, 55.0f};
            const float floorY[5] = {0.0f, 0.0f, 0.0f, 0.0f, 0.0f};
            int newRear = 0, legacyRear = 0;
            for (float lz = -200.0f; lz <= -0.5f; lz += 10.0f) {
                for (float lx = -200.0f; lx <= 200.0f; lx += 10.0f) {
                    std::vector<Prey> prey{pikmin(localToWorld(actor, face, Vec3{lx, 0.0f, lz}))};
                    for (int idx = 0; idx <= SnakeAnyZone; ++idx) {
                        newRear += snakeAttackPiki(z, idx, actor, face, floorY, prey.data(), 1, nullptr) >= 0 ? 1 : 0;
                    }
                    legacyRear += legacyNearest(prey, actor, legacyRange(src)) >= 0 ? 1 : 0;
                }
            }
            require(newRear == 0, "Snagret never bites behind its face");
            require(legacyRear > 0, "legacy 220 sweep bites behind (old behaviour fails)");
            // Each zone's own attack position lies inside its own box.
            for (int i = 0; i < 5; ++i) {
                const Vec3 q = snakeAttackPosition(z, i, actor, face);
                require(snakeZoneOf(z, i, actor, face, floorY, q) == i, "attack point inside its box");
                require(snakeZoneOf(z, SnakeAnyZone, actor, face, floorY, q) >= 0, "any-zone query finds it");
            }
        }
        // Zone restriction: at the bite only mAttackAnimIdx is searched.
        const Vec3 actor{0.0f, 0.0f, 0.0f};
        const float floorY[5] = {0.0f, 0.0f, 0.0f, 0.0f, 0.0f};
        const Vec3 farPt = snakeAttackPosition(z, 2, actor, 0.0f);
        std::vector<Prey> prey{pikmin(farPt)};
        int zone = -1;
        require(snakeAttackPiki(z, SnakeAnyZone, actor, 0.0f, floorY, prey.data(), 1, &zone) == 0 && zone == 2,
                "far Pikmin selects the far box");
        require(snakeAttackPiki(z, 0, actor, 0.0f, floorY, prey.data(), 1, nullptr) < 0,
                "near-box bite ignores a far Pikmin");
        // Height band follows the floor under the attack point (+-40).
        Prey high = pikmin(Vec3{farPt.x, 45.0f, farPt.z});
        std::vector<Prey> hp{high};
        require(snakeAttackPiki(z, 2, actor, 0.0f, floorY, hp.data(), 1, nullptr) < 0, "above the box is missed");
        const float raised[5] = {0.0f, 0.0f, 30.0f, 0.0f, 0.0f};
        require(snakeAttackPiki(z, 2, actor, 0.0f, raised, hp.data(), 1, nullptr) == 0, "raised floor shifts the box");
        // A Pikmin already in a mouth is never selected.
        Prey mouth = pikmin(farPt);
        mouth.stuckToAnyMouth = true;
        std::vector<Prey> mp{mouth};
        require(snakeAttackPiki(z, SnakeAnyZone, actor, 0.0f, floorY, mp.data(), 1, nullptr) < 0,
                "mouth-held Pikmin ignored");
    }
    // Right/left boxes: orthoDir = (-cos f, 0, sin f); at f = 0 that is -x.
    {
        const SnakeZones& z = kSnakeCrowZones;
        const float floorY[5] = {0.0f, 0.0f, 0.0f, 0.0f, 0.0f};
        const Vec3 actor{0.0f, 0.0f, 0.0f};
        require(snakeZoneOf(z, SnakeAnyZone, actor, 0.0f, floorY, Vec3{-80.0f, 0.0f, 90.0f}) == 3, "box 3 at -x");
        require(snakeZoneOf(z, SnakeAnyZone, actor, 0.0f, floorY, Vec3{80.0f, 0.0f, 90.0f}) == 4, "box 4 at +x");
    }
    // getSwallowSlot: first free slot, -1 when full.
    bool occ[3] = {true, false, false};
    require(firstFreeSlot(occ, 3) == 1, "first free slot");
    bool full[3] = {true, true, true};
    require(firstFreeSlot(full, 3) == -1, "full mouth refuses");
}

} // namespace

int main()
{
    testGeometry();
    testRearNeverCaptured();
    testFrontCaptureAndCapacity();
    testJigumoHeight();
    testFreedNotKilled();
    testRecycledSlotNotKilled();
    testSnagretBoxes();
    std::printf("PASS p2_captor_mouth_test checks=%d\n", gChecks);
    return 0;
}
