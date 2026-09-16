// Standalone engine-free fixture for the BigTreasure motion table loader
// (pc_port/pc_p2_bigtreasure_motion.h/.cpp over the vendored retail table
// reader/player), issue #246. Build (MinGW):
//   g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_bigtreasure_motion_test.cpp pc_port/pc_p2_bigtreasure_motion.cpp -o <private-output>/p2_bigtreasure_motion_test.exe

#include "pc_p2_bigtreasure_motion.h"
#include "pc_p2_retail_player.h"

// Release builds pass -DNDEBUG; force assertions (and their embedded
// side effects) on so this engine-free gate is not vacuous under ctest.
#undef NDEBUG
#include <cassert>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

namespace {
const char* kClips[] = {
    "appear", "appear2", "wait1", "preattackf", "attackf", "attackendf",
    "preattackfr", "attackfr", "attackendfr", "preattackfl", "attackfl",
    "attackendfl", "preattackfb", "attackfb", "attackendfb", "preattackw",
    "attackw", "attackendw", "preattackg", "attackg", "attackendg",
    "preattacke", "attacke", "attackende", "dropitem", "wait2", "flick",
    "dead", "move1",
};

std::string hash64(char fill)
{
    return std::string(64, fill);
}

void writeTable(const char* path, bool omitDead = false, bool badEvent = false)
{
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    int count = omitDead ? 28 : 29;
    out << "P2_RETAIL_EVENTS_1 " << hash64('a') << ' ' << count << '\n';
    for (const char* clip : kClips) {
        if (omitDead && std::string(clip) == "dead") {
            continue;
        }
        int duration = 90;
        out << clip << ".bca " << duration << " 2 " << hash64('b') << ' ';
        if (std::string(clip) == "wait1" || std::string(clip) == "wait2") {
            out << "2\n0 0\n89 1\n";
        } else if (std::string(clip) == "dead") {
            out << (badEvent ? "2\n60 2\n95 100\n" : "2\n60 2\n89 100\n");
        } else {
            out << "0\n";
        }
    }
}

const char* kPath = "p2_bigtreasure_motion_test_table.txt";

void testLoadValidate()
{
    writeTable(kPath);
    P2BigTreasureMotionBank bank;
    assert(p2_bigtreasure_motion_load(kPath, bank));
    assert(bank.loaded && bank.table.motions.size() == 29);
    const p2retail::Motion* wait1 = p2_bigtreasure_motion_find(bank, "wait1");
    assert(wait1 && wait1->duration == 90 && wait1->events.size() == 2);
    const p2retail::Motion* dead = p2_bigtreasure_motion_find(bank, "dead");
    assert(dead && dead->events.back().frame == 89 && dead->events.back().type == 100);
    assert(p2_bigtreasure_motion_find(bank, "nonexistent") == nullptr);
    assert(!p2_bigtreasure_motion_load(nullptr, bank));
    assert(!p2_bigtreasure_motion_load("p2_bigtreasure_motion_missing.txt", bank));
    std::puts("PASS motion_load");
}

void testRejections()
{
    P2BigTreasureMotionBank bank;
    writeTable(kPath, true); // missing dead.bca
    assert(!p2_bigtreasure_motion_load(kPath, bank));
    writeTable(kPath, false, true); // event frame 95 >= duration 90
    assert(!p2_bigtreasure_motion_load(kPath, bank));
    {
        std::ofstream out(kPath, std::ios::binary | std::ios::trunc);
        out << "P2_GROINK_EVENTS_1 " << hash64('a') << " 29\n";
    }
    assert(!p2_bigtreasure_motion_load(kPath, bank));
    std::puts("PASS motion_rejected");
}

void testRetailPlayback()
{
    writeTable(kPath);
    P2BigTreasureMotionBank bank;
    assert(p2_bigtreasure_motion_load(kPath, bank));
    // Loop semantics: wait1 loops at (89,1) back to the (0,0) loop start;
    // overshoot is discarded (retail Player contract).
    p2retail::Player player;
    assert(player.start(*p2_bigtreasure_motion_find(bank, "wait1")));
    std::vector<std::pair<int, int>> events;
    int guard = 0;
    while (events.size() < 6 && guard++ < 400) {
        player.advance(1.0f, [&](const p2retail::Event& event) {
            events.emplace_back(event.frame, event.type);
        });
    }
    assert(events.size() >= 6);
    assert((events[0] == std::pair<int, int>{0, 0}));
    assert((events[1] == std::pair<int, int>{89, 1}));
    assert((events[2] == std::pair<int, int>{0, 0})); // loop restart re-fires
    assert((events[3] == std::pair<int, int>{89, 1}));
    assert(!player.completed()); // loops never complete

    // One-shot clip completes with the implicit type-1000 event.
    assert(player.start(*p2_bigtreasure_motion_find(bank, "dead")));
    events.clear();
    guard = 0;
    while (!player.completed() && guard++ < 400) {
        player.advance(1.0f, [&](const p2retail::Event& event) {
            events.emplace_back(event.frame, event.type);
        });
    }
    assert(player.completed());
    assert(!events.empty() && events.back().second == 1000);
    assert((events.front() == std::pair<int, int>{60, 2}));
    assert((events[1] == std::pair<int, int>{89, 100})); // KEYEVENT_100 anchor type
    std::puts("PASS motion_playback");
}
} // namespace

int main()
{
    testLoadValidate();
    testRejections();
    testRetailPlayback();
    std::remove(kPath);
    std::puts("PASS BIGTREASURE_MOTION");
    return 0;
}
