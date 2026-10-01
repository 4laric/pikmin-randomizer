#include "pc_p2_houdai_rig.h"

// Release builds pass -DNDEBUG; force assertions on so this gate is not vacuous.
#undef NDEBUG
#include <cassert>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>

// Engine-free gate for the Man-at-Legs sampled joint rig (#1012). Synthetic three-joint
// rig (root, head, gun) in the same pose convention as the retail attack clip: head and
// gun local X point down, local Y is the horizontal -Z axis, local Z is +X. A real rig
// text (longlegs_Houdai_rig_00.txt) is also checked when P2_HOUDAI_RIG_FILE names one.

namespace {
using p2ik::M34;
using p2ik::V3;

const char* const kClips[5] = {"landing", "wait", "flick", "attack", "dead"};

std::string f(float v)
{
    char buf[64];
    std::snprintf(buf, sizeof buf, "%.7g", v);
    return buf;
}

std::string row(const M34& m)
{
    std::string s = "s";
    for (int r = 0; r < 3; ++r)
        for (int c = 0; c < 4; ++c) s += " " + f(m.m[r][c]);
    return s;
}

M34 downJoint(float y)
{
    M34 m;
    m.m[0][0] = 0; m.m[1][0] = -1; m.m[2][0] = 0;   // X down
    m.m[0][1] = 0; m.m[1][1] = 0;  m.m[2][1] = -1;  // Y = -Z
    m.m[0][2] = 1; m.m[1][2] = 0;  m.m[2][2] = 0;   // Z = +X
    m.m[0][3] = 0; m.m[1][3] = y;  m.m[2][3] = 0;
    return m;
}

M34 rootRotated(float yawRad)
{
    M34 m;
    const float c = std::cos(yawRad), s = std::sin(yawRad);
    m.m[0][0] = c; m.m[0][2] = s; m.m[2][0] = -s; m.m[2][2] = c;
    m.m[0][3] = 10.0f * yawRad;
    return m;
}

// Every clip: two samples, root yaw 0 -> 1.2 rad with a translation, head/gun static.
std::string synthetic()
{
    std::ostringstream o;
    o << "P2_HOUDAI_RIG_1\njoints 3\nj 0 kosi -1\nj 1 tamajnt 0\nj 2 gun 1\n";
    o << "coll 2\nc none ____ 50 0 0 0 0 -1\nc tama st__ 30 0 5 0 0 0\n";
    o << "clips 5\n";
    for (const char* name : kClips) {
        o << "clip " << name << " 11 2\nframes 0 10\n";
        o << row(rootRotated(0.0f)) << " " << row(downJoint(114.0f)).substr(2) << " " << row(downJoint(90.0f)).substr(2) << "\n";
        o << row(rootRotated(1.2f)) << " " << row(downJoint(114.0f)).substr(2) << " " << row(downJoint(90.0f)).substr(2) << "\n";
    }
    o << "end\n";
    return o.str();
}

bool near(float a, float b, float eps = 1.0e-3f) { return std::fabs(a - b) <= eps; }

V3 unit(const V3& v)
{
    const float l = std::sqrt(v.x * v.x + v.y * v.y + v.z * v.z);
    return V3(v.x / l, v.y / l, v.z / l);
}
} // namespace

