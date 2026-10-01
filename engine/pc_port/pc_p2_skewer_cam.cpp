#include "pc_p2_skewer_cam.h"

#include "gl/pc_gfx.h"
#include "teki.h"
#include "Piki.h"

#include <cmath>
#include <cstdio>
#include <cstdlib>

namespace {
struct State {
    bool have = false;
    float target[3] = {0, 0, 0};
    float yaw = 0.0f;
    int age = 0;      // frames since the last follow call
    int ticks = 0;    // follow calls in the current hold
    int shots = 0;
    char prefix[32] = {0};
};
State s;

float envFloat(const char* name, float fallback)
{
    const char* e = std::getenv(name);
    return e && *e ? float(std::atof(e)) : fallback;
}
}

bool pc_p2_skewer_cam_enabled()
{
    static const bool on = [] {
        const char* e = std::getenv("PIKMIN_P2_SKEWER_CAM");
        return e && *e && *e != '0';
    }();
    return on;
}

void pc_p2_skewer_cam_follow(BTeki* actor, float yaw, const char* prefix)
{
    if (!pc_p2_skewer_cam_enabled() || !actor) return;
    Creature* held = nullptr;
    for (Creature* c = actor->mStickListHead; c; c = c->mNextSticker)
        if (c->isPiki() && c->isStickToMouth()) { held = c; break; }
    if (!held) {
        if (s.age > 20) s.ticks = 0; // a new hold starts a new series
        return;
    }
    s.have = true;
    s.age = 0;
    s.target[0] = held->mSRT.t.x;
    s.target[1] = held->mSRT.t.y;
    s.target[2] = held->mSRT.t.z;
    s.yaw = yaw;
    std::snprintf(s.prefix, sizeof(s.prefix), "%s", prefix);
    if (s.ticks % 8 == 0 && s.shots < 12) {
        char key[64];
        std::snprintf(key, sizeof(key), "x|%s_h%d", prefix, s.shots++);
        pc_gfx_proxy_shot_notify_after(key, 3);
    }
    ++s.ticks;
}

bool pc_p2_skewer_cam_pose(float eye[3], float look[3], float* focusDist)
{
    if (!pc_p2_skewer_cam_enabled() || !s.have) return false;
    if (++s.age > 12) return false; // not held any more: hand the camera back
    static const float dist = envFloat("PIKMIN_P2_SKEWER_CAM_DIST", 55.0f);
    static const float lift = envFloat("PIKMIN_P2_SKEWER_CAM_LIFT", 12.0f);
    // right-hand side of the actor: (cos yaw, 0, -sin yaw)
    const float rx = std::cos(s.yaw), rz = -std::sin(s.yaw);
    eye[0] = s.target[0] + rx * dist;
    eye[1] = s.target[1] + lift;
    eye[2] = s.target[2] + rz * dist;
    look[0] = s.target[0];
    look[1] = s.target[1];
    look[2] = s.target[2];
    if (focusDist) {
        const float dx = look[0] - eye[0], dy = look[1] - eye[1], dz = look[2] - eye[2];
        *focusDist = std::sqrt(dx * dx + dy * dy + dz * dz);
    }
    return true;
}
