#include "pc_p2_houdai_rig.h"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <sstream>

namespace p2houdairig {
namespace {

using p2ik::M34;
using p2ik::V3;

const char* const kClipNames[Rig::ClipCount] = {"landing", "wait", "flick", "attack", "dead"};

bool fail(std::string* error, const char* what)
{
    if (error) *error = what;
    return false;
}

float len3(float x, float y, float z) { return std::sqrt(x * x + y * y + z * z); }

bool finite(float v) { return std::isfinite(v) != 0; }

M34 lerpMatrix(const M34& a, const M34& b, float t)
{
    M34 m;
    for (int r = 0; r < 3; ++r)
        for (int c = 0; c < 4; ++c) m.m[r][c] = a.m[r][c] + (b.m[r][c] - a.m[r][c]) * t;
    return m;
}

// Rotation of `angle` about the model +Y axis through `pivot`.
M34 yawAbout(const V3& pivot, float angle)
{
    const float c = std::cos(angle), s = std::sin(angle);
    M34 r;
    r.m[0][0] = c;  r.m[0][1] = 0.0f; r.m[0][2] = s;
    r.m[1][0] = 0.0f; r.m[1][1] = 1.0f; r.m[1][2] = 0.0f;
    r.m[2][0] = -s; r.m[2][1] = 0.0f; r.m[2][2] = c;
    // p - R p so the pivot is fixed.
    r.m[0][3] = pivot.x - (r.m[0][0] * pivot.x + r.m[0][1] * pivot.y + r.m[0][2] * pivot.z);
    r.m[1][3] = pivot.y - (r.m[1][0] * pivot.x + r.m[1][1] * pivot.y + r.m[1][2] * pivot.z);
    r.m[2][3] = pivot.z - (r.m[2][0] * pivot.x + r.m[2][1] * pivot.y + r.m[2][2] * pivot.z);
    return r;
}

}  // namespace

const char* Rig::clipName(int clip) { return clip >= 0 && clip < ClipCount ? kClipNames[clip] : "?"; }

int Rig::joint(const char* name) const
{
    for (size_t i = 0; i < mJointNames.size(); ++i)
        if (mJointNames[i] == name) return int(i);
    return -1;
}

int Rig::totalPoses() const
{
    int n = 0;
    for (const ClipData& c : mClips) n += int(c.frames.size());
    return n;
}

int Rig::minPoses() const
{
    int n = 1 << 30;
    for (const ClipData& c : mClips) n = std::min(n, int(c.frames.size()));
    return mClips.empty() ? 0 : n;
}

Rig::Decomposed Rig::decompose(const M34& m)
{
    Decomposed d;
    float col[3][3];
    for (int c = 0; c < 3; ++c) {
        col[c][0] = m.m[0][c];
        col[c][1] = m.m[1][c];
        col[c][2] = m.m[2][c];
        d.s[c] = len3(col[c][0], col[c][1], col[c][2]);
        if (!(d.s[c] > 1.0e-6f) || !finite(d.s[c])) return d;  // collapsed axis: not decomposable
        for (int r = 0; r < 3; ++r) col[c][r] /= d.s[c];
    }
    const float det = col[0][0] * (col[1][1] * col[2][2] - col[1][2] * col[2][1])
        - col[0][1] * (col[1][0] * col[2][2] - col[1][2] * col[2][0])
        + col[0][2] * (col[1][0] * col[2][1] - col[1][1] * col[2][0]);
    if (det < 0.0f) {  // mirrored axis: keep the rotation proper and carry the sign in the scale
        d.s[0] = -d.s[0];
        for (int r = 0; r < 3; ++r) col[0][r] = -col[0][r];
    }
    // Orthonormal check (shear from non-uniform scale under rotation breaks it).
    for (int a = 0; a < 3; ++a)
        for (int b = a + 1; b < 3; ++b) {
            const float dot = col[a][0] * col[b][0] + col[a][1] * col[b][1] + col[a][2] * col[b][2];
            if (std::fabs(dot) > 1.0e-3f) return d;
        }
    // Rotation matrix R (rows r, columns c) = col[c][r]. Quaternion from R.
    const float r00 = col[0][0], r01 = col[1][0], r02 = col[2][0];
    const float r10 = col[0][1], r11 = col[1][1], r12 = col[2][1];
    const float r20 = col[0][2], r21 = col[1][2], r22 = col[2][2];
    const float trace = r00 + r11 + r22;
    float x, y, z, w;
    if (trace > 0.0f) {
        const float s = std::sqrt(trace + 1.0f) * 2.0f;
        w = 0.25f * s;
        x = (r21 - r12) / s;
        y = (r02 - r20) / s;
        z = (r10 - r01) / s;
    } else if (r00 > r11 && r00 > r22) {
        const float s = std::sqrt(1.0f + r00 - r11 - r22) * 2.0f;
        w = (r21 - r12) / s;
        x = 0.25f * s;
        y = (r01 + r10) / s;
        z = (r02 + r20) / s;
    } else if (r11 > r22) {
        const float s = std::sqrt(1.0f + r11 - r00 - r22) * 2.0f;
        w = (r02 - r20) / s;
        x = (r01 + r10) / s;
        y = 0.25f * s;
        z = (r12 + r21) / s;
    } else {
        const float s = std::sqrt(1.0f + r22 - r00 - r11) * 2.0f;
        w = (r10 - r01) / s;
        x = (r02 + r20) / s;
        y = (r12 + r21) / s;
        z = 0.25f * s;
    }
    const float n = std::sqrt(x * x + y * y + z * z + w * w);
    if (!(n > 0.0f)) return d;
    d.q[0] = x / n; d.q[1] = y / n; d.q[2] = z / n; d.q[3] = w / n;
    d.t[0] = m.m[0][3]; d.t[1] = m.m[1][3]; d.t[2] = m.m[2][3];
    d.ok = true;
    // Verify the split reproduces the matrix.
    const M34 back = compose(d);
    for (int r = 0; r < 3; ++r)
        for (int c = 0; c < 4; ++c)
            if (!(std::fabs(back.m[r][c] - m.m[r][c]) < 1.0e-3f * (1.0f + std::fabs(m.m[r][c])))) {
                d.ok = false;
                return d;
            }
    return d;
}

M34 Rig::compose(const Decomposed& d)
{
    const float x = d.q[0], y = d.q[1], z = d.q[2], w = d.q[3];
    float R[3][3] = {
        {1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)},
        {2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)},
        {2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)},
    };
    M34 m;
    for (int r = 0; r < 3; ++r) {
        for (int c = 0; c < 3; ++c) m.m[r][c] = R[r][c] * d.s[c];
        m.m[r][3] = d.t[r];
    }
    return m;
}

