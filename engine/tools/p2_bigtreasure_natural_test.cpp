// Standalone engine-free end-to-end fixture for the ordinary BigTreasure
// chain, issue #246: the animation keyframe source (pc_p2_bigtreasure_animclock)
// drives the FSM host (pc_p2_bigtreasure_ordinary) with the live seam through
// Stay -> Land -> ItemWalk -> ... -> PreAttack -> Attack -> startAttack, then
// natural hits knocked off through the lane ingress with a DropItem/death
// finale. Build (MinGW):
//   g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_bigtreasure_natural_test.cpp pc_port/pc_p2_bigtreasure_ordinary.cpp pc_port/pc_p2_bigtreasure_animclock.cpp pc_port/pc_p2_bigtreasure_motion.cpp pc_port/pc_p2_bigtreasure_fsmhost.cpp pc_port/pc_p2_bigtreasure_host.cpp pc_port/pc_p2_bigtreasure_fsm.cpp pc_port/pc_p2_bigtreasure.cpp pc_port/pc_p2_bigtreasure_attacks.cpp -o <private-output>/p2_bigtreasure_natural_test.exe

#include "pc_p2_bigtreasure_animclock.h"
#include "pc_p2_bigtreasure_ordinary.h"

#include <cassert>
#include <cstdio>
#include <fstream>
#include <string>

namespace {
const char* kProfilePath = "p2_bigtreasure_natural_test_profile.txt";
const char* kTablePath = "p2_bigtreasure_natural_test_table.txt";

const char* kClips[] = {
    "appear", "appear2", "wait1", "preattackf", "attackf", "attackendf",
    "preattackfr", "attackfr", "attackendfr", "preattackfl", "attackfl",
    "attackendfl", "preattackfb", "attackfb", "attackendfb", "preattackw",
    "attackw", "attackendw", "preattackg", "attackg", "attackendg",
    "preattacke", "attacke", "attackende", "dropitem", "wait2", "flick",
    "dead", "move1",
};

std::string hash64(char fill) { return std::string(64, fill); }

void writeTable()
{
    std::ofstream out(kTablePath, std::ios::binary | std::ios::trunc);
    out << "P2_RETAIL_EVENTS_1 " << hash64('a') << " 29\n";
    for (const char* clip : kClips) {
        const std::string name(clip);
        int duration = 4;
        if (name == "appear2") duration = 3;
        if (name == "attacke") duration = 5;
        if (name == "dead") duration = 6;
        if (name == "wait1" || name == "wait2") duration = 90;
        out << name << ".bca " << duration << " 2 " << hash64('b');
        if (name == "wait1" || name == "wait2") {
            out << " 2\n0 0\n89 1\n";
        } else if (name == "attacke") {
            out << " 1\n1 2\n";
        } else if (name == "dead") {
            out << " 1\n2 100\n";
        } else {
            out << " 0\n";
        }
    }
}

struct Rig {
    P2BigTreasureHostSeam seam;
    P2BigTreasureOrdinary ord;
    P2BigTreasureAnimClock clock;
    P2BigTreasureFsmHostOutput out;
    bool startAttackSeen = false;

    Rig()
    {
        std::ofstream profile(kProfilePath, std::ios::binary | std::ios::trunc);
        profile << "P2_BIGTREASURE_HOST_1\n"
                   "placement 0 0 0 0\n"
                   "target 0 0 100\n"
                   "timer 0\n"
                   "discharge 16\n";
        profile.close();
        assert(p2_bigtreasure_host_setup(kProfilePath, seam));
        P2BigTreasureFsmParms parms;
        ord.reset(parms);
        assert(clock.load(kTablePath));
    }

    void tick()
    {
        P2BigTreasureAnimPulses pulses;
        clock.tick(ord.phase(), ord.chosenWeapon(), pulses);
        P2BigTreasureOrdinaryFacts f;
        f.delta = 1.0f / 30.0f;
        f.hasTarget = true;
        f.targetInBox = true;
        f.finishIKMotion = true;
        f.animEnd = pulses.animEnd;
        f.keyEvent2 = pulses.keyEvent2;
        f.keyEvent100 = pulses.keyEvent100;
        ord.tick(seam, f, out);
        startAttackSeen = startAttackSeen || out.fsm.startAttack;
    }
};

void testNaturalChainToAttack()
{
    writeTable();
    Rig rig;
    int guard = 0;
    while (!(rig.startAttackSeen && rig.seam.attacksStarted > 0) && guard++ < 8000) {
        rig.tick();
    }
    assert(rig.startAttackSeen);
    assert(rig.seam.attacksStarted >= 1);
    assert(rig.ord.phase() == P2BT_Attack);
    assert(rig.seam.director.pools.isStarted(rig.ord.chosenWeapon()));
    std::puts("PASS natural_attack_start");
}

void testNaturalKnockoffAndFinale()
{
    Rig rig;
    int guard = 0;
    while (!(rig.startAttackSeen && rig.seam.attacksStarted > 0) && guard++ < 8000) {
        rig.tick();
    }
    assert(rig.startAttackSeen);

    // Natural hits drain every weapon (one per source tick through the ingress).
    for (int weapon = 0; weapon < P2BTWEAPON_Count; ++weapon) {
        assert(rig.ord.postHit({weapon, P2BigTreasureOwnership::kWeaponMaxHealth, false}));
        rig.tick();
    }
    assert(rig.seam.ownership.weaponCount() == 0);
    assert(rig.seam.ownership.isBodyExposed());
    assert(rig.ord.phase() == P2BT_DropItem);

    // DropItem clip completes -> Walk; then a kill event drives Dead, whose
    // clip releases Louie and confirms the kill at the tail.
    int guard2 = 0;
    while (rig.ord.phase() == P2BT_DropItem && guard2++ < 100) {
        rig.tick();
    }
    assert(rig.ord.phase() == P2BT_Walk || rig.ord.phase() == P2BT_Wait);

    P2BigTreasureOrdinaryFacts kill;
    kill.killed = true;
    P2BigTreasureFsmHostOutput out;
    rig.ord.tick(rig.seam, kill, out);
    assert(rig.ord.phase() == P2BT_Dead);

    bool released = false, killRequested = false;
    for (int i = 0; i < 20; ++i) {
        rig.tick();
        released = released || rig.out.fsm.releaseLoozy;
        killRequested = killRequested || rig.out.fsm.killRequested;
    }
    assert(released);
    assert(killRequested);
    std::puts("PASS natural_knockoff_finale");
}
} // namespace

int main()
{
    testNaturalChainToAttack();
    testNaturalKnockoffAndFinale();
    std::remove(kProfilePath);
    std::remove(kTablePath);
    std::puts("PASS BIGTREASURE_NATURAL");
    return 0;
}
