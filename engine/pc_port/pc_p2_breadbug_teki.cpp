// Campaign OWN driver for the Breadbug (PanModoki 38, #898) and the Giant
// Breadbug (OoPanModoki 40, #958). See the header.
#include "pc_p2_breadbug_teki.h"
#include "pc_p2_breadbug_fsm.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_groink_clock.h"
#include "pc_p2_animation.h"
#include "pc_p2_purple.h"
#include "pc_p2_pose_family.h"
#include "pc_p2_breadbug_corpse.h"
#include "pc_p2_breadbug_nest.h"
#include "pc_p2_sfx.h"
#include "pc_randomizer.h"
#include "Interactions.h"
#include "MapCode.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Pellet.h"
#include "PelletState.h"
#include "Piki.h"
#include "PikiAI.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "Route.h"
#include "Shape.h"
#include "Stickers.h"
#include "Texture.h"
#include "Graphics.h"
#include "gameflow.h"
#include "gl/pc_gfx.h"
#include "system.h"
#include "teki.h"
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <map>
#include <set>
#include <string>
#include <vector>

namespace {
namespace bb = p2breadbugfsm;
// Variants (#958): 38 PanModoki (Breadbug) and 40 OoPanModoki (Giant Breadbug)
// share this driver and the FSM; they differ in staged inputs, parameters and
// the OoPanModoki rules applied through bb::applyVariant / the Purple-only press.
struct Variant {
    unsigned source;
    bool giant;
    const char* parms;      // staged verbatim retail enemyparm.txt
    const char* bank;       // staged clip/key-event/pose bank
    const char* posePrefix; // <prefix>_<clip>_<ii>.mod in the private model room
    const char* model;
};
constexpr int kVariantCount = 2;
constexpr Variant kVariants[kVariantCount] = {
    {38, false, "p2-breadbug-parms.txt", "p2-breadbug-bank.txt", "breadbug", "p2_panmodoki"},
    {40, true, "p2-giantbreadbug-parms.txt", "p2-giantbreadbug-bank.txt", "giantbreadbug", "p2_oopanmodoki"},
};
int variantOf(unsigned source) {
    for (int v = 0; v < kVariantCount; ++v)
        if (kVariants[v].source == source) return v;
    return -1;
}

struct Binding {
    unsigned generator = 0;
    unsigned source = 38;
    int variant = 0;
    int pressesRejectedKind = 0; // giant: non-Purple presses (pressCallBack refuses them)
    bb::Fsm fsm;
    P2GroinkSourceClock clock;
    bool escaped = false;       // host death funnel ran (pcEscapeNow)
    bool corpseLogged = false;
    bb::Animator corpseAnim;    // presentation-only carried-corpse clock (type5 loop); never read by gameplay
    bool corpseAnimStarted = false;
    float nestY = 0.0f;         // #1022 lair height (birth position y)
    float nestYaw = 0.0f;       // #1022 lair facing (birth faceDir)
    bool deadLogged = false;
    int pendingPresses = 0;
    bool pendingBounce = false;
    bool heldInGoal = false;    // last update: the held cargo was being sucked
    Pellet* held = nullptr;     // last update's stick object (for suck-finish)
    std::set<Piki*> pressedFlight;  // one press per thrown Pikmin flight
    int taiState = -1;          // P1 Collec mStateID at bind (must never change)
    int taiChanges = 0;
    int attacksIgnored = 0;
    int attacksIgnoredPiki = 0, attacksIgnoredNavi = 0;  // backstop leak by attacker kind
    int targetSkips = 0;        // target selections refused (isLivingThing seam)
    std::set<std::string> skipSitesLogged;
    std::set<Pellet*> spared;   // carcasses released at the nest (equality only)
    int consumed = 0, sparedCount = 0;
    int eventsConsumed = 0;
    int presses = 0, pressesRejected = 0;
    int flyContactsRising = 0;  // thrown Pikmin that touched it while still rising (no press)
    bool hidden = false;
    float logTimer = 0.0f;
    float corpseTimer = 0.0f;
    float lastContestPiki = -1.0f;
    bool lastCanBack = true;
    float motionTimer = 0.0f;   // Damage/Dead/corpse motion diagnostics (read-only)
    bool motionValid = false;
    float motionX = 0.0f, motionZ = 0.0f;
};
std::map<BTeki*, Binding> s;

bb::Params sParams[kVariantCount];
bb::Bank sBank[kVariantCount] = {bb::defaultBank(), bb::defaultBank()};
std::vector<Shape*> sPoses[kVariantCount][bb::AnimCount];
bool sPosesLoaded[kVariantCount] = {false, false};
std::map<BTeki*, int> sDrawLogged;
// #972 interpolated presentation: one bank + per-actor private Shapes per variant.
p2posefamily::Bank sFamilyBank[kVariantCount] = {p2posefamily::Bank("BREADBUG"), p2posefamily::Bank("GIANT_BREADBUG")};
p2posefamily::Actors sFamilyVis[kVariantCount];
// #1022 lair model (PanHouse enemy.bmd), static; null when not staged.
Shape* sNest[kVariantCount] = {nullptr, nullptr};
bool sNestLogged[kVariantCount] = {false, false};

// Wall-clock milliseconds, so frame dumps (file mtimes) can be matched to markers.
long long wallMs() {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
}

Binding* find(const BTeki* t) {
    auto i = s.find(const_cast<BTeki*>(t));
    return i == s.end() ? nullptr : &i->second;
}

// #898 read-only motion diagnostics: what moves a Damage/Dead body or its
// corpse pellet? Logs the host velocities, the ground slip code, the captain
// and the nearest Pikmin (every 0.25 s in Damage/Dead, 1 s for the corpse).
// Never writes game state.
void logMotion(Binding& b, const char* phase, Creature* body, float dt, float period) {
    b.motionTimer += dt;
    if (b.motionTimer < period) return;
    b.motionTimer = 0.0f;
    const Vector3f p = body->mSRT.t;
    const float dx = b.motionValid ? p.x - b.motionX : 0.0f, dz = b.motionValid ? p.z - b.motionZ : 0.0f;
    b.motionValid = true;
    b.motionX = p.x;
    b.motionZ = p.z;
    int slip = -1, attr = -1;
    float ny = 0.0f;
    if (body->mGroundTriangle) {
        slip = MapCode::getSlipCode(body->mGroundTriangle);
        attr = MapCode::getAttribute(body->mGroundTriangle);
        ny = body->mGroundTriangle->mTriangle.mNormal.y;
    }
    float nd = -1.0f, nx = 0.0f, nz = 0.0f, nvx = 0.0f, nvz = 0.0f;
    if (naviMgr && naviMgr->getNavi()) {
        Navi* n = naviMgr->getNavi();
        nx = n->mSRT.t.x;
        nz = n->mSRT.t.z;
        nd = std::sqrt((nx - p.x) * (nx - p.x) + (nz - p.z) * (nz - p.z));
        nvx = n->mVelocity.x;
        nvz = n->mVelocity.z;
    }
    int near40 = 0, pd_state = -1, pd_mode = -1;
    float pd = 1e9f, pvx = 0.0f, pvz = 0.0f;
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* k = static_cast<Piki*>(*it);
            if (!k || !k->isAlive()) continue;
            const float kx = k->mSRT.t.x - p.x, kz = k->mSRT.t.z - p.z;
            const float d = std::sqrt(kx * kx + kz * kz);
            if (d < 40.0f) ++near40;
            if (d < pd) {
                pd = d;
                pd_state = k->getState();
                pd_mode = int(k->mMode);
                pvx = k->mVelocity.x;
                pvz = k->mVelocity.z;
            }
        }
    }
    std::printf("P2_BREADBUG_OWN_MOTION generator=%u source_id=%u phase=%s x=%.1f y=%.1f z=%.1f dx=%.1f dz=%.1f "
                "vel=%.1f,%.1f,%.1f drive=%.1f,%.1f vol=%.1f,%.1f slip=%d attr=%d ny=%.3f ground=%d "
                "navi_d=%.1f navi=%.0f,%.0f navi_vel=%.0f,%.0f piki_near40=%d piki_d=%.1f piki_state=%d piki_mode=%d "
                "piki_vel=%.0f,%.0f coll_vel=%d wall=%lld\n",
                b.generator, b.source, phase, p.x, p.y, p.z, dx, dz, body->mVelocity.x, body->mVelocity.y, body->mVelocity.z,
                body->mTargetVelocity.x, body->mTargetVelocity.z, body->mVolatileVelocity.x, body->mVolatileVelocity.z,
                slip, attr, ny, body->mGroundTriangle ? 1 : 0, nd, nx, nz, nvx, nvz, near40, pd < 1e8f ? pd : -1.0f,
                pd_state, pd_mode, pvx, pvz, int(body->mHasCollChangedVelocity), wallMs());
}

