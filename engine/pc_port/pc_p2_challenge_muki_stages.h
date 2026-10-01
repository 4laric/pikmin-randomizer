#pragma once
// Pinned MUKI houdai + redblue stage rows for the P1 boots (#748).
//
// Consumed by the blocked P1 lanes p2-challenge-ch-muki-houdai-p1 (#735) and
// p2-challenge-ch-muki-redblue-p1 (#744). Rows are decoded live from the
// retail stage table (never invented) and cross-checked against the P0
// catalogue pins before commit. The table reuses p2challenge::StageEntry from
// the accepted #651 host-mode module, so no engine semantics are duplicated.
// SERIALIZED: pc_bbft.cpp / CMakeLists.txt integration is an explicit
// follow-on requiring #186 review; this header changes no shared target.
#include "pc_p2_challenge_mode.h"

namespace p2challenge {
namespace muki {

// ch_MUKI_houdai (ui 8): 2 floors, 100.0 + 150.0 s, bitter 1 / spicy 1,
// five colours x 10 leaf = 50 (roster rows 0-4, happa Leaf).
// ch_MUKI_redblue (ui 18): 2 floors, 200.0 + 200.0 s, bitter 1 / spicy 1,
// two colours x 25 leaf = 50 (roster rows 0-1, happa Leaf).
extern const StageEntry kMukiStages[2];
constexpr int kMukiStageCount = 2;

// Lookup by ui_index; returns index into kMukiStages or -1 when absent.
int selectMukiByUiIndex(int uiIndex);

} // namespace muki
} // namespace p2challenge