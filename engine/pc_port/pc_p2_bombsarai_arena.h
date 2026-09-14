#pragma once

#include "pc_p2_bombsarai_bomb.h"
#include "pc_p2_bombsarai_blast.h"
#include "pc_p2_bombsarai_fsm.h"
#include "pc_p2_bombsarai_hover.h"
#include "pc_p2_bombsarai_terrain.h"

class Graphics;

// Lane-owned registration/binding seam for the Careening Dirigibug lane
// (#244): one stationary, host-driven BombSarai arena loaded from an opt-in
// install profile (P2_BOMBSARAI_ARENA_1) per the #186 shared arena contract.
// Pinned placement only: the profile fixes the carrier hover position/yaw,
// bomb parameters, a static receiver list, and optional FSM keyframe timings
// plus a tick-indexed host-event script (stuck census, health, kill, bitter).
// The lane-owned 13-state FSM policy drives supply/release/fall/flick
// decisions; this module only senses targets from the pinned receivers,
// generates keyframes from the profile timings, and performs the FSM's
// requested effects through the bomb pool/hover/blast policies. There is no
// actor registry, AI perception, converted visual asset, sound, or effect
// integration in this module; those remain later slices and root-serialized
// work.

// Parses and installs the profile. Returns false (and installs nothing) on
// any invalid content.
bool pc_p2_bombsarai_arena_setup(const char* profilePath);
void pc_p2_bombsarai_arena_reset();

// Processes exactly one source 30 Hz update: FSM host inputs (target
// sensing, keyframes, scripted events) -> FSM decision -> hover vertical
// control -> requested effects (supply/throw) -> held bomb update through
// the required trace callback. A non-null trace is required; there is no
// no-trace fallback inside the arena. The traceContext must be a
// P2BombSaraiTerrainAdapter whose primitives are bound (the arena reuses its
// getMinY for hover terrain sampling and fall landing). Returns false if
// the arena is unavailable or input/trace failed.
bool pc_p2_bombsarai_arena_update(float sourceDelta,
                                  P2BombSaraiTraceFn trace, void* traceContext,
                                  P2BombSaraiCarrierFn carrier, void* carrierContext);

// FSM observation for fixtures/markers.
int pc_p2_bombsarai_arena_state();
const char* pc_p2_bombsarai_arena_state_name();
bool pc_p2_bombsarai_arena_carrier_dead();
bool pc_p2_bombsarai_arena_carrying();
// Last FSM-requested throw: P2BombSaraiThrowKind as int, or -1 when no throw
// has happened since setup; tick is the arena source tick of the throw.
int pc_p2_bombsarai_arena_last_throw_kind();
int pc_p2_bombsarai_arena_last_throw_tick();

// Latest routed blast hits from the pinned receiver list. blast_fired()
// latches true on the first detonation (even with zero in-volume hits) and
// stays latched until arena reset; the hit array is valid for that blast.
bool pc_p2_bombsarai_arena_blast_fired();
int pc_p2_bombsarai_arena_blast_count();
const P2BombSaraiRoutedHit* pc_p2_bombsarai_arena_blast_hits();

// Debug drawing only: carrier hover marker, held/in-flight bomb sphere, and
// a one-shot blast volume marker. No converted BombSarai assets exist yet
// (#128); nothing here claims visual fidelity.
void pc_p2_bombsarai_arena_draw(Graphics& gfx);
