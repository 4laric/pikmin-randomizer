#pragma once

class BTeki;
namespace p2purpleimpact { struct Event; }

void pc_p2_kochappy_stun_reset();
void pc_p2_kochappy_stun_register(BTeki*, float fitDuration);
void pc_p2_kochappy_stun_forget(BTeki*);
bool pc_p2_kochappy_stun_receive(BTeki*, const p2purpleimpact::Event&, float bounceRoll);
bool pc_p2_kochappy_stun_step(BTeki*, float deltaTime, float fitRoll);
bool pc_p2_kochappy_stun_needs_fit_roll(const BTeki*);
void pc_p2_kochappy_stun_interrupt(BTeki*);
bool pc_p2_kochappy_stun_active(const BTeki*);
