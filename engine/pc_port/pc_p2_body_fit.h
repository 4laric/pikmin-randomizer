// Engine-free body-collision fit for P2 meshes drawn on a P1 host (#964 follow-up,
// branch claude/p2-stick-surface).
//
// A P2 enemy on the port is a P2 mesh drawn over a P1 host actor. Stuck Pikmin
// are placed on the HOST's collision tree (creatureStick.cpp startStickObjectSphere:
// the sticker is projected onto the stickable part's sphere), and that tree has
// P1 proportions, so latched Pikmin float off or sink into a P2 body
// (owner playtest: Hana 84, Water Dumple 26, Empress 30).
//
// Joint world matrices are not available for a baked pose, so the retail
// enemycoll joint spheres cannot be posed. The mesh itself is: this fits a small
// set of spheres to the rest-pose vertices (deterministic k-means on the vertex
// cloud; each sphere's radius is the mean distance of its members, which sits a
// surface mesh on the sphere). A stuck Pikmin then rests on the drawn surface.
//
// The table is in mesh units (actor-local, +z forward, y up), ready for
// P2FlyerColl (pc_p2_flyer_coll.h).
#pragma once

#include "pc_p2_flyer.h"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <vector>

namespace p2bodyfit {

constexpr int kMaxSpheres = p2flyer::kMaxSpheres;  // root + up to 7 stickable bodies
constexpr int kMaxChildren = kMaxSpheres - 1;
constexpr std::size_t kMaxSample = 4096;

struct Table {
    p2flyer::Sphere spheres[kMaxSpheres] = {};
    int count = 0;              // 0 = no fit
    float bounds[6] = {};       // min xyz, max xyz of the input cloud
    float meanGap = 0.0f;       // mean |dist(v, centre) - radius| over the sample (fit quality)
    float maxGap = 0.0f;        // worst such gap
};

struct V3 {
    float x, y, z;
};

inline bool finite3(const V3& v)
{
    return std::isfinite(v.x) && std::isfinite(v.y) && std::isfinite(v.z) && std::fabs(v.x) < 1.0e5f
        && std::fabs(v.y) < 1.0e5f && std::fabs(v.z) < 1.0e5f;
}

// Number of body spheres for a cloud with the given extents: a long thin body
// gets a chain, a compact one a single sphere.
inline int sphereCountFor(float e0, float e1, float e2)
{
    float a[3] = {e0, e1, e2};
    std::sort(a, a + 3, [](float l, float r) { return l > r; });
    if (!(a[1] > 1.0e-3f)) return 1;
    const int k = int(a[0] / (a[1] * 0.75f) + 0.5f);
    return std::max(1, std::min(k, kMaxChildren));
}

// Fits the table. Returns false (table untouched) for an empty, non-finite or
// degenerate cloud.
template <typename VertexAt>
inline bool fit(std::size_t count, VertexAt vertexAt, Table& out)
{
    if (count < 4) return false;
    const std::size_t stride = count > kMaxSample ? (count + kMaxSample - 1) / kMaxSample : 1;
    std::vector<V3> pts;
    pts.reserve(count / stride + 1);
    float lo[3] = {1.0e30f, 1.0e30f, 1.0e30f}, hi[3] = {-1.0e30f, -1.0e30f, -1.0e30f};
    for (std::size_t i = 0; i < count; i += stride) {
        const V3 v = vertexAt(i);
        if (!finite3(v)) return false;
        pts.push_back(v);
        const float c[3] = {v.x, v.y, v.z};
        for (int a = 0; a < 3; ++a) {
            lo[a] = std::min(lo[a], c[a]);
            hi[a] = std::max(hi[a], c[a]);
        }
    }
    const float ext[3] = {hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]};
    if (!(ext[0] + ext[1] + ext[2] > 1.0e-2f)) return false;
    const int k = sphereCountFor(ext[0], ext[1], ext[2]);
    int longest = 0;
    for (int a = 1; a < 3; ++a)
        if (ext[a] > ext[longest]) longest = a;
    auto coord = [](const V3& v, int a) { return a == 0 ? v.x : (a == 1 ? v.y : v.z); };
    // Initial centres: evenly spaced quantiles along the longest axis.
    std::vector<std::size_t> order(pts.size());
    for (std::size_t i = 0; i < order.size(); ++i) order[i] = i;
    std::sort(order.begin(), order.end(), [&](std::size_t l, std::size_t r) {
        const float cl = coord(pts[l], longest), cr = coord(pts[r], longest);
        return cl < cr || (cl == cr && l < r);
    });
    V3 centre[kMaxChildren];
    for (int j = 0; j < k; ++j) centre[j] = pts[order[std::size_t((double(j) + 0.5) * double(order.size()) / double(k))]];
    std::vector<int> member(pts.size(), 0);
    for (int iter = 0; iter < 16; ++iter) {
        double sx[kMaxChildren] = {}, sy[kMaxChildren] = {}, sz[kMaxChildren] = {};
        int n[kMaxChildren] = {};
        for (std::size_t i = 0; i < pts.size(); ++i) {
            int best = 0;
            float bestD = 1.0e30f;
            for (int j = 0; j < k; ++j) {
                const float dx = pts[i].x - centre[j].x, dy = pts[i].y - centre[j].y, dz = pts[i].z - centre[j].z;
                const float d = dx * dx + dy * dy + dz * dz;
                if (d < bestD) { bestD = d; best = j; }
            }
            member[i] = best;
            sx[best] += pts[i].x; sy[best] += pts[i].y; sz[best] += pts[i].z;
            ++n[best];
        }
        for (int j = 0; j < k; ++j)
            if (n[j]) centre[j] = V3{float(sx[j] / n[j]), float(sy[j] / n[j]), float(sz[j] / n[j])};
    }
    // Radius = mean member distance; drop empty clusters.
    Table t;
    t.bounds[0] = lo[0]; t.bounds[1] = lo[1]; t.bounds[2] = lo[2];
    t.bounds[3] = hi[0]; t.bounds[4] = hi[1]; t.bounds[5] = hi[2];
    static const char* const kIds[kMaxChildren] = {"bod1", "bod2", "bod3", "bod4", "bod5", "bod6", "bod7"};
    V3 outC[kMaxChildren];
    float outR[kMaxChildren];
    int used = 0;
    for (int j = 0; j < k; ++j) {
        double sum = 0.0;
        int n = 0;
        for (std::size_t i = 0; i < pts.size(); ++i) {
            if (member[i] != j) continue;
            const double dx = pts[i].x - centre[j].x, dy = pts[i].y - centre[j].y, dz = pts[i].z - centre[j].z;
            sum += std::sqrt(dx * dx + dy * dy + dz * dz);
            ++n;
        }
        if (n < 2) continue;
        outC[used] = centre[j];
        outR[used] = std::max(1.0f, float(sum / n));
        ++used;
    }
    if (used == 0) return false;
    // Root: the enclosing bounding sphere (centre = bbox centre).
    const V3 rc{(lo[0] + hi[0]) * 0.5f, (lo[1] + hi[1]) * 0.5f, (lo[2] + hi[2]) * 0.5f};
    float rr = 1.0f;
    for (int j = 0; j < used; ++j) {
        const float dx = outC[j].x - rc.x, dy = outC[j].y - rc.y, dz = outC[j].z - rc.z;
        rr = std::max(rr, std::sqrt(dx * dx + dy * dy + dz * dz) + outR[j]);
    }
    t.spheres[0] = p2flyer::Sphere{"root", "____", rr, p2flyer::Vec3{rc.x, rc.y, rc.z}, -1};
    for (int j = 0; j < used; ++j)
        t.spheres[1 + j] = p2flyer::Sphere{kIds[j], "st__", outR[j], p2flyer::Vec3{outC[j].x, outC[j].y, outC[j].z}, 0};
    t.count = 1 + used;
    // Fit quality: how far the sample sits from its nearest body sphere surface.
    double gapSum = 0.0;
    float gapMax = 0.0f;
    for (std::size_t i = 0; i < pts.size(); ++i) {
        float best = 1.0e30f;
        for (int j = 0; j < used; ++j) {
            const float dx = pts[i].x - outC[j].x, dy = pts[i].y - outC[j].y, dz = pts[i].z - outC[j].z;
            best = std::min(best, std::fabs(std::sqrt(dx * dx + dy * dy + dz * dz) - outR[j]));
        }
        gapSum += best;
        gapMax = std::max(gapMax, best);
    }
    t.meanGap = float(gapSum / double(pts.size()));
    t.maxGap = gapMax;
    out = t;
    return true;
}

// Distance from a world point to the surface of sphere `i` of a table placed at
// `root` facing `yaw` (positive = outside). Used by the stick log and tests.
inline float surfaceGap(const Table& t, int i, const p2flyer::Vec3& root, float yaw, const p2flyer::Vec3& p,
                        float scale = 1.0f)
{
    const p2flyer::Vec3 c = p2flyer::sphereCentre(t.spheres, t.count, i, root, yaw, p2flyer::Vec3{});
    const float cx = root.x + (c.x - root.x) * scale, cy = root.y + (c.y - root.y) * scale,
                cz = root.z + (c.z - root.z) * scale;
    const float dx = p.x - cx, dy = p.y - cy, dz = p.z - cz;
    return std::sqrt(dx * dx + dy * dy + dz * dz) - t.spheres[i].radius * scale;
}

}  // namespace p2bodyfit
