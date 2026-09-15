#include "pc_p2_bigtreasure_animclock.h"

#include <cstdio>
#include <cstring>

namespace {
const char* weaponSuffix(int weapon)
{
    switch (weapon) {
    case P2BTWEAPON_Elec: return "e";
    case P2BTWEAPON_Fire: return "f";
    case P2BTWEAPON_Gas: return "g";
    case P2BTWEAPON_Water: return "w";
    default: return "f";
    }
}
} // namespace

bool p2_bigtreasure_anim_clip(P2BigTreasurePhase phase, int chosenWeapon,
                              char* out, std::size_t capacity)
{
    if (!out || capacity == 0) {
        return false;
    }
    const char* name = nullptr;
    char weapon[32] = {};
    switch (phase) {
    case P2BT_Dead: name = "dead"; break;
    case P2BT_Stay: name = "appear"; break;
    case P2BT_Land: name = "appear2"; break;
    case P2BT_Wait: name = "wait2"; break;
    case P2BT_ItemWait: name = "wait1"; break;
    case P2BT_Flick: name = "flick"; break;
    case P2BT_DropItem: name = "dropitem"; break;
    case P2BT_Walk: name = "wait2"; break; // source anim 29 reuses wait2.bca
    case P2BT_ItemWalk: name = "move1"; break;
    case P2BT_PreAttack:
        std::snprintf(weapon, sizeof(weapon), "preattack%s", weaponSuffix(chosenWeapon));
        name = weapon;
        break;
    case P2BT_Attack:
        std::snprintf(weapon, sizeof(weapon), "attack%s", weaponSuffix(chosenWeapon));
        name = weapon;
        break;
    case P2BT_PutItem:
        std::snprintf(weapon, sizeof(weapon), "attackend%s", weaponSuffix(chosenWeapon));
        name = weapon;
        break;
    default:
        return false;
    }
    if (std::strlen(name) + 1 > capacity) {
        return false;
    }
    std::strcpy(out, name);
    return true;
}

void p2_bigtreasure_anim_translate(const int* types, int count,
                                   P2BigTreasureAnimPulses& out)
{
    for (int i = 0; i < count; ++i) {
        switch (types[i]) {
        case 1000: out.animEnd = true; break;
        case 2: out.keyEvent2 = true; break;
        case 100: out.keyEvent100 = true; break;
        // The authored loop marker is where the host ends the current cycle.
        // The policy's idle states ignore animEnd, so this only finishes the
        // one-shot states (Land / PreAttack / Attack / PutItem / Flick /
        // DropItem / Dead); it mirrors the fixed loop-window the retail
        // event-player fixture stops on.
        case 1: out.animEnd = true; break;
        default: break;
        }
    }
}

bool P2BigTreasureAnimClock::load(const char* eventsPath)
{
    reset();
    return p2_bigtreasure_motion_load(eventsPath, mBank);
}

void P2BigTreasureAnimClock::reset()
{
    mBank = P2BigTreasureMotionBank();
    mPlayer = p2retail::Player();
    mActiveName[0] = '\0';
}

void P2BigTreasureAnimClock::tick(P2BigTreasurePhase phase, int chosenWeapon,
                                  P2BigTreasureAnimPulses& out)
{
    out = P2BigTreasureAnimPulses{};
    if (!mBank.loaded) {
        return;
    }
    char clip[40];
    if (!p2_bigtreasure_anim_clip(phase, chosenWeapon, clip, sizeof(clip))) {
        return;
    }
    if (std::strcmp(mActiveName, clip) != 0) {
        const p2retail::Motion* motion = p2_bigtreasure_motion_find(mBank, clip);
        if (!motion || !mPlayer.start(*motion)) {
            mActiveName[0] = '\0';
            return;
        }
        std::snprintf(mActiveName, sizeof(mActiveName), "%s", clip);
        return; // starting a clip produces no events this tick
    }
    int types[64];
    int count = 0;
    const p2retail::Update result = mPlayer.advance(1.0f, [&](const p2retail::Event& event) {
        if (count < static_cast<int>(sizeof(types) / sizeof(types[0]))) {
            types[count++] = event.type;
        }
    });
    if (result == p2retail::Update::Invalid || result == p2retail::Update::Inactive
        || result == p2retail::Update::Reentrant) {
        return;
    }
    p2_bigtreasure_anim_translate(types, count, out);
}
