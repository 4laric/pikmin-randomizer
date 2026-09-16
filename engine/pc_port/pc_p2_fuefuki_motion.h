#pragma once

#include "pc_p2_motion_events.h"

// Lane-owned loader for the Fuefuki P2_RETAIL_EVENTS_1 motion table
// (experimental/pikmin2_fuefuki_motion.py), consumed through the vendored,
// verified retail event player (pc_p2_retail_player.h). Engine-free. The lane
// FSM needs the authored KEYEVENT_2/3 and clip completion to advance; this
// table is the host feed until the source Beetle animation bank (#128) lands.

struct P2FuefukiMotionBank {
    p2retail::Table table;
    bool loaded = false;
};

// Reads and validates the table; requires exactly the 10 FUEFUKIANIM clips.
bool p2_fuefuki_motion_load(const char* path, P2FuefukiMotionBank& bank);

// Finds a motion by clip stem (e.g. "whisle" -> whisle.bca), or null.
const p2retail::Motion* p2_fuefuki_motion_find(const P2FuefukiMotionBank& bank,
                                               const char* name);

// Lane FSM state -> motion clip stem for the *event feed*. Unlike the visual
// mapping (which has no landing geometry) this uses landing/landfail, so the
// Land state receives its authored KEYEVENT_2/3 and END.
const char* p2_fuefuki_motion_clip_for_state(int state);
