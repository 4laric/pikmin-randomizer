#include "pc_p2_armor_receiver_policy.h"

#include <cstdio>

// Standalone accept/reject matrix for the Cloaking Burrow-nit (Armor, EnemyID
// 15) damage receiver. Source: Game/Entities/Armor.cpp Obj::damageCallBack
// (:117-128) / Obj::hipdropCallBack (:134-141) at research revision 632af937.
// Build: g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port
//            tools/p2_armor_receiver_policy_test.cpp -o armor_receiver_test

#undef assert
#define assert(condition) do { if (!(condition)) return __LINE__; } while (false)

using namespace p2armorreceiver;

int main()
{
    const std::uint32_t body = fourCC('b', 'o', 'd', 'y');
    const std::uint32_t cent = fourCC('c', 'e', 'n', 't');

    // Exact source predicate (used for damageCallBack and hipdropCallBack).
    assert(!sourceAccepts(false, false, 0));
    assert(!sourceAccepts(false, true, body));
    assert(sourceAccepts(false, true, DamagePartID));
    assert(sourceAccepts(true, false, 0));
    assert(sourceAccepts(true, true, body));
    assert(sourceAccepts(true, true, DamagePartID));

    Inputs in;

    // Non-bittered, no source part, no weakpoint -> reject.
    assert(decide(in) == Decision::Reject);

    // Non-bittered, unrelated part, no weakpoint -> reject.
    in = {};
    in.has_part = true;
    in.part_id = body;
    assert(decide(in) == Decision::Reject);

    // Non-bittered, source `dmg1` -> accept.
    in = {};
    in.has_part = true;
    in.part_id = DamagePartID;
    assert(decide(in) == Decision::AcceptDmg1);

    // Bittered with no part -> accept (source isEvent(0, EB_Bittered)).
    in = {};
    in.bittered = true;
    assert(decide(in) == Decision::AcceptBittered);

    // Bittered overrides a non-dmg1 part.
    in = {};
    in.bittered = true;
    in.has_part = true;
    in.part_id = body;
    assert(decide(in) == Decision::AcceptBittered);

    // Port weakpoint active: the substitute host part accepts; others reject.
    in = {};
    in.has_part = true;
    in.part_id = cent;
    in.weakpoint_active = true;
    in.weakpoint_id = cent;
    assert(decide(in) == Decision::AcceptWeakpoint);

    in = {};
    in.has_part = true;
    in.part_id = body;
    in.weakpoint_active = true;
    in.weakpoint_id = cent;
    assert(decide(in) == Decision::Reject);

    // Weakpoint requires an actual part (never an unconditional accept).
    in = {};
    in.weakpoint_active = true;
    in.weakpoint_id = cent;
    assert(decide(in) == Decision::Reject);

    // A null/zero weakpoint id changes nothing.
    in = {};
    in.has_part = true;
    in.part_id = 0;
    in.weakpoint_active = true;
    in.weakpoint_id = 0;
    assert(decide(in) == Decision::Reject);

    // The real `dmg1` still wins when the weakpoint is a substitute.
    in = {};
    in.has_part = true;
    in.part_id = DamagePartID;
    in.weakpoint_active = true;
    in.weakpoint_id = cent;
    assert(decide(in) == Decision::AcceptDmg1);

    // accept() mirrors the non-Reject decisions.
    in = {};
    assert(!accepts(in));
    in.bittered = true;
    assert(accepts(in));

    std::puts("p2_armor_receiver_policy_test PASS");
    return 0;
}
