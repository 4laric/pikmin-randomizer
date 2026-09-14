#pragma once

// Lane 31 (#443 / parent #175): opt-in registration seam that drives the
// source-correct Waterwraith actor (pc_p2_waterwraith_actor) inside the real
// engine tick/draw, mirroring the BigTreasure host registration in
// pc_p2_hardlanes.cpp. The caller only reaches setup when the experimental
// room-preview flag is active AND the `p2-waterwraith-actor.txt` profile is
// present; otherwise every entry point is a no-op and ordinary P1 play is
// untouched. Fixed placement comes first: no spawn-table registration, no
// source Map/AI/receiver wiring.
//
// The module owns the actor, the single Tyre child and (best-effort) the lane
// visual bank so `_draw` has poses. The engine supplies only the frame delta
// and the room transform.
//
// Profile grammar (P2_WATERWRAITH_ACTOR_1, fail-closed):
//   P2_WATERWRAITH_ACTOR_1
//   placement <x> <y> <z> <yawRadians>
//   target <x> <y> <z>
//   speed <travelSpeed>            (optional; default 120 = proper fp05)
// All coordinates must be finite within +/-100000; yaw finite in [-pi, pi];
// speed finite in (0, 1000]. Any malformed or duplicate line rejects the whole
// profile with no partial install.

#include "pc_p2_waterwraith.h"

#include <cstdint>

class Graphics;
struct Matrix4f;

struct P2WaterwraithRegisterPlacement {
    P2WaterwraithVec3 placement{}; // fixed world placement (actor origin)
    float yaw = 0.0f;              // fixed facing offset, radians
    P2WaterwraithVec3 target{};    // fixed host route goal (world)
    float travelSpeed = 120.0f;    // proper fp05 retail travel speed
};

// Parses the opt-in actor profile. Returns false on any malformed content
// (fail-closed, no partial result).
bool p2_waterwraith_register_parse(const char* profilePath, P2WaterwraithRegisterPlacement& out);

// Installs the seam from the profile: builds the actor on the fixed placement
// route, births the single Tyre child and loads the lane visual bank when
// `p2-waterwraith-visual.txt` is present. Any prior seam/visual state is torn
// down first. Returns false when the profile is missing/invalid.
bool pc_p2_waterwraith_register_setup(const char* profilePath);

// Full seam reset (actor, route, visual bank and evidence counters).
void pc_p2_waterwraith_register_reset();

bool pc_p2_waterwraith_register_ready();

// One engine frame: source-clocks the actor at 30 Hz (at most 4 steps per
// frame), feeds the fixed fall -> recover -> walk host script and advances the
// visual bank. Safe before setup (no-op).
void pc_p2_waterwraith_register_tick(float delta);

// Draws the actor's BlackMan + Tyre species under the room `world` transform.
// Returns the number of species drawn (0 when not ready or no visual bank).
int pc_p2_waterwraith_register_draw(Graphics& gfx, const Matrix4f& world);

// Evidence accessors.
std::uint64_t pc_p2_waterwraith_register_ticks();
float pc_p2_waterwraith_register_distance();
float pc_p2_waterwraith_register_roll();
const char* pc_p2_waterwraith_register_phase();
P2WaterwraithVec3 pc_p2_waterwraith_register_wraith_position();
P2WaterwraithVec3 pc_p2_waterwraith_register_roller_position();
bool pc_p2_waterwraith_register_attached();
float pc_p2_waterwraith_register_tyre_health();
float pc_p2_waterwraith_register_body_health();
