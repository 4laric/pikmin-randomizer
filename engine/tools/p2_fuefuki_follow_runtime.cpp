// Private real-GL Fuefuki follow-locomotion runtime fixture, issue #245.
// Compiled by the isolated fixture build only (root repo
// scripts/build_pikmin2_fixture.py); not part of the game target.
//
// Boots the frozen host with --experimental-pikmin2-room, births a real
// squad, claims the in-ring Pikmin through the lane binding seam, and then
// drives the ActTeki follow-locomotion policy (pc_p2_fuefuki_follow.h)
// against the REAL engine: the host sample reads real pikiMgr positions and
// the host drive applies the command to the real Piki actor (faithful
// Piki::setSpeed plus the labeled mVolatileVelocity approximation). The
// fixture measures the follower's real position change across frames.
//
// Honestly scoped: there is still no dedicated P1 follow-teki action (the
// volatile impulse is an approximation, see P2_FUEFUKI_FOLLOW.md), no Fuefuki
// actor/visual, and the beetle anchor is policy-side and static.

#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "gl/pc_opengl.h"
#include "App.h"
#include "Node.h"
#include "Graphics.h"
#include "MapMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "MoviePlayer.h"
#include "Shape.h"
#include "system.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "pc_window.h"
#include "pc_p2_preview.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "Traversable.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

#include "pc_p2_fuefuki_binding.h"
#include "pc_p2_fuefuki_visual.h"

namespace {
constexpr float kDt = 1.0f / 30.0f;

void require(bool value, const char* message)
{
    if (!value) {
        std::printf("FAIL FUEFUKI_FOLLOW_RUNTIME %s\n", message);
        std::fflush(stdout);
        std::_Exit(1);
    }
}

P2FuefukiFsmParms retailParms()
{
    P2FuefukiFsmParms p;
    p.maxGroundTime = 20.0f;            // fp01 retail
    p.minGroundTime = 10.0f;            // fp02 retail
    p.maxWhistleTimeNoSquad = 3.0f;     // fp12 retail re-cast interval
    p.struggleTime = 2.5f;              // fp21 retail
    p.attackRadius = 130.0f;            // retail whistle ring radius
    return p;
}

P2FuefukiFollowParms retailFollowParms()
{
    P2FuefukiFollowParms p;
    p.followDistance = 100.0f; // source FOLLOW_DISTANCE
    return p;
}

struct World {
    Navi* navi = nullptr;
    Vector3f anchor;
    std::vector<Piki*> pikis;
    std::vector<bool> held;
    std::vector<int> baselineMode;
    std::vector<std::uint32_t> started;
    std::vector<std::pair<std::uint32_t, int>> ended;
    int moveCommands = 0;
    int stopCommands = 0;
    int writes = 0;
    P2FuefukiBinding* binding = nullptr;
};

World g;

int pikiIndex(Piki* p)
{
    for (int i = 0; i < (int)g.pikis.size(); ++i)
        if (g.pikis[i] == p)
            return i;
    return -1;
}

float xzDist(const Vector3f& a, const Vector3f& b)
{
    float dx = a.x - b.x, dz = a.z - b.z;
    return speedy_sqrtf(dx * dx + dz * dz);
}

void rtProbe(void*, P2FuefukiProbeResult& out)
{
    out.x = g.anchor.x;
    out.z = g.anchor.z;
    out.vx = 0.0f;
    out.vz = 0.0f;
    out.arriveTarget = false;
    out.water = false;
    out.intruder = false;
    out.valid = true;
}

int rtEnumerate(void*, float x, float z, float radius, P2FuefukiSquadEntry* out, int capacity)
{
    int n = 0;
    Iterator it(pikiMgr);
    CI_LOOP(it)
    {
        Piki* p = static_cast<Piki*>(*it);
        if (!p || n >= capacity)
            continue;
        Vector3f pos(x, p->mSRT.t.y, z);
        if (xzDist(p->mSRT.t, pos) > radius)
            continue;
        P2FuefukiSquadEntry& e = out[n++];
        e.id = (std::uint32_t)(pikiIndex(p) + 1);
        e.living = p->isAlive();
        e.callable = p->getState() == PIKISTATE_Normal;
        e.stuckToMouth = false;
        e.alreadyTeki = false;
    }
    return n;
}

bool rtFollowStart(void*, std::uint32_t pikmin)
{
    if (pikmin == 0 || pikmin > (std::uint32_t)g.pikis.size())
        return false;
    Piki* p = g.pikis[pikmin - 1];
    if (!p || !p->isAlive())
        return false;
    g.held[pikmin - 1] = true;
    g.started.push_back(pikmin);
    return true;
}

void rtFollowEnd(void*, std::uint32_t pikmin, int reason)
{
    g.ended.push_back({ pikmin, reason });
    if (pikmin >= 1 && pikmin <= (std::uint32_t)g.pikis.size())
        g.held[pikmin - 1] = false;
}

int rtPingCollect(void*, std::uint32_t* out, int capacity)
{
    int n = 0;
    for (int i = 0; i < (int)g.pikis.size() && n < capacity; ++i)
        if (g.held[i] && g.pikis[i] && g.pikis[i]->isAlive())
            out[n++] = (std::uint32_t)(i + 1);
    return n;
}

void rtOwnershipWrite(void*, std::uint32_t, std::uint32_t) { g.writes++; }
void rtKill(void*, bool) { }

// (g) real follower sample: the Pikmin's live world position.
bool rtFollowerSample(void*, std::uint32_t pikmin, float& x, float& z)
{
    if (pikmin == 0 || pikmin > (std::uint32_t)g.pikis.size())
        return false;
    Piki* p = g.pikis[pikmin - 1];
    if (!p || !p->isAlive())
        return false;
    x = p->mSRT.t.x;
    z = p->mSRT.t.z;
    return true;
}

// (g) real follower drive, mirroring pc_p2_hardlanes.cpp:
// faithful Piki::setSpeed plus the labeled volatile-velocity approximation
// (P1 ActFree overwrites mTargetVelocity before moveVelocity each frame).
void rtFollowDrive(void*, std::uint32_t pikmin, const P2FuefukiFollowMove& move)
{
    if (pikmin == 0 || pikmin > (std::uint32_t)g.pikis.size())
        return;
    Piki* p = g.pikis[pikmin - 1];
    if (!p || !p->isAlive())
        return;
    if (move.stop) {
        p->mTargetVelocity.set(0.0f, 0.0f, 0.0f);
        p->mVolatileVelocity.set(0.0f, 0.0f, 0.0f);
        g.stopCommands++;
        return;
    }
    Vector3f dir(move.dirX, 0.0f, move.dirZ);
    p->setSpeed(move.speed, dir);
    p->mVolatileVelocity.set(move.dirX * p->mMoveSpeed, 0.0f, move.dirZ * p->mMoveSpeed);
    g.moveCommands++;
}

P2FuefukiHost rtHost()
{
    P2FuefukiHost h;
    h.probe = rtProbe;
    h.enumerate = rtEnumerate;
    h.followStart = rtFollowStart;
    h.followEnd = rtFollowEnd;
    h.pingCollect = rtPingCollect;
    h.ownershipWrite = rtOwnershipWrite;
    h.kill = rtKill;
    h.followerSample = rtFollowerSample;
    h.followDrive = rtFollowDrive;
    h.randFloat = nullptr;
    return h;
}

class FollowApp final : public PlugPikiApp {
    int frames = 0;
    int phase = 0;
    int locoFrames = 0;
    int moveFrames = 0;
    float locoStart = 0.0f;
    Vector3f approachEnd;
    float moveStartDist = 0.0f;
    P2FuefukiBinding binding;