// P1 carry-route graph ('test' handle) as the source WayPoint graph; the
// synchronous path is a breadth-first search over the same links.
struct P1Route : bb::Route {
    int nearest(const bb::Vec3& p) const override {
        if (!routeMgr || routeMgr->getNumWayPoints('test') <= 0) return -1;
        WayPoint* wp = routeMgr->findNearestWayPoint('test', Vector3f(p.x, p.y, p.z), false);
        return wp ? wp->mIndex : -1;
    }
    bool nearestEdge(const bb::Vec3& p, int& a, int& b) const override {
        a = b = -1;
        if (!routeMgr || routeMgr->getNumWayPoints('test') <= 0) return false;
        WayPoint* s0 = nullptr;
        WayPoint* s1 = nullptr;
        // Land edges only (a hauled carcass is not floated), open ends only.
        routeMgr->findNearestEdge(&s0, &s1, 'test', Vector3f(p.x, p.y, p.z), false, true, false);
        if (!s0 || !s1) return false;
        a = s0->mIndex;
        b = s1->mIndex;
        return true;
    }
    bool get(int index, bb::WayPointInfo& out) const override {
        if (!routeMgr || index < 0 || index >= routeMgr->getNumWayPoints('test')) return false;
        WayPoint* wp = routeMgr->getWayPoint('test', index);
        if (!wp) return false;
        out = bb::WayPointInfo{};
        out.index = wp->mIndex;
        out.pos = {wp->mPosition.x, wp->mPosition.y, wp->mPosition.z};
        out.open = wp->mIsOpen;
        for (int l = 0; l < wp->mLinkCount && l < 8; ++l)
            if (wp->mLinkIndices[l] >= 0) out.links[out.linkCount++] = wp->mLinkIndices[l];
        return true;
    }
    bool path(int from, int to, std::vector<int>& out) const override {
        out.clear();
        if (!routeMgr) return false;
        const int n = routeMgr->getNumWayPoints('test');
        if (from < 0 || to < 0 || from >= n || to >= n) return false;
        std::vector<int> prev(std::size_t(n), -2);
        std::vector<int> queue{from};
        prev[std::size_t(from)] = -1;
        for (std::size_t q = 0; q < queue.size(); ++q) {
            const int cur = queue[q];
            if (cur == to) break;
            WayPoint* wp = routeMgr->getWayPoint('test', cur);
            if (!wp) continue;
            for (int l = 0; l < wp->mLinkCount && l < 8; ++l) {
                const int next = wp->mLinkIndices[l];
                if (next < 0 || next >= n || prev[std::size_t(next)] != -2) continue;
                WayPoint* nw = routeMgr->getWayPoint('test', next);
                if (!nw || (!nw->mIsOpen && next != to)) continue;  // PATHFLAG_RequireOpen
                prev[std::size_t(next)] = cur;
                queue.push_back(next);
            }
        }
        if (prev[std::size_t(to)] == -2) return false;
        for (int at = to; at != -1; at = prev[std::size_t(at)]) out.insert(out.begin(), at);
        return true;
    }
};
P1Route sRoute;

void loadParams(int v) {
    const Variant& var = kVariants[v];
    sParams[v] = bb::Params{};
    bb::applyVariant(sParams[v], var.giant);
    std::ifstream in(var.parms);
    std::string error;
    if (in && !bb::parseEnemyParm(in, sParams[v], error)) {
        std::printf("P2_BREADBUG_PARMS_INVALID source_id=%u reason=%s fallback=source_defaults\n", var.source, error.c_str());
        sParams[v] = bb::Params{};
        bb::applyVariant(sParams[v], var.giant);
    }
    const bb::Params& p = sParams[v];
    std::printf("P2_BREADBUG_PARMS source_id=%u giant=%d retail=%d health=%.1f move=%.1f search=%.1f angle=%.1f "
                "press=%.1f suck=%.1f carry=%.1f hide=%.1f wait=%.1f weight=%d walk_anim=%.2f "
                "carry_size_diff=%.0f slack=%.0f\n",
                var.source, p.giant ? 1 : 0, p.retail ? 1 : 0, p.health, p.moveSpeed, p.searchDistance,
                p.searchAngle, p.pressDamage, p.suckDamage, p.carrySpeed,
                p.hideTime, p.waitTime, p.maxCarryWeight, p.walkAnimSpeed, p.carrySizeDiff, p.waypointSlack);
}

// Pose bank with shared materials (Groink/tank pattern), bounded bytes.
Shape* loadShape(const std::string& rel, Shape*& shared, std::size_t& total) {
    const std::string path = "assets/dataDir/courses/pikmin2room/" + rel;
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file) return nullptr;
    const auto size = file.tellg();
    if (size <= 0 || size > 1024 * 1024 || total + std::size_t(size) > 24u * 1024 * 1024) return nullptr;
    total += std::size_t(size);
    file.seekg(0);
    std::vector<unsigned char> bytes(std::size_t(size), 0), resources;
    if (!file.read(reinterpret_cast<char*>(bytes.data()), size) || !p2animation::resources(bytes, resources)) return nullptr;
    Shape* shape = gameflow.loadShape(("courses/pikmin2room/" + rel).c_str(), true);
    if (!shape) return nullptr;
    if (!shared) {
        shared = shape;
        for (int t = 0; t < shape->mTexAttrCount; ++t)
            if (shape->mTexAttrList[t].mTexture) shape->mTexAttrList[t].mTexture->attach();
    } else {
        if (shape->mMaterialCount != shared->mMaterialCount || shape->mTexAttrCount != shared->mTexAttrCount
            || shape->mTevInfoCount != shared->mTevInfoCount) return nullptr;
        for (int j = 0; j < shape->mTotalMatpolyCount; ++j) {
            auto* poly = shape->mMatpolyList[j];
            if (!poly || !poly->mMaterial) continue;
            int material = -1;
            for (int m = 0; m < shape->mMaterialCount; ++m)
                if (poly->mMaterial == &shape->mMaterialList[m]) material = m;
            if (material < 0) return nullptr;
            poly->mMaterial = &shared->mMaterialList[material];
        }
        shape->mMaterialList = shared->mMaterialList;
        shape->mTexAttrList = shared->mTexAttrList;
        shape->mTevInfoList = shared->mTevInfoList;
    }
    return shape;
}

