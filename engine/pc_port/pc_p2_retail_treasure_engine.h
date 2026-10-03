#pragma once
#include "pc_p2_retail_cave_context.h"
// Strong selected-session/context guard only. Does not authenticate a floor
// transaction, admit resources, authorize absent cargo or credit a receipt.
bool pc_p2_retail_treasure_session_matches(const p2retail::SceneIdentity&);