    P2FuefukiBindOut drive(const P2FuefukiBindTick& t)
    {
        P2FuefukiBindOut out = binding.tick(t);
        require(out.accepted, "binding tick rejected");
        return out;
    }

    void driveUntil(P2FuefukiFsmState target, int maxTicks)
    {
        P2FuefukiBindTick t;
        t.delta = kDt; t.health = 700.0f; t.animPlaying = true; t.turnComplete = true;
        for (int i = 0; i < maxTicks && binding.getFsm().getState() != target; ++i) {
            t.keyEvent = (binding.getFsm().getState() == P2FuefukiFsmState::Land) ? 2 + (i % 3) : 0;
            P2FuefukiBindOut out = drive(t);
            if (binding.getFsm().getState() != P2FuefukiFsmState::Land && out.fsm.requestFinishMotion) {
                t.keyEvent = 4;
                drive(t);
            }
        }
        require(binding.getFsm().getState() == target, "drive stall");
    }

public:
    int idle() override
    {
        int result = PlugPikiApp::idle();
        require(++frames < 1800, "timeout");
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
            gameflow.mMoviePlayer->requestSkip();
            return result;
        }
        if (!pc_p2_preview_ready() || !naviMgr || !naviMgr->getNavi() || gameflow.mPauseAll
            || gameflow.mIsUIOverlayActive) {
            return result;
        }
        switch (phase) {
        case 0: setup(); break;
        case 1: claimPhase(); break;
        case 2: locomotionPhase(); break;
        case 3: trailChasePhase(); break;
        case 4: finishPhase(); break;
        }
        return result;
    }

private:
    void setup()
    {
        Navi* navi = naviMgr->getNavi();
        g.navi = navi;
        const float ground = mapMgr->getMinY(0, 0, false);
        require(std::isfinite(ground), "ground unavailable");
        g.anchor = Vector3f(0, ground, 0);
        navi->resetPosition(Vector3f(0, ground, 300));
        navi->mFaceDirection = 0;
        const float offsets[6][2] = { { 70, 0 }, { 0, 90 }, { -80, 40 }, { 0, 220 }, { 250, 0 }, { -260, -40 } };
        for (int i = 0; i < 6; ++i) {
            Piki* p = static_cast<Piki*>(pikiMgr->birth());
            require(p != nullptr, "squad birth");
            p->init(navi);
            p->initColor(Red);
            p->setFlower(Leaf);
            Vector3f spot(offsets[i][0], ground + 2.0f, offsets[i][1]);
            spot.y = mapMgr->getMinY(spot.x, spot.z, true) + 2.0f;
            p->resetPosition(spot);
            p->mFSM->transit(p, PIKISTATE_Normal);
            p->changeMode(PikiMode::FreeMode, navi);
            g.pikis.push_back(p);
            g.held.push_back(false);
        }
        require(g.pikis.size() == 6, "squad size");
        require(pc_p2_fuefuki_visual_ready(), "visual bank not staged");
        require(pc_p2_fuefuki_visual_clip_count() == 8, "visual clip count");
        require(binding.bind(rtHost(), retailParms(), nullptr, retailFollowParms()), "binding bind");
        require(binding.spawn(1).accepted, "spawn");
        g.binding = &binding;
        std::printf("P2_FUEFUKI_FOLLOW_RT_READY squad=6 anchor=0,0 ring=130 follow_distance=100 locomotion=actteki_volatile_approx\n");
        std::fflush(stdout);
        phase = 1;
    }

