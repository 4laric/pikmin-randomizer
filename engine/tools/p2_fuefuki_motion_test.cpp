// Standalone fixture for the Fuefuki motion event bank loader and FSM clip
// mapping (#245). Engine-free: builds a synthetic P2_RETAIL_EVENTS_1 table and
// checks the loader plus p2_fuefuki_motion_clip_for_state.
//   g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_fuefuki_motion_test.cpp pc_port/pc_p2_fuefuki_motion.cpp -o ../p2_fuefuki_motion_test.exe
#include "pc_p2_fuefuki_motion.h"

#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>

namespace {
int gFailures = 0;

void check(bool cond, const char* what)
{
    if (!cond) {
        std::printf("FAIL: %s\n", what);
        gFailures++;
    }
}

const char* kClips[10] = { "dead", "landing", "landfail", "move", "pivot",
                           "wait", "whisle", "struggle", "jump", "carry" };

std::string makeTable(int count)
{
    std::string text = "P2_RETAIL_EVENTS_1 " + std::string(64, 'a') + " " + std::to_string(count) + "\n";
    for (int i = 0; i < count && i < 10; ++i) {
        text += std::string(kClips[i]) + ".bca 30 2 " + std::string(64, 'b') + " 2\n";
        text += "4 0\n29 1\n";
    }
    return text;
}

bool writeText(const char* path, const std::string& text)
{
    std::ofstream out(path, std::ios::binary);
    if (!out) return false;
    out.write(text.data(), static_cast<std::streamsize>(text.size()));
    return bool(out);
}

void testClipMapping()
{
    check(std::strcmp(p2_fuefuki_motion_clip_for_state(0), "dead") == 0, "state 0 -> dead");
    check(std::strcmp(p2_fuefuki_motion_clip_for_state(1), "jump") == 0, "state 1 -> jump");
    check(std::strcmp(p2_fuefuki_motion_clip_for_state(2), "landing") == 0, "state 2 -> landing");
    check(std::strcmp(p2_fuefuki_motion_clip_for_state(3), "jump") == 0, "state 3 -> jump");
    check(std::strcmp(p2_fuefuki_motion_clip_for_state(4), "wait") == 0, "state 4 -> wait");
    check(std::strcmp(p2_fuefuki_motion_clip_for_state(5), "pivot") == 0, "state 5 -> pivot");
    check(std::strcmp(p2_fuefuki_motion_clip_for_state(6), "move") == 0, "state 6 -> move");
    check(std::strcmp(p2_fuefuki_motion_clip_for_state(7), "whisle") == 0, "state 7 -> whisle");
    check(std::strcmp(p2_fuefuki_motion_clip_for_state(8), "struggle") == 0, "state 8 -> struggle");
    check(std::strcmp(p2_fuefuki_motion_clip_for_state(99), "wait") == 0, "unknown -> wait");
}

void testLoadAndFind()
{
    const char* path = "p2_fuefuki_motion_test.tmp";
    check(writeText(path, makeTable(10)), "write table");
    P2FuefukiMotionBank bank;
    check(p2_fuefuki_motion_load(path, bank), "load 10-clip table");
    check(bank.loaded, "bank loaded flag");
    check(bank.table.motions.size() == 10, "10 motions");
    const p2retail::Motion* wait = p2_fuefuki_motion_find(bank, "wait");
    check(wait != nullptr, "find wait");
    check(wait && wait->duration == 30 && wait->events.size() == 2, "wait duration/events");
    const p2retail::Motion* landing = p2_fuefuki_motion_find(bank, "landing");
    check(landing != nullptr, "find landing");
    check(p2_fuefuki_motion_find(bank, "nope") == nullptr, "unknown clip null");
    std::remove(path);
}

void testRejectWrongCount()
{
    const char* path = "p2_fuefuki_motion_test_bad.tmp";
    check(writeText(path, makeTable(9)), "write bad table");
    P2FuefukiMotionBank bank;
    check(!p2_fuefuki_motion_load(path, bank), "reject wrong clip count");
    check(!bank.loaded, "rejected bank not loaded");
    std::remove(path);
}
} // namespace

int main()
{
    testClipMapping();
    testLoadAndFind();
    testRejectWrongCount();
    if (gFailures == 0) {
        std::printf("PASS p2_fuefuki_motion_test\n");
        return 0;
    }
    std::printf("FAILURES: %d\n", gFailures);
    return 1;
}
