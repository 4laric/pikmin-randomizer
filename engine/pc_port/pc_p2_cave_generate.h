#pragma once
// Retail cave generation provider (lane cave-generate-provider, #129).
//
// Header-inline policy module: engine/pc_port/pc_p2_cave.cpp includes this
// header and calls pc_p2_cave_generate_run() once after P2_CAVE_READY. The
// companion pc_p2_cave_generate.cpp TU exists for the integrator to wire
// into PC_PORT_SOURCES under #186 review (follow-on); until then this
// header carries the full implementation so no CMakeLists change is needed.
//
// Contract: reads one decoded floor manifest as the p2-cave-generate.txt
// sidecar (written root-side from a completed-P0 packet, never forked).
// Flat sections in fixed order:
//
//   P2_CAVE_GENERATE_1
//   pool <pool-name> <nunits>
//   unit <idx> <name> <w> <d> <kind>            (idx ascending 0..nunits-1)
//   rooms <nrooms>
//   room <idx> <unit-idx> <turn> <ox> <oy> <oz> (idx ascending, turn 0..3)
//   doors <ndoors>
//   door <unit-idx> <door-id> <dir>             (dir 0..3)
//   links <nlinks>
//   link <unit-idx> <door-id> <peer-unit> <peer-door> <dist>
//   spawns <nspawns>
//   spawn <enemy-id> <count>                    (count >= 1)
//   anchor <hole|geyser>
//
// The generator selects the named pool, places rooms (quarter-turn rotation
// matching experimental.pikmin2_assembly.transform), records roster-minimum
// spawn intents, validates every door link resolves to a staged unit/door,
// and derives the transition anchor: room-0 origin, radius clamped 20..150
// over the largest room diagonal (mirroring p2_cave_read_anchor bounds).
// Every step emits a P2_CAVE_GENERATE_* marker; any malformed line emits
// P2_CAVE_GENERATE_REFUSED reason=<code> and changes nothing.
//
// Opt-in only: an absent sidecar returns false with zero markers and zero
// behavior change. Transfer/restore/checkpoint logic, Beasts paths, nav
// marker strings and Bulbmin rules are untouched. Stdlib only.
#include <cmath>
#include <cstdio>
#include <fstream>
#include <string>
#include <vector>

