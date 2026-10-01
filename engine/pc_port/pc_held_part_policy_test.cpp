// Engine-free contract test for the generic held ship part (#901).
#include "pc_held_part_policy.h"

#include <cassert>
#include <cstdio>

int main()
{
    using p2heldpart::Drop;
    using p2heldpart::Funnel;
    using p2heldpart::funnelDrops;
    using p2heldpart::keepAtBirth;
    using p2heldpart::onDeath;
    using p2heldpart::spawnItemsRuns;

    // Birth guard, P2-bound holder.
    assert(keepAtBirth(true, false, true));
    assert(!keepAtBirth(true, true, true));   // collected / cached / on the ground
    assert(!keepAtBirth(false, false, true)); // not a part holder
    // P1 holder: vanilla, always holds.
    assert(keepAtBirth(true, false, false));
    assert(keepAtBirth(true, true, false));
    assert(!keepAtBirth(false, false, false));

    // Funnels: a P1 holder drops only through spawnItems (vanilla).
    assert(funnelDrops(Funnel::SpawnItems, false));
    assert(!funnelDrops(Funnel::DieSoon, false));
    assert(!funnelDrops(Funnel::Die, false));
    assert(funnelDrops(Funnel::SpawnItems, true));
    assert(funnelDrops(Funnel::DieSoon, true));
    assert(funnelDrops(Funnel::Die, true));

    // spawnItems: vanilla for P1 even when latched; latched for P2.
    assert(spawnItemsRuns(false, false));
    assert(spawnItemsRuns(true, false));
    assert(spawnItemsRuns(false, true));
    assert(!spawnItemsRuns(true, true));

    // Real death drops once.
    assert(onDeath(false, true, 0.0f, false) == Drop::Spawn);
    assert(onDeath(false, true, -3.0f, false) == Drop::Spawn);
    // Latch: spawnItems or an earlier funnel already dropped it.
    assert(onDeath(true, true, 0.0f, false) == Drop::None);
    // Escape / burrow / teardown: health left, no drop, part still held.
    assert(onDeath(false, true, 0.5f, false) == Drop::None);
    // Not a holder.
    assert(onDeath(false, false, 0.0f, false) == Drop::None);
    // Duplicate guard: the part already exists somewhere.
    assert(onDeath(false, true, 0.0f, true) == Drop::AlreadyExists);

    std::puts("pc_held_part_policy_test: ok");
    return 0;
}
