// Engine-free contract for pc_p2_boss_arena_policy.h (P2 boss arenas).
#include "pc_p2_boss_arena_policy.h"
#include "pc_p2_campaign_policy.h"

#include <cassert>
#include <cstdio>

int main()
{
    // Hope snagret pit: the Snake mate is emptied by the BoxSnake spawn uid.
    assert(p2bossarena::suppressPrimary(2026735859u) == 295337326u);
    // A spawn uid is never itself suppressed; unknown uids are untouched.
    assert(p2bossarena::suppressPrimary(295337326u) == 0);
    assert(p2bossarena::suppressPrimary(0u) == 0);
    assert(p2bossarena::suppressPrimary(1945764764u) == 0);
    // Goolix day files re-key to the 8.gen primary; the primary is not an alias.
    assert(p2bossarena::aliasPrimary(131114894u) == 4019261003u);
    assert(p2bossarena::aliasPrimary(4019261003u) == 0);
    for (const auto& row : p2bossarena::kAlias) {
        assert(p2bossarena::isArenaUid(row.uid));
        assert(p2bossarena::isArenaUid(row.primary));
        assert(p2bossarena::aliasPrimary(row.primary) == 0);
    }
    // Every suppress row names two catalogued arena generators.
    for (const auto& row : p2bossarena::kSuppress) {
        assert(p2bossarena::isArenaUid(row.uid));
        assert(p2bossarena::isArenaUid(row.primary));
    }
    // Impact Goolix day files, protected holders and the Emperor are catalogued.
    assert(p2bossarena::isArenaUid(4019261003u));
    assert(p2bossarena::isArenaUid(131114894u));
    assert(p2bossarena::isArenaUid(304372265u));
    assert(p2bossarena::isArenaUid(3759070123u));
    // An ordinary campaign slot (bot start slot) is not an arena.
    assert(!p2bossarena::isArenaUid(1945764764u));
    // Vehicles: the admitted boss 94 keeps its Swallow host; an identity with
    // no static host falls back to TEKI_Swallow instead of the P1 boss id.
    assert(p2bossarena::hostFor(94, p2campaign::hostType) == 4);
    assert(p2bossarena::hostFor(66, p2campaign::hostType) == 4);
    assert(p2bossarena::hostFor(12345, p2campaign::hostType) == 4);
    std::puts("P2_BOSS_ARENA_POLICY_PASS");
    return 0;
}
