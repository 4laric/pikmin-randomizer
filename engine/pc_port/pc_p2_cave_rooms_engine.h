// Lane 44 (#482): engine-facing API for the proxy cave-room instantiation. The
// logic and parser stay in pc_p2_cave_rooms.h (engine-free); this header only
// declares the glue implemented in pc_p2_cave_rooms.cpp.
#pragma once

#include "pc_p2_cave_rooms.h"

class Graphics;

// True when a P2_CAVE_ROOMS_1 bridge config was loaded this run.
bool pc_p2_cave_rooms_active();

// Opt-in: reads PIKMIN_CAVE_ROOMS (path) or ./p2-cave-rooms.txt. No-op and no
// output when neither exists, so a normal run is unchanged.
void pc_p2_cave_rooms_setup();
void pc_p2_cave_rooms_shutdown();

// Proxy geometry overlay (rooms only; never a generation PASS).
void pc_p2_cave_rooms_draw(Graphics& gfx);

const P2CaveRoomLayout* pc_p2_cave_rooms_layout();

// Live squad keys from the real pikiMgr.
P2CaveAbilities pc_p2_cave_rooms_squad_abilities();

// Nearest proxy unit to a world XZ position (empty when inactive).
std::string pc_p2_cave_rooms_unit_at(float x, float z);

// Reachability of a unit id under the live squad's keys (bud fixpoint).
bool pc_p2_cave_rooms_reachable_now(const std::string& target);