    void claimPhase()
    {
        driveUntil(P2FuefukiFsmState::Whisle, 200);
        P2FuefukiBindTick t;
        t.delta = kDt; t.health = 700.0f; t.animPlaying = true;
        P2FuefukiBindOut out = drive(t);
        int claimed = out.claimed;
        for (int i = 0; i < 30; ++i) {
            out = drive(t);
            claimed += out.claimed;
        }
        require(claimed == 3, "claim count");
        require(g.started.size() == 3, "follow start count");
        for (int i = 0; i < 6; ++i)
            require(g.held[i] == (i < 3), "held set mismatch");
        for (Piki* p : g.pikis)
            g.baselineMode.push_back(p->mMode);
        locoStart = xzDist(g.pikis[0]->mSRT.t, g.anchor);
        require(locoStart > 50.0f && locoStart < 100.0f, "unexpected start distance");
        // State-driven visual clip: the FSM is casting, so the mapped clip must
        // be "whisle" (landing/landfail are not converted). Only re-select on a
        // change so the pose advances within the clip.
        pc_p2_fuefuki_visual_set_position(g.anchor.x, g.anchor.y, g.anchor.z);
        const int state = static_cast<int>(binding.getFsm().getState());
        const char* desired = pc_p2_fuefuki_visual_clip_for_state(state);
        const char* current = pc_p2_fuefuki_visual_active_clip();
        if (!current || std::strcmp(current, desired) != 0) {
            pc_p2_fuefuki_visual_clip(desired);
        }
        require(std::strcmp(pc_p2_fuefuki_visual_active_clip(), "whisle") == 0,
                "FSM state did not map to the whisle clip");
        std::printf("P2_FUEFUKI_FOLLOW_RT_CLAIM claimed=3 hold=3 start_dist=%.1f\n", locoStart);
        std::printf("P2_FUEFUKI_VISUAL_STATE state=%d clip=%s pose=%d\n", state,
                    pc_p2_fuefuki_visual_active_clip(), pc_p2_fuefuki_visual_pose_index());
        std::fflush(stdout);
        phase = 2;
    }

    void locomotionPhase()
    {
        P2FuefukiBindTick t;
        t.delta = kDt; t.health = 700.0f; t.animPlaying = true;
        drive(t);
        ++locoFrames;
        const float dist = xzDist(g.pikis[0]->mSRT.t, g.anchor);
        if (dist < locoStart - 20.0f || locoFrames >= 75) {
            require(g.moveCommands > 0, "no follow move command issued");
            require(dist < locoStart - 5.0f, "follower did not move toward the beetle");
            require(g.writes == 0, "ownership write during locomotion");
            for (int i = 0; i < 3; ++i) {
                require(g.pikis[i]->mMode == g.baselineMode[i], "held Pikmin mode disturbed");
                require(g.pikis[i]->mMode == PikiMode::FreeMode, "held Pikmin joined squad");
            }
            // Outside-ring Pikmin are not driven.
            for (int i = 3; i < 6; ++i)
                require(xzDist(g.pikis[i]->mSRT.t, g.anchor) > 130.0f, "outside Pikmin moved into ring");
            std::printf("P2_FUEFUKI_FOLLOW_RT_MOVE start=%.1f end=%.1f frames=%d moves=%d stops=%d writes=0 real_piki=1\n",
                        locoStart, dist, locoFrames, g.moveCommands, g.stopCommands);
            std::fflush(stdout);
            approachEnd = g.pikis[0]->mSRT.t;
            moveStartDist = dist;
            g.moveCommands = 0;
            g.stopCommands = 0;
            phase = 3;
        }
    }

