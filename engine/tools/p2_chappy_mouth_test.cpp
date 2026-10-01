// Isolated fixtures for pc_p2_chappy_mouth.h (Chappy-family mouth-slot eating, #884).
// Build: g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_chappy_mouth_test.cpp -o p2_chappy_mouth_test.exe
//
// Exercises the real runtime decision code (p2chappymouth::eat, slotWorld,
// eligible, hostPartIndex, profileForSource) against the source
// EnemyFunc::eatPikmin rules (enemyAction.cpp:1107-1142, 2113-2122). T14 keeps
// a verbatim engine-free transcription of the pre-#884 selection
// (pc_p2_chappy.cpp nearestEdiblePiki + doEat) to show the same scenes tell
// the two behaviours apart.
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>
#include "pc_p2_chappy_mouth.h"
#include "pc_p2_chappy_policy.h"

using namespace p2chappymouth;

static int gChecks = 0;
static void require(bool ok, const char* what)
{
    ++gChecks;
    if (!ok) {
        std::printf("FAIL p2_chappy_mouth_test: %s\n", what);
        std::fflush(stdout);
        std::_Exit(1);
    }
}

namespace {

constexpr float PI_F = 3.14159265f;
constexpr unsigned kAllSources[] = {2, 33, 35, 43, 53, 67, 76, 44};

constexpr const Profile* findProfile(unsigned source)
{
    for (const Profile& p : kProfiles) {
        if (p.source == source) return &p;
    }
    return nullptr;
}

// Source key-event frames must match the FSM constants that fire the bite.
static_assert(findProfile(2)->firstFrame == p2chappy::AttackBiteFrame, "Chappy eat frame");
static_assert(findProfile(33)->firstFrame == p2chappy::AttackBiteFrame, "FireChappy eat frame");
static_assert(findProfile(43)->firstFrame == p2chappy::AttackBiteFrame, "YellowChappy eat frame");
static_assert(findProfile(35)->firstFrame == p2chappy::AttackBiteFrame, "KumaChappy eat frame");
static_assert(findProfile(67)->firstFrame == p2chappy::AttackBiteFrame, "LeafChappy eat frame");
static_assert(findProfile(76)->firstFrame == p2chappy::DwarfAttackEatFrame, "KumaKochappy eat frame");
static_assert(findProfile(44)->firstFrame == p2chappy::DwarfAttackEatFrame, "BlueKochappy eat frame");
static_assert(findProfile(53)->firstFrame == 40 && findProfile(53)->lastFrame == 94, "King window 40..94");
static_assert(findProfile(42) == nullptr, "BlueChappy has no eat path");

Prey pikmin(const Vec3& pos)
{
    Prey p{};
    p.pos = pos;
    p.alive = true;
    p.visible = true;
    return p;
}

struct Capture {
    int prey;
    int slot;
};

// Runs one eat pass; `accept` scripts the receiver result per call.
struct Scene {
    std::vector<Prey> prey;
    bool occupied[MaxSlots] = {};
    std::vector<Capture> calls;
    std::vector<Capture> captured;
    std::vector<bool> accept; // per call; default true

    int run(const Profile& p, int frame, const Vec3& actor, float heading)
    {
        return eat(p, frame, actor, heading, prey.data(), (int)prey.size(), occupied, [&](int n, int slot) {
            const bool ok = calls.size() < accept.size() ? accept[calls.size()] : true;
            calls.push_back(Capture{n, slot});
            if (ok) captured.push_back(Capture{n, slot});
            return ok;
        });
    }
    bool stimulated(int n) const
    {
        for (const Capture& c : calls) {
            if (c.prey == n) return true;
        }
        return false;
    }
};

Vec3 add(const Vec3& a, const Vec3& b)
{
    return Vec3{a.x + b.x, a.y + b.y, a.z + b.z};
}

// ---- T14 legacy oracle: verbatim pre-#884 selection (engine-free) ---------
// pc_p2_chappy.cpp:193-211 nearestEdiblePiki: nearest alive Pikmin not stuck to
// a mouth or to anything, within `radius` (attackHitRange 80) of the feet, 3D.
int legacyNearestEdible(const std::vector<Prey>& prey, const Vec3& center, float radius)
{
    int best = -1;
    float bestSq = radius * radius;
    for (int n = 0; n < (int)prey.size(); ++n) {
        const Prey& p = prey[n];
        if (!p.alive) continue;
        if (p.stuckToAnyMouth || p.stuckToAny) continue;
        const float dx = p.pos.x - center.x, dy = p.pos.y - center.y, dz = p.pos.z - center.z;
        const float d = dx * dx + dy * dy + dz * dz;
        if (d < bestSq) {
            bestSq = d;
            best = n;
        }
    }
    return best;
}

struct LegacyResult {
    int prey = -1;
    bool nullPartKill = false; // InteractSwallow(actor, nullptr) -> immediate kill
    int hostSlot = -1;
};

// pc_p2_chappy.cpp:437-445 doEat: one prey; host getFreeSlot() or the null part.
LegacyResult legacyDoEat(const std::vector<Prey>& prey, const Vec3& center, const bool* hostOccupied,
                         int hostCount)
{
    LegacyResult r;
    r.prey = legacyNearestEdible(prey, center, 80.0f);
    if (r.prey < 0) return r;
    for (int i = 0; i < hostCount; ++i) {
        if (!hostOccupied[i]) {
            r.hostSlot = i;
            return r;
        }
    }
    r.nullPartKill = true;
    return r;
}

} // namespace

