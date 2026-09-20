// Lane 50 (#488, cave wave #468): carry blocking at a generated floor's hazards.
//
// Lane 44 draws the proxy rooms, lane 45 instantiates real geometry and an
// electric-gate actor, lane 46 spawns/carries/credits real treasures. This module
// consumes the host bridge's ``P2_CAVE_GATES_1`` plan (one row per room door: its
// hazard, whether it blocks carrying, and the Pikmin key that clears it) and
// answers the carry question the running engine needs: may a carrier cross this
// closed door, or does the hard hazard stop it?
//
// A closed electric gate blocks carrying until a yellow (electric-immune) Pikmin
// reaches it; a water pool blocks non-blue carrying. The plan never claims
// generation (``generation=false`` on the host side) and the geometry it rides on
// is proxy: this is a carry-blocking slice, never a generation PASS.
//
// This header is engine-free on purpose: the parser, the verdict decision and the
// marker shapes live here and the one-consumer test includes only this file. The
// engine glue (positions, the live hazard volumes, the electric/water reactions)
// lives in pc_p2_cave_carry.cpp.
//
// Grammar (fixed token order, whitespace separated, ``-`` for empty):
//
//   P2_CAVE_GATES_1
//   cave <cave>
//   floor <int>
//   seed <int>
//   geometry <real|mixed|proxy>
//   doors <N>
//   <door_id> <kind> <hazard|none> <carry_block|none> <key|-|yellow|blue>
//   ... (N rows)
//   entrance <id>
//   hole <id>

#pragma once

#include <cstdint>
#include <istream>
#include <ostream>
#include <string>
#include <vector>

struct P2CaveCarryDoor {
    std::string id;
    std::string kind;        // segment / choke / leaf / bud / gate
    std::string hazard;      // empty when the door is hazard-free
    std::string carry_block; // none / elec / water
    std::string key;         // empty, or yellow / blue
};

struct P2CaveCarryPlan {
    std::string cave;
    int floor = 0;
    std::uint64_t seed = 0;
    std::string geometry;  // real / mixed / proxy
    std::vector<P2CaveCarryDoor> doors;
    std::string entrance;
    std::string hole;
};

// How a carrier interacts with a door under the current squad keys. ``carrying``
// is whether the Pikmin holds a cave-item treasure (a non-carrier is not this
// lane's concern and returns Ignore so only the carry is gated).
enum P2CaveCarryVerdict {
    P2CaveCarryPass = 0,   // not a blocking door, or the Pikmin is immune
    P2CaveCarryBlock = 1,  // blocking door, non-immune carrier -> drop, no credit
    P2CaveCarryIgnore = 2, // blocking door, non-immune non-carrier -> leave alone
};

inline bool p2CaveCarryBlocks(const P2CaveCarryDoor& door)
{
    return door.carry_block == "elec" || door.carry_block == "water";
}

inline const char* p2CaveCarryHazardFor(const std::string& carry_block)
{
    if (carry_block == "elec") return "elec";
    if (carry_block == "water") return "water";
    return "";
}

inline const char* p2CaveCarryKeyFor(const std::string& carry_block)
{
    if (carry_block == "elec") return "yellow";
    if (carry_block == "water") return "blue";
    return "";
}

inline const P2CaveCarryDoor* p2CaveCarryFindDoor(const P2CaveCarryPlan& plan, const std::string& id)
{
    for (const P2CaveCarryDoor& door : plan.doors) {
        if (door.id == id) return &door;
    }
    return nullptr;
}

inline P2CaveCarryVerdict p2CaveCarryDecide(const P2CaveCarryDoor& door, bool immune, bool carrying)
{
    if (!p2CaveCarryBlocks(door)) return P2CaveCarryPass;
    if (immune) return P2CaveCarryPass;
    return carrying ? P2CaveCarryBlock : P2CaveCarryIgnore;
}

