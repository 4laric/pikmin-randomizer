#include "pc_p2_challenge_damagumo_stage.h"

#include <cstring>

namespace {

// Pinned from #740 source (lane p2-challenge-ch_muki_damagumo, issue #538):
// user/Mukki/mapunits/caveinfo/ch_MUKI_damagumo.txt, 1 floor, floor 150 s,
// roster row 2 (native color 2) leaf 50, bitter 0 / spicy 1, legacy 0.0,
// treasure-count field 0, ui 6, table order 9.
const P2DamagumoStageRow kRow = {
    "ch_MUKI_damagumo",
    "user/Mukki/mapunits/caveinfo/ch_MUKI_damagumo.txt",
    "c6f2dede22acb37cb0d939b1ee9670b103dc9408d3c9fe100000482891fefa9e",
    6, 9, 1,
    { 150.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f },
    { {0,0,0}, {0,0,0}, {0,0,50}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0} },
    0, 1, 0.0f, 0,
};

} // namespace

const P2DamagumoStageRow& p2_damagumo_stage_row()
{
    return kRow;
}

const P2DamagumoStageRow* p2_damagumo_stage_lookup(const char* caveId)
{
    if (caveId == nullptr) return nullptr;
    if (!std::strcmp(caveId, kRow.caveId)) return &kRow;
    return nullptr;
}
