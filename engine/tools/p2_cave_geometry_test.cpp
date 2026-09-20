// Lane 45 (#483): one-consumer gate for real cave-unit geometry + electric gate.
//
// Proves, over the lane-41 forest_1 floor-1 layout (seed 468001) rendered into the
// P2_CAVE_GEOMETRY_1 plan form:
//   * the plan parses to the same cave/floor/seed/salt, node order and ids;
//   * a fully-real plan with a placed electric gate is a real-geometry plan;
//   * a proxy plan is never accepted as real;
//   * an electric leaf without a placed gate actor is rejected;
//   * malformed/truncated/duplicate/unknown-class text is rejected.
// With argv[1] it also parses a host-written geometry config and prints the marker.
#include "pc_p2_cave_geometry.h"

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

static const char* kRealPlan =
    "P2_CAVE_GEOMETRY_1\n"
    "cave forest_1\n"
    "floor 1\n"
    "seed 468001\n"
    "salt 0\n"
    "geometry real\n"
    "units 6\n"
    "forest_1:f1:segment:0 segment none proxy - 0 0\n"
    "choke_water_0 choke water real courses/pikmin2room/p2cave_room_north3_1_tsuchi.mod 0 48\n"
    "forest_1:f1:segment:1 segment none proxy - 0 96\n"
    "leaf_elec_0 leaf elec real courses/pikmin2room/p2cave_room_north3_1_tsuchi.mod 48 0\n"
    "leaf_water_0 leaf water real courses/pikmin2room/p2cave_room_north3_1_tsuchi.mod 48 96\n"
    "gate:leaf_elec_0 gate elec real courses/pikmin2room/p2cave_e_gate.mod 96 0\n"
    "gates 2\n"
    "leaf_elec_0 elec p2_elec_gate courses/pikmin2room/p2cave_e_gate.mod 1\n"
    "gate:leaf_elec_0 elec p2_elec_gate courses/pikmin2room/p2cave_e_gate.mod 1\n"
    "entrance forest_1:f1:segment:0\n"
    "hole forest_1:f1:segment:1\n";

// Same layout with no converted models: every node is a proxy.
static const char* kProxyPlan =
    "P2_CAVE_GEOMETRY_1\n"
    "cave forest_1\n"
    "floor 1\n"
    "seed 468001\n"
    "salt 0\n"
    "geometry proxy\n"
    "units 5\n"
    "forest_1:f1:segment:0 segment none proxy - 0 0\n"
    "choke_water_0 choke water proxy - 0 48\n"
    "forest_1:f1:segment:1 segment none proxy - 0 96\n"
    "leaf_elec_0 leaf elec proxy - 48 0\n"
    "leaf_water_0 leaf water proxy - 48 96\n"
    "gates 0\n"
    "entrance forest_1:f1:segment:0\n"
    "hole forest_1:f1:segment:1\n";

static bool parse(const char* text, P2CaveGeometryPlan& plan)
{
    std::istringstream in(text);
    std::string error;
    return p2CaveGeometryParse(in, plan, error);
}

int main(int argc, char** argv)
{
    P2CaveGeometryPlan plan;
    CHECK(parse(kRealPlan, plan));
    CHECK(plan.cave == "forest_1");
    CHECK(plan.floor == 1);
    CHECK(plan.seed == 468001);
    CHECK(plan.salt == 0);
    CHECK(plan.geometry == "real");
    CHECK(plan.nodes.size() == 6);
    CHECK(plan.gates.size() == 2);
    CHECK(plan.entrance == "forest_1:f1:segment:0");
    CHECK(plan.hole == "forest_1:f1:segment:1");
    CHECK(plan.nodes[1].id == "choke_water_0");
    CHECK(plan.nodes[1].kind == "choke");
    CHECK(plan.nodes[1].hazard == "water");
    CHECK(plan.nodes[1].real);
    CHECK(plan.nodes[1].model == "courses/pikmin2room/p2cave_room_north3_1_tsuchi.mod");
    CHECK(plan.nodes[0].kind == "segment");
    CHECK(!plan.nodes[0].real);
    CHECK(p2CaveGeometryIsReal(plan));
    const std::string marker = p2CaveGeometryMarker(plan);
    CHECK(marker == "P2_CAVE_GEOMETRY_READY nodes=6 real=4 proxy=2 gate_actors=2 "
                    "geometry=real cave=forest_1 floor=1 seed=468001 salt=0");
    const std::string nodeMarker = p2CaveGeometryNodeMarker(plan.nodes[3]);
    CHECK(nodeMarker == "P2_CAVE_GEOMETRY_NODE id=leaf_elec_0 kind=leaf hazard=elec class=real "
                        "model=courses/pikmin2room/p2cave_room_north3_1_tsuchi.mod proxy=0");
    CHECK(p2CaveGeometryGateFor(plan, "leaf_elec_0") != nullptr);
    CHECK(p2CaveGeometryGateFor(plan, "leaf_water_0") == nullptr);

    P2CaveGeometryPlan proxy;
    CHECK(parse(kProxyPlan, proxy));
    CHECK(!p2CaveGeometryIsReal(proxy));
    CHECK(p2CaveGeometryMarker(proxy).find("geometry=proxy") != std::string::npos);

    // An electric leaf with no placed gate actor is not a real plan.
    std::string missing = std::string(kRealPlan);
    const std::string gateLine = "leaf_elec_0 elec p2_elec_gate "
                                 "courses/pikmin2room/p2cave_e_gate.mod 1\n";
    missing.replace(missing.find(gateLine), gateLine.size(), "");
    missing.replace(missing.find("gates 2"), 7, "gates 1");
    P2CaveGeometryPlan noGate;
    CHECK(parse(missing.c_str(), noGate));
    CHECK(!p2CaveGeometryIsReal(noGate));

    P2CaveGeometryPlan bad;
    CHECK(!parse("P2_CAVE_GEOMETRY_1\ncave forest_1\nfloor 1\nseed 1\nsalt 0\n"
                 "geometry proxy\nunits 1\nid segment\nentrance id\nhole id\n",
                 bad));
    CHECK(!parse("NOPE\ncave x\n", bad));
    std::string duplicate = std::string(kRealPlan);
    duplicate.replace(duplicate.find("forest_1:f1:segment:1 segment"),
                      21, "forest_1:f1:segment:0");
    CHECK(!parse(duplicate.c_str(), bad));
    std::string badClass = std::string(kRealPlan);
    badClass.replace(badClass.find("geometry real"), 13, "geometry bananas");
    CHECK(!parse(badClass.c_str(), bad));
    CHECK(!parse("P2_CAVE_GEOMETRY_1\ncave forest_1\nfloor 1\nseed 1\nsalt 0\n"
                 "geometry real\nunits 1\nchoke_water_0 choke water real "
                 "courses/pikmin2room/x.mod 0 48\n",
                 bad));

    if (argc > 1) {
        std::ifstream in(argv[1]);
        P2CaveGeometryPlan host;
        std::string error;
        CHECK(p2CaveGeometryParse(in, host, error));
        std::printf("%s\n", p2CaveGeometryMarker(host).c_str());
    }
    std::puts("PASS p2 cave geometry: real model plan, proxy rejection, gate actor binding");
    std::fflush(stdout);
    return 0;
}
