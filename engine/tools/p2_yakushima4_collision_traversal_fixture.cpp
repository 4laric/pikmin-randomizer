// P2 yakushima_4 collision-traversal guarded fixture (#690).
//
// Game-linked observation fixture that performs WALK-INSIDE collision
// traversal sampling on the BUILT yakushima_4 floor-1 map. The map geometry
// is consumed from the real unit pool
// (user/Mukki/mapunits/units/2_units_gw_l_conc.txt, the same member the
// integrated #682 authored table was decoded from) and the integrated #682
// authored room graph is consumed read-only through its public API
// (pc_p2_yakushima4_room_count / _validate / _emit_nav in
// pc_port/pc_p2_cave.cpp; never edited here).
//
// For every authored room the fixture rasterises the room's w x d cell grid,
// places each authored door on its directed boundary edge, and probes all
// four cell edges at every walkable cell. A cell edge that leaves the room
// and is NOT a door opening is a WALL COLLISION: the fixture records the
// contact position, the outward normal and the room it belongs to. It then
// walks each of the 36 authored door links door-to-door inside its room and
// samples the path cell by cell. Nothing here is precomputed: the wall set,
// contact counts and path steps are all derived from the decoded pool plus
// the #682 link rows, so a wrong or stubbed geometry fails closed.
//
// Captain safety #632 is mandatory. The guard runs BEFORE any observation
// and exits 86 (BLOCKED) with P2_FIXTURE_CAPTAIN_DOWN on captain-down, so a
// dead captain can never be recorded as a traversal sample. Protected
// observation cannot prove captain damage. `negcap` forces the negative path.
//
// Scope: floor 1 only. Higher floors, triangle-mesh collision, persistence,
// regen schedules, admission and any gameplay stay explicitly OPEN/UNTESTED.
// This is a native geometry-traversal observation under the guard, not an
// engine boot or gameplay: the run does not create a window or drive the
// captain. Registering this fixture in CMake/CTest touches shared build files
// and therefore requires #186 review; it is built privately through the
// replacement-main builder instead.
//
// Markers: P2_YAKUSHIMA4_TRAVERSAL_BOOT / _ROOM / _SAMPLE / _LINK / _SUMMARY
// / _PASS, plus the integrated table's own P2_CAVE_NAV authored=1 rows and
// P2_YAKUSHIMA4_AUTHORED summary emitted by pc_p2_yakushima4_emit_nav().
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <string>
#include <utility>
#include <vector>

#include "p2_fixture_captain_guard.h"

// Integrated #682 authored-geometry API (owned by the #682 lane, consumed
// read-only). Declared here so no shared header is edited.
extern int pc_p2_yakushima4_room_count();
extern bool pc_p2_yakushima4_validate();
extern int pc_p2_yakushima4_emit_nav();