int main()
{
    const Profile& chappy = *profileForSource(2);
    const Profile& king = *profileForSource(53);
    const Profile& kumako = *profileForSource(76);
    const Vec3 origin{0.0f, 0.0f, 0.0f};

    // --- T1: rear Pikmin nearest and first in manager order; front at kamu3 ---
    {
        Scene sc;
        sc.prey.push_back(pikmin(Vec3{0.0f, 0.0f, -20.0f}));        // B: rear, 20 away
        sc.prey.push_back(pikmin(slotWorld(chappy, 10, 2, origin, 0.0f))); // A: at kamu3
        const int n = sc.run(chappy, chappy.firstFrame, origin, 0.0f);
        require(!sc.stimulated(0), "T1 rear nearest Pikmin is not captured");
        require(n == 1 && sc.captured.size() == 1, "T1 exactly one capture");
        require(sc.captured[0].prey == 1, "T1 front Pikmin captured");
        require(sc.captured[0].slot == 0, "T1 front Pikmin takes first empty in-reach slot (kamu1)");
        require(sc.occupied[0] && !sc.occupied[1] && !sc.occupied[2], "T1 only slot 0 occupied");
    }

    // --- T2: heading/position invariance ---
    {
        const float headings[] = {PI_F * 0.5f, PI_F, -PI_F * 0.5f, 0.7f};
        const Vec3 actors[] = {origin, Vec3{120.0f, 7.5f, -340.0f}};
        for (const Vec3& actor : actors) {
            for (float h : headings) {
                Scene sc;
                sc.prey.push_back(pikmin(localToWorld(actor, h, Vec3{0.0f, 0.0f, -20.0f})));
                sc.prey.push_back(pikmin(slotWorld(chappy, 10, 2, actor, h)));
                sc.run(chappy, chappy.firstFrame, actor, h);
                require(!sc.stimulated(0), "T2 rotated rear Pikmin never stimulated");
                require(sc.captured.size() == 1 && sc.captured[0].prey == 1 && sc.captured[0].slot == 0,
                        "T2 rotated front Pikmin captured into slot 0");
            }
        }
        // toLocal is the inverse of localToWorld.
        const Vec3 w = localToWorld(Vec3{5.0f, 1.0f, 9.0f}, 1.1f, Vec3{3.0f, 4.0f, 70.0f});
        const Vec3 l = toLocal(Vec3{5.0f, 1.0f, 9.0f}, 1.1f, w);
        require(std::fabs(l.x - 3.0f) < 1e-3f && std::fabs(l.y - 4.0f) < 1e-3f && std::fabs(l.z - 70.0f) < 1e-3f,
                "T2 toLocal inverts localToWorld");
        // local +z maps to (sin h, 0, cos h).
        const Vec3 f = localToWorld(origin, 0.5f, Vec3{0.0f, 0.0f, 1.0f});
        require(std::fabs(f.x - std::sin(0.5f)) < 1e-6f && std::fabs(f.z - std::cos(0.5f)) < 1e-6f,
                "T2 local +z is the facing (sin h, cos h)");
    }

    // --- T3: rear-only scenes never capture, any profile, any King frame ---
    {
        const Vec3 rearLocal[] = {{0.0f, 0.0f, 0.0f}, {30.0f, 0.0f, -20.0f}, {-30.0f, 5.0f, -40.0f},
                                  {50.0f, -3.0f, -60.0f}, {-10.0f, 0.0f, -79.0f}};
        const float headings[] = {0.0f, 1.3f, PI_F, -2.2f};
        for (unsigned src : kAllSources) {
            const Profile& p = *profileForSource(src);
            for (int frame = p.firstFrame; frame <= p.lastFrame; ++frame) {
                for (float h : headings) {
                    Scene sc;
                    for (const Vec3& l : rearLocal) sc.prey.push_back(pikmin(localToWorld(origin, h, l)));
                    const int n = sc.run(p, frame, origin, h);
                    require(n == 0 && sc.calls.empty(), "T3 rear-only Pikmin never captured");
                }
            }
        }
    }

    // --- T4: side boundary (outward -x from kamu2) ---
    {
        const Vec3 k2 = slotWorld(chappy, 10, 1, origin, 0.0f);
        Scene in;
        in.prey.push_back(pikmin(add(k2, Vec3{-34.9f, 0.0f, 0.0f})));
        in.run(chappy, 10, origin, 0.0f);
        require(in.captured.size() == 1 && in.captured[0].slot == 1, "T4 side 34.9 captured into slot 1");
        Scene at;
        const Vec3 atPos = add(k2, Vec3{-35.0f, 0.0f, 0.0f});
        at.prey.push_back(pikmin(atPos));
        at.run(chappy, 10, origin, 0.0f);
        require(distance(k2, atPos) >= 35.0f && at.calls.empty(), "T4 side 35.0 not captured");
        Scene out;
        out.prey.push_back(pikmin(add(k2, Vec3{-35.1f, 0.0f, 0.0f})));
        out.run(chappy, 10, origin, 0.0f);
        require(out.calls.empty(), "T4 side 35.1 not captured");
        // Exact boundary on exactly representable geometry: distance == radius
        // is refused (source `dist < slot->mRadius`), just inside is captured.
        static const float kExact[1][3] = {{0.0f, 16.0f, 64.0f}};
        const Profile exact{999, 1, 16.0f, 1.0f, 10, 10, kExact};
        Scene edge;
        edge.prey.push_back(pikmin(Vec3{16.0f, 16.0f, 64.0f}));
        edge.prey.push_back(pikmin(Vec3{0.0f, 0.0f, 64.0f}));
        edge.prey.push_back(pikmin(Vec3{0.0f, 16.0f, 48.0f}));
        require(eat(exact, 10, origin, 0.0f, edge.prey.data(), 3, edge.occupied, [](int, int) { return true; }) == 0,
                "T4 distance == radius is not captured (strict <)");
        Scene justIn;
        justIn.prey.push_back(pikmin(Vec3{15.5f, 16.0f, 64.0f}));
        require(eat(exact, 10, origin, 0.0f, justIn.prey.data(), 1, justIn.occupied, [](int, int) { return true; }) == 1,
                "T4 just inside radius captured");
    }

    // --- T5: height boundary (below kamu3) ---
    {
        const Vec3 k3 = slotWorld(chappy, 10, 2, origin, 0.0f);
        Scene in;
        in.prey.push_back(pikmin(add(k3, Vec3{0.0f, -34.9f, 0.0f})));
        in.run(chappy, 10, origin, 0.0f);
        require(in.captured.size() == 1 && in.captured[0].slot == 2, "T5 height 34.9 captured into slot 2");
        Scene out;
        out.prey.push_back(pikmin(add(k3, Vec3{0.0f, -35.1f, 0.0f})));
        out.run(chappy, 10, origin, 0.0f);
        require(out.calls.empty(), "T5 height 35.1 not captured");
    }

    // --- T6: capacity per species ---
    {
        struct Expect {
            unsigned source;
            int slots;
            int frame;
        };
        const Expect rows[] = {{2, 5, 10}, {33, 5, 10}, {35, 5, 10}, {43, 5, 10}, {67, 3, 10},
                               {76, 1, 8},  {44, 1, 8},  {53, 9, 45}};
        for (const Expect& e : rows) {
            const Profile& p = *profileForSource(e.source);
            require(p.slots == e.slots, "T6 source slot count");
            Scene sc;
            for (int i = 0; i < p.slots; ++i) sc.prey.push_back(pikmin(slotWorld(p, e.frame, i, origin, 0.0f)));
            while (sc.prey.size() < 12) sc.prey.push_back(pikmin(slotWorld(p, e.frame, 0, origin, 0.0f)));
            const int n = sc.run(p, e.frame, origin, 0.0f);
            require(n == e.slots, "T6 capacity equals the source slot count");
            int occ = 0;
            for (int i = 0; i < MaxSlots; ++i) occ += sc.occupied[i] ? 1 : 0;
            require(occ == e.slots, "T6 never more than slots occupied");
            bool distinct = true;
            for (size_t a = 0; a < sc.captured.size(); ++a)
                for (size_t b = a + 1; b < sc.captured.size(); ++b)
                    if (sc.captured[a].slot == sc.captured[b].slot) distinct = false;
            require(distinct, "T6 one Pikmin per slot");
            // A second bite with every slot full captures nothing (no overflow).
            Scene again;
            again.prey = sc.prey;
            for (int i = 0; i < p.slots; ++i) again.occupied[i] = true;
            require(again.run(p, e.frame, origin, 0.0f) == 0 && again.calls.empty(), "T6 full mouth never overflows");
        }
    }

    // --- T7: occupied slots ---
    {
        const Vec3 k1 = slotWorld(chappy, 10, 0, origin, 0.0f);
        const Vec3 k2 = slotWorld(chappy, 10, 1, origin, 0.0f);
        Scene a;
        for (int i = 0; i < 5; ++i) a.occupied[i] = true;
        a.prey.push_back(pikmin(k1));
        require(a.run(chappy, 10, origin, 0.0f) == 0 && a.calls.empty(), "T7a all occupied captures nothing");
        Scene b;
        for (int i = 1; i < 5; ++i) b.occupied[i] = true;
        b.prey.push_back(pikmin(k1));
        require(b.run(chappy, 10, origin, 0.0f) == 1 && b.captured[0].slot == 0, "T7b free slot 0 captures");
        Scene c;
        for (int i = 1; i < 5; ++i) c.occupied[i] = true;
        c.prey.push_back(pikmin(add(k2, Vec3{-34.9f, 0.0f, 0.0f})));
        require(c.run(chappy, 10, origin, 0.0f) == 0 && c.calls.empty(),
                "T7c free slot out of reach: no capture, no overflow");
        // Occupied slot skipped, later in-reach slot used for the same prey.
        Scene d;
        d.occupied[0] = true;
        d.prey.push_back(pikmin(slotWorld(chappy, 10, 2, origin, 0.0f)));
        require(d.run(chappy, 10, origin, 0.0f) == 1 && d.captured[0].slot != 0, "T7d occupied slot skipped");
    }

    // --- T8: failed stimulate leaves the slot free; the prey is not retried ---
    {
        Scene sc;
        const Vec3 k1 = slotWorld(chappy, 10, 0, origin, 0.0f);
        sc.prey.push_back(pikmin(k1));
        sc.prey.push_back(pikmin(k1));
        sc.accept = {false, true};
        const int n = sc.run(chappy, 10, origin, 0.0f);
        require(n == 1, "T8 one capture after a refused stimulate");
        require(sc.calls.size() == 2 && sc.calls[0].prey == 0 && sc.calls[1].prey == 1, "T8 failed prey not retried");
        require(sc.calls[0].slot == 0 && sc.calls[1].slot == 0, "T8 refused slot stays free for the next prey");
        require(sc.occupied[0], "T8 slot occupied only on success");
    }

    // --- T9: attached / ineligible prey ---
    {
        const Vec3 k3 = slotWorld(chappy, 10, 2, origin, 0.0f);
        Prey self = pikmin(k3);
        self.stuckToSelf = true;
        self.stuckToAny = true;
        Prey mouth = pikmin(k3);
        mouth.stuckToAnyMouth = true;
        mouth.stuckToAny = true;
        Prey dead = pikmin(k3);
        dead.alive = false;
        Prey hidden = pikmin(k3);
        hidden.visible = false;
        Prey buried = pikmin(k3);
        buried.buried = true;
        const Prey refused[] = {self, mouth, dead, hidden, buried};
        for (const Prey& p : refused) {
            require(!eligible(p), "T9 ineligible prey");
            Scene sc;
            sc.prey.push_back(p);
            require(sc.run(chappy, 10, origin, 0.0f) == 0 && sc.calls.empty(), "T9 ineligible prey never stimulated");
        }
        Prey other = pikmin(k3);
        other.stuckToAny = true; // stuck to another creature: source condition accepts
        require(eligible(other), "T9 Pikmin stuck to another creature is eligible");
        Scene sc;
        sc.prey.push_back(other);
        require(sc.run(chappy, 10, origin, 0.0f) == 1, "T9 Pikmin stuck elsewhere captured");
    }

    // --- T10: host mouth mapping ---
    {
        require(hostPartIndex(0, 0) == -1 && hostPartIndex(4, 0) == -1, "T10 no host mouth -> -1");
        require(hostPartIndex(5, 3) == 2, "T10 5 % 3 maps to 2");
        require(hostPartIndex(0, 1) == 0 && hostPartIndex(8, 5) == 3 && hostPartIndex(2, 5) == 2,
                "T10 shared-part mapping");
        Scene sc;
        sc.prey.push_back(pikmin(slotWorld(chappy, 10, 0, origin, 0.0f)));
        int refusedNoHost = 0, nullRequests = 0;
        const int hostCount = 0;
        const int n = eat(chappy, 10, origin, 0.0f, sc.prey.data(), (int)sc.prey.size(), sc.occupied,
                          [&](int, int slot) {
                              const int idx = hostPartIndex(slot, hostCount);
                              if (idx < 0) {
                                  ++refusedNoHost;
                                  return false;
                              }
                              ++nullRequests; // unreachable: a part index always exists here
                              return true;
                          });
        require(n == 0 && refusedNoHost == 1 && nullRequests == 0, "T10 no host mouth refuses the capture");
        require(!sc.occupied[0], "T10 refused capture leaves the slot free");
    }

    // --- T11: King side sweep needs the whole 40..94 window ---
    {
        const Vec3 side = slotWorld(king, 75, 0, origin, 0.0f);
        require(side.x < -60.0f, "T11 frame-75 slot 0 is on the side");
        Scene only40;
        only40.prey.push_back(pikmin(side));
        require(only40.run(king, 40, origin, 0.0f) == 0, "T11 frame 40 alone does not reach the side");
        Scene sweep;
        sweep.prey.push_back(pikmin(side));
        int captureFrame = -1;
        for (int f = king.firstFrame; f <= king.lastFrame; ++f) {
            if (sweep.run(king, f, origin, 0.0f) > 0 && captureFrame < 0) captureFrame = f;
            // Captured prey is stuck to the mouth afterwards (not eligible again).
            if (!sweep.captured.empty()) sweep.prey[0].stuckToAnyMouth = true;
        }
        require(captureFrame > 40 && captureFrame <= 75, "T11 side prey captured during the sweep");
        require(sweep.captured.size() == 1, "T11 side prey captured once");
        Scene rear;
        rear.prey.push_back(pikmin(Vec3{0.0f, 0.0f, -30.0f}));
        for (int f = king.firstFrame; f <= king.lastFrame; ++f) rear.run(king, f, origin, 0.0f);
        require(rear.calls.empty(), "T11 rear prey never captured across the window");
        require(eat(king, 39, origin, 0.0f, rear.prey.data(), 1, rear.occupied, [](int, int) { return true; }) == 0 &&
                    eat(king, 95, origin, 0.0f, rear.prey.data(), 1, rear.occupied, [](int, int) { return true; }) == 0,
                "T11 frames outside the window never eat");
    }

    // --- T12: manager order decides a contested single slot ---
    {
        const Vec3 k = slotWorld(kumako, 8, 0, origin, 0.0f);
        const Vec3 p = add(k, Vec3{2.0f, 0.0f, 0.0f});
        const Vec3 q = add(k, Vec3{-1.0f, 0.0f, 0.0f}); // nearer, but listed second
        Scene first;
        first.prey.push_back(pikmin(p));
        first.prey.push_back(pikmin(q));
        first.run(kumako, 8, origin, 0.0f);
        require(first.captured.size() == 1 && first.captured[0].prey == 0, "T12 manager-order first wins");
        Scene swapped;
        swapped.prey.push_back(pikmin(q));
        swapped.prey.push_back(pikmin(p));
        swapped.run(kumako, 8, origin, 0.0f);
        require(swapped.captured.size() == 1 && swapped.captured[0].prey == 0, "T12 reordered first wins");
    }

    // --- T13: table integrity ---
    {
        for (unsigned src : kAllSources) require(profileForSource(src) != nullptr, "T13 admitted source has a profile");
        require(profileForSource(42) == nullptr && profileForSource(0) == nullptr, "T13 no profile for others");
        struct Row {
            unsigned source;
            int slots;
            float radius;
            int first, last;
        };
        const Row rows[] = {{2, 5, 35.0f, 10, 10}, {33, 5, 35.0f, 10, 10}, {35, 5, 35.0f, 10, 10},
                            {43, 5, 35.0f, 10, 10}, {53, 9, 25.0f, 40, 94}, {67, 3, 30.0f, 10, 10},
                            {76, 1, 15.0f, 8, 8},   {44, 1, 15.0f, 8, 8}};
        for (const Row& r : rows) {
            const Profile& p = *profileForSource(r.source);
            require(p.slots == r.slots && p.radius == r.radius && p.scale == 1.0f, "T13 slots/radius/scale");
            require(p.firstFrame == r.first && p.lastFrame == r.last, "T13 frame window");
            require(p.slots <= MaxSlots, "T13 slots fit MaxSlots");
            for (int f = p.firstFrame; f <= p.lastFrame; ++f) {
                for (int i = 0; i < p.slots; ++i) {
                    const Vec3 l = slotLocal(p, f, i);
                    require(std::isfinite(l.x) && std::isfinite(l.y) && std::isfinite(l.z), "T13 finite slot");
                    require(l.z - effectiveRadius(p) > 0.0f, "T13 every slot sphere is in front of the feet");
                }
            }
        }
        require(profileForSource(2)->table == profileForSource(43)->table &&
                    profileForSource(2)->table == profileForSource(35)->table,
                "T13 Chappy/Yellow/Kuma share one table");
        require(profileForSource(76)->table == profileForSource(44)->table, "T13 KumaKo/BlueKochappy share one table");
    }

    // --- T14: legacy oracle separates old and new behaviour on the same scenes ---
    {
        std::vector<Prey> scene;
        scene.push_back(pikmin(Vec3{0.0f, 0.0f, -20.0f}));
        scene.push_back(pikmin(slotWorld(chappy, 10, 2, origin, 0.0f)));
        bool hostFree[5] = {};
        const LegacyResult old = legacyDoEat(scene, origin, hostFree, 5);
        require(old.prey == 0, "T14 legacy oracle picks the rear Pikmin");
        Scene now;
        now.prey = scene;
        now.run(chappy, 10, origin, 0.0f);
        require(!now.stimulated(0) && now.captured.size() == 1 && now.captured[0].prey == 1,
                "T14 eat() refuses the rear Pikmin the oracle takes");

        std::vector<Prey> full;
        full.push_back(pikmin(slotWorld(chappy, 10, 0, origin, 0.0f)));
        bool hostFull[5] = {true, true, true, true, true};
        const LegacyResult overflow = legacyDoEat(full, origin, hostFull, 5);
        require(overflow.prey == 0 && overflow.nullPartKill, "T14 legacy oracle overflow-kills through the null part");
        Scene noOverflow;
        noOverflow.prey = full;
        for (int i = 0; i < 5; ++i) noOverflow.occupied[i] = true;
        require(noOverflow.run(chappy, 10, origin, 0.0f) == 0 && noOverflow.calls.empty(),
                "T14 eat() never overflows a full mouth");
        // Diagnostic helpers used by the runtime log fields.
        const int legacyIdx = nearestIndex(scene.data(), (int)scene.size(), origin, 80.0f,
                                           [](const Prey& p) { return legacyEdible(p); });
        require(legacyIdx == 0 && toLocal(origin, 0.0f, scene[legacyIdx].pos).z <= 0.0f,
                "T14 legacy_would_eat_behind diagnostic flags the rear pick");
    }

    // --- T15: King attack gate / target search (runtime i1-53 diagnosis) ---
    // Candidate build: 4 King attacks, 0 captures, captain at tdist=18. The
    // port gate (XZ < fp20 130 and angle <= fp21 30) started the tongue on
    // targets under the chin; source checkAttack also requires the target
    // outside the fp06 invisible range (80), and the tongue slots only reach
    // ground prey from ~75 out, so a sub-80 trigger sweeps empty ground.
    {
        using namespace p2chappymouth::king;
        const float groundY = -1.5f; // observed prey local_y (i1-2 P2_CHAPPY_EAT lines)
        auto sweepCaptures = [&](const Vec3& p) {
            Scene sc;
            sc.prey.push_back(pikmin(p));
            for (int f = king.firstFrame; f <= king.lastFrame && sc.captured.empty(); ++f) sc.run(king, f, origin, 0.0f);
            return !sc.captured.empty();
        };
        // Ground prey under the chin is never reachable by any window frame.
        for (int d = 0; d <= 70; ++d) {
            require(!sweepCaptures(Vec3{0.0f, groundY, float(d)}), "T15 ground prey inside 70 never reached");
        }
        // Every on-axis ground target the source gate admits is reached.
        for (int d = 81; d <= 129; ++d) {
            require(sweepCaptures(Vec3{0.0f, groundY, float(d)}), "T15 on-axis ground target 81..129 reached");
        }
        for (int d = 95; d <= 125; ++d) {
            const float a = 20.0f * DegToRad;
            require(sweepCaptures(Vec3{d * std::sin(a), groundY, d * std::cos(a)}) &&
                        sweepCaptures(Vec3{-d * std::sin(a), groundY, d * std::cos(a)}),
                    "T15 +-20 deg ground target 95..125 reached");
        }
        // Gate: the i1-53 trigger (captain 18 in front) is refused; 100 ahead is taken.
        require(!attackGate(origin, 0.0f, Vec3{0.0f, 0.0f, 18.0f}), "T15 gate refuses a target at 18");
        require(!attackGate(origin, 0.0f, Vec3{0.0f, 0.0f, 80.0f}), "T15 gate refuses the invisible-range edge");
        require(attackGate(origin, 0.0f, Vec3{0.0f, 0.0f, 100.0f}), "T15 gate takes a target at 100 ahead");
        require(!attackGate(origin, 0.0f, Vec3{0.0f, 0.0f, 130.0f}), "T15 gate refuses fp20 edge");
        require(!attackGate(origin, 0.0f, Vec3{0.0f, 90.0f, 100.0f}), "T15 gate range is 3D");
        {
            const float a = 35.0f * DegToRad;
            require(!attackGate(origin, 0.0f, Vec3{100.0f * std::sin(a), 0.0f, 100.0f * std::cos(a)}),
                    "T15 gate refuses 35 deg");
            const float h = 1.2f;
            require(attackGate(Vec3{50.0f, 3.0f, -20.0f}, h,
                               localToWorld(Vec3{50.0f, 3.0f, -20.0f}, h, Vec3{0.0f, 0.0f, 100.0f})),
                    "T15 gate follows the heading");
        }
        // Legacy port gate on the same trigger admitted it (the defect).
        {
            const p2chappy::SpeciesParams* sp = p2chappy::speciesForSource(53);
            const float d = 18.0f;
            const bool legacyGate = d < sp->attackRange && 0.0f <= sp->attackAngle;
            require(legacyGate, "T15 legacy port gate would have attacked at 18");
            require(sp->attackRange == AttackRange && sp->attackAngle == AttackAngleDeg, "T15 fp20/fp21 agree");
        }
        // Target search.
        const Vec3 naviNear{0.0f, 0.0f, 18.0f};
        Candidate c[6] = {
            {Vec3{0.0f, 0.0f, 40.0f}, true},   // 0: inside invisible range
            {Vec3{0.0f, 0.0f, 100.0f}, true},  // 1: valid
            {Vec3{0.0f, 60.0f, 90.0f}, true},  // 2: above the +-50 band
            {Vec3{0.0f, 0.0f, -95.0f}, true},  // 3: behind (outside 120 deg)
            {Vec3{0.0f, 0.0f, 85.0f}, false},  // 4: in a mouth (not searchable)
            {Vec3{30.0f, 0.0f, 120.0f}, true}, // 5: valid, farther than 1
        };
        require(selectTarget(origin, 0.0f, nullptr, c, 6) == 1, "T15 nearest searchable Pikmin beyond 80 chosen");
        require(selectTarget(origin, 0.0f, &naviNear, c, 6) == -2,
                "T15 a captain under the chin blocks Pikmin targets (shared searchDist)");
        const Vec3 naviFar{0.0f, 0.0f, 300.0f};
        require(selectTarget(origin, 0.0f, &naviFar, c, 6) == 1, "T15 a nearer Pikmin beats a far captain");
        const Vec3 naviBehind{0.0f, 0.0f, -30.0f};
        require(selectTarget(origin, 0.0f, &naviBehind, c, 6) == 1, "T15 a captain behind the cone is ignored");
        Candidate only[3] = {c[0], c[2], c[4]};
        require(selectTarget(origin, 0.0f, nullptr, only, 3) == -1, "T15 no valid target");
    }

    // --- T16: window diagnostics (closest / front / stuck_self) ---
    {
        WindowDiag d;
        std::vector<Prey> prey;
        prey.push_back(pikmin(add(slotWorld(chappy, 10, 2, origin, 0.0f), Vec3{0.0f, 0.0f, 3.0f})));
        Prey latched = pikmin(Vec3{0.0f, 20.0f, 10.0f});
        latched.stuckToSelf = true;
        latched.stuckToAny = true;
        prey.push_back(latched);
        prey.push_back(pikmin(Vec3{0.0f, 0.0f, -30.0f}));
        bool occ[MaxSlots] = {};
        observe(d, chappy, 10, origin, 0.0f, prey.data(), (int)prey.size(), occ);
        require(d.frames == 1 && std::fabs(d.closest - 3.0f) < 1e-3f && d.closestSlot == 2 && d.closestFrame == 10,
                "T16 closest measured to the nearest free slot");
        require(std::fabs(d.closestLocal.z - (slotLocal(chappy, 10, 2).z + 3.0f)) < 1e-3f, "T16 closest_local");
        require(d.front == 1 && d.stuckSelf == 1 && d.eligibleMin == 2, "T16 front / stuck_self / eligible_min");
        WindowDiag full;
        bool allOcc[MaxSlots] = {true, true, true, true, true};
        observe(full, chappy, 10, origin, 0.0f, prey.data(), (int)prey.size(), allOcc);
        require(full.closest < 0.0f, "T16 no free slot -> closest=-1");
        require(maxReach(*profileForSource(76)) > 30.0f && maxReach(*profileForSource(76)) < 50.0f,
                "T16 KumaKo reach");
        WindowDiag kw;
        for (int f = king.firstFrame; f <= king.lastFrame; ++f)
            observe(kw, king, f, origin, 0.0f, prey.data(), (int)prey.size(), occ);
        require(kw.frames == 55, "T16 King window observes 55 frames");
    }

    // --- T17: King pursuit, turn and gate reasons (#884 round 2) ---
    // Review of 1a7ee890e: the port King Walk went Walk -> WarCry on every
    // sighting and never turned or moved toward a target, so with the source
    // gate a target outside the fixed +-30 deg cone could never be attacked.
    // Source StateWalk walkFunc/checkTurn and StateTurn (kingChappy.cpp:
    // 1585-1612, 2505-2521; kingChappyState.cpp:69-107, 1800-1823).
    {
        using namespace p2chappymouth::king;
        // Turn law: remaining angle *= (1 - fp08) per source frame; a
        // multi-frame step equals the per-frame iteration.
        {
            const Vec3 goal{100.0f, 0.0f, 0.0f}; // 90 deg right
            float h1 = 0.0f;
            for (int f = 0; f < 10; ++f) h1 = turnStep(h1, origin, goal, 1.0f);
            const float h10 = turnStep(0.0f, origin, goal, 10.0f);
            require(std::fabs(h1 - h10) < 1e-4f, "T17 fractional turn step equals per-frame source law");
            const float expect = 0.5f * PI_F * (1.0f - std::pow(1.0f - TurnFactor, 10.0f));
            require(std::fabs(h10 - expect) < 1e-4f, "T17 turn factor fp08");
            float ang = 0.0f;
            require(turnStep(0.3f, origin, goal, 0.0f, &ang) == 0.3f && std::fabs(ang - (0.5f * PI_F - 0.3f)) < 1e-4f,
                    "T17 zero frames keeps heading, reports pre-turn angle");
            require(std::fabs(turnStep(0.0f, origin, goal, 1.0f)) <= MaxTurnDeg * DegToRad + 1e-6f, "T17 fp28 cap");
        }
        // checkTurn: proper fp01 60 deg.
        {
            const float a61 = 61.0f * DegToRad, a59 = 59.0f * DegToRad;
            require(needsTurn(origin, 0.0f, Vec3{std::sin(a61) * 100.0f, 0.0f, std::cos(a61) * 100.0f}),
                    "T17 checkTurn above fp01");
            require(!needsTurn(origin, 0.0f, Vec3{std::sin(a59) * 100.0f, 0.0f, std::cos(a59) * 100.0f}),
                    "T17 no turn below fp01");
        }
        // Gate reasons (logged on P2_CHAPPY_KING_GATE).
        {
            const Vec3 t18{0.0f, 0.0f, 18.0f}, t100{0.0f, 0.0f, 100.0f}, t140{0.0f, 0.0f, 140.0f};
            const Vec3 side{100.0f * std::sin(35.0f * DegToRad), 0.0f, 100.0f * std::cos(35.0f * DegToRad)};
            require(gateReason(origin, 0.0f, nullptr) == GateNoTarget, "T17 gate no_target");
            require(gateReason(origin, 0.0f, &t18) == GateInvisible, "T17 gate invisible (i1-53 captain at 18)");
            require(gateReason(origin, 0.0f, &t140) == GateRange, "T17 gate range");
            require(gateReason(origin, 0.0f, &side) == GateAngle, "T17 gate angle");
            require(gateReason(origin, 0.0f, &t100) == GateOk && attackGate(origin, 0.0f, t100), "T17 gate ok");
            require(std::string(gateName(GateInvisible)) == "invisible" && std::string(gateName(GateOk)) == "ok",
                    "T17 gate names");
        }
        // A Pikmin 200 away at 90 deg. (At 120 / 90 deg the source turn law,
        // 2% of the angle per frame, lets the target slip inside fp06 before
        // the angle drops under fp21: the source Emperor overruns close side
        // targets.) Round 3: the former frozen-heading "legacy oracle" here
        // could not fail (it re-implemented the defect and asserted it); the
        // Walk-state ordering that caused it is now the pure
        // king::walkStateStep, pinned in T18.
        const Vec3 prey90{200.0f, 0.0f, 0.0f};
        Candidate lone[1] = {{prey90, true}};
        // Source pursuit: Walk -> Turn -> Walk opens the gate with the target
        // still outside the invisible range (tongue band).
        {
            Walker w;
            initWalker(w, origin);
            Vec3 pos = origin;
            float heading = 0.0f;
            int state = 0; // 0 walk, 6 turn
            int attackFrame = -1;
            float attackDist = 0.0f;
            bool turned = false;
            for (int f = 0; f < 600 && attackFrame < 0; ++f) {
                tickDelay(w, 1.0f);
                const bool searched = canSearch(w, pos);
                const int pick = searched ? selectTarget(pos, heading, nullptr, lone, 1) : -1;
                const Vec3* target = pick == 0 ? &prey90 : nullptr;
                if (target && attackGate(pos, heading, *target)) {
                    attackFrame = f;
                    attackDist = std::sqrt(sqrXZ(pos, *target));
                    break;
                }
                if (state == 0) {
                    const WalkResult r = walkTick(w, pos, heading, target, 1.0f, 0.5f, 0.5f);
                    if (r == WalkTurn) {
                        state = 6;
                        turned = true;
                        continue;
                    }
                    pos.x += std::sin(heading) * MoveSpeed / 30.0f;
                    pos.z += std::cos(heading) * MoveSpeed / 30.0f;
                } else {
                    if (turnTick(heading, pos, target ? *target : w.goal, target != nullptr, 1.0f)) state = 0;
                }
            }
            require(turned, "T17 a 90 deg target sends the King through Turn (checkTurn)");
            require(attackFrame > 0 && attackFrame < 200, "T17 source pursuit opens the attack gate");
            require(attackDist > InvisibleRange && attackDist < AttackRange, "T17 attack starts in the tongue band");
        }
        // Stall check: blocked for > 120 frames -> 120-frame search delay, goal home.
        {
            Walker w;
            initWalker(w, Vec3{0.0f, 0.0f, -200.0f});
            float heading = 0.0f;
            const Vec3 captain{0.0f, 0.0f, 18.0f};
            // First check (call 121) only records the position; the second
            // (call 242) sees < 30 units of travel.
            for (int f = 0; f < 242; ++f) walkTick(w, origin, heading, &captain, 1.0f, 0.5f, 0.5f);
            require(w.searchDelay == SearchDelayFrames && goalIsHome(w) && !canSearch(w, origin),
                    "T17 stall check delays the search and sends the King home");
            tickDelay(w, 121.0f);
            require(w.searchDelay == 0.0f && canSearch(w, origin), "T17 search resumes after the delay");
        }
        // Incubation (ip01 500): no target -> walk home, Hide at home.
        {
            Walker w;
            initWalker(w, origin);
            w.goal = Vec3{200.0f, 0.0f, 0.0f};
            float heading = 0.5f * PI_F;
            const Vec3 away{150.0f, 0.0f, 0.0f};
            WalkResult r = WalkOn;
            for (int f = 0; f < 502; ++f) r = walkTick(w, away, heading, nullptr, 1.0f, 0.5f, 0.5f);
            require(r != WalkHide && goalIsHome(w), "T17 incubation sends the King home");
            require(walkTick(w, Vec3{10.0f, 0.0f, 0.0f}, heading, nullptr, 1.0f, 0.5f, 0.5f) == WalkHide,
                    "T17 Hide on reaching home");
            require(w.noTargetFrames == 0.0f, "T17 incubation timer reset at Hide");
            enterWalk(w, false);
            w.noTargetFrames = 7.0f;
            enterWalk(w, true);
            require(w.noTargetFrames == 0.0f, "T17 StateWalk::init resets the timer only with a target");
        }
        // setNextGoal.
        {
            Walker w;
            initWalker(w, origin);
            const Vec3 t{40.0f, 0.0f, 40.0f};
            nextGoal(w, origin, &t, 0.0f, 0.0f);
            require(w.goal.x == 40.0f && w.goal.z == 40.0f, "T17 next goal is the target");
            nextGoal(w, origin, nullptr, 0.0f, 0.25f);
            require(std::fabs(w.goal.x - 90.0f) < 1e-3f && std::fabs(w.goal.z) < 1e-3f, "T17 wander goal radius 0.3*fp09");
            nextGoal(w, Vec3{400.0f, 0.0f, 0.0f}, &t, 0.0f, 0.0f);
            require(goalIsHome(w), "T17 out of territory -> home");
        }
        // Census for the gate line (round 3: front = reachable by a slot).
        {
            Candidate c[4] = {
                {Vec3{0.0f, 0.0f, 30.0f}, true},  // under the chin: ahead but unreachable
                {Vec3{0.0f, 0.0f, 100.0f}, true}, // band + front
                {Vec3{0.0f, 0.0f, -40.0f}, true}, // behind (180 deg): outside the cone and not ahead
                {Vec3{0.0f, 0.0f, 60.0f}, false}, // in a mouth
            };
            const Census cs = census(origin, 0.0f, c, 4, &king);
            require(cs.underChin == 1 && cs.band == 1 && cs.front == 1 && cs.latched == 0,
                    "T17 census under_chin / band / front (reachable only)");
        }
    }

    // --- T18: King checkFlick, shake-off and Walk/Turn priorities (#884 round 3) ---
    // Review of af1e35f98: with the bot captain parked ~18 in front, the
    // source prefers that captain and checkAttack refuses it (fp06), so
    // neither side attacks; the SOURCE breaks the standoff through
    // Obj::checkFlick (captain inside fp06 adds 0.1 per frame; each hit adds
    // 1.0) -> Flick. The port flicked only on >= 3 stuck Pikmin and let
    // Attack win over Flick. kingChappy.cpp:2429-2470, enemyAction.cpp:1209-1240,
    // enemyBase.cpp:2762-2773, kingChappyState.cpp:69-107, 823-918, 1800-1823.
    {
        using namespace p2chappymouth::king;
        // isStartFlick: round, (int), u8, strictly above the tier threshold.
        require(!isStartFlick(0.0f, 3) && !isStartFlick(0.0f, 25),
                "T18 stuck Pikmin alone never start a flick (old port rule: 3 stuck)");
        require(!isStartFlick(6.49f, 0) && isStartFlick(6.5f, 0) && isStartFlick(6.5f, 4), "T18 tier A: > ip01 6");
        require(!isStartFlick(12.49f, 5) && isStartFlick(12.5f, 9), "T18 tier B (ip02 5): > ip03 12");
        require(!isStartFlick(17.49f, 10) && isStartFlick(17.5f, 19), "T18 tier C (ip04 10): > ip05 17");
        require(!isStartFlick(22.49f, 20) && isStartFlick(22.5f, 60), "T18 tier D (ip06 20): > ip07 22");
        require(isStartFlick(255.4f, 0) && !isStartFlick(256.2f, 0), "T18 u8 truncation of the rounded timer");
        require(flickThreshold(4) == 6 && flickThreshold(5) == 12 && flickThreshold(10) == 17 && flickThreshold(20) == 22,
                "T18 retail shake-off tiers");
        // Hits: damageCallBack flickSpeed 1.0 per hit.
        {
            float t = 0.0f;
            for (int i = 0; i < 6; ++i) t += FlickPerHit;
            require(!checkFlick(t, 0, 3, 1.0f), "T18 six hits with three stuck: no flick");
            t += FlickPerHit;
            require(checkFlick(t, 0, 3, 1.0f), "T18 seventh hit with three stuck: flick");
            float t5 = 12.0f;
            require(!checkFlick(t5, 0, 5, 1.0f) && (t5 += FlickPerHit, checkFlick(t5, 0, 5, 1.0f)),
                    "T18 five stuck need the 13th hit");
        }
        // Captain proximity: 3D separation strictly inside fp06.
        require(naviInInvisibleRange(origin, Vec3{0.0f, 0.0f, 18.0f}) && naviInInvisibleRange(origin, Vec3{0.0f, 0.0f, 79.9f})
                    && !naviInInvisibleRange(origin, Vec3{0.0f, 0.0f, 80.0f}),
                "T18 captain inside fp06");
        require(!naviInInvisibleRange(origin, Vec3{70.0f, 50.0f, 0.0f}), "T18 checkFlick uses the 3D separation");
        {
            // The i1-53 standoff: captain parked at 18, no stuck Pikmin, no hits.
            float t = 0.0f;
            int calls = 0;
            bool fired = false;
            while (calls < 1000 && !fired) {
                ++calls;
                fired = checkFlick(t, 1, 0, 1.0f);
            }
            require(fired && calls >= 64 && calls <= 66, "T18 a captain inside fp06 starts a flick after ~65 frames");
            float t2 = 0.0f;
            require(!checkFlick(t2, 1, 0, 64.0f) && checkFlick(t2, 1, 0, 1.0f), "T18 fractional ticks accrue per frame");
            float t3 = 0.0f;
            require(checkFlick(t3, 2, 0, 33.0f), "T18 two captains accrue twice as fast");
            float t4 = 0.0f;
            bool never = true;
            for (int f = 0; f < 1000; ++f) never = never && !checkFlick(t4, 0, 0, 1.0f);
            require(never && t4 == 0.0f, "T18 no captain, no hit: the timer never moves");
        }
        // Shake geometry around the parked captain (StateFlick KEYEVENT_3).
        {
            const Vec3 foot = footPosition(origin, 0.0f);
            require(foot.z == -FootBack && foot.x == 0.0f, "T18 foot = position - 10 * facing");
            require(tramples(foot, Vec3{0.0f, 0.0f, 18.0f}), "T18 the parked captain at 18 is trampled (pressed)");
            require(!tramples(foot, Vec3{0.0f, 0.0f, 40.0f}) && inShakeRange(origin, Vec3{0.0f, 0.0f, 40.0f}),
                    "T18 a Pikmin at 40 ahead is flicked, not trampled");
            require(!tramples(foot, Vec3{0.0f, 26.0f, 10.0f}) && !tramples(foot, Vec3{0.0f, -6.0f, 10.0f}),
                    "T18 trample y band (foot.y - 5, foot.y + 25)");
            require(!inShakeRange(origin, Vec3{0.0f, 0.0f, 60.0f}) && inShakeRange(origin, Vec3{0.0f, 0.0f, 59.9f}),
                    "T18 shake range fp19 60 (3D, strict)");
            require(!tramples(foot, Vec3{0.0f, 0.0f, 50.0f}) && inShakeRange(origin, Vec3{0.0f, 0.0f, 50.0f}),
                    "T18 a captain at 50 is flicked (flickNearbyNavi), not pressed");
            require(std::fabs(flickStuckAngle(0.0f) - PI_F) < 1e-5f && std::fabs(flickStuckAngle(0.75f * PI_F) - 1.75f * PI_F) < 1e-5f
                        && std::fabs(flickStuckAngle(-0.5f * PI_F) - 0.5f * PI_F) < 1e-5f,
                    "T18 stuck Pikmin fly at roundAng(facing + pi)");
        }
        // Walk priorities (walk clip mid-loop: a transit's blend makes every
        // later check*(true) return early).
        {
            WalkInputs in;
            in.hasTarget = true;
            require(walkStateStep(in) == NextWalk, "T18 a sighting alone keeps walking (no sees -> WarCry)");
            in.inRange = true;
            require(walkStateStep(in) == NextAttack, "T18 checkAttack in range -> Attack");
            in.flickStart = true;
            require(walkStateStep(in) == NextFlick, "T18 checkFlick's transit blocks checkAttack (Flick over Attack)");
            in.shout = true;
            require(walkStateStep(in) == NextWarCry, "T18 flick below half life with the fp13 roll -> WarCry");
            in.walker = WalkTurn;
            require(walkStateStep(in) == NextTurn, "T18 checkTurn's transit blocks checkFlick and checkAttack");
            WalkInputs h;
            h.walker = WalkHide;
            require(walkStateStep(h) == NextHide, "T18 incubation Hide when nothing else transits");
            h.inRange = true;
            require(walkStateStep(h) == NextAttack, "T18 deferred Hide loses to checkAttack");
            h.flickStart = true;
            require(walkStateStep(h) == NextFlick, "T18 deferred Hide loses to checkFlick");
            require(turnStateStep(false, false, false) == NextTurn && turnStateStep(true, false, false) == NextWalk
                        && turnStateStep(true, true, false) == NextFlick && turnStateStep(false, true, true) == NextWarCry,
                    "T18 Turn: checkFlick wins over the turn ending");
            require(std::string(walkNextName(NextFlick)) == "flick" && std::string(walkNextName(NextWarCry)) == "warcry",
                    "T18 names");
        }
        // The i1-53 standoff end to end through the runtime's Walk sequence:
        // captain parked at 18 in front, 12 free Pikmin under the chin, the
        // King blocked (position fixed). Source: no attack (fp06), a flick
        // after ~65 frames, before the 242-frame stall.
        {
            Walker w;
            initWalker(w, origin);
            float heading = 0.0f, timer = 0.0f;
            const Vec3 captain{0.0f, 0.0f, 18.0f};
            std::vector<Candidate> crowd;
            for (int i = 0; i < 12; ++i)
                crowd.push_back(Candidate{Vec3{-30.0f + 5.0f * i, 0.0f, 25.0f + 3.0f * i}, true});
            int flickFrame = -1, attackFrame = -1;
            for (int f = 0; f < 400 && flickFrame < 0 && attackFrame < 0; ++f) {
                tickDelay(w, 1.0f);
                const bool searched = canSearch(w, origin);
                const int pick = searched ? selectTarget(origin, heading, &captain, crowd.data(), (int)crowd.size()) : -1;
                const Vec3* target = pick == -2 ? &captain : (pick >= 0 ? &crowd[pick].pos : nullptr);
                WalkInputs in;
                in.walker = walkTick(w, origin, heading, target, 1.0f, 0.5f, 0.5f);
                in.hasTarget = target != nullptr;
                in.flickStart = in.walker != WalkTurn
                                && checkFlick(timer, naviInInvisibleRange(origin, captain) ? 1 : 0, 0, 1.0f);
                in.inRange = target && !w.targetDropped && attackGate(origin, heading, *target);
                const WalkNext next = walkStateStep(in);
                if (next == NextFlick) flickFrame = f;
                if (next == NextAttack) attackFrame = f;
            }
            require(attackFrame < 0, "T18 standoff: the captain at 18 is never attacked (fp06)");
            require(flickFrame >= 60 && flickFrame <= 70, "T18 standoff: the source flick timer breaks it (~65 frames)");
        }
        // Reachable band: nothing on the ground under the chin (local z <= 60,
        // any lateral offset) is reached by any slot of the 40..94 window
        // (the first reachable ground points are z 65 at x +10..+30).
        {
            const float reach = maxReach(king);
            bool any = false;
            for (int x = -60; x <= 60; x += 5)
                for (int z = 0; z <= 60; z += 5)
                    any = any || tongueReaches(king, reach, origin, 0.0f, Vec3{float(x), 0.0f, float(z)});
            require(!any, "T18 the under-chin ground zone is unreachable");
            require(tongueReaches(king, reach, origin, 0.0f, Vec3{0.0f, 0.0f, 100.0f}), "T18 ground prey at 100 ahead is reachable");
            Candidate c[3] = {{Vec3{0.0f, 0.0f, 30.0f}, true}, {Vec3{0.0f, 0.0f, 100.0f}, true}, {Vec3{0.0f, 25.0f, 20.0f}, true}};
            c[2].latched = true; // latched to the body
            const Census cs = census(origin, 0.0f, c, 3, &king);
            require(cs.latched == 1 && cs.underChin == 1 && cs.front == 1 && cs.band == 1,
                    "T18 census separates free and latched Pikmin");
        }
    }

    // --- T19: King damageCallBack acceptance (#884 round 4) ---
    // Review of c1dc3df7e: the port added FlickPerHit for every InteractAttack
    // the P1 host accepted, including P1 ground attacks (aiAttack.cpp:672/691,
    // collPart nullptr, from anywhere around the body). Source
    // KingChappy::Obj::damageCallBack (kingChappy.cpp:824-848) accepts only a
    // stuck attacker with a collision part (x1.0) or a partless attacker low
    // (y < King.y + 5) within 40 XZ (x0.2); everything else is no damage and
    // no flickSpeed. actTeki applies king::damageAccept before the host.
    {
        using namespace p2chappymouth::king;
        const Vec3 kp{100.0f, 10.0f, 50.0f};
        auto attacker = [&](bool part, bool alive, bool stuck, float dx, float dy, float dz) {
            DamageAttacker a;
            a.present = true;
            a.hasCollPart = part;
            a.alive = alive;
            a.stuck = stuck;
            a.pos = Vec3{kp.x + dx, kp.y + dy, kp.z + dz};
            return a;
        };
        // (a) collision part: alive and stuck, wherever on the body.
        require(damageAccept(kp, attacker(true, true, true, 60.0f, 40.0f, 0.0f), false) == DamageStuck,
                "T19 a stuck attacker with a part is accepted (x1.0)");
        require(damageRate(DamageStuck) == 1.0f, "T19 stuck rate 1.0");
        require(damageAccept(kp, attacker(true, true, false, 5.0f, 0.0f, 0.0f), false) == DamageRefused,
                "T19 a part without a stick is refused");
        require(damageAccept(kp, attacker(true, false, true, 5.0f, 0.0f, 0.0f), false) == DamageRefused,
                "T19 a dead stuck attacker is refused");
        // (b) no collision part: low and within 40 XZ of the centre only.
        require(damageAccept(kp, attacker(false, true, false, 70.0f, 0.0f, 0.0f), false) == DamageRefused,
                "T19 a free ground attacker at 70 XZ is refused (P1 aiAttack ground hit)");
        require(damageAccept(kp, attacker(false, true, false, 0.0f, 0.0f, -90.0f), false) == DamageRefused,
                "T19 a free ground attacker behind the King is refused");
        require(damageAccept(kp, attacker(false, true, false, 18.0f, 2.0f, 18.0f), false) == DamageLowPartless,
                "T19 a low partless attacker within 40 is accepted (P1 ground Pikmin under the chin)");
        require(damageRate(DamageLowPartless) == 0.2f, "T19 low partless rate 0.2");
        require(damageAccept(kp, attacker(false, true, false, 39.9f, 0.0f, 0.0f), false) == DamageLowPartless
                    && damageAccept(kp, attacker(false, true, false, 40.0f, 0.0f, 0.0f), false) == DamageRefused,
                "T19 the XZ radius is 40, strict");
        require(damageAccept(kp, attacker(false, true, false, 10.0f, 4.99f, 0.0f), false) == DamageLowPartless
                    && damageAccept(kp, attacker(false, true, false, 10.0f, 5.0f, 0.0f), false) == DamageRefused,
                "T19 the low band is y < King.y + 5, strict");
        require(damageAccept(kp, attacker(false, true, false, 10.0f, 20.0f, 0.0f), false) == DamageRefused,
                "T19 a high partless attacker within 40 is refused");
        require(damageAccept(kp, attacker(false, true, true, 10.0f, 30.0f, 0.0f), false) == DamageRefused,
                "T19 a partless hit from a stuck attacker still needs the low band");
        require(damageAccept(kp, attacker(false, false, false, 10.0f, 0.0f, 0.0f), false) == DamageRefused,
                "T19 a dead partless attacker is refused");
        require(damageAccept(kp, DamageAttacker{}, false) == DamageRefused, "T19 an ownerless hit is refused");
        // Round-5 review: the source captain punch always carries a part
        // (R naviState.cpp:1614-1627), so damageCallBack takes the part branch
        // and refuses it (a captain is never isStickTo). The P1 host punch
        // (W naviState.cpp:3237) is partless; sourceHasCollPart maps it back.
        {
            auto punch = [&](float dx, float dy, float dz) {
                return attacker(sourceHasCollPart(false, true), true, false, dx, dy, dz);
            };
            require(damageAccept(kp, punch(18.0f, 2.0f, 18.0f), false) == DamageRefused,
                    "T19 a captain punch from under the chin is refused (source part branch, not stuck)");
            require(damageAccept(kp, punch(0.0f, 0.0f, 10.0f), false) == DamageRefused
                        && damageAccept(kp, punch(70.0f, 0.0f, 0.0f), false) == DamageRefused,
                    "T19 a captain punch is refused from any position");
            require(damageAccept(kp, punch(0.0f, 0.0f, 10.0f), true) == DamageBittered,
                    "T19 a captain punch lands only on a bittered King (x0.1)");
            // Twenty under-chin punches add no flickSpeed.
            float timer = 0.0f;
            for (int i = 0; i < 20; ++i)
                if (damageRate(damageAccept(kp, punch(10.0f, 0.0f, 10.0f), false)) > 0.0f) timer += FlickPerHit;
            require(timer == 0.0f, "T19 under-chin captain punches add no flickSpeed");
        }
        require(sourceHasCollPart(false, true) && sourceHasCollPart(true, false) && sourceHasCollPart(true, true)
                    && !sourceHasCollPart(false, false),
                "T19 a captain owner always has a source part; others keep the host part");
        require(damageAccept(kp, attacker(false, true, false, 90.0f, 50.0f, 0.0f), true) == DamageBittered
                    && damageRate(DamageBittered) == 0.1f,
                "T19 bittered accepts everything at x0.1");
        require(damageRate(DamageRefused) == 0.0f, "T19 refused rate 0");
        // End to end through the hook order (filter, then FlickPerHit only on
        // accepted hits): 20 ground hits from around the body never move the
        // timer, so three stuck Pikmin do not flick; seven stuck-part hits do.
        {
            float timer = 0.0f;
            bool flicked = false;
            for (int i = 0; i < 20; ++i) {
                const float ang = i * 0.3f;
                const DamageAttacker a = attacker(false, true, false, 70.0f * std::sin(ang), 0.0f, 70.0f * std::cos(ang));
                if (damageRate(damageAccept(kp, a, false)) > 0.0f) timer += FlickPerHit;
                flicked = flicked || checkFlick(timer, 0, 3, 0.0f);
            }
            require(!flicked && timer == 0.0f, "T19 ground attacks around the body add no flickSpeed");
            int hits = 0;
            for (; hits < 20 && !flicked; ++hits) {
                if (damageRate(damageAccept(kp, attacker(true, true, true, 30.0f, 35.0f, 0.0f), false)) > 0.0f)
                    timer += FlickPerHit;
                flicked = checkFlick(timer, 0, 3, 0.0f);
            }
            require(flicked && hits == 7, "T19 the seventh stuck-attacker hit flicks (three stuck)");
        }
    }

    std::printf("PASS p2_chappy_mouth_test checks=%d\n", gChecks);
    return 0;
}
