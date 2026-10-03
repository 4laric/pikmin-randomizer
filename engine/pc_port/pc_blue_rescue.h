#pragma once
class Piki;
// Transient rescue ownership only; ordinary captain-held entries have no owner.
bool pc_blue_rescue_begin(Piki* victim, Piki* rescuer);
bool pc_blue_rescue_tick(Piki* victim);
void pc_blue_rescue_clear(Piki* victim);
void pc_blue_rescue_release(Piki* victim, Piki* rescuer);
bool pc_blue_rescue_owned(const Piki* victim, const Piki* rescuer);
