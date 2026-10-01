// World position of the Jellyfloat `suck` collision part (joint 4, "Proom",
// enemycoll.txt: radius 15 on Kurage, 25 on OniKurage, offset 0) in the pose the
// port actually draws (#960, owner playtest 2026-09-30: "olimar and the pikmin
// aren't really sucked up high enough into the body").
//
// The source pulls Pikmin toward, and hangs the captain from, that joint
// (Kurage.cpp suckPikmin: suckVec = part->mPosition - pikiPos;
// OniKurage.cpp suckNavi/updateCollPartOffset: slot offset relative to Proom).
// The first port cut used the body origin (the bell underside) minus the part
// radius, which is 15-60 units below where the joint is.
//
// The port draws one static baked pose per source motion, so the joint is
// tabulated per pose. Values are `Proom` world translations computed from the
// retail enemy.bmd skeleton and the retail BCA clip at the frame the pose was
// baked (scripts/kurage_proom_offsets.py regenerates this table from a staged
// content root): model units, origin = actor position, yaw 0, scale 1.
#pragma once

#include "pc_p2_kurage_fsm.h"

#include <cstring>

namespace p2kurageown {

struct ProomOffset { float x, y, z; };

struct ProomRow { const char* pose; ProomOffset lesser; ProomOffset greater; };

// pose names match poseFor(): dead1 dead2 flick1 flick2 wait move1 move2 type1 type2 attack
inline const ProomRow* proomTable(int& count)
{
    static const ProomRow kRows[] = {
        {"dead1",  {0.0f, 27.3f, 0.0f},  {0.0f, 41.4f, 0.0f}},
        {"dead2",  {0.0f, 19.3f, 1.7f},  {0.0f, 29.3f, 2.6f}},
        {"flick1", {0.0f, 28.1f, 0.0f},  {0.0f, 42.6f, 0.0f}},
        {"flick2", {-0.3f, 31.9f, -0.6f}, {-0.4f, 48.3f, -0.9f}},
        {"wait",   {0.0f, 11.2f, 0.7f},  {0.0f, 17.0f, 1.1f}},
        {"move1",  {0.0f, 27.3f, 0.0f},  {0.0f, 41.4f, 0.0f}},
        {"move2",  {0.0f, 27.3f, 0.0f},  {0.0f, 41.4f, 0.0f}},
        {"type1",  {0.0f, 11.2f, 0.7f},  {0.0f, 17.0f, 1.1f}},
        {"type2",  {0.0f, 27.3f, 0.0f},  {0.0f, 41.4f, 0.0f}},
        {"attack", {0.0f, 6.1f, 0.0f},   {0.0f, 9.2f, 0.0f}},
    };
    count = int(sizeof(kRows) / sizeof(kRows[0]));
    return kRows;
}

// `pose` null or unknown falls back to the move1 row (the flying idle pose).
inline ProomOffset proomOffset(p2kurage::Variant variant, const char* pose)
{
    int count = 0;
    const ProomRow* rows = proomTable(count);
    const ProomRow* pick = nullptr;
    const ProomRow* fallback = nullptr;
    for (int i = 0; i < count; ++i) {
        if (std::strcmp(rows[i].pose, "move1") == 0) fallback = &rows[i];
        if (pose && std::strcmp(rows[i].pose, pose) == 0) pick = &rows[i];
    }
    if (!pick) pick = fallback;
    return variant == p2kurage::Variant::Greater ? pick->greater : pick->lesser;
}

// Port adaptation for the captain (OniKurage only). The source rests the
// captain at Proom + (+-7.5, -20, 0) in the joint frame while the attack clip
// lifts Proom from ~9 to ~70 units, so the captain ends up inside the bell. The
// port draws the squashed frame-37 pose for the whole attack, so the joint stays
// near 9 and the same -20 would leave the captain hanging under the bell (owner
// playtest 2026-09-30; measured: the feet rested 2 units under the origin). The
// lift cancels the source's -20 so the captain's feet rest on the Proom joint,
// as a held Pikmin's do, and the captain stands inside the bell.
constexpr float kCaptainHoldLift = 20.0f;

} // namespace p2kurageown
