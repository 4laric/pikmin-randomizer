// Lane 44 (#482, cave wave #468): proxy room/unit instantiation for a generated
// cave floor.
//
// Lane 41 emits a logical observed layout (``p2-cave-observed-layout/1``); the PC
// port has no P2 MapUnit / MapUnitInterface room loader, so this module consumes
// the host bridge's ``P2_CAVE_ROOMS_1`` text form (one proxy unit per layout node
// with a deterministic grid cell) and answers the live questions a playable floor
// needs: where a unit is, whether the current squad can enter it, and whether a
// target is reachable from the entrance. Node ids, kinds, hazards, segment
// indices, items and edges are preserved verbatim so lane 40's checker still
// matches.
//
// This header is engine-free on purpose: the engine-side draw/tick/glue lives in
// pc_p2_cave_rooms.cpp, and this file is what the one-consumer test includes.
//
// The geometry is proxy geometry. ``P2CaveRoomLayout::geometry`` is expected to
// be "proxy" and callers must label it as such; it is never a generation PASS.

#pragma once

#include <algorithm>
#include <cstdint>
#include <istream>
#include <ostream>
#include <string>
#include <utility>
#include <vector>

struct P2CaveRoomUnit {
    std::string id;
    std::string kind;      // segment / choke / leaf / bud / gate
    std::string hazard;    // empty when the node is hazard-free
    int segment_index = 0;
    int gx = 0;
    int gz = 0;
    std::vector<std::string> doors;
    std::vector<std::string> items;
};

struct P2CaveRoomLayout {
    std::string cave;
    int floor = 0;
    std::uint64_t seed = 0;
    int salt = 0;
    int cell = 48;
    int origin_x = 0;
    int origin_z = 0;
    std::string source;    // engine / fixture / hand-placed
    std::string geometry;  // "proxy" for this bridge
    std::vector<P2CaveRoomUnit> units;
    std::vector<std::pair<std::string, std::string>> edges;
    std::string entrance;
    std::string hole;
};

// The squad's hard-hazard keys. Only hard hazards gate carrying (fan-out model).
struct P2CaveAbilities {
    bool blue = false;
    bool yellow = false;
    bool red = false;
    bool white = false;

    bool has(const std::string& key) const
    {
        if (key == "blue") return blue;
        if (key == "yellow") return yellow;
        if (key == "red") return red;
        if (key == "white") return white;
        return false;
    }

    void grant(const std::string& key)
    {
        if (key == "blue") blue = true;
        else if (key == "yellow") yellow = true;
        else if (key == "red") red = true;
        else if (key == "white") white = true;
    }
};

inline const char* p2CaveRoomsHazardKey(const std::string& hazard)
{
    if (hazard == "water") return "blue";
    if (hazard == "elec") return "yellow";
    if (hazard == "fire") return "red";
    if (hazard == "poison") return "white";
    return "";
}

inline bool p2CaveRoomsHardHazard(const std::string& hazard)
{
    return hazard == "water" || hazard == "elec";
}

inline bool p2CaveRoomsIsGateKind(const std::string& kind)
{
    return kind == "choke" || kind == "leaf" || kind == "gate";
}

inline float p2CaveRoomsWorldX(const P2CaveRoomLayout& layout, const P2CaveRoomUnit& unit)
{
    return static_cast<float>(layout.origin_x + unit.gx);
}

inline float p2CaveRoomsWorldZ(const P2CaveRoomLayout& layout, const P2CaveRoomUnit& unit)
{
    return static_cast<float>(layout.origin_z + unit.gz);
}

inline const P2CaveRoomUnit* p2CaveRoomsFind(const P2CaveRoomLayout& layout, const std::string& id)
{
    for (const P2CaveRoomUnit& unit : layout.units) {
        if (unit.id == id) return &unit;
    }
    return nullptr;
}

