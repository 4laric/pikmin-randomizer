#pragma once
#include <cmath>
#include <istream>
#include <string>

// Optional presentation/input configuration, not a checkpoint schema.
struct P2CaveAnchor {
    bool enabled = false;
    std::string kind;
    float x = 0, y = 0, z = 0, radius = 0;

    bool contains(float px, float py, float pz) const {
        if (!enabled || !std::isfinite(px) || !std::isfinite(py) || !std::isfinite(pz)) return false;
        const float dx = px - x, dz = pz - z;
        // Separate floors/platforms must not activate through one another.
        return dx * dx + dz * dz <= radius * radius && std::fabs(py - y) <= 40.f;
    }
};

inline bool p2_cave_read_anchor(std::istream& in, int floor, P2CaveAnchor& out) {
    P2CaveAnchor parsed;
    std::string version, extra;
    if (!(in >> version >> parsed.kind >> parsed.x >> parsed.y >> parsed.z >> parsed.radius)
        || version != "P2_CAVE_TRANSITION_1" || (floor != 1 && floor != 2)
        || parsed.kind != (floor == 1 ? "hole" : "geyser")
        || !std::isfinite(parsed.x) || !std::isfinite(parsed.y) || !std::isfinite(parsed.z)
        || !std::isfinite(parsed.radius) || parsed.radius < 20.f || parsed.radius > 150.f
        || std::fabs(parsed.x) > 100000.f || std::fabs(parsed.y) > 100000.f || std::fabs(parsed.z) > 100000.f
        || (in >> extra) || !in.eof()) return false;
    parsed.enabled = true;
    out = parsed;
    return true;
}
