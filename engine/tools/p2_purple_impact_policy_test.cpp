#include "pc_p2_purple_impact_policy.h"

#include <cassert>

#undef assert
#define assert(condition) do { if (!(condition)) return __LINE__; } while (false)

using namespace p2purpleimpact;

int main()
{
    Event event { 1, 1, 10.0f, -5000.0f, 20.0f };
    assert(inRange(event, 86.0f, 20.0f, 16.0f));
    assert(inRange(event, 85.999f, 20.0f, 16.0f));
    assert(!inRange(event, 86.001f, 20.0f, 16.0f));
    assert(!inRange(event, 10.0f, 20.0f, -1.0f));

    int purple = 0;
    Sources sources;
    Event first = sources.arm(&purple);
    Event emitted;
    assert(sources.consume(&purple, emitted, 1.0f, 2.0f, 3.0f));
    assert(emitted.sourceLifetime == first.sourceLifetime);
    assert(emitted.attackToken == first.attackToken);
    assert(!sources.consume(&purple, emitted, 4.0f, 5.0f, 6.0f));
    Event second = sources.arm(&purple);
    assert(second.sourceLifetime != first.sourceLifetime);
    assert(second.attackToken != first.attackToken);
    assert(sources.consume(&purple, emitted, 4.0f, 5.0f, 6.0f));
    sources.forget(&purple);
    assert(!sources.consume(&purple, emitted, 0.0f, 0.0f, 0.0f));

    ReceiverState receiver;
    receive(receiver, 7);
    assert(receiver.phase == Phase::Bounce);
    assert(!updateBounce(receiver, true, 0.299f));
    assert(!updateBounce(receiver, true, 0.299f));
    assert(!updateBounce(receiver, true, 0.299f));
    assert(updateBounce(receiver, true, 0.299f));
    assert(updateFit(receiver, 10.0f, false, RedFitDuration));
    assert(!updateFit(receiver, 0.001f, false, RedFitDuration));

    // Source variant fit duration: BlueKochappy (Dwarf Orange Bulborb) fp38 = 5 s.
    ReceiverState orange;
    receive(orange, 12);
    assert(orange.phase == Phase::Bounce);
    for (int i = 0; i < 3; ++i) assert(!updateBounce(orange, true, 0.1f));
    assert(updateBounce(orange, true, 0.1f));
    assert(updateFit(orange, 4.9f, false, 5.0f));
    assert(!updateFit(orange, 0.2f, false, 5.0f));

    receive(receiver, 7);
    receiver.fitElapsed = 4.0f;
    for (int i = 0; i < 3; ++i) assert(!updateBounce(receiver, true, 0.9f));
    assert(updateBounce(receiver, true, 0.9f));
    assert(receiver.fitElapsed == 4.0f);

    ReceiverState miss;
    receive(miss, 8);
    for (int i = 0; i < 3; ++i) assert(!updateBounce(miss, true, 0.3f));
    assert(!updateBounce(miss, true, 0.3f));
    assert(miss.phase == Phase::None);

    ReceiverState airborne;
    receive(airborne, 9);
    for (int i = 0; i < 10; ++i) assert(!updateBounce(airborne, false, 0.0f));
    assert(updateBounce(airborne, true, 0.0f));
    assert(!updateFit(airborne, 0.1f, true, RedFitDuration));

    ReceiverState reused;
    receive(reused, 10);
    reused.fitElapsed = 5.0f;
    receive(reused, 11);
    assert(reused.fitElapsed == 0.0f);
    assert(bounceVelocity(1.0f, 0.0f) == 200.0f);
    assert(bounceVelocity(1.0f, 1.0f) == 300.0f);
}
