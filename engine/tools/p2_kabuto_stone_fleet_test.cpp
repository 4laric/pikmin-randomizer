// Engine-free regression for #884: Kabuto 75 fires a travelling, non-homing
// Stone on KEYEVENT_2 instead of an instant cone strike at half the clip.
// Cases follow output/claude-orch/p2-884/design-kabuto.md section 4. The
// legacy rules (half-clip fire tick, immediate 180 / 0.5 rad cone strike) are
// re-implemented here as negative controls and asserted to violate the
// properties the fleet satisfies.
// Cases 1 and 14-19 drive the campaign seam the shipped FSM calls verbatim
// (p2kabutostone::advanceStateTime / attackStep / stoneTicksFor, see
// pc_p2_kabuto_fsm.cpp KB_ATTACK and pc_p2_kabuto_fsm_update_stones) on host
// frame clocks. p2_kabuto_stone_wiring_test pins that the shipped FSM and
// gameCoreSection actually call this seam.
// Cases 21-25 (review round 4) drive the source attack selection the FSM
// calls (pc_p2_kabuto_aim.h: isAttackableTarget lane, getSearchedTarget,
// StateTurn / StateMove / StateWait decisions) against the pre-round-4 native
// 180 / 0.5 rad gate and FACE_OK Turn exit as negative controls; case 26 pins
// the strike-buffer deferral and the P2 gravity constant; case 27 (round 5)
// pins the host target offer: sprouts are never targets, swallowed Pikmin
// are never searched, against the round-4 isAlive-only offer.
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <functional>
#include <vector>

#include "pc_p2_kabuto_stone_fleet.h"
#include "pc_p2_kabuto_aim.h"

using namespace p2kabutostone;

