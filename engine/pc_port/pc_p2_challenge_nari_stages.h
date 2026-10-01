#pragma once
// Pinned NARI 02tile + 03toy stage rows for the P1 boots (#769).
//
// Consumed by the blocked P1 lanes p2-challenge-ch-nari-02tile-p1 (#537) and
// p2-challenge-ch-nari-03toy-p1 (#746). Rows are decoded live from the retail
// stage table (never invented) and cross-checked against the P0 catalogue
// pins before commit:
// - ch_NARI_02tile: #705 landing adapter record (ui 4, order 19, 2 floors
//   200.0 + 150.0 s, bitter 0 / spicy 5, row 0 = 50 leaf red; source
//   d047060c...1479ea).
// - ch_NARI_03toy: #743 gap record (ui 5, order 2, 2 floors 100.0 + 150.0 s,
//   bitter 2 / spicy 2, row 2 = 100 flower blue; source d74b49ac...841f03c).
// Self-contained row struct (this base predates the shared #651 host-mode
// module, so no engine semantics are borrowed or duplicated); the
// single-writer integrator maps these rows onto the shared table.
// SERIALIZED: pc_bbft.cpp / CMakeLists.txt integration is an explicit
// follow-on requiring #186 review; this header changes no shared target.
namespace p2challenge {
namespace nari {

// One pinned stage row. Roster is the 7x3 native color/maturity matrix;
// boot pops equal the roster sum (02tile 50, 03toy 100).
struct NariStageRow {
    const char* caveId;
    int uiIndex;
    int tableOrder;
    int floorCount;
    float floorSeconds[8];
    int roster[7][3];
    int bitterSprays;
    int spicySprays;
};

extern const NariStageRow kNariStages[2];
constexpr int kNariStageCount = 2;

// Lookup by ui_index; returns index into kNariStages or -1 when absent.
int selectNariByUiIndex(int uiIndex);

// Total boot pops for a row (roster sum; 02tile 50, 03toy 100).
int bootPopTotal(const NariStageRow& row);

} // namespace nari
} // namespace p2challenge