void loadBank(int v) {
    const Variant& var = kVariants[v];
    sBank[v] = bb::defaultBank();
    for (auto& poses : sPoses[v]) poses.clear();
    sPosesLoaded[v] = false;
    sFamilyBank[v].reset();
    sFamilyVis[v].clear();
    std::ifstream in(var.bank);
    std::string error;
    if (in && !bb::parseBank(in, sBank[v], error)) {
        std::printf("P2_BREADBUG_BANK_INVALID source_id=%u reason=%s fallback=builtin_timing draw=host\n", var.source, error.c_str());
        sBank[v] = bb::defaultBank();
    }
    int staged = 0;
    for (const auto& c : sBank[v].clip) staged += c.staged ? 1 : 0;
    // #972: the shared compact loader (few Shapes per clip = nearest-pose
    // fallback, decoded vectors for every pose = lerp + crossfade).
    p2poseload::Shared shared;
    std::size_t total = 0, poses = 0, slots = 0;
    bool ok = staged > 0;
    for (int a = 0; ok && a < bb::AnimCount; ++a) {
        const auto& clip = sBank[v].clip[a];
        if (!clip.staged) continue;
        std::string loadError;
        if (!p2posefamily::loadFamilyClip(sFamilyBank[v], clip.name, std::string(var.posePrefix) + "_" + clip.name,
                                          int(clip.poses.size()), clip.frames, clip.poses, shared, total,
                                          sPoses[v][a], loadError)) {
            std::printf("P2_BREADBUG_BANK_INVALID source_id=%u clip=%s reason=%s fallback=host\n", var.source,
                        clip.name.c_str(), loadError.c_str());
            ok = false;
            break;
        }
        poses += clip.poses.size();
        std::set<Shape*> distinct(sPoses[v][a].begin(), sPoses[v][a].end());
        slots += distinct.size();
    }
    if (!ok) {
        for (auto& list : sPoses[v]) list.clear();
        sFamilyBank[v].reset();
    }
    sPosesLoaded[v] = ok && poses > 0;
    {   // #1022: the lair model staged next to the poses (optional).
        Shape* nestShared = nullptr;
        std::size_t nestBytes = 0;
        sNest[v] = loadShape(std::string(var.posePrefix) + "_nest.mod", nestShared, nestBytes);
        std::printf("P2_BREADBUG_NEST source_id=%u model=%s bytes=%zu scale=%.2f\n", var.source,
                    sNest[v] ? "panhouse" : "none", sNest[v] ? nestBytes : std::size_t(0),
                    p2breadbugnest::scale(sParams[v].nestScale));
    }
    std::printf("P2_BREADBUG_BANK source_id=%u staged_clips=%d poses=%zu shape_slots=%zu resident_bytes=%zu "
                "interpolation_clips=%zu draw=%s\n", var.source, staged, sPosesLoaded[v] ? poses : std::size_t(0),
                sPosesLoaded[v] ? slots : std::size_t(0), total, sFamilyBank[v].clipCount(),
                sPosesLoaded[v] ? "p2_model" : "host");
}

std::uint64_t idOf(const Pellet* p) { return static_cast<std::uint64_t>(reinterpret_cast<std::uintptr_t>(p)); }

float pikiStrength(Pellet* p) {
    float sum = 0.0f;
    Stickers stuck(p);
    Iterator it(&stuck);
    CI_LOOP(it) {
        Creature* c = *it;
        if (c && c->isPiki()) sum += float(pc_piki_carry_strength(static_cast<Piki*>(c)));
    }
    return sum;
}

bool otherTekiStuck(Pellet* p, const BTeki* self) {
    Stickers stuck(p);
    Iterator it(&stuck);
    CI_LOOP(it) {
        Creature* c = *it;
        if (c && c->isTeki() && c != self) return true;
    }
    return false;
}

int sPelletsAlive = 0;
float sPelletNearest = -1.0f;
void snapshot(BTeki* t, const Binding& b, std::vector<bb::PelletInfo>& out, std::vector<Pellet*>& who) {
    out.clear();
    who.clear();
    sPelletsAlive = 0;
    sPelletNearest = -1.0f;
    if (!pelletMgr) return;
    const Vector3f me = t->getPosition();
    Iterator it(pelletMgr);
    CI_LOOP(it) {
        Pellet* p = static_cast<Pellet*>(*it);
        if (!p || !p->isAlive() || !p->mConfig) continue;
        const Vector3f& pos = p->mSRT.t;
        const float dx = pos.x - me.x, dz = pos.z - me.z;
        ++sPelletsAlive;
        if (sPelletNearest < 0.0f || std::sqrt(dx * dx + dz * dz) < sPelletNearest) sPelletNearest = std::sqrt(dx * dx + dz * dz);
        if (dx * dx + dz * dz > 1000.0f * 1000.0f && t->getStickObject() != p) continue;
        bb::PelletInfo info;
        info.id = idOf(p);
        info.pos = {pos.x, pos.y, pos.z};
        // findNearestPellet compares the pellet's base with the Breadbug's
        // feet (retail: centre - 0.5 * cylinder height). A P1 pellet's origin
        // already is its base (Pellet::update puts the life gauge at
        // mSRT.t.y + height + 5), so the base is mSRT.t.y itself.
        info.bottomY = pos.y;
        info.radius = p->getBottomRadius();
        info.carryMin = p->mConfig->mCarryMinPikis();
        info.carryMax = p->mConfig->mCarryMaxPikis();
        if (info.carryMax < info.carryMin) info.carryMax = info.carryMin;
        info.pikiStrength = pikiStrength(p);
        info.alive = p->isAlive();
        info.inGoal = p->getState() == PELSTATE_Goal;
        // panmodokiCarryable + P1 exclusions: UFO parts, captains, pellets in
        // the goal / swallowed, pellets held in a mouth.
        info.captured = p->mStuckMouthPart != nullptr;
        info.pickable = !p->isUfoParts() && !p->mConfig->mModelId.match('NAVI') && !info.inGoal
                     && p->getState() != PELSTATE_Swallowed && p->getState() != PELSTATE_Dead
                     && !b.spared.count(p);  // #898: a carcass this Breadbug spared stays spared
        info.otherTekiStuck = otherTekiStuck(p, t);
        info.carcass = p->mPelletView != nullptr;
        info.slotFree = true;
        info.velocity = {p->mVelocity.x, p->mVelocity.y, p->mVelocity.z};
        out.push_back(info);
        who.push_back(p);
    }
}

Pellet* pelletFor(const std::vector<bb::PelletInfo>& infos, const std::vector<Pellet*>& who, std::uint64_t id) {
    for (std::size_t i = 0; i < infos.size(); ++i) if (infos[i].id == id) return who[i];
    return nullptr;
}

