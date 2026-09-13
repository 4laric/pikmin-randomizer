// Private real-GL Fuefuki whistle-path runtime fixture, issue #245. This
// file is compiled by the isolated fixture build only (root repo
// scripts/build_pikmin2_fixture.py); it is not part of the game target.
// Boots the frozen host with --experimental-pikmin2-room, stages a real
// captain and a real birthed Pikmin squad, and drives the lane-owned
// pc_p2_fuefuki binding seam with host adapters implemented over REAL
// engine queries (real pikiMgr scan, real positions, real alive/mode
// reads). The captain-whistle reclaim is executed through the real P1
// whistle path (Navi::callPikis) after the lane interception accepts.
//
// Honestly scoped (see native/tools/P2_FUEFUKI_BINDING.md gaps): no Fuefuki
// actor, no visual assets, no P1 follow-teki action exists (follow
// locomotion stays policy-fixture-only), and P1 has no PIKISTATE_Panic
// equivalent verified — released followers stay in PIKISTATE_Normal and the
// reclaim is verified through the real whistle gather.

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
#include <vector>

#include "pc_p2_fuefuki_binding.h"

namespace {
constexpr float kDt = 1.0f / 30.0f;

void require(bool value, const char* message)
{
    if (!value) {
        std::printf("FAIL FUEFUKI_RUNTIME %s\n", message);
        std::fflush(stdout);
        std::_Exit(1);
    }
}

// Retail parameters from the engine lane disc extraction
// (docs/PIKMIN2_ENGINE_DISC_PARMS.md). fp11/fp13/fp03/fp22/fp31 were not in
// the extraction batch and keep the header defaults; marked in the profile.
P2FuefukiFsmParms retailParms()
{
    P2FuefukiFsmParms p;
    p.maxGroundTime = 20.0f;            // fp01 retail
    p.minGroundTime = 10.0f;            // fp02 retail
    p.maxWhistleTimeNoSquad = 3.0f;     // fp12 retail re-cast interval
    p.struggleTime = 2.5f;              // fp21 retail
    p.attackRadius = 130.0f;            // retail whistle ring radius
    // mPrivateRadius = 60 is consumed by the probe (real distance check).
    // retail health 700 is the tick input in the defeat phase.
    return p;
}

struct FixtureWorld {
    Navi* navi = nullptr;
    Vector3f anchor;                 // policy-side beetle position
    std::vector<Piki*> pikis;        // 0..2 inside the 130 ring, 3..5 outside
    std::vector<bool> held;          // lane ownership view of each Pikmin
    std::vector<int> baselineMode;   // real mMode recorded after the scan claim
    std::vector<std::uint32_t> started;
    std::vector<std::pair<std::uint32_t, int>> ended;
    std::vector<bool> heldAtEnd;
    std::vector<std::pair<std::uint32_t, std::uint32_t>> writes;
    int killCalls = 0;
    bool killCarcass = false;
    P2FuefukiBinding* binding = nullptr;
};

FixtureWorld gWorld;

int pikiIndex(Piki* p)
{
    for (int i = 0; i < (int)gWorld.pikis.size(); ++i)
        if (gWorld.pikis[i] == p)
            return i;
    return -1;
}

float xzDist(const Vector3f& a, const Vector3f& b)
{
    float dx = a.x - b.x, dz = a.z - b.z;
    return speedy_sqrtf(dx * dx + dz * dz);
}

// (e) probe: real positions and real distance facts. mPrivateRadius 60
// retail; arrival/water pinned (flat room, policy-side target).
void rtProbe(void*, P2FuefukiProbeResult& out)
{
    out.x            = gWorld.anchor.x;
    out.z            = gWorld.anchor.z;
    out.arriveTarget = false;
    out.water        = false;
    out.intruder     = false;
    if (gWorld.navi && xzDist(gWorld.navi->mSRT.t, gWorld.anchor) < 60.0f)
        out.intruder = true;
    for (int i = 0; i < (int)gWorld.pikis.size(); ++i) {
        Piki* p = gWorld.pikis[i];
        if (p && p->isAlive() && !gWorld.held[i] && xzDist(p->mSRT.t, gWorld.anchor) < 60.0f)
            out.intruder = true;
    }
    out.valid = true;
}

// (a) real squad scan: iterate the real pikiMgr, XZ distance only (source
// sqrDistanceXZ, no height gate), classify from real Pikmin state.
// P1 approximations: callable = PIKISTATE_Normal (P2 per-state callable
// has no P1 equivalent); stuckToMouth = false (no mouth-stuck Pikmin are
// staged); alreadyTeki = false (no P1 follow-teki action exists; the
// ownership table rejects duplicates itself).
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
        e.id          = (std::uint32_t)(pikiIndex(p) + 1);
        e.living      = p->isAlive();
        e.callable    = p->getState() == PIKISTATE_Normal;
        e.stuckToMouth = false;
        e.alreadyTeki = false;
    }
    return n;
}

