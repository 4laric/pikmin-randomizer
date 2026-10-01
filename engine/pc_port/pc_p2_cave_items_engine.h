// Lane 46 (#484): engine-facing API for physical cave-item placement. The
// engine-free parse/validation stays in pc_p2_cave_items.h; this header only
// declares the glue implemented in pc_p2_cave_items.cpp.
#pragma once

#include "pc_p2_cave_items.h"

class Pellet;
class Graphics;
struct Matrix4f;

// True when a P2_CAVE_ITEMS_1 config was loaded, validated against the live
// proxy rooms layout and one real Pellet actor per item was spawned.
bool pc_p2_cave_items_active();

// Opt-in: reads PIKMIN_CAVE_ITEMS (path) or ./p2-cave-items.txt. No-op and no
// output when neither exists, so a normal run is unchanged. Requires an active
// lane-44 rooms layout; placement is validated against it and the spawn is
// refused on any mismatch.
void pc_p2_cave_items_setup();
void pc_p2_cave_items_shutdown();

// Draws one spawned cave-item pellet with the converted treasure model. Called
// from the pellet render seam; returns true when the pellet belongs to the cave
// item set (the caller must then skip its own shape draw).
bool pc_p2_cave_items_draw_pellet(Pellet* pellet, Graphics& gfx, Matrix4f& matrix);

// Exactly-once credit through the lane-06 ordinary receipt provider. Called from
// the pellet delivery seam; returns true when the pellet belongs to the cave item
// set, whether the grant was new or a durable duplicate.
bool pc_p2_cave_items_deliver(Pellet* pellet);

const P2CaveItemPlacement* pc_p2_cave_items_placement();
int pc_p2_cave_items_spawned();
// New first-time grants (exactly-once credit happened this run).
int pc_p2_cave_items_delivered();
// Completed delivery events, including durable duplicates from a prior process.
int pc_p2_cave_items_delivery_events();

// Test/fixture helper: the spawned pellet for an item token, or null.
Pellet* pc_p2_cave_items_pellet_for(const char* item);
