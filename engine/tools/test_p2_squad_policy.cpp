#include "pc_p2_captain_policy.h"
#include "pc_p2_squad_policy.h"

#include <cassert>
#include <cstdint>
#include <cstdio>
#include <vector>

// Lane 12 per-captain squad split + inactive-captain follow + dismiss/whistle
// priority test (#130). Engine-free: no Navi/Piki object is constructed. The
// same policy the live pc_p2_captain.cpp drives is exercised here.

namespace {

bool same(const std::vector<std::uint32_t>& a, const std::vector<std::uint32_t>& b)
{
    return a == b;
}

void test_follow_policy()
{
    P2SquadFollowPolicy follow;
    follow.reset();
    assert(follow.phase() == P2FollowPhase::Idle);

    // Band mapping mirrors NaviFollowState::exec thresholds.
    assert(follow.update(20.0f, true) == P2FollowPhase::Idle);
    assert(follow.update(29.9f, true) == P2FollowPhase::Idle);
    assert(follow.update(30.5f, true) == P2FollowPhase::Follow);
    assert(follow.update(60.0f, true) == P2FollowPhase::Follow);
    assert(follow.update(400.0f, true) == P2FollowPhase::Follow);
    assert(follow.update(431.0f, true) == P2FollowPhase::TooFar);

    // The idle counter only advances while the leader stands still, and clamps
    // at the source goof threshold.
    follow.reset();
    assert(follow.update(10.0f, false) == P2FollowPhase::Idle);
    assert(follow.idleFrames() == 1);
    assert(follow.update(10.0f, true) == P2FollowPhase::Idle);
    assert(follow.idleFrames() == 0); // leader moved: reset
    for (int i = 0; i < 200; ++i) follow.update(10.0f, false);
    assert(follow.idleFrames() == P2SquadFollowPolicy::kIdleGoofFrames);
    // Leaving the idle band clears the counter.
    assert(follow.update(200.0f, false) == P2FollowPhase::Follow);
    assert(follow.idleFrames() == 0);

    // Non-finite/negative distances are treated as zero, not UB.
    follow.reset();
    assert(follow.update(-5.0f, false) == P2FollowPhase::Idle);

    // Source speed curve: halted inside the stop radius, half speed inside the
    // blend band, full speed beyond it.
    assert(P2SquadFollowPolicy::followSpeed(20.0f, 170.0f) == 0.0f);
    assert(P2SquadFollowPolicy::followSpeed(45.0f, 170.0f) == 85.0f);
    assert(P2SquadFollowPolicy::followSpeed(100.0f, 170.0f) == 170.0f);
    assert(P2SquadFollowPolicy::followSpeed(100.0f, -1.0f) == 0.0f);
}

void test_whistle_and_dismiss()
{
    // A whistle claims free Pikmin and the whistler's own, never the other's.
    assert(p2_whistle_claim(P2CaptainA, P2CaptainInvalid) == P2WhistleClaim::Claim);
    assert(p2_whistle_claim(P2CaptainA, P2CaptainA) == P2WhistleClaim::Claim);
    assert(p2_whistle_claim(P2CaptainA, P2CaptainB) == P2WhistleClaim::Refuse);
    assert(p2_whistle_claim(P2CaptainB, P2CaptainA) == P2WhistleClaim::Refuse);
    assert(p2_whistle_claim(P2CaptainInvalid, P2CaptainInvalid) == P2WhistleClaim::Refuse);

    // Dismiss always releases the caller; the inactive follower is dismissed
    // only while it is following.
    P2DismissPlan standing = p2_dismiss_plan(false);
    assert(standing.releaseSelf && !standing.releaseInactive);
    P2DismissPlan following = p2_dismiss_plan(true);
    assert(following.releaseSelf && following.releaseInactive);
}

void test_squad_split()
{
    P2CaptainOwnershipTable table;
    P2CaptainPolicy policy;
    assert(policy.bind(&table));
    assert(policy.configure(P2CaptainA, 100.0f, true));
    assert(policy.configure(P2CaptainB, 100.0f, true));
    assert(policy.activeCaptain() == P2CaptainA);

    for (std::uint32_t id = 10; id < 15; ++id) {
        assert(policy.claim(P2CaptainA, id));
    }
    assert(table.ownedBy(P2CaptainA) == 5);

    // Claims out of order still split in ascending id order.
    assert(policy.claim(P2CaptainA, 3));
    assert(table.actorsOwnedBy(P2CaptainA) == std::vector<std::uint32_t>({3, 10, 11, 12, 13, 14}));

    std::vector<std::uint32_t> moved = policy.splitSquad(P2CaptainA, P2CaptainB, 2);
    assert(same(moved, {3, 10}));
    assert(table.ownerOf(3) == P2CaptainB && table.ownerOf(10) == P2CaptainB);
    assert(table.ownedBy(P2CaptainA) == 4 && table.ownedBy(P2CaptainB) == 2);
    // No actor is lost or duplicated by the split.
    assert(table.ownedCount() == 6);

    // Over-count clamps to what is owned; moving from A to A is refused.
    std::vector<std::uint32_t> rest = policy.splitSquad(P2CaptainA, P2CaptainB, 99);
    assert(rest.size() == 4);
    assert(table.ownedBy(P2CaptainA) == 0 && table.ownedBy(P2CaptainB) == 6);
    assert(policy.splitSquad(P2CaptainA, P2CaptainA, 1).empty());
    assert(policy.splitSquad(P2CaptainA, P2CaptainB, 1).empty()); // nothing left

    // Named transfer moves exactly the requested actors.
    std::size_t n = policy.transferSquad(P2CaptainB, P2CaptainA,
                                         std::vector<std::uint32_t>({3, 14, 999}).data(), 3);
    assert(n == 2);
    assert(table.ownerOf(3) == P2CaptainA && table.ownerOf(14) == P2CaptainA);
    assert(table.ownerOf(999) == P2CaptainInvalid);
    assert(table.ownedCount() == 6);

    // A Down or absent target cannot receive a split.
    P2CaptainOwnershipTable table2;
    P2CaptainPolicy policy2;
    assert(policy2.bind(&table2));
    assert(policy2.configure(P2CaptainA, 100.0f, true));
    assert(policy2.configure(P2CaptainB, 100.0f, false)); // absent
    assert(policy2.claim(P2CaptainA, 7));
    assert(policy2.splitSquad(P2CaptainA, P2CaptainB, 1).empty());
    assert(table2.ownerOf(7) == P2CaptainA);
}

} // namespace

int main()
{
    test_follow_policy();
    test_whistle_and_dismiss();
    test_squad_split();
    std::puts("PASS P2_SQUAD_POLICY");
    return 0;
}
