// Engine-free regressions for the #245 OWN Antenna Beetle campaign policy
// (pc_port/pc_p2_fuefuki_teki_policy.h + pc_p2_fuefuki_fsm.h).
//
// Each case is also compiled against one injected defect (CMake builds
// p2_fuefuki_teki_policy_mutant_<name> with -DP2_FUEFUKI_MUTANT_<NAME> and
// registers it WILL_FAIL): a case that still passed against its mutant would
// not be evidence of anything.
//
//   appear_roll    StateStay/StateLand::init resetAppearTimer rolls
//                  randWeightFloat(fp01 - fp02)            (mutant APPEAR_ZERO)
//   host_outputs   Land teleport into the territory ring with a random facing,
//                  Jump escape velocity 1500 along the facing, Untargetable
//                  hide from Jump KEYEVENT_3 through Stay   (mutant NO_HIDE)
//   multi_token    two beetles keyed on their own tokens: distinct landing
//                  rolls, exclusive claims in one table    (mutant TOKEN_UNUSED)
//   owner_panic    a live follower is released to Panic when its beetle dies
//                                                           (mutant NO_PANIC)
//   press_gate     pressCallBack accepts (Struggle, Pikmin latches) only in the
//                  mCanStruggle window; absorbs otherwise   (mutant PRESS_ALWAYS)
//   ring_filter    whistle claims only inside the growing fp22 ring, only
//                  callable Pikmin                          (mutant RING_IGNORED)
//   target_guard   P1 safety guard: Land/Walk targets the host probe rejects
//                  are re-rolled; all rejected -> home      (mutant NO_TARGET_GUARD)
#undef NDEBUG
#include "pc_p2_fuefuki_teki_policy.h"
#include <cassert>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <set>

using namespace p2fuefuki;
using S = P2FuefukiFsmState;

static int failures = 0;
#define CHECK(cond)                                                                          \
    do {                                                                                     \
        if (!(cond)) {                                                                       \
            std::fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);            \
            ++failures;                                                                      \
            return false;                                                                    \
        }                                                                                    \
    } while (0)

// Retail fuefuki/enemyparm.txt (GPVE01 rev 0), the rows the port consumes.
static const char* kRetailParm =
    "{\n{s000} 4 0.500000\n{_eof}\n}\n"
    "{\n{fp00} 4 700.000000\n{fp06} 4 250.000000\n{fp08} 4 0.100000\n{fp28} 4 10.000000\n"
    "{fp09} 4 300.000000\n{fp10} 4 100.000000\n{fp11} 4 60.000000\n{fp14} 4 0.000000\n"
    "{fp16} 4 1.000000\n{fp17} 4 120.000000\n{fp18} 4 1.000000\n{fp19} 4 30.000000\n"
    "{fp22} 4 130.000000\n{fp23} 4 0.100000\n{_eof}\n}\n"
    "{\n{fp01} 4 20.000000\n{fp02} 4 10.000000\n{fp03} 4 3.000000\n{fp11} 4 0.000000\n"
    "{fp12} 4 3.000000\n{fp13} 4 10.000000\n{fp21} 4 2.500000\n{fp22} 4 0.000000\n"
    "{fp31} 4 0.500000\n{_eof}\n}\n";

static Retail retail()
{
    std::istringstream in(kRetailParm);
    Retail r;
    std::string error;
    const bool ok = parseEnemyParm(in, r, error);
    assert(ok && r.retail);
    return r;
}

static p2retail::Motion motion(const char* name, int frames, std::vector<p2retail::Event> events)
{
    p2retail::Motion m;
    m.name = std::string(name) + ".bca";
    m.sha = std::string(64, 'a');
    m.duration = frames;
    m.attribute = 0;
    m.events = events;
    return m;
}

// Retail FUEFUKIANIM key events (fuefuki/enemyanimmgr.txt); durations are
// representative (the retail table is staged at runtime).
static Motions motions()
{
    Motions m;
    m.clip[AnimDead] = motion("dead", 60, {});
    m.clip[AnimLanding] = motion("landing", 60, {{21, 2}, {45, 3}});
    m.clip[AnimLandFail] = motion("landfail", 80, {{21, 2}, {60, 3}});
    m.clip[AnimMove] = motion("move", 20, {{4, 0}, {14, 1}});
    m.clip[AnimPivot] = motion("pivot", 20, {{4, 0}, {13, 1}});
    m.clip[AnimWait] = motion("wait", 30, {{0, 0}, {29, 1}});
    m.clip[AnimWhisle] = motion("whisle", 30, {{14, 0}, {23, 1}});
    m.clip[AnimStruggle] = motion("struggle", 45, {{20, 0}, {39, 1}});
    m.clip[AnimJump] = motion("jump", 30, {{3, 0}, {8, 1}, {13, 2}, {15, 3}});
    m.clip[AnimCarry] = motion("carry", 30, {{10, 0}, {29, 1}});
    m.loaded = true;
    return m;
}