    // Moving-beetle trail chase: the anchor walks away along -Z and the
    // follower must keep following the real footmark trail instead of parking
    // at the static target. The anchor is policy-side here (no native beetle
    // actor), but the Pikmin motion and the trail it follows are real.
    void trailChasePhase()
    {
        const float step = 2.5f; // units/frame -> ~75 units/s at the 30 Hz tick
        g.anchor.z -= step;
        P2FuefukiBindTick t;
        t.delta = kDt; t.health = 700.0f; t.animPlaying = true;
        drive(t);
        // The visual anchor tracks the beetle; the FSM clip follows the state
        // (only re-selected on a change so the pose advances within the clip).
        pc_p2_fuefuki_visual_set_position(g.anchor.x, g.anchor.y, g.anchor.z);
        const char* desired = pc_p2_fuefuki_visual_clip_for_state(
            static_cast<int>(binding.getFsm().getState()));
        if (std::strcmp(pc_p2_fuefuki_visual_active_clip(), desired) != 0) {
            pc_p2_fuefuki_visual_clip(desired);
        }
        pc_p2_fuefuki_visual_update(1.0f);
        ++moveFrames;
        const Vector3f& fpos = g.pikis[0]->mSRT.t;
        const float moved = xzDist(fpos, approachEnd);
        const float toAnchor = xzDist(fpos, g.anchor);
        if (moved >= 25.0f || moveFrames >= 60) {
            require(g.moveCommands > 0, "no trail-chase move command issued");
            require(moved >= 15.0f, "follower did not chase the moving trail");
            require(toAnchor <= 180.0f, "follower lost the moving beetle");
            require(g.writes == 0, "ownership write during trail chase");
            float vx = 0.0f, vy = 0.0f, vz = 0.0f;
            pc_p2_fuefuki_visual_position(vx, vy, vz);
            require(std::fabs(vx - g.anchor.x) < 0.01f && std::fabs(vz - g.anchor.z) < 0.01f,
                    "visual anchor did not track the moving beetle");
            std::printf("P2_FUEFUKI_FOLLOW_RT_TRAIL anchors_moved=%.1f follower_moved=%.1f dist_to_anchor=%.1f frames=%d moves=%d stops=%d writes=0\n",
                        -(g.anchor.z), moved, toAnchor, moveFrames, g.moveCommands, g.stopCommands);
            std::printf("P2_FUEFUKI_VISUAL_TRACK x=%.1f z=%.1f clip=%s pose=%d\n", vx, vz,
                        pc_p2_fuefuki_visual_active_clip(), pc_p2_fuefuki_visual_pose_index());
            std::fflush(stdout);
            phase = 4;
        }
    }

    void finishPhase()
    {
        require(pc_p2_fuefuki_visual_drew(), "visual never reached the draw path");
        std::puts("PASS FUEFUKI_FOLLOW_RUNTIME");
        std::fflush(stdout);
        std::_Exit(0);
    }
};
} // namespace

int main(int argc, char** argv)
{
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    pc_bbft_init(argc, argv);
    require(pc_pikipelago_room_preview(), "requires --experimental-pikmin2-room");
    require(pc_window_init("Fuefuki follow runtime fixture", 960, 540), "window init");
    pc_window_center();
    {
        SDL_Window* window = SDL_GL_GetCurrentWindow();
        int width = 0, height = 0, x = 0, y = 0; SDL_GetWindowSize(window, &width, &height);
        SDL_GetWindowPosition(window, &x, &y);
        SDL_Rect bounds{0, 0, 0, 0}; SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(window), &bounds);
        const bool centered = std::abs(x - (bounds.x + (bounds.w - width) / 2)) <= 2
            && std::abs(y - (bounds.y + (bounds.h - height) / 2)) <= 2;
        std::printf("P2_FUEFUKI_FOLLOW_RT_WINDOW size=%dx%d pos=%d,%d display=%dx%d centered=%d\n",
            width, height, x, y, bounds.w, bounds.h, int(centered));
        std::fflush(stdout);
    }
    pc_settings_init();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new FollowApp());
    return 0;
}
