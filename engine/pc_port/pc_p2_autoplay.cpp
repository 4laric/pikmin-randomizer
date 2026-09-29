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

#include "pc_p2_input_script.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_sokkuri.h"
#include "pc_p2_kogane.h"
#include "pc_p2_chappy.h"
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
#include "Route.h"
#include "Camera.h"
#include "gameflow.h"

#include <algorithm>
#include <chrono>
#include <cmath>
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
std::vector<int> nearestWpIdx(float x, float z, int k)
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
        const float dx = wp->mPosition.x - pos.x, dz = wp->mPosition.z - pos.z;
        scored.push_back({ dx * dx + dz * dz, i });
    }
    std::sort(scored.begin(), scored.end(), [](const Scored& a, const Scored& b) { return a.d < b.d; });
    for (int i = 0; i < int(scored.size()) && int(out.size()) < k; ++i) out.push_back(scored[i].idx);
    return out;
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
// legs reversed) as the alternate for directed links.
bool graphLegs(PathFinder* finder, int startIdx, int goalIdx,
               std::vector<std::pair<float, float>>& out, bool& reversed)
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

void planDetour(float naviX, float naviZ, float tgtX, float tgtZ)
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
        const std::vector<int> starts = nearestWpIdx(naviX, naviZ, 3);
        const std::vector<int> goals = nearestWpIdx(tgtX, tgtZ, 3);
        PathFinder* finder = routeMgr->getPathFinder('test');
        if (starts.empty()) failReason = "no_start_wp";
        else if (goals.empty()) failReason = "no_goal_wp";
        else if (!finder) failReason = "no_finder";
        else {
            bool anyPath = false;
            const u32 handle = 'test';
            for (int si : starts) {
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
            if (sPath.size() > 1 && sReplanCount % 3 == 0) {
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
    if (!naviMgr || !pikiMgr || !tekiMgr || !itemMgr) {
        return; // boot/menus: no game state yet, emit nothing
    }
    Navi* navi = naviMgr->getNavi();
    if (!navi || !navi->isAlive()) {
        sBrain.update(0.016f, p2autoplay::Senses{});
        pc_p2_input_script_set(1, 0, 0, 0);
        return;
    }

    const float dt = gsys ? gsys->getFrameTime() : 0.016f;
    const float naviX = navi->getPosition().x;
    const float naviZ = navi->getPosition().z;

    // --- Pikmin census (read-only, except bot-v4 power-mode flowering) ---
    int alive = 0, nearCount = 0, farCount = 0, transport = 0, distress = 0;
    std::vector<std::pair<float, float>> transportPos;
    const bool powerMode = p2autoplay::isPowerEnabled();
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
            if (p->mMode == PikiMode::TransportMode) {
                ++transport;
                transportPos.emplace_back(p->getPosition().x, p->getPosition().z);
            }
            // bot-v4 power mode: flowers through the normal maturity path
            // (virtual ViewPiki::setFlower, the same call the nectar GrowUp,
            // Onion exit, and pluck paths use). No direct mHappa pokes.
            if (powerMode && p->mHappa != Flower) p->setFlower(Flower);
            // bot-v4 regroup sense: grabbed (mouth-stuck / swallowed),
            // thrown off (flick/flown/fall/wave/pressed), burning/panicking.
            const int pst = p->getState();
            if (pst == PIKISTATE_Fired || pst == PIKISTATE_Flick || pst == PIKISTATE_Flown
                || pst == PIKISTATE_FallMeck || pst == PIKISTATE_Wave || pst == PIKISTATE_Pressed
                || pst == PIKISTATE_Swallowed || pst == PIKISTATE_Panic || pst == PIKISTATE_Drown
                || pst == PIKISTATE_Bubble || p->isFired() || p->isStickToMouth())
                ++distress;
        }
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
            const unsigned token = pc_p2_campaign_token(actor);
            if (!token) continue;
            unsigned source = pc_randomizer_p2_source_for(actor);
            if (!source) source = pc_randomizer_p2_source_for_id(token);
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
            c.health = actor->mHealth;
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
            if (pc_p2_campaign_token(b) != sEngage.token) continue;
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
    if (sEngage.token && sEngage.deadLatch && pelletMgr && !sEngage.bodyPresent) {
        float best2 = 600.0f * 600.0f;
        Pellet* best = nullptr;
        Iterator pit(pelletMgr);
        CI_LOOP(pit)
        {
            Pellet* pel = static_cast<Pellet*>(*pit);
            if (!pel || !pel->isAlive()) continue;
            const float dx = pel->getPosition().x - sEngage.lastX;
            const float dz = pel->getPosition().z - sEngage.lastZ;
            const float d2 = dx * dx + dz * dz;
            if (d2 < best2) {
                best2 = d2;
                best = pel;
            }
        }
        if (best) {
            sEngage.pelletFound = true;
            sEngage.pelletCarriers = best->mCarrierCounter;
            sEngage.lastX = best->getPosition().x;
            sEngage.lastZ = best->getPosition().z;
            trackedPellet = best;
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
    senses.onionStored = onionStored;
    senses.onionDist = onionDist;
    senses.containerOpen = navi->getCurrState() && navi->getCurrState()->getID() == NAVISTATE_Container;
    senses.scattered = (farCount >= 3) || (alive >= 10 && nearCount < 5);
    senses.squadDistress = distress > 0;
    // bot-v5: live per-corpse carry (was a forever latch on ANY transport).
    // receiptSeen stays the per-token ledger query (per-token bystander-proof).
    senses.transportSeen = carryActive;
    senses.carryCount = sEngage.carryNear;
    senses.pelletCarriers = sEngage.pelletCarriers;
    senses.carryWant = sEngage.carryWant; // bot-v7: declared minimum (0 = unknown)
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
    // Onion receipt for this token (bot-v2 gap 1): durable delivery-ledger
    // query, read-only. carried=1 in RESULT means this was seen.
    senses.receiptSeen = sEngage.token ? pc_randomizer_p2_receipt_seen(sEngage.token) : false;
    if (pick) {
        senses.targetToken = pick->token;
        senses.targetSource = pick->source;
        senses.tgtX = pick->x;
        senses.tgtZ = pick->z;
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
        if (sBrain.current() == p2autoplay::State::WithdrawSeek && hasOnion) {
            planDetour(naviX, naviZ, onionX, onionZ);
        } else if (sBrain.current() == p2autoplay::State::Done && hasOnion) {
            planDetour(naviX, naviZ, onionX, onionZ);
        } else if (pick) {
            planDetour(naviX, naviZ, pick->x, pick->z);
        } else if (sEngage.token) {
            planDetour(naviX, naviZ, sEngage.lastX, sEngage.lastZ);
        }
        sBrain.clearReplan();
    }
    // Waypoint-by-waypoint following: steer each leg until reached (80u) or
    // its 25s budget expires, then advance; the Brain steers the active leg.
    if (!sPath.empty() && sPathIdx < sPath.size()) {
        sLegTime += dt > 0.0f && dt <= 0.5f ? dt : 0.016f;
        float legX = sPath[sPathIdx].first, legZ = sPath[sPathIdx].second;
        while (sPathIdx < sPath.size()
               && (distXZ(naviX, naviZ, legX, legZ) < 80.0f || sLegTime > 25.0f)) {
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
    const p2autoplay::Command cmd = sBrain.command();
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
    pc_p2_input_script_set(1, buttons, stickX, stickY);

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
            std::printf("AUTOPLAY_NAVI state=%s navi=(%.0f,%.0f) tgt=(%.0f,%.0f) tdist=%.0f leg=(%.0f,%.0f) move=(%.2f,%.2f) stick=(%d,%d) btn=%u nstate=%d open=%d yaw=%.2f vel=%.1f mstick=%.2f hp=%.2f scat=%d field=%d navi_hp=%.1f cursor=(%.0f,%.0f) king_attack=%d bot-driven\n",
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
                        navi->mHealth, senses.cursorX, senses.cursorZ, senses.targetAttacking ? 1 : 0);
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
