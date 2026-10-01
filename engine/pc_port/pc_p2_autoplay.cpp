// TEST-ONLY headless autoplay bot driver (brief keys: bot-impl wf9, bot-v2/v3/v4 wf10, bot-v5 wf10).
//
// Drives the game through the NORMAL controller input path: each logical
// tick ControllerMgr::update() calls pc_p2_autoplay_tick(), which senses
// live game state (read-only), steps the engine-free Brain
// (pc_p2_autoplay_policy.h), converts its world-space move vector through
// the live camera basis into a stick deflection, and publishes pad buttons +
// stick via pc_p2_input_script_set() -- the same hook the real pad read
// feeds (ControllerMgr::updateController). The bot never teleports,
// never mode-forces, never mutates enemies/Pikmin: only pad state.
//
// Enabled only when PIKMIN_RANDOMIZER_AUTOPLAY is set (non-empty, != "0").
// Otherwise tick() returns before touching anything: production input is
// untouched (native test: tools/p2_autoplay_test.cpp).
//
// bot-v7 (wf10): Aftermath knows the corpse's declared carry minimum
// (carryWant, PelletConfig p01, latched from the tracked pellet or the dead
// host's corpse config) and logs AUTOPLAY_CARRY carriers=<near> want=<min>
// tdist=<d> moving=<0/1>; proxy ("proxy|" visual) campaign actors bind
// their lane-06 ordinary-delivery source at visual-bind time so a hauled
// proxy corpse grants onion:p2 exactly once like Sokkuri (v6b-1: Chappy and
// Tadpole corpses reached the Onion with crews attached but no receipt
// could ever land - nothing had ever bound a delivery source for proxies).
// bot-v6 (wf10): power mode takes the squad in ONE step (whole Onion queued
// through the normal exitPikis path once at start; WithdrawSeek waits neutral
// until field>=80, no menu) and logs AUTOPLAY_POWER squad=<n> seconds=<t>;
// Select names a dead/absent target (GIVEUP reason=target_gone) and a latched
// kill for the same token returns to Aftermath so delivery still finishes.
// bot-v5 (wf10): aftermath delivers (no whistle; onto the corpse, throw to
// seed grabs, back off, bounded re-throws) with live per-corpse carry sensing
// (TransportMode bodies near the corpse + pellet carriers), a window that
// extends only while carriers > 0 AND the corpse moves, named giveup reasons,
// and AUTOPLAY_CARRY diagnostics; receipt stays the per-token ledger query.
// bot-v3 (wf10): approach plans over the routeMgr waypoint graph with
// next-nearest start/goal alternates + reversed legs, never repeats an
// identical detour, logs AUTOPLAY_ROUTE_FAIL when the graph cannot route,
// and diagnoses stick-vs-motion (navi pos in STUCK, NAVI diagnostic with
// stick/state/yaw/velocity). Unreachable-after-N-replans GIVEUP idles near
// the Onion.
// bot-v2 (wf10): waypoint-by-waypoint route-graph following with BFS
// fallback + replan on every STUCK; generic death latch (health/isAlive/
// dead-state/corpse pellet) for every species; Onion receipt sensing from
// the delivery ledger; flyer height/grab senses (Sarai low-or-grabbing
// throws + whistle, Kurage body-position throws).

#include "pc_p2_autoplay_policy.h"
#include "pc_p2_queen_teki.h"

#include "pc_p2_input_script.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_sokkuri.h"
#include "pc_p2_kogane.h"
#include "pc_p2_chappy.h"
#include "pc_p2_fuefuki_teki.h"
#include "pc_p2_bigtreasure_teki.h"
#include "pc_p2_teki_lifetime.h"
#include "pc_p2_test_day_cycle.h"
#include "pc_p2_dangomushi.h"
#include "pc_p2_purple.h"
#include "pc_randomizer.h"
#include "Controller.h"

#include "teki.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Pellet.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "PikiState.h"
#include "GlobalGameOptions.h"
#include "BaseInf.h"
#include "GameStat.h"
#include "PlayerState.h"
#include "settings/pc_settings.h"
#include "Generator.h"
#include "GoalItem.h"
#include "ItemMgr.h"
#include "MapMgr.h"
#include "MapCode.h"
#include "Route.h"
#include "WorkObject.h"
#include "Camera.h"
#include "BuildingItem.h"
#include "WorkObject.h"
#include "gameflow.h"
#include "MoviePlayer.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <cstdio>
#include <queue>
#include <set>
#include <string>
#include <vector>

// Pad bits emitted here must equal the engine's KeyboardButtons.
static_assert(unsigned(p2autoplay::PadA) == unsigned(KBBTN_A), "autoplay pad bits drifted");
static_assert(unsigned(p2autoplay::PadB) == unsigned(KBBTN_B), "autoplay pad bits drifted");
static_assert(unsigned(p2autoplay::PadMainUp) == unsigned(KBBTN_MSTICK_UP), "autoplay pad bits drifted");
static_assert(unsigned(p2autoplay::PadMainDown) == unsigned(KBBTN_MSTICK_DOWN), "autoplay pad bits drifted");
static_assert(unsigned(p2autoplay::PadMainLeft) == unsigned(KBBTN_MSTICK_LEFT), "autoplay pad bits drifted");
static_assert(unsigned(p2autoplay::PadMainRight) == unsigned(KBBTN_MSTICK_RIGHT), "autoplay pad bits drifted");
static_assert(unsigned(p2autoplay::PadStart) == unsigned(KBBTN_START), "autoplay pad bits drifted");