// (b) claim -> follow binding: record the claim and verify the real Pikmin
// object is alive; no captain-ownership write (mNavi/mMode untouched).
bool rtFollowStart(void*, std::uint32_t pikmin)
{
    if (pikmin == 0 || pikmin > (std::uint32_t)gWorld.pikis.size())
        return false;
    Piki* p = gWorld.pikis[pikmin - 1];
    if (!p || !p->isAlive())
        return false;
    gWorld.held[pikmin - 1] = true;
    gWorld.started.push_back(pikmin);
    return true;
}

void rtFollowEnd(void*, std::uint32_t pikmin, int reason)
{
    gWorld.ended.push_back({ pikmin, reason });
    if (pikmin >= 1 && pikmin <= (std::uint32_t)gWorld.pikis.size()) {
        gWorld.held[pikmin - 1] = false;
        // Contract-critical: table release committed before this callback.
        gWorld.heldAtEnd.push_back(gWorld.binding->getFsm().squad().holds(pikmin));
    }
}

// (b) ping return: held Pikmin whose real object is still alive.
int rtPingCollect(void*, std::uint32_t* out, int capacity)
{
    int n = 0;
    for (int i = 0; i < (int)gWorld.pikis.size() && n < capacity; ++i)
        if (gWorld.held[i] && gWorld.pikis[i] && gWorld.pikis[i]->isAlive())
            out[n++] = (std::uint32_t)(i + 1);
    return n;
}

// (c) marker for the lane's single ownership write; the fixture executes
// the real Navi::callPikis afterwards and verifies real squad membership.
void rtOwnershipWrite(void*, std::uint32_t pikmin, std::uint32_t naviId)
{
    gWorld.writes.push_back({ pikmin, naviId });
}

void rtKill(void*, bool carcassCarryAnim)
{
    gWorld.killCalls++;
    gWorld.killCarcass = carcassCarryAnim;
}

P2FuefukiHost rtHost()
{
    P2FuefukiHost h;
    h.probe          = rtProbe;
    h.enumerate      = rtEnumerate;
    h.followStart    = rtFollowStart;
    h.followEnd      = rtFollowEnd;
    h.pingCollect    = rtPingCollect;
    h.ownershipWrite = rtOwnershipWrite;
    h.kill           = rtKill;
    return h;
}

class FuefukiApp final : public PlugPikiApp {
    int frames = 0;
    int phase = 0;
    int reclaimWait = 0;
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
        case 1: scanClaimPhase(); break;
        case 2: nonRoutePhase(); break;
        case 3: defeatReclaimPhase(); break;
        case 4: reclaimConfirmPhase(); break;
        }
        return result;
    }