struct Mock {
    World w;
    float x = 0.0f, z = 0.0f;
    // Integrate host velocity exactly as the engine wrapper does (no walls).
    void apply(const Commands& c)
    {
        if (c.teleport) {
            x = c.tx;
            z = c.tz;
        }
        x += c.vx * kSourceDelta;
        z += c.vz * kSourceDelta;
    }
    Commands step(Actor& a)
    {
        w.x = x;
        w.z = z;
        const Commands c = a.step(w);
        apply(c);
        w.pressed = false;
        return c;
    }
};

static Commands runUntil(Actor& a, Mock& m, S want, int maxTicks)
{
    Commands c;
    for (int i = 0; i < maxTicks; ++i) {
        c = m.step(a);
        if (a.fsm().getState() == want) return c;
    }
    return c;
}

static bool appear_roll()
{
    const Retail r = retail();
    const Motions mo = motions();
    int positive = 0;
    for (std::uint32_t token = 1; token <= 8; ++token) {
        P2FuefukiOwnershipTable table;
        Actor a;
        CHECK(a.bind(r, mo, table, token, token * 7919u, 0.0f, 0.0f, 0.0f, 0.0f));
        const float t = a.fsm().getAppearTimer();
        CHECK(t >= 0.0f && t < r.fsm.maxGroundTime - r.fsm.minGroundTime);
        if (t > 0.5f) ++positive;
    }
    // resetAppearTimer is a roll, never a constant reset to zero.
    CHECK(positive >= 4);
    // Land also re-arms the whistle so the beetle casts right after landing.
    P2FuefukiOwnershipTable table;
    Actor a;
    CHECK(a.bind(r, mo, table, 1, 42u, 0.0f, 0.0f, 0.0f, 0.0f));
    CHECK(a.fsm().getWhistleTimer() > r.fsm.maxWhistleTimeNoSquad);
    return true;
}

static bool host_outputs()
{
    const Retail r = retail();
    P2FuefukiOwnershipTable table;
    Actor a;
    Mock m;
    CHECK(a.bind(r, motions(), table, 1, 1234u, 0.0f, 0.0f, 0.0f, 0.0f));
    const Commands spawn = a.takeSpawnCommands();
    // onInit -> Land: teleport into [fp10, fp09] of home with a random facing.
    CHECK(spawn.teleport);
    const float d = std::sqrt(spawn.tx * spawn.tx + spawn.tz * spawn.tz);
    CHECK(d >= r.homeRadius - 1e-3f && d <= r.territoryRadius + 1e-3f);
    m.apply(spawn);
    // A captain inside mPrivateRadius (fp11 = 60) makes the landed beetle jump.
    NaviView navi;
    navi.id = 1;
    navi.alive = true;
    navi.x = m.x + 20.0f;
    navi.z = m.z;
    m.w.navis.push_back(navi);
    bool sawEscape = false, sawHide = false;
    for (int i = 0; i < 400 && a.fsm().getState() != S::Stay; ++i) {
        m.w.navis[0].x = m.x + 20.0f;
        m.w.navis[0].z = m.z;
        const Commands c = m.step(a);
        if (a.fsm().getState() == S::Jump && (c.vx != 0.0f || c.vz != 0.0f)) {
            // Escape velocity 1500 along the facing (StateJump::exec).
            CHECK(std::fabs(std::sqrt(c.vx * c.vx + c.vz * c.vz) - kEscapeSpeed) < 0.5f);
            CHECK(std::fabs(c.vx - kEscapeSpeed * std::sin(c.faceDir)) < 0.5f);
            sawEscape = true;
        }
        if (c.untargetableChanged && c.untargetable) sawHide = true;
    }
    CHECK(a.fsm().getState() == S::Stay);
    CHECK(sawEscape);
    CHECK(sawHide);
    const Commands stay = m.step(a);
    CHECK(stay.untargetable && stay.drawHidden && stay.vx == 0.0f && stay.vz == 0.0f);
    // fp03 airborne -> Land again: teleport + unhide.
    m.w.navis.clear();
    bool relanded = false, unhid = false;
    for (int i = 0; i < 200 && !relanded; ++i) {
        const Commands c = m.step(a);
        if (c.teleport) relanded = true;
        if (c.untargetableChanged && !c.untargetable) unhid = true;
    }
    CHECK(relanded && unhid && !a.untargetable());
    return true;
}