namespace {

// Engagement token: the campaign token, or for a #901 TEST-ONLY P1 target
// (whose retail _70 may be zero) its seed generator uid.
unsigned botToken(const BTeki* actor)
{
    if (actor && actor->mGenerator && p2autoplay::isP1TargetUid(pc_randomizer_generator_id(actor->mGenerator)))
        return pc_randomizer_generator_id(actor->mGenerator);
    return pc_p2_campaign_token(actor);
}

float distXZ(float ax, float az, float bx, float bz)
{
    const float dx = ax - bx, dz = az - bz;
    return std::sqrt(dx * dx + dz * dz);
}

const char* sourceDisplayName(unsigned source)
{
    switch (source) {
    case 79: return "Sokkuri";
    case 9: return "Kogane";
    case 23: return "Sarai";
    case 57: return "Kurage";
    case 72: return "OniKurage";
    case 58: return "BombSarai";
    case 54: return "Miulin";
    case 44: return "BlueKochappy";
    case 59: return "FireOtakara";
    case 60: return "WaterOtakara";
    case 61: return "GasOtakara";
    case 62: return "ElecOtakara";
    default: return "unknown";
    }
}

struct Engagement {
    unsigned token = 0;
    unsigned source = 0;
    float initialHealth = 0.0f;
    int initialNectar = 0;
    float lastX = 0.0f;
    float lastZ = 0.0f;
    bool homeValid = false; // #897 roller home (first sighting, still in Stay)
    float homeX = 0.0f;
    float homeZ = 0.0f;
    bool lastAlive = false;
    bool carryLatch = false;
    bool deadLatch = false; // generic death observed (any species, gap 5)
    // bot-v5 corpse tracking: death spot (window anchor), live corpse pos
    // (dead body, then its pellet - follows the haul), pellet carrier
    // strength, TransportMode bodies near the corpse.
    float deathX = 0.0f;
    float deathZ = 0.0f;
    bool deathRecorded = false;
    float trackX = 0.0f; // bot-v5 recent-motion fix (still-time anchor)
    float trackZ = 0.0f;
    float stillTime = 0.0f;
    bool bodyPresent = false;
    bool pelletFound = false;
    int pelletCarriers = 0;
    int carryNear = 0;
    // bot-v7: declared carry minimum (PelletConfig p01 strength units) for
    // the tracked corpse, latched once resolved; host teki type while only
    // the dead body exists (pellet config lookup key).
    int carryWant = 0;
    int hostType = -1;
    // #901: the dropped ship part this engagement tracked (config pointers are
    // static in pelletMgr), latched so its departure (ship suck) is sensed.
    const PelletConfig* partConfig = nullptr;
};

p2autoplay::Brain sBrain;
Engagement sEngage;
std::set<unsigned> sCompleted;
// Waypoint-by-waypoint route-graph path (bot-v2 gap 2, bot-v3 hardening):
// legs from a nearby waypoint through the graph to a waypoint near the
// target, advanced as each leg is reached, replanned on every STUCK.
std::vector<std::pair<float, float>> sPath;
size_t sPathIdx = 0;
float sLegTime = 0.0f;
// bot-v3: per-engagement replan count + detour history so an identical
// detour is never repeated (bc2: same sidestep 38x at dist=1065).
int sReplanCount = 0;
unsigned sReplanToken = 0;
float sLastDetourX = 0.0f, sLastDetourZ = 0.0f;
bool sLastDetourValid = false;
std::vector<std::pair<float, float>> sDetourHist;
long long sTicks = 0;
std::chrono::steady_clock::time_point sFpsStart = std::chrono::steady_clock::now();
bool sFpsLogged = false;
int sPowerRestocks = 0; // #897 power resupply restocks spent this process
bool sPowerRestockVisit = false; // #897 one restock per Onion visit
int sTextTick = 0; // #897 tutorial-text A tap clock
bool sTextOpen = false; // #897 tutorial text window seen open (edge log)
bool sPowerLogged = false; // bot-v4: AUTOPLAY_POWER is logged exactly once per process
bool sPowerStocked = false; // bot-v4b: power-mode Onion stock runs once per process
float sPowerSeconds = 0.0f; // bot-v6: game-time seconds since the first live power tick

// BFS over the raw waypoint link graph (bot-v2 gap 2 fallback): the engine
// findSync below is the primary real graph search (A* over the same graph);
// when it yields no legs, this BFS over mLinkIndices still produces a real
// waypoint-by-waypoint route instead of a blind sidestep.
bool bfsPath(int selfIdx, int tgtIdx, std::vector<std::pair<float, float>>& out)
{
    out.clear();
    if (!routeMgr || selfIdx < 0 || tgtIdx < 0 || selfIdx == tgtIdx) return false;
    const u32 handle = 'test';
    const int n = routeMgr->getNumWayPoints(handle);
    if (n <= 0 || selfIdx >= n || tgtIdx >= n || n > 4096) return false;
    std::vector<int> parent(n, -1);
    std::queue<int> q;
    q.push(selfIdx);
    parent[selfIdx] = selfIdx;
    bool found = false;
    while (!q.empty()) {
        const int cur = q.front();
        q.pop();
        if (cur == tgtIdx) {
            found = true;
            break;
        }
        WayPoint* wp = routeMgr->getWayPoint(handle, cur);
        if (!wp) continue;
        const int links = wp->mLinkCount > 8 ? 8 : wp->mLinkCount;
        for (int k = 0; k < links; ++k) {
            const int nx = wp->mLinkIndices[k];
            if (nx < 0 || nx >= n || parent[nx] != -1) continue;
            parent[nx] = cur;
            q.push(nx);
        }
    }
    if (!found) return false;
    std::vector<int> rev;
    for (int cur = tgtIdx; cur != selfIdx; cur = parent[cur]) {
        rev.push_back(cur);
        if (int(rev.size()) > 64) break;
        if (parent[cur] < 0) return false;
    }
    for (int i = int(rev.size()) - 1; i >= 0 && out.size() < 64; --i) {
        WayPoint* wp = routeMgr->getWayPoint(handle, rev[i]);
        if (!wp) continue;
        out.emplace_back(wp->mPosition.x, wp->mPosition.z);
    }
    return !out.empty();
}

// bot-v3: k nearest open land waypoints to (x,z), closest first.
// #246/#899: a waypoint under a P1 HinderRock (the Impact Site box comes to
// rest on wp (-347,-30,709)) is inside the box, never a reachable leg.
bool underHinderRock(float x, float z)
{
    if (!workObjectMgr) return false;
    Iterator it(workObjectMgr);
    CI_LOOP(it)
    {
        WorkObject* obj = static_cast<WorkObject*>(*it);
        if (!obj || !obj->isHinderRock()) continue;
        const float r = static_cast<HinderRock*>(obj)->getCentreSize() * 0.5f;
        if (distXZ(x, z, obj->getPosition().x, obj->getPosition().z) < (r > 40.0f ? r : 40.0f)) return true;
    }
    return false;
}

// Height of the route waypoint a path leg was built from (legs keep only
// x/z), or NAN for a synthetic leg (sidestep, box push).
float waypointYAt(float x, float z)
{
    if (!routeMgr) return NAN;
    const int n = routeMgr->getNumWayPoints('test');
    for (int i = 0; i < n && n <= 4096; ++i) {
        WayPoint* wp = routeMgr->getWayPoint('test', i);
        if (wp && std::fabs(wp->mPosition.x - x) < 0.5f && std::fabs(wp->mPosition.z - z) < 0.5f) return wp->mPosition.y;
    }
    return NAN;
}

// #246/#899: a leg counts as reached within 80 units, except around a level
// change: when the leg's waypoint is off the captain's level, or the next leg
// climbs/descends from it, it must be reached within 30. Otherwise the
// captain cuts the corner under a ledge and presses into its wall (Impact
// Site pit: wp (-177,-30,714) -> ramp top (-281,18,719) -> (-420,20,718)).
float legReachRadiusLevel(size_t idx, float naviY)
{
    std::vector<std::pair<float, float>>& path = sPath;
    if (idx >= path.size()) return 80.0f;
    const float y = waypointYAt(path[idx].first, path[idx].second);
    if (!std::isfinite(y)) return 80.0f;
    if (std::isfinite(naviY) && std::fabs(y - naviY) > 20.0f) return 30.0f;
    if (idx + 1 < path.size()) {
        const float ny = waypointYAt(path[idx + 1].first, path[idx + 1].second);
        if (std::isfinite(ny) && std::fabs(ny - y) > 20.0f) return 30.0f;
    }
    return 80.0f;
}

// #897: height of the plan start / goal for nearestWpIdx (NAN = XZ only).
float sPlanStartY = NAN;
float sPlanGoalY = NAN;

// bot-v3: k nearest open land waypoints to (x,z), closest first. #897: with
// a finite y the score adds (3*dy)^2, so a waypoint on the ledge above (the
// Impact Site upper tier, y=20, 90 u from a captain at y=-30) never beats
// the reachable one on his own tier (ar3/ar4: 6 STUCK under the ledge).
std::vector<int> nearestWpIdx(float x, float z, int k, float y = NAN)
{
    std::vector<int> out;
    if (!routeMgr) return out;
    const u32 handle = 'test';
    const int n = routeMgr->getNumWayPoints(handle);
    if (n <= 0 || n > 4096) return out;
    Vector3f pos(x, 0.0f, z);
    struct Scored {
        float d;
        int idx;
    };
    std::vector<Scored> scored;
    scored.reserve(size_t(n));
    for (int i = 0; i < n; ++i) {
        WayPoint* wp = routeMgr->getWayPoint(handle, i);
        if (!wp || !wp->mIsOpen || wp->inWater()) continue;
        if (underHinderRock(wp->mPosition.x, wp->mPosition.z)) continue; // not a standable leg
        const float dx = wp->mPosition.x - pos.x, dz = wp->mPosition.z - pos.z;
        float score = dx * dx + dz * dz;
        if (std::isfinite(y)) {
            const float dy = 3.0f * (wp->mPosition.y - y);
            score += dy * dy;
        }
        scored.push_back({ score, i });
    }
    std::sort(scored.begin(), scored.end(), [](const Scored& a, const Scored& b) { return a.d < b.d; });
    for (int i = 0; i < int(scored.size()) && int(out.size()) < k; ++i) out.push_back(scored[i].idx);
    return out;
}

// #897: reach radius for a detour leg = the route waypoint's own radius
// (clamped 30..80) when the leg is a waypoint; 80 for sidesteps. The flat 80
// cut the Impact Site ramp corners (waypoints r=19..23) into the walls.
float legReachRadius(float x, float z)
{
    if (!routeMgr) return 80.0f;
    const u32 handle = 'test';
    const int n = routeMgr->getNumWayPoints(handle);
    for (int i = 0; i < n && i < 4096; ++i) {
        WayPoint* wp = routeMgr->getWayPoint(handle, i);
        if (!wp) continue;
        if (std::fabs(wp->mPosition.x - x) < 1.0f && std::fabs(wp->mPosition.z - z) < 1.0f) {
            float r = wp->mRadius;
            if (r < 30.0f) r = 30.0f;
            if (r > 80.0f) r = 80.0f;
            return r;
        }
    }
    return 80.0f;
}

// #901: route ends on the right floor first. A boss arena on a plateau (FoH
// part Snagret, y -17) sits above a basin (y -95) whose waypoints are nearer
// in XZ; a start or goal waypoint on the other level asks the captain to climb
// a cliff. Waypoints within kLevel of `y` come first (closest first), then the
// rest, so flat ground is unchanged.
std::vector<int> levelWpIdx(float x, float y, float z, int k)
{
    std::vector<int> near = nearestWpIdx(x, z, 64);
    if (!routeMgr || near.empty()) {
        if (int(near.size()) > k) near.resize(size_t(k));
        return near;
    }
    constexpr float kLevel = 40.0f;
    std::vector<int> level, other;
    for (int idx : near) {
        WayPoint* wp = routeMgr->getWayPoint('test', idx);
        if (wp && std::fabs(wp->mPosition.y - y) <= kLevel) level.push_back(idx);
        else other.push_back(idx);
    }
    std::vector<int> out;
    for (int idx : level) if (int(out.size()) < k) out.push_back(idx);
    for (int idx : other) if (int(out.size()) < k) out.push_back(idx);
    return out;
}

// Goal waypoints on the target's own ground level.
std::vector<int> goalWpIdx(float x, float z, int k)
{
    if (!mapMgr) return nearestWpIdx(x, z, k);
    return levelWpIdx(x, mapMgr->getMinY(x, z, true), z, k);
}

bool detourSeen(float x, float z)
{
    for (const auto& d : sDetourHist) {
        const float dx = d.first - x, dz = d.second - z;
        if (dx * dx + dz * dz < 1.0f) return true;
    }
    if (sLastDetourValid) {
        const float dx = sLastDetourX - x, dz = sLastDetourZ - z;
        if (dx * dx + dz * dz < 1.0f) return true;
    }
    return false;
}

void recordDetour(float x, float z)
{
    sLastDetourX = x;
    sLastDetourZ = z;
    sLastDetourValid = true;
    sDetourHist.emplace_back(x, z);
    if (sDetourHist.size() > 16) sDetourHist.erase(sDetourHist.begin());
}

// Engine findSync forward; on empty, the reversed search (goal->start,
// legs reversed) as the alternate for directed links. #901: `allowReverse`
// false keeps the forward search only (a reversed directed link can be a
// cliff drop walked upwards).
bool graphLegs(PathFinder* finder, int startIdx, int goalIdx,
               std::vector<std::pair<float, float>>& out, bool& reversed, bool allowReverse = true)
{
    out.clear();
    reversed = false;
    if (!finder || startIdx < 0 || goalIdx < 0 || startIdx == goalIdx) return false;
    WayPoint* legs[64] = {};
    const int n = finder->findSync(legs, 64, startIdx, goalIdx, false);
    for (int i = 0; i < n && int(out.size()) < 64; ++i) {
        if (!legs[i]) continue;
        out.emplace_back(legs[i]->mPosition.x, legs[i]->mPosition.z);
    }
    if (!out.empty()) return true;
    if (!allowReverse) return false;
    WayPoint* rlegs[64] = {};
    const int rn = finder->findSync(rlegs, 64, goalIdx, startIdx, false);
    std::vector<std::pair<float, float>> rev;
    for (int i = 0; i < rn && int(rev.size()) < 64; ++i) {
        if (!rlegs[i]) continue;
        rev.emplace_back(rlegs[i]->mPosition.x, rlegs[i]->mPosition.z);
    }
    if (rev.empty()) return false;
    for (int i = int(rev.size()) - 1; i >= 0; --i) out.push_back(rev[size_t(i)]);
    reversed = true;
    return !out.empty();
}

// #246/#899: an unfinished P1 HinderRock (pushable box, e.g. the Impact
// Site box in front of the Goolix arena) closes the route to a target. A
// player walks the squad into it and the formation Pikmin push it through
// the normal collision path (piki.cpp PushstoneMode). The bot does the same:
// on a STUCK approach with an unfinished box nearby it walks to the box's
// push side (opposite its destination) and then into the box, holding there
// while it moves, for at most kHinderBudget seconds per process. Only pad
// input is published; the box, its pushers and its route are untouched.
float sNaviY = NAN; // live captain height for level-aware start waypoints
HinderRock* sHinder = nullptr;
bool sHinderLeg = false;
float sHinderTime = 0.0f;
constexpr float kHinderBudget = 120.0f;

// TEST-ONLY day cycle (#246): a new scene (next day) invalidates every
// per-stage pointer and plan. Completed tokens (receipts) are kept.
void resetStageState()
{
    sBrain.reset();
    sEngage = Engagement{};
    sPath.clear();
    sPathIdx = 0;
    sLegTime = 0.0f;
    sReplanCount = 0;
    sReplanToken = 0;
    sLastDetourValid = false;
    sDetourHist.clear();
    sHinder = nullptr;
    sHinderLeg = false;
    sHinderTime = 0.0f;
    sPowerStocked = false;
    sPowerSeconds = 0.0f;
    std::printf("AUTOPLAY_STAGE_RESET completed=%zu bot-driven\n", sCompleted.size());
    std::fflush(stdout);
}

HinderRock* nearestOpenHinderRock(float x, float z, float maxDist)
{
    if (!workObjectMgr) return nullptr;
    HinderRock* best = nullptr;
    float bestDist = maxDist;
    Iterator it(workObjectMgr);
    CI_LOOP(it)
    {
        WorkObject* obj = static_cast<WorkObject*>(*it);
        if (!obj || !obj->isHinderRock() || obj->isFinished()) continue;
        const float d = distXZ(x, z, obj->getPosition().x, obj->getPosition().z);
        if (d < bestDist) {
            bestDist = d;
            best = static_cast<HinderRock*>(obj);
        }
    }
    return best;
}

bool planHinderRock(float naviX, float naviZ)
{
    if (sHinderTime >= kHinderBudget) return false;
    HinderRock* box = nearestOpenHinderRock(naviX, naviZ, 500.0f);
    if (!box) return false;
    const Vector3f pos = box->getPosition();
    float ax = box->mDestinationPosition.x - pos.x, az = box->mDestinationPosition.z - pos.z;
    float len = std::sqrt(ax * ax + az * az);
    if (len < 1.0f) {
        ax = pos.x - naviX;
        az = pos.z - naviZ;
        len = std::sqrt(ax * ax + az * az);
        if (len < 1.0f) return false;
    }
    ax /= len;
    az /= len;
    const float size = box->getCentreSize();
    sPath.clear();
    sPathIdx = 0;
    sLegTime = 0.0f;
    sPath.emplace_back(pos.x - ax * (size + 90.0f), pos.z - az * (size + 90.0f)); // push side
    sPath.emplace_back(pos.x, pos.z);                                             // into the box
    sHinder = box;
    sHinderLeg = true;
    std::printf("AUTOPLAY_HINDER_PUSH token=%u box=(%.0f,%.0f) dest=(%.0f,%.0f) size=%.0f need=%d navi=(%.0f,%.0f) "
                "stand=(%.0f,%.0f) bot-driven\n",
                sEngage.token, double(pos.x), double(pos.z), double(box->mDestinationPosition.x),
                double(box->mDestinationPosition.z), double(size), box->mAmountPushersToStart, double(naviX),
                double(naviZ), double(sPath[0].first), double(sPath[0].second));
    std::fflush(stdout);
    return true;
}

void planDetour(float naviX, float naviY, float naviZ, float tgtX, float tgtZ)
{
    // Per-engagement replan sequencing (token change resets the history so
    // alternates vary within one stuck approach, not across targets).
    if (sReplanToken != sEngage.token) {
        sReplanToken = sEngage.token;
        sReplanCount = 0;
        sDetourHist.clear();
        sLastDetourValid = false;
    }
    ++sReplanCount;
    sPath.clear();
    sPathIdx = 0;
    sLegTime = 0.0f;
    const char* method = "none";
    const char* failReason = nullptr;
    // Real path planning over the routeMgr waypoint graph (bot-v3: approach
    // must use method=graph): next-nearest start/goal alternates, reversed
    // legs for directed links, BFS fallback per pair. First non-duplicate
    // route wins so an identical detour is never repeated.
    if (!routeMgr) {
        failReason = "no_routemgr";
    } else {
        const std::vector<int> starts = levelWpIdx(naviX, naviY, naviZ, 3);
        // #897: a live actor height (sPlanGoalY) picks the goal's floor; else
        // the map height under the target (#901).
        const std::vector<int> goals = std::isfinite(sPlanGoalY) ? levelWpIdx(tgtX, sPlanGoalY, tgtZ, 3)
                                                                  : goalWpIdx(tgtX, tgtZ, 3);
        PathFinder* finder = routeMgr->getPathFinder('test');
        if (starts.empty()) failReason = "no_start_wp";
        else if (goals.empty()) failReason = "no_goal_wp";
        else if (!finder) failReason = "no_finder";
        else {
            bool anyPath = false;
            const u32 handle = 'test';
            // #901: a forward route (graph, then BFS over outgoing links) for
            // any start/goal pair wins over a reversed one.
            for (int si : starts) {
                for (int gi : goals) {
                    if (si == gi) continue;
                    std::vector<std::pair<float, float>> legs;
                    bool reversed = false;
                    if (!graphLegs(finder, si, gi, legs, reversed, false)
                        && !bfsPath(si, gi, legs)) continue;
                    anyPath = true;
                    if (!legs.empty() && detourSeen(legs[0].first, legs[0].second)) continue;
                    sPath = legs;
                    method = "forward";
                    break;
                }
                if (!sPath.empty()) break;
            }
            for (int si : sPath.empty() ? starts : std::vector<int>{}) {
                for (int gi : goals) {
                    if (si == gi) continue;
                    std::vector<std::pair<float, float>> legs;
                    bool reversed = false;
                    if (!graphLegs(finder, si, gi, legs, reversed)) continue;
                    anyPath = true;
                    if (!legs.empty() && detourSeen(legs[0].first, legs[0].second)) continue; // alternate
                    sPath = legs;
                    method = reversed ? "graph-rev" : "graph";
                    break;
                }
                if (!sPath.empty()) break;
            }
            // BFS fallback per pair (same alternates discipline).
            if (sPath.empty()) {
                for (int si : starts) {
                    for (int gi : goals) {
                        std::vector<std::pair<float, float>> legs;
                        if (!bfsPath(si, gi, legs)) continue;
                        anyPath = true;
                        if (!legs.empty() && detourSeen(legs[0].first, legs[0].second)) continue;
                        sPath = legs;
                        method = "bfs";
                        break;
                    }
                    if (!sPath.empty()) break;
                }
            }
            if (sPath.empty()) {
                failReason = anyPath ? "all_routes_duplicate" : "no_path";
                // Single-leg graph-nearest fallback only when it is fresh.
                WayPoint* gwp = routeMgr->getWayPoint(handle, goals[0]);
                if (gwp && !detourSeen(gwp->mPosition.x, gwp->mPosition.z)
                    && sReplanCount <= 2) {
                    sPath.emplace_back(gwp->mPosition.x, gwp->mPosition.z);
                    method = "graph-nearest";
                    failReason = nullptr;
                }
            }
            // Reverse the accepted multi-leg route on alternate replans when
            // the head leg keeps duplicating (directed-link alternates).
            if (sPath.size() > 1 && sReplanCount % 3 == 0 && std::strcmp(method, "forward") != 0) {
                std::vector<std::pair<float, float>> rev(sPath.rbegin(), sPath.rend());
                if (!rev.empty() && !detourSeen(rev[0].first, rev[0].second)) {
                    sPath = rev;
                    method = "graph-rev-alt";
                }
            }
        }
    }
    if (failReason) {
        std::printf("AUTOPLAY_ROUTE_FAIL reason=%s token=%u replan=%d bot-driven\n",
                    failReason, sEngage.token, sReplanCount);
        std::fflush(stdout);
    }
    if (sPath.empty()) {
        // Graph cannot route: perpendicular sidestep that is guaranteed
        // fresh (growing lateral + forward mix per replan; flip when the
        // computed point still duplicates history).
        const float dx = tgtX - naviX, dz = tgtZ - naviZ;
        const float len = std::sqrt(dx * dx + dz * dz);
        if (len > 1.0f) {
            float side = (sReplanCount % 2 == 1) ? 1.0f : -1.0f;
            const int step = (sReplanCount - 1) % 6;
            const float fwd = 0.35f + 0.05f * float(step % 5);
            const float lat = 220.0f + 60.0f * float(step);
            float px = naviX + dx * fwd - dz / len * lat * side;
            float pz = naviZ + dz * fwd + dx / len * lat * side;
            if (detourSeen(px, pz)) {
                side = -side;
                px = naviX + dx * fwd - dz / len * (lat + 80.0f) * side;
                pz = naviZ + dz * fwd + dx / len * (lat + 80.0f) * side;
            }
            sPath.emplace_back(px, pz);
            method = "sidestep";
        }
    }
    if (!sPath.empty()) {
        recordDetour(sPath[0].first, sPath[0].second);
        std::printf("AUTOPLAY_REPLAN token=%u detour=(%.0f,%.0f) legs=%d method=%s replan=%d bot-driven\n",
                    sEngage.token, sPath[0].first, sPath[0].second,
                    int(sPath.size()), method, sReplanCount);
        std::fflush(stdout);
    }
}

} // namespace