bool Rig::parse(const std::string& text, std::string* error)
{
    mJointNames.clear();
    mParents.clear();
    mColl.clear();
    mClips.clear();
    std::istringstream in(text);
    std::string word;
    if (!(in >> word) || word != "P2_HOUDAI_RIG_1") return fail(error, "bad header");
    int count = 0;
    if (!(in >> word >> count) || word != "joints" || count < 2 || count > 64) return fail(error, "bad joint count");
    for (int i = 0; i < count; ++i) {
        std::string name;
        int index = 0, parent = 0;
        if (!(in >> word >> index >> name >> parent) || word != "j" || index != i || parent < -1 || parent >= count
                || parent == i)
            return fail(error, "bad joint row");
        mJointNames.push_back(name);
        mParents.push_back(parent);
    }
    int nodes = 0;
    if (!(in >> word >> nodes) || word != "coll" || nodes < 0 || nodes > 16) return fail(error, "bad coll count");
    for (int i = 0; i < nodes; ++i) {
        CollNode node;
        if (!(in >> word >> node.id >> node.code >> node.radius >> node.joint >> node.offset.x >> node.offset.y
              >> node.offset.z >> node.parent) || word != "c" || node.id.size() != 4 || node.code.size() != 4
                || !(node.radius >= 0.0f) || node.joint < 0 || node.joint >= count || node.parent < -1
                || node.parent >= nodes)
            return fail(error, "bad coll row");
        mColl.push_back(node);
    }
    int clips = 0;
    if (!(in >> word >> clips) || word != "clips" || clips != ClipCount) return fail(error, "bad clip count");
    mClips.resize(size_t(clips));
    for (int ci = 0; ci < clips; ++ci) {
        ClipData& clip = mClips[size_t(ci)];
        std::string name;
        int samples = 0;
        if (!(in >> word >> name >> clip.duration >> samples) || word != "clip" || name != kClipNames[ci]
                || clip.duration < 2 || clip.duration > 10000 || samples < 2 || samples > 512)
            return fail(error, "bad clip header");
        if (!(in >> word) || word != "frames") return fail(error, "missing frames");
        for (int k = 0; k < samples; ++k) {
            int frame = 0;
            if (!(in >> frame) || frame < 0 || frame >= clip.duration || (k && frame <= clip.frames.back()))
                return fail(error, "bad frame list");
            clip.frames.push_back(frame);
        }
        if (clip.frames.front() != 0 || clip.frames.back() != clip.duration - 1) return fail(error, "frame range");
        for (int k = 0; k < samples; ++k) {
            if (!(in >> word) || word != "s") return fail(error, "missing sample");
            std::vector<M34> joints; joints.resize(size_t(count));
            for (int j = 0; j < count; ++j)
                for (int r = 0; r < 3; ++r)
                    for (int c = 0; c < 4; ++c) {
                        float v = 0.0f;
                        if (!(in >> v) || !finite(v)) return fail(error, "bad sample value");
                        joints[size_t(j)].m[r][c] = v;
                    }
            std::vector<Decomposed> dec; dec.resize(size_t(count));
            for (int j = 0; j < count; ++j) dec[size_t(j)] = decompose(joints[size_t(j)]);
            clip.raw.push_back(std::move(joints));
            clip.decomp.push_back(std::move(dec));
        }
    }
    if (!(in >> word) || word != "end") return fail(error, "missing end");
    if (in >> word) return fail(error, "trailing data");
    return true;
}

