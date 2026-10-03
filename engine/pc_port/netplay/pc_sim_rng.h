#pragma once

// Simulation vs cosmetic RNG for deterministic netplay, M1 (issue #878).
//
// Two independent streams sharing one MSL-compatible generator:
//   state = state * 1103515245 + 12345; return (state >> 16) & 0x7fff;
// LCG range is always0..32767; libc retains its platform range. Both streams use this formula with
// separate state.
//
// When deterministic mode is OFF, pc_sim_rand()/pc_cosmetic_rand() return
// rand() exactly as today, in the same call order, so the libc sequence is
// unchanged. When ON, each stream draws from its own LCG state, seeded per
// day by pc_netplay_det_reseed_for_new_day().
//
// Interface contract (fixed names/signatures; the harness lane calls these):
//   pc_sim_rand, pc_sim_srand, pc_sim_rng_state, pc_sim_rng_set_state,
//   pc_cosmetic_rand.
// Additive M1 helpers: pc_sim_randf / pc_cosmetic_randf (one stream draw per
// call, same float shaping as System::getRand, so the off-mode sequence is
// bit-identical) and pc_cosmetic_srand / pc_cosmetic_rng_state (the contract
// requires reseeding the cosmetic stream per day but provides no setter).

#include <cstdlib>

int      pc_sim_rand(void);          // sim stream; when NOT deterministic it returns rand() (identical to today)
void     pc_sim_srand(unsigned seed);
unsigned pc_sim_rng_state(void);
void     pc_sim_rng_set_state(unsigned state);
int      pc_cosmetic_rand(void);     // draw/UI-only stream; when NOT deterministic it returns rand()

// Seeds/reads the cosmetic stream (see header note above).
void     pc_cosmetic_srand(unsigned seed);
unsigned pc_cosmetic_rng_state(void);
void     pc_cosmetic_rng_set_state(unsigned state);

// Records the calling thread as the RNG owner (called by
// pc_netplay_det_init from main()). Det-mode draws from any other thread log
// once to stderr; see pc_sim_rng.cpp.
void pc_sim_rng_note_main_thread(void);

// One-draw float shapers mirroring System::getRand: max * (draw / RAND_MAX).
float pc_sim_rng_denominator(); // portable offline32767; legacy/netplay unchanged RAND_MAX
inline float pc_sim_randf(float max) { return max * (pc_sim_rand() / pc_sim_rng_denominator()); }
inline float pc_cosmetic_randf(float max) { return max * (pc_cosmetic_rand() / pc_sim_rng_denominator()); }

// Explicit bootstrap-only portable profile for resumable offline sessions.
// Default libc/netplay behavior stays selected until the scene owner opts in.
#include <cstdint>
#include <string>
struct PcSimRngCheckpoint {
    uint32_t version=1,profile=0,simState=0,cosmeticState=0;
    uint64_t simDraws=0,cosmeticDraws=0;
};
bool pc_sim_rng_begin_offline(unsigned simSeed,unsigned cosmeticSeed,std::string&);
bool pc_sim_rng_capture(PcSimRngCheckpoint&,std::string&);
// Only the owner may establish/remove constructor suppression; apply requires it.
bool pc_sim_rng_constructor_suppression(bool enabled,std::string&);
bool pc_sim_rng_apply(const PcSimRngCheckpoint&,std::string&);