void pc_p2_autoplay_tick(void)
{
    if (!p2autoplay::isEnabled()) {
        return; // inert when unset: production input path untouched
    }
    // #901 TEST-ONLY (PIKMIN_RANDOMIZER_AUTOPLAY_NEXT_DAY=1): once a stage has run,
    // tap A whenever there is no live captain (day-end movie, result and save
    // screens) so a run reaches the next day. Never before the first captain,
    // so boot menus are untouched.
    static bool sSawCaptain = false;
    static long sNoCaptainTicks = 0;
    {
        Navi* live = naviMgr ? naviMgr->getNavi() : nullptr;
        if (live && live->isAlive()) {
            sSawCaptain = true;
            sNoCaptainTicks = 0;
        } else if (sSawCaptain && p2autoplay::nextDayTap()) {
            ++sNoCaptainTicks;
            pc_p2_input_script_set(1, (sNoCaptainTicks % 40 < 6) ? unsigned(p2autoplay::PadA) : 0u, 0, 0);
            return;
        }
    }
    // TEST-ONLY day cycle (#246): between the forced sunset and the next
    // stage only tap A (results, save); a new scene resets per-stage state.
    if (pc_p2_test_day_cycle_active()) {
        static unsigned long sScene = 0;
        static bool sSceneValid = false;
        static int sAdvanceFrames = 0;
        const unsigned long scene = pc_p2_scene_generation();
        if (sSceneValid && scene != sScene) resetStageState();
        sScene = scene;
        sSceneValid = true;
        if (pc_p2_test_day_cycle_advancing()) {
            pc_p2_input_script_set(1, ((sAdvanceFrames++ / 6) & 1) ? unsigned(p2autoplay::PadA) : 0u, 0, 0);
            return;
        }
        sAdvanceFrames = 0;
    }
    if (!naviMgr || !pikiMgr || !tekiMgr || !itemMgr) {
        return; // boot/menus: no game state yet, emit nothing
    }
    Navi* navi = naviMgr->getNavi();
    if (!navi || !navi->isAlive()) {
        sBrain.update(0.016f, p2autoplay::Senses{});
        pc_p2_input_script_set(1, 0, 0, 0);
        return;
    }

    // #897: a tutorial / part-discovery text window (createTutorialWindow,
    // gameflow.mIsTutorialTextActive) freezes the field until A or B is
    // clicked (ogScrMessageMgr keyClick). The Brain must not count that
    // time as a stuck approach (a2-impact: tu_tx window at the Goolix
    // approach -> 6 STUCK -> target_unreachable). Tap A (4 ticks down, 8 up:
    // keyClick needs the edge) and hold the Brain until it closes. Normal
    // pad input only.
    if (gameflow.mIsTutorialTextActive) {
        if (!sTextOpen) {
            sTextOpen = true;
            std::printf("AUTOPLAY_TEXT_DISMISS open=1 navi=(%.0f,%.0f) bot-driven\n",
                        navi->getPosition().x, navi->getPosition().z);
            std::fflush(stdout);
        }
        const bool down = (sTextTick++ % 12) < 4;
        pc_p2_input_script_set(1, down ? unsigned(p2autoplay::PadA) : 0u, 0, 0);
        return;
    }
    if (sTextOpen) {
        sTextOpen = false;
        sTextTick = 0;
        std::printf("AUTOPLAY_TEXT_DISMISS open=0 bot-driven\n");
        std::fflush(stdout);
    }

    const float dt = gsys ? gsys->getFrameTime() : 0.016f;
    const float naviX = navi->getPosition().x;
    const float naviY = navi->getPosition().y;
    const float naviZ = navi->getPosition().z;
    sNaviY = navi->getPosition().y;

    // --- Pikmin census (read-only, except bot-v4 power-mode flowering) ---
    int panicCount = 0; // #245: Pikmin in PIKISTATE_Panic, nearest XZ to the captain
    float panicNearest = 1.0e30f;
    int alive = 0, nearCount = 0, farCount = 0, transport = 0, distress = 0, squad = 0;
    int strays = 0;
    float strayX = 0.0f, strayZ = 0.0f;
    float strayNearX = 0.0f, strayNearZ = 0.0f, strayNearDist = 1.0e30f; // #256 nearest lost Pikmin
    int lostCount = 0;
    int partyCount = 0; // #901: FormationMode Pikmin following this captain
    int workCount = 0; // #901: Pikmin working a gate / bridge / hinder rock
    std::vector<std::pair<float, float>> transportPos;
    std::vector<std::pair<float, float>> freePos; // #901: idle FreeMode Pikmin
    const bool powerMode = p2autoplay::isPowerEnabled();
    const bool purplePower = p2autoplay::isPurplePower() && pc_p2_purples_enabled();
    int purpleConverted = 0;
    {
        Iterator it(pikiMgr);
        CI_LOOP(it)
        {
            Piki* p = static_cast<Piki*>(*it);
            if (!p || !p->isAlive()) continue;
            ++alive;
            const float d = distXZ(naviX, naviZ, p->getPosition().x, p->getPosition().z);
            if (d < 350.0f) ++nearCount;
            if (d > 550.0f) ++farCount;
            if (p->mMode == PikiMode::FormationMode) ++squad;
            // #246: idle strays (not following, not carrying) within 600 u.
            if (p->mMode == PikiMode::FreeMode && d < 600.0f) {
                ++strays;
                strayX += p->getPosition().x;
                strayZ += p->getPosition().z;
            }
            // #256 lost Pikmin: idle or Formation, left 350-1000 u behind.
            if ((p->mMode == PikiMode::FreeMode || p->mMode == PikiMode::FormationMode) && d > 350.0f && d < 1000.0f) {
                ++lostCount;
                if (d < strayNearDist) {
                    strayNearDist = d;
                    strayNearX = p->getPosition().x;
                    strayNearZ = p->getPosition().z;
                }
            }
            if (p->mMode == PikiMode::TransportMode) {
                ++transport;
                transportPos.emplace_back(p->getPosition().x, p->getPosition().z);
            }
            if (p->mMode == PikiMode::FormationMode && p->mNavi == navi) ++partyCount;
            if (p->mMode == PikiMode::BreakwallMode || p->mMode == PikiMode::BridgeMode
                || p->mMode == PikiMode::PushstoneMode || p->mMode == PikiMode::RopeMode)
                ++workCount;
            // #901: recruitable = not following, not carrying, not on its way
            // out (idle, fighting, working): a whistle calls these back.
            if (p->mMode != PikiMode::FormationMode && p->mMode != PikiMode::TransportMode
                && p->getState() != PIKISTATE_Bury && p->getState() != PIKISTATE_Dying && p->getState() != PIKISTATE_Dead
                && p->getState() != PIKISTATE_Swallowed && p->getState() != PIKISTATE_NukareWait)
                freePos.emplace_back(p->getPosition().x, p->getPosition().z);
            // bot-v4 power mode: flowers through the normal maturity path
            // (virtual ViewPiki::setFlower, the same call the nectar GrowUp,
            // Onion exit, and pluck paths use). No direct mHappa pokes.
            if (powerMode && p->mHappa != Flower) p->setFlower(Flower);
            // #958 power mode + PIKMIN_RANDOMIZER_AUTOPLAY_PURPLE: Purple squad
            // (only the Giant Breadbug press needs it; TEST-ONLY).
            if (purplePower && !pc_p2_is_purple(p)) {
                pc_p2_make_purple(p);
                ++purpleConverted;
            }
            // bot-v4 regroup sense: grabbed (mouth-stuck / swallowed),
            // thrown off (flick/flown/fall/wave/pressed), burning/panicking.
            const int pst = p->getState();
            if (pst == PIKISTATE_Fired || pst == PIKISTATE_Flick || pst == PIKISTATE_Flown
                || pst == PIKISTATE_FallMeck || pst == PIKISTATE_Wave || pst == PIKISTATE_Pressed
                || pst == PIKISTATE_Swallowed || pst == PIKISTATE_Panic || pst == PIKISTATE_Drown
                || pst == PIKISTATE_Bubble || p->isFired() || p->isStickToMouth())
                ++distress;
            if (pst == PIKISTATE_Panic) {
                ++panicCount;
                panicNearest = std::min(panicNearest, d);
            }
        }
    }
    if (purpleConverted > 0) {
        // Throttled: the whole squad converts one Pikmin per tick as it exits.
        static int sPurpleTotal = 0;
        const int before = sPurpleTotal;
        sPurpleTotal += purpleConverted;
        if (before == 0 || sPurpleTotal / 25 != before / 25)
            std::printf("AUTOPLAY_POWER_PURPLE converted_total=%d field=%d bot-driven\n", sPurpleTotal, alive);
    }
    if (powerMode) sPowerSeconds += (dt > 0.0f && dt <= 0.5f) ? dt : 0.016f;
    if (powerMode && !sPowerLogged && alive >= 80) {
        // bot-v6: the one-step squad is in the field (queued through the
        // normal Onion exit path at start, no menu cycles). Log its real size
        // with the game-time seconds it took, whatever state we are in
        // (normally still WithdrawSeek) - this is the field>=80 evidence.
        sPowerLogged = true;
        std::printf("AUTOPLAY_POWER squad=%d seconds=%.0f maturity=flower damage_mult=%g bot-driven\n",
                    alive, double(sPowerSeconds), double(p2autoplay::powerDamageMult()));
        std::fflush(stdout);
    }

    // bot-v4b power-mode Onion stock (TEST-ONLY, gated by BOTH the autoplay
    // gate and PIKMIN_RANDOMIZER_AUTOPLAY_POWER via isPowerEnabled(): inert
    // when either is unset). The day-start Onion only holds the 20 starting
    // Pikmin (gameSetup sets 20), so top the start-colour Onion up to ~100
    // once per process through the normal born/stored bookkeeping: pikiInfMgr (stock carried
    // between days) + the Onion's mHeldPikis (what the withdrawal screen
    // counts) + GameStat::containerPikis/allPikis (HUD + birth caps) +
    // playerState born/living/plucked counters. Stocked as Leaf (the normal
    // birth stage); the power-mode census above flowers the field squad
    // through the normal setFlower path after withdrawal.
    // bot-v6: then put the whole Onion in the field in ONE step through the
    // normal day-start exit path (GoalItem::exitPikis, the same call
    // gameCoreSection uses for the starting squad). The withdraw menu only
    // accumulates ~5-6 Pikmin of UI-local delta per cycle (bc4: 9-10 cycles to
    // reach 100), eating the run; the exit queue births ~100 in ~5 s of game
    // time with no menu input. The Brain waits it out in WithdrawSeek (power
    // path: neutral pad, no A) until field>=80.
    if (powerMode && !sPowerStocked && playerState) {
        int stockColor = pc_randomizer_enabled() ? pc_randomizer_start_color() : Red;
        if (stockColor < PikiMinColor || stockColor > PikiMaxColor) stockColor = Red;
        GoalItem* stockOnion = itemMgr ? itemMgr->getContainer(stockColor) : nullptr;
        if (!stockOnion && itemMgr) {
            for (int color = PikiMinColor; color <= PikiMaxColor; ++color) {
                stockOnion = itemMgr->getContainer(color);
                if (stockOnion) {
                    stockColor = color;
                    break;
                }
            }
        }
        if (stockOnion) {
            const int stored = stockOnion->getTotalStorePikis();
            const int already = int(GameStat::allPikis);
            const int limit = pc_settings_get_piki_limit();
            const int delta = p2autoplay::powerStockDelta(true, stored, alive, already, limit);
            if (delta > 0) {
                pikiInfMgr.mPikiCounts[stockColor][Leaf] += delta;
                stockOnion->mHeldPikis[Leaf] += (u32)delta;
                GameStat::containerPikis.add(stockColor, delta);
                playerState->mTotalBornPikiNum += delta;
                playerState->mLivingPikiNum += delta;
                playerState->mTotalPluckedPikiCount += delta;
                GameStat::update();
                std::printf("AUTOPLAY_POWER_STOCK color=%d added=%d stored=%d field=%d bot-driven\n",
                            stockColor, delta, stored + delta, alive);
                std::fflush(stdout);
            }
            // bot-v6 one-step squad: queue the whole stocked Onion to the field
            // through the normal exit path (clamped by field capacity, 100 in
            // power mode). Dispenses via exitPiki births over the next seconds;
            // the Brain's power WithdrawSeek waits for field>=80 meanwhile.
            {
                const int total = stockOnion->getTotalStorePikis();
                if (total > 0) stockOnion->exitPikis(total);
            }
            sPowerStocked = true;
        }
    }

    // #901 TEST-ONLY arena teleport (PIKMIN_RANDOMIZER_AUTOPLAY_TELEPORT="x,z",
    // autoplay-gated): once the squad is out, move the captain and every
    // Pikmin that is not carrying or leaving to the point, so the bot can
    // fight an arena it cannot route to. Never runs in normal play.
    {
        static bool teleported = false;
        static int settleTicks = 0;
        float tx = 0.0f, tz = 0.0f;
        // Wait for the whole Onion queue (up to ~15 s after the squad first reaches
        // the threshold) so the last births are not left at the Onion.
        const int need = powerMode ? 80 : 20;
        if (!teleported && alive >= need) ++settleTicks;
        if (!teleported && mapMgr && alive >= need && (alive >= 98 || settleTicks > 450)
            && p2autoplay::teleportTarget(tx, tz)) {
            teleported = true;
            const float ty = mapMgr->getMinY(tx, tz, true);
            Vector3f at(tx, ty, tz);
            navi->resetPosition(at);
            int moved = 0;
            Iterator it(pikiMgr);
            CI_LOOP(it)
            {
                Piki* p = static_cast<Piki*>(*it);
                if (!p || !p->isAlive() || p->mMode == PikiMode::TransportMode) continue;
                const int st = p->getState();
                if (st == PIKISTATE_Bury || st == PIKISTATE_Dying || st == PIKISTATE_Dead) continue;
                const float ang = 0.61803f * 6.2831853f * float(moved);
                const float rad = 40.0f + 6.0f * float(moved % 12);
                Vector3f pp(tx + rad * std::cos(ang), ty, tz + rad * std::sin(ang));
                pp.y = mapMgr->getMinY(pp.x, pp.z, true);
                p->resetPosition(pp);
                ++moved;
            }
            std::printf("AUTOPLAY_TELEPORT x=%.1f y=%.1f z=%.1f moved=%d TEST-ONLY bot-driven\n", double(tx),
                        double(ty), double(tz), moved);
            std::fflush(stdout);
        }
    }

    // #897 power resupply (TEST-ONLY, power mode only): the Brain walked the
    // captain back to the Onion after a crush (wantsPowerRestock). Top the
    // start-colour Onion up again through the SAME bookkeeping as the one-time
    // power stock above and queue it out through the normal exit path, once
    // per visit, at most powerRestockMax times per process.
    if (!sBrain.wantsPowerRestock()) sPowerRestockVisit = false;
    if (powerMode && sPowerStocked && playerState && sBrain.wantsPowerRestock() && !sPowerRestockVisit
        && sPowerRestocks < p2autoplay::Config().powerRestockMax) {
        sPowerRestockVisit = true;
        int stockColor = pc_randomizer_enabled() ? pc_randomizer_start_color() : Red;
        if (stockColor < PikiMinColor || stockColor > PikiMaxColor) stockColor = Red;
        GoalItem* stockOnion = itemMgr ? itemMgr->getContainer(stockColor) : nullptr;
        if (stockOnion) {
            const int stored = stockOnion->getTotalStorePikis();
            const int delta = p2autoplay::powerStockDelta(true, stored, alive, int(GameStat::allPikis),
                                                          pc_settings_get_piki_limit());
            if (delta > 0) {
                pikiInfMgr.mPikiCounts[stockColor][Leaf] += delta;
                stockOnion->mHeldPikis[Leaf] += (u32)delta;
                GameStat::containerPikis.add(stockColor, delta);
                playerState->mTotalBornPikiNum += delta;
                playerState->mLivingPikiNum += delta;
                playerState->mTotalPluckedPikiCount += delta;
                GameStat::update();
            }
            const int total = stockOnion->getTotalStorePikis();
            if (total > 0) stockOnion->exitPikis(total);
            ++sPowerRestocks;
            std::printf("AUTOPLAY_POWER_RESTOCK n=%d color=%d added=%d exit=%d field=%d bot-driven\n",
                        sPowerRestocks, stockColor, delta > 0 ? delta : 0, total, alive);
            std::fflush(stdout);
        }
    }

    // #897 one-time map dump (read-only diagnostics): route waypoints with
    // links/open/water flags and every HinderRock/Bridge work object, so a
    // STUCK can be read against the real graph and obstacles.
    static bool sMapDumped = false;
    static int sHinderFinished = -1; // #897 finished-count at the last work dump
    if (sMapDumped && workObjectMgr) {
        int finished = 0;
        Iterator fit(workObjectMgr);
        CI_LOOP(fit)
        {
            WorkObject* w = static_cast<WorkObject*>(*fit);
            if (w && w->isHinderRock() && w->isFinished()) ++finished;
        }
        if (finished != sHinderFinished) {
            sHinderFinished = finished;
            Iterator wit(workObjectMgr);
            CI_LOOP(wit)
            {
                WorkObject* w = static_cast<WorkObject*>(*wit);
                if (!w || !w->isHinderRock()) continue;
                std::printf("AUTOPLAY_MAP_WORK kind=hinder x=%.0f y=%.0f z=%.0f finished=%d navi=(%.0f,%.0f,%.0f) bot-driven\n",
                            w->getPosition().x, w->getPosition().y, w->getPosition().z, w->isFinished() ? 1 : 0,
                            navi->getPosition().x, navi->getPosition().y, navi->getPosition().z);
            }
            std::fflush(stdout);
        }
    }
    if (!sMapDumped && routeMgr && workObjectMgr) {
        sMapDumped = true;
        const u32 handle = 'test';
        const int n = routeMgr->getNumWayPoints(handle);
        for (int i = 0; i < n && i < 4096; ++i) {
            WayPoint* wp = routeMgr->getWayPoint(handle, i);
            if (!wp) continue;
            char links[96] = {0};
            int off = 0;
            for (int k = 0; k < wp->mLinkCount && k < 8 && off < 88; ++k)
                off += std::snprintf(links + off, sizeof(links) - size_t(off), "%s%d", k ? "," : "", wp->mLinkIndices[k]);
            std::printf("AUTOPLAY_MAP_WP idx=%d x=%.0f y=%.0f z=%.0f r=%.0f open=%d water=%d links=%s bot-driven\n",
                        i, wp->mPosition.x, wp->mPosition.y, wp->mPosition.z, wp->mRadius, wp->mIsOpen ? 1 : 0,
                        wp->inWater() ? 1 : 0, links);
        }
        Iterator wit(workObjectMgr);
        CI_LOOP(wit)
        {
            WorkObject* w = static_cast<WorkObject*>(*wit);
            if (!w) continue;
            std::printf("AUTOPLAY_MAP_WORK kind=%s x=%.0f y=%.0f z=%.0f finished=%d bot-driven\n",
                        w->isHinderRock() ? "hinder" : (w->isBridge() ? "bridge" : "other"),
                        w->getPosition().x, w->getPosition().y, w->getPosition().z, w->isFinished() ? 1 : 0);
        }
        std::fflush(stdout);
    }

    // --- Nearest stocked Onion (read-only) ---
    bool hasOnion = false;
    float onionX = 0.0f, onionZ = 0.0f, onionDist = 1.0e30f;
    int onionStored = 0;
    for (int color = 0; color < 3; ++color) {
        GoalItem* onion = itemMgr->getContainer(color);
        if (!onion) continue;
        const float d = distXZ(naviX, naviZ, onion->getPosition().x, onion->getPosition().z);
        const int stored = onion->getTotalStorePikis();
        if (!hasOnion || (stored > 0 && onionStored <= 0) || (stored > 0 && d < onionDist)
            || (stored == 0 && onionStored == 0 && d < onionDist)) {
            hasOnion = true;
            onionX = onion->getPosition().x;
            onionZ = onion->getPosition().z;
            onionDist = d;
            onionStored = stored;
        }
    }

    // --- P2-bound target scan (read-only) ---
    const std::string filter = p2autoplay::targetFilter();
    struct Candidate {
        unsigned token;
        unsigned source;
        float x, z, dist;
        BTeki* actor;
        float health;
    };
    std::vector<Candidate> candidates;
    {
        Iterator it(tekiMgr);
        CI_LOOP(it)
        {
            Teki* teki = static_cast<Teki*>(*it);
            if (!teki) continue;
            BTeki* actor = static_cast<BTeki*>(teki);
            if (!actor->mGenerator) continue;
            if (!actor->isAlive() || actor->mHealth <= 0.0f) continue;
            const unsigned token = botToken(actor);
            if (!token) continue;
            unsigned source = pc_randomizer_p2_source_for(actor);
            if (!source) source = pc_randomizer_p2_source_for_id(token);
            // #901 TEST-ONLY regression target: a vanilla P1 teki named by its
            // seed generator uid (PIKMIN_RANDOMIZER_AUTOPLAY_P1_UID), so the bot
            // can fight a P1 part holder. Pseudo source 0 is never a species.
            if (!source && p2autoplay::isP1TargetUid(pc_randomizer_generator_id(actor->mGenerator))) {
                source = p2autoplay::kP1TargetSource;
            }
            if (!source) continue; // not P2-bound
            if (sCompleted.count(token)) continue;
            const char* name = sourceDisplayName(source);
            if (!p2autoplay::matchTarget(token, source, name, filter)) continue;
            Candidate c;
            c.token = token;
            c.source = source;
            c.x = actor->getPosition().x;
            c.z = actor->getPosition().z;
            c.dist = distXZ(naviX, naviZ, c.x, c.z);
            c.actor = actor;
            // #246: a bound Titan's weapons take the hits first; sense body +
            // weapon HP so progress (and the damaged latch) is visible.
            c.health = pc_p2_bigtreasure_teki_effective_health(actor, actor->mHealth);
            candidates.push_back(c);
        }
    }
    // Keep the sticky engagement when it is still live; else nearest -- but
    // NEVER silently re-target mid-fight (bot-v2 fix for the wf10-v2-1
    // Otakara mis-score: the engaged Otakara died, the scan fell through to
    // a live Kogane, and the Kogane-confirm path then scored the stale
    // Otakara token as damaged=1 killed=0). While the Brain is in
    // Approach/Attack/Aftermath for a live engagement token, hold the
    // last-known dead report until the Brain emits RESULT (which clears the
    // engagement); only Select/Done/Withdraw may acquire a new target.
    const Candidate* pick = nullptr;
    if (sEngage.token) {
        for (const Candidate& c : candidates) {
            if (c.token == sEngage.token) {
                pick = &c;
                break;
            }
        }
    }
    if (!pick && !candidates.empty()) {
        const p2autoplay::State st = sBrain.current();
        const bool midFight = (st == p2autoplay::State::Approach || st == p2autoplay::State::Attack
                               || st == p2autoplay::State::Aftermath);
        if (!sEngage.token || !midFight) {
            pick = &*std::min_element(candidates.begin(), candidates.end(),
                                      [](const Candidate& a, const Candidate& b) { return a.dist < b.dist; });
        }
    }
    if (pick && pick->token != sEngage.token) {
        sEngage = Engagement{};
        sEngage.token = pick->token;
        sEngage.source = pick->source;
        sEngage.initialHealth = pick->health > 0.0f ? pick->health : 1.0f;
        if (p2autoplay::isKoganeLike(pick->source)) sEngage.initialNectar = pc_p2_kogane_nectar_dropped(pick->token);
        sPath.clear();
        sPathIdx = 0;
        sLegTime = 0.0f;
        sReplanCount = 0;
        sReplanToken = pick->token;
        sDetourHist.clear();
        sLastDetourValid = false;
    }

    // --- Generic death scan (bot-v2 gap 5): the engaged actor by token among
    // ALL teki (including dead bodies the live-list filter skips). Any of
    // health<=0 / !isAlive / dead-state / corpse pellet formed latches death
    // for every species, not just per-module markers (Otakara wf9-4 fix). ---
    // bot-v5: the scan runs every tick (not just until the latch) so the dead
    // body position keeps updating while it exists; the death spot anchors
    // the corpse-motion sense, and the pellet scan below takes over once the
    // body is gone.
    bool deadSignal = sEngage.deadLatch;
    sEngage.bodyPresent = false;
    if (sEngage.token && tekiMgr) {
        Iterator dit(tekiMgr);
        CI_LOOP(dit)
        {
            Teki* t = static_cast<Teki*>(*dit);
            if (!t || !t->mGenerator) continue;
            BTeki* b = static_cast<BTeki*>(t);
            if (botToken(b) != sEngage.token) continue;
            sEngage.hostType = b->mTekiType; // bot-v7: corpse-config key while the body exists
            if (b->mHealth <= 0.0f || !b->isAlive() || b->mDeadState != 0 || b->mPellet != nullptr) {
                deadSignal = true;
                if (!sEngage.deadLatch) {
                    sEngage.deadLatch = true;
                    sEngage.deathX = b->getPosition().x;
                    sEngage.deathZ = b->getPosition().z;
                    sEngage.deathRecorded = true;
                    sEngage.trackX = sEngage.deathX;
                    sEngage.trackZ = sEngage.deathZ;
                    sEngage.stillTime = 0.0f;
                }
                sEngage.bodyPresent = true;
                sEngage.lastX = b->getPosition().x;
                sEngage.lastZ = b->getPosition().z;
            }
            break;
        }
    }

    // bot-v5 corpse-pellet scan: once the body is gone the corpse is a Pellet
    // (a DualCreature in pelletMgr, not tekiMgr). Follow the nearest live
    // pellet to the last corpse pos so tgtX/Z tracks the haul and the Brain
    // escorts it; read its mCarrierCounter (carrying strength, Pellet.h:412)
    // for the stalled-lift verdict.
    sEngage.pelletFound = false;
    sEngage.pelletCarriers = 0;
    Pellet* trackedPellet = nullptr; // bot-v7: live corpse pellet for carryWant
    if (sEngage.token && sEngage.deadLatch && pelletMgr) {
        // #901: while the dead host still lingers, only the ship part it
        // dropped beside it is tracked (the corpse pellet does not exist yet).
        const bool partsOnly = sEngage.bodyPresent;
        float best2 = (partsOnly ? 300.0f : 600.0f) * (partsOnly ? 300.0f : 600.0f);
        Pellet* best = nullptr;
        bool bestPart = false;
        Iterator pit(pelletMgr);
        CI_LOOP(pit)
        {
            Pellet* pel = static_cast<Pellet*>(*pit);
            if (!pel || !pel->isAlive()) continue;
            const float dx = pel->getPosition().x - sEngage.lastX;
            const float dz = pel->getPosition().z - sEngage.lastZ;
            const float d2 = dx * dx + dz * dz;
            // #901: a ship part the target dropped outranks its corpse, so the
            // bot escorts the part to the ship (the check under test).
            const bool part = pel->isUfoParts();
            // #901: until a part is adopted, only a part that appeared near the death
            // spot counts (a level's own parts elsewhere are not the held part).
            if (part && !sEngage.partConfig && sEngage.deathRecorded) {
                const float px = pel->getPosition().x - sEngage.deathX, pz = pel->getPosition().z - sEngage.deathZ;
                if (px * px + pz * pz > 250.0f * 250.0f) continue;
            }
            if (partsOnly && !part) continue;
            if (bestPart && !part) continue;
            if ((part && !bestPart && d2 < 600.0f * 600.0f) || d2 < best2) {
                best2 = d2;
                best = pel;
                bestPart = part;
            }
        }
        if (best) {
            sEngage.pelletFound = true;
            sEngage.pelletCarriers = best->mCarrierCounter;
            sEngage.lastX = best->getPosition().x;
            sEngage.lastZ = best->getPosition().z;
            trackedPellet = best;
            if (bestPart && sEngage.partConfig != best->mConfig) {
                // #901: log which ship part the aftermath escorts, and where.
                const u32 pid = best->mConfig->mModelId.mId;
                std::printf("AUTOPLAY_PART_TRACK part=%c%c%c%c x=%.0f y=%.0f z=%.0f carriers=%d token=%u bot-driven\n",
                            char(pid >> 24), char(pid >> 16), char(pid >> 8), char(pid), double(best->getPosition().x),
                            double(best->getPosition().y), double(best->getPosition().z), int(best->mCarrierCounter),
                            sEngage.token);
                std::fflush(stdout);
            }
            if (bestPart) sEngage.partConfig = best->mConfig;
        }
    }
    // #901: the latched part left the field (no live part pellet of that
    // config remains): it was sucked into the ship.
    bool partGone = false;
    if (sEngage.partConfig && pelletMgr) {
        partGone = true;
        Iterator git(pelletMgr);
        CI_LOOP(git)
        {
            Pellet* pel = static_cast<Pellet*>(*git);
            if (pel && pel->isAlive() && pel->mConfig == sEngage.partConfig) {
                partGone = false;
                break;
            }
        }
    }

    // bot-v7: resolve the tracked corpse's declared carry minimum
    // (PelletConfig p01, strength units, same scale as mCarrierCounter).
    // Prefer the live pellet's own config; while only the dead body exists,
    // resolve through the host teki type (TekiMgr::getTypeId, the same key
    // dieSoon/becomePellet uses for the corpse pellet). Latched once known
    // so the Brain keeps the shortfall visible across handoffs and gaps.
    if (sEngage.token && sEngage.deadLatch) {
        int want = 0;
        if (trackedPellet && trackedPellet->mConfig) {
            want = trackedPellet->mConfig->mCarryMinPikis();
        } else if (sEngage.bodyPresent && sEngage.hostType >= 0 && pelletMgr) {
            PelletConfig* hostConfig = pelletMgr->getConfig(TekiMgr::getTypeId(sEngage.hostType));
            if (hostConfig) want = hostConfig->mCarryMinPikis();
        }
        if (want > 0) sEngage.carryWant = want;
    }

    // bot-v5 carry attribution: TransportMode bodies near THIS corpse (600 u),
    // not any hauler on the map, so a bystander pellet's crew never latches
    // this engagement's carry.
    sEngage.carryNear = 0;
    if (sEngage.token && sEngage.deadLatch) {
        for (const auto& tp : transportPos) {
            if (distXZ(tp.first, tp.second, sEngage.lastX, sEngage.lastZ) <= 600.0f) ++sEngage.carryNear;
        }
    }
    const bool carryActive = sEngage.carryNear > 0 || sEngage.pelletCarriers > 0;
    // bot-v5 recent motion: displaced-ever (motion history for reasons) AND
    // displaced again within corpseStillWindow (moving NOW for the window).
    // A lift that moved then stopped reads moving=false, so the window stops
    // extending and the Brain's stall re-throw fires instead.
    bool corpseMoved = false, corpseMoving = false;
    if (sEngage.deathRecorded) {
        corpseMoved = p2autoplay::corpseDisplaced(sEngage.lastX - sEngage.deathX,
                                                  sEngage.lastZ - sEngage.deathZ);
        const float tx = sEngage.lastX - sEngage.trackX, tz = sEngage.lastZ - sEngage.trackZ;
        if (tx * tx + tz * tz > 4.0f) { // 2 u jitter margin per tick
            sEngage.trackX = sEngage.lastX;
            sEngage.trackZ = sEngage.lastZ;
            sEngage.stillTime = 0.0f;
        } else {
            sEngage.stillTime += dt > 0.0f && dt <= 0.5f ? dt : 0.016f;
        }
        corpseMoving = corpseMoved && sEngage.stillTime < p2autoplay::Config().corpseStillWindow;
    }

    // --- Senses ---
    p2autoplay::Senses senses;
    senses.enabled = true;
    senses.naviAlive = true;
    senses.dt = dt;
    senses.naviX = naviX;
    senses.naviZ = naviZ;
    senses.hasOnion = hasOnion;
    senses.onionX = onionX;
    senses.onionZ = onionZ;
    senses.fieldPikmin = alive;
    senses.squadPikmin = squad;
    senses.strayPikmin = strays;
    senses.lostPikmin = lostCount;
    senses.nearPikmin = nearCount;
    senses.strayNearX = strayNearX;
    senses.strayNearZ = strayNearZ;
    senses.strayNearDist = strayNearDist;
    senses.strayX = strays ? strayX / float(strays) : naviX;
    senses.strayZ = strays ? strayZ / float(strays) : naviZ;
    senses.onionStored = onionStored;
    senses.onionDist = onionDist;
    senses.containerOpen = navi->getCurrState() && navi->getCurrState()->getID() == NAVISTATE_Container;
    senses.scattered = (farCount >= 3) || (alive >= 10 && nearCount < 5);
    // #256 TEST-ONLY census marker: why the squad reads as scattered.
    if (senses.scattered) {
        static float diagClock = 0.0f;
        diagClock += (dt > 0.0f && dt <= 0.5f) ? dt : 0.016f;
        if (diagClock >= 10.0f) {
            diagClock = 0.0f;
            std::printf("AUTOPLAY_SCATTER alive=%d near350=%d far550=%d squad=%d party=%d strays=%d lost=%d stray_near=%.0f@(%.0f,%.0f) navi=(%.0f,%.0f) bot-driven\n",
                        alive, nearCount, farCount, squad, partyCount, strays, lostCount, double(strayNearDist), double(strayNearX),
                        double(strayNearZ), double(naviX), double(naviZ));
            std::fflush(stdout);
        }
    }
    senses.squadDistress = distress > 0;
    senses.panicCount = panicCount; // #245 Fuefuki owner-death Panic reclaim
    senses.panicNearest = panicNearest;
    // bot-v5: live per-corpse carry (was a forever latch on ANY transport).
    // receiptSeen stays the per-token ledger query (per-token bystander-proof).
    senses.transportSeen = carryActive;
    senses.carryCount = sEngage.carryNear;
    senses.pelletCarriers = sEngage.pelletCarriers;
    senses.carryWant = sEngage.carryWant; // bot-v7: declared minimum (0 = unknown)
    senses.trackingPart = trackedPellet && trackedPellet->isUfoParts();
    // #901 TEST-ONLY (PIKMIN_RANDOMIZER_AUTOPLAY_TELEPORT_TO_PART=1, autoplay-gated):
    // a dropped ship part whose crew stays short for 20 s (the part fell where the
    // squad cannot reach it on foot) gets the captain and the free Pikmin moved
    // beside it once. The carry itself is still done by the Pikmin.
    {
        static float partStall = 0.0f;
        static const Pellet* partMoved = nullptr;
        if (p2autoplay::teleportToPart() && senses.trackingPart && trackedPellet != partMoved && mapMgr
            && sEngage.carryWant > 0 && sEngage.pelletCarriers < sEngage.carryWant) {
            partStall += (dt > 0.0f && dt <= 0.5f) ? dt : 0.016f;
            if (partStall > 20.0f) {
                partMoved = trackedPellet;
                partStall = 0.0f;
                const float px = trackedPellet->getPosition().x, pz = trackedPellet->getPosition().z;
                Vector3f at(px + 70.0f, mapMgr->getMinY(px + 70.0f, pz, true), pz);
                navi->resetPosition(at);
                int moved = 0;
                Iterator pit2(pikiMgr);
                CI_LOOP(pit2)
                {
                    Piki* p = static_cast<Piki*>(*pit2);
                    if (!p || !p->isAlive() || p->mMode == PikiMode::TransportMode) continue;
                    const int st = p->getState();
                    if (st == PIKISTATE_Bury || st == PIKISTATE_Dying || st == PIKISTATE_Dead) continue;
                    const float ang = 0.61803f * 6.2831853f * float(moved);
                    const float rad = 40.0f + 5.0f * float(moved % 12);
                    Vector3f pp(px + rad * std::cos(ang), 0.0f, pz + rad * std::sin(ang));
                    pp.y = mapMgr->getMinY(pp.x, pp.z, true);
                    p->resetPosition(pp);
                    ++moved;
                }
                std::printf("AUTOPLAY_TELEPORT_TO_PART x=%.1f z=%.1f moved=%d TEST-ONLY bot-driven\n", double(px), double(pz), moved);
                std::fflush(stdout);
            }
        } else if (!senses.trackingPart) {
            partStall = 0.0f;
        }
    }
    senses.partGone = partGone;
    senses.workCount = workCount;
    senses.movieActive = gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive;
    senses.overlayActive = gameflow.mIsUIOverlayActive || gameflow.mPauseAll;
    {
        // #901: nearest unfinished route obstacle within 600 u of the captain
        // (read-only): gates (sluices), bridges, hinder rocks, climbing
        // stalks (Kusa: formed Pikmin that touch one climb it, RopeMode).
        float bestD = 600.0f;
        // Only an obstacle on the way counts: next to the captain, or nearer
        // the target than he is (a bridge behind him is not the blocker).
        const float obsTx = pick ? pick->x : sEngage.lastX, obsTz = pick ? pick->z : sEngage.lastZ;
        const float naviToTarget = distXZ(naviX, naviZ, obsTx, obsTz);
        auto consider = [&](Creature* obj, int kind, int stage, int stages) {
            const float d = distXZ(naviX, naviZ, obj->getPosition().x, obj->getPosition().z);
            const float toTarget = distXZ(obj->getPosition().x, obj->getPosition().z, obsTx, obsTz);
            if (d > 200.0f && toTarget > naviToTarget + 100.0f) return;
            if (d < bestD) {
                bestD = d;
                senses.obstacleKind = kind;
                senses.obstacleX = obj->getPosition().x;
                senses.obstacleZ = obj->getPosition().z;
                senses.obstacleType = obj->mObjType;
                senses.obstacleStage = stage;
                senses.obstacleStages = stages;
                senses.obstacleHealth = obj->mHealth;
            }
        };
        if (itemMgr->getMeltingPotMgr()) {
            Iterator oit(itemMgr->getMeltingPotMgr());
            CI_LOOP(oit)
            {
                Creature* obj = *oit;
                // Bomb gates (24/25) open only to bombs: never a punch target.
                if (obj && (obj->mObjType == OBJTYPE_SluiceSoft || obj->mObjType == OBJTYPE_SluiceHard) && obj->isAlive()
                    && !static_cast<BuildingItem*>(obj)->isCompleted()) {
                    BuildingItem* gate = static_cast<BuildingItem*>(obj);
                    consider(obj, 1, gate->mCurrStage, gate->mNumStages);
                } else if (obj && obj->mObjType == OBJTYPE_Kusa && obj->mMaxHealth > 0.0f
                           && obj->mHealth < obj->mMaxHealth) {
                    consider(obj, 4, 0, 0);
                }
            }
        }
        if (workObjectMgr) {
            Iterator oit(workObjectMgr);
            CI_LOOP(oit)
            {
                WorkObject* obj = static_cast<WorkObject*>(*oit);
                if (!obj || obj->isFinished()) continue;
                if (obj->isBridge()) consider(obj, 2, 0, 0);
                else if (obj->isHinderRock()) consider(obj, 3, 0, 0);
            }
        }
    }
    senses.partyCount = partyCount;
    if (senses.trackingPart) {
        // Idle Pikmin within 600 u of the part, and their centroid.
        float sx = 0.0f, sz = 0.0f;
        int n = 0;
        for (const auto& fp : freePos) {
            if (distXZ(fp.first, fp.second, sEngage.lastX, sEngage.lastZ) > 600.0f) continue;
            sx += fp.first;
            sz += fp.second;
            ++n;
        }
        senses.freeCount = n;
        senses.freeX = n ? sx / float(n) : sEngage.lastX;
        senses.freeZ = n ? sz / float(n) : sEngage.lastZ;
    }
    senses.pelletExists = sEngage.bodyPresent || sEngage.pelletFound || !sEngage.deadLatch;
    senses.corpseMoving = corpseMoving;
    senses.corpseMoved = corpseMoved;
    senses.targetDead = deadSignal;
    // #884 round 4: the live throw cursor (read-only) for the King standoff
    // hold (Navi::mCursorPosition is the XZ offset from the captain).
    senses.cursorValid = true;
    senses.cursorX = naviX + navi->mCursorPosition.x;
    senses.cursorZ = naviZ + navi->mCursorPosition.z;
    // #884 round 5: the captain's live health for the King stance's
    // low-health guard (read-only).
    senses.naviHpValid = true;
    senses.naviHp = navi->mHealth;
    senses.powerRestocks = sPowerRestocks;
    // #897 push obstacle (read-only): nearest unfinished HinderRock within
    // 400 of the captain and ahead of where the Brain is steering (the
    // current waypoint leg, else the target).
    if (workObjectMgr && pick && sBrain.current() == p2autoplay::State::Approach) {
        float aheadX = pick->x, aheadZ = pick->z;
        if (!sPath.empty() && sPathIdx < sPath.size()) {
            aheadX = sPath[sPathIdx].first;
            aheadZ = sPath[sPathIdx].second;
        }
        const float hx = aheadX - naviX, hz = aheadZ - naviZ;
        const float hl = std::sqrt(hx * hx + hz * hz);
        float best = 400.0f;
        Iterator wit(workObjectMgr);
        CI_LOOP(wit)
        {
            WorkObject* w = static_cast<WorkObject*>(*wit);
            if (!w || !w->isHinderRock() || w->isFinished()) continue;
            const float ox = w->getPosition().x, oz = w->getPosition().z;
            const float d = distXZ(naviX, naviZ, ox, oz);
            if (d >= best) continue;
            const float dot = hl > 1.0f && d > 1.0f ? ((ox - naviX) * hx + (oz - naviZ) * hz) / (hl * d) : 1.0f;
            if (dot < 0.2f && d > 200.0f) continue;
            best = d;
            senses.pushValid = true;
            senses.pushX = ox;
            senses.pushZ = oz;
            senses.pushDist = d;
            HinderRock* rock = static_cast<HinderRock*>(w);
            senses.pushMoving = rock->isMoving();
            // Near-face aim: extent of the box footprint toward the captain
            // (max over its four corners) plus a margin.
            const float ux = d > 1.0f ? (naviX - ox) / d : 0.0f, uz = d > 1.0f ? (naviZ - oz) / d : 1.0f;
            float ext = 0.0f;
            for (int v = 0; v < 4; ++v) {
                const Vector3f c = rock->getVertex(v);
                const float e = (c.x - ox) * ux + (c.z - oz) * uz;
                if (e > ext && e < 400.0f) ext = e;
            }
            if (ext <= 1.0f) ext = 50.0f;
            senses.pushAimX = ox + ux * (ext + 22.0f);
            senses.pushAimZ = oz + uz * (ext + 22.0f);
        }
    }
    // Onion receipt for this token (bot-v2 gap 1): durable delivery-ledger
    // query, read-only. carried=1 in RESULT means this was seen.
    senses.receiptSeen = sEngage.token ? pc_randomizer_p2_receipt_seen(sEngage.token) : false;
    if (pick) {
        senses.targetToken = pick->token;
        senses.targetSource = pick->source;
        senses.tgtX = pick->x;
        senses.tgtZ = pick->z;
        senses.aimValid = pick->source == 73
                          && pc_p2_bigtreasure_teki_aim_point(pick->actor, naviX, naviZ, &senses.aimX, &senses.aimZ);
        senses.targetDist = pick->dist;
        senses.targetAlive = true;
        senses.targetHealthFrac = pick->health / (sEngage.initialHealth > 0.0f ? sEngage.initialHealth : 1.0f);
        if (senses.targetHealthFrac < 0.0f) senses.targetHealthFrac = 0.0f;
        sEngage.lastX = pick->x;
        sEngage.lastZ = pick->z;
        sEngage.lastAlive = true;
        const bool kogane = p2autoplay::isKoganeLike(pick->source);
        if (!kogane && pick->health < sEngage.initialHealth - 0.5f) senses.targetDamagedLatch = true;
        if (kogane) {
            if (pc_p2_kogane_nectar_dropped(pick->token) > sEngage.initialNectar) senses.targetDamagedLatch = true;
            if (pc_p2_kogane_escaped(pick->actor)) senses.targetDamagedLatch = true;
        }
        if (pick->source == 79 && pc_p2_sokkuri_revealed(pick->actor)) senses.targetRevealed = true;
        else if (pick->source == 79) senses.targetRevealed = false;
        // #884 round 5: KingChappy in its attack state (read-only FSM probe;
        // what a player sees as the King rearing up to tongue). The stance
        // leaves the tongue sweep while it lasts.
        if (p2autoplay::isKingStandoff(pick->source)) {
            const char* kst = nullptr;
            senses.targetAttacking = pc_p2_chappy_probe(pick->actor, &kst, nullptr, nullptr) && kst
                && std::strcmp(kst, "attack") == 0;
        }
        // #245: the Antenna Beetle's whistle cast (read-only FSM probe). The
        // Fuefuki stance leaves the growing cast ring while it lasts.
        if (p2autoplay::isFuefukiStandoff(pick->source))
            senses.targetAttacking = pc_p2_fuefuki_teki_casting(pick->actor);
        if (!sEngage.homeValid) {
            sEngage.homeValid = true;
            sEngage.homeX = pick->x;
            sEngage.homeZ = pick->z;
        }
        senses.homeValid = sEngage.homeValid;
        senses.homeX = sEngage.homeX;
        senses.homeZ = sEngage.homeZ;
        senses.targetDyValid = true;
        senses.targetDy = pick->actor->getPosition().y - navi->getPosition().y;
        // #897 roller stance: Crawbster FSM facts (read-only probe).
        if (p2autoplay::isRollerStance(pick->source)) {
            const char* dst = nullptr;
            bool rolling = false, stickable = false;
            float vx = 0.0f, vz = 0.0f;
            if (pc_p2_dangomushi_probe(pick->actor, &dst, &rolling, &stickable, &vx, &vz)) {
                senses.targetDormant = dst && std::strcmp(dst, "stay") == 0;
                senses.targetRolling = rolling;
                senses.targetVulnerable = stickable;
                senses.targetVelX = vx;
                senses.targetVelZ = vz;
            }
        }
        // #256 Empress Bulblax roll dodge senses (read-only FSM probe).
        if (pick->source == 30) {
            int qst = -1;
            float qface = 0.0f, qhx = 0.0f, qhz = 0.0f;
            if (pc_p2_queen_teki_probe(pick->actor, &qst, &qface, &qhx, &qhz)) {
                senses.queenDanger = qst == 4 || qst == 5; // Flick / Rolling (Queen.h StateID)
                const float fx = std::sin(qface), fz = std::cos(qface);
                const float side = ((naviX - qhx) * fx + (naviZ - qhz) * fz) >= 0.0f ? 1.0f : -1.0f;
                senses.dodgeX = qhx + fx * side * 320.0f;
                senses.dodgeZ = qhz + fz * side * 320.0f;
            }
        }
        // Flyer senses (bot-v2 gap 3): height above ground, grab latch.
        // Kurage's body is on the ground (visual float only), so its XZ body
        // position above is already the throw aim; Sarai throws only when low
        // or holding a Pikmin.
        {
            float groundY = pick->actor->getPosition().y;
            if (mapMgr) groundY = mapMgr->getMinY(pick->actor->getPosition().x,
                                                 pick->actor->getPosition().z, true);
            float height = pick->actor->getPosition().y - groundY;
            if (!(height > 0.0f)) height = 0.0f;
            senses.targetHeight = height;
            senses.targetLow = height <= 120.0f;
            bool grabbing = false;
            if (pikiMgr) {
                Iterator git(pikiMgr);
                CI_LOOP(git)
                {
                    Piki* p = static_cast<Piki*>(*git);
                    if (!p || !p->isAlive()) continue;
                    if (p->getStickObject() == pick->actor) {
                        grabbing = true;
                        break;
                    }
                }
            }
            senses.targetGrabbing = grabbing;
            if (pick->source == 23 && (grabbing || height <= 120.0f)) senses.targetLow = true;
        }
        // #901 TEST-ONLY diagnostic: dump the ground heights and route
        // waypoints around the first target once, so an arena approach can be
        // read offline (PIKMIN_RANDOMIZER_AUTOPLAY_TERRAIN_DUMP=1).
        {
            static bool terrainDumped = false;
            const char* dump = std::getenv("PIKMIN_RANDOMIZER_AUTOPLAY_TERRAIN_DUMP");
            if (!terrainDumped && dump && *dump == '1' && mapMgr) {
                terrainDumped = true;
                const float cx = pick->x, cz = pick->z;
                for (int j = -24; j <= 24; ++j) {
                    std::string row;
                    char cell[24];
                    for (int i = -24; i <= 24; ++i) {
                        const float px = cx + 25.0f * float(i), pz = cz + 25.0f * float(j);
                        CollTriInfo* tri = mapMgr->getCurrTri(px, pz, true);
                        if (!tri) std::snprintf(cell, sizeof(cell), i == -24 ? "x" : ",x");
                        else std::snprintf(cell, sizeof(cell), i == -24 ? "%.0f%s" : ",%.0f%s",
                                           double(mapMgr->getMinY(px, pz, true)),
                                           MapCode::getAttribute(tri) == ATTR_Water ? "w" : "");
                        row += cell;
                    }
                    std::printf("AUTOPLAY_TERRAIN cx=%.0f cz=%.0f j=%d z=%.0f row=%s bot-driven\n", double(cx),
                                double(cz), j, double(cz + 25.0f * float(j)), row.c_str());
                }
                if (routeMgr) {
                    const int n = routeMgr->getNumWayPoints('test');
                    for (int w = 0; w < n && n <= 4096; ++w) {
                        WayPoint* wp = routeMgr->getWayPoint('test', w);
                        if (!wp) continue;
                        std::string links;
                        for (int k = 0; k < wp->mLinkCount && k < 8; ++k)
                            links += (k ? "," : "") + std::to_string(wp->mLinkIndices[k]);
                        std::printf("AUTOPLAY_WAYPOINT idx=%d x=%.0f y=%.0f z=%.0f open=%d water=%d links=%s bot-driven\n",
                                    w, double(wp->mPosition.x), double(wp->mPosition.y), double(wp->mPosition.z),
                                    int(wp->mIsOpen), int(wp->inWater()), links.c_str());
                    }
                }
                std::fflush(stdout);
            }
        }
    } else if (sEngage.token) {
        // Engagement target no longer live-listed: report last-known facts;
        // the Brain scores the outcome (kill vs giveup) from damage history.
        senses.targetToken = sEngage.token;
        senses.targetSource = sEngage.source;
        senses.tgtX = sEngage.lastX;
        senses.tgtZ = sEngage.lastZ;
        senses.targetDist = distXZ(naviX, naviZ, sEngage.lastX, sEngage.lastZ);
        senses.targetAlive = false;
        senses.targetHealthFrac = 0.0f;
    }

    // --- Stuck replan via the map's route/waypoint graph ---
    // Every STUCK replans (bot-v3: approach must use method=graph, never an
    // identical detour; Done holds near the Onion so it replans there too).
    if (sBrain.replanWanted()) {
        sPlanStartY = navi->getPosition().y;
        sPlanGoalY = NAN;
        if (pick && pick->actor && sBrain.current() != p2autoplay::State::WithdrawSeek
            && sBrain.current() != p2autoplay::State::Done)
            sPlanGoalY = pick->actor->getPosition().y;
        if (sBrain.current() == p2autoplay::State::WithdrawSeek && hasOnion) {
            planDetour(naviX, naviY, naviZ, onionX, onionZ);
        } else if (sBrain.current() == p2autoplay::State::Done && hasOnion) {
            planDetour(naviX, naviY, naviZ, onionX, onionZ);
        } else if (pick && sBrain.current() == p2autoplay::State::Approach && planHinderRock(naviX, naviZ)) {
            // walking the squad into a route-closing box first (#246/#899)
        } else if (pick) {
            planDetour(naviX, naviY, naviZ, pick->x, pick->z);
        } else if (sEngage.token) {
            planDetour(naviX, naviY, naviZ, sEngage.lastX, sEngage.lastZ);
        }
        sBrain.clearReplan();
    }
    // #256 Empress regroup: route to the nearest idle stray through the waypoint graph.
    if (sBrain.strayRouteWanted()) {
        sPlanStartY = navi->getPosition().y;
        sPlanGoalY = NAN;
        planDetour(naviX, naviY, naviZ, sBrain.strayRouteGoalX(), sBrain.strayRouteGoalZ());
        std::printf("AUTOPLAY_STRAY_ROUTE goal=(%.0f,%.0f) legs=%zu bot-driven\n", double(sBrain.strayRouteGoalX()),
                    double(sBrain.strayRouteGoalZ()), sPath.size());
        sBrain.clearStrayRoute();
    }
    // Waypoint-by-waypoint following: steer each leg until reached (80u) or
    // its 25s budget expires, then advance; the Brain steers the active leg.
    if (sHinderLeg) {
        const float step = dt > 0.0f && dt <= 0.5f ? dt : 0.016f;
        sHinderTime += step;
        const bool done = !sHinder || sHinder->isFinished();
        if (done || sHinderTime >= kHinderBudget || sPath.empty()
            || sBrain.current() != p2autoplay::State::Approach) {
            std::printf("AUTOPLAY_HINDER_END finished=%d seconds=%.0f moving=%d navi=(%.0f,%.0f) bot-driven\n",
                        int(sHinder && sHinder->isFinished()), double(sHinderTime),
                        int(sHinder && sHinder->isMoving()), double(naviX), double(naviZ));
            if (sHinder && mapMgr) {
                // Ground profile along the push line through the box (read-only).
                const Vector3f bp = sHinder->getPosition();
                float ax = sHinder->mDestinationPosition.x - bp.x, az = sHinder->mDestinationPosition.z - bp.z;
                const float len = std::sqrt(ax * ax + az * az);
                if (len > 1.0f) { ax /= len; az /= len; } else { ax = 0.0f; az = -1.0f; }
                std::printf("AUTOPLAY_HINDER_PROFILE box=(%.0f,%.0f,%.0f) navi_y=%.0f", double(bp.x), double(bp.y),
                            double(bp.z), double(navi->getPosition().y));
                for (int k = -6; k <= 6; ++k) {
                    const float px = bp.x + ax * 40.0f * float(k), pz = bp.z + az * 40.0f * float(k);
                    std::printf(" %d:%.0f/%.0f", k * 40, double(mapMgr->getMinY(px, pz, false)),
                                double(mapMgr->getMinY(px, pz, true)));
                }
                std::printf(" bot-driven\n");
                if (routeMgr) {
                    const int n = routeMgr->getNumWayPoints('test');
                    for (int i = 0; i < n && n <= 4096; ++i) {
                        WayPoint* wp = routeMgr->getWayPoint('test', i);
                        if (!wp || distXZ(wp->mPosition.x, wp->mPosition.z, bp.x, bp.z) > 450.0f) continue;
                        std::printf("AUTOPLAY_HINDER_WP idx=%d pos=(%.0f,%.0f,%.0f) open=%d links=", i,
                                    double(wp->mPosition.x), double(wp->mPosition.y), double(wp->mPosition.z),
                                    int(wp->mIsOpen));
                        for (int l = 0; l < 8; ++l)
                            if (wp->mLinkIndices[l] >= 0) std::printf("%d,", wp->mLinkIndices[l]);
                        std::printf(" bot-driven\n");
                    }
                }
                std::fflush(stdout);
            }
            sHinderLeg = false;
            sHinder = nullptr;
            sPath.clear();
            sPathIdx = 0;
            sLegTime = 0.0f;
        } else if (sPathIdx == 0) {
            // Leg 0: reach the push side (80u or 25 s), then leg 1 holds.
            sLegTime += step;
            if (distXZ(naviX, naviZ, sPath[0].first, sPath[0].second) < 80.0f || sLegTime > 25.0f) {
                sPathIdx = 1;
                sLegTime = 0.0f;
            }
            senses.waypointLeg = true;
            senses.obstacleWork = true;
            senses.wpX = sPath[sPathIdx].first;
            senses.wpZ = sPath[sPathIdx].second;
        } else {
            // Leg 1: keep walking into the box (it moves: follow its centre).
            senses.waypointLeg = true;
            senses.obstacleWork = true;
            senses.wpX = sHinder->getPosition().x;
            senses.wpZ = sHinder->getPosition().z;
        }
    } else if (!sPath.empty() && sPathIdx < sPath.size()) {
        sLegTime += dt > 0.0f && dt <= 0.5f ? dt : 0.016f;
        float legX = sPath[sPathIdx].first, legZ = sPath[sPathIdx].second;
        while (sPathIdx < sPath.size()
               && (distXZ(naviX, naviZ, legX, legZ)
                       < std::min(legReachRadius(legX, legZ), legReachRadiusLevel(sPathIdx, naviY))
                   || sLegTime > 25.0f)) {
            ++sPathIdx;
            sLegTime = 0.0f;
            if (sPathIdx < sPath.size()) {
                legX = sPath[sPathIdx].first;
                legZ = sPath[sPathIdx].second;
            }
        }
        if (sPathIdx < sPath.size()) {
            senses.waypointLeg = true;
            senses.wpX = legX;
            senses.wpZ = legZ;
            // #901: remaining route length for the approach progress metric.
            float rem = distXZ(naviX, naviZ, legX, legZ);
            for (size_t i = sPathIdx; i + 1 < sPath.size(); ++i)
                rem += distXZ(sPath[i].first, sPath[i].second, sPath[i + 1].first, sPath[i + 1].second);
            rem += distXZ(sPath.back().first, sPath.back().second, senses.tgtX, senses.tgtZ);
            senses.pathRemaining = rem;
        } else {
            sPath.clear();
            sPathIdx = 0;
            sLegTime = 0.0f;
        }
    }

    sBrain.update(dt, senses);

    // Completed-target bookkeeping from emitted RESULT lines.
    for (const std::string& marker : sBrain.takeMarkers()) {
        std::printf("%s\n", marker.c_str());
        unsigned done = 0;
        if (std::sscanf(marker.c_str(), "AUTOPLAY_RESULT target=%u", &done) == 1 && done) {
            sCompleted.insert(done);
            if (done == sEngage.token) {
                sEngage = Engagement{};
                sPath.clear();
                sPathIdx = 0;
                sLegTime = 0.0f;
                sDetourHist.clear();
                sLastDetourValid = false;
            }
        }
    }
    std::fflush(stdout);

    // --- Pad synthesis through the live camera basis ---
    p2autoplay::Command cmd = sBrain.command();
    // TEST-ONLY coarse water map (PIKMIN_RANDOMIZER_AUTOPLAY_WATER_MAP=1): one dump of
    // ground (.), water (W) and no-ground (x) on a 50 u grid so a lure path can be planned.
    {
        static bool waterMapped = false;
        const char* wm = std::getenv("PIKMIN_RANDOMIZER_AUTOPLAY_WATER_MAP");
        if (!waterMapped && wm && *wm == '1' && mapMgr) {
            waterMapped = true;
            for (int j = 0; j <= 90; ++j) {
                const float pz = 50.0f * float(j);
                std::string row;
                for (int i = -50; i <= 40; ++i) {
                    const float px = 50.0f * float(i);
                    CollTriInfo* tri = mapMgr->getCurrTri(px, pz, true);
                    row += !tri ? 'x' : (MapCode::getAttribute(tri) == ATTR_Water ? 'W' : '.');
                }
                std::printf("AUTOPLAY_WATERMAP z=%.0f x0=-2500 step=50 row=%s TEST-ONLY bot-driven\n", double(pz), row.c_str());
            }
            std::fflush(stdout);
        }
    }
    // TEST-ONLY lure path (PIKMIN_RANDOMIZER_AUTOPLAY_LURE): replace the Brain
    // command with a walk along the waypoint list, then hold still.
    {
        static const std::vector<std::pair<float, float>> lure = p2autoplay::lurePath();
        static size_t lureIdx = 0;
        static int lureWarm = 0;
        if (!lure.empty()) {
            cmd = p2autoplay::Command{};
            if (lureWarm == 300) {
                const char* lt = std::getenv("PIKMIN_RANDOMIZER_AUTOPLAY_LURE_TELEPORT");
                if (lt && *lt == '1' && mapMgr) {
                    // Start the lure at its first waypoint (the walk from the Onion is not what is under test).
                    const float ty = mapMgr->getMinY(lure[0].first, lure[0].second, true);
                    Vector3f at(lure[0].first, ty, lure[0].second);
                    navi->resetPosition(at);
                    std::printf("AUTOPLAY_LURE_TELEPORT x=%.0f z=%.0f TEST-ONLY bot-driven\n", double(at.x), double(at.z));
                    std::fflush(stdout);
                    lureIdx = 1;
                }
            }
            if (lureWarm % 120 == 0) {
                std::printf("AUTOPLAY_LURE_POS idx=%zu navi=(%.0f,%.0f) attr=%d TEST-ONLY bot-driven\n", lureIdx, double(naviX), double(naviZ),
                            navi->mGroundTriangle ? MapCode::getAttribute(navi->mGroundTriangle) : -1);
                // Every campaign teki within 1200 u: where it is and whether the engine is still updating it.
                Iterator lit(tekiMgr);
                CI_LOOP(lit)
                {
                    Teki* lt = static_cast<Teki*>(*lit);
                    if (!lt || !lt->mGenerator) continue;
                    BTeki* lb = static_cast<BTeki*>(lt);
                    const float d = distXZ(naviX, naviZ, lb->getPosition().x, lb->getPosition().z);
                    if (d > 1200.0f) continue;
                    std::printf("AUTOPLAY_LURE_TEKI type=%d pos=(%.0f,%.0f) dist=%.0f vel=(%.1f,%.1f) aiCulling=%d aiCullable=%d alwaysActive=%d attr=%d TEST-ONLY bot-driven\n",
                                int(lb->mTekiType), double(lb->getPosition().x), double(lb->getPosition().z), double(d), double(lb->mVelocity.x),
                                double(lb->mVelocity.z), int(lb->mGrid.aiCulling()), int(lb->aiCullable()), int(lb->insideView()),
                                lb->getPositionMapCode());
                }
                std::fflush(stdout);
            }
            if (++lureWarm > 300 && lureIdx < lure.size()) {
                const float dx = lure[lureIdx].first - naviX, dz = lure[lureIdx].second - naviZ;
                const float len = std::sqrt(dx * dx + dz * dz);
                if (len < 30.0f) {
                    std::printf("AUTOPLAY_LURE reached=%zu navi=(%.0f,%.0f) TEST-ONLY bot-driven\n", lureIdx, double(naviX), double(naviZ));
                    std::fflush(stdout);
                    ++lureIdx;
                } else {
                    cmd.moveX = dx / len;
                    cmd.moveZ = dz / len;
                }
            }
        }
    }
    unsigned buttons = cmd.buttons;
    int stickX = 0, stickY = 0;
    float yawDbg = 0.0f;
    if (cmd.menuHold) {
        stickY = -127; // container withdraw direction
        buttons |= unsigned(p2autoplay::PadMainDown);
    } else if (cmd.moveX != 0.0f || cmd.moveZ != 0.0f) {
        float yaw = 0.0f;
        if (navi->mNaviCamera) yaw = std::atan2(navi->mNaviCamera->mViewXAxis.z, navi->mNaviCamera->mViewXAxis.x);
        yawDbg = yaw;
        const float c = std::cos(yaw), s = std::sin(yaw);
        // Inverse of makeVelocity's RotY(yaw): local = RotY(-yaw) * world.
        const float lx = c * cmd.moveX + s * cmd.moveZ;
        const float lz = -s * cmd.moveX + c * cmd.moveZ;
        float sx = lx > 1.0f ? 1.0f : (lx < -1.0f ? -1.0f : lx);
        float sy = lz > 1.0f ? -1.0f : (lz < -1.0f ? 1.0f : -lz);
        // #884 round 4: the King standoff hold scales the stick into the
        // P1 look band (Command::stickScale); everything else stays 1.
        const float scale = (cmd.stickScale > 0.0f && cmd.stickScale < 1.0f) ? cmd.stickScale : 1.0f;
        stickX = int(sx * scale * 127.0f);
        stickY = int(sy * scale * 127.0f);
        if (stickX > 32) buttons |= unsigned(p2autoplay::PadMainRight);
        else if (stickX < -32) buttons |= unsigned(p2autoplay::PadMainLeft);
        if (stickY > 32) buttons |= unsigned(p2autoplay::PadMainUp);
        else if (stickY < -32) buttons |= unsigned(p2autoplay::PadMainDown);
    }
    // #901: C-stick swarm through the same camera basis (Navi::makeCStick
    // rotates (subX, -subY) by the camera yaw, like the main stick).
    int subX = 0, subY = 0;
    if (cmd.swarmX != 0.0f || cmd.swarmZ != 0.0f) {
        float yaw = 0.0f;
        if (navi->mNaviCamera) yaw = std::atan2(navi->mNaviCamera->mViewXAxis.z, navi->mNaviCamera->mViewXAxis.x);
        const float c = std::cos(yaw), s = std::sin(yaw);
        const float lx = c * cmd.swarmX + s * cmd.swarmZ;
        const float lz = -s * cmd.swarmX + c * cmd.swarmZ;
        const float sx = lx > 1.0f ? 1.0f : (lx < -1.0f ? -1.0f : lx);
        const float sy = lz > 1.0f ? -1.0f : (lz < -1.0f ? 1.0f : -lz);
        subX = int(sx * 72.0f);
        subY = int(sy * 72.0f);
        if (subX > 32) buttons |= unsigned(p2autoplay::PadCStickRight);
        else if (subX < -32) buttons |= unsigned(p2autoplay::PadCStickLeft);
        if (subY > 32) buttons |= unsigned(p2autoplay::PadCStickUp);
        else if (subY < -32) buttons |= unsigned(p2autoplay::PadCStickDown);
    }
    pc_p2_input_script_set(1, buttons, stickX, stickY);
    pc_p2_input_script_set_sub(1, subX, subY);

    // --- Withdraw diagnostics (bot-driven): proves the captain closes to
    // the real container trigger instead of stalling at arriveRadius. ---
    if (sBrain.current() == p2autoplay::State::WithdrawSeek && (sTicks % 300 == 0)) {
        std::printf("AUTOPLAY_WITHDRAW navi=(%.0f,%.0f) onion=(%.0f,%.0f) dist=%.0f stored=%d field=%d open=%d bot-driven\n",
                    naviX, naviZ, onionX, onionZ, onionDist, onionStored, alive,
                    senses.containerOpen ? 1 : 0);
        std::fflush(stdout);
    }

    // --- bot-v3 steering diagnostics: proves the navi moves under stick
    // input (or exposes why: state, menu, stick, camera yaw, velocity). ---
    {
        const p2autoplay::State st = sBrain.current();
        const bool steering = (st == p2autoplay::State::Approach || st == p2autoplay::State::Done
                               || st == p2autoplay::State::WithdrawSeek
                               || st == p2autoplay::State::Attack
                               || st == p2autoplay::State::Aftermath);
        if (steering && (sTicks % 300 == 0)) {
            const int stateId = (navi->getCurrState() != nullptr) ? navi->getCurrState()->getID() : -999;
            float legX = senses.waypointLeg ? senses.wpX : senses.tgtX;
            float legZ = senses.waypointLeg ? senses.wpZ : senses.tgtZ;
            if (st != p2autoplay::State::Approach && st != p2autoplay::State::Attack
                && st != p2autoplay::State::Aftermath) {
                legX = senses.waypointLeg ? senses.wpX : onionX;
                legZ = senses.waypointLeg ? senses.wpZ : onionZ;
            }
            const float velLen = navi->mTargetVelocity.length();
            const float stickLen = navi->mMainStick.length();
            const float showDist = (st == p2autoplay::State::Approach || st == p2autoplay::State::Attack
                                    || st == p2autoplay::State::Aftermath)
                ? senses.targetDist
                : onionDist;
            std::printf("AUTOPLAY_NAVI state=%s navi=(%.0f,%.0f) tgt=(%.0f,%.0f) tdist=%.0f leg=(%.0f,%.0f) move=(%.2f,%.2f) stick=(%d,%d) btn=%u nstate=%d open=%d yaw=%.2f vel=%.1f mstick=%.2f hp=%.2f scat=%d field=%d navi_hp=%.1f cursor=(%.0f,%.0f) king_attack=%d ny=%.0f bot-driven\n",
                        p2autoplay::stateName(st), naviX, naviZ,
                        (st == p2autoplay::State::Approach || st == p2autoplay::State::Attack
                         || st == p2autoplay::State::Aftermath)
                            ? senses.tgtX
                            : onionX,
                        (st == p2autoplay::State::Approach || st == p2autoplay::State::Attack
                         || st == p2autoplay::State::Aftermath)
                            ? senses.tgtZ
                            : onionZ,
                        showDist, legX, legZ, cmd.moveX, cmd.moveZ, stickX, stickY, buttons,
                        stateId, senses.containerOpen ? 1 : 0, yawDbg, velLen, stickLen,
                        senses.targetHealthFrac, senses.scattered ? 1 : 0, alive,
                        navi->mHealth, senses.cursorX, senses.cursorZ, senses.targetAttacking ? 1 : 0,
                        navi->getPosition().y);
            std::fflush(stdout);
        }
    }

    // --- bot-v7 carry diagnostics: carriers vs the corpse's declared
    // minimum + corpse distance + live motion, rate-limited (every 300 ticks
    // like NAVI) plus the rising edge, so the matrix reports the shortfall
    // per species even when no receipt lands. Format is the brief's:
    // AUTOPLAY_CARRY carriers=<n> want=<min> tdist=<d> moving=<0/1>. ---
    {
        const p2autoplay::State st = sBrain.current();
        if (st == p2autoplay::State::Aftermath && sEngage.token) {
            const float tdist = distXZ(naviX, naviZ, sEngage.lastX, sEngage.lastZ);
            const bool edge = carryActive && !sEngage.carryLatch;
            if (edge || (sTicks % 300 == 0)) {
                std::printf("AUTOPLAY_CARRY carriers=%d want=%d tdist=%.0f moving=%d bot-driven\n",
                            sEngage.carryNear, sEngage.carryWant, tdist,
                            corpseMoving ? 1 : 0);
                std::fflush(stdout);
            }
            if (carryActive) sEngage.carryLatch = true;
        } else if (!carryActive) {
            sEngage.carryLatch = false;
        }
    }

    // --- FPS evidence ---
    if (++sTicks % 3600 == 0) {
        const auto now = std::chrono::steady_clock::now();
        const double secs = std::chrono::duration<double>(now - sFpsStart).count();
        if (secs > 0.0) {
            std::printf("AUTOPLAY_FPS ticks=%lld seconds=%.0f fps=%.1f bot-driven\n",
                        sTicks, secs, double(sTicks) / secs);
            std::fflush(stdout);
            sFpsLogged = true;
        }
    }
    (void)sFpsLogged;
}
