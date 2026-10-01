#include "pc_p2_surface_water_policy.h"
#include <cassert>
#include <limits>
#include <sstream>
int main() {
    const p2water::Box b{0,{-140,-55,350},{960,45,1150},45};
    assert(p2water::valid(b));
    assert(p2water::contains(b,-150,42,350,10)); // Inclusive sphere boundary.
    assert(!p2water::contains(b,-150.01f,42,350,10));
    assert(!p2water::contains(b,0,42.01f,500,0)); // Upper bridge remains dry.
    assert(p2water::contains(b,0,-100000,500,0)); // Source has no bottom cutoff.
    assert(!p2water::contains(b,0,0,500,-1));
    assert(!p2water::contains(b,0,std::numeric_limits<float>::quiet_NaN(),500,0));
    auto duplicate=b;duplicate.id=1;
    assert(p2water::find({b,duplicate},0,0,500,0)==0); // Source order, no nearest selection.
    const char* row="0 -140 -55 350 960 45 1150 45 0";
    std::vector<p2water::Box> result;
    std::istringstream good(std::string("P2_SURFACE_WATER_1 tutorial 1 ")+row);
    assert(p2water::read(good,result) && result.size()==1);
    for (const char* text : {
        "P2_SURFACE_WATER_1 tutorial 1", // Declared row truncated.
        "P2_SURFACE_WATER_1 tutorial 0 extra", // No ignored trailing records.
        "P2_SURFACE_WATER_1 tutorial 129",
        "P2_SURFACE_WATER_1 forest 0",
        "P2_SURFACE_WATER_1 tutorial 1 1 -140 -55 350 960 45 1150 45 0",
        "P2_SURFACE_WATER_1 tutorial 1 0 -140 -55 350 960 45 1150 44 0",
        "P2_SURFACE_WATER_1 tutorial 1 0 -140 -55 350 960 45 1150 45 1",
        "P2_SURFACE_WATER_1 tutorial 1 0 -140 -55 350 -140 45 1150 45 0"
    }) {
        result={b};std::istringstream bad(text);
        assert(!p2water::read(bad,result) && result.empty()); // Reset stale course state on refusal.
    }
    std::istringstream empty("P2_SURFACE_WATER_1 tutorial 0\n");
    assert(p2water::read(empty,result) && result.empty());
    std::istringstream absentVolumes("P2_SURFACE_WATER_1 tutorial 0\n");
    assert(!p2water::readTutorial(absentVolumes,result) && result.empty());
    std::istringstream oneVolume(std::string("P2_SURFACE_WATER_1 tutorial 1 ")+row);
    assert(!p2water::readTutorial(oneVolume,result) && result.empty());
    std::istringstream allVolumes(std::string("P2_SURFACE_WATER_1 tutorial 3 ")+row+
        " 1 -1210 -30 -650 -410 70 150 70 0 2 -140 -60 1250 960 40 2150 40 0");
    assert(p2water::readTutorial(allVolumes,result) && result.size()==3);
}
