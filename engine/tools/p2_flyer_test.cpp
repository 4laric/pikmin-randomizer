// Engine-free fixtures for pc_p2_flyer.h and pc_p2_kurage_own.h (wave 3 flyers,
// #960): the CF_IsFlying mirror rule, the retail Kurage collision tree, the
// walk/turn maths and the source clip clock driving the Kurage FSM.
// Build: g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_flyer_test.cpp -o p2_flyer_test.exe
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include "pc_p2_flyer.h"
#include "pc_p2_kurage_fsm.h"
#include "pc_p2_kurage_own.h"
#include "pc_p2_retail_player.h"

static int gChecks = 0;
static void require(bool ok, const char* what)
{
    ++gChecks;
    if (!ok) {
        std::printf("FAIL p2_flyer_test: %s\n", what);
        std::fflush(stdout);
        std::_Exit(1);
    }
}
static bool near(float a, float b, float eps = 0.01f) { return std::fabs(a - b) <= eps; }

// Runs the FSM with a scripted world, the same way P2KurageOwn does: one
// source tick per step, the retail clip advancing one frame per tick.
struct Sim {
    p2kurage::Fsm fsm{p2kurageown::flightParms(), p2kurage::Variant::Lesser};
    p2retail::Player player;
    p2kurage::Out out;
    p2kurage::KeyEvent key = p2kurage::KeyEvent::None;
    bool end = false;
    bool untargetable = true;
    int stuck = 0;
    float health = 2500.0f;
    float y = 70.0f;
    Sim() { fsm.spawn(); }
    void step()
    {
        p2kurage::In in;
        in.deltaTime = 1.0f / 30.0f;
        in.health = health;
        in.stuckPikminCount = stuck;
        in.isFlying = untargetable;
        in.mapY = 0.0f;
        in.positionY = y;
        in.motionFrame = player.frame();
        in.keyEvent = key;
        in.motionFinished = end;
        key = p2kurage::KeyEvent::None;
        end = false;
        out = fsm.tick(in);
        if (out.motionChanged) { player.cancel(); player.start(p2kurageown::clipFor(out.motion)); }
        untargetable = out.flags.untargetable;
        player.finishMotion(out.finishing);
        player.advance(1.0f, [this](const p2retail::Event& e) {
            if (e.type == 1000) end = true;
            else if (e.type >= 1 && e.type <= 3) key = p2kurageown::keyFor(e.type);
        });
    }
};