void Rig::sample(int clipIndex, float frame, std::vector<M34>& out) const
{
    const ClipData& clip = mClips[size_t(clipIndex)];
    const int count = int(mJointNames.size());
    out.resize(size_t(count));
    if (!(frame > 0.0f)) frame = 0.0f;
    const float last = float(clip.duration - 1);
    if (frame > last) frame = last;
    // Span [i, i+1] with frames[i] <= frame <= frames[i+1].
    size_t hi = 1;
    while (hi + 1 < clip.frames.size() && float(clip.frames[hi]) < frame) ++hi;
    const size_t lo = hi - 1;
    const float f0 = float(clip.frames[lo]), f1 = float(clip.frames[hi]);
    float t = f1 > f0 ? (frame - f0) / (f1 - f0) : 0.0f;
    t = t < 0.0f ? 0.0f : (t > 1.0f ? 1.0f : t);
    for (int j = 0; j < count; ++j) {
        const Decomposed& a = clip.decomp[lo][size_t(j)];
        const Decomposed& b = clip.decomp[hi][size_t(j)];
        if (t <= 0.0f) { out[size_t(j)] = clip.raw[lo][size_t(j)]; continue; }
        if (t >= 1.0f) { out[size_t(j)] = clip.raw[hi][size_t(j)]; continue; }
        if (!a.ok || !b.ok) {
            out[size_t(j)] = lerpMatrix(clip.raw[lo][size_t(j)], clip.raw[hi][size_t(j)], t);
            continue;
        }
        Decomposed d;
        d.ok = true;
        for (int i = 0; i < 3; ++i) {
            d.s[i] = a.s[i] + (b.s[i] - a.s[i]) * t;
            d.t[i] = a.t[i] + (b.t[i] - a.t[i]) * t;
        }
        float q1[4] = {b.q[0], b.q[1], b.q[2], b.q[3]};
        float dot = a.q[0] * q1[0] + a.q[1] * q1[1] + a.q[2] * q1[2] + a.q[3] * q1[3];
        if (dot < 0.0f) {
            dot = -dot;
            for (float& v : q1) v = -v;
        }
        float k0, k1;
        if (dot > 0.9995f) {
            k0 = 1.0f - t;
            k1 = t;
        } else {
            const float theta = std::acos(dot);
            const float st = std::sin(theta);
            k0 = std::sin((1.0f - t) * theta) / st;
            k1 = std::sin(t * theta) / st;
        }
        float n = 0.0f;
        for (int i = 0; i < 4; ++i) {
            d.q[i] = a.q[i] * k0 + q1[i] * k1;
            n += d.q[i] * d.q[i];
        }
        n = std::sqrt(n);
        for (float& v : d.q) v /= n;
        out[size_t(j)] = compose(d);
    }
}

