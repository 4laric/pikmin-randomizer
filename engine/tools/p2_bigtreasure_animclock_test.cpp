// Standalone engine-free fixture for the BigTreasure animation keyframe source
// (pc_port/pc_p2_bigtreasure_animclock.h/.cpp), issue #246. Proves the source
// state -> clip mapping, the retail event -> FSM pulse translation, and that
// the clock starts the mapped clip on a phase change and advances it one
// source tick at a time. Build (MinGW):
//   g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_bigtreasure_animclock_test.cpp pc_port/pc_p2_bigtreasure_animclock.cpp pc_port/pc_p2_bigtreasure_motion.cpp -o <private-output>/p2_bigtreasure_animclock_test.exe

#include "pc_p2_bigtreasure_animclock.h"

#include <cassert>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>

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

void writeTable(const char* path)
{
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    out << "P2_RETAIL_EVENTS_1 " << hash64('a') << " 29\n";
    for (const char* clip : kClips) {
        const std::string name(clip);
        int duration = 8;
        if (name == "appear2") duration = 3;
        if (name == "dead") duration = 6;
        out << name << ".bca " << duration << " 2 " << hash64('b');
        if (name == "attacke") {
            out << " 1\n1 2\n";
        } else if (name == "dead") {
            out << " 1\n2 100\n";
        } else {
            out << " 0\n";
        }
    }
}

const char* kPath = "p2_bigtreasure_animclock_test_table.txt";

void testClipMapping()
{
    char buffer[40];
    assert(p2_bigtreasure_anim_clip(P2BT_Stay, -1, buffer, sizeof(buffer))
           && std::strcmp(buffer, "appear") == 0);
    assert(p2_bigtreasure_anim_clip(P2BT_Land, -1, buffer, sizeof(buffer))
           && std::strcmp(buffer, "appear2") == 0);
    assert(p2_bigtreasure_anim_clip(P2BT_Wait, -1, buffer, sizeof(buffer))
           && std::strcmp(buffer, "wait2") == 0);
    assert(p2_bigtreasure_anim_clip(P2BT_ItemWait, -1, buffer, sizeof(buffer))
           && std::strcmp(buffer, "wait1") == 0);
    assert(p2_bigtreasure_anim_clip(P2BT_Flick, -1, buffer, sizeof(buffer))
           && std::strcmp(buffer, "flick") == 0);
    assert(p2_bigtreasure_anim_clip(P2BT_DropItem, -1, buffer, sizeof(buffer))
           && std::strcmp(buffer, "dropitem") == 0);
    assert(p2_bigtreasure_anim_clip(P2BT_Walk, -1, buffer, sizeof(buffer))
           && std::strcmp(buffer, "wait2") == 0);
    assert(p2_bigtreasure_anim_clip(P2BT_ItemWalk, -1, buffer, sizeof(buffer))
           && std::strcmp(buffer, "move1") == 0);
    assert(p2_bigtreasure_anim_clip(P2BT_Dead, -1, buffer, sizeof(buffer))
           && std::strcmp(buffer, "dead") == 0);

    assert(p2_bigtreasure_anim_clip(P2BT_PreAttack, P2BTWEAPON_Elec, buffer, sizeof(buffer))
           && std::strcmp(buffer, "preattacke") == 0);
    assert(p2_bigtreasure_anim_clip(P2BT_PreAttack, P2BTWEAPON_Fire, buffer, sizeof(buffer))
           && std::strcmp(buffer, "preattackf") == 0);
    assert(p2_bigtreasure_anim_clip(P2BT_Attack, P2BTWEAPON_Gas, buffer, sizeof(buffer))
           && std::strcmp(buffer, "attackg") == 0);
    assert(p2_bigtreasure_anim_clip(P2BT_PutItem, P2BTWEAPON_Water, buffer, sizeof(buffer))
           && std::strcmp(buffer, "attackendw") == 0);
    // Unknown weapon index falls back to the forward fire variant.
    assert(p2_bigtreasure_anim_clip(P2BT_Attack, 99, buffer, sizeof(buffer))
           && std::strcmp(buffer, "attackf") == 0);
    // Too-small buffer fails closed.
    assert(!p2_bigtreasure_anim_clip(P2BT_Attack, P2BTWEAPON_Elec, buffer, 4));
    assert(!p2_bigtreasure_anim_clip(P2BT_Attack, P2BTWEAPON_Elec, nullptr, sizeof(buffer)));
    std::puts("PASS animclock_mapping");
}

