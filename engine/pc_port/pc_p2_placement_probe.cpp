#include "pc_p2_placement_probe.h"

#include "pc_bbft.h"
#include "pc_randomizer.h"
#include "teki.h"
#include "MapMgr.h"
#include "MapCode.h"
#include "Route.h"
#include "Creature.h"
#include "Generator.h"

#include <cmath>
#include <cstdio>
#include <fstream>
#include <map>
#include <string>

namespace {
// Mirror the family adapters' bound: reject NaN/Inf and absurd coordinates
// before touching the map, so a malformed spawn never reads out of bounds.
bool bounded(float x, float y, float z)
{
    constexpr float kBound = 100000.0f;
    return std::isfinite(x) && std::isfinite(y) && std::isfinite(z)
        && std::fabs(x) <= kBound && std::fabs(y) <= kBound && std::fabs(z) <= kBound;
}

// Carry-route coverage radius. A spawn is "on the route graph" only when its
// nearest OPEN waypoint lies within this XZ distance. This mirrors engine
// reach conventions (aiRescue.cpp thresholds against the waypoint radius;
// navi.cpp:761 uses 200.0f as its nearest-actor bound) and admits every point
// inside a corridor segment of the P2 room graph (worst half-segment ~183
// units) while rejecting points off the graph.
constexpr float kRouteCoverageRadius = 200.0f;

// Shared terrain/water/route sample + marker. `slot` is the placement-catalog
// slot uid (crc32) when known, else 0. Returns true when the sampled point
// carries both terrain and route evidence.
bool emitPlacementSlot(float x, float y, float z, unsigned generator, unsigned slot, int actorType)
{
    if (!mapMgr || !routeMgr || !bounded(x, y, z)) return false;

    // (a) XYZ evidence: a ground triangle must exist beneath the spawn, so we
    // never admit a position the map does not actually cover.
    CollTriInfo* tri = mapMgr->getCurrTri(x, z, true);
    const bool hasTerrain = tri != nullptr;

    // (b) Terrain class: 'none' when no triangle, otherwise 'water' vs 'ground'
    // by map-code attribute. A missing triangle never reads back as 'ground'.
    const int attribute = tri ? MapCode::getAttribute(tri) : ATTR_NULL;
    const char* terrain = hasTerrain ? (attribute == ATTR_Water ? "water" : "ground") : "none";
    const float groundY = hasTerrain ? mapMgr->getMinY(x, z, true) : 0.0f;
    const float depth = (hasTerrain && attribute == ATTR_Water && std::isfinite(groundY))
                            ? (y - groundY) : 0.0f;

    // (c) Route evidence: the spawn must sit within the route graph's coverage
    // radius so a corpse corridor exists.
    const Vector3f pos(x, y, z);
    WayPoint* waypoint = routeMgr->findNearestWayPoint('test', pos, false);
    bool route = waypoint != nullptr;
    float routeDistance = -1.0f;
    if (waypoint) {
        const float dx = waypoint->mPosition.x - x;
        const float dz = waypoint->mPosition.z - z;
        routeDistance = std::sqrt(dx * dx + dz * dz);
        route = routeDistance <= kRouteCoverageRadius;
    }

    std::printf("P2_PLACEMENT_SLOT generator=%u slot=%u actor=%d xyz=%d terrain=%s route=%d route_distance=%.1f x=%.3f y=%.3f z=%.3f water_depth=%.2f\n",
                generator, slot, actorType, hasTerrain ? 1 : 0, terrain, route ? 1 : 0,
                static_cast<double>(routeDistance),
                static_cast<double>(x), static_cast<double>(y), static_cast<double>(z),
                static_cast<double>(depth));
    return hasTerrain && route;
}

// #256 boss-slot measurement (read-only): walk 16 rays out from the slot in
// 25-unit steps to 300 and record how far each ray stays on dry ground whose
// height never steps by more than 20 between samples (a wall or ledge) and
// stays within 60 of the slot height. `clear` is the minimum over all rays:
// the radius of a flat, dry, wall-free disc around the slot. A rolling boss
// with territory 200 needs clear >= 250 (P2_BOSS_SLOT_PROBE ok=1).
void emitBossClearance(float x, float y, float z, unsigned slot)
{
    if (!mapMgr || !bounded(x, y, z)) return;
    const float centre = mapMgr->getMinY(x, z, true);
    float clear = 1e9f, maxDy = 0.0f;
    int water = 0, missing = 0, steps = 0;
    for (int ray = 0; ray < 16; ++ray) {
        const float a = float(ray) * 6.2831853f / 16.0f;
        float prev = centre, reach = 0.0f;
        for (float r = 25.0f; r <= 300.0f; r += 25.0f) {
            const float px = x + std::sin(a) * r, pz = z + std::cos(a) * r;
            CollTriInfo* tri = mapMgr->getCurrTri(px, pz, true);
            if (!tri) { ++missing; break; }
            if (MapCode::getAttribute(tri) == ATTR_Water) { ++water; break; }
            const float h = mapMgr->getMinY(px, pz, true);
            if (std::fabs(h - prev) > 20.0f || std::fabs(h - centre) > 60.0f) { ++steps; break; }
            if (std::fabs(h - centre) > maxDy) maxDy = std::fabs(h - centre);
            prev = h;
            reach = r;
        }
        if (reach < clear) clear = reach;
    }
    std::printf("P2_BOSS_SLOT_PROBE slot=%u clear=%.0f max_dy=%.1f water_rays=%d offmap_rays=%d wall_rays=%d ok=%d "
                "x=%.1f y=%.1f z=%.1f\n",
                slot, static_cast<double>(clear), static_cast<double>(maxDy), water, missing, steps,
                clear >= 250.0f ? 1 : 0, static_cast<double>(x), static_cast<double>(centre), static_cast<double>(z));
}
}

