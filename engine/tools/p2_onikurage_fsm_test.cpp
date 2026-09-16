// Isolated fixtures for pc_p2_onikurage_fsm.h / pc_p2_kurage_flight_policy.h
// (Greater Spotted Jellyfloat, enemy ID 72, shared-base variant of Kurage).
// Build: g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_onikurage_fsm_test.cpp -o p2_onikurage_fsm_test.exe
#include <cstdio>
#include <cstdlib>
#include "pc_p2_onikurage_fsm.h"

using namespace p2onikurage;

static int gChecks = 0;
static void require(bool ok, const char* what)
{
    ++gChecks;
    if (!ok) {
        std::printf("FAIL p2_onikurage_fsm_test: %s\n", what);
        std::fflush(stdout);
        std::_Exit(1);
    }
}
static In base()
{
    In in;
    in.deltaTime = 1.0f / 30.0f;
    in.health = 100.0f;
    in.isFlying = true;
    in.mapY = 0.0f;
    in.positionY = 90.0f;
    return in;
}

int main()
{
    // --- identity: the OniKurage face is the shared base pinned to Greater ---
    {
        Fsm fsm;
        require(fsm.variant() == Variant::Greater, "OniKurage FSM selects the Greater variant");
        fsm.spawn();
        require(fsm.state() == State::Wait, "spawn enters Wait");
    }

    // --- Greater pitch numerics differ from the Kurage defaults ---
    {
        require(p2kurage::attackPitchOffset(65.0f, Variant::Greater) == 30.0f, "Greater attack pitch key 65");
        require(p2kurage::attackPitchOffset(65.0f, Variant::Lesser) == 15.0f, "Lesser attack pitch key 65 unchanged");
        require(p2kurage::flickPitchOffset(20.0f, Variant::Greater) == -100.0f, "Greater flick pitch key 20");
        require(p2kurage::takeOffPitchOffset(40.0f, Variant::Greater) == -50.0f, "Greater takeoff pitch key 40");
        require(p2kurage::fallPitchOffset(1.0f, Variant::Greater) != p2kurage::fallPitchOffset(1.0f, Variant::Lesser),
            "Greater fall pitch differs from Lesser");
        require(p2kurage::greaterMovePitchAmplitude == 20.0f && p2kurage::lesserMovePitchAmplitude == 50.0f,
            "move-pitch amplitudes match both species");
    }

    // --- Drop entry routes from Attack END when a captain is held ---
    {
        Fsm fsm; fsm.forceState(State::Attack);
        In in = base(); in.naviSucked = true; in.naviSuckFinished = true; in.motionFinished = true;
        require(fsm.tick(in).state == State::Drop, "Attack END with a held captain enters Drop");
        require(fsm.motion() == Motion::Fall, "Drop reuses the Fall motion");
        require(!fsm.flags().untargetable, "Drop entry is targetable (disableEvent Untargetable)");
    }

    // --- health death wins over a held captain (source order) ---
    {
        Fsm fsm; fsm.forceState(State::Attack);
        In in = base(); in.health = 0.0f; in.naviSucked = true; in.naviSuckFinished = true; in.motionFinished = true;
        require(fsm.tick(in).state == State::Dead, "Attack END with zero health enters Dead before Drop");
    }

    // --- Greater Attack finishing needs a settled mouth while a captain is held ---
    {
        Fsm fsm; fsm.forceState(State::Attack);
        In held = base(); held.naviSucked = true; held.naviSuckFinished = false;
        Out out = fsm.tick(held);
        require(!out.finishing, "Greater Attack holds while the captain mouth is still settling");
        Fsm fsm2; fsm2.forceState(State::Attack);
        In ready = base(); ready.naviSucked = true; ready.naviSuckFinished = true;
        require(fsm2.tick(ready).finishing, "Greater Attack finishes once the captain mouth settles");
    }

    // --- Drop falling finish conditions (OniKurageState.cpp:492) ---
    {
        Fsm ground; ground.forceState(State::Drop);
        In nearGround = base(); nearGround.positionY = 20.0f; nearGround.mapY = 0.0f;
        require(ground.tick(nearGround).finishing, "Drop finishes within 25 units of the ground");

        Fsm rising; rising.forceState(State::Drop);
        In up = base(); up.velocityY = 1.0f;
        require(rising.tick(up).finishing, "Drop finishes when vertical velocity turns positive");

        Fsm timed; timed.forceState(State::Drop);
        In first = base(); timed.tick(first); // state timer now ~0.033
        In longTick = base(); longTick.deltaTime = 3.1f;
        timed.tick(longTick); // evaluates the previous timer, then advances
        In final = base();
        require(timed.tick(final).finishing, "Drop finishes after the three second timer");
    }

    // --- Drop END chooses Dead or Land ---
    {
        Fsm alive; alive.forceState(State::Drop);
        In end = base(); end.motionFinished = true;
        require(alive.tick(end).state == State::Land, "Drop END alive enters Land");
        Fsm dead; dead.forceState(State::Drop);
        In endDead = base(); endDead.health = 0.0f; endDead.motionFinished = true;
        require(dead.tick(endDead).state == State::Dead, "Drop END dead enters Dead");
    }

    // --- Ground with a held captain ground-flicks (OniKurageState.cpp:639) ---
    {
        Fsm fsm; fsm.forceState(State::Ground);
        In in = base(); in.naviSucked = true; in.stuckPikminCount = 0; in.motionFinished = true;
        require(fsm.tick(in).state == State::GroundFlick, "Greater Ground with a held captain enters GroundFlick");
    }

    // --- Lesser shared base ignores the captain fields (Kurage unchanged) ---
    {
        p2kurage::Fsm lesser;
        lesser.forceState(p2kurage::State::Attack);
        In in = base(); in.naviSucked = true; in.naviSuckFinished = true; in.motionFinished = true;
        require(lesser.tick(in).state == p2kurage::State::Wait,
            "Lesser Kurage Attack END ignores captain fields and returns to Wait");
        require(lesser.variant() == Variant::Lesser, "default shared FSM remains Lesser");
    }

    std::printf("p2_onikurage_fsm_test PASS checks=%d\n", gChecks);
    std::fflush(stdout);
    return 0;
}
