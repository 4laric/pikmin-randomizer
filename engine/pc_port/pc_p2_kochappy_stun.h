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

// Read-only acceptance observer. No RNG consumption or lifecycle mutation.
struct PcP2KochappyStunSample {
    bool registered = false;
    unsigned long long lifetime = 0;
    int phase = 0; // p2purpleimpact::Phase: None=0, Bounce=1, Fit=2
    unsigned bounceUpdates = 0;
    float fitElapsed = 0.0f;
    float fitDuration = 0.0f;
};
PcP2KochappyStunSample pc_p2_kochappy_stun_sample(const BTeki*);