void logState(const Binding& b, bb::State from, bb::State to, BTeki* t) {
    const Vector3f p = t->getPosition();
    std::printf("P2_BREADBUG_OWN_STATE generator=%u source_id=%u from=%s to=%s x=%.1f z=%.1f health=%.1f wall=%lld\n",
                b.generator, b.source, bb::stateName(from), bb::stateName(to), p.x, p.z, b.fsm.health(), wallMs());
}

void setHidden(BTeki* t, Binding& b, bool hidden) {
    if (hidden == b.hidden) return;
    b.hidden = hidden;
    if (hidden) t->clearTekiOption(TEKIOPT_Atari | TEKIOPT_ShadowVisible);
    else t->setTekiOption(TEKIOPT_Atari | TEKIOPT_ShadowVisible);
}

// #898 fix: the source PelletCarry (FSM) decides the tug; the P1 pellet must
// follow it exactly. P1 Pellet::doCarry arbitrates by sticker count with a
// 3.5 s ownership swap, and the Pikmin pass numStickers, which counts the
// Breadbug itself: a Breadbug presenting crew+1 tied them, and the two sides
// swapped ownership every 3.5 s pulling opposite ways (g2: 5-6 carriers vs a
// winning Breadbug, 20 minutes of stalemate). So while the FSM says the
// Breadbug owns the cargo it is written as the carrier directly, with a count
// no Pikmin crew can exceed; when the FSM says the Pikmin won, or the
// Breadbug lets go, its ownership is cleared so the Pikmin carry at once.
void ownCargo(Pellet* p, BTeki* t, float vx, float vz) {
    p->mPikiCarrier = t;
    p->mCarrierCount = 0xFFFF;
    p->mCarryState = 2;
    p->mTransitionTimer = 0.0f;
    p->mCarryDirection.set(vx, 0.0f, vz);
}
void yieldCargo(Pellet* p, BTeki* t) {
    if (!p || p->mPikiCarrier != t) return;
    p->mPikiCarrier = nullptr;
    p->mCarrierCount = 0;
    p->mCarryState = 0;
    p->mTransitionTimer = 0.0f;
    p->mCarryDirection.set(0.0f, 0.0f, 0.0f);
}

// Kill the Pikmin still stuck to a consumed cargo (endCarry InteractKill),
// then the cargo itself (P1 Collec putting recipe: InteractKill).
void consumeCargo(BTeki* t, Binding& b, Pellet* p) {
    int killed = 0;
    {
        Stickers stuck(p);
        Iterator it(&stuck);
        CI_LOOP(it) {
            Creature* c = *it;
            if (c && c->isPiki() && c->isAlive()) {
                c->stimulate(InteractKill(t, 0));
                ++killed;
                it.dec();
            }
        }
    }
    yieldCargo(p, t);
    if (t->getStickObject() == p) p->endStickTeki(t);
    const bool carcass = p->mPelletView != nullptr;
    // #898 fix: a teki carcass is spared, never destroyed (consumeOutcome):
    // released at the nest, still carriable, never re-picked by this
    // Breadbug. Plain pellets are eaten (retail endCarry). The bound source
    // is logged to show which delivery check the spare preserved.
    const unsigned boundSource = carcass ? pc_randomizer_p2_source_for(p->mPelletView) : 0u;
    const unsigned boundGen = carcass ? pc_randomizer_p2_generator_for(p->mPelletView) : 0u;
    const bool destroy = bb::consumeOutcome(carcass) == bb::ConsumeOutcome::Destroy;
    if (destroy) {
        p->stimulate(InteractKill(t, 0));
        ++b.consumed;
    } else {
        p->mVelocity.x = p->mVelocity.z = 0.0f;
        b.spared.insert(p);
        ++b.sparedCount;
    }
    std::printf("P2_BREADBUG_OWN_CONSUME generator=%u source_id=%u cargo_carcass=%d cargo_bound_source=%u "
                "cargo_generator=%u destroyed=%d spared=%s pikmin_killed=%d pellet_alive_after=%d wall=%lld\n",
                b.generator, b.source, carcass ? 1 : 0, boundSource, boundGen, destroy ? 1 : 0,
                destroy ? "no" : (boundSource ? "carcass_check_bound" : "carcass"), killed, p->isAlive() ? 1 : 0, wallMs());
}

