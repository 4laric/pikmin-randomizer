// Pinned NARI stage rows (#769). See the header for provenance.
#include "pc_p2_challenge_nari_stages.h"

namespace p2challenge {
namespace nari {

const NariStageRow kNariStages[2] = {
    {"ch_NARI_02tile", 4, 19, 2, {200.0f, 150.0f, 0, 0, 0, 0, 0, 0},
     {{0, 0, 50}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0},
      {0, 0, 0}, {0, 0, 0}}, 0, 5},
    {"ch_NARI_03toy", 5, 2, 2, {100.0f, 150.0f, 0, 0, 0, 0, 0, 0},
     {{0, 0, 0}, {0, 0, 0}, {0, 0, 100}, {0, 0, 0}, {0, 0, 0},
      {0, 0, 0}, {0, 0, 0}}, 2, 2},
};

int selectNariByUiIndex(int uiIndex)
{
    for (int i = 0; i < kNariStageCount; ++i) {
        if (kNariStages[i].uiIndex == uiIndex) return i;
    }
    return -1;
}

int bootPopTotal(const NariStageRow& row)
{
    int total = 0;
    for (int c = 0; c < 7; ++c)
        for (int m = 0; m < 3; ++m) total += row.roster[c][m];
    return total;
}

} // namespace nari
} // namespace p2challenge