void testTranslate()
{
    const int all[] = {2, 100, 1000};
    P2BigTreasureAnimPulses pulses;
    p2_bigtreasure_anim_translate(all, 3, pulses);
    assert(pulses.animEnd && pulses.keyEvent2 && pulses.keyEvent100);

    const int none[] = {0, 3, 7};
    pulses = P2BigTreasureAnimPulses{};
    p2_bigtreasure_anim_translate(none, 3, pulses);
    assert(!pulses.animEnd && !pulses.keyEvent2 && !pulses.keyEvent100);

    // The authored loop marker ends the host cycle.
    const int loop[] = {1};
    pulses = P2BigTreasureAnimPulses{};
    p2_bigtreasure_anim_translate(loop, 1, pulses);
    assert(pulses.animEnd);

    pulses = P2BigTreasureAnimPulses{};
    p2_bigtreasure_anim_translate(nullptr, 0, pulses);
    assert(!pulses.animEnd);
    std::puts("PASS animclock_translate");
}

void testClockProgression()
{
    writeTable(kPath);
    P2BigTreasureAnimClock clock;
    assert(clock.load(kPath));
    assert(clock.ready());

    // First tick on a new phase starts the clip; no events that tick.
    P2BigTreasureAnimPulses pulses;
    clock.tick(P2BT_Land, -1, pulses);
    assert(clock.activeClip() && std::strcmp(clock.activeClip(), "appear2") == 0);
    assert(!pulses.animEnd);

    // appear2 is a 3-frame one-shot: it completes and emits animEnd.
    bool ended = false;
    for (int i = 0; i < 8 && !ended; ++i) {
        clock.tick(P2BT_Land, -1, pulses);
        ended = pulses.animEnd;
    }
    assert(ended);

    // Attack for elec: the authored KEYEVENT_2 fires, then completion.
    clock.tick(P2BT_Attack, P2BTWEAPON_Elec, pulses);
    assert(clock.activeClip() && std::strcmp(clock.activeClip(), "attacke") == 0);
    bool key2 = false, end = false;
    for (int i = 0; i < 10 && !(key2 && end); ++i) {
        clock.tick(P2BT_Attack, P2BTWEAPON_Elec, pulses);
        key2 = key2 || pulses.keyEvent2;
        end = end || pulses.animEnd;
    }
    assert(key2 && end);

    // Dead: authored KEYEVENT_100 then completion.
    clock.tick(P2BT_Dead, -1, pulses);
    assert(clock.activeClip() && std::strcmp(clock.activeClip(), "dead") == 0);
    bool key100 = false;
    end = false;
    for (int i = 0; i < 10 && !(key100 && end); ++i) {
        clock.tick(P2BT_Dead, -1, pulses);
        key100 = key100 || pulses.keyEvent100;
        end = end || pulses.animEnd;
    }
    assert(key100 && end);
    std::puts("PASS animclock_progression");
}

void testInactiveAndRestart()
{
    P2BigTreasureAnimClock clock;
    P2BigTreasureAnimPulses pulses;
    clock.tick(P2BT_Land, -1, pulses); // not loaded: no-op
    assert(!clock.ready() && clock.activeClip() == nullptr && !pulses.animEnd);

    writeTable(kPath);
    assert(clock.load(kPath));
    clock.tick(P2BT_Land, -1, pulses);
    clock.tick(P2BT_ItemWalk, -1, pulses);
    assert(std::strcmp(clock.activeClip(), "move1") == 0);

    // A weapon change restarts the weapon-suffixed clip.
    clock.tick(P2BT_PreAttack, P2BTWEAPON_Fire, pulses);
    assert(std::strcmp(clock.activeClip(), "preattackf") == 0);
    clock.tick(P2BT_PreAttack, P2BTWEAPON_Elec, pulses);
    assert(std::strcmp(clock.activeClip(), "preattacke") == 0);
    std::puts("PASS animclock_inactive_restart");
}
} // namespace

int main()
{
    testClipMapping();
    testTranslate();
    testClockProgression();
    testInactiveAndRestart();
    std::remove(kPath);
    std::puts("PASS BIGTREASURE_ANIMCLOCK");
    return 0;
}
