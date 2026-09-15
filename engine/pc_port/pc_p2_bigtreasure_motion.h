#pragma once

#include "pc_p2_motion_events.h"

// Lane-owned loader for the BigTreasure P2_RETAIL_EVENTS_1 motion table
// (experimental/pikmin2_bigtreasure_motion.py), consumed through the
// vendored, verified retail event player (#257/#259; provenance in
// docs/PIKMIN2_BIGTREASURE_CONVERSION.md). Engine-free.

struct P2BigTreasureMotionBank {
    p2retail::Table table;
    bool loaded = false;
};

// Reads and validates the table: the vendored reader enforces format,
// ordering, loop pairing and per-clip bounds; this loader additionally
// requires exactly the 29 unique BigTreasure clips (the 30-slot registry
// registers wait2.bca twice; the table keys the loop-carrying variant).
bool p2_bigtreasure_motion_load(const char* path, P2BigTreasureMotionBank& bank);

const p2retail::Motion* p2_bigtreasure_motion_find(const P2BigTreasureMotionBank& bank,
                                                   const char* name);
