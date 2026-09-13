#pragma once

class Piki;

void pc_p2_purple_impact_reset();
void pc_p2_purple_impact_set_enabled(bool);
bool pc_p2_purple_impact_enabled();
void pc_p2_purple_impact_arm(Piki*);
void pc_p2_purple_impact_forget(Piki*);
bool pc_p2_purple_impact_emit(Piki*, const char* cause);