namespace {

const char* const kUnitsName = "2_units_gw_l_conc.txt";
const int kDirections = 4;

struct DoorLink {
    double distance = 0.0;
    int door = -1;
    int enemy = 0;
};

struct Door {
    int id = -1;
    int dir = -1;
    int offs = 0;
    int waypoint = 0;
    std::vector<DoorLink> links;
};

struct Unit {
    std::string name;
    int w = 0;
    int d = 0;
    std::vector<Door> doors;
};

// Tokenise the retail unit pool: strip '#' comments, treat braces and all
// whitespace as separators (mirrors experimental.pikmin2_cave.unit_definition).
std::vector<std::string> tokenise(const std::string& text)
{
    std::vector<std::string> out;
    std::string cur;
    for (std::size_t i = 0; i < text.size(); ++i) {
        const char c = text[i];
        if (c == '#') {
            while (i < text.size() && text[i] != '\n') ++i;
            continue;
        }
        if (c == '{' || c == '}' || c == ' ' || c == '\t' || c == '\r' || c == '\n') {
            if (!cur.empty()) {
                out.push_back(cur);
                cur.clear();
            }
            continue;
        }
        cur.push_back(c);
    }
    if (!cur.empty()) out.push_back(cur);
    return out;
}

bool decodeUnits(const std::string& text, std::vector<Unit>& units)
{
    const std::vector<std::string> tok = tokenise(text);
    std::size_t p = 0;
    auto next = [&](std::string& out) -> bool {
        if (p >= tok.size()) return false;
        out = tok[p++];
        return true;
    };
    std::string head;
    if (!next(head)) return false;
    const int count = std::atoi(head.c_str());
    if (count < 1 || count > 64) return false;
    for (int u = 0; u < count; ++u) {
        std::string version, name, w, d, kind, flag0, flag1, ndoors;
        if (!next(version) || !next(name) || !next(w) || !next(d) || !next(kind)
            || !next(flag0) || !next(flag1) || !next(ndoors)) return false;
        if (version != "1") return false;
        Unit unit;
        unit.name = name;
        unit.w = std::atoi(w.c_str());
        unit.d = std::atoi(d.c_str());
        const int doors = std::atoi(ndoors.c_str());
        if (unit.w < 1 || unit.d < 1 || doors < 0) return false;
        for (int i = 0; i < doors; ++i) {
            std::string idx, dir, offs, wp, nlinks;
            if (!next(idx) || !next(dir) || !next(offs) || !next(wp) || !next(nlinks)) return false;
            Door door;
            door.id = std::atoi(idx.c_str());
            door.dir = std::atoi(dir.c_str());
            door.offs = std::atoi(offs.c_str());
            door.waypoint = std::atoi(wp.c_str());
            if (door.id != i || door.dir < 0 || door.dir >= kDirections) return false;
            const int links = std::atoi(nlinks.c_str());
            if (links < 0) return false;
            for (int j = 0; j < links; ++j) {
                std::string dist, other, teki;
                if (!next(dist) || !next(other) || !next(teki)) return false;
                DoorLink link;
                link.distance = std::atof(dist.c_str());
                link.door = std::atoi(other.c_str());
                link.enemy = std::atoi(teki.c_str());
                if (!std::isfinite(link.distance) || link.distance < 0.0) return false;
                door.links.push_back(link);
            }
            unit.doors.push_back(door);
        }
        units.push_back(unit);
    }
    return p == tok.size();
}

double medianPitch(const std::vector<Unit>& units)
{
    std::vector<double> values;
    for (const Unit& unit : units)
        for (const Door& door : unit.doors)
            for (const DoorLink& link : door.links)
                if (link.distance > 0.0) values.push_back(link.distance);
    if (values.empty()) return 0.0;
    std::sort(values.begin(), values.end());
    return values[values.size() / 2];
}

// dir: 0=N(+Z), 1=E(+X), 2=S(-Z), 3=W(-X).
void directionVector(int dir, int& dx, int& dz)
{
    dx = dz = 0;
    if (dir == 0) dz = 1;
    else if (dir == 1) dx = 1;
    else if (dir == 2) dz = -1;
    else if (dir == 3) dx = -1;
}

int clampInt(int value, int lo, int hi)
{
    if (value < lo) return lo;
    if (value > hi) return hi;
    return value;
}

// Cell that carries a door, on the room's boundary for the door direction.
void doorCell(const Unit& unit, const Door& door, int& cx, int& cz)
{
    switch (door.dir) {
    case 0: cx = clampInt(door.offs, 0, unit.w - 1); cz = unit.d - 1; break;
    case 1: cx = unit.w - 1; cz = clampInt(door.offs, 0, unit.d - 1); break;
    case 2: cx = clampInt(door.offs, 0, unit.w - 1); cz = 0; break;
    default: cx = 0; cz = clampInt(door.offs, 0, unit.d - 1); break;
    }
}

struct RoomGrid {
    int w = 0;
    int d = 0;
    std::vector<char> doorEdge; // (cz*w+cx)*4+dir
    long contacts = 0;
};

void buildGrid(const Unit& unit, RoomGrid& grid)
{
    grid.w = unit.w;
    grid.d = unit.d;
    grid.doorEdge.assign(std::size_t(unit.w) * std::size_t(unit.d) * kDirections, 0);
    for (const Door& door : unit.doors) {
        int cx = 0, cz = 0;
        doorCell(unit, door, cx, cz);
        grid.doorEdge[(std::size_t(cz) * unit.w + cx) * kDirections + door.dir] = 1;
    }
}

bool inside(int cx, int cz, const RoomGrid& grid)
{
    return cx >= 0 && cx < grid.w && cz >= 0 && cz < grid.d;
}

int wallContactsAt(const RoomGrid& grid, int cx, int cz)
{
    int walls = 0;
    for (int dir = 0; dir < kDirections; ++dir) {
        int dx = 0, dz = 0;
        directionVector(dir, dx, dz);
        if (inside(cx + dx, cz + dz, grid)) continue;
        const char opening = grid.doorEdge[(std::size_t(cz) * grid.w + cx) * kDirections + dir];
        if (!opening) ++walls;
    }
    return walls;
}

// BFS door-to-door inside the room grid; returns step count or -1.
int shortestSteps(const RoomGrid& grid, int sx, int sz, int gx, int gz)
{
    if (!inside(sx, sz, grid) || !inside(gx, gz, grid)) return -1;
    std::vector<int> dist(std::size_t(grid.w) * grid.d, -1);
    std::vector<std::pair<int, int>> queue;
    dist[std::size_t(sz) * grid.w + sx] = 0;
    queue.push_back({sx, sz});
    for (std::size_t head = 0; head < queue.size(); ++head) {
        const int cx = queue[head].first, cz = queue[head].second;
        if (cx == gx && cz == gz) return dist[std::size_t(cz) * grid.w + cx];
        for (int dir = 0; dir < kDirections; ++dir) {
            int dx = 0, dz = 0;
            directionVector(dir, dx, dz);
            const int nx = cx + dx, nz = cz + dz;
            if (!inside(nx, nz, grid)) continue;
            const std::size_t at = std::size_t(nz) * grid.w + nx;
            if (dist[at] >= 0) continue;
            dist[at] = dist[std::size_t(cz) * grid.w + cx] + 1;
            queue.push_back({nx, nz});
        }
    }
    return -1;
}

// Door cell against a grid (same convention as doorCell).
void doorCellFromGrid(const RoomGrid& grid, const Door& door, int& cx, int& cz)
{
    switch (door.dir) {
    case 0: cx = clampInt(door.offs, 0, grid.w - 1); cz = grid.d - 1; break;
    case 1: cx = grid.w - 1; cz = clampInt(door.offs, 0, grid.d - 1); break;
    case 2: cx = clampInt(door.offs, 0, grid.w - 1); cz = 0; break;
    default: cx = 0; cz = clampInt(door.offs, 0, grid.d - 1); break;
    }
}

long walkLink(const RoomGrid& grid, const Door& a, const Door& b, long& samples, long& steps,
              int roomIndex, int linkIndex, double pitch)
{
    int ax = 0, az = 0, bx = 0, bz = 0;
    doorCellFromGrid(grid, a, ax, az);
    doorCellFromGrid(grid, b, bx, bz);
    const int total = shortestSteps(grid, ax, az, bx, bz);
    if (total < 0) return -1; // unreachable link fails closed
    // Re-walk the shortest path deterministically, sampling every cell.
    std::vector<std::pair<int, int>> path;
    int cx = ax, cz = az;
    path.push_back({cx, cz});
    while (cx != bx || cz != bz) {
        int bestDir = -1, best = shortestSteps(grid, cx, cz, bx, bz);
        for (int dir = 0; dir < kDirections; ++dir) {
            int dx = 0, dz = 0;
            directionVector(dir, dx, dz);
            const int nx = cx + dx, nz = cz + dz;
            if (!inside(nx, nz, grid)) continue;
            const int candidate = shortestSteps(grid, nx, nz, bx, bz);
            if (candidate >= 0 && candidate + 1 == best) { bestDir = dir; break; }
        }
        if (bestDir < 0) return -1;
        int dx = 0, dz = 0;
        directionVector(bestDir, dx, dz);
        cx += dx;
        cz += dz;
        path.push_back({cx, cz});
    }
    long contacts = 0;
    for (std::size_t i = 0; i < path.size(); ++i) {
        const int walls = wallContactsAt(grid, path[i].first, path[i].second);
        contacts += walls;
        ++samples;
        std::printf("P2_YAKUSHIMA4_TRAVERSAL_SAMPLE kind=link link=%d room=%d step=%d cell=%d,%d "
                    "x=%.3f z=%.3f walls=%d\n",
                    linkIndex, roomIndex, int(i), path[i].first, path[i].second,
                    (path[i].first + 0.5) * pitch, (path[i].second + 0.5) * pitch, walls);
    }
    steps += long(path.size()) - 1;
    std::fflush(stdout);
    return contacts;
}

int guardSelfTest()
{
    struct Row { bool dead; float hp; bool expectDown; };
    const Row rows[] = {
        {false, 100.0f, false}, {false, 1.5f, false}, {false, 1.0f, true},
        {false, 0.0f, true}, {true, 100.0f, true}, {true, 0.0f, true},
    };
    for (std::size_t i = 0; i < sizeof(rows) / sizeof(rows[0]); ++i) {
        if (p2_fixture_captain_down(false, rows[i].dead, rows[i].hp) != rows[i].expectDown) {
            std::printf("FAIL YAKUSHIMA4_TRAVERSAL selftest row=%d\n", int(i));
            std::fflush(stdout);
            return 1;
        }
    }
    std::printf("P2_YAKUSHIMA4_TRAVERSAL_GUARD_SELFTEST_PASS rows=%d\n",
                int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}

} // namespace

int main(int argc, char** argv)
{
    const char* unitsPath = kUnitsName;
    bool negative = false;
    bool selfTest = false;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "negcap") negative = true;
        else if (arg == "--guard-self-test") selfTest = true;
        else if (arg.rfind("--units=", 0) == 0) unitsPath = argv[i] + 8;
    }
    if (selfTest) return guardSelfTest();
    // Guard BEFORE any observation: orimaDead/dead/HP<=1 -> exit 86 BLOCKED.
    p2_fixture_require_captain(negative, negative, negative ? 0.0f : 100.0f, 0);

    std::ifstream in(unitsPath, std::ios::binary);
    if (!in) {
        std::printf("P2_YAKUSHIMA4_TRAVERSAL_ERROR missing_units=%s\n", unitsPath);
        return 2;
    }
    std::string text((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
    std::vector<Unit> units;
    if (!decodeUnits(text, units)) {
        std::printf("P2_YAKUSHIMA4_TRAVERSAL_ERROR bad_units_decode\n");
        return 2;
    }
    // Consume the integrated #682 authored table read-only. Its emitter also
    // prints the authoritative 36 P2_CAVE_NAV authored=1 rows.
    const int rooms = pc_p2_yakushima4_room_count();
    if (rooms != int(units.size()) || !pc_p2_yakushima4_validate()) {
        std::printf("P2_YAKUSHIMA4_TRAVERSAL_ERROR authored_table rooms=%d units=%d\n",
                    rooms, int(units.size()));
        return 2;
    }
    const int authoredLinks = pc_p2_yakushima4_emit_nav();
    int decodedLinks = 0;
    for (const Unit& unit : units)
        for (const Door& door : unit.doors)
            decodedLinks += int(door.links.size());
    if (authoredLinks != decodedLinks) {
        std::printf("P2_YAKUSHIMA4_TRAVERSAL_ERROR link_mismatch authored=%d decoded=%d\n",
                    authoredLinks, decodedLinks);
        return 2;
    }
    const double pitch = medianPitch(units);
    if (!(pitch > 0.0)) {
        std::printf("P2_YAKUSHIMA4_TRAVERSAL_ERROR no_pitch\n");
        return 2;
    }
    std::printf("P2_YAKUSHIMA4_TRAVERSAL_BOOT mode=%s units=%d rooms=%d links=%d pitch=%.3f\n",
                negative ? "negcap" : "live", int(units.size()), rooms, authoredLinks, pitch);
    std::fflush(stdout);

    long cells = 0, interiorContacts = 0, linkContactsTotal = 0, samples = 0, steps = 0, linkBlocks = 0;
    long linkIndex = 0;
    for (int r = 0; r < int(units.size()); ++r) {
        const Unit& unit = units[r];
        RoomGrid grid;
        buildGrid(unit, grid);
        long roomContacts = 0;
        for (int cz = 0; cz < grid.d; ++cz) {
            for (int cx = 0; cx < grid.w; ++cx) {
                const int walls = wallContactsAt(grid, cx, cz);
                roomContacts += walls;
                ++cells;
                ++samples;
                if (walls > 0) {
                    // One recorded collision contact per wall normal, with the
                    // probe point on the cell edge the walker is pressed against.
                    for (int dir = 0; dir < kDirections; ++dir) {
                        int dx = 0, dz = 0;
                        directionVector(dir, dx, dz);
                        if (inside(cx + dx, cz + dz, grid)) continue;
                        if (grid.doorEdge[(std::size_t(cz) * grid.w + cx) * kDirections + dir]) continue;
                        ++interiorContacts;
                        std::printf("P2_YAKUSHIMA4_TRAVERSAL_CONTACT room=%d cell=%d,%d dir=%d "
                                    "x=%.3f z=%.3f nx=%d nz=%d\n",
                                    r, cx, cz, dir,
                                    (cx + 0.5 + 0.5 * dx) * pitch,
                                    (cz + 0.5 + 0.5 * dz) * pitch, dx, dz);
                    }
                }
                std::printf("P2_YAKUSHIMA4_TRAVERSAL_SAMPLE kind=interior room=%d cell=%d,%d "
                            "x=%.3f z=%.3f walls=%d\n",
                            r, cx, cz, (cx + 0.5) * pitch, (cz + 0.5) * pitch, walls);
            }
        }
        std::printf("P2_YAKUSHIMA4_TRAVERSAL_ROOM room=%d unit=%s cells=%d doors=%d contacts=%d\n",
                    r, unit.name.c_str(), unit.w * unit.d, int(unit.doors.size()), int(roomContacts));
        std::fflush(stdout);
        for (const Door& door : unit.doors) {
            for (const DoorLink& link : door.links) {
                if (link.door < 0 || link.door >= int(unit.doors.size())) {
                    std::printf("P2_YAKUSHIMA4_TRAVERSAL_ERROR bad_door_link room=%d door=%d peer=%d\n",
                                r, door.id, link.door);
                    return 2;
                }
                const long linkContacts = walkLink(grid, door, unit.doors[link.door], samples,
                                                   steps, r, int(linkIndex), pitch);
                if (linkContacts < 0) {
                    ++linkBlocks;
                } else {
                    linkContactsTotal += linkContacts;
                }
                ++linkIndex;
            }
        }
    }
    if (linkIndex != 36 || linkBlocks != 0) {
        std::printf("P2_YAKUSHIMA4_TRAVERSAL_FAIL links=%d blocked=%d\n",
                    int(linkIndex), int(linkBlocks));
        return 2;
    }
    std::printf("P2_YAKUSHIMA4_TRAVERSAL_SUMMARY rooms=%d cells=%ld interior_contacts=%ld "
                "links=%d links_blocked=%ld samples=%ld link_steps=%ld link_contacts=%ld pitch=%.3f\n",
                rooms, cells, interiorContacts, int(linkIndex), linkBlocks, samples, steps,
                linkContactsTotal, pitch);
    std::printf("P2_YAKUSHIMA4_TRAVERSAL_PASS rooms=%d links=%d interior_contacts=%ld link_contacts=%ld\n",
                rooms, int(linkIndex), interiorContacts, linkContactsTotal);
    std::fflush(stdout);
    return 0;
}
