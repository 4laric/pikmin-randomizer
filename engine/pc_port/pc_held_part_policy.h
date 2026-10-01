#pragma once

// Generic held ship part contract (#901), engine-free decisions.
//
// Any enemy (P1 teki, P2 own-FSM actor, P2 proxy, or a P2 boss born in a P1
// boss arena) can hold a ship part. The part lives in the holder's
// TekiPersonality::mID, exactly like a P1 part-holder teki, and the
// Archipelago check stays keyed by the UFO id delivered to the ship
// (UfoItem::finishSuck -> PlayerState::getUfoParts -> pc_bbft_check), so the
// drop is the ordinary PELTYPE_UfoPart pellet and nothing else changes.
//
// A P1 holder (no P2 source bound) keeps the vanilla behaviour exactly: it
// always holds its part at birth, and only BTeki::spawnItems spawns it, with
// the vanilla spawnPellets(id, -2, 1) call. Every #901 decision below applies
// only to a P2-bound holder.
//
// Everything here is a pure function of simulation state so both lockstep
// peers take the same branch on the same frame.

namespace p2heldpart {

// Birth. A P1 holder holds its part (vanilla). A P2-bound holder whose part is
// already collected, cached on the ground, or alive as a pellet must not hold
// it again (respawning generators, arena alias generators, re-created cached
// creatures).
inline bool keepAtBirth(bool isPart, bool partExists, bool p2Bound)
{
    if (!isPart) return false;
    return !p2Bound || !partExists;
}

// Which funnels may drop. P1 holders: only spawnItems (vanilla). P2-bound
// holders: spawnItems (proxies running a P1 strategy), dieSoon (NoCorpse
// families, pcEscapeNow) and die() (own-FSM families), latched to one drop.
enum class Funnel { SpawnItems, DieSoon, Die };

inline bool funnelDrops(Funnel funnel, bool p2Bound)
{
    return funnel == Funnel::SpawnItems || p2Bound;
}

// spawnItems part branch: P1 holders run it every time, as vanilla does; a
// P2-bound holder runs it only if no other funnel dropped the part yet.
inline bool spawnItemsRuns(bool latched, bool p2Bound)
{
    return !p2Bound || !latched;
}

// Death: drop exactly once, only on a real death (health spent). Escape,
// burrow, day-end teardown, doKill and exitCourse leave health above zero and
// never drop, so the holder keeps the part for the next visit.
enum class Drop { None, Spawn, AlreadyExists };

inline Drop onDeath(bool latched, bool isPart, float health, bool partExists)
{
    if (latched || !isPart || health > 0.0f) return Drop::None;
    return partExists ? Drop::AlreadyExists : Drop::Spawn;
}

} // namespace p2heldpart
