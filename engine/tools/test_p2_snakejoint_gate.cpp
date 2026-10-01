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
#include "pc_p2_imomushi.h"
#include "pc_p2_umimushi.h"

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

// Round 2 (#871 inst2-worms): the P2 FSM drives every tick in bridge mode, so
// the P1 Chappy host strategy (BTeki::doAI) must not run for a registered
// actor of any worms family; unregistered actors are unaffected. The engine
// glue (pc_p2_*_suppress_ai) routes through these header-inline predicates,
// mirroring pc_p2_frog_suppress_ai.
void testWormsSuppressRegistered() {
    assert(pc_p2_snakejoint_suppressed(true));
    assert(pc_p2_imomushi_suppressed(true));
    assert(pc_p2_umimushi_suppressed(true));
    std::puts("CASE worms_suppress_registered PASS");
}

void testWormsSuppressUnregistered() {
    assert(!pc_p2_snakejoint_suppressed(false));
    assert(!pc_p2_imomushi_suppressed(false));
    assert(!pc_p2_umimushi_suppressed(false));
    std::puts("CASE worms_suppress_unregistered PASS");
}

}  // namespace

int main() {
    testBuriedSnakeRejects();
    testEmergedSnakeAdmits();
    testNonSnakeUnaffected();
    testWormsSuppressRegistered();
    testWormsSuppressUnregistered();
    std::puts("PASS p2_snakejoint_gate_test");
    return 0;
}
