#pragma once

// Optional, authoritative world-space doorway volumes for bounded cave stages.
// The old gates plan describes semantics; this sidecar binds those semantics to
// the actual staged collision corridor instead of guessing a midpoint radius.
#include "pc_p2_cave_carry.h"
#include <algorithm>
#include <cmath>
#include <limits>

struct P2CaveBarrier {
    std::string id;
    double low[3] = {};
    double high[3] = {};
};

inline bool p2CaveBarrierTouches(const P2CaveBarrier& box,
                               double ax, double ay, double az,
                               double bx, double by, double bz)
{
    const double from[] = {ax, ay, az}, to[] = {bx, by, bz};
    double enter = 0, leave = 1;
    for (int axis = 0; axis < 3; ++axis) {
        if (!std::isfinite(from[axis]) || !std::isfinite(to[axis])) return false;
        const double delta = to[axis] - from[axis];
        if (delta == 0) {
            if (from[axis] < box.low[axis] || from[axis] > box.high[axis]) return false;
            continue;
        }
        double a = (box.low[axis] - from[axis]) / delta;
        double b = (box.high[axis] - from[axis]) / delta;
        if (a > b) std::swap(a, b);
        enter = std::max(enter, a);
        leave = std::min(leave, b);
        if (enter > leave) return false;
    }
    return true;
}

// Fixed grammar: header, cave/floor/seed/barriers fields, then N rows containing
// door_id minX minY minZ maxX maxY maxZ, followed by EOF. Every blocking door
// must occur exactly once; nonblocking doors (including buds) must not occur.
inline bool p2CaveBarrierParse(std::istream& in, const P2CaveCarryPlan& plan,
                              std::vector<P2CaveBarrier>& out, std::string& error)
{
    auto fail = [&error](const char* why) { error = why; return false; };
    std::string word, cave, seedText;
    int floor = 0, count = 0;
    if (!(in >> word) || word != "P2_CAVE_BARRIERS_1") return fail("bad barrier header");
    if (!(in >> word >> cave) || word != "cave" || cave != plan.cave) return fail("barrier cave mismatch");
    if (!(in >> word >> floor) || word != "floor" || floor <= 0 || floor != plan.floor) return fail("barrier floor mismatch");
    if (!(in >> word >> seedText) || word != "seed" || seedText.empty()) return fail("bad barrier seed");
    std::uint64_t seed = 0;
    for (char c : seedText) {
        if (c < '0' || c > '9' || seed > (std::numeric_limits<std::uint64_t>::max() - (c-'0')) / 10)
            return fail("bad barrier seed");
        seed = seed * 10 + (c-'0');
    }
    if (seed != plan.seed) return fail("barrier seed mismatch");
    if (!(in >> word >> count) || word != "barriers" || count < 0 || count > 4096
        || count != p2CaveCarryBlockingCount(plan)) return fail("barrier count mismatch");
    std::vector<P2CaveBarrier> parsed;
    for (int i = 0; i < count; ++i) {
        P2CaveBarrier box;
        if (!(in >> box.id >> box.low[0] >> box.low[1] >> box.low[2]
              >> box.high[0] >> box.high[1] >> box.high[2])) return fail("truncated barrier row");
        const auto* door = p2CaveCarryFindDoor(plan, box.id);
        if (!door || !p2CaveCarryBlocks(*door) || door->kind == "bud") return fail("unknown or nonblocking barrier door");
        for (const auto& existing : parsed) if (existing.id == box.id) return fail("duplicate barrier door");
        for (int axis = 0; axis < 3; ++axis) {
            if (!std::isfinite(box.low[axis]) || !std::isfinite(box.high[axis])
                || box.low[axis] >= box.high[axis] || std::fabs(box.low[axis]) > 1000000
                || std::fabs(box.high[axis]) > 1000000) return fail("invalid barrier bounds");
        }
        parsed.push_back(box);
    }
    if ((in >> word) || !in.eof()) return fail("trailing barrier data");
    out.swap(parsed);
    return true;
}