// A node can be entered only when it is not a hard hazard the squad cannot key.
inline bool p2CaveRoomsUnitEnterable(const P2CaveRoomLayout&, const P2CaveRoomUnit& unit,
                                     const P2CaveAbilities& abilities)
{
    if (!p2CaveRoomsIsGateKind(unit.kind)) return true;
    if (!p2CaveRoomsHardHazard(unit.hazard)) return true;
    return abilities.has(p2CaveRoomsHazardKey(unit.hazard));
}

// Reachability from the entrance under the given keys. Buds grant their hazard
// key once reachable (the model's bud alternative), so this iterates to a
// fixpoint bounded by the unit count.
inline bool p2CaveRoomsReachable(const P2CaveRoomLayout& layout, const std::string& target,
                                 const P2CaveAbilities& abilities)
{
    P2CaveAbilities effective = abilities;
    std::vector<std::string> reachable;
    for (int iteration = 0; iteration <= static_cast<int>(layout.units.size()); ++iteration) {
        std::vector<std::string> seen;
        std::vector<std::string> stack;
        seen.push_back(layout.entrance);
        stack.push_back(layout.entrance);
        while (!stack.empty()) {
            const std::string current = stack.back();
            stack.pop_back();
            for (const std::pair<std::string, std::string>& edge : layout.edges) {
                std::string next;
                if (edge.first == current) next = edge.second;
                else if (edge.second == current) next = edge.first;
                else continue;
                if (std::find(seen.begin(), seen.end(), next) != seen.end()) continue;
                const P2CaveRoomUnit* unit = p2CaveRoomsFind(layout, next);
                if (!unit || !p2CaveRoomsUnitEnterable(layout, *unit, effective)) continue;
                seen.push_back(next);
                stack.push_back(next);
            }
        }
        bool changed = false;
        for (const std::string& id : seen) {
            const P2CaveRoomUnit* unit = p2CaveRoomsFind(layout, id);
            if (!unit || unit->kind != "bud") continue;
            const std::string key = p2CaveRoomsHazardKey(unit->hazard);
            if (!key[0] || effective.has(key)) continue;
            effective.grant(key);
            changed = true;
        }
        reachable = seen;
        if (!changed) break;
    }
    return std::find(reachable.begin(), reachable.end(), target) != reachable.end();
}

// Canonical, position-free projection used to prove re-roll invariance: the same
// table at two different salts has identical projections but different geometry.
inline std::string p2CaveRoomsLogicalProjection(const P2CaveRoomLayout& layout)
{
    std::vector<std::string> unit_tokens;
    for (const P2CaveRoomUnit& unit : layout.units) {
        unit_tokens.push_back(unit.id + "|" + unit.kind + "|" + unit.hazard + "|"
                             + std::to_string(unit.segment_index));
    }
    std::sort(unit_tokens.begin(), unit_tokens.end());
    std::vector<std::string> edge_tokens;
    for (const std::pair<std::string, std::string>& edge : layout.edges) {
        edge_tokens.push_back(edge.first < edge.second ? edge.first + "|" + edge.second
                                                       : edge.second + "|" + edge.first);
    }
    std::sort(edge_tokens.begin(), edge_tokens.end());
    std::string projection = layout.cave + "|" + std::to_string(layout.floor) + "|";
    projection += layout.entrance + "|" + layout.hole;
    for (const std::string& token : unit_tokens) projection += "|" + token;
    for (const std::string& token : edge_tokens) projection += "|" + token;
    return projection;
}

namespace p2caverooms_detail {
inline std::vector<std::string> splitCsv(const std::string& value, const char* empty)
{
    std::vector<std::string> result;
    if (value == empty) return result;
    std::string current;
    for (char ch : value) {
        if (ch == ',') {
            result.push_back(current);
            current.clear();
        } else {
            current.push_back(ch);
        }
    }
    result.push_back(current);
    return result;
}
}  // namespace p2caverooms_detail

