// Standalone engine-free fixture for the generation-keyed per-actor Kabuto
// binding table (pc_port/pc_p2_kabuto_binding.h/.cpp). It links only the pure
// attachment bank (header-only), the shared sampled clock, the event adapter,
// the moving-muzzle provider, the fire FSM and the Stone birth helper; no engine
// headers are used.
//
// Build (MinGW):
//   g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_kabuto_binding_test.cpp
//       pc_port/pc_p2_kabuto_binding.cpp pc_port/pc_p2_kabuto_events.cpp
//       pc_port/pc_p2_kabuto_muzzle.cpp pc_port/pc_p2_kabuto_cannon.cpp
//       pc_port/pc_p2_cannon_stone.cpp -o <private-output>/p2_kabuto_binding_test.exe

#include "pc_p2_kabuto_binding.h"

#include <cassert>
#include <cmath>
#include <cstdio>
#include <sstream>
#include <vector>

namespace {

bool near(float a, float b, float eps = 0.0001f) { return std::fabs(a - b) <= eps; }

// Joints root(-1), body(0), mouth "KuTi"(1). Surfaced `attack` duration 51 fires
// at frame 50 with the mouth moving to z=5; buried `k_attack` duration 56 fires
// at frame 55 (z=7). The mixed-case joint exercises the name fallback.
const char* kBank =
    "P2_ATTACHMENTS_1 3 2\n"
    "root -1\n"
    "body 0\n"
    "KuTi 1\n"
    "attack 51 2\n"
    "0 50\n"
    "0 0 0 0 0 0 1 1 1 1\n"
    "0 0 0 0 0 0 1 1 1 1\n"
    "0 0 0 0 0 0 1 1 1 1\n"
    "10 0 0 0 0 0 1 1 1 1\n"
    "0 0 0 0 0 0 1 1 1 1\n"
    "0 0 5 0 0 0 1 1 1 1\n"
    "k_attack 56 2\n"
    "0 55\n"
    "0 0 0 0 0 0 1 1 1 1\n"
    "0 0 0 0 0 0 1 1 1 1\n"
    "0 0 0 0 0 0 1 1 1 1\n"
    "10 0 0 0 0 0 1 1 1 1\n"
    "0 0 0 0 0 0 1 1 1 1\n"
    "0 0 7 0 0 0 1 1 1 1\n";

std::shared_ptr<const p2attach::Bank> readBank(const char* text)
{
    std::istringstream input(text);
    auto bank = p2attach::read(input);
    assert(bank && p2attach::checked(*bank));
    return bank;
}

P2KabutoHostState idleHost() { return P2KabutoHostState{ false, false, false, 0.0f, 10.0f }; }

void testBindAdvanceFiresExactlyOnce()
{
    auto bank = readBank(kBank);
    P2KabutoBindingTable table;
    const P2KabutoBindingToken token = table.bind(1001, P2KabutoSpecies::Kabuto, bank);
    assert(token != 0);
    assert(table.bound(token) && table.identity(token) == 1001);
    assert(table.size() == 1 && !table.full());
    assert(table.phase(token) == P2KabutoPhase::Wait);
    assert(table.mouthBinding(token) && table.mouthBinding(token)->fireFrame == 50);
    assert(table.beginAttack(token));
    assert(table.attackActive(token));

    const P2KabutoHostState host = idleHost();
    P2KabutoAdvanceOut out;
    // 50 frames crosses the authored KEYEVENT_2 at frame 50 and births the Stone.
    assert(table.advance(token, p2attach::Affine{}, 50.0, 1, 1.0f, host, out));
    assert(out.accepted && out.key2 && out.fired && out.events == 1);
    assert(out.birth.valid && !out.birth.homing);
    assert(near(out.birth.faceDir, 1.0f));
    // createStoneAttack mouth joint (10,0,5) + (0,25,0).
    assert(near(out.birth.mouthPosition.x, 10.0f));
    assert(near(out.birth.mouthPosition.y, 25.0f));
    assert(near(out.birth.mouthPosition.z, 5.0f));

    // No second birth while the motion stays at frame 50.
    P2KabutoAdvanceOut idle;
    assert(table.advance(token, p2attach::Affine{}, 0.0, 2, 1.0f, host, idle));
    assert(idle.accepted && idle.events == 0 && !idle.fired);

    // Reaching the one-shot boundary emits End and returns to Wait.
    P2KabutoAdvanceOut end;
    assert(table.advance(token, p2attach::Affine{}, 1.0, 3, 1.0f, host, end));
    assert(end.accepted && end.end && !end.fired);
    assert(!table.attackActive(token));
    assert(table.phase(token) == P2KabutoPhase::Wait);

    // Nothing lingers: a further tick emits nothing.
    P2KabutoAdvanceOut quiet;
    assert(table.advance(token, p2attach::Affine{}, 5.0, 4, 1.0f, host, quiet));
    assert(quiet.accepted && quiet.events == 0 && !quiet.fired);
}

void testBuriedFkabutoBindsAndFires()
{
    auto bank = readBank(kBank);
    P2KabutoBindingTable table;
    const P2KabutoBindingToken token = table.bind(2002, P2KabutoSpecies::Fkabuto, bank);
    assert(token != 0);
    assert(table.phase(token) == P2KabutoPhase::FixStay); // buried at spawn
    assert(table.beginAttack(token));
    assert(table.phase(token) == P2KabutoPhase::FixAttack);

    P2KabutoAdvanceOut out;
    assert(table.advance(token, p2attach::Affine{}, 55.0, 1, 0.0f, idleHost(), out));
    assert(out.accepted && out.key2 && out.fired);
    assert(out.birth.valid && !out.birth.homing);
    assert(near(out.birth.mouthPosition.x, 10.0f));
    assert(near(out.birth.mouthPosition.y, 25.0f));
    assert(near(out.birth.mouthPosition.z, 7.0f)); // buried K_attack mouth
}

void testRkabutoBirthIsHoming()
{
    auto bank = readBank(kBank);
    P2KabutoBindingTable table;
    const P2KabutoBindingToken token = table.bind(3003, P2KabutoSpecies::Rkabuto, bank);
    assert(token != 0 && table.beginAttack(token));
    P2KabutoAdvanceOut out;
    assert(table.advance(token, p2attach::Affine{}, 50.0, 1, 0.0f, idleHost(), out));
    assert(out.fired && out.birth.valid && out.birth.homing);
}

void testStaleAndRecycledTokenRejection()
{
    auto bank = readBank(kBank);
    P2KabutoBindingTable table;
    P2KabutoAdvanceOut out;
    const P2KabutoHostState host = idleHost();

    const P2KabutoBindingToken first = table.bind(1001, P2KabutoSpecies::Kabuto, bank);
    assert(first != 0 && table.release(first));
    assert(!table.bound(first));
    // A stale handle cannot advance, start, or read phase.
    assert(!table.advance(first, p2attach::Affine{}, 1.0, 1, 0.0f, host, out));
    assert(!table.beginAttack(first));
    assert(table.phase(first) == P2KabutoPhase::Inactive);
    assert(table.mouthBinding(first) == nullptr);

    // A recycled identity receives a new generation; the old handle stays dead.
    const P2KabutoBindingToken second = table.bind(1001, P2KabutoSpecies::Kabuto, bank);
    assert(second != 0 && second != first);
    assert(!table.advance(first, p2attach::Affine{}, 1.0, 1, 0.0f, host, out));
    assert(table.advance(second, p2attach::Affine{}, 1.0, 1, 0.0f, host, out));
    assert(out.accepted && out.events == 0);

    // Two live owners that share an identity value get distinct handles.
    const P2KabutoBindingToken third = table.bind(1001, P2KabutoSpecies::Kabuto, bank);
    assert(third != 0 && third != second && table.size() == 2);
}

void testCapacityOverflowFailsClosed()
{
    auto bank = readBank(kBank);
    P2KabutoBindingTable table;
    std::vector<P2KabutoBindingToken> tokens;
    for (std::size_t i = 0; i < table.kCapacity; ++i) {
        const P2KabutoBindingToken token =
            table.bind(1000 + i, P2KabutoSpecies::Kabuto, bank);
        assert(token != 0);
        tokens.push_back(token);
    }
    assert(table.full() && table.size() == table.kCapacity);
    // One past capacity is refused with no partial state.
    assert(table.bind(9999, P2KabutoSpecies::Kabuto, bank) == 0);
    assert(table.size() == table.kCapacity);

    // Releasing a slot admits exactly one new binding.
    assert(table.release(tokens.front()));
    assert(table.size() == table.kCapacity - 1);
    const P2KabutoBindingToken admitted = table.bind(9999, P2KabutoSpecies::Kabuto, bank);
    assert(admitted != 0 && table.full());
}

void testReleaseAndReset()
{
    auto bank = readBank(kBank);
    P2KabutoBindingTable table;
    const P2KabutoBindingToken a = table.bind(1, P2KabutoSpecies::Kabuto, bank);
    const P2KabutoBindingToken b = table.bind(2, P2KabutoSpecies::Rkabuto, bank);
    assert(a != 0 && b != 0 && table.size() == 2);

    assert(table.release(a));
    assert(!table.release(a)); // double release is refused
    assert(table.bound(b) && !table.bound(a));

    table.reset();
    assert(table.size() == 0 && !table.bound(b));
    P2KabutoAdvanceOut out;
    assert(!table.advance(b, p2attach::Affine{}, 1.0, 1, 0.0f, idleHost(), out));
}

void testInvalidBankAndTickFailClosed()
{
    P2KabutoBindingTable table;
    assert(table.bind(1, P2KabutoSpecies::Kabuto, nullptr) == 0);
    assert(table.bind(1, P2KabutoSpecies::Kabuto,
                      std::shared_ptr<const p2attach::Bank>{}) == 0);
    // A bank without the source mouth joint cannot bind.
    auto noJoint = readBank("P2_ATTACHMENTS_1 1 1\nroot -1\nattack 51 2\n0 50\n"
                            "0 0 0 0 0 0 1 1 1 1\n0 0 0 0 0 0 1 1 1 1\n");
    assert(table.bind(1, P2KabutoSpecies::Kabuto, noJoint) == 0);
    assert(table.size() == 0);

    auto bank = readBank(kBank);
    const P2KabutoBindingToken token = table.bind(7, P2KabutoSpecies::Kabuto, bank);
    assert(token != 0 && table.beginAttack(token));
    P2KabutoAdvanceOut out;
    // A negative delta is refused before any clock mutation.
    assert(!table.advance(token, p2attach::Affine{}, -1.0, 1, 0.0f, idleHost(), out));
    assert(table.advance(token, p2attach::Affine{}, 1.0, 5, 0.0f, idleHost(), out));
    // The per-handle source tick must not go backwards.
    assert(!table.advance(token, p2attach::Affine{}, 1.0, 4, 0.0f, idleHost(), out));
}

} // namespace

int main()
{
    testBindAdvanceFiresExactlyOnce();
    testBuriedFkabutoBindsAndFires();
    testRkabutoBirthIsHoming();
    testStaleAndRecycledTokenRejection();
    testCapacityOverflowFailsClosed();
    testReleaseAndReset();
    testInvalidBankAndTickFailClosed();
    std::puts("p2_kabuto_binding_test PASS");
    return 0;
}
