// Standalone engine-free chain fixture for lane 20 (#169/#424): shared sampled
// clock -> Kabuto event adapter -> fire FSM -> attachment-bank muzzle -> Stone
// birth. It links only the header-only attachment bank, the shared sampled
// clock, the event adapter, the fire FSM, the muzzle provider and the Stone
// birth helper; no engine headers are used.
//
// Build (MinGW):
//   g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_kabuto_chain_test.cpp
//       pc_port/pc_p2_kabuto_events.cpp pc_port/pc_p2_kabuto_muzzle.cpp
//       pc_port/pc_p2_kabuto_cannon.cpp pc_port/pc_p2_cannon_stone.cpp
//       -o <private-output>/p2_kabuto_chain_test.exe

#include "pc_p2_kabuto_events.h"
#include "pc_p2_kabuto_muzzle.h"

#include <cassert>
#include <cmath>
#include <cstdio>
#include <sstream>

namespace {

bool near(float a, float b, float eps = 0.0001f) { return std::fabs(a - b) <= eps; }

// Joints root(-1), body(0), mouth "KuTi"(1); surfaced `attack` fires at frame 50
// with the mouth at z=5.
const char* kBank =
    "P2_ATTACHMENTS_1 3 1\n"
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
    "0 0 5 0 0 0 1 1 1 1\n";

std::shared_ptr<const p2attach::Bank> readBank(const char* text)
{
    std::istringstream input(text);
    auto bank = p2attach::read(input);
    assert(bank && p2attach::checked(*bank));
    return bank;
}

P2KabutoCannonConfig config() { return P2KabutoCannonConfig{0.0f, 10.0f}; }

P2KabutoHostState idleHost()
{
    return P2KabutoHostState{false, false, false, 0.0f, 10.0f};
}

// Feeds each event to the FSM in order; records whether FireStone was reached.
struct FeedResult {
    int key2 = 0;
    int end = 0;
    bool fired = false;
};

FeedResult feed(P2KabutoCannon& cannon, const P2KabutoEvent* events, int count)
{
    FeedResult result;
    const P2KabutoHostState host = idleHost();
    for (int i = 0; i < count; ++i) {
        const P2KabutoAction action = cannon.onEvent(events[i], host);
        if (events[i] == P2KabutoEvent::Key2) {
            ++result.key2;
        }
        if (events[i] == P2KabutoEvent::End) {
            ++result.end;
        }
        if (action == P2KabutoAction::FireStone) {
            result.fired = true;
        }
    }
    return result;
}

void testSourceFrameAndBirth()
{
    auto bank = readBank(kBank);
    P2KabutoMuzzle muzzle;
    assert(muzzle.bind(*bank, P2KabutoSpecies::Kabuto));
    p2attach::Instance instance;
    const p2attach::Token token = instance.bind(bank);

    P2KabutoCannon cannon;
    cannon.reset(config(), P2KabutoSpecies::Kabuto);
    assert(cannon.start() && cannon.beginAttack());

    P2KabutoEventAdapter adapter;
    assert(adapter.begin(p2_kabuto_attack_clip(51, 50, "attack", "key2")));

    P2KabutoEvent events[4];
    int count = 0;
    assert(adapter.advance(49.0, events, 4, count));
    assert(count == 0);
    assert(cannon.phase() == P2KabutoPhase::Attack);

    assert(adapter.advance(1.0, events, 4, count)); // crosses frame 50
    assert(count == 1 && events[0] == P2KabutoEvent::Key2);
    const FeedResult fired = feed(cannon, events, count);
    assert(fired.fired && fired.key2 == 1 && !fired.end);
    assert(cannon.hasPendingBirth());

    P2KabutoStoneBirth birth;
    assert(muzzle.takeBirth(cannon, instance, token, p2attach::Affine{}, 1, 0.0f, birth));
    assert(birth.valid && !birth.homing);
    assert(near(birth.mouthPosition.x, 10.0f) && near(birth.mouthPosition.y, 25.0f)
           && near(birth.mouthPosition.z, 5.0f));
    assert(!cannon.hasPendingBirth());

    assert(adapter.advance(1.0, events, 4, count)); // reaches the one-shot end
    assert(count == 1 && events[0] == P2KabutoEvent::End);
    feed(cannon, events, count);
    assert(cannon.phase() == P2KabutoPhase::Wait);
}

void testFrameSkipYieldsSameEventCount()
{
    auto bank = readBank(kBank);
    P2KabutoMuzzle muzzle;
    assert(muzzle.bind(*bank, P2KabutoSpecies::Rkabuto));
    p2attach::Instance instance;
    const p2attach::Token token = instance.bind(bank);

    P2KabutoCannon cannon;
    cannon.reset(config(), P2KabutoSpecies::Rkabuto);
    assert(cannon.start() && cannon.beginAttack());
    P2KabutoEventAdapter adapter;
    assert(adapter.begin(p2_kabuto_attack_clip(51, 50, "attack", "key2")));

    // A single big advance must still deliver exactly one Key2 then one End.
    P2KabutoEvent events[4];
    int count = 0;
    assert(adapter.advance(1000.0, events, 4, count));
    assert(count == 2 && events[0] == P2KabutoEvent::Key2 && events[1] == P2KabutoEvent::End);
    const FeedResult result = feed(cannon, events, count);
    assert(result.key2 == 1 && result.end == 1 && result.fired);

    P2KabutoStoneBirth birth;
    assert(muzzle.takeBirth(cannon, instance, token, p2attach::Affine{}, 1, 0.0f, birth));
    assert(birth.valid && birth.homing);
}

void testPauseSuppressesEvents()
{
    P2KabutoEventAdapter adapter;
    assert(adapter.begin(p2_kabuto_attack_clip(51, 50, "attack", "key2")));
    P2KabutoEvent events[4];
    int count = 0;
    adapter.pause(true);
    assert(adapter.advance(100.0, events, 4, count));
    assert(count == 0 && !adapter.finished());
    adapter.pause(false);
    assert(adapter.advance(50.0, events, 4, count)); // resumes from frame 0
    assert(count == 1 && events[0] == P2KabutoEvent::Key2);
}

void testEventsFailClosed()
{
    P2KabutoEventAdapter adapter;
    // Duration below the fire frame yields an invalid clip.
    assert(!adapter.begin(p2_kabuto_attack_clip(40, 50, "attack", "key2")));
    assert(!adapter.active());
    // An empty key is rejected.
    assert(!adapter.begin(p2_kabuto_attack_clip(51, 50, "attack", "key2"), ""));
    assert(!adapter.active());

    // Capacity smaller than the batch is refused so no event is silently dropped.
    assert(adapter.begin(p2_kabuto_attack_clip(51, 50, "attack", "key2")));
    P2KabutoEvent single[1];
    int count = 0;
    assert(!adapter.advance(1000.0, single, 1, count));
}

} // namespace

int main()
{
    testSourceFrameAndBirth();
    testFrameSkipYieldsSameEventCount();
    testPauseSuppressesEvents();
    testEventsFailClosed();
    std::puts("p2_kabuto_chain_test PASS");
    return 0;
}
