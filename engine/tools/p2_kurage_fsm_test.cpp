// Isolated fixtures for pc_p2_kurage_fsm.h (Lesser Jellyfloat, #243).
// Build: g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_kurage_fsm_test.cpp -o p2_kurage_fsm_test.exe
#include <cstdio>
#include <cstdlib>
#include "pc_p2_kurage_fsm.h"

using namespace p2kurage;

static int gChecks = 0;
static void require(bool ok, const char* what)
{
    ++gChecks;
    if (!ok) {
        std::printf("FAIL p2_kurage_fsm_test: %s\n", what);
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
    // --- spawn ---
    {
        Fsm fsm; fsm.spawn();
        require(fsm.state() == State::Wait, "spawn enters Wait");
        Out out = fsm.tick(base());
        require(out.motionChanged && out.motion == Motion::Move, "Wait entry uses the Move motion");
    }

    // --- Wait target routing ---
    {
        Fsm fsm; fsm.forceState(State::Wait);
        In in = base(); in.targetFound = true; in.suckTarget = true; in.motionFinished = true;
        require(fsm.tick(in).state == State::Attack, "Wait + suckable target enters Attack");

        Fsm fsm2; fsm2.forceState(State::Wait);
        In chase = base(); chase.targetFound = true; chase.suckTarget = false; chase.motionFinished = true;
        require(fsm2.tick(chase).state == State::Chase, "Wait + distant target enters Chase");

        Fsm fsm3; fsm3.forceState(State::Wait);
        In t1 = base(); t1.deltaTime = 4.0f; fsm3.tick(t1);
        In t2 = base(); t2.motionFinished = true;
        require(fsm3.tick(t2).state == State::Move, "Wait timeout with no target enters Move");
    }

    // --- Move arrival ---
    {
        Fsm fsm; fsm.forceState(State::Move);
        In in = base(); in.distToTargetXZ = 20.0f; in.motionFinished = true;
        require(fsm.tick(in).state == State::Wait, "Move arrival within 25 units enters Wait");
    }

    // --- Chase lost target ---
    {
        Fsm fsm; fsm.forceState(State::Chase);
        In in = base(); in.targetFound = false; in.motionFinished = true;
        require(fsm.tick(in).state == State::Move, "Chase losing target returns to Move");
    }

    // --- Attack ---
    {
        Fsm fsm; fsm.forceState(State::Attack);
        In k2 = base(); k2.keyEvent = KeyEvent::Key2;
        Out out = fsm.tick(k2);
        require(out.suckStart && out.isSucking, "Attack Key2 starts suction");

        Fsm fsm2; fsm2.forceState(State::Attack);
        In endSuck = base(); endSuck.suckAny = true; endSuck.motionFinished = true;
        require(fsm2.tick(endSuck).state == State::Attack, "Attack END with a suckable Piki re-attacks");

        Fsm fsm3; fsm3.forceState(State::Attack);
        In endIdle = base(); endIdle.motionFinished = true;
        require(fsm3.tick(endIdle).state == State::Wait, "Attack END with nothing nearby returns to Wait");

        Fsm fsm4; fsm4.forceState(State::Attack);
        In purple = base(); purple.purpleStuck = true; purple.motionFinished = true;
        require(fsm4.tick(purple).state == State::Fall, "Purple latch during Attack forces Fall");
    }

    // --- Fall / Land lifecycle ---
    {
        Fsm fsm; fsm.forceState(State::Fall);
        In in = base(); in.motionFinished = true;
        require(fsm.tick(in).state == State::Land, "Fall alive enters Land");
        Fsm fsm2; fsm2.forceState(State::Fall);
        In dead = base(); dead.health = 0.0f; dead.motionFinished = true;
        require(fsm2.tick(dead).state == State::Dead, "Fall death enters Dead");
        Fsm fsm3; fsm3.forceState(State::Land);
        In land = base(); land.motionFinished = true;
        require(fsm3.tick(land).state == State::Ground, "Land alive enters Ground");
    }

    // --- Ground routing ---
    {
        Fsm fsm; fsm.forceState(State::Ground);
        In in = base(); in.stuckPikminCount = 0; in.motionFinished = true;
        require(fsm.tick(in).state == State::TakeOff, "Ground with no Pikmin takes off");
        Fsm fsm2; fsm2.forceState(State::Ground);
        In stuck = base(); stuck.stuckPikminCount = 3; stuck.motionFinished = true;
        require(fsm2.tick(stuck).state == State::GroundFlick, "Ground with Pikmin ground-flicks");
        Fsm fsm3; fsm3.forceState(State::Ground);
        In dead = base(); dead.health = 0.0f; dead.motionFinished = true;
        require(fsm3.tick(dead).state == State::Dead, "Ground death enters Dead");
    }

    // --- TakeOff ---
    {
        Fsm fsm; fsm.forceState(State::TakeOff);
        In in = base(); in.motionFinished = true;
        require(fsm.tick(in).state == State::Wait, "TakeOff enters Wait");
        Fsm fsm2; fsm2.forceState(State::TakeOff);
        In dead = base(); dead.health = 0.0f; dead.motionFinished = true;
        require(fsm2.tick(dead).state == State::Dead, "TakeOff death enters Dead");
        Fsm fsm3; fsm3.forceState(State::TakeOff);
        require(!fsm3.flags().untargetable, "TakeOff entry is targetable");
        In k2 = base(); k2.keyEvent = KeyEvent::Key2; fsm3.tick(k2);
        require(fsm3.flags().untargetable, "TakeOff Key2 becomes untargetable again");
    }

    // --- FlyFlick / GroundFlick ---
    {
        Fsm fsm; fsm.forceState(State::FlyFlick);
        In in = base(); in.suckAny = true; in.motionFinished = true;
        require(fsm.tick(in).state == State::Attack, "FlyFlick END with target re-attacks");
        Fsm fsm2; fsm2.forceState(State::FlyFlick);
        In idle = base(); idle.motionFinished = true;
        require(fsm2.tick(idle).state == State::Wait, "FlyFlick END without target returns to Wait");

        Fsm fsm3; fsm3.forceState(State::GroundFlick);
        In k3 = base(); k3.keyEvent = KeyEvent::Key3;
        require(fsm3.tick(k3).flickNearby, "GroundFlick Key3 flicks nearby and stuck actors");
        In end = base(); end.motionFinished = true;
        require(fsm3.tick(end).state == State::TakeOff, "GroundFlick END takes off");
    }

    // --- Dead ---
    {
        Fsm fsm; fsm.forceState(State::Dead);
        require(!fsm.flags().cullable, "Dead clears Cullable");
        require(fsm.motion() == Motion::DeadFly, "flying death uses the DeadFly motion");
        In k2 = base(); k2.keyEvent = KeyEvent::Key2;
        require(fsm.tick(k2).flickStick, "Dead Key2 flicks stuck Pikmin");
        In k3 = base(); k3.keyEvent = KeyEvent::Key3;
        Out out = fsm.tick(k3);
        require(out.deathProcedure && out.bodyBomb, "Dead Key3 runs the death procedure and body bomb");
        In end = base(); end.motionFinished = true;
        require(fsm.tick(end).kill, "Dead END kills the enemy");

        Fsm ground; ground.forceState(State::Dead);
        In g = base(); g.isFlying = false;
        ground.tick(g);
        ground.forceState(State::Dead);
        In gn = base(); gn.isFlying = false; ground.tick(gn);
        require(ground.state() == State::Dead, "grounded death stays in Dead");
    }

    // --- getFlyingNextState immediate routing ---
    {
        Fsm dead; dead.forceState(State::Wait);
        In d = base(); d.health = 0.0f;
        require(dead.tick(d).state == State::Dead, "flying death routes immediately to Dead");

        Fsm purple; purple.forceState(State::Wait);
        In p = base(); p.purpleStuck = true;
        require(purple.tick(p).state == State::Fall, "Purple latch routes immediately to Fall");

        Fsm fall; fall.forceState(State::Wait);
        In f = base(); f.stuckPikminCount = 10;
        require(fall.tick(f).state == State::Fall, "reaching ip01 routes immediately to Fall");

        Fsm flick; flick.forceState(State::Wait);
        In k = base(); k.deltaTime = 4.0f; k.stuckPikminCount = 2;
        require(flick.tick(k).state == State::FlyFlick, "long shake with few Pikmin routes to FlyFlick");
    }

    std::printf("p2_kurage_fsm_test PASS checks=%d\n", gChecks);
    std::fflush(stdout);
    return 0;
}
