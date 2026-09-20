// Pinned MUKI stage rows (#748). See the header for provenance.
#include "pc_p2_challenge_muki_stages.h"

namespace p2challenge {
namespace muki {

const StageEntry kMukiStages[2] = {
    {"ch_MUKI_houdai", 8, 2, {100.0f, 150.0f, 0, 0, 0, 0, 0, 0},
     {{0, 0, 10}, {0, 0, 10}, {0, 0, 10}, {0, 0, 10}, {0, 0, 10},
      {0, 0, 0}, {0, 0, 0}}, 1, 1},
    {"ch_MUKI_redblue", 18, 2, {200.0f, 200.0f, 0, 0, 0, 0, 0, 0},
     {{0, 0, 25}, {0, 0, 25}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0},
      {0, 0, 0}, {0, 0, 0}}, 1, 1},
};

int selectMukiByUiIndex(int uiIndex)
{
    return selectByUiIndex(kMukiStages, kMukiStageCount, uiIndex);
}

} // namespace muki
} // namespace p2challenge