bool ownTick(BTeki* t, Binding& b, float dt) {
    // doAI tail the suppressed strategy no longer runs: gravity, life gauge.
    if (t->getTekiOption(TEKIOPT_Gravitatable)) t->gravitate(t->getGravity());
    // The P1 Collec TAI must stay frozen (negative evidence).
    if (t->mStateID != b.taiState) {
        ++b.taiChanges;
        std::printf("P2_BREADBUG_OWN_TAI_TRANSITION generator=%u source_id=%u from=%d to=%d\n",
                    b.generator, b.source, b.taiState, int(t->mStateID));
        b.taiState = t->mStateID;
    }
    // Stored damage reaches mStoredDamage only through InteractBomb (ordinary
    // attacks are refused at InteractAttack::actTeki): EnemyBase::bombCallBack.
    const float external = t->mStoredDamage > 0.0f ? t->mStoredDamage : 0.0f;
    t->mStoredDamage = 0.0f;
    // Prune the per-flight press memory once a Pikmin is no longer flying.
    for (auto it = b.pressedFlight.begin(); it != b.pressedFlight.end();) {
        if (!*it || !(*it)->isAlive() || (*it)->getState() != PIKISTATE_Flying) it = b.pressedFlight.erase(it);
        else ++it;
    }
    const int ticks = b.clock.step(double(dt), true);
    if (ticks <= 0) {
        if (external > 0.0f) t->mStoredDamage += external;  // keep for the next source update
        return false;
    }
    std::vector<bb::PelletInfo> infos;
    std::vector<Pellet*> who;
    bool kill = false;
    for (int k = 0; k < ticks && !kill; ++k) {
        snapshot(t, b, infos, who);
        Creature* stick = t->getStickObject();
        Pellet* held = stick && stick->isObjType(OBJTYPE_Pellet) ? static_cast<Pellet*>(stick) : nullptr;
        bb::TickInput in;
        const Vector3f pos = t->getPosition();
        in.position = {pos.x, pos.y, pos.z};
        in.externalDamage = k == 0 ? external : 0.0f;
        in.presses = k == 0 ? b.pendingPresses : 0;
        in.bounced = k == 0 && b.pendingBounce;
        // InteractSuckFinish: the cargo we held while it was in the Onion goal
        // is gone (PelletGoalState::exec kills it and frees its stickers).
        in.suckFinished = b.held && b.heldInGoal && held != b.held;
        in.held = held ? idOf(held) : 0;
        in.pellets = infos.data();
        in.count = infos.size();
        in.route = &sRoute;
        const bb::State before = b.fsm.state();
        const float hpBefore = b.fsm.health();
        const bb::TickOutput o = b.fsm.tick(in);
        if (!o.valid) break;
        if (in.suckFinished)
            std::printf("P2_BREADBUG_OWN_SUCKED generator=%u source_id=%u health=%.1f\n", b.generator, b.source, hpBefore);
        if (k == 0) {
            b.presses += in.presses;
            b.pendingPresses = 0;
            b.pendingBounce = false;
        }
        bb::State shown = before;
        for (bb::State e : o.entered) {
            logState(b, shown, e, t);
            shown = e;
            // P1 approximation of the source PSSE keys (output-only, #946).
            switch (e) {
            case bb::State::Pulled: pc_p2_sfx(b.source, b.generator, p2sfx::Event::Pull, t); break;
            case bb::State::Stick: pc_p2_sfx(b.source, b.generator, p2sfx::Event::Attack, t); break;
            case bb::State::Damage: pc_p2_sfx(b.source, b.generator, p2sfx::Event::Damage, t); break;
            case bb::State::Dead: pc_p2_sfx(b.source, b.generator, p2sfx::Event::Dead, t); break;
            case bb::State::Appear: pc_p2_sfx(b.source, b.generator, p2sfx::Event::Land, t); break;
            default: break;
            }
            if (e == bb::State::Pulled)
                std::printf("P2_BREADBUG_OWN_PULLED generator=%u source_id=%u carriers=%.1f self=%.1f\n",
                            b.generator, b.source, o.contestPiki, o.contestSelf);
            if (e == bb::State::Dead && !b.deadLogged) {
                b.deadLogged = true;
                std::printf("P2_BREADBUG_OWN_DEAD generator=%u source_id=%u health=%.1f wall=%lld\n", b.generator, b.source, b.fsm.health(), wallMs());
            }
        }
        if (o.damageKind != bb::DamageKind::None) {
            if (o.hpAfter < o.hpBefore && o.hpAfter > 0.0f)
                pc_p2_sfx(b.source, b.generator, p2sfx::Event::Damage, t);
            const char* kind = o.damageKind == bb::DamageKind::Press ? "P2_BREADBUG_OWN_PRESS"
                             : o.damageKind == bb::DamageKind::Suck ? "P2_BREADBUG_OWN_SUCK_DAMAGE"
                                                                     : "P2_BREADBUG_OWN_EXTERNAL_DAMAGE";
            std::printf("%s generator=%u source_id=%u hp_before=%.1f hp_after=%.1f state_before=%s wall=%lld\n", kind,
                        b.generator, b.source, o.hpBefore, o.hpAfter, bb::stateName(before), wallMs());
        }
        if (o.pressRejected) {
            ++b.pressesRejected;
            std::printf("P2_BREADBUG_OWN_PRESS_IGNORED generator=%u source_id=%u state=%s\n", b.generator, b.source,
                        bb::stateName(b.fsm.state()));
        }
        if (o.backStuckSkip)
            std::printf("P2_BREADBUG_OWN_BACK_STUCK generator=%u source_id=%u action=skip_node x=%.1f z=%.1f wall=%lld\n",
                        b.generator, b.source, t->getPosition().x, t->getPosition().z, wallMs());
        if (o.backStuckRelease) {
            // Never re-pick the cargo it could not haul (no grab/wedge loop).
            if (held) b.spared.insert(held);
            std::printf("P2_BREADBUG_OWN_BACK_STUCK generator=%u source_id=%u action=release x=%.1f z=%.1f wall=%lld\n",
                        b.generator, b.source, t->getPosition().x, t->getPosition().z, wallMs());
        }
        if (o.refilled)
            std::printf("P2_BREADBUG_OWN_HIDE_REFILL generator=%u source_id=%u health=%.1f\n", b.generator, b.source, b.fsm.health());
        // Commands.
        if (o.release && held) {
            if (o.releaseReverse) { held->mVelocity.x = -held->mVelocity.x; held->mVelocity.z = -held->mVelocity.z; }
            yieldCargo(held, t);
            held->endStickTeki(t);
            std::printf("P2_BREADBUG_OWN_RELEASE generator=%u source_id=%u reverse=%d\n", b.generator, b.source, o.releaseReverse ? 1 : 0);
            held = nullptr;
        }
        if (o.stickTo) {
            Pellet* p = pelletFor(infos, who, o.stickTo);
            const bool ok = p && p->startStickTeki(t, 1.0f + t->getTekiCollisionSize());
            std::printf("P2_BREADBUG_OWN_STICK generator=%u source_id=%u ok=%d carcass=%d carry_min=%d carry_max=%d "
                        "strength=%.1f carriers=%.1f\n",
                        b.generator, b.source, ok ? 1 : 0, p && p->mPelletView ? 1 : 0, p ? int(p->mConfig->mCarryMinPikis()) : 0,
                        p ? int(p->mConfig->mCarryMaxPikis()) : 0, b.fsm.carryStrength(), p ? pikiStrength(p) : 0.0f);
            if (ok) held = p;
        }
        if (held && o.stopCargo) { held->mVelocity.x = 0.0f; held->mVelocity.z = 0.0f; }
        if (held && o.contest) {
            // The source PelletCarry decided the tug (see ownCargo).
            if (o.pulled) ownCargo(held, t, o.pullVelocity.x, o.pullVelocity.z);
            else if (!o.canBack) yieldCargo(held, t);
            if (o.contestPiki != b.lastContestPiki || o.canBack != b.lastCanBack) {
                b.lastContestPiki = o.contestPiki;
                b.lastCanBack = o.canBack;
                std::printf("P2_BREADBUG_OWN_CONTEST generator=%u source_id=%u carriers=%.1f self=%.1f breadbug_wins=%d state=%s\n",
                            b.generator, b.source, o.contestPiki, o.contestSelf, o.canBack ? 1 : 0, bb::stateName(b.fsm.state()));
            }
        }
        if (held && o.holdCargo) {
            // CarryEnd/Hide: the cargo is in the mouth (updateCaptureMatrix);
            // the home nudge moves the cargo and the Breadbug riding it.
            ownCargo(held, t, 0.0f, 0.0f);
            held->mVelocity.x = held->mVelocity.z = 0.0f;
            held->mSRT.t.x += o.homeNudge.x;
            held->mSRT.t.z += o.homeNudge.z;
        } else if (!held && (o.homeNudge.x != 0.0f || o.homeNudge.z != 0.0f)) {
            Vector3f p = t->getPosition();
            p.x += o.homeNudge.x;
            p.z += o.homeNudge.z;
            t->mSRT.t = p;
        }
        if (o.consumeCargo && held) {
            consumeCargo(t, b, held);
            held = nullptr;
        }
        b.heldInGoal = held && held->getState() == PELSTATE_Goal;
        b.held = held;
        setHidden(t, b, o.hidden);
        // Movement/facing (free Breadbug only; a stuck one rides its cargo).
        if (!held) {
            t->setDirection(o.faceDir);
            const Vector3f drive(o.velocity.x, 0.0f, o.velocity.z);
            t->inputDrive(drive);
            t->mVelocity.x = drive.x;
            t->mVelocity.z = drive.z;
        } else {
            t->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
        }
        t->mHealth = b.fsm.health();
        kill = o.killRequest;
    }
    // Footsteps while walking / hauling (Collec stride, output-only).
    if (b.fsm.state() == bb::State::Walk || b.fsm.state() == bb::State::Back)
        pc_p2_sfx_stride(b.source, b.generator, t, 22.0f);
    if (t->mHealth > 0.0f) t->updateLifeGauge();
    if (b.fsm.state() == bb::State::Damage || b.fsm.state() == bb::State::Dead)
        logMotion(b, bb::stateName(b.fsm.state()), t, dt, 0.25f);
    b.logTimer += dt;
    if (b.logTimer >= 1.0f) {
        b.logTimer = 0.0f;
        const Vector3f p = t->getPosition();
        const bb::Vec3& wp = b.fsm.nextWayPoint();
        if (b.held) {
            // Haul diagnostics (read-only): is the cargo driven, grounded, moving?
            Pellet* c = b.held;
            std::printf("P2_BREADBUG_OWN_HAUL generator=%u source_id=%u state=%s cargo=%.1f,%.1f,%.1f vel=%.1f,%.1f,%.1f "
                        "dir=%.1f,%.1f carrier_self=%d carry_state=%d ground=%d pellet_state=%d pick=%.1f crew=%.1f "
                        "min=%d next=%.1f,%.1f pathfinding=%d path_len=%zu\n",
                        b.generator, b.source, bb::stateName(b.fsm.state()), c->mSRT.t.x, c->mSRT.t.y, c->mSRT.t.z,
                        c->mVelocity.x, c->mVelocity.y, c->mVelocity.z, c->mCarryDirection.x, c->mCarryDirection.z,
                        c->mPikiCarrier == t ? 1 : 0, int(c->mCarryState), c->onGround() ? 1 : 0, c->getState(),
                        c->getPickOffset(), pikiStrength(c), int(c->mConfig->mCarryMinPikis()), wp.x, wp.z, b.fsm.pathfinding() ? 1 : 0,
                        b.fsm.pathLength());
        }
        std::printf("P2_BREADBUG_OWN_POS generator=%u source_id=%u state=%s anim=%d frame=%.0f x=%.1f z=%.1f "
                    "home=%.1f,%.1f next=%.1f,%.1f health=%.1f target=%d held=%d pellets=%zu tai_changes=%d "
                    "attacks_ignored=%d target_skips=%d consumed=%d spared=%d events_consumed=%d presses=%d fly_rising=%d "
                    "pellets_alive=%d nearest_pellet=%.0f wall=%lld\n",
                    b.generator, b.source, bb::stateName(b.fsm.state()), b.fsm.animator().anim(), b.fsm.animator().frame(),
                    p.x, p.z, b.fsm.home().x, b.fsm.home().z, wp.x, wp.z, b.fsm.health(), b.fsm.target() ? 1 : 0,
                    b.held ? 1 : 0, infos.size(), b.taiChanges, b.attacksIgnored, b.targetSkips, b.consumed,
                    b.sparedCount, b.eventsConsumed, b.presses,
                    b.flyContactsRising, sPelletsAlive, sPelletNearest, wallMs());
    }
    std::fflush(stdout);
    if (kill && !b.escaped) {
        // Dead KEYEVENT_END -> kill(): the host death funnel (die + dieSoon)
        // births the LeaveCorpse pellet; dieSoon only runs inside the
        // suppressed doAI, hence pcEscapeNow (Groink/long-legs pattern).
        b.escaped = true;
        if (Creature* stick = t->getStickObject())
            if (stick->isObjType(OBJTYPE_Pellet)) {
                yieldCargo(static_cast<Pellet*>(stick), t);
                static_cast<Pellet*>(stick)->endStickTeki(t);
            }
        setHidden(t, b, false);
        t->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
        t->mVelocity.x = t->mVelocity.z = 0.0f;
        std::printf("P2_BREADBUG_OWN_ESCAPE generator=%u source_id=%u native=host_escape_now tai_changes=%d "
                    "attacks_ignored=%d attacks_ignored_piki=%d attacks_ignored_navi=%d target_skips=%d presses=%d "
                    "presses_rejected=%d presses_rejected_nonpurple=%d consumed=%d spared=%d\n",
                    b.generator, b.source, b.taiChanges, b.attacksIgnored, b.attacksIgnoredPiki, b.attacksIgnoredNavi,
                    b.targetSkips, b.presses, b.pressesRejected, b.pressesRejectedKind, b.consumed, b.sparedCount);
        std::fflush(stdout);
        t->pcEscapeNow();
        return true;
    }
    return false;
}
} // namespace

