// Standalone engine-free fixture for the generated-session Cannon Beetle family
// host (pc_port/pc_p2_kabuto_host.h/.cpp). It links only the pure attachment bank
// (header-only), the shared sampled clock, the event adapter, the moving-muzzle
// provider, the fire FSM, the Stone birth helper and the per-actor binding table;
// no engine headers are used.
//
// Build (MinGW):
//   g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_kabuto_host_test.cpp
//       pc_port/pc_p2_kabuto_host.cpp pc_port/pc_p2_kabuto_binding.cpp
//       pc_port/pc_p2_kabuto_events.cpp pc_port/pc_p2_kabuto_muzzle.cpp
//       pc_port/pc_p2_kabuto_cannon.cpp pc_port/pc_p2_cannon_stone.cpp
//       -o <private-output>/p2_kabuto_host_test.exe

#include "pc_p2_kabuto_host.h"

#include <cassert>
#include <cmath>
#include <cstdio>
#include <sstream>
#include <vector>

namespace {

bool near(float a, float b, float eps = 0.0001f) { return std::fabs(a - b) <= eps; }

// Joints root(-1), body(0), mouth "KuTi"(1). Surfaced `attack` duration 51 fires
// at frame 50 with the hierarchical root+KuTi mouth at world (10, 0, 5); buried
// `k_attack` duration 56 fires at frame 55 (world z=7). Mixed-case joint exercises
// the case-insensitive fallback.
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

P2KabutoHostAnimator idleAnimator()
{
    P2KabutoHostAnimator animator;
    animator.motion = 2; // Wait1
    animator.frameCount = 20;
    animator.counter = 0.0;
    animator.attackMotion = false;
    return animator;
}

P2KabutoHostAnimator attackAnimator(double counter, long frameCount)
{
    P2KabutoHostAnimator animator;
    animator.motion = 8; // TekiMotion::Attack
    animator.frameCount = frameCount;
    animator.counter = counter;
    animator.attackMotion = true;
    return animator;
}

void testSpeciesMapping()
{
    P2KabutoSpecies species = P2KabutoSpecies::Kabuto;
    assert(P2KabutoHost::species_for_source(75, species) && species == P2KabutoSpecies::Kabuto);
    assert(P2KabutoHost::species_for_source(95, species) && species == P2KabutoSpecies::Rkabuto);
    assert(P2KabutoHost::species_for_source(96, species) && species == P2KabutoSpecies::Fkabuto);
    assert(!P2KabutoHost::species_for_source(0, species));
    assert(!P2KabutoHost::species_for_source(45, species)); // Snow is a different family
    assert(!P2KabutoHost::species_for_source(94, species));
}

void testFeedContract()
{
    // A single-frame motion cannot be phased for an attack.
    assert(!P2KabutoHost::feed(idleAnimator(), attackAnimator(0.0, 1), 51).valid);

    // Entering attack begins the clock at the current phase.
    const P2KabutoHostFeed begin = P2KabutoHost::feed(idleAnimator(), attackAnimator(0.0, 51), 51);
    assert(begin.valid && begin.begin && !begin.restart && !begin.leave);
    assert(near(float(begin.sourceFrameDelta), 0.0f));

    // Forward progress scales the live phase to the authored source span.
    const P2KabutoHostFeed step = P2KabutoHost::feed(attackAnimator(10.0, 51), attackAnimator(11.0, 51), 51);
    assert(step.valid && !step.begin && !step.restart && !step.leave);
    assert(step.sourceFrameDelta > 0.0 && step.sourceFrameDelta <= 51.0);

    // A wrapped counter restarts the source clock at the new phase.
    const P2KabutoHostFeed restart = P2KabutoHost::feed(attackAnimator(40.0, 51), attackAnimator(3.0, 51), 51);
    assert(restart.valid && restart.restart && !restart.begin);

    // Leaving attack drops any unfinished clock.
    const P2KabutoHostFeed leave = P2KabutoHost::feed(attackAnimator(40.0, 51), idleAnimator(), 51);
    assert(leave.valid && leave.leave);

    // Invalid readings fail closed.
    P2KabutoHostAnimator bad = attackAnimator(-1.0, 51);
    assert(!P2KabutoHost::feed(attackAnimator(0.0, 51), bad, 51).valid);
    bad = attackAnimator(0.0, 51);
    bad.counter = std::nan("");
    assert(!P2KabutoHost::feed(attackAnimator(0.0, 51), bad, 51).valid);
    assert(!P2KabutoHost::feed(idleAnimator(), attackAnimator(0.0, 51), 0).valid);
}

// Drive one full live attack motion from counter 0..frameCount-1, counting fires.
int driveAttack(P2KabutoHost& host, std::uint64_t identity, long frameCount, float faceDir)
{
    int fires = 0;
    for (long counter = 0; counter < frameCount; ++counter) {
        P2KabutoAdvanceOut out;
        const bool accepted = host.advance(identity, attackAnimator(double(counter), frameCount),
                                           p2attach::Affine{}, faceDir, idleHost(), out);
        assert(accepted);
        if (out.fired) {
            ++fires;
            assert(out.birth.valid);
            assert(near(out.birth.mouthPosition.x, 10.0f));
            assert(near(out.birth.mouthPosition.y, 25.0f));
            assert(near(out.birth.mouthPosition.z, 5.0f));
        }
    }
    return fires;
}

void testLiveAnimatorFiresOnce()
{
    auto bank = readBank(kBank);
    P2KabutoHost host;
    const P2KabutoBindingToken token = host.bind(1001, P2KabutoSpecies::Kabuto, bank);
    assert(token != 0 && host.bound(1001) && host.token(1001) == token);
    assert(host.species(1001) == P2KabutoSpecies::Kabuto);
    assert(host.phase(1001) == P2KabutoPhase::Wait);
    assert(host.size() == 1);

    // An idle reading is accepted but produces nothing.
    P2KabutoAdvanceOut idle;
    assert(host.advance(1001, idleAnimator(), p2attach::Affine{}, 0.0f, idleHost(), idle));
    assert(idle.accepted && idle.events == 0 && !idle.fired);

    // The live attack motion starts the source clock and fires exactly once.
    assert(driveAttack(host, 1001, 51, 1.0f) == 1);

    // Leaving attack clears the unfinished/reset state; a second attack fires again.
    P2KabutoAdvanceOut leave;
    assert(host.advance(1001, idleAnimator(), p2attach::Affine{}, 0.0f, idleHost(), leave));
    assert(leave.accepted && !leave.fired);
    assert(driveAttack(host, 1001, 51, 1.0f) == 1);
}

void testRkabutoAndFkabuto()
{
    auto bank = readBank(kBank);
    P2KabutoHost host;
    assert(host.bind(2002, P2KabutoSpecies::Rkabuto, bank) != 0);
    // Rkabuto births a homing Stone.
    int homing = 0;
    for (long counter = 0; counter < 51; ++counter) {
        P2KabutoAdvanceOut out;
        assert(host.advance(2002, attackAnimator(double(counter), 51), p2attach::Affine{}, 0.0f,
                            idleHost(), out));
        if (out.fired) {
            ++homing;
            assert(out.birth.homing);
        }
    }
    assert(homing == 1);

    // Fkabuto binds buried (FixStay) and fires from the buried k_attack clip.
    assert(host.bind(3003, P2KabutoSpecies::Fkabuto, bank) != 0);
    assert(host.phase(3003) == P2KabutoPhase::FixStay);
    int buried = 0;
    for (long counter = 0; counter < 56; ++counter) {
        P2KabutoAdvanceOut out;
        assert(host.advance(3003, attackAnimator(double(counter), 56), p2attach::Affine{}, 0.0f,
                            idleHost(), out));
        if (out.fired) {
            ++buried;
            assert(near(out.birth.mouthPosition.z, 7.0f));
            assert(!out.birth.homing);
        }
    }
    assert(buried == 1);
}

void testRestartRefires()
{
    auto bank = readBank(kBank);
    P2KabutoHost host;
    assert(host.bind(4004, P2KabutoSpecies::Kabuto, bank) != 0);

    int fires = 0;
    for (long counter = 0; counter < 20; ++counter) {
        P2KabutoAdvanceOut out;
        assert(host.advance(4004, attackAnimator(double(counter), 51), p2attach::Affine{}, 0.0f,
                            idleHost(), out));
        fires += out.fired;
    }
    // Wrap the live counter back to the start; the source clock restarts.
    for (long counter = 0; counter < 51; ++counter) {
        P2KabutoAdvanceOut out;
        assert(host.advance(4004, attackAnimator(double(counter), 51), p2attach::Affine{}, 0.0f,
                            idleHost(), out));
        fires += out.fired;
    }
    assert(fires == 1);
}

void testInvalidAndCapacityFailClosed()
{
    P2KabutoHost host;
    P2KabutoAdvanceOut out;
    // Unknown identity and null bank fail closed.
    assert(!host.advance(999, attackAnimator(0.0, 51), p2attach::Affine{}, 0.0f, idleHost(), out));
    assert(host.bind(1, P2KabutoSpecies::Kabuto, nullptr) == 0);
    assert(host.bind(1, P2KabutoSpecies::Kabuto, std::shared_ptr<const p2attach::Bank>{}) == 0);
    assert(host.bind(0, P2KabutoSpecies::Kabuto, readBank(kBank)) == 0); // zero identity refused

    auto bank = readBank(kBank);
    std::vector<std::uint64_t> ids;
    for (std::size_t i = 0; i < host.kCapacity; ++i) {
        const std::uint64_t id = 5000 + i;
        assert(host.bind(id, P2KabutoSpecies::Kabuto, bank) != 0);
        ids.push_back(id);
    }
    assert(host.size() == host.kCapacity);
    assert(host.bind(9999, P2KabutoSpecies::Kabuto, bank) == 0);
    assert(host.size() == host.kCapacity);

    // Releasing admits exactly one new binding.
    assert(host.release(ids.front()));
    assert(host.size() == host.kCapacity - 1);
    assert(host.bind(9999, P2KabutoSpecies::Kabuto, bank) != 0);

    // Rebinding an existing identity keeps it bounded and usable.
    assert(host.bind(9999, P2KabutoSpecies::Rkabuto, bank) != 0);
    assert(host.size() == host.kCapacity);
    host.reset();
    assert(host.size() == 0 && !host.bound(9999));
    assert(!host.advance(9999, attackAnimator(0.0, 51), p2attach::Affine{}, 0.0f, idleHost(), out));
}

} // namespace

int main()
{
    testSpeciesMapping();
    testFeedContract();
    testLiveAnimatorFiresOnce();
    testRkabutoAndFkabuto();
    testRestartRefires();
    testInvalidAndCapacityFailClosed();
    std::puts("p2_kabuto_host_test PASS");
    return 0;
}
