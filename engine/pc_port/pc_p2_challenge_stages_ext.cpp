#include "pc_p2_challenge_stages_ext.h"

#include <cstring>

// Pinned rows (#730). Source: docs/PIKMIN_CONTENT_IMPORT_LANES.json lane
// entries p2-challenge-ch_abem_leafchappy (issue #550) and
// p2-challenge-ch_nari_02tile (issue #537); cross-checked against the family
// issue evidence (#550: UI 17, 2 floors, 85/100s, legacy 400s, 30 leaf
// Pikmin as 10/10/10, sprays 1/1, treasure 11, sha 49cc9076...;
// #537: UI 4, 2 floors, 200/150s, roster 50 leaf, sprays 0/5, sha d047060c...).
static const P2ChallengeStageExtRow kP2ChallengeStagesExt[] = {
    { "ch_ABEM_LeafChappy",
      "user/Mukki/mapunits/caveinfo/ch_ABEM_LeafChappy.txt",
      "49cc9076cede949786025b3bcd08ce60362096d8fe8f8b5330c725de4acd2baf",
      17, 4, 2,
      { 85.0f, 100.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f },
      { {10,0,0}, {10,0,0}, {10,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0} },
      1, 1, 400.0f, 11 },
    { "ch_NARI_02tile",
      "user/Mukki/mapunits/caveinfo/ch_NARI_02tile.txt",
      "d047060c7965e501d23b23e2850b5f58e327d40b452d70710149ea4b41479ea6",
      4, 19, 2,
      { 200.0f, 150.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f },
      { {0,0,50}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0} },
      0, 5, 0.0f, 0 },
};

std::size_t pc_p2_challenge_stages_ext_count() {
    return sizeof(kP2ChallengeStagesExt) / sizeof(kP2ChallengeStagesExt[0]);
}

const P2ChallengeStageExtRow* pc_p2_challenge_stages_ext_lookup(const char* caveId) {
    if (caveId == nullptr) return nullptr;
    for (std::size_t i = 0; i < pc_p2_challenge_stages_ext_count(); ++i)
        if (!std::strcmp(kP2ChallengeStagesExt[i].caveId, caveId)) return &kP2ChallengeStagesExt[i];
    return nullptr;
}
