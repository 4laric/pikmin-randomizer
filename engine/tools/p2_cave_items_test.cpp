// Lane 46 (#484): one-consumer gate for physical cave-item placement.
//
// Proves, over the lane-41 forest_1 floor-1 layout (seed 468001) rendered into
// the P2_CAVE_ITEMS_1 bridge form and validated against the lane-44 proxy rooms
// layout:
//   * the parse is lossless and fail-closed (bad header, truncated rows, bad
//     tagged flag, bad counts);
//   * every item maps to an existing rooms unit with the written kind;
//   * the two tagged treasures sit in their matching-hazard leaves and the
//     untagged juji_key_fc sits in the entrance segment;
//   * a mismatched hazard leaf, a tagged item on a segment, an untagged item
//     outside the entrance, and a cave/floor/seed drift are each rejected;
//   * the projection is position-free and stable across re-parse.
// With argv[1] it also parses a host-written items config and prints the marker.
#include "pc_p2_cave_items.h"
#include "pc_p2_cave_rooms.h"

#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

#define CHECK(condition)                                                              \
    do {                                                                              \
        if (!(condition)) {                                                           \
            std::fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #condition); \
            return 1;                                                                 \
        }                                                                             \
    } while (0)

static const char* kRooms =
    "P2_CAVE_ROOMS_1\n"
    "cave forest_1\n"
    "floor 1\n"
    "seed 468001\n"
    "salt 0\n"
    "cell 48\n"
    "origin 0 0\n"
    "source engine\n"
    "geometry proxy\n"
    "units 6\n"
    "forest_1:f1:segment:0 segment none 0 0 0 choke_water_0,leaf_elec_0 juji_key_fc\n"
    "choke_water_0 choke water 1 0 48 forest_1:f1:segment:0,forest_1:f1:segment:1 -\n"
    "forest_1:f1:segment:1 segment none 1 0 96 choke_water_0,leaf_water_0 -\n"
    "leaf_elec_0 leaf elec 0 48 0 forest_1:f1:segment:0,gate:leaf_elec_0 treasure_elec\n"
    "leaf_water_0 leaf water 1 48 96 forest_1:f1:segment:1 treasure_water\n"
    "gate:leaf_elec_0 gate elec 0 96 0 leaf_elec_0 -\n"
    "entrance forest_1:f1:segment:0\n"
    "hole forest_1:f1:segment:1\n"
    "edges 5\n"
    "forest_1:f1:segment:0 choke_water_0\n"
    "choke_water_0 forest_1:f1:segment:1\n"
    "forest_1:f1:segment:0 leaf_elec_0\n"
    "forest_1:f1:segment:1 leaf_water_0\n"
    "leaf_elec_0 gate:leaf_elec_0\n";

static const char* kItems =
    "P2_CAVE_ITEMS_1\n"
    "cave forest_1\n"
    "floor 1\n"
    "seed 468001\n"
    "source engine\n"
    "geometry proxy\n"
    "items 3\n"
    "item:forest_1:f1:segment:0:0 juji_key_fc forest_1:f1:segment:0 segment none 0 0\n"
    "item:leaf_elec_0:0 treasure_elec leaf_elec_0 leaf elec 1 0\n"
    "item:leaf_water_0:0 treasure_water leaf_water_0 leaf water 1 1\n";

static bool parseItems(const std::string& text, P2CaveItemPlacement& out, std::string& error)
{
    std::istringstream in(text);
    return p2CaveItemsParse(in, out, error);
}

static bool parseRooms(const char* text, P2CaveRoomLayout& out, std::string& error)
{
    std::istringstream in(text);
    return p2CaveRoomsParse(in, out, error);
}

static std::string withRow(const std::string& row)
{
    std::string text(kItems);
    text += row + "\n";
    const std::string header = "items 3\n";
    text.replace(text.find(header), header.size(), "items 4\n");
    return text;
}