// Parse the bridge's P2_CAVE_ROOMS_1 text form. The header line is fixed, then
// ``cave/floor/seed/salt/cell/origin``, two optional ``source``/``geometry``
// lines, ``units N`` with N eight-token rows, ``entrance``/``hole`` and
// ``edges N`` with N id pairs. Fail-closed on any mismatch.
inline bool p2CaveRoomsParse(std::istream& in, P2CaveRoomLayout& out, std::string& error)
{
    std::string word;
    auto fail = [&error](const std::string& message) {
        error = message;
        return false;
    };
    if (!(in >> word) || word != "P2_CAVE_ROOMS_1") return fail("bad rooms header");
    if (!(in >> word) || word != "cave" || !(in >> out.cave)) return fail("missing cave");
    if (!(in >> word) || word != "floor" || !(in >> out.floor)) return fail("missing floor");
    if (!(in >> word) || word != "seed" || !(in >> out.seed)) return fail("missing seed");
    if (!(in >> word) || word != "salt" || !(in >> out.salt)) return fail("missing salt");
    if (!(in >> word) || word != "cell" || !(in >> out.cell)) return fail("missing cell");
    if (!(in >> word) || word != "origin" || !(in >> out.origin_x) || !(in >> out.origin_z))
        return fail("missing origin");
    if (in >> word) {
        if (word == "source") {
            if (!(in >> out.source)) return fail("missing source token");
            if (!(in >> word)) return fail("missing section after source");
        }
        if (word == "geometry") {
            if (!(in >> out.geometry)) return fail("missing geometry token");
            if (!(in >> word)) return fail("missing section after geometry");
        }
        if (word != "units") return fail("expected units section");
    } else {
        return fail("missing units section");
    }
    int unit_count = 0;
    if (!(in >> unit_count) || unit_count < 0) return fail("bad unit count");
    out.units.clear();
    for (int index = 0; index < unit_count; ++index) {
        P2CaveRoomUnit unit;
        std::string doors, items;
        if (!(in >> unit.id >> unit.kind >> unit.hazard >> unit.segment_index >> unit.gx
                 >> unit.gz >> doors >> items))
            return fail("truncated unit row");
        if (unit.hazard == "none") unit.hazard.clear();
        unit.doors = p2caverooms_detail::splitCsv(doors, "-");
        unit.items = p2caverooms_detail::splitCsv(items, "-");
        out.units.push_back(unit);
    }
    if (!(in >> word) || word != "entrance" || !(in >> out.entrance)) return fail("missing entrance");
    if (!(in >> word) || word != "hole" || !(in >> out.hole)) return fail("missing hole");
    if (!(in >> word) || word != "edges") return fail("missing edges");
    int edge_count = 0;
    if (!(in >> edge_count) || edge_count < 0) return fail("bad edge count");
    out.edges.clear();
    for (int index = 0; index < edge_count; ++index) {
        std::pair<std::string, std::string> edge;
        if (!(in >> edge.first >> edge.second)) return fail("truncated edge row");
        out.edges.push_back(edge);
    }
    if (!p2CaveRoomsFind(out, out.entrance)) return fail("entrance is not a unit");
    if (!p2CaveRoomsFind(out, out.hole)) return fail("hole is not a unit");
    return true;
}

// One-line evidence marker. Mirrors p2CaveLayoutMarker's shape.
inline std::string p2CaveRoomsMarker(const P2CaveRoomLayout& layout)
{
    int proxies = 0;
    int hard = 0;
    for (const P2CaveRoomUnit& unit : layout.units) {
        ++proxies;
        hard += p2CaveRoomsHardHazard(unit.hazard) ? 1 : 0;
    }
    return "P2_CAVE_ROOMS_READY units=" + std::to_string(proxies) + " geometry="
           + (layout.geometry.empty() ? std::string("proxy") : layout.geometry) + " cave="
           + layout.cave + " floor=" + std::to_string(layout.floor) + " seed="
           + std::to_string(layout.seed) + " salt=" + std::to_string(layout.salt) + " hard="
           + std::to_string(hard) + " entrance=" + layout.entrance + " hole=" + layout.hole;
}
