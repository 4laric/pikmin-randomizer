#pragma once
class Piki;
class Graphics;
class Pom;

bool pc_p2_whites_enabled();
bool pc_p2_is_white(const Piki* piki);
void pc_p2_make_white(Piki* piki);
void pc_p2_white_setup();
float pc_p2_white_move_multiplier();
float pc_p2_white_attack();
float pc_p2_white_carry_power(int maturity);
float pc_p2_white_carry_min_factor();
float pc_p2_white_carry_max_factor();
bool pc_p2_draw_white(Piki* piki, Graphics& gfx);
bool pc_p2_ivory(const Pom* pom);
int pc_p2_convert_ivory(Pom* pom, int remaining);
