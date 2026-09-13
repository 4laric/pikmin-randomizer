#pragma once
class BTeki;
class Creature;
class PelletView;
class Graphics;
struct Matrix4f;
void pc_p2_snow_setup();
void pc_p2_snow_reset();
void pc_p2_snow_forget(BTeki*);
float pc_p2_snow_max_health(const BTeki*, float fallback);
const char* pc_p2_enemy_name(PelletView*);
bool pc_p2_snow_draw(BTeki*, Graphics&, const Matrix4f&, bool corpse=false);

// Returns whether this registered actor has an opt-in entry gate.
bool pc_p2_snow_attackable(BTeki*, Creature&, bool& result);

// Per-update angular response, retaining the caller's P1 arrival threshold.
bool pc_p2_snow_turn(BTeki*, float targetAngle, float arrivalStep, bool& arrived);

struct Vector3f;
// Source chase target velocity; false leaves the native tracing path untouched.
bool pc_p2_snow_chase(BTeki*, const Vector3f& target);

#include <string>
namespace p2pose { struct Pose; }
// Diagnostic copy of the last drawn geometry, absent for disabled/forgotten actors.
bool pc_p2_snow_geometry(BTeki*,p2pose::Pose&,std::string& clip,float& frame,bool& corpse);