private:
    void setup()
    {
        Navi* navi = naviMgr->getNavi();
        gWorld.navi = navi;
        const float ground = mapMgr->getMinY(0, 0, false);
        require(std::isfinite(ground), "ground unavailable");
        gWorld.anchor = Vector3f(0, ground, 0);
        // Captain well outside the 60-unit retail private radius.
        navi->resetPosition(Vector3f(0, ground, 300));
        navi->mFaceDirection = 0;
        // Real squad: 3 Pikmin inside the 130 ring but outside the 60
        // private radius, 3 beyond the ring.
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
            // Fresh births default to the captain's formation in this engine
            // (mNavi is set by init); stage them as free-roaming Pikmin so
            // the fixture owns the baseline the seam must not disturb.
            p->changeMode(PikiMode::FreeMode, navi);
            gWorld.pikis.push_back(p);
            gWorld.held.push_back(false);
        }
        require(gWorld.pikis.size() == 6, "squad size");
        require(binding.bind(rtHost(), retailParms(), nullptr), "binding bind");
        gWorld.binding = &binding;
        P2FuefukiBindOut out = binding.spawn(1);
        require(out.accepted && out.state == P2FuefukiFsmState::Land, "spawn");
        std::printf("P2_FUEFUKI_RT_READY squad=6 ring=130 private=60 fp12=3.0 fp01=20 fp21=2.5 health=700 "
                    "no_beetle_actor=1 no_visual_assets=1\n");
        std::fflush(stdout);
        phase = 1;
    }

    void scanClaimPhase()
    {
        driveUntil(P2FuefukiFsmState::Whisle, 200);
        P2FuefukiBindTick t;
        t.delta = kDt; t.health = 700.0f; t.animPlaying = true;
        P2FuefukiBindOut out = drive(t); // first scan tick (ring 1/30 grown)
        int claimed          = out.claimed;
        for (int i = 0; i < 30; ++i) {   // ring reaches full 130 after 1 s
            out = drive(t);
            claimed += out.claimed;
        }
        require(claimed == 3, "real scan claim count");
        require(gWorld.started.size() == 3, "follow start count");
        for (std::uint32_t id : gWorld.started)
            require(id >= 1 && id <= 3, "outside-ring Pikmin claimed");
        for (int i = 0; i < 6; ++i)
            require(gWorld.held[i] == (i < 3), "held set mismatch");
        // per-tick ping from real alive followers keeps the squad active
        P2FuefukiBindOut pinged = drive(t);
        require(pinged.fsm.squadActive, "squad ping inactive");
        require(out.whistleRadius == 130.0f, "retail ring radius");
        for (Piki* p : gWorld.pikis)
            gWorld.baselineMode.push_back(p->mMode);
        std::printf("P2_FUEFUKI_RT_SCAN claimed=3 outside=0 radius=%.1f squad_active=1 real_pikimgr=1\n",
                    out.whistleRadius);
        std::fflush(stdout);
        phase = 2;
    }

    void nonRoutePhase()
    {
        // Live beetle: captain whistle, captain switch and party combine
        // must NOT route to beetle-held Pikmin on the real objects.
        for (std::uint32_t id = 1; id <= 3; ++id) {
            require(!binding.onCaptainWhistle(id, 0), "held Pikmin reclaim routed");
            require(!binding.onCaptainSwitch(id), "captain switch routed");
            require(!binding.onPartyCombine(id), "party combine routed");
            require(binding.getFsm().squad().holds(id), "held lost during non-route");
            Piki* p = gWorld.pikis[id - 1];
            // The engine must not have moved the beetle-held Pikmin: the
            // real mode stays at the recorded free-roam baseline.
            require(p->mMode == gWorld.baselineMode[id - 1], "held Pikmin mode disturbed");
            require(p->mMode != PikiMode::FormationMode, "held Pikmin joined squad");
        }
        require(gWorld.writes.empty(), "ownership write during non-route");
        std::puts("P2_FUEFUKI_RT_NONROUTE whistle=0 switch=0 combine=0 held=3 writes=0 live_beetle=1");
        std::fflush(stdout);
        phase = 3;
    }

    void defeatReclaimPhase()
    {
        P2FuefukiBindTick t;
        t.delta = kDt; t.health = 0.0f; t.animPlaying = true;
        P2FuefukiBindOut out = drive(t);
        if (out.fsm.requestFinishMotion) {
            t.keyEvent = 4;
            out        = drive(t);
        }
        require(out.state == P2FuefukiFsmState::Dead, "death routing");
        require(gWorld.ended.size() == 3, "panic release count");
        for (int i = 0; i < 3; ++i) {
            require(gWorld.ended[i].second == P2FUEFUKI_END_PANIC, "release reason");
            require(!gWorld.heldAtEnd[i], "release not committed before callback");
        }
        std::puts("P2_FUEFUKI_RT_DEATH released=3 reason=panic committed_before_callback=1");
        // Captain-whistle reclaim interception on the real P1 whistle path:
        // the lane accepts the Panic-released follower, then the REAL
        // Navi::callPikis performs the gather.
        require(binding.onCaptainWhistle(1, 0), "reclaim rejected");
        require(gWorld.writes.size() == 1 && gWorld.writes[0].first == 1, "single write");
        require(!binding.onCaptainWhistle(1, 0), "reclaim not once-only");
        gWorld.navi->mCursorWorldPos = gWorld.anchor;
        gWorld.navi->callPikis(140.0f, true);
        Piki* reclaimed = gWorld.pikis[0];
        require(reclaimed->mNavi == gWorld.navi, "reclaimed Pikmin captain");
        // Real P1 whistle path: callPikis transits the Pikmin to LookAt;
        // the formation join completes in later frames (LookAt timeout).
        require(reclaimed->getState() == PIKISTATE_LookAt
                    || reclaimed->mMode == PikiMode::FormationMode,
                "reclaim not accepted by real whistle path");
        // Outside-ring Pikmin (beyond callPikis radius) are untouched.
        for (int i = 3; i < 6; ++i)
            require(gWorld.pikis[i]->mMode != PikiMode::FormationMode, "outside Pikmin gathered");
        std::printf("P2_FUEFUKI_RT_RECLAIM id=1 writes=1 real_callPikis=1 state=%d navi_match=1 outside_untouched=3\n",
                    reclaimed->getState());
        reclaimWait = 0;
        phase       = 4;
    }

    void reclaimConfirmPhase()
    {
        // Wait for the real LookAt -> formation join to complete.
        Piki* reclaimed = gWorld.pikis[0];
        if (reclaimed->mMode != PikiMode::FormationMode) {
            require(++reclaimWait < 300, "formation join timeout");
            return;
        }
        std::printf("P2_FUEFUKI_RT_FORMJOIN id=1 mode=%d frames=%d\n", (int)reclaimed->mMode, reclaimWait);
        // Dead-anim END: kill + Carry carcass through the seam.
        P2FuefukiBindTick dk;
        dk.delta = kDt; dk.health = 0.0f; dk.animPlaying = true; dk.keyEvent = 4;
        P2FuefukiBindOut out = drive(dk);
        require(out.kill && out.carcassCarryAnim, "kill/carcass delivery");
        require(gWorld.killCalls == 1 && gWorld.killCarcass, "kill callback");
        std::puts("P2_FUEFUKI_RT_KILL carcass=carry_anim");
        std::puts("PASS FUEFUKI_RUNTIME");
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
    require(pc_window_init("Fuefuki whistle-path runtime fixture", 960, 720), "window init");
    pc_settings_init();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new FuefukiApp());
    return 0;
}
