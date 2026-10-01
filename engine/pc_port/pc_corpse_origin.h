#pragma once
// Corpse origin sanity for BTeki::dieSoon (engine-free).
//
// dieSoon places the carcass pellet at the 'carc' collision sphere centre.
// That centre is world space and only written by CollInfo::updateInfo, which
// runs in BTeki::refresh (and is skipped while rendering is not authoritative).
// A teki killed before its first refresh (e.g. spawned and killed in the same
// frame) still carries a never-written (0,0,0) centre ('carc', and 'cent'
// behind getCentre()), and the corpse appeared at the world origin (#972
// breadbug: dev-console "spawn 38" + "kill" in one frame; reproduced 3/3 on
// fork/main f38e70599). When the centre is implausibly far from the teki's
// position (mSRT.t, always valid), fall back to that position. A valid centre
// (inside the body) is kept unchanged.
namespace pc_corpse_origin {
constexpr float kMinSlack = 150.0f;  // world units; well above any carc offset
constexpr float kSizeFactor = 4.0f;  // times the teki collision size

inline float limit(float collisionSize) {
    const float scaled = collisionSize > 0.0f ? collisionSize * kSizeFactor : 0.0f;
    return scaled > kMinSlack ? scaled : kMinSlack;
}

// True if the carcass sphere centre (cx,cy,cz) is plausible for a body centred
// at (bx,by,bz) with the given collision size.
inline bool carcassUsable(float cx, float cy, float cz, float bx, float by, float bz, float collisionSize) {
    if (!(cx == cx) || !(cy == cy) || !(cz == cz)) return false;  // NaN
    const float dx = cx - bx, dy = cy - by, dz = cz - bz;
    const float lim = limit(collisionSize);
    return dx * dx + dy * dy + dz * dz <= lim * lim;
}
}  // namespace pc_corpse_origin