V3 Rig::collCentre(const std::vector<M34>& joints, int node) const
{
    const CollNode& n = mColl[size_t(node)];
    return p2ik::apply(joints[size_t(n.joint)], n.offset);
}

bool Rig::aimGun(std::vector<M34>& joints, int head, int gun, const V3& dir) const
{
    const int count = int(mJointNames.size());
    if (head < 0 || gun < 0 || head >= count || gun >= count || int(joints.size()) != count) return false;
    const float dl = len3(dir.x, dir.y, dir.z);
    if (!(dl > 1.0e-6f)) return false;
    const V3 d(dir.x / dl, dir.y / dl, dir.z / dl);
    const V3 gunY = joints[size_t(gun)].col(1);
    float fx = gunY.x, fz = gunY.z;
    const float fl = std::sqrt(fx * fx + fz * fz);
    if (!(fl > 1.0e-4f)) return false;
    fx /= fl;
    fz /= fl;
    const float dhl = std::sqrt(d.x * d.x + d.z * d.z);
    float phi = 0.0f;
    if (dhl > 1.0e-4f) {
        const float dx = d.x / dhl, dz = d.z / dhl;
        phi = std::atan2(fz * dx - fx * dz, fx * dx + fz * dz);
    }
    // Descendants (inclusive) of a joint, in index order.
    auto isUnder = [&](int j, int root) {
        for (int guard = 0; j >= 0 && guard < count; ++guard, j = mParents[size_t(j)])
            if (j == root) return true;
        return false;
    };
    // Head yaw: the head joint and everything below it turn about the vertical through the head origin.
    const M34 yaw = yawAbout(joints[size_t(head)].col(3), phi);
    for (int j = 0; j < count; ++j)
        if (isUnder(j, head)) joints[size_t(j)] = p2ik::mul(yaw, joints[size_t(j)]);
    // Gun pitch: Z rotation post-concatenated on the gun joint (columns renormalised, scale restored).
    M34& g = joints[size_t(gun)];
    const M34 before = g;
    const float theta = std::atan2(dhl, -d.y);
    const float c = std::cos(theta), s = std::sin(theta);
    const float sx = len3(g.m[0][0], g.m[1][0], g.m[2][0]);
    const float sy = len3(g.m[0][1], g.m[1][1], g.m[2][1]);
    if (!(sx > 1.0e-6f) || !(sy > 1.0e-6f)) return false;
    for (int r = 0; r < 3; ++r) {
        const float n0 = g.m[r][0] / sx, n1 = g.m[r][1] / sy;
        g.m[r][0] = (n0 * c + n1 * s) * sx;
        g.m[r][1] = (-n0 * s + n1 * c) * sy;
    }
    M34 inv;
    if (p2ik::inverse(before, inv)) {
        const M34 delta = p2ik::mul(g, inv);
        for (int j = 0; j < count; ++j)
            if (j != gun && isUnder(j, gun)) joints[size_t(j)] = p2ik::mul(delta, joints[size_t(j)]);
    }
    return true;
}

}  // namespace p2houdairig
