// Lane 30 (#242) exhaustive admission-allowlist test.
//
// Exercises pc_demon_captain_admission_eligible() (pc_port/pc_p2_demon_admission.h)
// over every NaviStateID declared in include/NaviState.h, plus NAVISTATE_NULL and
// out-of-range / negative values. The predicate is the shared captain-semantics
// change submitted for #186 and lane-12 (#130) review.
//
// Expected result:
//   default (PIKMIN_DEMON_WALK_ONLY_ADMISSION unset/other): Walk(0) and Idle(17).
//   toggle  (PIKMIN_DEMON_WALK_ONLY_ADMISSION=1)          : Walk(0) only.
// Every other value, nullptr, and a Navi without a state machine is rejected.
//
// The predicate only reads n->mStateMachine and n->getCurrState()->getID(); it
// does not touch engine state. The test therefore lays out a Navi-shaped buffer
// and points the two relevant public members at a real AState<Navi> whose only
// job is to carry the ID. This links without any engine object and with no GL.
//
// Toggle semantics: pc_demon_admission_walk_only() performs a one-shot getenv()
// into a function-local static, so the value is fixed for the life of a process.
// This binary asserts the mode it was started in and then re-executes itself
// once with PIKMIN_DEMON_WALK_ONLY_ADMISSION=1, so the same executable proves
// both branches. A child guard variable prevents recursion.
//
// Build (PowerShell; PATH has C:\msys64\mingw64\bin first):
//   g++ -std=gnu++17 -Wall -Wextra -Werror -fpermissive -UWIN32 -DPIKI_PC_PORT=1 `
//     -include pc_port/pc_types.h -I pc_port `
//     -isystem include -isystem include/Dolphin -isystem include/Dolphin/OS `
//     -isystem include/Dolphin/GX tools/p2_demon_admission_test.cpp `
//     -o p2_demon_admission_test.exe

#include "pc_p2_demon_admission.h"
#include "NaviState.h"

#include <climits>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <process.h>

