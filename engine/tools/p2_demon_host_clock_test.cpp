#include "pc_p2_retail_player.h"
#include "pc_p2_demon_catchfly_policy.h"
#include <cassert>
#include <cstdio>
#include <initializer_list>

static p2retail::Motion motion(const char* name, int duration,
                               std::initializer_list<p2retail::Event> events)
{
    p2retail::Motion result;
    result.name = name;
    result.duration = duration;
    result.events.assign(events.begin(), events.end());
    return result;
}

int main()
{
    const auto selected = p2demon::selectTarget(2, 3, 4, 10, 1.5707963f);
    assert(selected.valid && selected.x > 11.9f && selected.y == 3.0f && selected.z > 3.9f && selected.z < 4.1f);
    assert(!p2demon::selectTarget(0, 0, 0, -1, 0).valid);
    const auto seedA = p2demon::selectTargetSeeded(1, 2, 3, 8, 0x40000000u);
    const auto seedB = p2demon::selectTargetSeeded(1, 2, 3, 8, 0x40000000u);
    assert(seedA.valid && seedB.valid && seedA.x == seedB.x && seedA.z == seedB.z);
    assert(seedA.x > 8.9f && seedA.x < 9.1f && seedA.z > 2.9f && seedA.z < 3.1f);
    p2demon::CatchFlyInput input{0, 10, 0, 40, 10, 0, 0, 0, 20, 25,
        1, 0, 10, 0, 0.4f, 10.0f, 0, p2demon::HeightNext::Fall, true};
    auto pursuit = p2demon::catchFly(input);
    assert(pursuit.velocityX > 0 && pursuit.velocityY > 0 && !pursuit.finishMotion);
    assert(pursuit.faceDirection > 0 && pursuit.faceDirection < 0.18f);
    input.faceDirection = pursuit.faceDirection;
    auto turn2 = p2demon::catchFly(input);
    assert(turn2.faceDirection > pursuit.faceDirection && turn2.faceDirection < 0.36f);
    input.elapsedSeconds = 4.0f;
    assert(p2demon::catchFly(input).heightNext == p2demon::HeightNext::Fall);
    input.targetAttached = false;
    assert(p2demon::catchFly(input).next == P2DemonAttackNext::Move);
    input.targetAttached = true; input.elapsedSeconds = 11.0f;
    assert(p2demon::catchFly(input).finishMotion);

    const auto catchFly = motion("waitact2.bca", 50, {{0, 0}, {39, 1}});
    p2retail::Player player;
    assert(player.start(catchFly));
    for (int i = 0; i < 39; ++i)
        assert(player.advance(1.0f, [](p2retail::Event) {}) == p2retail::Update::Ok);
    assert(player.frame() == 39.0f);
    assert(player.advance(1.0f, [](p2retail::Event event) { assert(event.type == 1); }) == p2retail::Update::Ok);
    assert(player.frame() == 0.0f); // CatchFly loops until the host calls finishMotion.
    player.finishMotion();
    bool ended = false;
    for (int i = 0; i < 50; ++i)
        assert(player.advance(1.0f, [&](p2retail::Event event) {
            assert(event.type == 0 || event.type == 1 || event.type == 1000);
            ended |= event.type == 1000;
        }) == p2retail::Update::Ok);
    assert(ended && player.completed());

    const auto fallMeck = motion("waitact1.bca", 30, {{8, 2}, {19, 3}, {25, 4}});
    assert(player.start(fallMeck));
    bool released = false, fallEnded = false;
    for (int i = 0; i < 30; ++i)
        assert(player.advance(1.0f, [&](p2retail::Event event) {
            if (event.type == 3) {
                assert(player.frame() == 20.0f && !released);
                released = true;
            }
            if (event.type == 1000) fallEnded = true;
        }) == p2retail::Update::Ok);
    assert(released && fallEnded);
    std::puts("p2_demon_host_clock_test PASS");
}

