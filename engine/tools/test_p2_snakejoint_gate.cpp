// Focused gate fixture for the SnakeCrow/SnakeWhole emerged-vulnerability gate
// (rd-snakecrow-gate, #174): InteractAttack/InteractBomb consult
// pc_p2_snakejoint_invulnerable, which rejects damage only for a registered
// snagret buried in Stay (EB_Invulnerable set by StateStay::init, cleared by
// StateStay::cleanup) and admits it everywhere else.
//
// Engine-free: exercises the shared predicate pc_p2_snakejoint_attack_rejected
// compiled from the owned header pc_port/pc_p2_snakejoint.h -- the same
// predicate the engine-linked pc_p2_snakejoint_invulnerable routes through --
// mirroring P2DangoMushiHazardPolicy::attackRejected
// (tools/p2_dangomushi_hazard_test.cpp). No engine, GL or arena is required.
#include "pc_p2_snakejoint.h"

// Release builds pass -DNDEBUG; force assertions (and their embedded
// side effects) on so this engine-free gate is not vacuous under ctest.
#undef NDEBUG
#include <cassert>
#include <cstdio>

namespace {

// Case 1: buried_snake_rejects -- a registered snagret buried in Stay rejects
// damage, so both InteractAttack and InteractBomb swallow it (the hook returns
// true without reaching the host interact).
void testBuriedSnakeRejects() {
    // Attack path: registered + buried Stay => rejected (ignored).
    assert(pc_p2_snakejoint_attack_rejected(true, true));
    // Bomb path: the same shared gate guards InteractBomb => rejected too.
    assert(pc_p2_snakejoint_attack_rejected(true, true));
    std::puts("CASE buried_snake_rejects_attack_and_bomb PASS");
}

// Case 2: emerged_snake_admits -- every emerged state clears EB_Invulnerable
// (StateStay::cleanup), so a registered emerged snagret admits damage.
void testEmergedSnakeAdmits() {
    assert(!pc_p2_snakejoint_attack_rejected(true, false));
    std::puts("CASE emerged_snake_admits_damage PASS");
}

// Case 3: non_snake_unaffected -- unregistered actors (P1 controls and every
// other family) admit damage regardless of the buried flag, so the shared hook
// stays a no-op for them.
void testNonSnakeUnaffected() {
    assert(!pc_p2_snakejoint_attack_rejected(false, false));
    assert(!pc_p2_snakejoint_attack_rejected(false, true));
    std::puts("CASE non_snake_unaffected PASS");
}

}  // namespace

int main() {
    testBuriedSnakeRejects();
    testEmergedSnakeAdmits();
    testNonSnakeUnaffected();
    std::puts("PASS p2_snakejoint_gate_test");
    return 0;
}