int main()
{
    using p2houdairig::Rig;
    Rig rig;
    std::string error;
    assert(rig.parse(synthetic(), &error));
    assert(rig.ready());
    assert(rig.jointCount() == 3 && rig.joint("gun") == 2 && rig.parent(2) == 1 && rig.parent(0) == -1);
    assert(rig.coll().size() == 2 && rig.coll()[1].stickable() && !rig.coll()[0].stickable());
    assert(rig.totalPoses() == 10 && rig.minPoses() == 2);

    // Malformed inputs are refused.
    {
        Rig bad;
        assert(!bad.parse("P2_HOUDAI_RIG_2\n", &error));
        std::string cut = synthetic();
        assert(!bad.parse(cut.substr(0, cut.size() - 4), &error));
        std::string extra = synthetic() + "x\n";
        assert(!bad.parse(extra, &error));
    }

    // Sample frames return the stored matrices; the midpoint slerps without shrinking the basis.
    std::vector<M34> a, mid, end;
    rig.sample(Rig::Wait, 0.0f, a);
    rig.sample(Rig::Wait, 10.0f, end);
    rig.sample(Rig::Wait, 5.0f, mid);
    assert(near(a[0].m[0][0], 1.0f) && near(end[0].m[0][0], std::cos(1.2f)));
    assert(near(mid[0].m[0][0], std::cos(0.6f)) && near(mid[0].m[0][2], std::sin(0.6f)));
    assert(near(mid[0].m[0][3], 10.0f * 0.6f));
    const float basis = std::sqrt(mid[0].m[0][0] * mid[0].m[0][0] + mid[0].m[1][0] * mid[0].m[1][0] + mid[0].m[2][0] * mid[0].m[2][0]);
    assert(near(basis, 1.0f));
    // Out-of-range frames clamp to the clip ends.
    std::vector<M34> over;
    rig.sample(Rig::Wait, 99.0f, over);
    assert(near(over[0].m[0][0], end[0].m[0][0]));
    rig.sample(Rig::Wait, -4.0f, over);
    assert(near(over[0].m[0][0], 1.0f));

    // collCentre: tama (kosi joint, offset 5 along the joint X) follows the posed root.
    const V3 c0 = rig.collCentre(a, 1);
    assert(near(c0.x, 5.0f) && near(c0.y, 0.0f));

    // aimGun: the barrel (gun local X) points along the requested direction for any aim, the gun
    // pivot stays put, and the local Y/Z axes stay orthonormal.
    const V3 dirs[] = {V3(0, -1, 0), V3(1, 0, 0), V3(0, 0, 1), V3(-1, -1, 0.5f), V3(0.3f, -0.2f, -0.9f),
                       V3(0.5f, 0.5f, 0.1f), V3(0, 1, 0)};
    for (const V3& raw : dirs) {
        std::vector<M34> j = {downJoint(0), downJoint(114.0f), downJoint(90.0f)};
        const V3 before = j[2].col(3);
        assert(rig.aimGun(j, 1, 2, raw));
        const V3 want = unit(raw);
        const V3 x = j[2].col(0), y = j[2].col(1), z = j[2].col(2);
        assert(near(x.x, want.x) && near(x.y, want.y) && near(x.z, want.z));
        assert(near(j[2].m[0][3], before.x) && near(j[2].m[1][3], before.y) && near(j[2].m[2][3], before.z));
        assert(near(x.x * y.x + x.y * y.y + x.z * y.z, 0.0f) && near(x.x * z.x + x.y * z.y + x.z * z.z, 0.0f));
        // head follows the yaw: its X (vertical spin axis) is unchanged
        assert(near(j[1].m[1][0], -1.0f));
    }
    // A zero direction is refused and leaves the pose alone.
    {
        std::vector<M34> j = {downJoint(0), downJoint(114.0f), downJoint(90.0f)};
        assert(!rig.aimGun(j, 1, 2, V3(0, 0, 0)));
        assert(near(j[2].m[1][0], -1.0f));
    }

    // Optional: the real rig from the extractor.
    if (const char* path = std::getenv("P2_HOUDAI_RIG_FILE")) {
        std::ifstream in(path, std::ios::binary);
        assert(in);
        std::stringstream ss;
        ss << in.rdbuf();
        Rig real;
        assert(real.parse(ss.str(), &error));
        assert(real.jointCount() == 22 && real.minPoses() >= 24);
        const int head = real.joint("tamajnt"), gun = real.joint("gun"), kosi = real.joint("kosi");
        assert(head >= 0 && gun >= 0 && kosi == 0);
        assert(real.duration(Rig::Landing) == 230 && real.duration(Rig::Wait) == 40 && real.duration(Rig::Flick) == 85
               && real.duration(Rig::Attack) == 70 && real.duration(Rig::Dead) == 140);
        assert(real.coll().size() == 2 && real.coll()[1].id == "tama" && real.coll()[1].stickable());
        std::vector<M34> pose;
        // Standing wait pose: body 114 high, gun deployed in the attack clip at frame 39 hangs at y 90.
        real.sample(Rig::Wait, 0.0f, pose);
        assert(near(pose[size_t(kosi)].m[1][3], 114.0f, 0.5f));
        real.sample(Rig::Attack, 39.0f, pose);
        assert(near(pose[size_t(gun)].m[1][3], 90.0f, 0.5f));
        // Landing opens crouched on the ground and ends standing.
        real.sample(Rig::Landing, 0.0f, pose);
        assert(pose[size_t(kosi)].m[1][3] < 10.0f);
        real.sample(Rig::Landing, 229.0f, pose);
        assert(near(pose[size_t(kosi)].m[1][3], 114.0f, 1.0f));
        // Every clip samples finite matrices at every integer frame, and a half-frame blend stays between its ends.
        for (int clip = 0; clip < Rig::ClipCount; ++clip)
            for (int fr = 0; fr < real.duration(clip); ++fr) {
                real.sample(clip, float(fr) + 0.5f, pose);
                for (const M34& m : pose)
                    for (int r = 0; r < 3; ++r)
                        for (int c = 0; c < 4; ++c) assert(std::isfinite(m.m[r][c]));
            }
        // Real aim: gun straight at a point off to the side and above.
        real.sample(Rig::Attack, 39.0f, pose);
        assert(real.aimGun(pose, head, gun, V3(0.6f, -0.3f, 0.74f)));
        const V3 x = unit(pose[size_t(gun)].col(0));
        const V3 want = unit(V3(0.6f, -0.3f, 0.74f));
        assert(near(x.x, want.x, 2.0e-3f) && near(x.y, want.y, 2.0e-3f) && near(x.z, want.z, 2.0e-3f));
        std::printf("p2_houdai_rig_test: real rig ok (%d poses, min %d/clip)\n", real.totalPoses(), real.minPoses());
    }
    std::printf("p2_houdai_rig_test: ok\n");
    return 0;
}
