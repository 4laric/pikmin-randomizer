#pragma once
class Pellet;
class Graphics;
class GoalItem;
struct Suckable;
struct Matrix4f;
void pc_p2_preview_setup();
bool pc_p2_preview_draw(Pellet*, Graphics&, Matrix4f&);
bool pc_p2_preview_deliver(Pellet*);

bool pc_p2_preview_ready();
// Separate from treasure readiness: old fixture callers require a nonnull target.
bool pc_p2_preview_cargo_free_ready();
Pellet* pc_p2_preview_treasure();
Suckable* pc_p2_preview_goal();
bool pc_p2_preview_is_pod(GoalItem*);
bool pc_p2_preview_draw_pod(GoalItem*, Graphics&, Matrix4f&);
int pc_p2_preview_pokos();
// Lifecycle (#397): re-scan live Chappy actors into the corpse receipt registry
// (no economy/shape changes) and report its size. Additive, behavior-neutral.
void pc_p2_preview_rebind_corpses();
int pc_p2_preview_corpse_count();

class Shape;
int pc_p2_preview_cargo_count();
Pellet* pc_p2_preview_cargo_at(int);
Shape* pc_p2_preview_cargo_shape(Pellet*);
