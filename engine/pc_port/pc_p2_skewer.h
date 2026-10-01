#pragma once
// Shared "skewered Pikmin" orientation helper (#1020; Bloyster tongue, reusable by the Armored Maw #1014).
//
// A swallowed Pikmin is drawn from its mouth part's view-space matrix (viewPiki.cpp:671-682: the part
// matrix times a +90 degree Z turn), which makes the Pikmin's own up axis the part matrix's -X axis. A
// captor that only sets a yaw therefore leaves every held Pikmin standing upright at its joint. To look
// impaled, a captor aims the part matrix's X column along the spear/tongue instead: the Pikmin then lies
// along it with its head toward the tip.
//
// Engine-free: world-space basis only. The caller multiplies it by its camera rotation exactly as it
// already does for the yaw (see pc_p2_umimushi.cpp updateColl).
#include <cmath>
#include <cstdlib>
#include <cstring>
#include "pc_p2_skewer_axes.h"

namespace p2skewer {

struct Basis {
    float x[3]; // part matrix X column (the Pikmin's up axis is -x)
    float y[3];
    float z[3];
};

// Basis whose -X axis is `dir` (the Pikmin's head points along dir). `dir` need not be normalised; a
// near-zero or vertical-degenerate direction falls back to `fallbackYaw` facing with a horizontal pose.
inline Basis along(const float dir[3], float fallbackYaw)
{
    float d[3] = {dir[0], dir[1], dir[2]};
    float len = std::sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]);
    if (!(len > 1.0e-3f)) {
        d[0] = std::sin(fallbackYaw);
        d[1] = 0.0f;
        d[2] = std::cos(fallbackYaw);
        len = 1.0f;
    }
    for (float& v : d) v /= len;
    Basis b;
    for (int i = 0; i < 3; ++i) b.x[i] = -d[i];
    // Y: world up made orthogonal to x (a sideways reference when the spear is vertical).
    float up[3] = {0.0f, 1.0f, 0.0f};
    if (std::fabs(b.x[1]) > 0.98f) { up[0] = 1.0f; up[1] = 0.0f; }
    const float dot = up[0] * b.x[0] + up[1] * b.x[1] + up[2] * b.x[2];
    for (int i = 0; i < 3; ++i) b.y[i] = up[i] - dot * b.x[i];
    const float yl = std::sqrt(b.y[0] * b.y[0] + b.y[1] * b.y[1] + b.y[2] * b.y[2]);
    for (float& v : b.y) v /= yl;
    // Z = X x Y
    b.z[0] = b.x[1] * b.y[2] - b.x[2] * b.y[1];
    b.z[1] = b.x[2] * b.y[0] - b.x[0] * b.y[2];
    b.z[2] = b.x[0] * b.y[1] - b.x[1] * b.y[0];
    return b;
}

// Direction of the spear at slot `i` of `n` slot positions p[i][3]: the central difference of its
// neighbours (forward/backward at the ends), i.e. the local tangent of the tongue.
inline void tangent(const float (*p)[3], int n, int i, float out[3])
{
    const int a = i > 0 ? i - 1 : i;
    const int c = i + 1 < n ? i + 1 : i;
    for (int k = 0; k < 3; ++k) out[k] = p[c][k] - p[a][k];
}

// The slot joint's own orientation, as P2 uses it: `r` is the model-space rotation (row-major 3x3, from
// pc_p2_skewer_axes.h), turned by the actor yaw into world space. The Pikmin then gets exactly the pose P2 gives
// it: joint matrix times a +90 degree Z turn (viewPiki.cpp:671-682 here, Creature::updateStick in P2).
inline Basis fromRotation(const float r[9], float yaw)
{
    const float c = std::cos(yaw), s = std::sin(yaw);
    Basis b;
    float* cols[3] = {b.x, b.y, b.z};
    for (int k = 0; k < 3; ++k) {
        const float mx = r[0 * 3 + k], my = r[1 * 3 + k], mz = r[2 * 3 + k]; // column k in model space
        cols[k][0] = c * mx + s * mz;
        cols[k][1] = my;
        cols[k][2] = -s * mx + c * mz;
    }
    return b;
}