int main()
{
    // --- the mirror rule is EnemyBase::isFlying() == EB_Untargetable ---
    require(p2flyer::airborne(true) && !p2flyer::airborne(false), "airborne mirrors EB_Untargetable");

    // --- retail collision tree: enemy/data/Kurage enemycoll.txt ---
    {
        const p2flyer::Sphere* t = p2kurageown::spheres();
        require(p2kurageown::kSphereCount == 3, "root + two stickable children (the suck part is the receiver mouth)");
        require(t[0].parent == -1 && t[1].parent == 0 && t[2].parent == 0, "pre-order tree");
        require(near(t[0].radius, 40.0f) && std::strcmp(t[0].code, "____") == 0, "radius-40 bounding sphere, not stickable");
        require(near(t[1].radius, 10.0f) && std::strcmp(t[1].code, "st__") == 0, "bod1 = 10 stickable");
        require(near(t[2].radius, 25.0f) && near(t[2].offset.x, -7.5f) && std::strcmp(t[2].code, "st__") == 0,
                "bod2 = 25 @ (-7.5,0,0) stickable");
        const p2flyer::Vec3 body = p2kurageown::defaultBodyOffset();
        // A thrown Pikmin latches from below: the lowest stickable point must sit
        // inside the bell underside band, not above the whole body.
        const float bottom = p2flyer::stickableBottom(t, p2kurageown::kSphereCount, body);
        require(bottom < 5.0f && bottom > -30.0f, "stickable bottom reaches the bell underside");
        const p2flyer::Vec3 c = p2flyer::sphereCentre(t, 3, 2, {100.0f, 70.0f, -40.0f}, 0.0f, body);
        require(near(c.x, 92.5f) && near(c.y, 92.0f) && near(c.z, -40.0f), "bod2 centre follows the root");
        const float yaw = 3.14159265f * 0.5f;
        const p2flyer::Vec3 r = p2flyer::sphereCentre(t, 3, 2, {0.0f, 0.0f, 0.0f}, yaw, {0.0f, 0.0f, 0.0f});
        require(near(r.x, 0.0f, 0.05f) && near(r.z, 7.5f, 0.05f), "offsets rotate with yaw");
    }

    // --- body offset from a mesh, fallback otherwise ---
    {
        std::vector<p2flyer::Vec3> cloud = {{-40.0f, 0.0f, -40.0f}, {40.0f, 50.0f, 40.0f}};
        p2flyer::Vec3 body{9.0f, 9.0f, 9.0f};
        require(p2flyer::bodyOffsetFromMesh(cloud.size(), [&](std::size_t i) { return cloud[i]; }, body), "finite cloud");
        require(near(body.x, 0.0f) && near(body.y, 25.0f) && near(body.z, 0.0f), "centroid");
        p2flyer::Vec3 keep{1.0f, 2.0f, 3.0f};
        require(!p2flyer::bodyOffsetFromMesh(0, [&](std::size_t i) { return cloud[i]; }, keep) && near(keep.y, 2.0f),
                "empty cloud keeps the fallback");
        std::vector<p2flyer::Vec3> bad = {{0.0f, std::nanf(""), 0.0f}};
        require(!p2flyer::bodyOffsetFromMesh(bad.size(), [&](std::size_t i) { return bad[i]; }, keep), "non-finite cloud rejected");
    }

    // --- turnToTarget / walkToTarget maths ---
    {
        // 90 degrees off, factor 0.1: step = 0.157 rad, clamped to 5 deg = 0.0873.
        const float y1 = p2flyer::turnStep(0.0f, 1.0f, 0.0f, 0.1f, 5.0f);
        require(near(y1, 5.0f * 3.14159265f / 180.0f, 0.001f), "turn clamps to the max angle");
        const float y2 = p2flyer::turnStep(0.0f, std::sin(0.2f), std::cos(0.2f), 0.1f, 5.0f);
        require(near(y2, 0.02f, 0.001f), "small error turns at the factor");
        float vx, vz;
        p2flyer::walkVelocity(0.0f, 50.0f, vx, vz);
        require(near(vx, 0.0f) && near(vz, 50.0f), "yaw 0 walks +z");
        require(near(p2flyer::roundAng(7.0f), 7.0f - 2.0f * 3.14159265f, 0.001f), "roundAng wraps");
    }

    // --- retail parms (not the Kurage.h defaults) ---
    {
        const p2kurage::Parms p = p2kurageown::flightParms();
        require(near(p.flightHeight, 70.0f) && near(p.groundTime, 0.5f) && near(p.suckTime, 2.0f), "retail proper parms");
        require(near(p.suckChance, 0.1f) && near(p.shakeTime, 1.0f) && p.minFallPiki == 6 && p.maxSuckPiki == 10,
                "retail chance/shake/min-fall");
        require(near(p2kurageown::general().life, 2500.0f), "retail life");
    }

    // --- Greater Spotted Jellyfloat (OniKurage 72): retail entry differs ---
    {
        using V = p2kurage::Variant;
        const p2kurageown::General g = p2kurageown::general(V::Greater);
        require(near(g.life, 4500.0f) && near(g.moveSpeed, 75.0f) && near(g.territoryRadius, 500.0f)
                    && near(g.sightRadius, 500.0f) && near(g.maxAttackRange, 60.0f) && near(g.attackRadius, 60.0f),
                "OniKurage general parms (life 4500, speed 75, territory/sight 500, attack 60)");
        require(near(p2kurageown::general(V::Lesser).life, 2500.0f), "Lesser parms unchanged");
        const p2kurage::Parms p = p2kurageown::flightParms(V::Greater);
        require(near(p.flightHeight, 75.0f) && near(p.riseFactor, 5.0f) && p.maxSuckPiki == 20 && p.minFallPiki == 6
                    && near(p.suckTime, 2.0f) && near(p.shakeTime, 1.0f),
                "OniKurage proper parms (flight 75, rise 5, max suck 20)");
        const p2flyer::Sphere* t = p2kurageown::spheres(V::Greater);
        require(near(t[0].radius, 55.0f) && near(t[0].offset.x, 20.0f) && near(t[1].radius, 40.0f) && near(t[1].offset.x, -10.0f)
                    && near(t[2].radius, 25.0f) && std::strcmp(t[1].code, "st__") == 0 && std::strcmp(t[2].code, "st__") == 0,
                "OniKurage retail collision tree");
        require(near(p2kurageown::mouthRadius(V::Greater), 25.0f) && near(p2kurageown::mouthRadius(V::Lesser), 15.0f), "mouth radius");
        require(std::strcmp(p2kurageown::posePrefix(V::Greater), "onikurage_") == 0, "onikurage pose prefix");
        // The Greater FSM runs the same lifecycle: six latched Pikmin drop it to Land.
        p2kurage::Fsm fsm(p, V::Greater);
        fsm.spawn();
        p2kurage::In in;
        in.deltaTime = 1.0f / 30.0f;
        in.positionY = 75.0f;
        in.stuckPikminCount = 6;
        bool fell = false;
        for (int i = 0; i < 5 && !fell; ++i) fell = fsm.tick(in).state == p2kurage::State::Fall;
        require(fell, "Greater: six latched Pikmin force Fall");
        // OniKurageState passes speedFactor 0 to setHeightVelocity everywhere (rise fp02 = 5),
        // the Kurage passes 5/2/2/5: the same 20-unit error gives a different climb speed.
        p2kurage::Fsm lesser(p2kurageown::flightParms(V::Lesser), V::Lesser);
        lesser.spawn();
        lesser.forceState(p2kurage::State::Attack);
        fsm.forceState(p2kurage::State::Attack);
        p2kurage::In hold;
        hold.deltaTime = 1.0f / 30.0f;
        hold.positionY = 0.0f;
        hold.mapY = 0.0f;
        hold.motionFrame = 0.0f;
        const float vLesser = lesser.tick(hold).heightVelocity;
        const float vGreater = fsm.tick(hold).heightVelocity;
        require(near(vLesser, (5.0f + 1.0f) * 70.0f, 0.1f), "Lesser Attack: (5 + fp02 1) * flight 70");
        require(near(vGreater, (0.0f + 5.0f) * 75.0f, 0.1f), "Greater Attack: (0 + fp02 5) * flight 75");
    }

    // --- clip table: ANF1 lengths and enemyanimmgr keys ---
    {
        using M = p2kurage::Motion;
        require(p2kurageown::clipFor(M::DeadFly).duration == 96 && p2kurageown::clipFor(M::DeadFly).events.size() == 2, "dead1");
        require(p2kurageown::clipFor(M::Land).duration == 30 && p2kurageown::clipFor(M::Land).events.empty(),
                "Land = move2, 30 frames, no keys");
        require(std::strcmp(p2kurageown::poseFor(M::Land), "move2") == 0, "Land pose is move2");
        require(std::strcmp(p2kurageown::poseFor(M::TakeOff), "type1") == 0, "TakeOff pose is type1");
        require(std::strcmp(p2kurageown::poseFor(M::Fall), "type2") == 0, "Fall pose is type2");
        for (M m : {M::DeadFly, M::DeadGround, M::FlickFly, M::FlickGround, M::Wait, M::Move, M::Land, M::TakeOff, M::Fall,
                    M::Attack}) {
            p2retail::Player p;
            require(p.start(p2kurageown::clipFor(m)), "every clip is a valid retail motion");
        }
    }

    // --- the flyer lifecycle: hover untargetable, latch weight drops it, then
    //     the grounded body is targetable; recovery back to flight ---
    {
        Sim sim;
        bool sawUntargetableHover = false;
        for (int i = 0; i < 90; ++i) {
            sim.step();
            if (sim.out.state == p2kurage::State::Wait || sim.out.state == p2kurage::State::Move)
                sawUntargetableHover = sim.untargetable;
        }
        require(sawUntargetableHover, "Wait/Move hover is EB_Untargetable (CF_IsFlying)");
        // Six thrown Pikmin latch (ip01 minFallPiki): getFlyingNextState -> Fall.
        sim.stuck = 6;
        bool fell = false, landed = false, targetableInFall = false;
        for (int i = 0; i < 400 && !landed; ++i) {
            sim.step();
            if (sim.out.state == p2kurage::State::Fall) {
                fell = true;
                if (!sim.untargetable) targetableInFall = true;
            }
            if (sim.out.state == p2kurage::State::Land) landed = true;
        }
        require(fell, "enough latched Pikmin force the Fall state");
        require(targetableInFall, "the descent drops EB_Untargetable before landing (squad can attack)");
        require(landed, "Fall ends in Land");
        require(!sim.untargetable, "Land is targetable");
        // Ground stays targetable until takeoff; with no stuck Pikmin it takes off.
        sim.stuck = 0;
        bool ground = false, takeoff = false, reflew = false;
        for (int i = 0; i < 600; ++i) {
            sim.step();
            if (sim.out.state == p2kurage::State::Ground) {
                ground = true;
                require(!sim.untargetable, "Ground is targetable");
            }
            if (sim.out.state == p2kurage::State::TakeOff) takeoff = true;
            if (takeoff && sim.untargetable) { reflew = true; break; }
        }
        require(ground && takeoff && reflew, "Land -> Ground -> TakeOff -> untargetable flight again");
    }

    // --- fewer than ip01 latched Pikmin for shakeTime: the flyer shakes them off ---
    {
        Sim sim;
        for (int i = 0; i < 10; ++i) sim.step();
        sim.stuck = 2;
        bool flick = false, keyStick = false;
        for (int i = 0; i < 200 && !flick; ++i) {
            sim.step();
            if (sim.out.state == p2kurage::State::FlyFlick) flick = true;
        }
        require(flick, "a few latched Pikmin held past fp04 trigger the airborne flick");
        for (int i = 0; i < 100 && !keyStick; ++i) {
            sim.step();
            if (sim.out.flickStick) keyStick = true;
        }
        require(keyStick, "the flick KEY2 flicks the stuck Pikmin off");
    }

    // --- death: health <= 0 while hovering goes to Dead, then the END key kills ---
    {
        Sim sim;
        for (int i = 0; i < 20; ++i) sim.step();
        sim.health = 0.0f;
        bool dead = false, killed = false, flick = false, bomb = false;
        for (int i = 0; i < 400 && !killed; ++i) {
            sim.step();
            if (sim.out.state == p2kurage::State::Dead) dead = true;
            if (sim.out.flickStick) flick = true;
            if (sim.out.bodyBomb) bomb = true;
            if (sim.out.kill) killed = true;
        }
        require(dead && flick && bomb && killed, "Dead: KEY2 flick, KEY3 death procedure, END kill");
    }

    // --- suction: the attack clip opens the window on KEY2 and closes on KEY1 ---
    {
        Sim sim;
        sim.fsm.forceState(p2kurage::State::Attack);
        bool sucked = false, stopped = false;
        for (int i = 0; i < 200; ++i) {
            sim.step();
            if (sim.out.isSucking) sucked = true;
            if (sucked && !sim.out.isSucking) { stopped = true; break; }
        }
        require(sucked && stopped, "suction opens at KEY2 and closes at KEY1 once finishing");
    }

    // --- suckFull ends the attack early (suckPikmin -> finishMotion) ---
    {
        Sim sim;
        sim.fsm.forceState(p2kurage::State::Attack);
        bool sawFinishing = false;
        for (int i = 0; i < 60; ++i) {
            sim.step();
            if (sim.out.isSucking) break;
        }
        p2kurage::In in;
        in.deltaTime = 1.0f / 30.0f;
        in.suckFull = true;
        in.isFlying = true;
        in.positionY = 70.0f;
        const p2kurage::Out o = sim.fsm.tick(in);
        sawFinishing = o.finishing;
        require(sawFinishing, "a full stomach requests the motion finish while sucking");
    }

    std::printf("PASS p2_flyer_test checks=%d\n", gChecks);
    return 0;
}
