// Lane 50 (#488, cave wave #468): engine glue for carry blocking at a generated
// floor's hard hazards.
//
// Reads the host bridge's P2_CAVE_GATES_1 plan, places one hazard volume per
// blocking door on the door between the hazard node and its entrance-ward
// neighbour, and makes the hazard physically gate carrying: a closed electric
// gate zaps non-electric-immune Pikmin (an electric-immune Pikmin opens it), a
// water pool panics non-blue Pikmin. Both reactions drop a carried cave treasure
// through the engine's own release path, so a red-carried tagged treasure cannot
// cross the closed door and is never credited until the key Pikmin clears it.
//
// This is proxy geometry with real engine reactions: it is never a generation
// PASS.
#include "pc_p2_cave_carry_engine.h"
#include "pc_p2_cave_rooms_engine.h"
#include "pc_p2_cave_items_engine.h"

#include "Interactions.h"
#include "MapMgr.h"
#include "Pellet.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "pc_p2_species.h"
#include "pc_p2_species_policy.h"
#include "system.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>

namespace {
P2CaveCarryPlan carryPlan;
bool carryActive = false;

struct CarryBlocker {
    std::string id;       // door node id (leaf_elec_0, choke_water_0, ...)
    std::string hazard;   // elec / water
    std::string key;      // yellow / blue
    Vector3f position;
    bool open = false;    // electric gates only; water never opens
    float cooldown = 0.0f;
};

std::vector<CarryBlocker> blockers;
int blockedCount = 0;
int openedCount = 0;
int carriersDropped = 0;
int waterBlockedCount = 0;

int hazardCode(const std::string& hazard)
{
    if (hazard == "elec") return P2HazardElectric;
    if (hazard == "water") return P2HazardWater;
    return -1;
}

Vector3f unitGround(const P2CaveRoomLayout& rooms, const P2CaveRoomUnit& unit)
{
    const float x = p2CaveRoomsWorldX(rooms, unit);
    const float z = p2CaveRoomsWorldZ(rooms, unit);
    const float y = mapMgr ? mapMgr->getMinY(x, z, true) : 0.f;
    return Vector3f(x, y, z);
}

int hopDistance(const P2CaveRoomLayout& rooms, const std::string& target)
{
    if (target == rooms.entrance) return 0;
    std::vector<std::string> seen;
    std::vector<std::string> frontier;
    seen.push_back(rooms.entrance);
    frontier.push_back(rooms.entrance);
    int depth = 0;
    while (!frontier.empty()) {
        std::vector<std::string> next;
        ++depth;
        for (const std::string& current : frontier) {
            for (const std::pair<std::string, std::string>& edge : rooms.edges) {
                std::string neighbour;
                if (edge.first == current) neighbour = edge.second;
                else if (edge.second == current) neighbour = edge.first;
                else continue;
                if (std::find(seen.begin(), seen.end(), neighbour) != seen.end()) continue;
                if (neighbour == target) return depth;
                seen.push_back(neighbour);
                next.push_back(neighbour);
            }
        }
        frontier = next;
    }
    return -1;
}

// A blocking door sits on the edge between its node and the reachable neighbour
// closest to the entrance, so a carrier is zapped as it tries to leave the
// hazard node rather than the instant it picks the treasure up.
Vector3f doorPosition(const P2CaveRoomLayout& rooms, const P2CaveRoomUnit& unit)
{
    const int unitHops = hopDistance(rooms, unit.id);
    const P2CaveRoomUnit* best = nullptr;
    int bestHops = 0;
    for (const std::pair<std::string, std::string>& edge : rooms.edges) {
        std::string neighbour;
        if (edge.first == unit.id) neighbour = edge.second;
        else if (edge.second == unit.id) neighbour = edge.first;
        else continue;
        const P2CaveRoomUnit* candidate = p2CaveRoomsFind(rooms, neighbour);
        if (!candidate) continue;
        const int hops = hopDistance(rooms, neighbour);
        if (hops < 0) continue;
        if (unitHops >= 0 && hops >= unitHops) continue;
        if (!best || hops < bestHops) {
            best = candidate;
            bestHops = hops;
        }
    }
    const Vector3f here = unitGround(rooms, unit);
    if (!best) return here;
    const Vector3f there = unitGround(rooms, *best);
    return Vector3f((here.x + there.x) * 0.5f, (here.y + there.y) * 0.5f,
                    (here.z + there.z) * 0.5f);
}

bool readPlan(const std::string& path, P2CaveCarryPlan& out, std::string& error)
{
    std::ifstream in(path);
    if (!in) {
        error = "cannot open gates config: " + path;
        return false;
    }
    return p2CaveCarryParse(in, out, error);
}

Piki* nearestPikmin(const Vector3f& position, float radius, int hazard, bool immuneOnly,
                    bool& immune)
{
    Piki* best = nullptr;
    float bestSq = radius * radius;
    immune = false;
    if (!pikiMgr) return nullptr;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* piki = static_cast<Piki*>(*it);
        if (!piki || !piki->isAlive()) continue;
        const int species = pc_p2_species(piki);
        const bool pikminImmune = p2_species_immune(species, hazard);
        if (immuneOnly && !pikminImmune) continue;
        if (!immuneOnly && pikminImmune) continue;
        const float dx = piki->getPosition().x - position.x;
        const float dz = piki->getPosition().z - position.z;
        const float distance = dx * dx + dz * dz;
        if (distance >= bestSq) continue;
        bestSq = distance;
        best = piki;
        immune = pikminImmune;
    }
    return best;
}