// Rotation of the Armor kamujnt at `frame` of clip `stem`; false when the clip is not tabled.
inline bool armorRotation(const char* stem, float frame, float out[9])
{
    for (int i = 0; i < p2skeweraxes::kArmorClipCount; ++i) {
        const p2skeweraxes::Clip& c = p2skeweraxes::kArmorClips[i];
        if (std::strcmp(c.stem, stem) != 0) continue;
        int f = int(frame + 0.5f);
        if (f < 0) f = 0;
        if (f >= c.frames) f = c.frames - 1;
        for (int k = 0; k < 9; ++k) out[k] = p2skeweraxes::kArmor[c.offset + f * 9 + k];
        return true;
    }
    return false;
}

// Rotation of UmiMushi kamu_joint(slot+1) at `frame` of attack1/eat1.
inline bool umiRotation(const char* stem, float frame, int slot, float out[9])
{
    for (int i = 0; i < p2skeweraxes::kUmiClipCount; ++i) {
        const p2skeweraxes::Clip& c = p2skeweraxes::kUmiClips[i];
        if (std::strcmp(c.stem, stem) != 0 || slot < 0 || slot >= p2skeweraxes::kUmiJoints) continue;
        int f = int(frame + 0.5f);
        if (f < 0) f = 0;
        if (f >= c.frames) f = c.frames - 1;
        for (int k = 0; k < 9; ++k) out[k] = p2skeweraxes::kUmi[c.offset + (f * p2skeweraxes::kUmiJoints + slot) * 9 + k];
        return true;
    }
    return false;
}

// Part joint matrix for an explicit basis (camRot * world basis).
template <class Mtx>
inline void jointMatrixBasis(Mtx& out, const Mtx& camRot, const Basis& b)
{
    Mtx world;
    world.makeIdentity();
    for (int r = 0; r < 3; ++r) {
        world.mMtx[r][0] = b.x[r];
        world.mMtx[r][1] = b.y[r];
        world.mMtx[r][2] = b.z[r];
    }
    camRot.multiplyTo(world, out);
}

// Writes the part joint matrix (camRot * world basis) for a Pikmin skewered along `dir`.
// camRot is the transpose of the camera rotation, exactly as the captors build their yaw matrix.
template <class Mtx>
inline void jointMatrix(Mtx& out, const Mtx& camRot, const float dir[3], float fallbackYaw)
{
    const Basis b = along(dir, fallbackYaw);
    Mtx world;
    world.makeIdentity();
    for (int r = 0; r < 3; ++r) {
        world.mMtx[r][0] = b.x[r];
        world.mMtx[r][1] = b.y[r];
        world.mMtx[r][2] = b.z[r];
    }
    camRot.multiplyTo(world, out);
}

// Optional extra seating back along the spear (model units at scale 1), default 0: P2 seats the Pikmin ON the slot
// joint (creatureStick.cpp:221-247). PIKMIN_P2_SKEWER_DEPTH overrides it for tuning only.
inline float depth()
{
    static const float d = [] {
        const char* e = std::getenv("PIKMIN_P2_SKEWER_DEPTH");
        return e && *e ? float(std::atof(e)) : 0.0f;
    }();
    return d;
}

// Moves `p` back along `dir` (unit or not) by depth() * scale: toward the captor, onto the spear.
inline void seat(float p[3], const float dir[3], float scale)
{
    const float len = std::sqrt(dir[0] * dir[0] + dir[1] * dir[1] + dir[2] * dir[2]);
    if (!(len > 1.0e-3f)) return;
    const float k = depth() * scale / len;
    for (int i = 0; i < 3; ++i) p[i] -= dir[i] * k;
}

} // namespace p2skewer