namespace {

constexpr float kPi = 3.14159265358979323846f;
constexpr float kGravity = kStoneGravity; // retail P2 aiConstants gravity 560 (round 4; was P1 550)
constexpr float kDt = P2CannonStone::kSourceDelta;
constexpr std::uint64_t kShooter = 0x1000;

// Fake flat floor at y = 0 with an optional wall plane at z >= wallZ.
struct FlatMap {
    bool hasWall = false;
    float wallZ = 0.0f;
    int calls = 0;
};

bool flatTrace(void* ctx, const P2CannonStoneVec3& base, const P2CannonStoneVec3& vel, float dt,
               float radius, P2CannonStoneTraceResult& out)
{
    FlatMap& m = *static_cast<FlatMap*>(ctx);
    ++m.calls;
    P2CannonStoneVec3 p{ base.x + vel.x * dt, base.y + vel.y * dt, base.z + vel.z * dt };
    P2CannonStoneVec3 v = vel;
    if (p.y <= 0.0f) {
        p.y = 0.0f;
        v.y = 0.0f;
    }
    out.wall = false;
    if (m.hasWall && p.z + radius >= m.wallZ) {
        p.z = m.wallZ - radius;
        v.z = 0.0f;
        out.wall = true;
    }
    out.position = p;
    out.velocity = v;
    return true;
}

Target piki(std::uint64_t token, float x, float z, bool onFloor = true)
{
    Target t;
    t.token = token;
    t.centre = { x, 10.0f, z };
    t.radius = 10.0f;
    t.kind = P2CannonStoneContactKind::NaviPiki;
    t.onFloor = onFloor;
    t.alive = true;
    return t;
}

Target teki(std::uint64_t token, float x, float z, float radius)
{
    Target t;
    t.token = token;
    t.centre = { x, 30.0f, z };
    t.radius = radius;
    t.kind = P2CannonStoneContactKind::Teki;
    t.onFloor = true;
    t.alive = true;
    return t;
}

struct Log {
    struct S { int tick; Strike s; };
    struct D { int tick; DeadEvent d; };
    struct R { int tick; Released r; };
    std::vector<S> strikes;
    std::vector<D> deads;
    std::vector<R> released;
    int strikesOn(std::uint64_t token) const
    {
        int n = 0;
        for (const S& s : strikes) {
            n += s.s.target == token ? 1 : 0;
        }
        return n;
    }
    const S* firstOn(std::uint64_t token) const
    {
        for (const S& s : strikes) {
            if (s.s.target == token) {
                return &s;
            }
        }
        return nullptr;
    }
};

// Runs `ticks` source ticks; `before(tick, targets)` may move targets first.
void run(Fleet& fleet, FlatMap& map, std::vector<Target>& targets, int ticks, Log& log,
         const std::function<void(int, std::vector<Target>&)>& before = nullptr, int tick0 = 1)
{
    for (int i = 0; i < ticks; ++i) {
        const int tick = tick0 + i;
        if (before) {
            before(tick, targets);
        }
        Strike s[64];
        DeadEvent d[16];
        Released r[16];
        int sn = 0, dn = 0, rn = 0;
        fleet.tick(kGravity, &flatTrace, &map, targets.data(), int(targets.size()), s, 64, sn, d,
                   16, dn, r, 16, rn);
        for (int k = 0; k < sn; ++k) log.strikes.push_back({ tick, s[k] });
        for (int k = 0; k < dn; ++k) log.deads.push_back({ tick, d[k] });
        for (int k = 0; k < rn; ++k) log.released.push_back({ tick, r[k] });
    }
}

int fireForward(Fleet& fleet, std::uint32_t& id, float heading = 0.0f,
                P2CannonStoneVec3 kabuto = { 0.0f, 0.0f, 0.0f })
{
    return fleet.fire(kShooter, mouthBirthPosition(kabuto, heading), heading, id);
}

// ---- Legacy (pre-#884) rules, kept only as negative controls ----
// pc_p2_kabuto_fsm.cpp:258 (old): fire once stateTime >= 0.5 * attack clip.
int legacyHalfClipTick(int clipFrames)
{
    float t = 0.0f;
    for (int tick = 1; tick < 1000; ++tick) {
        t += 1.0f / 30.0f;
        if (t >= 0.5f * clipFrames / 30.0f) {
            return tick;
        }
    }
    return -1;
}
// pc_p2_kabuto_fsm.cpp:122-139 (old): immediate strike on everything with
// XZ distance < 180 and |angle| < 0.5 rad from the actor's feet.
bool legacyConeStrikes(const Target& t, float heading = 0.0f)
{
    const float dx = t.centre.x, dz = t.centre.z;
    if (std::sqrt(dx * dx + dz * dz) >= 180.0f) {
        return false;
    }
    float a = std::atan2(dx, dz) - heading;
    while (a > kPi) a -= 2.0f * kPi;
    while (a < -kPi) a += 2.0f * kPi;
    return std::fabs(a) < 0.5f;
}

// The shipped KB_ATTACK path (pc_p2_kabuto_fsm.cpp): prev from
// advanceStateTime, then attackStep into a real fleet. Returns the fire tick
// (or -1) and the count.
int fireTickFor(const std::vector<float>& dts, float health, int& fires, float& fireTime)
{
    Fleet fleet;
    float stateTime = 0.0f;
    bool fireDone = false;
    int tick = -1;
    fires = 0;
    for (size_t i = 0; i < dts.size(); ++i) {
        const float prev = advanceStateTime(stateTime, dts[i]);
        const AttackStep step =
            attackStep(fleet, kShooter, health, fireDone, prev, stateTime, { 0.0f, 0.0f, 0.0f }, 0.0f);
        if (step.action == AttackAction::Fired) {
            ++fires;
            tick = int(i) + 1;
            fireTime = stateTime;
        }
    }
    assert(fleet.active() == fires);
    return tick;
}

void case1_key2Timing()
{
    const int legacy = legacyHalfClipTick(95);
    assert(legacy == 48);
    int fires = 0;
    float at = 0.0f;
    {
        std::vector<float> dts(200, 1.0f / 30.0f);
        const int tick = fireTickFor(dts, 850.0f, fires, at);
        std::printf("case1 30Hz fire tick=%d t=%.4f legacy_tick=%d\n", tick, at, legacy);
        assert(fires == 1);
        // Key frame 50 is seen after 51 animator frames (sysShape.cpp:142).
        assert(tick == 51);
        assert(tick != 48);
        assert(tick != legacy); // the old rule is discriminated
        assert(at >= key2Seconds() - kKey2Epsilon && at < key2Seconds() + 1.0f / 30.0f);
    }
    {
        std::vector<float> dts(400, 1.0f / 60.0f);
        const int tick = fireTickFor(dts, 850.0f, fires, at);
        assert(fires == 1);
        assert(tick == 102);
    }
    {
        std::vector<float> dts;
        std::uint32_t s = 12345u;
        for (int i = 0; i < 300; ++i) {
            s = s * 1664525u + 1013904223u;
            const float u = float((s >> 8) & 0xffffu) / 65535.0f;
            dts.push_back(1.0f / 45.0f + u * (1.0f / 20.0f - 1.0f / 45.0f));
        }
        const int tick = fireTickFor(dts, 850.0f, fires, at);
        assert(fires == 1 && tick > 0);
        float prev = 0.0f;
        for (int i = 0; i < tick - 1; ++i) prev += dts[size_t(i)];
        assert(prev < key2Seconds() - kKey2Epsilon && at >= key2Seconds() - kKey2Epsilon);
    }
    {
        std::vector<float> dts(200, 1.0f / 30.0f);
        const int tick = fireTickFor(dts, 0.0f, fires, at);
        assert(fires == 0 && tick == -1); // KabutoState.cpp:350-353 death gate first
    }
    assert(clipHasKey2(95));
    assert(clipHasKey2(51));
    assert(!clipHasKey2(50));
    assert(std::fabs(key2Seconds() - 51.0f / 30.0f) < 1e-6f);
}

void case2_birthAndConfig()
{
    // Retail mouth joint at the KEYEVENT_2 pose (frame 51), model space.
    assert(kMouthPoseFrame == 51);
    assert(std::fabs(kMouthLocalZ - 62.898f) < 1e-3f && std::fabs(kMouthLocalX - -0.025f) < 1e-4f);
    // Heading 0: model +z is world +z.
    const P2CannonStoneVec3 a = mouthBirthPosition({ 0.0f, 0.0f, 0.0f }, 0.0f);
    assert(std::fabs(a.x - -0.025f) < 1e-4f && std::fabs(a.z - 62.898f) < 1e-3f && a.y == 25.0f);
    // Heading pi/2: model +z -> world +x, model +x -> world -z.
    const P2CannonStoneVec3 b = mouthBirthPosition({ 10.0f, 7.0f, -3.0f }, kPi / 2.0f);
    assert(std::fabs(b.y - 32.0f) < 1e-4f); // body Y + 25, not mouth Y (38.7)
    assert(std::fabs(b.x - (10.0f + 62.898f)) < 1e-3f);
    assert(std::fabs(b.z - (-3.0f + 0.025f)) < 1e-3f);
    // The previous host approximation (root sphere r55 forward) is gone.
    assert(std::fabs(a.z - 55.0f) > 5.0f);
    const P2CannonStoneConfig c = stoneConfig();
    assert(c.variant == P2CannonStoneVariant::Stone);
    assert(c.moveSpeed == 250.0f && c.attackDamage == 10.0f && c.health == 99999.0f);
    assert(c.turnSpeed == 0.03f && c.maxTurnAngle == 3.0f && c.collisionRadius == 25.0f);
    assert(c.searchRumbleSpeed == 100.0f && c.sightRadius == 150.0f);
    Fleet fleet;
    std::uint32_t id = 0;
    for (int i = 0; i < 4; ++i) {
        const int slot = fireForward(fleet, id, 0.3f * i);
        assert(slot >= 0);
        assert(!fleet.stone(slot).homing());
        assert(fleet.stone(slot).sourceToken() == kShooter);
    }
}

void case3_travelTime()
{
    Fleet fleet;
    FlatMap map;
    std::uint32_t id = 0;
    assert(fireForward(fleet, id) == 0);
    std::vector<Target> targets{ piki(1, 0.0f, 200.0f) };
    Log log;
    run(fleet, map, targets, 60, log);
    const Log::S* first = log.firstOn(1);
    assert(first);
    assert(first->tick > 3);
    // Grounded Stone: r27 leaf centred at y 25 vs Pikmin centre y 10 (r10),
    // reach sqrt(37^2 - 15^2) = 33.8 horizontally -> travel 200 - 62.9 - 33.8.
    const float reach = std::sqrt(37.0f * 37.0f - 15.0f * 15.0f);
    const float expected = (200.0f - kMouthLocalZ - reach) / 250.0f;
    std::printf("case3 first press tick=%d flight=%.3f expected~%.3f travel=%.1f\n", first->tick,
                first->s.flight, expected, first->s.travel);
    assert(first->s.flight > 0.3f);
    assert(first->s.flight >= expected - 2.0f * kDt && first->s.flight <= expected + 2.0f * kDt);
    assert(first->s.kind == P2CannonStoneStrikeKind::Press);
    assert(first->s.damage == 10.0f);
    assert(first->s.owner == kShooter);
    assert(log.strikesOn(1) == 1);
    // Negative control: the old cone strikes a Pikmin 150 ahead at flight 0;
    // the fleet reaches the same Pikmin only after travelling.
    Fleet f2;
    FlatMap m2;
    assert(fireForward(f2, id) >= 0);
    std::vector<Target> near{ piki(2, 0.0f, 150.0f) };
    assert(legacyConeStrikes(near[0])); // legacy flight = 0
    Log l2;
    run(f2, m2, near, 60, l2);
    assert(l2.firstOn(2) && l2.firstOn(2)->s.flight > 0.15f);
}

void case4_stepOut()
{
    std::uint32_t id = 0;
    { // (a) 100 units lateral: never struck.
        Fleet fleet;
        FlatMap map;
        fireForward(fleet, id);
        std::vector<Target> targets{ piki(1, 100.0f, 200.0f) };
        Log log;
        run(fleet, map, targets, 500, log);
        assert(log.strikes.empty());
        assert(log.deads.size() == 1 && log.deads[0].d.reason == DeadReason::Timeout);
    }
    { // (b) on the path, leaves it at t = 0.2 s before the Stone arrives.
        Fleet fleet;
        FlatMap map;
        fireForward(fleet, id);
        std::vector<Target> targets{ piki(1, 0.0f, 170.0f) };
        assert(legacyConeStrikes(targets[0])); // old rule: hit at t = 0
        Log log;
        run(fleet, map, targets, 120, log, [](int tick, std::vector<Target>& t) {
            if (tick == 6) t[0].centre.x = 100.0f;
        });
        assert(log.strikes.empty());
        // Control: staying put on the same spot is struck.
        Fleet f2;
        FlatMap m2;
        fireForward(f2, id);
        std::vector<Target> stay{ piki(1, 0.0f, 170.0f) };
        Log l2;
        run(f2, m2, stay, 120, l2);
        assert(l2.strikesOn(1) == 1);
    }
    { // (c) 60 lateral at 150: inside the old cone, outside the Stone's path.
        Fleet fleet;
        FlatMap map;
        fireForward(fleet, id);
        std::vector<Target> targets{ piki(1, 60.0f, 150.0f) };
        assert(legacyConeStrikes(targets[0]));
        Log log;
        run(fleet, map, targets, 200, log);
        assert(log.strikes.empty());
    }
}

void case5_noHoming()
{
    Fleet fleet;
    FlatMap map;
    std::uint32_t id = 0;
    const int slot = fireForward(fleet, id);
    assert(slot == 0 && !fleet.stone(slot).homing());
    const float face0 = fleet.stone(slot).faceDir();
    const float x0 = fleet.stone(slot).position().x; // mouth lateral offset (-0.025)
    std::vector<Target> targets{ piki(1, 100.0f, 200.0f) };
    auto circle = [](int tick, std::vector<Target>& t) {
        const float a = tick * 0.15f;
        t[0].centre.x = 100.0f * std::cos(a);
        t[0].centre.z = 200.0f + 100.0f * std::sin(a);
    };
    float lastZ = fleet.stone(slot).position().z;
    for (int tick = 1; tick <= 90; ++tick) {
        Log log;
        run(fleet, map, targets, 1, log, circle, tick);
        const P2CannonStone& s = fleet.stone(slot);
        assert(std::fabs(s.position().x - x0) < 1e-3f);
        assert(s.faceDir() == face0);
        // Source move speed 250 along the facing (homing would use 100).
        assert(std::fabs((s.position().z - lastZ) - 250.0f * kDt) < 1e-2f);
        lastZ = s.position().z;
    }
    assert(fleet.maxLateral(slot) < 1e-3f);
    // Control: a homing Stone (Rkabuto rule) against the same target deviates.
    P2CannonStone homing;
    homing.reset(stoneConfig());
    assert(homing.birth({ 0.0f, 25.0f, kMouthLocalZ }, 0.0f, true, kShooter, 99));
    float maxX = 0.0f;
    for (int tick = 1; tick <= 90; ++tick) {
        std::vector<Target> t{ piki(1, 0.0f, 0.0f) };
        circle(tick, t);
        P2CannonStoneTarget tg;
        tg.hasTarget = true;
        tg.position = t[0].centre;
        homing.update(kDt, tg);
        maxX = std::fmax(maxX, std::fabs(homing.position().x));
    }
    assert(maxX > 1.0f);
}

void case6_row()
{
    Fleet fleet;
    FlatMap map;
    std::uint32_t id = 0;
    const int slot = fireForward(fleet, id);
    std::vector<Target> targets{ piki(1, 0.0f, 150.0f), piki(2, 0.0f, 250.0f),
                                 piki(3, 0.0f, 350.0f), piki(4, 0.0f, 200.0f, false) };
    Log log;
    run(fleet, map, targets, 60, log);
    assert(log.strikesOn(1) == 1 && log.strikesOn(2) == 1 && log.strikesOn(3) == 1);
    assert(log.strikesOn(4) == 0); // airborne: no press
    assert(fleet.stone(slot).isAlive()); // Navi/Piki contact never kills the Stone
    assert(fleet.hits(slot) == 3);
    assert(log.deads.empty());
}

void case7_tekiSingleImpact()
{
    Fleet fleet;
    FlatMap map;
    std::uint32_t id = 0;
    const int slot = fireForward(fleet, id);
    const std::uint32_t firstId = id;
    std::vector<Target> targets{ teki(7, 0.0f, 150.0f, 20.0f), piki(8, 0.0f, 250.0f) };
    Log log;
    int attackTick = -1;
    P2CannonStoneVec3 deadPos;
    run(fleet, map, targets, 60, log, [&](int tick, std::vector<Target>& t) {
        // During the dead hold, move the Pikmin onto the Stone's position.
        if (!log.deads.empty() && tick > log.deads[0].tick) {
            deadPos = log.deads[0].d.pos;
            t[1].centre = { deadPos.x, 10.0f, deadPos.z };
        }
    });
    assert(log.strikesOn(7) == 1);
    const Log::S* a = log.firstOn(7);
    attackTick = a->tick;
    assert(a->s.kind == P2CannonStoneStrikeKind::Attack && a->s.damage == 250.0f);
    assert(log.deads.size() == 1);
    assert(log.deads[0].d.reason == DeadReason::Contact);
    assert(log.deads[0].tick == attackTick + 1);
    assert(log.deads[0].d.stone == firstId);
    assert(log.strikesOn(8) == 0);
    for (const auto& s : log.strikes) assert(s.tick <= log.deads[0].tick);
    assert(log.released.size() == 1 && log.released[0].r.stone == firstId);
    assert(log.released[0].tick > log.deads[0].tick);
    assert(fleet.active() == 0 && !fleet.used(slot));
    std::uint32_t id2 = 0;
    assert(fireForward(fleet, id2) == slot && id2 > firstId);
}

void case8_wall()
{
    Fleet fleet;
    FlatMap map;
    map.hasWall = true;
    map.wallZ = 120.0f;
    std::uint32_t id = 0;
    fireForward(fleet, id);
    std::vector<Target> targets{ piki(1, 0.0f, 200.0f) };
    Log log;
    run(fleet, map, targets, 60, log);
    assert(log.deads.size() == 1 && log.deads[0].d.reason == DeadReason::Wall);
    assert(log.strikes.empty());
}

void case9_timeout()
{
    Fleet fleet;
    FlatMap map;
    std::uint32_t id = 0;
    fireForward(fleet, id);
    std::vector<Target> targets;
    Log log;
    run(fleet, map, targets, 600, log);
    assert(log.deads.size() == 1);
    assert(log.deads[0].d.reason == DeadReason::Timeout);
    assert(log.deads[0].d.flight > 15.0f && log.deads[0].d.flight < 15.0f + 2.0f * kDt);
    assert(log.released.size() == 1);
    assert(fleet.active() == 0);
}

void case10_sourceGrace()
{
    Fleet fleet;
    FlatMap map;
    std::uint32_t id = 0;
    const int slot = fireForward(fleet, id);
    // The shooter's own body overlaps the birth point (62.9 ahead, radius 80).
    std::vector<Target> targets{ teki(kShooter, 0.0f, 0.0f, 80.0f) };
    Log log;
    run(fleet, map, targets, 29, log); // < 1 s of flight
    assert(log.strikes.empty());
    assert(fleet.graceIgnored() > 0);
    assert(fleet.stone(slot).isAlive());
    // Not recorded in the ledger: once grace ends a renewed overlap counts.
    run(fleet, map, targets, 3, log, [&](int, std::vector<Target>& t) {
        const P2CannonStoneVec3 p = fleet.stone(slot).position();
        t[0].centre = { p.x, p.y + kContactCentreYFull, p.z };
    }, 30);
    assert(log.strikesOn(kShooter) == 1);
    assert(log.firstOn(kShooter)->s.flight >= P2CannonStone::kAtariGraceSeconds);
}

void case11_exhaustion()
{
    Fleet fleet;
    std::uint32_t id = 0, maxId = 0;
    for (int i = 0; i < Fleet::capacity(); ++i) {
        // Stone 0 faces +Z; the others fan out over the back half-plane so
        // only stone 0 can meet the Teki placed ahead.
        const float heading = i == 0 ? 0.0f : kPi / 2.0f + kPi * float(i - 1) / 14.0f;
        assert(fireForward(fleet, id, heading) == i);
        maxId = id;
    }
    std::uint32_t refused = 777;
    assert(fireForward(fleet, refused) == -1);
    assert(refused == 777 && fleet.active() == Fleet::capacity());
    // Stone 0 (heading 0) meets a Teki right in front; the rest fly on.
    FlatMap map;
    std::vector<Target> targets{ teki(50, 0.0f, 100.0f, 20.0f) };
    Log log;
    run(fleet, map, targets, 40, log);
    assert(log.released.size() == 1 && log.released[0].r.slot == 0);
    assert(fleet.active() == Fleet::capacity() - 1);
    std::uint32_t fresh = 0;
    assert(fireForward(fleet, fresh) == 0 && fresh > maxId);
    assert(fleet.active() == Fleet::capacity());
}

void case12_forgetOwner()
{
    Fleet fleet;
    FlatMap map;
    std::uint32_t id = 0;
    const int slot = fireForward(fleet, id);
    std::vector<Target> targets{ piki(1, 0.0f, 250.0f) };
    Log log;
    run(fleet, map, targets, 5, log);
    assert(fleet.ownedBy(kShooter) == 1);
    assert(fleet.forgetOwner(kShooter) == 1);
    assert(fleet.owner(slot) == 0 && fleet.stone(slot).isAlive());
    run(fleet, map, targets, 60, log, nullptr, 6);
    assert(log.strikesOn(1) == 1 && log.firstOn(1)->s.owner == 0);
}

void case13_resetReentry()
{
    Fleet fleet;
    FlatMap map;
    std::uint32_t a = 0, b = 0;
    fireForward(fleet, a);
    fireForward(fleet, b, 1.0f);
    std::vector<Target> targets{ piki(1, 0.0f, 150.0f) };
    Log log;
    run(fleet, map, targets, 5, log);
    fleet.reset();
    assert(fleet.active() == 0);
    Log after;
    run(fleet, map, targets, 600, after);
    assert(after.strikes.empty() && after.deads.empty() && after.released.empty());
    std::uint32_t c = 0;
    assert(fireForward(fleet, c) >= 0);
    assert(c > a && c > b);
}

// ---- Campaign seam on host frame clocks ----

// One simulated campaign frame: the KB_ATTACK part of pc_p2_kabuto_fsm_update
// for one shooter, then pc_p2_kabuto_fsm_update_stones (stoneTicksFor debt +
// fleet ticks). Mirrors the shipped call order: actors update before the
// global stone update in the same frame.
struct Campaign {
    Fleet fleet;
    FlatMap map;
    std::vector<Target> targets;
    double debt = 0.0;
    float stateTime = 0.0f;
    bool fireDone = false;
    float health = 850.0f;
    bool inAttack = true;
    bool shooterAlive = true;
    float clock = 0.0f;
    int sourceTicks = 0;
    struct Birth { float t; float stateTime; AttackStep step; };
    std::vector<Birth> births;
    int dies = 0;
    Log log;

