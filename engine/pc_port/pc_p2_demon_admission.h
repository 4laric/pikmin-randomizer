#pragma once
#include "Navi.h"
#include "NaviState.h"
#include <cstdlib>
#include <cstring>

// Lane 30 / #242. Shared captain-semantics change submitted for #186 and
// lane-12 (#130) review: retail P2 Snitchbugs (Swooping `Sarai` ID 23 / Bumbling
// `Demon` ID 32) target a captain independently of the captain's neutral
// locomotion state. The grab lands while the captain is idling (`NaviStateWait`)
// as well as while walking, and the mouth-stick relation is kept across both.
//
// The historical P1 bridge admitted capture only from NAVISTATE_Walk and
// detached ownership as soon as the captain left Walk, so every natural fixture
// had to hold the captain in Walk artificially and could not exercise an idling
// target.
//
// This is a deny-by-default allowlist: only these states make a captain a valid
// mouth-stick owner/capture target.
//   NAVISTATE_Walk (0)  - ordinary ground locomotion.
//   NAVISTATE_Idle (17) - the neutral/wait state retail P2 grabs from.
//
// Every other NaviState owns control, animation, damage, impulse, UI or life
// semantics that a captor must not pre-empt, so it is rejected explicitly:
//   Throw(1)/ThrowWait(2)/Pick(16)  - held/aimed Pikmin contract is live.
//   Gather(3)/Release(4)            - issuing/releasing a Pikmin command.
//   Nuku(5)/NukuAdjust(6)           - plucking Pikmin from the ground.
//   Pressed(7)/Flick(8)             - own damage/impulse state (invincible).
//   Rope(10)/RopeExit(11)           - rope/climb control (also `mRope`).
//   Container(12)                   - Onion/container UI (invincible).
//   Ufo(13)/UfoAccess(14)/PartsAccess(15) - ship interaction (invincible).
//   Stuck(18)                       - Puffmin-stuck/stunned.
//   Bury(19)/Geyzer(20)             - buried/launched (invincible, own motion).
//   DemoWait(21)/DemoInf(22)/Starting(23)/DemoSunset(25) - scene owns control.
//   Pellet(24)/Sow(26)/Clear(34)/IroIro(35) - special scripted states.
//   Water(27)                       - separate aquatic semantics.
//   Attack(28)                      - melee action in progress.
//   Dead(29)                        - not a live target.
//   Push(30)/PushPiki(31)/Lock(32)  - wall/push/locked control.
//   PikiZero(33)                    - game-over countdown.
//   DemonDrop(36)/DemonEscape(37)   - already in a receiver; no re-admission.
inline bool pc_demon_admission_walk_only()
{
    // A/B toggle for the same binary. Set PIKMIN_DEMON_WALK_ONLY_ADMISSION=1 to
    // restore the historical Walk-only gate; default is the source-backed set.
    static const bool walkOnly = [] {
        const char* value = std::getenv("PIKMIN_DEMON_WALK_ONLY_ADMISSION");
        return value && std::strcmp(value, "1") == 0;
    }();
    return walkOnly;
}

inline bool pc_demon_captain_admission_eligible(Navi* n)
{
    if (!n || !n->mStateMachine) return false;
    auto* current = n->getCurrState();
    if (!current) return false;
    const int id = current->getID();
    if (pc_demon_admission_walk_only()) return id == NAVISTATE_Walk;
    switch (id) {
    case NAVISTATE_Walk:
    case NAVISTATE_Idle:
        return true;
    default:
        return false;
    }
}
