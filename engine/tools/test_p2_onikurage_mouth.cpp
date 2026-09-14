// Isolated fixtures for pc_p2_onikurage_mouth.h (OniKurage captain mouth slots).
// Build: g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/test_p2_onikurage_mouth.cpp pc_port/pc_p2_onikurage_mouth.cpp -o test_p2_onikurage_mouth.exe
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include "pc_p2_onikurage_mouth.h"

using namespace p2onikurage;

static int gChecks = 0;
static void require(bool ok, const char* what)
{
    ++gChecks;
    if (!ok) {
        std::printf("FAIL p2_onikurage_mouth_test: %s\n", what);
        std::fflush(stdout);
        std::_Exit(1);
    }
}
static bool near(float a, float b) { return std::fabs(a - b) < 1e-4f; }

int main()
{
    // --- initMouthSlots: two captain slots, empty after reset ---
    {
        MouthSlots slots;
        require(slots.slots().size() == 2, "two configured mouth slots");
        require(slots.occupiedCount() == 0 && !slots.isNaviSucked(), "reset clears slots");
        require(kDefaultKamuJointOffset[0] == 7.5f && kDefaultKamuJointOffset[1] == -7.5f,
            "default kamu joint offsets match source");
    }

    // --- suckNavi: first free slot, then the second, then rejection ---
    {
        MouthSlots slots;
        require(!slots.capture(5, false), "ineligible capture rejected");
        require(slots.capture(5, true), "first captain captures slot 0");
        require(slots.capture(6, true), "second captain captures slot 1");
        require(!slots.capture(7, true), "a third captain finds no free slot");
        require(slots.isNaviSucked() && slots.occupiedCount() == 2, "both captains recorded as sucked");
        require(slots.slots()[0].target == 5 && slots.slots()[1].target == 6, "slot identities preserved");
    }

    // --- updateCollPartOffset settles at the rest pose ---
    {
        MouthSlots slots;
        require(slots.capture(1, true), "capture for rest-pose test");
        slots.setOffset(0, { 40.0f, 10.0f, 20.0f });
        int frames = 0;
        Event event = Event::None;
        while (event != Event::MouthReady && frames < 100) { event = slots.advanceDefaultOffset(0); ++frames; }
        require(event == Event::MouthReady, "offset reaches the default rest pose");
        require(std::fabs(slots.slots()[0].offset.x - 7.5f) < 1.0f, "rest offset x matches cDefaultKamuJointOffset");
        require(std::fabs(slots.slots()[0].offset.y + 20.0f) < 1.0f, "rest offset y matches -20");
        require(std::fabs(slots.slots()[0].offset.z) < 1.0f, "rest offset z settles to zero");
        require(slots.isFinishNaviSuck(), "settled mouth reports isFinishNaviSuck");

        MouthSlots moving;
        moving.capture(2, true);
        moving.setOffset(0, { 40.0f, 10.0f, 20.0f });
        require(!moving.isFinishNaviSuck(), "moving mouth is not finished");
    }

    // --- flickStickNavi release: explicit Flick + Bomb branch ---
    {
        MouthSlots slots;
        slots.capture(9, true);
        slots.setOffset(0, { kFlickKamuJointOffset[0], kFlickOffsetY, 0.0f });
        FlickResult result = slots.flick(0, false, 3.0f, 4.0f, 0.0f, 0.0f);
        require(result.applied && result.flick && result.bomb, "flick release applies InteractFlick and InteractBomb");
        require(near(result.dirX, 30.0f) && near(result.dirZ, 40.0f), "bomb separation is normalised * 50");
        require(!slots.slots()[0].occupied, "flicked captain leaves the slot");
        FlickResult again = slots.flick(0, false, 3.0f, 4.0f, 0.0f, 0.0f);
        require(!again.applied, "empty slot cannot be flicked twice");
    }

    // --- flickStickNavi(check) uses the default offset and -75 ---
    {
        MouthSlots slots;
        slots.capture(9, true);
        slots.capture(10, true);
        slots.setOffset(1, { kDefaultKamuJointOffset[1], kCheckOffsetY, 0.0f });
        FlickResult result = slots.flick(1, true, 0.0f, 1.0f, 0.0f, 0.0f);
        require(result.applied && near(result.dirX, 0.0f) && near(result.dirZ, 50.0f),
            "check branch settles at default offset and bombs along z");
    }

    // --- escapeCheckNavi: observed bookkeeping, bitter escalation ---
    {
        MouthSlots slots;
        slots.capture(11, true);
        require(slots.escapeCheck(0, true, false) == Event::None, "held captain keeps the slot observed");
        require(slots.escapeCheck(0, false, false) == Event::EscapeReleased, "non-bitter escape releases the captain");
        require(!slots.slots()[0].observed, "escape clears the source bookkeeping");

        MouthSlots bitter;
        bitter.capture(12, true);
        require(bitter.escapeCheck(0, false, true) == Event::EnemyDied,
            "bittered escape forces enemy health to zero");
    }

    // --- onDeath releases every captured captain ---
    {
        MouthSlots slots;
        slots.capture(1, true);
        slots.capture(2, true);
        require(slots.onDeath() == 2, "death releases both captains");
        require(slots.occupiedCount() == 0, "death clears the mouth slots");
    }

    std::printf("p2_onikurage_mouth_test PASS checks=%d\n", gChecks);
    std::fflush(stdout);
    return 0;
}
