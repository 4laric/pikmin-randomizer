#pragma once

#include "pc_p2_bombsarai_bomb.h"
#include "pc_p2_bombsarai_blast.h"
#include "pc_p2_bombsarai_fsm.h"
#include "pc_p2_bombsarai_hover.h"
#include "pc_p2_bombsarai_terrain.h"

class Graphics;

// Lane-owned registration/binding seam for the Careening Dirigibug lane
// (#244): a host-driven BombSarai arena loaded from an opt-in install profile
// (P2_BOMBSARAI_ARENA_1) per the #186 shared arena contract. Supports one or
// two carriers (the profile's `carrier` block plus an optional `carrier2`
// block) sharing a single bomb pool and receiver list, so multi-carrier
// ownership can be exercised. Placement is still pseudo/scripted: the profile
// fixes each carrier's origin/yaw/token, bomb parameters, a static receiver
// list, optional FSM keyframe timings, an optional scripted horizontal x/z
// path per carrier (injected walkToTarget stand-in), and optional per-carrier
// tick-indexed host-event scripts (stuck census, health, kill, bitter). The
// lane-owned 13-state FSM policy drives supply/release/fall/flick decisions;
// this module senses targets from the pinned receivers, generates keyframes
// from the profile timings, advances a scripted horizontal path, and performs
// the FSM's requested effects through the shared bomb pool/hover/blast
// policies. There is no actor registry, AI perception, converted visual asset,
// sound, or effect integration in this module; those remain later slices and
// root-serialized work.

// One recorded detonation plus its routed receiver hits, for per-carrier
// attribution evidence at runtime.
struct P2BombSaraiBlastRecord {
    int carrier = -1;                 // originating carrier index
    std::uint64_t carrierToken = 0;   // the carrier token the bomb carried
    bool carrierValid = false;        // resolved at blast time (dead -> false)
    P2BombSaraiVec3 center;
    int tick = 0;                     // arena source tick of detonation
    P2BombSaraiRoutedHit hits[8];
    int hitCount = 0;
};

// Parses and installs the profile. Returns false (and installs nothing) on
// any invalid content.
bool pc_p2_bombsarai_arena_setup(const char* profilePath);
void pc_p2_bombsarai_arena_reset();

// Processes exactly one source 30 Hz update for all carriers: scripted events
// -> horizontal path advance -> FSM host inputs (target sensing, keyframes)
// -> FSM decision -> hover vertical control -> requested effects
// (supply/throw through the shared pool) -> all live bombs advanced through
// the required trace callback, with detonations recorded per carrier. A
// non-null trace is required; the traceContext must be a
// P2BombSaraiTerrainAdapter whose primitives are bound. Returns false if the
// arena is unavailable or input/trace failed.
bool pc_p2_bombsarai_arena_update(float sourceDelta,
                                  P2BombSaraiTraceFn trace, void* traceContext,
                                  P2BombSaraiCarrierFn carrier, void* carrierContext);

int pc_p2_bombsarai_arena_carrier_count();

// Per-carrier FSM observation for fixtures/markers (carrier in [0, count)).
int pc_p2_bombsarai_arena_state(int carrier);
const char* pc_p2_bombsarai_arena_state_name(int carrier);
bool pc_p2_bombsarai_arena_carrier_dead(int carrier);
bool pc_p2_bombsarai_arena_carrying(int carrier);
// Last resolved captured-bomb world position (joint-follow evidence). Returns
// true only while carrier's bomb is riding its capture joint.
bool pc_p2_bombsarai_arena_captured_position(int carrier, P2BombSaraiVec3& out);
// Last FSM-requested throw: P2BombSaraiThrowKind as int, or -1 when no throw
// has happened since setup; tick is the arena source tick of that throw.
int pc_p2_bombsarai_arena_last_throw_kind(int carrier);
int pc_p2_bombsarai_arena_last_throw_tick(int carrier);

// Detonation records across all carriers. blast_fired() latches true on the
// first detonation and stays latched until reset. Each record owns its routed
// hits; records accumulate per detonation (one per bomb), never overwritten.
bool pc_p2_bombsarai_arena_blast_fired();
int pc_p2_bombsarai_arena_blast_record_count();
const P2BombSaraiBlastRecord* pc_p2_bombsarai_arena_blast_records();

// Debug drawing only: carrier hover markers, held/in-flight bomb spheres, and
// one-shot blast volume markers. No converted BombSarai assets exist yet
// (#128); nothing here claims visual fidelity.
void pc_p2_bombsarai_arena_draw(Graphics& gfx);
