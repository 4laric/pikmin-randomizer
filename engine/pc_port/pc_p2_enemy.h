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