// True when the Pikmin holds a live cave-item Pellet (lane 46's spawned set).
bool isCaveCarrier(Piki* piki)
{
    if (!piki) return false;
    Creature* stick = piki->getStickObject();
    if (!stick || stick->mObjType != OBJTYPE_Pellet) return false;
    Pellet* pellet = static_cast<Pellet*>(stick);
    const P2CaveItemPlacement* placement = pc_p2_cave_items_placement();
    if (!placement) return false;
    for (const P2CaveItemEntry& entry : placement->items) {
        if (pc_p2_cave_items_pellet_for(entry.item.c_str()) == pellet) return true;
    }
    return false;
}
}  // namespace

bool pc_p2_cave_carry_active() { return carryActive; }

const P2CaveCarryPlan* pc_p2_cave_carry_plan() { return carryActive ? &carryPlan : nullptr; }

int pc_p2_cave_carry_blocked() { return blockedCount; }

int pc_p2_cave_carry_opened() { return openedCount; }

int pc_p2_cave_carry_carriers_dropped() { return carriersDropped; }

int pc_p2_cave_carry_water_blocked() { return waterBlockedCount; }

bool pc_p2_cave_carry_door_pos(const char* door_id, float* x, float* z)
{
    if (!door_id || !x || !z) return false;
    for (const CarryBlocker& blocker : blockers) {
        if (blocker.id == door_id) {
            *x = blocker.position.x;
            *z = blocker.position.z;
            return true;
        }
    }
    return false;
}

bool pc_p2_cave_carry_handles(const std::string& door_id)
{
    if (!carryActive) return false;
    for (const CarryBlocker& blocker : blockers) {
        if (blocker.id == door_id) return true;
    }
    return false;
}

void pc_p2_cave_carry_shutdown()
{
    carryPlan = P2CaveCarryPlan{};
    carryActive = false;
    blockers.clear();
    blockedCount = 0;
    openedCount = 0;
    carriersDropped = 0;
    waterBlockedCount = 0;
}

