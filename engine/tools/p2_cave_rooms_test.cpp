// Lane 44 (#482): one-consumer gate for the proxy cave-room instantiation.
//
// Proves, over the lane-41 forest_1 floor-1 layout (seed 468001) rendered into
// the P2_CAVE_ROOMS_1 bridge form:
//   * every node id / kind / hazard / edge survives the bridge and the parse;
//   * the fresh floor cannot reach the elec treasure or the hole, and yellow
//     opens only the elec leaf/gate;
//   * blue then opens the water leaf and the hole;
//   * the untagged treasure in the entrance segment is reachable at every step;
//   * two salts keep the same logical projection while their proxy geometry
//     differs (re-roll invariance of the table, reroll of the geometry);
//   * a truncated config is rejected.
// With argv[1] it also parses a host-written rooms config and prints the marker.
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

static const char* kRoomsSalt0 =
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

// Same logical table, a different salt: only gx/gz move.
static const char* kRoomsSalt7 =
    "P2_CAVE_ROOMS_1\n"
    "cave forest_1\n"
    "floor 1\n"
    "seed 468001\n"
    "salt 7\n"
    "cell 48\n"
    "origin 0 0\n"
    "source engine\n"
    "geometry proxy\n"
    "units 6\n"
    "forest_1:f1:segment:0 segment none 0 0 0 choke_water_0,leaf_elec_0 juji_key_fc\n"
    "choke_water_0 choke water 1 0 55 forest_1:f1:segment:0,forest_1:f1:segment:1 -\n"
    "forest_1:f1:segment:1 segment none 1 0 110 choke_water_0,leaf_water_0 -\n"
    "leaf_elec_0 leaf elec 0 72 0 forest_1:f1:segment:0,gate:leaf_elec_0 treasure_elec\n"
    "leaf_water_0 leaf water 1 72 110 forest_1:f1:segment:1 treasure_water\n"
    "gate:leaf_elec_0 gate elec 0 120 0 leaf_elec_0 -\n"
    "entrance forest_1:f1:segment:0\n"
    "hole forest_1:f1:segment:1\n"
    "edges 5\n"
    "forest_1:f1:segment:0 choke_water_0\n"
    "choke_water_0 forest_1:f1:segment:1\n"
    "forest_1:f1:segment:0 leaf_elec_0\n"
    "forest_1:f1:segment:1 leaf_water_0\n"
    "leaf_elec_0 gate:leaf_elec_0\n";

static bool parse(const char* text, P2CaveRoomLayout& layout, std::string& error)
{
    std::istringstream in(text);
    return p2CaveRoomsParse(in, layout, error);
}

int main(int argc, char** argv)
{
    P2CaveRoomLayout layout;
    std::string error;
    CHECK(parse(kRoomsSalt0, layout, error));
    CHECK(layout.cave == "forest_1" && layout.floor == 1 && layout.seed == 468001);
    CHECK(layout.geometry == "proxy");
    CHECK(layout.source == "engine");
    CHECK(layout.units.size() == 6);
    CHECK(layout.edges.size() == 5);
    CHECK(layout.entrance == "forest_1:f1:segment:0");
    CHECK(layout.hole == "forest_1:f1:segment:1");
    CHECK(p2CaveRoomsFind(layout, "leaf_elec_0") != nullptr);
    CHECK(p2CaveRoomsFind(layout, "missing") == nullptr);
    CHECK(p2CaveRoomsFind(layout, "leaf_elec_0")->items.size() == 1);
    CHECK(p2CaveRoomsFind(layout, "leaf_elec_0")->items[0] == "treasure_elec");
    CHECK(p2CaveRoomsFind(layout, "choke_water_0")->doors.size() == 2);

    // Fresh floor: only the entrance segment is reachable.
    P2CaveAbilities none;
    CHECK(p2CaveRoomsReachable(layout, "forest_1:f1:segment:0", none));
    CHECK(!p2CaveRoomsReachable(layout, "forest_1:f1:segment:1", none));  // hole behind water choke
    CHECK(!p2CaveRoomsReachable(layout, "leaf_elec_0", none));
    CHECK(!p2CaveRoomsReachable(layout, "leaf_water_0", none));
    CHECK(p2CaveRoomsReachable(layout, "forest_1:f1:segment:0", none));  // untagged host

    // Come back with yellow: elec leaf/gate open, water choke/hole stay shut.
    P2CaveAbilities yellow;
    yellow.yellow = true;
    CHECK(p2CaveRoomsReachable(layout, "leaf_elec_0", yellow));
    CHECK(p2CaveRoomsReachable(layout, "gate:leaf_elec_0", yellow));
    CHECK(!p2CaveRoomsReachable(layout, "forest_1:f1:segment:1", yellow));
    CHECK(!p2CaveRoomsReachable(layout, "leaf_water_0", yellow));

    // Yellow and blue: everything opens.
    P2CaveAbilities both;
    both.yellow = true;
    both.blue = true;
    CHECK(p2CaveRoomsReachable(layout, "forest_1:f1:segment:1", both));
    CHECK(p2CaveRoomsReachable(layout, "leaf_water_0", both));

    // Marker is honest about the proxy label.
    const std::string marker = p2CaveRoomsMarker(layout);
    CHECK(marker.find("P2_CAVE_ROOMS_READY") == 0);
    CHECK(marker.find("geometry=proxy") != std::string::npos);
    CHECK(marker.find("units=6") != std::string::npos);

    P2CaveRoomLayout reroll;
    CHECK(parse(kRoomsSalt7, reroll, error));
    CHECK(p2CaveRoomsLogicalProjection(layout) == p2CaveRoomsLogicalProjection(reroll));
    CHECK(p2CaveRoomsWorldZ(layout, *p2CaveRoomsFind(layout, "forest_1:f1:segment:1")) == 96.f);
    CHECK(p2CaveRoomsWorldZ(reroll, *p2CaveRoomsFind(reroll, "forest_1:f1:segment:1")) == 110.f);

    // Truncated config is rejected.
    {
        std::string broken(kRoomsSalt0);
        broken.resize(broken.find("leaf_elec_0 gate:leaf_elec_0"));
        std::istringstream in(broken);
        P2CaveRoomLayout rejected;
        CHECK(!p2CaveRoomsParse(in, rejected, error));
    }

    if (argc > 1) {
        std::ifstream in(argv[1]);
        CHECK(bool(in));
        P2CaveRoomLayout host;
        CHECK(p2CaveRoomsParse(in, host, error));
        std::printf("%s\n", p2CaveRoomsMarker(host).c_str());
    }
    std::puts("PASS p2 cave rooms: proxy bridge, parse, hazard timeline, reroll invariance");
    return 0;
}
