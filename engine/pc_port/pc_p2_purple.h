#pragma once
class Piki;
class Pellet;
class Graphics;
class Matrix4f;
class Pom;
struct PikiHeadItem;
bool pc_p2_purples_enabled();
bool pc_p2_is_purple(const Piki*);
void pc_p2_make_purple(Piki*);
void pc_p2_purple_setup();
int pc_piki_carry_strength(const Piki*);
float pc_piki_carry_power(const Piki*);
float pc_p2_move_multiplier(const Piki*);
float pc_p2_purple_attack();
float pc_p2_purple_throw_height();
float pc_p2_transport_speed(Pellet*,float fallback);
bool pc_p2_draw_purple(Piki*,Graphics&);
bool pc_p2_violet(const Pom*);
// Returns non-Purple slots used, or -1 for the ordinary P1 path.
int pc_p2_convert_violet(Pom*, int remaining);
void pc_p2_purple_status();
