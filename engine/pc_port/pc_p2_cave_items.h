// Lane 46 (#484, cave wave #468): physical item placement for a generated cave
// floor.
//
// Lane 41 emits a logical observed layout and lane 44 projects it onto a proxy
// room grid whose units already carry item names. This module consumes the host
// bridge's ``P2_CAVE_ITEMS_1`` text form (one entry per item: which host unit it
// must be spawned at, its hazard tag and whether it is a tagged treasure) and
// answers the placement question the native spawner needs: is every tagged
// treasure in a matching-hazard leaf and every untagged item in the entrance
// segment, on a host unit that actually exists in the live proxy layout?
//
// This header is engine-free on purpose: the engine-side spawn/draw/receipt glue
// lives in pc_p2_cave_items.cpp, and this file is what the one-consumer test
// includes. Placement is proxy placement: it is never a generation PASS.
#pragma once

#include "pc_p2_cave_rooms.h"

#include <cstdint>
#include <istream>
#include <string>
#include <vector>

struct P2CaveItemEntry {
    std::string slot_id;  // stable placement uid, e.g. item:leaf_elec_0:0
    std::string item;     // treasure token, e.g. treasure_elec / juji_key_fc
    std::string host;     // host unit id, e.g. leaf_elec_0
    std::string kind;     // host kind as written by the bridge (segment/leaf/...)
    std::string hazard;   // empty when the host is hazard-free
    bool tagged = false;  // true for a hazard-tagged treasure
    int segment_index = 0;
};

struct P2CaveItemPlacement {
    std::string cave;
    int floor = 0;
    std::uint64_t seed = 0;
    std::string source;    // engine / fixture / hand-placed
    std::string geometry;  // "proxy" for this bridge
    std::vector<P2CaveItemEntry> items;
};

// Required hazard for a tagged treasure token, or "" when the token is untagged.
inline const char* p2CaveItemsTagHazard(const std::string& item)
{
    if (item == "treasure_elec") return "elec";
    if (item == "treasure_water") return "water";
    if (item == "treasure_fire") return "fire";
    if (item == "treasure_poison") return "poison";
    return "";
}

inline int p2CaveItemsTaggedCount(const P2CaveItemPlacement& placement)
{
    int tagged = 0;
    for (const P2CaveItemEntry& entry : placement.items) tagged += entry.tagged ? 1 : 0;
    return tagged;
}

inline int p2CaveItemsUntaggedCount(const P2CaveItemPlacement& placement)
{
    return static_cast<int>(placement.items.size()) - p2CaveItemsTaggedCount(placement);
}

// Parse the bridge's P2_CAVE_ITEMS_1 text form. The header line is fixed, then
// ``cave/floor/seed/source/geometry``, ``items N`` with N seven-token rows
// (``slot_id item host kind hazard|none tagged segment_index``). Fail-closed on
// any mismatch, including a tagged flag outside {0,1}.
inline bool p2CaveItemsParse(std::istream& in, P2CaveItemPlacement& out, std::string& error)
{
    std::string word;
    auto fail = [&error](const std::string& message) {
        error = message;
        return false;
    };
    if (!(in >> word) || word != "P2_CAVE_ITEMS_1") return fail("bad items header");
    if (!(in >> word) || word != "cave" || !(in >> out.cave)) return fail("missing cave");
    if (!(in >> word) || word != "floor" || !(in >> out.floor)) return fail("missing floor");
    if (!(in >> word) || word != "seed" || !(in >> out.seed)) return fail("missing seed");
    if (!(in >> word) || word != "source" || !(in >> out.source)) return fail("missing source");
    if (!(in >> word) || word != "geometry" || !(in >> out.geometry)) return fail("missing geometry");
    if (!(in >> word) || word != "items") return fail("expected items section");
    int item_count = 0;
    if (!(in >> item_count) || item_count < 0) return fail("bad items count");
    out.items.clear();
    for (int index = 0; index < item_count; ++index) {
        P2CaveItemEntry entry;
        int tagged = 0;
        if (!(in >> entry.slot_id >> entry.item >> entry.host >> entry.kind >> entry.hazard
                 >> tagged >> entry.segment_index))
            return fail("truncated item row");
        if (entry.hazard == "none") entry.hazard.clear();
        if (tagged != 0 && tagged != 1) return fail("tagged flag must be 0 or 1");
        entry.tagged = tagged == 1;
        out.items.push_back(entry);
    }
    return true;
}