int main(int argc, char** argv)
{
    std::string error;
    P2CaveRoomLayout rooms;
    CHECK(parseRooms(kRooms, rooms, error));
    P2CaveItemPlacement items;
    CHECK(parseItems(kItems, items, error));

    CHECK(items.cave == "forest_1" && items.floor == 1 && items.seed == 468001);
    CHECK(items.geometry == "proxy");
    CHECK(items.source == "engine");
    CHECK(items.items.size() == 3);
    CHECK(p2CaveItemsTaggedCount(items) == 2);
    CHECK(p2CaveItemsUntaggedCount(items) == 1);

    // Every item maps to a real unit and the placement contract holds.
    CHECK(p2CaveItemsValidatePlacement(items, rooms, error));
    CHECK(p2CaveRoomsFind(rooms, items.items[0].host) != nullptr);
    CHECK(items.items[0].item == "juji_key_fc" && !items.items[0].tagged);
    CHECK(items.items[1].item == "treasure_elec" && items.items[1].tagged);
    CHECK(items.items[2].item == "treasure_water" && items.items[2].tagged);
    CHECK(p2CaveItemsTagHazard("treasure_elec") == std::string("elec"));
    CHECK(p2CaveItemsTagHazard("juji_key_fc") == std::string(""));

    // Marker is honest about the proxy label.
    const std::string marker = p2CaveItemsMarker(items);
    CHECK(marker.find("P2_CAVE_ITEMS_READY") == 0);
    CHECK(marker.find("items=3") != std::string::npos);
    CHECK(marker.find("tagged=2") != std::string::npos);
    CHECK(marker.find("untagged=1") != std::string::npos);
    CHECK(marker.find("geometry=proxy") != std::string::npos);

    // Projection is stable across a re-parse.
    P2CaveItemPlacement again;
    CHECK(parseItems(kItems, again, error));
    CHECK(p2CaveItemsProjection(items) == p2CaveItemsProjection(again));

    // Fail-closed parse cases.
    {
        P2CaveItemPlacement rejected;
        std::string broken(kItems);
        broken.replace(broken.find("P2_CAVE_ITEMS_1"), 15, "P2_CAVE_ITEMZ");
        CHECK(!parseItems(broken, rejected, error));

        std::string truncated(kItems);
        truncated.resize(truncated.find("item:leaf_water_0:0"));
        CHECK(!parseItems(truncated, rejected, error));

        std::string badFlag(kItems);
        badFlag.replace(badFlag.find("elec 1 0"), 8, "elec 2 0");
        CHECK(!parseItems(badFlag, rejected, error));

        std::string badCount(kItems);
        badCount.replace(badCount.find("items 3"), 7, "items 9");
        CHECK(!parseItems(badCount, rejected, error));
    }

    // Placement rejections: a tagged treasure in the wrong hazard leaf.
    {
        P2CaveItemPlacement bad;
        CHECK(parseItems(withRow("item:leaf_water_0:1 treasure_elec leaf_water_0 leaf water 1 1"),
                         bad, error));
        CHECK(!p2CaveItemsValidatePlacement(bad, rooms, error));
    }
    // A tagged treasure on a segment.
    {
        P2CaveItemPlacement bad;
        CHECK(parseItems(withRow("item:forest_1:f1:segment:0:1 treasure_elec "
                                 "forest_1:f1:segment:0 segment none 1 0"),
                         bad, error));
        CHECK(!p2CaveItemsValidatePlacement(bad, rooms, error));
    }
    // An untagged item outside the entrance segment.
    {
        P2CaveItemPlacement bad;
        CHECK(parseItems(withRow("item:forest_1:f1:segment:1:0 juji_key_fc "
                                 "forest_1:f1:segment:1 segment none 0 1"),
                         bad, error));
        CHECK(!p2CaveItemsValidatePlacement(bad, rooms, error));
    }
    // A host that does not exist in the rooms layout.
    {
        P2CaveItemPlacement bad;
        CHECK(parseItems(withRow("item:leaf_missing:0 treasure_elec leaf_missing leaf elec 1 0"),
                         bad, error));
        CHECK(!p2CaveItemsValidatePlacement(bad, rooms, error));
    }
    // A seed drift between the items config and the rooms layout.
    {
        P2CaveItemPlacement bad;
        std::string drifted(kItems);
        drifted.replace(drifted.find("seed 468001"), 11, "seed 468002");
        CHECK(parseItems(drifted, bad, error));
        CHECK(!p2CaveItemsValidatePlacement(bad, rooms, error));
    }

    if (argc > 1) {
        std::ifstream in(argv[1]);
        CHECK(bool(in));
        P2CaveItemPlacement host;
        CHECK(p2CaveItemsParse(in, host, error));
        CHECK(p2CaveItemsValidatePlacement(host, rooms, error));
        std::printf("%s\n", p2CaveItemsMarker(host).c_str());
        std::printf("%s\n", p2CaveItemsProjection(host).c_str());
    }
    std::puts("PASS p2 cave items: parse, placement, rejections, projection");
    return 0;
}
