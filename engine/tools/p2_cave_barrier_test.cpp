// Geometry/parser regression only. Real attachment release requires the engine fixture.
#include "pc_p2_cave_barrier.h"
#include <iostream>
#include <sstream>
#include <stdexcept>

static void require(bool value) { if (!value) throw std::runtime_error("barrier assertion failed"); }
int main()
{
    P2CaveCarryPlan plan;
    plan.cave = "forest_1"; plan.floor = 1; plan.seed = 930;
    plan.doors = {{"electric", "leaf", "elec", "elec", "yellow"},
                  {"water", "choke", "water", "water", "blue"},
                  {"bud", "bud", "water", "", ""}};
    const std::string prefix = "P2_CAVE_BARRIERS_1 cave forest_1 floor 1 seed 930 barriers 2\n";
    const std::string electric = "electric -60 -20 -460 60 130 -440\n";
    const std::string water = "water 350 -20 -60 450 130 60\n";
    std::vector<P2CaveBarrier> boxes;
    auto parse = [&](const std::string& text) {
        std::istringstream in(text); std::string error;
        return p2CaveBarrierParse(in, plan, boxes, error);
    };
    require(parse(prefix + electric + water));
    const auto box = boxes[0];
    // Entire 100-unit corridor, including the old radius-16 bypass and edges.
    for (double x : {-50., -30., 0., 30., 50., 60.}) {
        require(p2CaveBarrierTouches(box, x, 0, -450, x, 0, -450));
        // Both endpoints outside; the narrow strip must still intercept travel.
        require(p2CaveBarrierTouches(box, x, 0, -500, x, 0, -400));
        require(p2CaveBarrierTouches(box, x, 0, -400, x, 0, -500));
    }
    require(!p2CaveBarrierTouches(box, 61, 0, -500, 61, 0, -400));
    require(!p2CaveBarrierTouches(box, 0, 131, -500, 0, 131, -400));
    require(!p2CaveBarrierTouches(box, 0, -21, -500, 0, -21, -400));
    require(!p2CaveBarrierTouches(box, 0, 0, -500, 0, 0, -461));
    require(!p2CaveBarrierTouches(box, std::numeric_limits<double>::quiet_NaN(), 0, -450, 0, 0, -450));
    require(!parse(prefix + electric + electric));
    require(!parse(prefix + electric));
    require(!parse(prefix + "bud -60 -20 -460 60 130 -440\n" + water));
    require(!parse(prefix + "unknown -60 -20 -460 60 130 -440\n" + water));
    require(!parse(prefix + "electric 60 -20 -460 -60 130 -440\n" + water));
    require(!parse(prefix + "electric -60 -20 -460 -60 130 -440\n" + water));
    require(!parse(prefix + "electric -60 -20 -460 60 130 inf\n" + water));
    require(!parse(prefix + electric + water + "trailing"));
    require(!parse("P2_CAVE_BARRIERS_1 cave forest_1 floor 1 seed -1 barriers 2\n" + electric + water));
    require(!parse("P2_CAVE_BARRIERS_1 cave forest_1 floor 1 seed 18446744073709551616 barriers 2\n" + electric + water));
    require(!parse("P2_CAVE_BARRIERS_1 cave forest_1 floor 1 seed 931 barriers 2\n" + electric + water));
    require(!parse("P2_CAVE_BARRIERS_1 cave forest_2 floor 1 seed 930 barriers 2\n" + electric + water));
    require(!parse("P2_CAVE_BARRIERS_1 cave forest_1 floor 2 seed 930 barriers 2\n" + electric + water));
    require(!parse("P2_CAVE_BARRIERS_1 cave forest_1 floor 1 seed 930 barriers 1\n" + electric));
    // Failed parsing must not replace a previously accepted set of volumes.
    require(boxes.size() == 2 && boxes[0].id == "electric" && boxes[1].id == "water");
    std::cout << "P2_CAVE_BARRIER_HEADLESS PASS corridor sweep vertical identity strict_parser\n";
}