static bool multi_token()
{
    const Retail r = retail();
    const Motions mo = motions();
    P2FuefukiOwnershipTable table;
    Actor a, b;
    CHECK(a.bind(r, mo, table, 1, 1945764764u, 0.0f, 0.0f, 0.0f, 0.0f));
    CHECK(b.bind(r, mo, table, 2, 1254096625u, 0.0f, 0.0f, 0.0f, 0.0f));
    const Commands sa = a.takeSpawnCommands(), sb = b.takeSpawnCommands();
    // Each actor rolls its own stream from its own token.
    CHECK(std::fabs(sa.tx - sb.tx) > 1e-3f || std::fabs(sa.tz - sb.tz) > 1e-3f);
    CHECK(std::fabs(a.faceDir() - b.faceDir()) > 1e-4f);
    // Exclusive claims across instances: the same Pikmin in both rings.
    Mock ma, mb;
    ma.apply(sa);
    mb.apply(sb);
    runUntil(a, ma, S::Whisle, 200);
    runUntil(b, mb, S::Whisle, 200);
    CHECK(a.fsm().getState() == S::Whisle && b.fsm().getState() == S::Whisle);
    PikiView p;
    p.id = 77;
    p.alive = p.callable = true;
    p.x = ma.x + 1.0f;
    p.z = ma.z;
    ma.w.pikis = {p};
    p.x = mb.x + 1.0f;
    p.z = mb.z;
    mb.w.pikis = {p};
    const Commands ca = ma.step(a);
    const Commands cb = mb.step(b);
    CHECK(ca.claimed.size() == 1 && ca.claimed[0] == 77);
    CHECK(cb.claimed.empty());
    CHECK(a.holds(77) && !b.holds(77));
    return true;
}

// Drive a fresh beetle into Whisle and claim one Pikmin next to it.
static bool claimOne(Actor& a, Mock& m, std::uint32_t id)
{
    runUntil(a, m, S::Whisle, 200);
    CHECK(a.fsm().getState() == S::Whisle);
    PikiView p;
    p.id = id;
    p.alive = p.callable = true;
    p.x = m.x + 1.0f;
    p.z = m.z;
    m.w.pikis = {p};
    const Commands c = m.step(a);
    CHECK(c.claimed.size() == 1 && c.claimed[0] == id);
    return true;
}

static bool owner_panic()
{
    const Retail r = retail();
    P2FuefukiOwnershipTable table;
    Actor a;
    Mock m;
    CHECK(a.bind(r, motions(), table, 1, 99u, 0.0f, 0.0f, 0.0f, 0.0f));
    m.apply(a.takeSpawnCommands());
    if (!claimOne(a, m, 5)) return false;
    CHECK(a.holds(5));
    // The follower pings every frame; the beetle dies of ordinary damage.
    m.w.health = 0.0f;
    std::vector<std::uint32_t> panic;
    for (int i = 0; i < 200 && a.fsm().getState() != S::Dead; ++i) {
        const Commands c = m.step(a);
        panic.insert(panic.end(), c.releasedPanic.begin(), c.releasedPanic.end());
    }
    CHECK(a.fsm().getState() == S::Dead);
    CHECK(panic.size() == 1 && panic[0] == 5);
    CHECK(!a.holds(5));
    // Dead KEYEVENT_END -> kill request (host pcEscapeNow -> carcass).
    bool killed = false;
    for (int i = 0; i < 200 && !killed; ++i) killed = m.step(a).kill;
    CHECK(killed);
    return true;
}

static bool ring_filter()
{
    const Retail r = retail();
    P2FuefukiOwnershipTable table;
    Actor a;
    Mock m;
    CHECK(a.bind(r, motions(), table, 1, 314u, 0.0f, 0.0f, 0.0f, 0.0f));
    m.apply(a.takeSpawnCommands());
    runUntil(a, m, S::Whisle, 200);
    CHECK(a.fsm().getState() == S::Whisle);
    auto piki = [&](std::uint32_t id, float dist, bool callable) {
        PikiView p;
        p.id = id;
        p.alive = true;
        p.callable = callable;
        p.x = m.x + dist;
        p.z = m.z;
        return p;
    };
    // Ring after one frame of growth: (1/30) * 130 = 4.3.
    m.w.pikis = {piki(1, 2.0f, true), piki(2, 100.0f, true), piki(3, 200.0f, true), piki(4, 90.0f, false)};
    std::set<std::uint32_t> claimed;
    const Commands first = m.step(a);
    claimed.insert(first.claimed.begin(), first.claimed.end());
    CHECK(claimed.count(1) == 1);
    CHECK(claimed.count(2) == 0 && claimed.count(3) == 0 && claimed.count(4) == 0);
    for (int i = 0; i < 45 && a.fsm().getState() == S::Whisle; ++i) {
        m.w.pikis = {piki(1, 2.0f, true), piki(2, 100.0f, true), piki(3, 200.0f, true), piki(4, 90.0f, false)};
        const Commands c = m.step(a);
        claimed.insert(c.claimed.begin(), c.claimed.end());
    }
    // The ring reaches 100 once it has grown past 100/130 of fp22.
    CHECK(claimed.count(2) == 1);
    CHECK(claimed.count(3) == 0);  // outside fp22 = 130
    CHECK(claimed.count(4) == 0);  // not callable
    return true;
}