void pc_p2_cave_carry_setup()
{
    carryPlan = P2CaveCarryPlan{};
    carryActive = false;
    blockers.clear();
    blockedCount = 0;
    openedCount = 0;
    carriersDropped = 0;
    waterBlockedCount = 0;

    const char* env = std::getenv("PIKMIN_CAVE_GATES");
    const std::string path = env && env[0] ? env : "p2-cave-gates.txt";
    if (!std::ifstream(path)) return;

    std::string error;
    if (!readPlan(path, carryPlan, error)) {
        std::printf("P2_CAVE_CARRY FAILED reason=%s\n", error.c_str());
        std::fflush(stdout);
        return;
    }
    const P2CaveRoomLayout* rooms = pc_p2_cave_rooms_layout();
    if (!rooms) {
        std::printf("P2_CAVE_CARRY FAILED reason=no rooms layout\n");
        std::fflush(stdout);
        return;
    }
    if (carryPlan.cave != rooms->cave || carryPlan.floor != rooms->floor
        || carryPlan.seed != rooms->seed) {
        std::printf("P2_CAVE_CARRY FAILED reason=plan/rooms drift\n");
        std::fflush(stdout);
        return;
    }
    for (const P2CaveCarryDoor& door : carryPlan.doors) {
        const P2CaveRoomUnit* unit = p2CaveRoomsFind(*rooms, door.id);
        if (!unit) {
            std::printf("P2_CAVE_CARRY FAILED reason=door not in rooms: %s\n", door.id.c_str());
            std::fflush(stdout);
            return;
        }
        if (!p2CaveCarryBlocks(door)) continue;
        CarryBlocker blocker;
        blocker.id = door.id;
        blocker.hazard = p2CaveCarryHazardFor(door.carry_block);
        blocker.key = p2CaveCarryKeyFor(door.carry_block);
        blocker.position = doorPosition(*rooms, *unit);
        blockers.push_back(blocker);
        std::printf("%s\n", p2CaveCarryDoorMarker(door).c_str());
        std::printf("P2_CAVE_CARRY_VOLUME id=%s hazard=%s key=%s x=%.3f y=%.3f z=%.3f\n",
                    blocker.id.c_str(), blocker.hazard.c_str(), blocker.key.c_str(),
                    blocker.position.x, blocker.position.y, blocker.position.z);
    }
    carryActive = true;
    std::printf("%s\n", p2CaveCarryMarker(carryPlan).c_str());
    std::fflush(stdout);
}

void pc_p2_cave_carry_tick()
{
    if (!carryActive) return;
    const float dt = gsys ? gsys->getFrameTime() : 0.0f;
    // An electric-immune Pikmin at any electric gate clears every electric
    // gate: the squad holds the yellow key, so the hazard system is passable.
    bool yellowKey = false;
    for (CarryBlocker& blocker : blockers) {
        if (blocker.hazard != "elec" || blocker.open) continue;
        const int hazard = hazardCode(blocker.hazard);
        if (hazard < 0) continue;
        bool immune = false;
        if (nearestPikmin(blocker.position, 22.0f, hazard, true, immune)) yellowKey = true;
    }
    if (yellowKey) {
        for (CarryBlocker& blocker : blockers) {
            if (blocker.hazard == "elec" && !blocker.open) {
                blocker.open = true;
                ++openedCount;
                std::printf("P2_CAVE_CARRY_OPEN id=%s hazard=elec reason=electric_immune\n",
                            blocker.id.c_str());
                std::fflush(stdout);
            }
        }
    }
    for (CarryBlocker& blocker : blockers) {
        if (blocker.cooldown > 0.0f) blocker.cooldown -= dt;
        const int hazard = hazardCode(blocker.hazard);
        if (hazard < 0) continue;
        if (blocker.open) continue;
        if (blocker.cooldown > 0.0f) continue;
        bool immune = false;
        Piki* target = nearestPikmin(blocker.position, 16.0f, hazard, false, immune);
        if (!target) continue;
        const bool carrying = isCaveCarrier(target);
        bool accepted = false;
        if (blocker.hazard == "elec") {
            Vector3f direction(target->getPosition().x - blocker.position.x, 0.0f,
                               target->getPosition().z - blocker.position.z);
            accepted = target->stimulate(InteractDenki(nullptr, 1.0f, &direction));
        } else {
            accepted = target->stimulate(InteractBubble(nullptr, 1.0f));
        }
        blocker.cooldown = 0.5f;
        ++blockedCount;
        if (carrying) ++carriersDropped;
        if (blocker.hazard == "water") ++waterBlockedCount;
        std::printf(
            "P2_CAVE_CARRY_BLOCKED id=%s hazard=%s species=%d carrying=%d accepted=%d tx=%.2f tz=%.2f\n",
            blocker.id.c_str(), blocker.hazard.c_str(), pc_p2_species(target), int(carrying),
            int(accepted), target->getPosition().x, target->getPosition().z);
        std::fflush(stdout);
    }
}