// Placement validation against the live proxy rooms layout. Every entry's host
// must exist and match the written kind; a tagged item must sit in a leaf whose
// hazard equals its tag; an untagged item must sit on a segment in the entrance
// segment. The cave/floor/seed must also match the rooms layout so a stale
// config can never be spawned.
inline bool p2CaveItemsValidatePlacement(const P2CaveItemPlacement& placement,
                                         const P2CaveRoomLayout& rooms, std::string& error)
{
    auto fail = [&error](const std::string& message) {
        error = message;
        return false;
    };
    if (placement.cave != rooms.cave) return fail("items cave differs from rooms cave");
    if (placement.floor != rooms.floor) return fail("items floor differs from rooms floor");
    if (placement.seed != rooms.seed) return fail("items seed differs from rooms seed");
    const P2CaveRoomUnit* entrance = p2CaveRoomsFind(rooms, rooms.entrance);
    if (!entrance) return fail("rooms entrance is not a unit");
    for (const P2CaveItemEntry& entry : placement.items) {
        const P2CaveRoomUnit* host = p2CaveRoomsFind(rooms, entry.host);
        if (!host) return fail("item host is not a rooms unit: " + entry.host);
        if (host->kind != entry.kind) return fail("item host kind drift: " + entry.host);
        const std::string required = p2CaveItemsTagHazard(entry.item);
        if (entry.tagged) {
            if (required.empty()) return fail("unknown tagged treasure token: " + entry.item);
            if (host->kind != "leaf")
                return fail("tagged item " + entry.item + " must sit on a leaf, not " + host->kind);
            if (host->hazard != required)
                return fail("tagged item " + entry.item + " needs a " + required + " leaf");
        } else {
            if (!required.empty())
                return fail("item " + entry.item + " is tagged but not flagged tagged");
            if (host->kind != "segment")
                return fail("untagged item " + entry.item + " must sit on a segment");
            if (host->segment_index != entrance->segment_index)
                return fail("untagged item " + entry.item + " must sit in the entrance segment");
        }
    }
    return true;
}

// One-line evidence marker. Mirrors p2CaveRoomsMarker's shape.
inline std::string p2CaveItemsMarker(const P2CaveItemPlacement& placement)
{
    return "P2_CAVE_ITEMS_READY items=" + std::to_string(placement.items.size()) + " tagged="
           + std::to_string(p2CaveItemsTaggedCount(placement)) + " untagged="
           + std::to_string(p2CaveItemsUntaggedCount(placement)) + " geometry="
           + (placement.geometry.empty() ? std::string("proxy") : placement.geometry) + " cave="
           + placement.cave + " floor=" + std::to_string(placement.floor) + " seed="
           + std::to_string(placement.seed);
}

// Stable, position-free projection used to prove re-entry invariance: the same
// seeded table yields the same item->host mapping across re-rolls/restarts.
inline std::string p2CaveItemsProjection(const P2CaveItemPlacement& placement)
{
    std::string projection = "P2_CAVE_ITEMS_PROJECTION cave=" + placement.cave + " floor="
                             + std::to_string(placement.floor) + " seed="
                             + std::to_string(placement.seed);
    for (const P2CaveItemEntry& entry : placement.items) {
        projection += " [" + entry.slot_id + "|" + entry.item + "|" + entry.host + "|"
                      + (entry.tagged ? "tagged" : "untagged") + "]";
    }
    return projection;
}