static bool press_gate()
{
    const Retail r = retail();
    P2FuefukiOwnershipTable table;
    Actor a;
    Mock m;
    CHECK(a.bind(r, motions(), table, 1, 2718u, 0.0f, 0.0f, 0.0f, 0.0f));
    m.apply(a.takeSpawnCommands());
    // Land before its KEYEVENT_3: pressCallBack returns true (absorbed, the
    // thrown Pikmin must not latch).
    CHECK(a.fsm().getState() == S::Land);
    CHECK(!a.fsm().getCanStruggle());
    CHECK(!pressAccepted(a.fsm(), true, false));
    for (int i = 0; i < 120 && !a.fsm().getCanStruggle(); ++i) m.step(a);
    CHECK(a.fsm().getState() == S::Land && a.fsm().getCanStruggle());
    // Inside the mCanStruggle window: accepted (Struggle, the Pikmin latches),
    // but never without a presser or while bittered.
    CHECK(pressAccepted(a.fsm(), true, false));
    CHECK(!pressAccepted(a.fsm(), false, false));
    CHECK(!pressAccepted(a.fsm(), true, true));
    m.w.pressed = true;
    const Commands c = m.step(a);
    CHECK(a.fsm().getState() == S::Struggle && c.transited && c.pressAccepted);
    CHECK(!pressAccepted(a.fsm(), true, false));
    return true;
}

// P1 safety guard on setTargetPosition: the host probe rejects the x > 0 half
// of the territory (stand-in for a ledge / closed-route region). No Land
// teleport and no Walk target may land there, and a probe that rejects
// everything sends the beetle home.
static bool target_guard()
{
    const Retail r = retail();
    const Motions mo = motions();
    int rerolled = 0, unprobed = 0;
    for (std::uint32_t token = 1; token <= 8; ++token) {
        P2FuefukiOwnershipTable table;
        Actor a;
        int asked = 0;
        a.setTargetProbe([&](float x, float) {
            ++asked;
            return x <= 0.0f;
        });
        CHECK(a.bind(r, mo, table, token, token * 7919u, 0.0f, 0.0f, 0.0f, 0.0f));
        const Commands spawn = a.takeSpawnCommands();
        CHECK(spawn.teleport);
        CHECK(spawn.tx <= 0.0f);
        if (asked == 0) ++unprobed;
        if (spawn.targetTries > 1) ++rerolled;
        // Walk targets over a long quiet run (Land -> Whisle -> Wait -> Turn ->
        // Walk cycles) must respect the probe too.
        Mock m;
        m.apply(spawn);
        for (int i = 0; i < 3000; ++i) {
            const Commands c = m.step(a);
            if (c.teleport) CHECK(c.tx <= 0.0f);
            if (a.fsm().getState() == S::Walk || a.fsm().getState() == S::Turn) CHECK(a.targetX() <= 0.0f);
        }
    }
    CHECK(rerolled > 0 && unprobed == 0);
    // Every roll rejected: the Land target is home, flagged as a fallback.
    P2FuefukiOwnershipTable table;
    Actor a;
    a.setTargetProbe([](float, float) { return false; });
    CHECK(a.bind(r, mo, table, 1, 99u, 40.0f, 0.0f, -25.0f, 0.0f));
    const Commands spawn = a.takeSpawnCommands();
    CHECK(spawn.teleport && spawn.targetFallback && spawn.targetTries == kTargetTries);
    CHECK(std::fabs(spawn.tx - 40.0f) < 1e-3f && std::fabs(spawn.tz + 25.0f) < 1e-3f);
    CHECK(a.fallbackTargets() == 1 && a.rejectedTargets() == kTargetTries);
    return true;
}

int main(int argc, char** argv)
{
    struct Case {
        const char* name;
        bool (*fn)();
    } cases[] = {{"appear_roll", appear_roll}, {"host_outputs", host_outputs}, {"multi_token", multi_token},
                 {"owner_panic", owner_panic}, {"ring_filter", ring_filter}, {"press_gate", press_gate},
                 {"target_guard", target_guard}};
    const char* only = argc > 1 ? argv[1] : nullptr;
    int ran = 0;
    for (const Case& c : cases) {
        if (only && std::strcmp(only, c.name) != 0) continue;
        ++ran;
        const bool ok = c.fn();
        std::printf("%s %s\n", ok ? "PASS" : "FAIL", c.name);
    }
    if (!ran) {
        std::fprintf(stderr, "no such case\n");
        return 2;
    }
    return failures ? 1 : 0;
}