namespace { bool sLoaded[kVariantCount] = {false, false}; bool sCensusDone = false; } // staged parms/bank loaded for this scene

void pc_p2_breadbug_teki_reset() {
    s.clear();
    sDrawLogged.clear();
    for (int v = 0; v < kVariantCount; ++v) {
        sFamilyBank[v].reset();
        sFamilyVis[v].clear();
        sNest[v] = nullptr;
        sNestLogged[v] = false;
    }
    for (auto& variant : sPoses)
        for (auto& poses : variant) poses.clear();
    for (bool& loaded : sPosesLoaded) loaded = false;
    for (bool& loaded : sLoaded) loaded = false;
    sCensusDone = false;
}

void pc_p2_breadbug_teki_forget(BTeki* t) {
    if (!t) return;
    auto i = s.find(t);
    if (i == s.end()) return;
    std::printf("P2_BREADBUG_OWN_FORGET generator=%u source_id=%u dead_state=%d\n", i->second.generator, i->second.source, t->mDeadState);
    std::fflush(stdout);
    s.erase(i);
    sDrawLogged.erase(t);
    for (auto& vis : sFamilyVis) vis.forget(t);
}

bool pc_p2_breadbug_teki_is_bound(const BTeki* t) { return t && find(t); }

bool pc_p2_breadbug_teki_suppress_ai(const BTeki* t) {
    const Binding* b = find(t);
    return b && !b->escaped;
}

namespace {
void ensureLoaded(int v) {
    if (sLoaded[v]) return;
    sLoaded[v] = true;
    loadParams(v);
    loadBank(v);
    if (sCensusDone) return;
    sCensusDone = true;
    // One-shot census of the stage's pellets (read-only diagnosis of
    // what a wandering Breadbug can find; fp14 search is 500).
    if (pelletMgr) {
        Iterator pit(pelletMgr);
        CI_LOOP(pit) {
            Pellet* p = static_cast<Pellet*>(*pit);
            if (!p || !p->isAlive() || !p->mConfig) continue;
            std::printf("P2_BREADBUG_OWN_PELLET_CENSUS model=%s min=%d max=%d x=%.0f y=%.0f z=%.0f ufo=%d state=%d\n",
                        p->mConfig->mModelId.mStringID, int(p->mConfig->mCarryMinPikis()),
                        int(p->mConfig->mCarryMaxPikis()), p->mSRT.t.x, p->mSRT.t.y, p->mSRT.t.z,
                        p->isUfoParts() ? 1 : 0, p->getState());
        }
    }
}

// Bind one Breadbug-family actor (source 38 Breadbug or 40 Giant Breadbug): setup
// loop body; also the dev-console late binder (#942).
bool bindOne(Teki* t) {
    const unsigned src = pc_p2_campaign_source(t);
    const int v = variantOf(src);
    if (v < 0) return false;
    const unsigned gen = pc_p2_campaign_token(t);
    if (t->mTekiType != TEKI_Collec) {
        std::printf("P2_SETUP_SKIP Breadbug host_type_mismatch source_id=%u generator=%u type=%d\n", src, gen, t->mTekiType);
        return false;
    }
    if (t->getParameterI(TPI_CorpseType) != TEKICORPSE_LeaveCorpse) {
        std::printf("P2_SETUP_SKIP Breadbug no_corpse source_id=%u generator=%u\n", src, gen);
        return false;
    }
    ensureLoaded(v);
    Binding& b = s[static_cast<BTeki*>(t)];
    b = Binding{};
    b.generator = gen;
    b.source = src;
    b.variant = v;
    const Vector3f pos = t->getPosition();
    b.fsm.init(sParams[v], sBank[v], {pos.x, pos.y, pos.z}, t->getDirection(), (gen * 2654435761u) | 1u, &sRoute);
    b.nestY = pos.y;
    b.nestYaw = t->getDirection();
    t->mHealth = b.fsm.health();
    b.taiState = t->mStateID;
    // Retail PanModoki is not a living thing while unbittered (isLivingThing).
    // Clearing ORGANIC only stops the organic-gated P1 paths (thrown stick,
    // formation contact, captain punch entry); it does NOT stop P1 ground
    // attacks. Every P1 target-selection site asks
    // pc_p2_breadbug_teki_untargetable() instead (#898 fix).
    t->clearTekiOption(TEKIOPT_Organic);
    std::printf("P2_BREADBUG_OWN_BIND generator=%u source_id=%u host_type=%d health=%.1f retail_parms=%d draw=%s "
                "home=%.1f,%.1f wp=%d state=%s tai_state=%d\n",
                gen, src, t->mTekiType, t->mHealth, sParams[v].retail ? 1 : 0, sPosesLoaded[v] ? "p2_model" : "host", pos.x,
                pos.z, sRoute.nearest({pos.x, pos.y, pos.z}), bb::stateName(b.fsm.state()), b.taiState);
    // Ordinary-delivery bridge: GoalItem::suckMe grants onion:p2:<source> once
    // for the delivered corpse of THIS generator token.
    pc_randomizer_p2_bind_source(static_cast<PelletView*>(static_cast<BTeki*>(t)), src, gen);
    std::printf("P2_BREADBUG_DELIVERY_BIND generator=%u source_id=%u\n", gen, src);
    std::fflush(stdout);
    return true;
}
} // namespace