namespace {

void require(bool ok, const char* what)
{
    if (!ok) {
        std::printf("p2_demon_admission_test FAIL: %s\n", what);
        std::fflush(stdout);
        std::exit(1);
    }
}

bool envWalkOnly()
{
    const char* value = std::getenv("PIKMIN_DEMON_WALK_ONLY_ADMISSION");
    return value && std::strcmp(value, "1") == 0;
}

struct IdCase {
    int id;
    const char* name;
};

// Every declared NaviStateID, in declaration order, plus NAVISTATE_NULL and
// out-of-range values. NAVISTATE_Count is 38 on the PC port (36 retail).
const IdCase kIds[] = {
    { NAVISTATE_NULL, "NULL" },
    { NAVISTATE_Walk, "Walk" },
    { NAVISTATE_Throw, "Throw" },
    { NAVISTATE_ThrowWait, "ThrowWait" },
    { NAVISTATE_Gather, "Gather" },
    { NAVISTATE_Release, "Release" },
    { NAVISTATE_Nuku, "Nuku" },
    { NAVISTATE_NukuAdjust, "NukuAdjust" },
    { NAVISTATE_Pressed, "Pressed" },
    { NAVISTATE_Flick, "Flick" },
    { NAVISTATE_Funbari, "Funbari" },
    { NAVISTATE_Rope, "Rope" },
    { NAVISTATE_RopeExit, "RopeExit" },
    { NAVISTATE_Container, "Container" },
    { NAVISTATE_Ufo, "Ufo" },
    { NAVISTATE_UfoAccess, "UfoAccess" },
    { NAVISTATE_PartsAccess, "PartsAccess" },
    { NAVISTATE_Pick, "Pick" },
    { NAVISTATE_Idle, "Idle" },
    { NAVISTATE_Stuck, "Stuck" },
    { NAVISTATE_Bury, "Bury" },
    { NAVISTATE_Geyzer, "Geyzer" },
    { NAVISTATE_DemoWait, "DemoWait" },
    { NAVISTATE_DemoInf, "DemoInf" },
    { NAVISTATE_Starting, "Starting" },
    { NAVISTATE_Pellet, "Pellet" },
    { NAVISTATE_DemoSunset, "DemoSunset" },
    { NAVISTATE_Sow, "Sow" },
    { NAVISTATE_Water, "Water" },
    { NAVISTATE_Attack, "Attack" },
    { NAVISTATE_Dead, "Dead" },
    { NAVISTATE_Push, "Push" },
    { NAVISTATE_PushPiki, "PushPiki" },
    { NAVISTATE_Lock, "Lock" },
    { NAVISTATE_PikiZero, "PikiZero" },
    { NAVISTATE_Clear, "Clear" },
    { NAVISTATE_IroIro, "IroIro" },
    { NAVISTATE_DemonDrop, "DemonDrop" },
    { NAVISTATE_DemonEscape, "DemonEscape" },
    { NAVISTATE_Count, "Count" },
    { NAVISTATE_Count + 1, "Count+1" },
    { -2, "-2" },
    { 100, "100" },
    { 255, "255" },
    { INT_MIN, "INT_MIN" },
    { INT_MAX, "INT_MAX" },
};

bool expected(bool walkOnly, int id)
{
    if (walkOnly) {
        return id == NAVISTATE_Walk;
    }
    return id == NAVISTATE_Walk || id == NAVISTATE_Idle;
}

int runChecks(bool walkOnly)
{
    require(pc_demon_admission_walk_only() == walkOnly, "toggle value does not match process environment");
    require(!pc_demon_captain_admission_eligible(nullptr), "nullptr Navi admitted");

    alignas(Navi) static unsigned char storage[sizeof(Navi)];
    std::memset(storage, 0, sizeof(storage));
    Navi* n = reinterpret_cast<Navi*>(storage);
    n->mStateMachine = reinterpret_cast<NaviStateMachine*>(0x1);

    int checks = 0;
    int eligible = 0;
    for (const IdCase& c : kIds) {
        AState<Navi> state(c.id);
        n->mCurrState = &state;
        const bool got = pc_demon_captain_admission_eligible(n);
        if (got != expected(walkOnly, c.id)) {
            std::printf("p2_demon_admission_test FAIL: id=%d (%s) walkOnly=%d got=%d\n", c.id, c.name, walkOnly ? 1 : 0, got ? 1 : 0);
            std::fflush(stdout);
            std::exit(1);
        }
        if (got) {
            ++eligible;
        }
        ++checks;
    }

    // A Navi with no state machine is rejected before the state ID is read.
    AState<Navi> walk(NAVISTATE_Walk);
    n->mCurrState = &walk;
    n->mStateMachine = nullptr;
    require(!pc_demon_captain_admission_eligible(n), "Navis without a state machine admitted");

    // Exactly the allowlist is eligible: {Walk, Idle} by default, {Walk} with the toggle.
    const int expectedEligible = walkOnly ? 1 : 2;
    require(eligible == expectedEligible, "eligible count does not match the allowlist");
    return checks;
}

} // namespace

int main()
{
    const bool walkOnly = envWalkOnly();
    const int checks = runChecks(walkOnly);
    require(checks > 0, "no state IDs exercised");

    if (walkOnly) {
        std::printf("p2_demon_admission_test PASS mode=walk-only checks=%d\n", checks);
        std::fflush(stdout);
        return 0;
    }

    std::printf("p2_demon_admission_test PASS mode=walk+idle checks=%d\n", checks);

    // Prove the same binary flips to Walk-only when the toggle is set, without
    // relying on the runner to invoke it twice.
    if (std::getenv("P2_DEMON_ADMISSION_SELF") == nullptr) {
        _putenv_s("PIKMIN_DEMON_WALK_ONLY_ADMISSION", "1");
        _putenv_s("P2_DEMON_ADMISSION_SELF", "1");
        const int rc = _spawnl(_P_WAIT, _pgmptr, _pgmptr, static_cast<const char*>(nullptr));
        _putenv_s("PIKMIN_DEMON_WALK_ONLY_ADMISSION", "");
        _putenv_s("P2_DEMON_ADMISSION_SELF", "");
        require(rc == 0, "walk-only child process did not pass");
    }

    std::fflush(stdout);
    return 0;
}