inline int p2CaveCarryBlockingCount(const P2CaveCarryPlan& plan)
{
    int count = 0;
    for (const P2CaveCarryDoor& door : plan.doors) count += p2CaveCarryBlocks(door) ? 1 : 0;
    return count;
}

inline std::string p2CaveCarryMarker(const P2CaveCarryPlan& plan)
{
    int elec = 0;
    int water = 0;
    for (const P2CaveCarryDoor& door : plan.doors) {
        elec += door.carry_block == "elec" ? 1 : 0;
        water += door.carry_block == "water" ? 1 : 0;
    }
    return "P2_CAVE_CARRY_PLAN doors=" + std::to_string(plan.doors.size()) + " blocking="
           + std::to_string(elec + water) + " elec=" + std::to_string(elec) + " water="
           + std::to_string(water) + " geometry="
           + (plan.geometry.empty() ? std::string("proxy") : plan.geometry) + " cave=" + plan.cave
           + " floor=" + std::to_string(plan.floor) + " seed=" + std::to_string(plan.seed);
}

inline std::string p2CaveCarryDoorMarker(const P2CaveCarryDoor& door)
{
    return "P2_CAVE_CARRY_DOOR id=" + door.id + " kind=" + door.kind + " hazard="
           + (door.hazard.empty() ? std::string("none") : door.hazard) + " carry_block="
           + (door.carry_block.empty() ? std::string("none") : door.carry_block) + " key="
           + (door.key.empty() ? std::string("-") : door.key);
}

// Fail-closed parse of the canonical carry plan. Any mismatch, truncation,
// duplicate id, unknown token or inconsistent carry_block/key pair returns false.
inline bool p2CaveCarryParse(std::istream& in, P2CaveCarryPlan& out, std::string& error)
{
    std::string word;
    auto fail = [&error](const std::string& message) {
        error = message;
        return false;
    };
    if (!(in >> word) || word != "P2_CAVE_GATES_1") return fail("bad gates header");
    if (!(in >> word) || word != "cave" || !(in >> out.cave)) return fail("missing cave");
    if (!(in >> word) || word != "floor" || !(in >> out.floor)) return fail("missing floor");
    if (!(in >> word) || word != "seed" || !(in >> out.seed)) return fail("missing seed");
    if (!(in >> word) || word != "geometry" || !(in >> out.geometry)) return fail("missing geometry");
    if (out.geometry != "real" && out.geometry != "mixed" && out.geometry != "proxy")
        return fail("unknown geometry class");

    if (!(in >> word) || word != "doors") return fail("expected doors section");
    int door_count = 0;
    if (!(in >> door_count) || door_count < 0) return fail("bad door count");
    out.doors.clear();
    for (int index = 0; index < door_count; ++index) {
        P2CaveCarryDoor door;
        if (!(in >> door.id >> door.kind >> door.hazard >> door.carry_block >> door.key))
            return fail("truncated door row");
        if (door.hazard == "none") door.hazard.clear();
        if (door.carry_block == "none") door.carry_block.clear();
        if (door.key == "-") door.key.clear();
        if (door.carry_block != "" && door.carry_block != "elec" && door.carry_block != "water")
            return fail("unknown carry_block");
        if (!door.key.empty() && door.key != "yellow" && door.key != "blue")
            return fail("unknown key");
        if (std::string(p2CaveCarryKeyFor(door.carry_block)) != door.key)
            return fail("carry_block/key mismatch");
        if (p2CaveCarryFindDoor(out, door.id)) return fail("duplicate door id");
        out.doors.push_back(door);
    }

    if (!(in >> word) || word != "entrance" || !(in >> out.entrance)) return fail("missing entrance");
    if (!(in >> word) || word != "hole" || !(in >> out.hole)) return fail("missing hole");
    if (!p2CaveCarryFindDoor(out, out.entrance)) return fail("entrance is not a door");
    if (!p2CaveCarryFindDoor(out, out.hole)) return fail("hole is not a door");
    return true;
}