void pc_p2_breadbug_teki_setup() {
    pc_p2_breadbug_teki_reset();
    if (!pc_randomizer_p2_bridge() || !tekiMgr) return;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        auto* t = static_cast<Teki*>(*it);
        if (!t || !t->mGenerator || variantOf(pc_p2_campaign_source(t)) < 0) continue;
        bindOne(t);
    }
}

bool pc_p2_breadbug_teki_bind_dynamic(BTeki* t) {
    if (!t || !tekiMgr || !t->mGenerator || !pc_randomizer_p2_bridge() || variantOf(pc_p2_campaign_source(t)) < 0)
        return false;
    if (s.count(t)) return true;
    return bindOne(static_cast<Teki*>(t));
}

void pc_p2_breadbug_teki_tick(BTeki* t) {
    auto i = s.find(t);
    if (i == s.end()) return;
    Binding& b = i->second;
    const float dt = gsys ? gsys->getFrameTime() : 0.0f;
    if (!b.escaped && t->mDeadState == 0) {
        if (!(dt > 0.0f && dt < 0.5f)) return;
        ownTick(t, b, dt);  // may run the host teardown; never touch b after a kill
        return;
    }
    if (!b.escaped && t->mDeadState == 1) {
        // Something outside the FSM called die(): finish the teardown so the
        // corpse pelletizes (dieSoon only runs in the suppressed doAI).
        b.escaped = true;
        std::printf("P2_BREADBUG_OWN_ESCAPE generator=%u source_id=%u native=host_die_external\n", b.generator, b.source);
        std::fflush(stdout);
        t->pcEscapeNow();
        return;
    }
    // Corpse phase: observe the carcass carry (read-only).
    if (t->mPellet && t->mPellet->isAlive()) {
        Pellet* c = t->mPellet;
        if (!b.corpseLogged) {
            b.corpseLogged = true;
            std::printf("P2_BREADBUG_OWN_CORPSE generator=%u source_id=%u x=%.1f z=%.1f carry_min=%d carry_max=%d\n",
                        b.generator, b.source, c->mSRT.t.x, c->mSRT.t.z, int(c->mConfig->mCarryMinPikis()),
                        int(c->mConfig->mCarryMaxPikis()));
        }
        logMotion(b, "corpse", c, dt, 1.0f);
        if (dt > 0.0f && dt < 0.5f) {  // presentation clock only (type5 loop)
            const bb::Clip& carry = sBank[b.variant].clip[bb::AnimCarry];
            if (!b.corpseAnimStarted && carry.staged) {
                b.corpseAnim.start(&carry, bb::AnimCarry);
                b.corpseAnim.setFrame(p2breadbugcorpse::kHoldFrame);
                b.corpseAnimStarted = true;
            }
            if (b.corpseAnimStarted) b.corpseAnim.animate(dt);
        }
        b.corpseTimer += dt;
        if (b.corpseTimer >= 2.0f) {
            b.corpseTimer = 0.0f;
            std::printf("P2_BREADBUG_OWN_CORPSE_CARRY generator=%u source_id=%u x=%.1f z=%.1f carriers=%.1f state=%d wall=%lld\n",
                        b.generator, b.source, c->mSRT.t.x, c->mSRT.t.z, pikiStrength(c), c->getState(), wallMs());
        }
        std::fflush(stdout);
    }
}

bool pc_p2_breadbug_teki_event(BTeki* t, const TekiEvent& event) {
    Binding* b = find(t);
    if (!b || b->escaped) return false;
    ++b->eventsConsumed;
    if (event.mEventType == TekiEventType::Ground) {
        b->pendingBounce = true;
        t->mActionVelocity.y = 0.0f;  // landed: gravitate's fall speed resets
        return true;
    }
    if (event.mEventType == TekiEventType::Entity && event.mOther && event.mOther->isPiki()) {
        // PikiFlyingState::collisionCallback (pikiState.cpp:2322-2330): a
        // thrown Pikmin touching the enemy while falling sends InteractPress.
        Piki* piki = static_cast<Piki*>(event.mOther);
        if (piki->isAlive() && piki->getState() == PIKISTATE_Flying && piki->mVelocity.y >= 0.0f
            && !b->pressedFlight.count(piki)) {
            ++b->flyContactsRising;  // rising contact: retail sends no press (vel.y < 0 only)
        }
        if (piki->isAlive() && piki->getState() == PIKISTATE_Flying && piki->mVelocity.y < 0.0f
            && !b->pressedFlight.count(piki) && b->fsm.params().giant && !pc_p2_is_purple(piki)) {
            // OoPanModoki::Obj::pressCallBack (panModoki.cpp:1738-1744): a press
            // by a non-Purple Pikmin returns false before the base class runs,
            // so no Damage transition and no health change.
            b->pressedFlight.insert(piki);
            ++b->pressesRejectedKind;
            if (b->pressesRejectedKind <= 5 || b->pressesRejectedKind % 50 == 0)
                std::printf("P2_BREADBUG_OWN_PRESS_REJECTED generator=%u source_id=%u reason=non_purple count=%d state=%s wall=%lld\n",
                            b->generator, b->source, b->pressesRejectedKind, bb::stateName(b->fsm.state()), wallMs());
            std::fflush(stdout);
        }
        if (piki->isAlive() && piki->getState() == PIKISTATE_Flying && piki->mVelocity.y < 0.0f
            && !b->pressedFlight.count(piki)) {
            b->pressedFlight.insert(piki);
            ++b->pendingPresses;
            std::printf("P2_BREADBUG_OWN_PRESS_CONTACT generator=%u source_id=%u vy=%.1f state=%s wall=%lld\n", b->generator, b->source,
                        piki->mVelocity.y, bb::stateName(b->fsm.state()), wallMs());
            std::fflush(stdout);
        }
    }
    return true;  // the P1 Collec TAI never sees an OWN Breadbug's events
}

