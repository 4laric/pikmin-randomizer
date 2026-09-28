// Lane 48 (#486, cave wave #468): engine-facing real Candypop bud actor.
//
// Instantiates one actor per seeded ``kind=="bud"`` node in the live lane-44
// cave layout, then runs the ordinary throw/convert path: an airborne Pikmin
// inside the source slot radius (p2pom::SlotRadius, lane 23) is consumed and the
// bud births a real PikiHeadItem of the bud's colour, which is completed through
// the ordinary pluck (PikiHeadItem::interactBikkuri). No staged recolour or forced
// species write: the resulting live Pikmin gives the squad its colour key.
#pragma once

#include "Vector.h"

// True when at least one seeded bud actor was instantiated this run.
bool pc_p2_cave_bud_active();

// Number of seeded bud actors (0 when inactive).
int pc_p2_cave_bud_count();

void pc_p2_cave_bud_setup();
void pc_p2_cave_bud_shutdown();
void pc_p2_cave_bud_tick();

// Completed ordinary conversions (a live Pikmin was born from a bud).
int pc_p2_cave_bud_conversions();

// World position of the first actor of a colour ("yellow"/"blue"/...).
bool pc_p2_cave_bud_position(const char* colour, Vector3f& out);
