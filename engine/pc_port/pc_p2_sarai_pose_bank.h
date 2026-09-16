#pragma once
// Generic alias onto the shared sampled-pose bank format. Sarai (enemy ID 23)
// reuses the P2_DEMON_POSES_2 / P2_DEMON_MOUTHS_1 text bank unchanged; only the
// local type names differ so the Sarai host reads without demon-specific names.
#include "pc_p2_demon_pose_bank.h"

using P2SaraiMouthFrame = P2DemonMouthFrame;
using P2SaraiPoseBank = P2DemonPoseBank;