bool pc_p2_breadbug_teki_attack(BTeki* t, const Creature* attacker, float damage) {
    Binding* b = find(t);
    if (!b || b->escaped) return false;
    ++b->attacksIgnored;
    const char* kind = "other";
    int action = -1, state = -1;
    if (attacker && attacker->mObjType == OBJTYPE_Piki) {
        kind = "piki";
        ++b->attacksIgnoredPiki;
        Piki* pk = static_cast<Piki*>(const_cast<Creature*>(attacker));
        state = pk->getState();
        action = pk->mActiveAction ? pk->mActiveAction->mCurrActionIdx : -1;
    } else if (attacker && attacker->mObjType == OBJTYPE_Navi) {
        kind = "navi";
        ++b->attacksIgnoredNavi;
    }
    if (b->attacksIgnored <= 5 || b->attacksIgnored % 50 == 0)
        std::printf("P2_BREADBUG_OWN_ATTACK_IGNORED generator=%u source_id=%u attacker=%s piki_state=%d piki_action=%d "
                    "damage=%.1f health=%.1f count=%d\n",
                    b->generator, b->source, kind, state, action, damage, b->fsm.health(), b->attacksIgnored);
    std::fflush(stdout);
    return true;
}

bool pc_p2_breadbug_teki_untargetable(const Creature* c, const char* site) {
    if (!c || c->mObjType != OBJTYPE_Teki) return false;
    BTeki* t = static_cast<BTeki*>(const_cast<Creature*>(c));
    Binding* b = find(t);
    if (!b || b->escaped || t->mDeadState != 0) return false;
    // The port has no bitter spray: a bound Breadbug is always unbittered.
    constexpr bool bittered = false;
    if (bb::isLivingThing(bittered, b->fsm.health() > 0.0f)) return false;
    ++b->targetSkips;
    const std::string where = site ? site : "?";
    if (b->skipSitesLogged.insert(where).second) {
        std::printf("P2_BREADBUG_OWN_TARGET_SKIP generator=%u source_id=%u site=%s living=0 bittered=0 count=%d wall=%lld\n",
                    b->generator, b->source, where.c_str(), b->targetSkips, wallMs());
        std::fflush(stdout);
    }
    return true;
}

float pc_p2_breadbug_teki_param_f(const BTeki* t, int idx, float fallback) {
    const Binding* b = find(t);
    if (!b || b->escaped) return fallback;
    if (idx == TPF_Life) return b->fsm.params().health;
    if (idx == TPF_LifeRecoverRate) return 0.0f;
    return fallback;
}

bool pc_p2_breadbug_teki_draw(BTeki* t, Graphics& gfx, const Matrix4f& view, bool corpse) {
    auto i = s.find(t);
    if (i == s.end() || !gfx.mCamera) return false;
    Binding& b = i->second;
    const int v = b.variant;
    if (!sPosesLoaded[v]) return false;
    auto& sPoseList = sPoses[v];
    const bb::Bank& bank = sBank[v];
    const bool dead = corpse || b.escaped || t->mDeadState != 0;
    int anim = b.fsm.animator().anim();
    float frame = b.fsm.animator().frame();
    if (dead) {
        // startCarcassMotion: the carcass clip (type5), loop start pose.
        anim = bb::AnimCarry;
        frame = 10.0f;
        if (sPoseList[anim].empty()) { anim = bb::AnimDead; frame = 1e9f; }
    }
    if (anim < 0 || anim >= bb::AnimCount || sPoseList[anim].empty()) {
        anim = !sPoseList[bb::AnimWalk].empty() ? int(bb::AnimWalk) : int(bb::AnimWait);
        frame = 0.0f;
        if (sPoseList[anim].empty()) return false;
    }
    const auto& poses = bank.clip[anim].poses;
    std::size_t best = 0;
    for (std::size_t k = 1; k < poses.size() && k < sPoseList[anim].size(); ++k)
        if (std::fabs(float(poses[k]) - frame) < std::fabs(float(poses[best]) - frame)) best = k;
    Shape* shape = sPoseList[anim][best];
    {   // #972: lerped pose + 150 ms crossfade through a private Shape; nearest pose stays the fallback.
        float sourceFrame = frame;
        if (dead && anim == bb::AnimCarry && b.corpseAnimStarted) sourceFrame = b.corpseAnim.frame();
        sourceFrame = p2breadbugcorpse::clampFrame(sourceFrame, bank.clip[anim].frames);
        if (Shape* smooth = sFamilyVis[v].draw(t, sFamilyBank[v], bank.clip[anim].name, sourceFrame, b.generator))
            shape = smooth;
    }
    shape->updateAnim(gfx, view, nullptr, t);
    pc_gfx_specular_family_scope(1);
    shape->drawshape(gfx, *gfx.mCamera, nullptr);
    pc_gfx_specular_family_scope(0);
    int& logged = sDrawLogged[t];
    const int bit = dead ? 2 : 1;
    if (!(logged & bit)) {
        logged |= bit;
        std::printf("P2_BREADBUG_OWN_DRAW generator=%u source_id=%u corpse=%d clip=%s pose=%zu model=%s\n",
                    b.generator, b.source, dead ? 1 : 0, bank.clip[anim].name.c_str(), best, kVariants[v].model);
        std::fflush(stdout);
    }
    return true;
}

// #1022: the Breadbug's lair, drawn once per frame for every living bound
// Breadbug at its birth position (= FSM home) whether or not the Breadbug
// itself is on screen. Presentation only: no collision, no actor.
void pc_p2_breadbug_teki_draw_nests(Graphics& gfx) {
    if (!gfx.mCamera || s.empty()) return;
    bool prepared = false;
    for (auto& entry : s) {
        BTeki* t = entry.first;
        const Binding& b = entry.second;
        const int v = b.variant;
        if (!p2breadbugnest::visible(true, b.escaped, t ? t->mDeadState : 1, sNest[v] != nullptr)) continue;
        if (!prepared) {
            gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx, gfx.mCamera->mFov, gfx.mCamera->mAspectRatio,
                               gfx.mCamera->mNear, gfx.mCamera->mFar, 1.f);
            gfx.useMaterial(nullptr);
            gfx.setDepth(true);
            prepared = true;
        }
        const float k = p2breadbugnest::scale(sParams[v].nestScale);
        const auto home = b.fsm.home();
        Matrix4f world, view;
        world.makeSRT(Vector3f(k, k, k), Vector3f(0.0f, b.nestYaw, 0.0f), Vector3f(home.x, b.nestY, home.z));
        gfx.mCamera->mLookAtMtx.multiplyTo(world, view);
        sNest[v]->updateAnim(gfx, view, nullptr, nullptr);
        pc_gfx_specular_family_scope(1);
        sNest[v]->drawshape(gfx, *gfx.mCamera, nullptr);
        pc_gfx_specular_family_scope(0);
        if (!sNestLogged[v]) {
            sNestLogged[v] = true;
            std::printf("P2_BREADBUG_NEST_DRAW generator=%u source_id=%u x=%.1f y=%.1f z=%.1f scale=%.2f "
                        "behavior=visual_only\n", b.generator, b.source, home.x, b.nestY, home.z, k);
            std::fflush(stdout);
        }
    }
}
