// Lane 50 (#488): engine-facing API for carry blocking. The engine-free
// parse/verdict/markers stay in pc_p2_cave_carry.h; this header only declares the
// glue implemented in pc_p2_cave_carry.cpp.
#pragma once

#include "pc_p2_cave_carry.h"

// True when a P2_CAVE_GATES_1 plan was loaded this run.
bool pc_p2_cave_carry_active();

// Opt-in: reads PIKMIN_CAVE_GATES (path) or ./p2-cave-gates.txt. No-op and no
// output when neither exists, so a normal run is unchanged. Requires the live
// lane-44 rooms layout to place the hazard volumes and is refused on any
// cave/floor/seed drift.
void pc_p2_cave_carry_setup();
void pc_p2_cave_carry_shutdown();

// Live carry-blocking tick (electric gate/water pool hazard volumes).
void pc_p2_cave_carry_tick();

// True when this module owns the carry block for a door id (the lane-45 gate
// actor then yields its generic hazard to this module).
bool pc_p2_cave_carry_handles(const std::string& door_id);

const P2CaveCarryPlan* pc_p2_cave_carry_plan();

// Evidence counters: carriers/hazards blocked, and electric gates opened by an
// immune Pikmin.
int pc_p2_cave_carry_blocked();
int pc_p2_cave_carry_opened();
int pc_p2_cave_carry_carriers_dropped();
int pc_p2_cave_carry_water_blocked();

// Fixture helper: world position of a blocking door's hazard volume.
bool pc_p2_cave_carry_door_pos(const char* door_id, float* x, float* z);
