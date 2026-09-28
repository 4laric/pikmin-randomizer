// Standalone engine-free fixture for the Kabuto moving-muzzle provider
// (pc_port/pc_p2_kabuto_muzzle.h/.cpp). It links only the pure attachment bank
// (header-only, pc_p2_attachments.h), the pure Cannon Beetle fire FSM
// (pc_p2_kabuto_cannon.*) and the Stone birth helper (pc_p2_cannon_stone.*); no
// engine headers are used.
//
// Build (MinGW):
//   g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_kabuto_muzzle_test.cpp
//       pc_port/pc_p2_kabuto_muzzle.cpp pc_port/pc_p2_kabuto_cannon.cpp
//       pc_port/pc_p2_cannon_stone.cpp -o <private-output>/p2_kabuto_muzzle_test.exe

#include "pc_p2_kabuto_muzzle.h"

#include <cassert>
#include <cmath>
#include <cstdio>
#include <sstream>

namespace {

bool near(float a, float b, float eps = 0.0001f) { return std::fabs(a - b) <= eps; }

// Joints root(-1), body(0), mouth "KuTi"(1). Surfaced `attack` fires at frame 50
// with the mouth moving to z=5; buried `k_attack` fires at frame 55 (z=7). The
// mixed-case joint and lowercased buried clip exercise the fallback matching.
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

P2KabutoCannonConfig config() { return P2KabutoCannonConfig{0.0f, 10.0f}; }

void testResolvePerSpecies()
{
    auto bank = readBank(kBank);

    P2KabutoMouthBinding kabuto;
    assert(p2_kabuto_mouth_resolve(*bank, P2KabutoSpecies::Kabuto, kabuto));
    assert(kabuto.valid() && kabuto.clip >= 0 && kabuto.joint >= 0);
    assert(bank->clips[kabuto.clip].name == "attack" && kabuto.fireFrame == 50);

    P2KabutoMouthBinding rkabuto;
    assert(p2_kabuto_mouth_resolve(*bank, P2KabutoSpecies::Rkabuto, rkabuto));
    assert(rkabuto.valid() && rkabuto.fireFrame == 50
           && bank->clips[rkabuto.clip].name == "attack");

    // Fkabuto asks for "K_attack"; the bank ships "k_attack" (case-insensitive).
    P2KabutoMouthBinding fkabuto;
    assert(p2_kabuto_mouth_resolve(*bank, P2KabutoSpecies::Fkabuto, fkabuto));
    assert(fkabuto.valid() && fkabuto.fireFrame == 55
           && bank->clips[fkabuto.clip].name == "k_attack");

    // Missing mouth joint fails closed.
    auto noJoint = readBank("P2_ATTACHMENTS_1 1 1\nroot -1\nattack 51 2\n0 50\n"
                            "0 0 0 0 0 0 1 1 1 1\n0 0 0 0 0 0 1 1 1 1\n");
    P2KabutoMouthBinding missing;
    assert(!p2_kabuto_mouth_resolve(*noJoint, P2KabutoSpecies::Kabuto, missing));
    assert(!missing.valid());

    // A fire frame outside the resolved clip fails closed.
    auto shortClip = readBank("P2_ATTACHMENTS_1 2 1\nroot -1\nkuti 0\nattack 40 2\n0 39\n"
                              "0 0 0 0 0 0 1 1 1 1\n0 0 0 0 0 0 1 1 1 1\n"
                              "0 0 0 0 0 0 1 1 1 1\n0 0 0 0 0 0 1 1 1 1\n");
    P2KabutoMouthBinding range;
    assert(!p2_kabuto_mouth_resolve(*shortClip, P2KabutoSpecies::Kabuto, range));
}

void testSampleMouthFollowsOwner()
{
    auto bank = readBank(kBank);
    P2KabutoMuzzle muzzle;
    assert(muzzle.bind(*bank, P2KabutoSpecies::Kabuto));

    p2attach::Instance instance;
    const p2attach::Token token = instance.bind(bank);
    assert(token != 0);

    p2attach::Affine owner;
    owner.m[0][3] = 1.0f;
    owner.m[1][3] = 2.0f;
    owner.m[2][3] = 3.0f;

    p2attach::Vec mouth;
    assert(muzzle.sampleMouth(instance, token, owner, 1, mouth));
    // root (10,0,0) + mouth local (0,0,5) + owner (1,2,3).
    assert(near(mouth.x, 11.0f) && near(mouth.y, 2.0f) && near(mouth.z, 8.0f));

    // A stale token cannot read the muzzle.
    assert(!muzzle.sampleMouth(instance, token + 1, owner, 2, mouth));
}

void testSurfacedBirthAddsMouthOffsetAndReadsHoming()
{
    auto bank = readBank(kBank);
    P2KabutoMuzzle muzzle;
    assert(muzzle.bind(*bank, P2KabutoSpecies::Kabuto));

    p2attach::Instance instance;
    const p2attach::Token token = instance.bind(bank);

    P2KabutoCannon cannon;
    cannon.reset(config(), P2KabutoSpecies::Kabuto);
    assert(cannon.start());
    assert(cannon.beginAttack());
    const P2KabutoHostState host{ false, false, false, 0.0f, 10.0f };
    assert(cannon.onEvent(P2KabutoEvent::Key2, host) == P2KabutoAction::FireStone);
    assert(cannon.hasPendingBirth());

    P2KabutoStoneBirth birth;
    assert(muzzle.takeBirth(cannon, instance, token, p2attach::Affine{}, 1, 1.0f, birth));
    assert(birth.valid);
    assert(near(birth.faceDir, 1.0f));
    assert(!birth.homing);
    // createStoneAttack mouth joint + (0, 25, 0): (10, 0, 5) -> (10, 25, 5).
    assert(near(birth.mouthPosition.x, 10.0f) && near(birth.mouthPosition.y, 25.0f)
           && near(birth.mouthPosition.z, 5.0f));
    // The FireStone decision is consumed exactly once.
    assert(!cannon.hasPendingBirth());
    assert(!muzzle.takeBirth(cannon, instance, token, p2attach::Affine{}, 2, 1.0f, birth));
}

void testRkabutoBirthIsHoming()
{
    auto bank = readBank(kBank);
    P2KabutoMuzzle muzzle;
    assert(muzzle.bind(*bank, P2KabutoSpecies::Rkabuto));

    p2attach::Instance instance;
    const p2attach::Token token = instance.bind(bank);

    P2KabutoCannon cannon;
    cannon.reset(config(), P2KabutoSpecies::Rkabuto);
    assert(cannon.start() && cannon.beginAttack());
    const P2KabutoHostState host{ false, false, false, 0.0f, 10.0f };
    assert(cannon.onEvent(P2KabutoEvent::Key2, host) == P2KabutoAction::FireStone);

    P2KabutoStoneBirth birth;
    assert(muzzle.takeBirth(cannon, instance, token, p2attach::Affine{}, 1, 0.0f, birth));
    assert(birth.valid && birth.homing);
}

void testBuriedFkabutoUsesBuriedClip()
{
    auto bank = readBank(kBank);
    P2KabutoMuzzle muzzle;
    assert(muzzle.bind(*bank, P2KabutoSpecies::Fkabuto));

    p2attach::Instance instance;
    const p2attach::Token token = instance.bind(bank);

    P2KabutoCannon cannon;
    cannon.reset(config(), P2KabutoSpecies::Fkabuto);
    assert(cannon.start());
    assert(cannon.phase() == P2KabutoPhase::FixStay);

    P2KabutoHostState host;
    host.health = 10.0f;
    host.targetPresent = true;
    assert(cannon.onEvent(P2KabutoEvent::None, host) == P2KabutoAction::ToFixAppear);
    host.targetAttackable = true;
    assert(cannon.onEvent(P2KabutoEvent::End, host) == P2KabutoAction::ToFixAttack);
    assert(cannon.beginFixAttack());
    assert(cannon.onEvent(P2KabutoEvent::Key2, host) == P2KabutoAction::FireStone);

    P2KabutoStoneBirth birth;
    assert(muzzle.takeBirth(cannon, instance, token, p2attach::Affine{}, 1, 0.0f, birth));
    assert(birth.valid && !birth.homing);
    // Buried k_attack mouth at frame 55 is (0,0,7) under root (10,0,0) -> +25 y.
    assert(near(birth.mouthPosition.x, 10.0f) && near(birth.mouthPosition.y, 25.0f)
           && near(birth.mouthPosition.z, 7.0f));
}

void testTakeBirthFailsClosedWithoutPendingFire()
{
    auto bank = readBank(kBank);
    P2KabutoMuzzle muzzle;
    assert(muzzle.bind(*bank, P2KabutoSpecies::Kabuto));

    p2attach::Instance instance;
    const p2attach::Token token = instance.bind(bank);

    P2KabutoCannon cannon;
    cannon.reset(config(), P2KabutoSpecies::Kabuto);
    assert(cannon.start());

    P2KabutoStoneBirth birth;
    assert(!muzzle.takeBirth(cannon, instance, token, p2attach::Affine{}, 1, 0.0f, birth));
    assert(!birth.valid);
}

} // namespace

int main()
{
    testResolvePerSpecies();
    testSampleMouthFollowsOwner();
    testSurfacedBirthAddsMouthOffsetAndReadsHoming();
    testRkabutoBirthIsHoming();
    testBuriedFkabutoUsesBuriedClip();
    testTakeBirthFailsClosedWithoutPendingFire();
    std::puts("p2_kabuto_muzzle_test PASS");
    return 0;
}
