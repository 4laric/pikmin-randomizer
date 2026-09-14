#include "pc_p2_projectile_host.h"

#include <cassert>
#include <cmath>
#include <cstdint>
#include <limits>

namespace {
constexpr float kDelta = P2CannonStone::kSourceDelta;
constexpr float kPi = 3.14159265358979323846f;

P2CannonStoneConfig testConfig()
{
    P2CannonStoneConfig config;
    config.variant = P2CannonStoneVariant::Stone;
    config.moveSpeed = 250.0f;
    config.searchRumbleSpeed = 100.0f;
    config.turnSpeed = 1.0f;
    config.maxTurnAngle = 180.0f;
    config.attackDamage = 10.0f;
    config.sightRadius = 550.0f;
    config.collisionRadius = 40.0f;
    config.health = 99999.0f;
    return config;
}

bool near(float actual, float expected, float epsilon = 0.001f)
{
    return std::fabs(actual - expected) <= epsilon;
}

struct HostState {
    // Trace output controls.
    bool floor = false;
    bool wall = false;
    bool hasGroundY = true;
    float groundY = 0.0f;
    bool fail = false;
    bool nonFinitePosition = false;
    int traceCalls = 0;
    P2CannonStoneVec3 lastCenter{};
    P2CannonStoneVec3 lastVelocity{};
    float lastDelta = 0.0f;
    float lastRadius = 0.0f;