    void frame(float dt)
    {
        clock += dt;
        if (shooterAlive && inAttack) {
            const float prev = advanceStateTime(stateTime, dt);
            const AttackStep step =
                attackStep(fleet, kShooter, health, fireDone, prev, stateTime, { 0.0f, 0.0f, 0.0f }, 0.0f);
            if (step.action == AttackAction::Die) {
                ++dies;
                inAttack = false;
            } else if (step.action == AttackAction::Fired) {
                births.push_back({ clock, stateTime, step });
            }
        }
        const int ticks = stoneTicksFor(debt, dt);
        for (int i = 0; i < ticks && fleet.active() > 0; ++i) {
            ++sourceTicks;
            run(fleet, map, targets, 1, log, nullptr, sourceTicks);
        }
    }
    // FSM transition into a fresh attack (transition() resets both).
    void enterAttack()
    {
        stateTime = 0.0f;
        fireDone = false;
        inAttack = true;
    }
};

void case14_hostClockEmissionAndFlight()
{
    // 60 Hz host frames with a little jitter; Pikmin 200 ahead.
    Campaign c;
    c.targets = { piki(1, 0.0f, 200.0f) };
    std::uint32_t s = 7u;
    float firstStrikeClock = -1.0f;
    for (int f = 0; f < 240; ++f) {
        s = s * 1664525u + 1013904223u;
        const float dt = 1.0f / 60.0f + (float((s >> 8) & 0xffu) / 255.0f - 0.5f) * 0.004f;
        const size_t before = c.log.strikes.size();
        c.frame(dt);
        if (c.log.strikes.size() > before && firstStrikeClock < 0.0f) {
            firstStrikeClock = c.clock;
        }
    }
    assert(c.births.size() == 1);
    const Campaign::Birth& b = c.births[0];
    std::printf("case14 birth t=%.4f key2=%.4f strike_clock=%.3f flight=%.3f\n", b.stateTime,
                key2Seconds(), firstStrikeClock, c.log.strikes.empty() ? -1.0f : c.log.strikes[0].s.flight);
    assert(b.stateTime >= key2Seconds() - kKey2Epsilon && b.stateTime < key2Seconds() + 1.0f / 50.0f);
    assert(std::fabs(b.step.birth.z - kMouthLocalZ) < 1e-3f && b.step.birth.y == 25.0f);
    assert(!c.fleet.stone(b.step.slot).homing());
    // Travel before impact: strike strictly after the birth frame, flight > 0.
    assert(c.log.strikesOn(1) == 1);
    assert(firstStrikeClock > b.t + 0.3f);
    assert(c.log.strikes[0].s.flight > 0.3f && c.log.strikes[0].s.kind == P2CannonStoneStrikeKind::Press);
    // Negative control: the old campaign rule struck this Pikmin at half the
    // clip (t = 1.583 s) with zero flight; the seam never strikes at birth.
    assert(legacyConeStrikes(piki(1, 0.0f, 150.0f)));
}

void case15_killBeforeEvent()
{
    // (a) Killed at t = 1.5 s, before KEYEVENT_2: Die, nothing fired, ever.
    Campaign c;
    for (int f = 0; f < 120; ++f) {
        if (c.clock >= 1.5f) c.health = 0.0f;
        c.frame(1.0f / 30.0f);
    }
    assert(c.dies == 1 && c.births.empty() && c.fleet.active() == 0);
    // (b) Health reaches 0 on the very frame that crosses the event: the
    //     death gate runs first (KabutoState.cpp:350-353), still no Stone.
    Campaign d;
    for (int f = 0; f < 120; ++f) {
        const float prevT = d.stateTime;
        if (prevT < key2Seconds() - kKey2Epsilon && prevT + 1.0f / 30.0f >= key2Seconds() - kKey2Epsilon) {
            d.health = 0.0f;
        }
        d.frame(1.0f / 30.0f);
    }
    assert(d.dies == 1 && d.births.empty() && d.fleet.active() == 0);
    // (c) Control: alive through the event fires exactly once.
    Campaign e;
    for (int f = 0; f < 120; ++f) e.frame(1.0f / 30.0f);
    assert(e.dies == 0 && e.births.size() == 1);
}

void case16_stoneOutlivesShooter()
{
    Campaign c;
    c.targets = { piki(1, 0.0f, 260.0f) };
    int f = 0;
    while (c.births.empty() && f++ < 200) c.frame(1.0f / 60.0f);
    assert(c.births.size() == 1);
    const int slot = c.births[0].step.slot;
    // Shooter killed right after firing, then destroyed (forget) next frame.
    c.health = 0.0f;
    c.frame(1.0f / 60.0f);
    assert(c.dies == 1);
    c.shooterAlive = false;
    assert(c.fleet.forgetOwner(kShooter) == 1);
    assert(c.fleet.used(slot) && c.fleet.stone(slot).isAlive());
    const float z0 = c.fleet.stone(slot).position().z;
    for (int i = 0; i < 120; ++i) c.frame(1.0f / 60.0f);
    // The Stone kept travelling without its shooter and pressed the Pikmin,
    // attributed to no one (owner 0).
    assert(c.log.strikesOn(1) == 1 && c.log.firstOn(1)->s.owner == 0);
    assert(!c.fleet.used(slot) || c.fleet.stone(slot).position().z > z0 + 100.0f);
    assert(c.births.size() == 1); // a dead shooter never fires again
}

void case17_teardownReentry()
{
    Campaign c;
    c.targets = { piki(1, 0.0f, 400.0f) };
    while (c.births.empty()) c.frame(1.0f / 30.0f);
    const std::uint32_t firstId = c.births[0].step.id;
    for (int i = 0; i < 5; ++i) c.frame(1.0f / 30.0f);
    assert(c.fleet.active() == 1);
    // pc_p2_kabuto_fsm_reset: fleet.reset(); stoneDebt = 0.
    c.fleet.reset();
    c.debt = 0.0;
    const size_t strikes = c.log.strikes.size(), deads = c.log.deads.size();
    for (int i = 0; i < 300; ++i) c.frame(1.0f / 30.0f);
    assert(c.fleet.active() == 0);
    assert(c.log.strikes.size() == strikes && c.log.deads.size() == deads);
    // Re-entry: a fresh attack state fires again with a larger id.
    c.enterAttack();
    while (c.births.size() < 2) c.frame(1.0f / 30.0f);
    assert(c.births[1].step.id > firstId);
    assert(c.births[1].stateTime >= key2Seconds() - kKey2Epsilon);
}

void case18_stoneClock()
{
    double debt = 0.0;
    int total = 0;
    for (int i = 0; i < 30; ++i) {
        const int t = stoneTicksFor(debt, 1.0f / 30.0f);
        assert(t == 0 || t == 1);
        total += t;
    }
    assert(total >= 29 && total <= 30);
    debt = 0.0;
    total = 0;
    for (int i = 0; i < 60; ++i) total += stoneTicksFor(debt, 1.0f / 60.0f);
    assert(total >= 29 && total <= 30);
    debt = 0.0;
    assert(stoneTicksFor(debt, 0.5f) == kMaxStoneTicksPerFrame && debt == 0.0);
    assert(stoneTicksFor(debt, 0.0f) == 0 && stoneTicksFor(debt, -1.0f) == 0 && debt == 0.0);
}

void case19_oncePerAttackState()
{
    Campaign c;
    for (int f = 0; f < 90; ++f) c.frame(1.0f / 30.0f); // 3 s in one attack state
    assert(c.births.size() == 1);
    c.enterAttack();
    for (int f = 0; f < 90; ++f) c.frame(1.0f / 30.0f);
    assert(c.births.size() == 2);
    // Exhaustion is tolerated, not fatal (Kabuto.cpp:283).
    Fleet full;
    std::uint32_t id = 0;
    for (int i = 0; i < Fleet::capacity(); ++i) assert(fireForward(full, id, kPi) >= 0);
    bool done = false;
    const AttackStep st =
        attackStep(full, kShooter, 850.0f, done, key2Seconds() - 0.01f, key2Seconds() + 0.01f, { 0.0f, 0.0f, 0.0f }, 0.0f);
    assert(st.action == AttackAction::PoolFull && st.slot == -1 && done);
    assert(full.active() == Fleet::capacity());
}

// Contact geometry (review round 2): the creature contact is the Rock/Stone
// enemycoll r27 leaf on rock_body (y 25 x scale), not the r40 broadphase root
// centred one radius up (the round-1 host: r = 40 x scale at base + r).
bool legacyRootSphereTouches(const P2CannonStoneVec3& base, float scale, const Target& t)
{
    const float r = 40.0f * scale;
    const float dx = t.centre.x - base.x, dy = t.centre.y - (base.y + r), dz = t.centre.z - base.z;
    return std::sqrt(dx * dx + dy * dy + dz * dz) - r - t.radius <= 0.0f;
}

void case20_leafContactGeometry()
{
    // Behaviour first (so a geometry revert fails here, not on a constant).
    // Horizontal reach against a grounded Pikmin (centre y 10, r 10):
    // source sqrt(37^2 - 15^2) = 33.82, round-1 root sphere sqrt(50^2 - 30^2) = 40.
    const float reach = std::sqrt(37.0f * 37.0f - 15.0f * 15.0f);
    assert(std::fabs(reach - 33.823f) < 1e-2f);
    std::uint32_t id = 0;
    const float pathX = kMouthLocalX; // heading 0: the Stone runs along x = -0.025
    struct Lane { float lateral; bool struck; };
    const Lane lanes[] = { { 30.0f, true }, { 33.0f, true }, { 35.0f, false }, { 37.0f, false },
                           { 39.0f, false } };
    for (const Lane& lane : lanes) {
        Fleet fleet;
        FlatMap map;
        fireForward(fleet, id);
        std::vector<Target> targets{ piki(1, pathX + lane.lateral, 200.0f) };
        Log log;
        run(fleet, map, targets, 120, log);
        std::printf("case20 lateral=%.1f strikes=%d (source %s, round-1 root sphere %s)\n", lane.lateral,
                    log.strikesOn(1), lane.struck ? "hit" : "miss",
                    legacyRootSphereTouches({ pathX, 0.0f, 200.0f }, 1.0f, targets[0]) ? "hit" : "miss");
        assert(log.strikesOn(1) == (lane.struck ? 1 : 0));
        // Negative control: the round-1 r40 root sphere, grounded and level
        // with the Pikmin, strikes every lane here, including the three the
        // source r27 leaf misses.
        assert(legacyRootSphereTouches({ pathX, 0.0f, 200.0f }, 1.0f, targets[0]));
    }

    // Retail enemycoll: root r40 (bound only), leaf r27, both on joint 6.
    assert(kBoundRadiusFull == 40.0f && kContactRadiusFull == 27.0f);
    assert(kContactCentreYFull == 25.0f);
    const ContactSphere full = contactSphere({ 3.0f, 7.0f, -2.0f }, 1.0f);
    assert(full.radius == 27.0f && full.centre.x == 3.0f && full.centre.y == 32.0f &&
           full.centre.z == -2.0f);
    // CollPart::setScale scales the radius; the joint height scales with the
    // model matrix.
    const ContactSphere half = contactSphere({ 0.0f, 0.0f, 0.0f }, 0.5f);
    assert(half.radius == 13.5f && half.centre.y == 12.5f);
}


// ---- Round 4: source attack selection (isAttackableTarget lane) ----
// p2kabutoaim is what the shipped KB_WAIT / KB_TURN / KB_MOVE call
// (pc_p2_kabuto_fsm.cpp); the legacy gate below is the pre-round-4 native
// rule, kept only as a negative control.
namespace aim = p2kabutoaim;

aim::Vec3 v3(float x, float y, float z)
{
    aim::Vec3 v;
    v.x = x;
    v.y = y;
    v.z = z;
    return v;
}

aim::Candidate pikiAt(float x, float y, float z)
{
    aim::Candidate c;
    c.pos = v3(x, y, z);
    c.navi = false;
    c.alive = true;
    return c;
}

// Old pc_p2_kabuto_fsm.cpp:136-141 attackable(): XZ distance < attackRange
// (180) and |angle| < ATTACK_ANGLE (0.5 rad).
bool legacyAttackable(const aim::Vec3& pos, float heading, const aim::Vec3& t)
{
    const float dx = t.x - pos.x, dz = t.z - pos.z;
    if (std::sqrt(dx * dx + dz * dz) >= 180.0f) {
        return false;
    }
    return std::fabs(aim::wrapPi(std::atan2(dx, dz) - heading)) < 0.5f;
}

// Old KB_WAIT / KB_TURN selection (pc_p2_kabuto_fsm.cpp:262-287 at f06fb9cc7):
// Wait attacks on the legacy gate at clip end or turns when more than
// FACE_OK_ANGLE (10 deg) off; Turn turns at 2.5 rad/s, attacks on the legacy
// gate, and drops back to Wait once within 10 deg. Returns the host frame of
// the first Attack entry or -1, and the heading at that moment.
int legacyFirstAttackFrame(float heading, const aim::Vec3& t, int frames, float dt, float& outHeading)
{
    const aim::Vec3 pos = v3(0.0f, 0.0f, 0.0f);
    bool turning = false;
    float stateTime = 0.0f;
    const float waitClip = 1.0f;
    for (int f = 1; f <= frames; ++f) {
        stateTime += dt;
        const float ang = aim::wrapPi(std::atan2(t.x - pos.x, t.z - pos.z) - heading);
        if (!turning) {
            if (stateTime >= waitClip) {
                stateTime = 0.0f;
                if (legacyAttackable(pos, heading, t)) {
                    outHeading = heading;
                    return f;
                }
                if (std::fabs(ang) > 0.174533f) {
                    turning = true;
                }
            }
        } else {
            float step = ang;
            const float cap = 2.5f * dt;
            if (step > cap) step = cap;
            if (step < -cap) step = -cap;
            heading = aim::wrapPi(heading + step);
            const float after = aim::wrapPi(std::atan2(t.x - pos.x, t.z - pos.z) - heading);
            if (legacyAttackable(pos, heading, t)) {
                outHeading = heading;
                return f;
            }
            if (std::fabs(after) <= 0.174533f) {
                turning = false;
                stateTime = 0.0f;
            }
        }
    }
    outHeading = heading;
    return -1;
}

// Fires one stone from a Kabuto at the origin facing `heading` and returns
// the strikes the fleet lands on a grounded Pikmin (centre y 10) at `t`.
int stoneStrikesFrom(float heading, const aim::Vec3& t)
{
    Fleet fleet;
    FlatMap map;
    std::uint32_t id = 0;
    assert(fireForward(fleet, id, heading) >= 0);
    std::vector<Target> targets{ piki(77, t.x, t.z) };
    Log log;
    run(fleet, map, targets, 200, log);
    return log.strikesOn(77);
}

// The shipped chain on a host clock for a Kabuto facing +z at the origin:
// KB_TURN (aim::turnExec) until Attack, then KB_ATTACK (attackStep, heading 0
// in Campaign::frame) to KEYEVENT_2, then the fleet. Only used with targets
// already dead ahead, so the attack heading stays 0.
struct AimRun {
    int attackFrame = -1;
    float attackHeading = 0.0f;
    int strikes = 0;
    int births = 0;
    bool attackedOutOfLane = false;
};
AimRun runAimAhead(const aim::Candidate& target, int frames, float dt)
{
    AimRun r;
    Campaign c;
    c.inAttack = false;
    c.targets = { piki(77, target.pos.x, target.pos.z) };
    const aim::Vec3 pos = v3(0.0f, 0.0f, 0.0f);
    const aim::Vec3 wander = v3(0.0f, 0.0f, -100.0f);
    float heading = 0.0f;
    for (int f = 1; f <= frames; ++f) {
        if (!c.inAttack && r.attackFrame < 0) {
            const aim::TurnResult t = aim::turnExec(pos, heading, dt, aim::viewAngleDeg(0.0f), &target, 1, wander);
            heading = t.faceDir;
            if (t.next == aim::Next::Attack) {
                if (!aim::inAttackLane(pos, heading, target.pos)) {
                    r.attackedOutOfLane = true;
                }
                r.attackFrame = f;
                r.attackHeading = heading;
                c.enterAttack();
            }
        }
        c.frame(dt);
    }
    assert(std::fabs(r.attackHeading) < 1e-6f);
    r.births = int(c.births.size());
    r.strikes = c.log.strikesOn(77);
    return r;
}

void case21_offAxisTurnsUntilLane()
{
    // Pikmin 150 away, 17 deg off the Kabuto's facing.
    const float off = 17.0f * kPi / 180.0f;
    const aim::Candidate t = pikiAt(150.0f * std::sin(off), 0.0f, 150.0f * std::cos(off));
    const aim::Vec3 pos = v3(0.0f, 0.0f, 0.0f);
    // Source lane refuses it at the current facing (lateral 43.9 > 15) ...
    assert(!aim::inAttackLane(pos, 0.0f, t.pos));
    assert(std::fabs(std::fabs(aim::laneCoords(pos, 0.0f, t.pos).lateral) - 43.86f) < 0.05f);
    // ... while the legacy gate accepts it and the Stone fired along that
    // facing misses (negative control: the defect the lane gate fixes).
    assert(legacyAttackable(pos, 0.0f, t.pos));
    float legacyHeading = 1.0f;
    assert(legacyFirstAttackFrame(0.0f, t.pos, 600, 1.0f / 60.0f, legacyHeading) > 0);
    assert(legacyHeading == 0.0f);
    const int legacyStrikes = stoneStrikesFrom(legacyHeading, t.pos);
    std::printf("case21 legacy: attack at heading 0, stone strikes=%d (miss)\n", legacyStrikes);
    assert(legacyStrikes == 0);

    // Shipped selection: Turn keeps turning (no Attack while out of lane),
    // enters Attack once the lane holds, and the Stone reaches the Pikmin.
    float heading = 0.0f;
    int frames = 0;
    const aim::Vec3 wander = v3(0.0f, 0.0f, -100.0f);
    for (; frames < 600; ++frames) {
        const aim::TurnResult r = aim::turnExec(pos, heading, 1.0f / 60.0f, aim::viewAngleDeg(0.0f), &t, 1, wander);
        assert(r.target == 0);
        heading = r.faceDir;
        if (r.next == aim::Next::Attack) {
            break;
        }
        assert(!aim::inAttackLane(pos, heading, t.pos));
    }
    assert(frames > 1 && frames < 600);
    const aim::LaneCoords lc = aim::laneCoords(pos, heading, t.pos);
    std::printf("case21 lane: attack after %d frames (%.2f s) face=%.2f deg lateral=%.2f forward=%.1f\n",
                frames + 1, (frames + 1) / 60.0f, heading * 180.0f / kPi, lc.lateral, lc.forward);
    assert(std::fabs(lc.lateral) < aim::kLaneHalfWidth && lc.forward > 15.0f);
    const int strikes = stoneStrikesFrom(heading, t.pos);
    std::printf("case21 lane: stone strikes=%d\n", strikes);
    assert(strikes == 1);
    // The old Turn's FACE_OK exit stalls on a target 10 deg off at 200
    // (lateral 34.7, beyond the old 180 range): it never attacks. The new
    // Turn keeps turning until the lane holds.
    const float ten = 10.0f * kPi / 180.0f;
    const aim::Candidate far = pikiAt(200.0f * std::sin(ten), 0.0f, 200.0f * std::cos(ten));
    heading = 0.0f;
    bool attacked = false;
    for (int f = 0; f < 600 && !attacked; ++f) {
        const aim::TurnResult r = aim::turnExec(pos, heading, 1.0f / 60.0f, aim::viewAngleDeg(0.0f), &far, 1, wander);
        heading = r.faceDir;
        attacked = r.next == aim::Next::Attack;
    }
    assert(attacked && aim::inAttackLane(pos, heading, far.pos));
    assert(stoneStrikesFrom(heading, far.pos) == 1);
    float lh = 0.0f;
    const int legacyFar = legacyFirstAttackFrame(0.0f, far.pos, 1800, 1.0f / 60.0f, lh);
    std::printf("case21 stall: legacy attack frame=%d over 30 s, lane attacked=%d\n", legacyFar, int(attacked));
    assert(legacyFar < 0);
}

void case22_inLaneBeyond180()
{
    const aim::Vec3 pos = v3(0.0f, 0.0f, 0.0f);
    const aim::Candidate t = pikiAt(0.0f, 0.0f, 250.0f);
    assert(aim::inAttackLane(pos, 0.0f, t.pos));
    assert(aim::isAttackableTarget(pos, 0.0f, &t, 1));
    // Legacy gate: 250 >= attackRange 180 -> never fired at, and the old
    // Wait/Turn selection never reaches Attack for it.
    assert(!legacyAttackable(pos, 0.0f, t.pos));
    float lh = 0.0f;
    const int legacy = legacyFirstAttackFrame(0.0f, t.pos, 1800, 1.0f / 60.0f, lh);
    // Shipped chain: Turn -> Attack on the first exec, Stone born at
    // KEYEVENT_2, strike after travel.
    const AimRun r = runAimAhead(t, 240, 1.0f / 60.0f);
    std::printf("case22 legacy attack frame=%d; lane attack frame=%d births=%d strikes=%d\n", legacy, r.attackFrame,
                r.births, r.strikes);
    assert(legacy < 0);
    assert(r.attackFrame == 1 && !r.attackedOutOfLane);
    assert(r.births == 1 && r.strikes == 1);
    // Lane bounds on forward distance: 340 in, 350 (sight, strict) out.
    assert(aim::inAttackLane(pos, 0.0f, v3(0.0f, 0.0f, 340.0f)));
    assert(!aim::inAttackLane(pos, 0.0f, v3(0.0f, 0.0f, 350.0f)));
}

void case23_laneRefusals()
{
    const aim::Vec3 pos = v3(5.0f, 20.0f, -7.0f);
    auto at = [&](float fwd, float lat, float dy) { return v3(pos.x + lat, pos.y + dy, pos.z + fwd); };
    // |dy| < fov (100): 99.9 in, 100 / -100 / 150 out.
    assert(aim::inAttackLane(pos, 0.0f, at(100.0f, 0.0f, 99.9f)));
    assert(!aim::inAttackLane(pos, 0.0f, at(100.0f, 0.0f, 100.0f)));
    assert(!aim::inAttackLane(pos, 0.0f, at(100.0f, 0.0f, -100.0f)));
    assert(!aim::inAttackLane(pos, 0.0f, at(100.0f, 0.0f, 150.0f)));
    // forward > 15: 15 and below out (including right on top / behind).
    assert(!aim::inAttackLane(pos, 0.0f, at(15.0f, 0.0f, 0.0f)));
    assert(!aim::inAttackLane(pos, 0.0f, at(5.0f, 0.0f, 0.0f)));
    assert(!aim::inAttackLane(pos, 0.0f, at(-100.0f, 0.0f, 0.0f)));
    assert(aim::inAttackLane(pos, 0.0f, at(15.5f, 0.0f, 0.0f)));
    // |lateral| < 15 (both sides).
    assert(aim::inAttackLane(pos, 0.0f, at(100.0f, 14.9f, 0.0f)));
    assert(aim::inAttackLane(pos, 0.0f, at(100.0f, -14.9f, 0.0f)));
    assert(!aim::inAttackLane(pos, 0.0f, at(100.0f, 15.0f, 0.0f)));
    assert(!aim::inAttackLane(pos, 0.0f, at(100.0f, -15.0f, 0.0f)));
    // Rotated facing: heading 90 deg looks down +x.
    assert(aim::inAttackLane(pos, kPi / 2.0f, v3(pos.x + 200.0f, pos.y, pos.z + 10.0f)));
    assert(!aim::inAttackLane(pos, kPi / 2.0f, v3(pos.x, pos.y, pos.z + 200.0f)));
    // Targets straight ahead but 120 above (|dy| >= fov) or 10 ahead
    // (forward <= 15) are searched (XZ sight) and turned toward, but never
    // attacked; the legacy gate (XZ only) attacks both at once.
    const aim::Candidate high = pikiAt(pos.x, pos.y + 120.0f, pos.z + 100.0f);
    const aim::Candidate close = pikiAt(pos.x, pos.y, pos.z + 10.0f);
    const aim::Vec3 wander = v3(0.0f, 0.0f, -100.0f);
    for (const aim::Candidate* c : { &high, &close }) {
        float heading = 0.0f;
        for (int f = 0; f < 300; ++f) {
            const aim::TurnResult r = aim::turnExec(pos, heading, 1.0f / 60.0f, aim::viewAngleDeg(0.0f), c, 1, wander);
            assert(r.target == 0 && r.next == aim::Next::Stay);
            heading = r.faceDir;
        }
        assert(legacyAttackable(pos, 0.0f, c->pos));
    }
    // A dead candidate never opens the lane.
    aim::Candidate dead = pikiAt(pos.x, pos.y, pos.z + 100.0f);
    dead.alive = false;
    assert(!aim::isAttackableTarget(pos, 0.0f, &dead, 1));
}

void case24_searchAndTurnRate()
{
    const aim::Vec3 pos = v3(0.0f, 0.0f, 0.0f);
    // View angle: 180 deg while alert (< fp29 15 s), fp13 90 deg after.
    assert(aim::viewAngleDeg(0.0f) == 180.0f && aim::viewAngleDeg(14.9f) == 180.0f);
    assert(aim::viewAngleDeg(15.0f) == 90.0f);
    const aim::Candidate behind = pikiAt(-50.0f, 0.0f, -100.0f); // ~153 deg off
    assert(aim::searchTarget(pos, 0.0f, 180.0f, &behind, 1) == 0);
    assert(aim::searchTarget(pos, 0.0f, 90.0f, &behind, 1) == -1);
    // Sight is XZ 350.
    const aim::Candidate farT = pikiAt(0.0f, 0.0f, 351.0f);
    assert(aim::searchTarget(pos, 0.0f, 180.0f, &farT, 1) == -1);
    // Nearest wins; a Pikmin beats a Navi only when strictly closer.
    aim::Candidate cs[3] = { pikiAt(0.0f, 0.0f, 200.0f), pikiAt(0.0f, 0.0f, 100.0f), pikiAt(0.0f, 0.0f, 100.0f) };
    cs[1].navi = true;
    assert(aim::searchTarget(pos, 0.0f, 180.0f, cs, 3) == 1);
    cs[2].pos.z = 99.0f;
    assert(aim::searchTarget(pos, 0.0f, 180.0f, cs, 3) == 2);
    // turnToTarget per 30 Hz exec: clamp(angle * 0.05, 5 deg).
    const aim::Vec3 right = v3(100.0f, 0.0f, 0.0f); // +90 deg
    const aim::TurnStep a = aim::turnToward(pos, 0.0f, right, 1.0f / 30.0f);
    assert(std::fabs(a.faceDir - 0.05f * kPi / 2.0f) < 1e-5f); // 4.5 deg < cap
    const aim::Vec3 back = v3(0.001f, 0.0f, -100.0f); // ~180 deg
    const aim::TurnStep b = aim::turnToward(pos, 0.0f, back, 1.0f / 30.0f);
    assert(std::fabs(b.faceDir - 5.0f * kPi / 180.0f) < 1e-5f); // capped at 5 deg
    // Host-rate independence: two 60 Hz frames ~ one 30 Hz exec.
    const aim::TurnStep h1 = aim::turnToward(pos, 0.0f, right, 1.0f / 60.0f);
    const aim::TurnStep h2 = aim::turnToward(pos, h1.faceDir, right, 1.0f / 60.0f);
    assert(std::fabs(h2.faceDir - a.faceDir) < 0.002f);
}

void case25_moveAndWander()
{
    const aim::Vec3 pos = v3(0.0f, 0.0f, 0.0f);
    const aim::Vec3 home = v3(0.0f, 0.0f, 0.0f);
    // Wander target within [home 30, territory 150] of home.
    for (int i = 0; i < 20; ++i) {
        const aim::Vec3 w = aim::wanderTarget(v3(10.0f, 0.0f, 3.0f), home, i / 20.0f, (19 - i) / 20.0f);
        const float r = std::sqrt(w.x * w.x + w.z * w.z);
        assert(r >= 30.0f - 1e-3f && r <= 150.0f + 1e-3f);
    }
    const aim::Vec3 wander = v3(0.0f, 0.0f, 100.0f);
    // No target: walk while facing within 30 deg, Turn beyond, Wait on
    // timeout (> 6 s) or arrival (< 25).
    aim::MoveResult m = aim::moveExec(pos, 0.0f, 1.0f / 60.0f, 90.0f, 0.0f, nullptr, 0, wander);
    assert(m.walk && m.next == aim::Next::Stay);
    m = aim::moveExec(pos, kPi / 2.0f, 1.0f / 60.0f, 90.0f, 0.0f, nullptr, 0, wander);
    assert(!m.walk && m.next == aim::Next::Turn);
    m = aim::moveExec(pos, 0.0f, 1.0f / 60.0f, 90.0f, 6.1f, nullptr, 0, wander);
    assert(m.next == aim::Next::Wait);
    m = aim::moveExec(v3(0.0f, 0.0f, 80.0f), 0.0f, 1.0f / 60.0f, 90.0f, 0.0f, nullptr, 0, wander);
    assert(m.next == aim::Next::Wait);
    // A searched target: Attack when already in lane, else Turn (source
    // Move never chases a target).
    const aim::Candidate inLane = pikiAt(0.0f, 0.0f, 200.0f);
    const aim::Candidate offLane = pikiAt(60.0f, 0.0f, 200.0f);
    assert(aim::moveExec(pos, 0.0f, 1.0f / 60.0f, 90.0f, 0.0f, &inLane, 1, wander).next == aim::Next::Attack);
    m = aim::moveExec(pos, 0.0f, 1.0f / 60.0f, 90.0f, 0.0f, &offLane, 1, wander);
    assert(m.next == aim::Next::Turn && !m.walk);
    // Turn with no target heads for the wander point and moves within 30 deg.
    aim::TurnResult t = aim::turnExec(pos, 0.0f, 1.0f / 60.0f, 90.0f, nullptr, 0, wander);
    assert(t.target < 0 && t.next == aim::Next::Move);
    t = aim::turnExec(pos, kPi, 1.0f / 60.0f, 90.0f, nullptr, 0, wander);
    assert(t.next == aim::Next::Stay);
    // Wait latches Turn on a target or after 3 s.
    assert(aim::waitWantsTurn(0.0f, true) && aim::waitWantsTurn(3.1f, false) && !aim::waitWantsTurn(2.9f, false));
}

void case26_strikeCapDefers()
{
    // Two grounded Pikmin reached on the same tick with a 1-strike buffer:
    // the second is not recorded as struck, and is struck on the next tick.
    Fleet fleet;
    FlatMap map;
    std::uint32_t id = 0;
    assert(fireForward(fleet, id) >= 0);
    std::vector<Target> targets{ piki(1, -5.0f, 150.0f), piki(2, 5.0f, 150.0f) };
    int per[3] = { 0, 0, 0 };
    int firstTick = -1, secondTick = -1;
    for (int tick = 1; tick <= 120; ++tick) {
        Strike s[1];
        DeadEvent d[16];
        Released r[16];
        int sn = 0, dn = 0, rn = 0;
        fleet.tick(kGravity, &flatTrace, &map, targets.data(), int(targets.size()), s, 1, sn, d, 16, dn, r, 16, rn);
        assert(sn <= 1);
        for (int k = 0; k < sn; ++k) {
            ++per[s[k].target];
            (firstTick < 0 ? firstTick : secondTick) = tick;
        }
    }
    std::printf("case26 strikes p1=%d p2=%d ticks=%d,%d deferred=%llu\n", per[1], per[2], firstTick, secondTick,
                static_cast<unsigned long long>(fleet.strikesDeferred()));
    assert(per[1] == 1 && per[2] == 1);
    assert(secondTick == firstTick + 1);
    assert(fleet.strikesDeferred() >= 1);
    // P2 gravity constant (aiConstants 560).
    assert(kStoneGravity == 560.0f);
}

// Round-4 buildAim offered every P1 Piki passing isAlive() (which only
// excludes Dying / Dead, piki.cpp:2546-2553) as both searchable and in-lane.
// Kept only as the negative control for case 27.
aim::Candidate legacyHostPiki(float x, float y, float z)
{
    aim::Candidate c = pikiAt(x, y, z);
    c.alive = true;
    c.searchable = true;
    return c;
}

// Runs KB_TURN (aim::turnExec) for up to `frames` 60 Hz frames from facing
// +z at the origin. Returns the Attack frame or -1 and the final heading.
int turnUntilAttack(const aim::Candidate* c, int n, int frames, float& heading)
{
    const aim::Vec3 pos = v3(0.0f, 0.0f, 0.0f);
    const aim::Vec3 wander = v3(0.0f, 0.0f, -100.0f);
    heading = 0.0f;
    for (int f = 1; f <= frames; ++f) {
        const aim::TurnResult r = aim::turnExec(pos, heading, 1.0f / 60.0f, aim::viewAngleDeg(0.0f), c, n, wander);
        heading = r.faceDir;
        if (r.next == aim::Next::Attack) {
            return f;
        }
    }
    return -1;
}

void case27_sproutsAndSwallowedPikmin()
{
    const aim::Vec3 pos = v3(0.0f, 0.0f, 0.0f);
    const aim::Vec3 ahead150 = v3(0.0f, 0.0f, 150.0f);
    // Host mapping: sprouts (P1 Grow / Bury / NukareWait) are P2
    // ItemPikihead, never a Piki target; swallowed Pikmin are in P2
    // PikiSwallowedState, whose dead() is true (PikiState.h:823), so P2
    // isAlive rejects them from search and lane alike; plucking
    // (Nukare / AutoNuki) stays an ordinary Piki.
    const aim::Candidate sprout = aim::pikminCandidate(ahead150, true, aim::PikminPhase::Sprout);
    const aim::Candidate mouth = aim::pikminCandidate(ahead150, true, aim::PikminPhase::Dead);
    const aim::Candidate active = aim::pikminCandidate(ahead150, true, aim::PikminPhase::Active);
    const aim::Candidate dying = aim::pikminCandidate(ahead150, false, aim::PikminPhase::Active);
    assert(!sprout.alive && !sprout.searchable && !sprout.navi);
    assert(!mouth.alive && !mouth.searchable);
    assert(active.alive && active.searchable);
    assert(!dying.alive && !dying.searchable);
    const aim::Candidate navi = aim::naviCandidate(ahead150, true);
    assert(navi.navi && navi.alive && navi.searchable);

    // (a) A sprout alone in the lane at 150: the round-4 host offer searched
    // it and fired at once, although the Stone contact snapshot never holds
    // a sprout (pc_p2_kabuto_fsm.cpp snapshotAdd: !isAtari || isBuried).
    const aim::Candidate legacySprout = legacyHostPiki(0.0f, 0.0f, 150.0f);
    float h = 0.0f;
    assert(aim::searchTarget(pos, 0.0f, 180.0f, &legacySprout, 1) == 0);
    assert(turnUntilAttack(&legacySprout, 1, 1, h) == 1);
    assert(aim::searchTarget(pos, 0.0f, 180.0f, &sprout, 1) == -1);
    assert(!aim::isAttackableTarget(pos, 0.0f, &sprout, 1));
    assert(turnUntilAttack(&sprout, 1, 600, h) < 0);
    const aim::Vec3 wander = v3(0.0f, 0.0f, 100.0f);
    assert(aim::moveExec(pos, 0.0f, 1.0f / 60.0f, 180.0f, 0.0f, &sprout, 1, wander).target < 0);
    assert(!aim::waitWantsTurn(0.0f, aim::searchTarget(pos, 0.0f, 180.0f, &sprout, 1) >= 0));

    // (b) Sprout 10 ahead (forward <= 15: never in the lane) plus a Navi 200
    // away 60 deg off. Round-4 offer: the sprout is the nearest searched
    // target, the Kabuto already faces it and the lane never holds -> stuck
    // in KB_TURN. Shipped: the sprout is ignored, the Kabuto turns to the
    // Navi until the lane holds, fires, and the Stone reaches it.
    const float sixty = 60.0f * kPi / 180.0f;
    const aim::Vec3 naviPos = v3(200.0f * std::sin(sixty), 0.0f, 200.0f * std::cos(sixty));
    const aim::Candidate legacyPair[2] = { legacyHostPiki(0.0f, 0.0f, 10.0f), aim::naviCandidate(naviPos, true) };
    const aim::Candidate pair[2] = { aim::pikminCandidate(v3(0.0f, 0.0f, 10.0f), true, aim::PikminPhase::Sprout),
                                     aim::naviCandidate(naviPos, true) };
    float legacyHeading = 0.0f;
    const int legacyFrame = turnUntilAttack(legacyPair, 2, 1800, legacyHeading);
    float heading = 0.0f;
    const int frame = turnUntilAttack(pair, 2, 1800, heading);
    std::printf("case27 sprout stall: round-4 attack frame=%d heading=%.2f deg; shipped attack frame=%d heading=%.2f deg\n",
                legacyFrame, legacyHeading * 180.0f / kPi, frame, heading * 180.0f / kPi);
    assert(legacyFrame < 0 && std::fabs(legacyHeading) < 1e-3f);
    assert(frame > 1 && aim::inAttackLane(pos, heading, naviPos));
    assert(aim::searchTarget(pos, heading, 180.0f, pair, 2) == 1);
    const int strikes = stoneStrikesFrom(heading, naviPos);
    std::printf("case27 sprout stall: shipped stone strikes on the Navi=%d\n", strikes);
    assert(strikes == 1);

    // (c) A swallowed Pikmin: never searched and never in the lane (source
    // isAttackableTarget tests creature->isAlive(), Kabuto.cpp:242, which is
    // false in PikiSwallowedState). Round 5 kept it in the lane.
    assert(aim::searchTarget(pos, 0.0f, 180.0f, &mouth, 1) == -1);
    assert(!aim::isAttackableTarget(pos, 0.0f, &mouth, 1));
    const aim::Candidate mouthOff = aim::pikminCandidate(v3(100.0f, 0.0f, 150.0f), true, aim::PikminPhase::Dead);
    assert(turnUntilAttack(&mouthOff, 1, 600, h) < 0);
    // (d) A Pikmin being plucked is an ordinary target.
    assert(aim::searchTarget(pos, 0.0f, 180.0f, &active, 1) == 0 && turnUntilAttack(&active, 1, 1, h) == 1);
}

// Round-5 host mapping for a P1 Pikmin in a P2 dead() state (Pressed,
// DenkiDying, Swallowed): Pressed / DenkiDying were Active (searched and in
// the lane), Swallowed was alive but not searched. Negative control only.
aim::Candidate round5HostPiki(const aim::Vec3& p, int p1State)
{
    aim::Candidate c = pikiAt(p.x, p.y, p.z);
    c.alive = true;
    c.searchable = p1State != 8; // PIKISTATE_Swallowed -> round-5 StuckToMouth
    return c;
}

void case28_p2DeadStatesAreNotTargets()
{
    // A Pikmin 100 dead ahead in a P2 dead() state (squashed by this Stone,
    // electrocuted, or held in another enemy's mouth) plus a live Navi 200
    // away at 40 deg. Source (P2 isAlive false, piki.cpp:319-327): the
    // Pikmin is neither searched nor in the lane, the Kabuto turns to the
    // Navi, fires once the lane holds, and the Stone reaches it. Round 5
    // attacked the flattened / swallowed Pikmin at once (heading 0), though
    // P1 isAtari excludes Pressed and Swallowed (piki.cpp:1586-1587) so the
    // Stone cannot hit it, and re-attacked it at every Attack end.
    const aim::Vec3 pos = v3(0.0f, 0.0f, 0.0f);
    const aim::Vec3 pikiPos = v3(0.0f, 0.0f, 100.0f);
    const float forty = 40.0f * kPi / 180.0f;
    const aim::Vec3 naviPos = v3(200.0f * std::sin(forty), 0.0f, 200.0f * std::cos(forty));
    const char* const names[3] = { "Pressed", "DenkiDying", "Swallowed" };
    const int p1States[3] = { 33, 35, 8 }; // include/PikiState.h:49,51,24
    for (int k = 0; k < 3; ++k) {
        const aim::Candidate dead = aim::pikminCandidate(pikiPos, true, aim::PikminPhase::Dead);
        assert(!dead.alive && !dead.searchable);
        const aim::Candidate shipped[2] = { dead, aim::naviCandidate(naviPos, true) };
        const aim::Candidate legacy[2] = { round5HostPiki(pikiPos, p1States[k]), aim::naviCandidate(naviPos, true) };
        float legacyHeading = 0.0f;
        const int legacyFrame = turnUntilAttack(legacy, 2, 1800, legacyHeading);
        float heading = 0.0f;
        const int frame = turnUntilAttack(shipped, 2, 1800, heading);
        const bool legacyLaneOnNavi = aim::inAttackLane(pos, legacyHeading, naviPos);
        const bool laneOnNavi = aim::inAttackLane(pos, heading, naviPos);
        std::printf("case28 %s: round-5 attack frame=%d heading=%.1f deg lane_on_navi=%d; shipped attack frame=%d heading=%.1f deg lane_on_navi=%d\n",
                    names[k], legacyFrame, legacyHeading * 180.0f / kPi, int(legacyLaneOnNavi), frame,
                    heading * 180.0f / kPi, int(laneOnNavi));
        // Round 5: fires at once at the dead Pikmin, not at the Navi.
        assert(legacyFrame == 1 && !legacyLaneOnNavi);
        // Shipped: the dead Pikmin is invisible; the Navi is searched,
        // turned to and attacked once the lane holds.
        assert(aim::searchTarget(pos, 0.0f, 180.0f, shipped, 2) == 1);
        assert(!aim::isAttackableTarget(pos, 0.0f, &dead, 1));
        assert(frame > 1 && laneOnNavi && aim::attackableIndex(pos, heading, shipped, 2) == 1);
        assert(stoneStrikesFrom(heading, naviPos) == 1);
    }
    // Alone in the lane, a P2-dead Pikmin never triggers an attack, and
    // Wait never latches Turn for it before the 3 s timer.
    const aim::Candidate dead = aim::pikminCandidate(pikiPos, true, aim::PikminPhase::Dead);
    float h = 0.0f;
    assert(turnUntilAttack(&dead, 1, 600, h) < 0);
    assert(!aim::waitWantsTurn(0.0f, aim::searchTarget(pos, 0.0f, 180.0f, &dead, 1) >= 0));
    assert(aim::moveExec(pos, 0.0f, 1.0f / 60.0f, 180.0f, 0.0f, &dead, 1, v3(0.0f, 0.0f, 50.0f)).next != aim::Next::Attack);
    // The host dead flag still wins for an Active phase (P1 Dying / Dead).
    assert(!aim::pikminCandidate(pikiPos, false, aim::PikminPhase::Active).alive);
}
} // namespace