void pc_p2_placement_probe_birth(float x, float y, float z, unsigned generator, unsigned slot, int actorType)
{
    // Campaign path: the generated placement already carries its catalog slot uid
    // (pc_randomizer_generator_id), so no sidecar join is needed. Read-only.
    emitPlacementSlot(x, y, z, generator, slot, actorType);
    emitBossClearance(x, y, z, slot);
    std::fflush(stdout);
}

void pc_p2_placement_probe_run()
{
    if (!pc_pikipelago_room_preview()) return; // room-preview path; campaign uses birth hook
    if (!mapMgr || !routeMgr || !tekiMgr) return;

    // When the P2 seed bridge is active the per-birth hook already emitted one
    // resolved-uid placement marker per generated generator; do not double-emit
    // them here (the sidecar path is for runs without the bridge).
    if (pc_randomizer_p2_bridge()) {
        std::printf("P2_PLACEMENT_PROBE actors=0 evidence_slots=0 source=birth_hook\n");
        std::fflush(stdout);
        return;
    }

    int actors = 0;
    int evidenceSlots = 0;

    // Catalog-join sidecar: maps a generator's 4-byte file id (_70) to a
    // placement-catalog slot uid (crc32). Best-effort: absent/partial sidecars
    // simply leave `slot` at 0 (unmapped) and the root audit reports
    // catalog_join=false. Format: `P2_PLACEMENT_SLOTS_1` then one
    // `<generator_id> <slot_uid>` pair per line.
    std::map<unsigned, unsigned> slotByGenerator;
    {
        std::ifstream sidecar("p2-placement-slots.txt");
        if (sidecar) {
            std::string magic;
            if ((sidecar >> magic) && magic == "P2_PLACEMENT_SLOTS_1") {
                unsigned generator = 0, slot = 0;
                while (sidecar >> generator >> slot) slotByGenerator[generator] = slot;
            }
        }
    }

    Iterator it(tekiMgr);
    CI_LOOP(it) {
        Teki* teki = static_cast<Teki*>(*it);
        if (!teki) continue;
        const Vector3f& pos = teki->getPosition();
        if (!bounded(pos.x, pos.y, pos.z)) continue;

        // `generator` is the 4-byte file id (_70); `slot` is the catalog uid from
        // the sidecar, or 0.
        const unsigned generator = teki->mGenerator ? teki->mGenerator->_70 : 0;
        const unsigned slot = slotByGenerator.count(generator) ? slotByGenerator.at(generator) : 0;
        if (emitPlacementSlot(pos.x, pos.y, pos.z, generator, slot, static_cast<int>(teki->mTekiType)))
            ++evidenceSlots;
        ++actors;
    }
    std::printf("P2_PLACEMENT_PROBE actors=%d evidence_slots=%d\n", actors, evidenceSlots);
    std::fflush(stdout);
}