    // Token liveness table.
    std::uint64_t liveTokens[8] = {};
    int liveCount = 0;
    int tokenCalls = 0;
};

bool hostTrace(void* opaque, const P2CannonStoneVec3& center, const P2CannonStoneVec3& velocity,
               float delta, float radius, P2ProjectileHostTrace& result)
{
    HostState& state = *static_cast<HostState*>(opaque);
    ++state.traceCalls;
    state.lastCenter = center;
    state.lastVelocity = velocity;
    state.lastDelta = delta;
    state.lastRadius = radius;
    if (state.fail) {
        return false;
    }
    result.position = { center.x + velocity.x * delta, center.y + velocity.y * delta,
                        center.z + velocity.z * delta };
    if (state.nonFinitePosition) {
        result.position.x = std::numeric_limits<float>::quiet_NaN();
    }
    result.velocity = velocity;
    result.floor = state.floor;
    result.wall = state.wall;
    result.groundY = state.groundY;
    result.hasGroundY = state.hasGroundY;
    return true;
}

bool tokenLive(void* opaque, std::uint64_t token)
{
    HostState& state = *static_cast<HostState*>(opaque);
    ++state.tokenCalls;
    for (int i = 0; i < state.liveCount; ++i) {
        if (state.liveTokens[i] == token) {
            return true;
        }
    }
    return false;
}

P2CannonStone makeStone(float faceDir, bool homing, std::uint64_t source = 0,
                        std::uint64_t self = 222)
{
    P2CannonStone stone;
    stone.reset(testConfig());
    assert(stone.birth({ 0.0f, 50.0f, 0.0f }, faceDir, homing, source, self));
    return stone;
}

P2ProjectileHostAdapter makeAdapter(HostState& state)
{
    P2ProjectileHostAdapter adapter;
    adapter.reset(hostTrace, &state, tokenLive, &state);
    return adapter;
}

void testActiveNaviPrecedence()
{
    P2ProjectileHostCandidate candidates[1];
    candidates[0].position = { 5.0f, 0.0f, 5.0f };
    candidates[0].token = 5;
    candidates[0].alive = true;

    P2ProjectileHostCandidateSnapshot snapshot;
    snapshot.candidates = candidates;
    snapshot.candidateCount = 1;

    // With no active Navi the nearest candidate wins.
    P2CannonStoneTarget without = P2ProjectileHostAdapter::selectTarget({ 0, 0, 0 }, snapshot, 550.0f);
    assert(without.hasTarget && near(without.position.x, 5.0f));

    // The active Navi wins even when it is far outside sight and y range.
    snapshot.hasActiveNavi = true;
    snapshot.activeNaviPosition = { 9000.0f, 9000.0f, 9000.0f };
    snapshot.activeNaviToken = 1;
    P2CannonStoneTarget with =
        P2ProjectileHostAdapter::selectTarget({ 0, 0, 0 }, snapshot, 550.0f);
    assert(with.hasTarget && near(with.position.x, 9000.0f));

    // A non-finite active-Navi position falls through to the candidate list.
    snapshot.activeNaviPosition = { std::numeric_limits<float>::quiet_NaN(), 0.0f, 0.0f };
    P2CannonStoneTarget fallback =
        P2ProjectileHostAdapter::selectTarget({ 0, 0, 0 }, snapshot, 550.0f);
    assert(fallback.hasTarget && near(fallback.position.x, 5.0f));
}

void testNearestCandidateSelection()
{
    P2ProjectileHostCandidate candidates[4];
    candidates[0].position = { 100.0f, 0.0f, 0.0f }; // 100
    candidates[0].token = 1;
    candidates[0].alive = true;
    candidates[1].position = { 10.0f, 0.0f, 5.0f }; // ~11.2
    candidates[1].token = 2;
    candidates[1].alive = true;
    candidates[2].position = { 1.0f, 0.0f, 0.0f }; // dead: ignored
    candidates[2].token = 3;
    candidates[2].alive = false;
    candidates[3].position = { -20.0f, 0.0f, 0.0f }; // 20
    candidates[3].token = 4;
    candidates[3].alive = true;

    P2ProjectileHostCandidateSnapshot snapshot;
    snapshot.candidates = candidates;
    snapshot.candidateCount = 4;
    P2CannonStoneTarget target =
        P2ProjectileHostAdapter::selectTarget({ 0, 0, 0 }, snapshot, 550.0f);
    assert(target.hasTarget && near(target.position.x, 10.0f) && near(target.position.z, 5.0f));

    // Equal 2D distance keeps the first live entry (deterministic tie-break).
    P2ProjectileHostCandidate tie[2];
    tie[0].position = { 10.0f, 0.0f, 0.0f };
    tie[0].token = 10;
    tie[0].alive = true;
    tie[1].position = { -10.0f, 0.0f, 0.0f };
    tie[1].token = 11;
    tie[1].alive = true;
    P2ProjectileHostCandidateSnapshot tieSnapshot;
    tieSnapshot.candidates = tie;
    tieSnapshot.candidateCount = 2;
    P2CannonStoneTarget tieTarget =
        P2ProjectileHostAdapter::selectTarget({ 0, 0, 0 }, tieSnapshot, 550.0f);
    assert(tieTarget.hasTarget && near(tieTarget.position.x, 10.0f));

    // An empty/null snapshot yields no target.
    P2ProjectileHostCandidateSnapshot empty;
    assert(!P2ProjectileHostAdapter::selectTarget({ 0, 0, 0 }, empty, 550.0f).hasTarget);
}

void testSightRadiusFiltering()
{
    P2ProjectileHostCandidate candidate;
    candidate.position = { 600.0f, 0.0f, 0.0f };
    candidate.token = 1;
    candidate.alive = true;
    P2ProjectileHostCandidateSnapshot snapshot;
    snapshot.candidates = &candidate;
    snapshot.candidateCount = 1;

    // Outside 550: filtered. At exactly 550: included (<= boundary).
    assert(!P2ProjectileHostAdapter::selectTarget({ 0, 0, 0 }, snapshot, 550.0f).hasTarget);
    candidate.position = { 550.0f, 0.0f, 0.0f };
    P2CannonStoneTarget edge =
        P2ProjectileHostAdapter::selectTarget({ 0, 0, 0 }, snapshot, 550.0f);
    assert(edge.hasTarget && near(edge.position.x, 550.0f));
    candidate.position = { 600.0f, 0.0f, 0.0f };

    // Negative sight radius means unlimited (getNearestPikminOrNavi semantics).
    assert(P2ProjectileHostAdapter::selectTarget({ 0, 0, 0 }, snapshot, -1.0f).hasTarget);
    // Non-finite sight radius yields no target.
    assert(!P2ProjectileHostAdapter::selectTarget(
                { 0, 0, 0 }, snapshot, std::numeric_limits<float>::quiet_NaN())
                .hasTarget);
}

void testNoYFilter()
{
    // The source call passes a 180-degree searchAngle (unrestricted), so
    // vertical separation never filters a candidate (Rock.cpp:376,
    // enemyAction.cpp:21,45). Only the 2D x/z distance ranks/filters.
    P2ProjectileHostCandidate candidates[2];
    candidates[0].position = { 0.0f, 5000.0f, 10.0f }; // far above, near in x/z
    candidates[0].token = 1;
    candidates[0].alive = true;
    candidates[1].position = { 0.0f, 0.0f, 100.0f }; // on plane, farther in x/z
    candidates[1].token = 2;
    candidates[1].alive = true;

    P2ProjectileHostCandidateSnapshot snapshot;
    snapshot.candidates = candidates;
    snapshot.candidateCount = 2;
    P2CannonStoneTarget target =
        P2ProjectileHostAdapter::selectTarget({ 0, 0, 0 }, snapshot, 550.0f);
    assert(target.hasTarget && near(target.position.y, 5000.0f));

    // Beyond the 2D radius, no target regardless of height.
    P2ProjectileHostCandidateSnapshot far;
    far.candidates = &candidates[1];
    far.candidateCount = 1;
    assert(!P2ProjectileHostAdapter::selectTarget({ 0, 0, 0 }, far, 50.0f).hasTarget);
    // The same candidate is included once the 2D radius covers it.
    assert(P2ProjectileHostAdapter::selectTarget({ 0, 0, 0 }, far, 150.0f).hasTarget);
}

void testNoTargetFallbackToHeading()
{
    HostState state;
    P2ProjectileHostAdapter adapter = makeAdapter(state);

    // Candidate-based selection yields nothing, so the policy must keep the
    // heading it was born with (Rock.cpp:382-384).
    P2CannonStone stone = makeStone(kPi / 2.0f, true);
    P2CannonStoneTarget noTarget =
        P2ProjectileHostAdapter::selectTarget({ 0, 50, 0 }, P2ProjectileHostCandidateSnapshot{},
                                              550.0f);
    assert(!noTarget.hasTarget);
    assert(stone.update(kDelta, noTarget, P2ProjectileHostAdapter::trace, &adapter));
    assert(near(stone.faceDir(), kPi / 2.0f));
    assert(near(stone.targetVelocity().x, 100.0f));
    assert(near(stone.targetVelocity().z, 0.0f, 0.5f));

    // Once turned by a real target, losing it keeps the new heading.
    P2CannonStone turning = makeStone(0.0f, true);
    P2CannonStoneTarget target;
    target.hasTarget = true;
    target.position = { 100.0f, 50.0f, 0.0f };
    assert(turning.update(kDelta, target, P2ProjectileHostAdapter::trace, &adapter));
    const float turned = turning.faceDir();
    assert(turned > 0.0f);
    assert(turning.update(kDelta, P2CannonStoneTarget{}, P2ProjectileHostAdapter::trace, &adapter));
    assert(near(turning.faceDir(), turned));
}

void testTraceMapping()
{
    HostState state;
    P2ProjectileHostAdapter adapter = makeAdapter(state);
    P2CannonStoneVec3 center{ 1.0f, 50.0f, -2.0f };
    P2CannonStoneVec3 velocity{ 10.0f, -30.0f, 4.0f };
    P2CannonStoneTraceResult result;

    // Clean flight: center and radius pass through unchanged, position and
    // velocity are the trace-mutated center-space values, wall=false.
    assert(P2ProjectileHostAdapter::trace(&adapter, center, velocity, kDelta, 40.0f, result));
    assert(near(state.lastCenter.x, 1.0f) && near(state.lastCenter.y, 50.0f)
           && near(state.lastCenter.z, -2.0f));
    assert(near(state.lastRadius, 40.0f) && near(state.lastDelta, kDelta));
    assert(near(result.position.x, 1.0f + 10.0f * kDelta));
    assert(near(result.position.y, 50.0f - 30.0f * kDelta));
    assert(near(result.velocity.y, -30.0f));
    assert(!result.wall);

    // Wall contact maps to P2CannonStoneTraceResult::wall (wallCallback),
    // which interrupts Move into Dead.
    state.wall = true;
    assert(P2ProjectileHostAdapter::trace(&adapter, center, velocity, kDelta, 40.0f, result));
    assert(result.wall);
    P2CannonStone stone = makeStone(0.0f, false);
    assert(stone.update(kDelta, P2CannonStoneTarget{}, P2ProjectileHostAdapter::trace, &adapter));
    assert(stone.phase() == P2CannonStonePhase::Dead);

    // Floor contact with groundY is a valid trace but does not set `wall`.
    state.wall = false;
    state.floor = true;
    state.groundY = 5.0f;
    state.hasGroundY = true;
    assert(P2ProjectileHostAdapter::trace(&adapter, center, velocity, kDelta, 40.0f, result));
    assert(!result.wall);
    P2CannonStone floating = makeStone(0.0f, false);
    assert(floating.update(kDelta, P2CannonStoneTarget{}, P2ProjectileHostAdapter::trace, &adapter));
    assert(floating.phase() == P2CannonStonePhase::Move);

    // A contact without a terrain sample fails the trace; the policy then
    // integrates directly and stays in Move.
    state.hasGroundY = false;
    P2CannonStoneTraceResult untouched;
    assert(!P2ProjectileHostAdapter::trace(&adapter, center, velocity, kDelta, 40.0f, untouched));
    P2CannonStone falling = makeStone(0.0f, false);
    assert(falling.update(kDelta, P2CannonStoneTarget{}, P2ProjectileHostAdapter::trace, &adapter));
    assert(falling.phase() == P2CannonStonePhase::Move);

    // Host trace failure returns false with no partial result.
    state.fail = true;
    assert(!P2ProjectileHostAdapter::trace(&adapter, center, velocity, kDelta, 40.0f, untouched));
    state.fail = false;

    // Non-finite trace output is rejected.
    state.nonFinitePosition = true;
    assert(!P2ProjectileHostAdapter::trace(&adapter, center, velocity, kDelta, 40.0f, untouched));
    state.nonFinitePosition = false;
}

void testTraceValidationAndImmutability()
{
    HostState state;
    P2ProjectileHostAdapter adapter = makeAdapter(state);
    P2CannonStoneTraceResult result;
    result.position = { 7.0f, 7.0f, 7.0f };
    result.velocity = { 7.0f, 7.0f, 7.0f };
    result.wall = true;

    // Invalid delta, radius, center or velocity all reject without touching
    // the caller's result.
    const float nan = std::numeric_limits<float>::quiet_NaN();
    assert(!P2ProjectileHostAdapter::trace(&adapter, { 0, 50, 0 }, { 0, -30, 0 }, 1.0f / 60.0f,
                                           40.0f, result));
    assert(!P2ProjectileHostAdapter::trace(&adapter, { 0, 50, 0 }, { 0, -30, 0 }, kDelta, 0.0f,
                                           result));
    assert(!P2ProjectileHostAdapter::trace(&adapter, { 0, 50, 0 }, { 0, -30, 0 }, kDelta, -40.0f,
                                           result));
    assert(!P2ProjectileHostAdapter::trace(&adapter, { nan, 50, 0 }, { 0, -30, 0 }, kDelta, 40.0f,
                                           result));
    assert(!P2ProjectileHostAdapter::trace(&adapter, { 0, 50, 0 }, { 0, nan, 0 }, kDelta, 40.0f,
                                           result));
    assert(!P2ProjectileHostAdapter::trace(&adapter, { 200000, 50, 0 }, { 0, -30, 0 }, kDelta,
                                           40.0f, result));
    assert(!P2ProjectileHostAdapter::trace(&adapter, { 0, 50, 0 }, { 0, -30, 0 }, nan, 40.0f,
                                           result));
    assert(near(result.position.x, 7.0f) && near(result.velocity.y, 7.0f) && result.wall);

    // Unbound trace callback fails cleanly.
    P2ProjectileHostAdapter unbound;
    assert(!P2ProjectileHostAdapter::trace(&unbound, { 0, 50, 0 }, { 0, -30, 0 }, kDelta, 40.0f,
                                           result));

    // Invalid-delta stone step leaves the pure policy state untouched.
    P2CannonStone stone = makeStone(kPi / 4.0f, true);
    const float savedFace = stone.faceDir();
    const float savedTimer = stone.timer();
    const float savedX = stone.position().x;
    assert(!stone.update(nan, P2CannonStoneTarget{}, P2ProjectileHostAdapter::trace, &adapter));
    assert(!stone.update(1.0f / 60.0f, P2CannonStoneTarget{}, P2ProjectileHostAdapter::trace,
                         &adapter));
    assert(near(stone.faceDir(), savedFace) && near(stone.timer(), savedTimer)
           && near(stone.position().x, savedX));

    // Non-finite origin/candidate data in selection is ignored, not mutated
    // into a target.
    assert(!P2ProjectileHostAdapter::selectTarget({ nan, 0, 0 }, P2ProjectileHostCandidateSnapshot{},
                                                  550.0f)
                .hasTarget);
    P2ProjectileHostCandidate bad;
    bad.position = { nan, 0, 0 };
    bad.token = 1;
    bad.alive = true;
    P2ProjectileHostCandidate good;
    good.position = { 10.0f, 0.0f, 0.0f };
    good.token = 2;
    good.alive = true;
    P2ProjectileHostCandidate pair[2] = { bad, good };
    P2ProjectileHostCandidateSnapshot snapshot;
    snapshot.candidates = pair;
    snapshot.candidateCount = 2;
    P2CannonStoneTarget target =
        P2ProjectileHostAdapter::selectTarget({ 0, 0, 0 }, snapshot, 550.0f);
    assert(target.hasTarget && near(target.position.x, 10.0f));
}

void testTokenLiveness()
{
    HostState state;
    P2ProjectileHostAdapter adapter = makeAdapter(state);
    P2CannonStone stone = makeStone(0.0f, false, 111, 222);

    // Live target and live source: reachable, attributed to the source.
    state.liveTokens[0] = 111;
    state.liveTokens[1] = 900;
    state.liveCount = 2;
    P2ProjectileHostStrikeResult live =
        adapter.contact(stone, P2CannonStoneContactKind::NaviPiki, true, false, 900);
    assert(live.contact.strikeEmitted && live.targetLive && live.attributedLive);
    assert(!live.unreachable && live.attributionToken == 111);

    // Stale source token: attribution falls back to the Stone's self token.
    state.liveTokens[0] = 222;
    state.liveTokens[1] = 900;
    P2CannonStone stone2 = makeStone(0.0f, false, 111, 222);
    P2ProjectileHostStrikeResult staleSource =
        adapter.contact(stone2, P2CannonStoneContactKind::NaviPiki, true, false, 900);
    assert(staleSource.contact.strikeEmitted && staleSource.targetLive);
    assert(!staleSource.attributedLive && !staleSource.unreachable);
    assert(staleSource.attributionToken == 222);

    // Stale target token: strike is unreachable.
    state.liveTokens[0] = 111;
    state.liveCount = 1;
    P2CannonStone stone3 = makeStone(0.0f, false, 111, 222);
    P2ProjectileHostStrikeResult staleTarget =
        adapter.contact(stone3, P2CannonStoneContactKind::NaviPiki, true, false, 900);
    assert(staleTarget.contact.strikeEmitted && !staleTarget.targetLive);
    assert(staleTarget.attributedLive && staleTarget.unreachable);
    assert(staleTarget.attributionToken == 111);

    // Teki attack attributes to the Stone itself; token 0 is never live.
    state.liveTokens[0] = 222;
    state.liveCount = 1;
    P2CannonStone stone4 = makeStone(0.0f, false, 111, 222);
    P2ProjectileHostStrikeResult teki =
        adapter.contact(stone4, P2CannonStoneContactKind::Teki, true, false, 0);
    assert(teki.contact.strikeEmitted && teki.contact.strike.attributedToken == 222);
    assert(teki.attributedLive && teki.attributionToken == 222);
    assert(!adapter.tokenLive(0));

    // No callbacks bound: all tokens unconfirmed, strikes unreachable.
    P2ProjectileHostAdapter unbound;
    assert(!unbound.tokenLive(222));
    P2CannonStone stone5 = makeStone(0.0f, false, 111, 222);
    P2ProjectileHostStrikeResult none =
        unbound.contact(stone5, P2CannonStoneContactKind::NaviPiki, true, false, 900);
    assert(none.contact.strikeEmitted && !none.targetLive && none.unreachable);
    assert(none.attributionToken == 222);

    // Non-strike contacts (airborne Navi/Piki) report nothing.
    P2CannonStone stone6 = makeStone(0.0f, false, 111, 222);
    P2ProjectileHostStrikeResult noStrike =
        adapter.contact(stone6, P2CannonStoneContactKind::NaviPiki, false, false, 900);
    assert(!noStrike.contact.strikeEmitted && !noStrike.unreachable);
    assert(noStrike.attributionToken == 0);
}
} // namespace

int main()
{
    testActiveNaviPrecedence();
    testNearestCandidateSelection();
    testSightRadiusFiltering();
    testNoYFilter();
    testNoTargetFallbackToHeading();
    testTraceMapping();
    testTraceValidationAndImmutability();
    testTokenLiveness();
    return 0;
}