int main(int argc, char** argv)
{
    // Optional single-case selection (used for mutation evidence): `test 4`.
    const int only = argc > 1 ? std::atoi(argv[1]) : 0;
    void (*const cases[])() = { case1_key2Timing, case2_birthAndConfig, case3_travelTime,
                                case4_stepOut, case5_noHoming, case6_row,
                                case7_tekiSingleImpact, case8_wall, case9_timeout,
                                case10_sourceGrace, case11_exhaustion, case12_forgetOwner,
                                case13_resetReentry, case14_hostClockEmissionAndFlight,
                                case15_killBeforeEvent, case16_stoneOutlivesShooter,
                                case17_teardownReentry, case18_stoneClock,
                                case19_oncePerAttackState, case20_leafContactGeometry,
                                case21_offAxisTurnsUntilLane, case22_inLaneBeyond180,
                                case23_laneRefusals, case24_searchAndTurnRate,
                                case25_moveAndWander, case26_strikeCapDefers,
                                case27_sproutsAndSwallowedPikmin, case28_p2DeadStatesAreNotTargets };
    const int count = int(sizeof(cases) / sizeof(cases[0]));
    for (int i = 0; i < count; ++i) {
        if (only == 0 || only == i + 1) {
            cases[i]();
            std::printf("case %d passed\n", i + 1);
        }
    }
    std::printf("p2_kabuto_stone_fleet_test: all checks passed\n");
    return 0;
}
