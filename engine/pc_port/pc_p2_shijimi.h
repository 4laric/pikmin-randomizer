#pragma once
class BTeki;
class PelletView;
class Graphics;
struct Matrix4f;
// Family-owned lane-15/20 flying slice: Unmarked Spectralids (ShijimiChou,
// EnemyID 77) bounded source FSM on the private P1 Chappy placement vehicle.
// Every hook is a no-op for unregistered actors; ordinary P1 play is untouched.
void pc_p2_shijimi_setup();
void pc_p2_shijimi_reset();
void pc_p2_shijimi_forget(BTeki*);
const char* pc_p2_shijimi_name(PelletView*);
bool pc_p2_shijimi_draw(BTeki*, Graphics&, const Matrix4f&, bool corpse);
void pc_p2_shijimi_update(BTeki*);
float pc_p2_shijimi_param_f(const BTeki*, int idx, float fallback);
bool pc_p2_shijimi_suppress_ai(const BTeki*);