namespace p2_cave_generate {

struct Vec3 { float x = 0, y = 0, z = 0; };

// Quarter-turn rotation identical to experimental.pikmin2_assembly.transform:
// turn t applies t times (x,z) -> (-z,x), then adds the offset.
inline Vec3 rotateTurn(Vec3 p, int turn) {
    for (int i = 0; i < turn; ++i) { float x = p.x; p.x = -p.z; p.z = x; }
    return p;
}

inline bool finite(float v) { return std::isfinite(v) && std::fabs(v) <= 100000.f; }

inline bool nameOk(const std::string& s, bool allowDollar) {
    if (s.empty() || s.size() > 128) return false;
    for (size_t i = 0; i < s.size(); ++i) {
        char c = s[i];
        bool ok = (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
                  (c >= '0' && c <= '9') || c == '_' || c == '-' || c == '.' ||
                  (allowDollar && c == '$' && i == 0);
        if (!ok) return false;
    }
    return true;
}

struct Unit { std::string name; float w = 0, d = 0; int kind = 0; };
struct Room { int unit = -1, turn = 0; Vec3 offset; };
struct Door { int unit = -1, id = -1, dir = -1; };
struct Link { int unit = -1, door = -1, peerUnit = -1, peerDoor = -1; float dist = 0; };
struct Spawn { std::string id; int count = 0; };

struct Manifest {
    std::string pool;
    std::vector<Unit> units;
    std::vector<Room> rooms;
    std::vector<Door> doors;
    std::vector<Link> links;
    std::vector<Spawn> spawns;
    std::string anchorKind;
};

inline bool refuse(const char* reason) {
    std::printf("P2_CAVE_GENERATE_REFUSED reason=%s\n", reason);
    std::fflush(stdout);
    return false;
}

inline bool readWord(std::istream& in, const char* want) {
    std::string word;
    return (in >> word) && word == want;
}

// Strict sidecar parse. Emits nothing itself; the caller refuses on false.
inline bool readManifest(std::istream& in, Manifest& out) {
    if (!readWord(in, "P2_CAVE_GENERATE_1")) return false;
    int nunits = 0;
    if (!readWord(in, "pool")) return false;
    if (!(in >> out.pool >> nunits)) return false;
    if (!nameOk(out.pool, false) || nunits < 1 || nunits > 64) return false;
    for (int i = 0; i < nunits; ++i) {
        int idx = -1, kind = 0;
        float w = 0, d = 0;
        std::string name;
        if (!readWord(in, "unit")) return false;
        if (!(in >> idx >> name >> w >> d >> kind)) return false;
        if (idx != i || !nameOk(name, false) || !(w > 0) || !(d > 0) ||
            !finite(w) || !finite(d) || kind < 0 || kind > 255) return false;
        Unit u; u.name = name; u.w = w; u.d = d; u.kind = kind;
        out.units.push_back(u);
    }
    int nrooms = 0;
    if (!readWord(in, "rooms")) return false;
    if (!(in >> nrooms) || nrooms < 1 || nrooms > 256) return false;
    for (int i = 0; i < nrooms; ++i) {
        int idx = -1, unit = -1, turn = -1;
        float ox = 0, oy = 0, oz = 0;
        if (!readWord(in, "room")) return false;
        if (!(in >> idx >> unit >> turn >> ox >> oy >> oz)) return false;
        if (idx != i || unit < 0 || unit >= nunits || turn < 0 || turn > 3 ||
            !finite(ox) || !finite(oy) || !finite(oz)) return false;
        Room r; r.unit = unit; r.turn = turn; r.offset.x = ox; r.offset.y = oy; r.offset.z = oz;
        out.rooms.push_back(r);
    }
    int ndoors = 0;
    if (!readWord(in, "doors")) return false;
    if (!(in >> ndoors) || ndoors < 0 || ndoors > 4096) return false;
    for (int i = 0; i < ndoors; ++i) {
        int unit = -1, id = -1, dir = -1;
        if (!readWord(in, "door")) return false;
        if (!(in >> unit >> id >> dir)) return false;
        if (unit < 0 || unit >= nunits || id < 0 || id > 1024 || dir < 0 || dir > 3) return false;
        Door dr; dr.unit = unit; dr.id = id; dr.dir = dir;
        out.doors.push_back(dr);
    }
    int nlinks = 0;
    if (!readWord(in, "links")) return false;
    if (!(in >> nlinks) || nlinks < 0 || nlinks > 4096) return false;
    for (int i = 0; i < nlinks; ++i) {
        int unit = -1, door = -1, peerUnit = -1, peerDoor = -1;
        float dist = 0;
        if (!readWord(in, "link")) return false;
        if (!(in >> unit >> door >> peerUnit >> peerDoor >> dist)) return false;
        if (unit < 0 || unit >= nunits || door < 0 || peerUnit < 0 || peerUnit >= nunits ||
            peerDoor < 0 || dist < 0 || !finite(dist)) return false;
        Link l; l.unit = unit; l.door = door; l.peerUnit = peerUnit; l.peerDoor = peerDoor; l.dist = dist;
        out.links.push_back(l);
    }
    int nspawns = 0;
    if (!readWord(in, "spawns")) return false;
    if (!(in >> nspawns) || nspawns < 1 || nspawns > 256) return false;
    for (int i = 0; i < nspawns; ++i) {
        std::string id;
        int count = 0;
        if (!readWord(in, "spawn")) return false;
        if (!(in >> id >> count)) return false;
        if (!nameOk(id, true) || count < 1 || count > 10000) return false;
        Spawn s; s.id = id; s.count = count;
        out.spawns.push_back(s);
    }
    if (!readWord(in, "anchor")) return false;
    if (!(in >> out.anchorKind)) return false;
    if (out.anchorKind != "hole" && out.anchorKind != "geyser") return false;
    std::string trailing;
    if (in >> trailing) return false;
    return true;
}

// World-space AABB of a room: rotate the unit cell corners, then min/max.
inline void roomBounds(const Manifest& m, const Room& r, Vec3& lo, Vec3& hi) {
    const Unit& u = m.units[size_t(r.unit)];
    lo.x = lo.y = lo.z = 1e30f;
    hi.x = hi.y = hi.z = -1e30f;
    const float xs[2] = {-u.w / 2, u.w / 2}, zs[2] = {-u.d / 2, u.d / 2};
    for (int a = 0; a < 2; ++a) for (int b = 0; b < 2; ++b) {
        Vec3 p = rotateTurn(Vec3{xs[a], 0, zs[b]}, r.turn);
        p.x += r.offset.x; p.y += r.offset.y; p.z += r.offset.z;
        if (p.x < lo.x) lo.x = p.x; if (p.y < lo.y) lo.y = p.y; if (p.z < lo.z) lo.z = p.z;
        if (p.x > hi.x) hi.x = p.x; if (p.y > hi.y) hi.y = p.y; if (p.z > hi.z) hi.z = p.z;
    }
}

inline int symmetricLinks(const Manifest& m) {
    int symmetric = 0;
    for (size_t i = 0; i < m.links.size(); ++i) {
        for (size_t j = 0; j < m.links.size(); ++j) {
            if (i == j) continue;
            const Link& a = m.links[i];
            const Link& b = m.links[j];
            if (a.unit == b.peerUnit && a.door == b.peerDoor &&
                b.unit == a.peerUnit && b.door == a.peerDoor) { ++symmetric; break; }
        }
    }
    return symmetric;
}

// Drive the manifest: validate, emit, derive the anchor. Pure markers.
inline bool drive(const Manifest& m) {
    std::printf("P2_CAVE_GENERATE_POOL pool=%s units=%d\n",
                m.pool.c_str(), int(m.units.size()));
    std::fflush(stdout);
    float maxDiag = 0;
    for (size_t i = 0; i < m.rooms.size(); ++i) {
        Vec3 lo, hi;
        roomBounds(m, m.rooms[i], lo, hi);
        const Unit& u = m.units[size_t(m.rooms[i].unit)];
        const float diag = std::sqrt(u.w * u.w + u.d * u.d);
        if (diag > maxDiag) maxDiag = diag;
        std::printf("P2_CAVE_GENERATE_ROOM idx=%d unit=%d turn=%d "
                    "x0=%.3f y0=%.3f z0=%.3f x1=%.3f y1=%.3f z1=%.3f\n",
                    int(i), m.rooms[i].unit, m.rooms[i].turn,
                    lo.x, lo.y, lo.z, hi.x, hi.y, hi.z);
        std::fflush(stdout);
    }
    for (size_t i = 0; i < m.spawns.size(); ++i) {
        std::printf("P2_CAVE_GENERATE_SPAWN id=%s count=%d\n",
                    m.spawns[i].id.c_str(), m.spawns[i].count);
        std::fflush(stdout);
    }
    std::printf("P2_CAVE_GENERATE_LINKS total=%d symmetric=%d\n",
                int(m.links.size()), symmetricLinks(m));
    std::fflush(stdout);
    const Room& first = m.rooms[0];
    float radius = maxDiag / 2;
    if (radius < 20.f) radius = 20.f;
    if (radius > 150.f) radius = 150.f;
    std::printf("P2_CAVE_GENERATE_ANCHOR kind=%s x=%.3f y=%.3f z=%.3f radius=%.3f\n",
                m.anchorKind.c_str(), first.offset.x, first.offset.y,
                first.offset.z, radius);
    std::fflush(stdout);
    std::printf("P2_CAVE_GENERATE_PASS rooms=%d spawns=%d links=%d anchor=%s\n",
                int(m.rooms.size()), int(m.spawns.size()), int(m.links.size()),
                m.anchorKind.c_str());
    std::fflush(stdout);
    return true;
}

}  // namespace p2_cave_generate

// Opt-in entry: absent sidecar returns false with zero markers.
inline bool pc_p2_cave_generate_run() {
    std::ifstream in("p2-cave-generate.txt");
    if (!in) return false;
    p2_cave_generate::Manifest manifest;
    if (!p2_cave_generate::readManifest(in, manifest))
        return p2_cave_generate::refuse("bad-manifest");
    return p2_cave_generate::drive(manifest);
}