// Isolated fixtures for pc_p2_sarai_fsm.h (Swooping Snitchbug, #166, lane 30).
// Build: g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_sarai_fsm_test.cpp -o p2_sarai_fsm_test.exe
#include <cstdio>
#include <cstdlib>
#include "pc_p2_sarai_fsm.h"

using namespace p2sarai;

static int gChecks = 0;
static void require(bool ok, const char* what)
{
    ++gChecks;
    if (!ok) {
        std::printf("FAIL p2_sarai_fsm_test: %s\n", what);
        std::fflush(stdout);
        std::_Exit(1);
    }
}
static In base()
{
    In in;
    in.deltaTime = 1.0f / 30.0f;
    in.health = 100.0f;
    in.mapY = 0.0f;
    in.positionY = 0.0f;
    return in;
}

int main()
{
    // --- spawn chooses idle motion by random ---
    {
        Fsm fsm; fsm.spawn(0.9f);
        require(fsm.state() == State::Wait, "spawn enters Wait");
        In in = base(); Out out = fsm.tick(in);
        require(out.motionChanged && out.motion == Motion::Move, "spawn random >= 0.5 picks Move motion");
        Fsm fsm2; fsm2.spawn(0.1f);
        Out out2 = fsm2.tick(base());
        require(out2.motion == Motion::Wait, "spawn random < 0.5 picks Wait motion");
    }

    // --- Wait -> Attack on target + END; Wait -> Move otherwise ---
    {
        Fsm fsm; fsm.forceState(State::Wait, 0.1f);
        In in = base(); in.targetPresent = true; in.motionFinished = true;
        Out out = fsm.tick(in);
        require(out.state == State::Attack && out.motionChanged, "Wait+target+END enters Attack");
        Fsm fsm2; fsm2.forceState(State::Wait, 0.1f);
        In idle = base(); idle.motionFinished = true;
        Out out2 = fsm2.tick(idle);
        require(out2.state == State::Move, "Wait idle END returns to Move");
    }

    // --- Attack: catch window, Key4 fail, END catch/fail, Key3 interrupt ---
    {
        Fsm fsm; fsm.forceState(State::Attack, 0.1f);
        In in = base(); in.hasTargetCreature = true; in.targetFrame = 20.0f;
        Out out = fsm.tick(in);
        require(out.attemptCatch, "Attack frame 20 attempts catch");
        In early = base(); early.hasTargetCreature = true; early.targetFrame = 10.0f;
        require(!fsm.tick(early).attemptCatch, "Attack frame 10 does not catch");

        Fsm fsm2; fsm2.forceState(State::Attack, 0.1f);
        In fail = base(); fail.hasTargetCreature = true; fail.mouthCarried = 0; fail.keyEvent = KeyEvent::Key4;
        Out out2 = fsm2.tick(fail);
        require(out2.state == State::Fail, "Attack Key4 without catch enters Fail");

        Fsm fsm3; fsm3.forceState(State::Attack, 0.1f);
        In endCatch = base(); endCatch.hasTargetCreature = true; endCatch.mouthCarried = 1; endCatch.motionFinished = true;
        require(fsm3.tick(endCatch).state == State::CatchFly, "Attack END with catch enters CatchFly");

        Fsm fsm4; fsm4.forceState(State::Attack, 0.1f);
        In endMiss = base(); endMiss.hasTargetCreature = true; endMiss.mouthCarried = 0; endMiss.motionFinished = true;
        require(fsm4.tick(endMiss).state == State::Move, "Attack END without catch returns to Move");

        require(fsm.flags().noInterrupt, "Attack entry sets NoInterrupt");
        Fsm fsm5; fsm5.forceState(State::Attack, 0.1f);
        In k3 = base(); k3.hasTargetCreature = true; k3.keyEvent = KeyEvent::Key3;
        fsm5.tick(k3);
        require(!fsm5.flags().noInterrupt, "Attack Key3 clears NoInterrupt");

        Fsm fsm6; fsm6.forceState(State::Attack, 0.1f);
        In lost = base(); lost.hasTargetCreature = false;
        require(fsm6.tick(lost).state == State::Move, "Attack with no target creature returns to Move");
    }

    // --- CatchFly: keep-flying when no decision; drop decision routes ---
    {
        Fsm fsm; fsm.forceState(State::CatchFly, 0.1f);
        In in = base(); in.mouthCarried = 1; in.bodyStuckCount = 2;
        require(fsm.tick(in).state == State::CatchFly, "CatchFly keeps flying with catch and no decision");

        In highPurple = in; highPurple.positionY = 100.0f; highPurple.purpleLatched = true;
        require(fsm.tick(highPurple).state == State::Fall, "Purple latch at height drops (Fall)");

        Fsm fsm2; fsm2.forceState(State::CatchFly, 0.1f);
        In highFlick = in; highFlick.positionY = 100.0f; highFlick.randomUnit = 0.0f;
        require(fsm2.tick(highFlick).state == State::Flick, "Low random at height flicks attackers");

        Fsm fsm3; fsm3.forceState(State::CatchFly, 0.1f);
        In highFall = in; highFall.positionY = 100.0f; highFall.randomUnit = 0.99f;
        require(fsm3.tick(highFall).state == State::Fall, "High random at height drops captured Pikmin");

        Fsm fsm4; fsm4.forceState(State::CatchFly, 0.1f);
        In lost = base(); lost.mouthCarried = 0;
        require(fsm4.tick(lost).state == State::Move, "losing the catch exits CatchFly to Move");

        Fsm fsm5; fsm5.forceState(State::CatchFly, 0.1f);
        In end = in; end.motionFinished = true;
        require(fsm5.tick(end).state == State::FallMeck, "CatchFly END enters FallMeck");
    }

    // --- FallMeck drop at Key3 then Move ---
    {
        Fsm fsm; fsm.forceState(State::FallMeck, 0.1f);
        In k3 = base(); k3.keyEvent = KeyEvent::Key3;
        require(fsm.tick(k3).drop, "FallMeck Key3 releases captives");
        In end = base(); end.motionFinished = true;
        require(fsm.tick(end).state == State::Move, "FallMeck END returns to Move");
    }

    // --- TakeOff decision routing ---
    {
        Fsm fsm; fsm.forceState(State::TakeOff, 0.1f);
        In in = base(); in.mouthCarried = 1; in.motionFinished = true;
        require(fsm.tick(in).state == State::CatchFly, "TakeOff with catch and no height decision enters CatchFly");
        Fsm fsm2; fsm2.forceState(State::TakeOff, 0.1f);
        In in2 = base(); in2.motionFinished = true;
        require(fsm2.tick(in2).state == State::Move, "TakeOff with no catch enters Move");
        Fsm fsm3; fsm3.forceState(State::TakeOff, 0.1f);
        In in3 = base(); in3.health = 0.0f; in3.motionFinished = true;
        Out out3 = fsm3.tick(in3);
        require(out3.state == State::Fall && out3.flickAttackers, "TakeOff death routes to Fall and flicks attackers");
    }

    // --- Fall / Damage lifecycle ---
    {
        Fsm fsm; fsm.forceState(State::Fall, 0.1f);
        In in = base(); in.health = 0.0f; in.motionFinished = true;
        Out out = fsm.tick(in);
        require(out.state == State::Dead && out.flickAttackers, "Fall death enters Dead and flicks");
        Fsm fsm2; fsm2.forceState(State::Fall, 0.1f);
        In in2 = base(); in2.motionFinished = true;
        require(fsm2.tick(in2).state == State::Damage, "Fall alive enters Damage");
        Fsm fsm3; fsm3.forceState(State::Fall, 0.1f);
        In in3 = base(); in3.keyEvent = KeyEvent::Key2;
        require(fsm3.tick(in3).downEffect, "Fall Key2 emits down effect");

        Fsm fsm4; fsm4.forceState(State::Damage, 0.1f);
        In in4 = base(); in4.motionFinished = true;
        require(fsm4.tick(in4).state == State::TakeOff, "Damage alive enters TakeOff");
        Fsm fsm5; fsm5.forceState(State::Damage, 0.1f);
        In in5 = base(); in5.health = 0.0f; in5.motionFinished = true;
        require(fsm5.tick(in5).state == State::Dead, "Damage death enters Dead");
    }

    // --- Flick: Key2 flicks, END routes ---
    {
        Fsm fsm; fsm.forceState(State::Flick, 0.1f);
        In in = base(); in.keyEvent = KeyEvent::Key2;
        require(fsm.tick(in).flickAttackers, "Flick Key2 flicks stuck Pikmin");
        In end = base(); end.motionFinished = true;
        require(fsm.tick(end).state == State::Move, "Flick END without catch returns to Move");
        Fsm fsm2; fsm2.forceState(State::Flick, 0.1f);
        In endCatch = base(); endCatch.mouthCarried = 1; endCatch.motionFinished = true;
        require(fsm2.tick(endCatch).state == State::CatchFly, "Flick END with catch enters CatchFly");
        Fsm fsm3; fsm3.forceState(State::Flick, 0.1f);
        In endDead = base(); endDead.health = 0.0f; endDead.motionFinished = true;
        require(fsm3.tick(endDead).state == State::Fall, "Flick END death enters Fall");
    }

    // --- Dead ---
    {
        Fsm fsm; fsm.forceState(State::Dead, 0.1f);
        require(!fsm.flags().cullable, "Dead clears Cullable");
        In in = base(); in.motionFinished = true;
        require(fsm.tick(in).kill, "Dead END kills the enemy");
    }

    // --- Move arrival / END routing ---
    {
        Fsm fsm; fsm.forceState(State::Move, 0.1f);
        In in = base(); in.distToPatrolTargetXZ = 24.0f;
        require(fsm.tick(in).finishing, "Move within 25 units finishes its motion");
        Fsm fsm2; fsm2.forceState(State::Move, 0.1f);
        In end = base(); end.motionFinished = true;
        require(fsm2.tick(end).state == State::Wait, "Move END without target returns to Wait");
    }

    std::printf("p2_sarai_fsm_test PASS checks=%d\n", gChecks);
    std::fflush(stdout);
    return 0;
}
