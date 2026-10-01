#pragma once
#include <cmath>
#include <istream>
#include <string>
#include <vector>

namespace p2water {
struct Box {
    int id;
    float min[3], max[3], surface;
};
inline bool valid(const Box& b) {
    if (!std::isfinite(b.surface) || b.surface != b.max[1]) return false;
    for (int a=0; a<3; ++a)
        if (!std::isfinite(b.min[a]) || !std::isfinite(b.max[a]) || b.min[a]>=b.max[a]) return false;
    return true;
}
// Game::AABBWaterBox::inWater, source632af937 gameSeaMgr.cpp:269.
// Inclusive X/Z interval overlap; center Y <= surface-3; deliberately no bottom.
inline bool contains(const Box& b, float x, float y, float z, float radius) {
    if (!std::isfinite(x) || !std::isfinite(y) || !std::isfinite(z)
        || !std::isfinite(radius) || radius<0) return false;
    return y<=b.surface-3.0f && x+radius>=b.min[0] && x-radius<=b.max[0]
        && z+radius>=b.min[2] && z-radius<=b.max[2];
}
inline int find(const std::vector<Box>& boxes, float x, float y, float z, float radius) {
    for (const Box& b:boxes) if (contains(b,x,y,z,radius)) return b.id;
    return -1;
}
inline bool read(std::istream& in, std::vector<Box>& result) {
    result.clear();
    std::string magic,course; long long count=-1;
    if (!(in>>magic>>course>>count) || magic!="P2_SURFACE_WATER_1" || course!="tutorial"
        || count<0 || count>128) return false;
    std::vector<Box> candidate;
    for (int i=0; i<count; ++i) {
        Box b{}; float lowering=0;
        if (!(in>>b.id>>b.min[0]>>b.min[1]>>b.min[2]>>b.max[0]>>b.max[1]>>b.max[2]
              >>b.surface>>lowering) || b.id!=i || lowering!=0 || !valid(b)) return false;
        candidate.push_back(b);
    }
    in>>std::ws;
    if (!in.eof()) return false;
    result.swap(candidate); return true;
}
inline bool readTutorial(std::istream& in, std::vector<Box>& result) {
    if (!read(in,result) || result.size()!=3) {result.clear();return false;}
    return true;
}
}
