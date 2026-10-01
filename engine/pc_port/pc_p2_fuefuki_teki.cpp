// Campaign OWN Antenna Beetle (P2 Fuefuki, source 41), #245. See the header.
#include "pc_p2_campaign_actor.h"
#include "pc_p2_setup_failsafe.h"
#include "pc_p2_fuefuki_teki.h"
#include "pc_p2_sfx.h"
#include "pc_p2_fuefuki_teki_policy.h"
#include "pc_p2_animation.h"
#include "pc_p2_navi_select.h"
#include "pc_randomizer.h"
#include "Generator.h"
#include "MapMgr.h"
#include "MapCode.h"
#include "Route.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Pellet.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "PaniPikiAnimator.h"
#include "Shape.h"
#include <algorithm>
#include "pc_p2_fb_smooth.h"
#include "pc_p2_pose_family.h"
#include "Texture.h"
#include "Graphics.h"
#include "gameflow.h"
#include "gl/pc_gfx.h"
#include "Interactions.h"
#include "system.h"
#include "teki.h"
#include <cmath>
#include <cstdlib>
#include <cstdio>
#include <fstream>
#include <map>
#include <memory>
#include <set>
#include <string>
#include <vector>

namespace {
using p2fuefuki::Actor;
using p2fuefuki::Commands;

struct Binding {
    unsigned token = 0;
    Actor actor;
    double debt = 0.0;
    bool pressed = false;
    float lastHealth = 0.0f;
    float lastPositiveHealth = 0.0f;
    bool deadLogged = false;
    bool escaped = false;   // kill requested -> pcEscapeNow ran
    bool carcass = false;   // corpse pellet observed
    bool weighted = false;  // retail carcass carry weight applied
    bool hidden = false;    // host targetability flags currently cleared
    float logTimer = 0.0f;
    unsigned long hostSkips = 0;
    int claims = 0;
    int drawLogged = 0;
    // Dead-state pin (source StateDead zeroes mTargetVelocity; the P1 pairwise
    // creature separation in creatureCollision.cpp still pushes the host).
    bool pinned = false;
    float pinX = 0.0f, pinZ = 0.0f, pinCorrection = 0.0f, pinMaxStep = 0.0f;
    int pinTicks = 0;
    // Damage attribution since the last DAMAGE marker (InteractAttack owner).
    int hitsPiki = 0, hitsNavi = 0, hitsOther = 0;
    float dmgPiki = 0.0f, dmgNavi = 0.0f, dmgOther = 0.0f;
    // Whistle-ring stand-in (source efx::TCursor ring, updateWhisleEffect).
    float ringRadius = 0.0f;
    float ringAngle = 0.0f;
    int ringLogged = 0; // 1 = drawn this cast, 2 = drawn at full radius
    int casts = 0;
    int screenLogCountdown = 0;
    int stayDrawCalls = 0;   // draw hook calls while Stay (drawn nothing)
    float carcassTime = 0.0f; // seconds since the corpse was carried (carry clip clock)
    int stayFrames = 0;      // engine ticks spent in Stay this airborne spell
    int stayVisibleTicks = 0; // Stay ticks with TEKIOPT_Visible still set (want 0)
    // P1 target guard (policy kTargetTries): home ground height / waypoint and
    // per-reason rejection counts since the last LAND_TELEPORT marker.
    float homeY = 0.0f;
    int homeWp = -1;
    int rejNoGround = 0, rejWater = 0, rejDy = 0, rejNoRoute = 0, rejClosed = 0;
    int guardAccepted = 0;
    // Airborne hold (Jump after takeoff + Stay): XZ held while untargetable.
    bool airHeld = false;
    float airX = 0.0f, airZ = 0.0f, airCorrection = 0.0f;
    int airTicks = 0;
};

std::map<BTeki*, Binding> sBound;
P2FuefukiOwnershipTable sTable;
std::uint64_t sEpoch = 0;

// Stable Pikmin ids for the ownership table / follow controller.
std::map<const Piki*, std::uint32_t> sPikiId;
std::map<std::uint32_t, Piki*> sIdPiki;
std::uint32_t sNextPikiId = 1;
// Live ActTeki followers -> owning beetle.
std::map<const Piki*, BTeki*> sFollowerOwner;
// Owner-death PIKIPANIC_Panic (astonish) releases still panicking.
std::map<const Piki*, unsigned> sAstonish;
// Pikmin a beetle released (airborne emote -> Free, or owner-death Panic) that
// have not rejoined a captain yet.
struct Released {
    unsigned token = 0;
    const char* reason = "";
    bool whistled = false;
};
std::map<const Piki*, Released> sReleased;

p2fuefuki::Retail sRetail;
p2fuefuki::Motions sMotions;
bool sReady = false;

// Staged pose bank: fuefuki_Fuefuki_<clip>_<ii>.mod, frames from p2-fuefuki-bank.txt.
struct PoseClip {
    std::vector<int> frames;
    std::vector<Shape*> shapes;
};
PoseClip sPoses[p2fuefuki::AnimCount];
bool sPosesLoaded = false;
std::size_t sPoseCount = 0, sPoseBytes = 0, sPoseDiskBytes = 0;
// #972: lerp + 150 ms crossfade over the shared pose bank (nearest Shapes in
// sPoses stay the fallback). Presentation only; PIKMIN_P2_INTERPOLATION=0 -> nearest.
p2posefamily::Bank sPoseBank("FUEFUKI");
p2posefamily::Actors sPoseVis;

std::uint32_t pikiId(const Piki* p)
{
    auto it = sPikiId.find(p);
    if (it != sPikiId.end()) return it->second;
    const std::uint32_t id = sNextPikiId++;
    sPikiId[p] = id;
    sIdPiki[id] = const_cast<Piki*>(p);
    return id;
}
Piki* pikiFor(std::uint32_t id)
{
    auto it = sIdPiki.find(id);
    return it == sIdPiki.end() ? nullptr : it->second;
}

const char* colorName(int c) { return c == 0 ? "blue" : c == 1 ? "red" : c == 2 ? "yellow" : "other"; }

bool loadParms()
{
    sRetail = p2fuefuki::Retail{};
    std::ifstream in("p2-fuefuki-parms.txt");
    std::string error = "missing";
    if (!in || !p2fuefuki::parseEnemyParm(in, sRetail, error)) {
        std::printf("P2_FUEFUKI_PARMS_INVALID file=p2-fuefuki-parms.txt reason=%s\n", error.c_str());
        return false;
    }
    const auto& f = sRetail.fsm;
    std::printf("P2_FUEFUKI_PARMS source_id=41 retail=1 life=%.1f move=%.1f turn=%.3f max_turn=%.1f "
                "territory=%.1f home=%.1f private=%.1f attack_radius=%.1f shake_range=%.1f "
                "shake_knockback=%.1f shake_damage=%.1f fp01=%.1f fp02=%.1f fp03=%.1f fp11=%.1f fp12=%.1f "
                "fp13=%.1f fp21=%.1f fp22=%.1f fp31=%.2f\n",
                sRetail.life, sRetail.moveSpeed, sRetail.turnSpeed, sRetail.maxTurnAngle, sRetail.territoryRadius,
                sRetail.homeRadius, sRetail.privateRadius, sRetail.attackRadius, sRetail.shakeRange,
                sRetail.shakeKnockback, sRetail.shakeDamage, f.maxGroundTime, f.minGroundTime, f.airborneTime,
                f.minWhistleTime, f.maxWhistleTimeNoSquad, f.maxWhistleTimeWithSquad, f.struggleTime, f.jumpTime,
                f.normalLandingChance);
    return true;
}

bool loadMotions()
{
    sMotions = p2fuefuki::Motions{};
    std::ifstream in("p2-fuefuki-motion.txt");
    std::string error = "missing";
    if (!in || !p2fuefuki::loadMotions(in, sMotions, error)) {
        std::printf("P2_FUEFUKI_MOTION_INVALID file=p2-fuefuki-motion.txt reason=%s\n", error.c_str());
        return false;
    }
    std::printf("P2_FUEFUKI_MOTION clips=%d", p2fuefuki::AnimCount);
    for (int a = 0; a < p2fuefuki::AnimCount; ++a)
        std::printf(" %s=%d/%zu", p2fuefuki::animName(a), sMotions.clip[a].duration, sMotions.clip[a].events.size());
    std::printf("\n");
    return true;
}

Shape* loadShape(const std::string& rel, Shape*& shared, std::size_t& total)
{
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

// p2-fuefuki-bank.txt: `P2_FUEFUKI_BANK_1 <n>` then n rows
// `clip <name> <frames> <poses> <frame>...` and `END`.
void loadPoses()
{
    for (auto& c : sPoses) c = PoseClip{};
    sPosesLoaded = false;
    sPoseCount = sPoseBytes = sPoseDiskBytes = 0;
    sPoseBank.reset();
    sPoseVis.clear();
    std::ifstream in("p2-fuefuki-bank.txt");
    std::string header;
    int count = 0;
    if (!in || !(in >> header >> count) || header != "P2_FUEFUKI_BANK_1" || count < 1 || count > p2fuefuki::AnimCount) {
        std::printf("P2_FUEFUKI_BANK_INVALID reason=header draw=host\n");
        return;
    }
    p2poseload::Shared shared;
    bool ok = true;
    for (int i = 0; ok && i < count; ++i) {
        std::string word, name;
        int frames = 0, poses = 0;
        if (!(in >> word >> name >> frames >> poses) || word != "clip" || poses < 0 || poses > 24) { ok = false; break; }
        int anim = -1;
        for (int a = 0; a < p2fuefuki::AnimCount; ++a)
            if (name == p2fuefuki::animName(a)) anim = a;
        std::vector<int> fr(std::size_t(poses), 0);
        for (int& f : fr)
            if (!(in >> f)) ok = false;
        if (!ok || anim < 0) { ok = false; break; }
        // Compact loader: a few nearest-pose Shapes + decoded vectors for every pose.
        std::vector<Shape*> shapes;
        std::string error;
        const std::string stem = "fuefuki_Fuefuki_" + name;
        if (!p2posefamily::loadFamilyClip(sPoseBank, name, stem, poses, p2fbsmooth::bankDuration(fr, frames), fr, shared,
                                          sPoseBytes, shapes, error)) {
            std::printf("P2_FUEFUKI_BANK_INVALID reason=%s clip=%s draw=host\n", error.c_str(), name.c_str());
            ok = false;
            break;
        }
        for (int k = 0; k < poses; ++k) {
            std::ifstream size(p2poseload::stemPath(true, stem, k), std::ios::binary | std::ios::ate);
            if (size) sPoseDiskBytes += std::size_t(size.tellg());
            sPoses[anim].frames.push_back(fr[std::size_t(k)]);
            sPoses[anim].shapes.push_back(shapes[std::size_t(k)]);
            ++sPoseCount;
        }
    }
    std::string end;
    if (ok && (!(in >> end) || end != "END")) ok = false;
    if (!ok) {
        for (auto& c : sPoses) c = PoseClip{};
        sPoseCount = 0;
        sPoseBank.reset();
    }
    sPosesLoaded = ok && sPoseCount > 0;
    int clips = 0;
    for (const auto& c : sPoses) clips += c.shapes.empty() ? 0 : 1;
    std::printf("P2_FUEFUKI_BANK staged_clips=%d poses=%zu bytes=%zu disk_bytes=%zu interpolation=%d draw=%s "
                "landing=%zu landfail=%zu carry=%zu\n",
                clips, sPoseCount, sPoseBytes, sPoseDiskBytes, sPoseBank.ready() ? 1 : 0,
                sPosesLoaded ? "p2_model" : "host",
                sPoses[p2fuefuki::AnimLanding].shapes.size(), sPoses[p2fuefuki::AnimLandFail].shapes.size(),
                sPoses[p2fuefuki::AnimCarry].shapes.size());
}

Binding* find(const BTeki* t)
{
    auto it = sBound.find(const_cast<BTeki*>(t));
    return it == sBound.end() ? nullptr : &it->second;
}

bool pikiCallable(Piki* p)
{
    // P1 stand-in for the source PikiState::callable() gate (walk/normal only):
    // a Pikmin in its Normal state that is not stuck to anything and not buried.
    return p->getState() == PIKISTATE_Normal && !p->isStickTo() && !p->isBuried();
}

void setHidden(BTeki* t, Binding& b, bool hide)
{
    if (b.hidden == hide) return;
    b.hidden = hide;
    if (hide) {
        // EB_Untargetable: airborne beetle is not a target, not collidable.
        t->clearTekiOption(TEKIOPT_Atari | TEKIOPT_Visible | TEKIOPT_ShadowVisible | TEKIOPT_LifeGaugeVisible);
        t->setTekiOption(TEKIOPT_Invincible);
    } else {
        t->setTekiOption(TEKIOPT_Atari | TEKIOPT_Visible | TEKIOPT_ShadowVisible | TEKIOPT_LifeGaugeVisible);
        t->clearTekiOption(TEKIOPT_Invincible);
    }
    std::printf("P2_FUEFUKI_UNTARGETABLE generator=%u source_id=41 on=%d no_atari=%d invincible=%d\n", b.token,
                hide ? 1 : 0, hide ? 1 : 0, hide ? 1 : 0);
}

// ---- followers ------------------------------------------------------------
void claimFollower(BTeki* t, Binding& b, Piki* p)
{
    if (!p || !p->isAlive()) return;
    const int modeBefore = p->mMode;
    sFollowerOwner[p] = t;
    sReleased.erase(p); // re-stolen before a captain reclaimed it
    // Brain::start(ACT_Teki): the current action (formation, transport, ...)
    // is abandoned; the Pikmin leaves the party. No captain write.
    p->changeMode(PikiMode::FreeMode, p->mNavi);
    p->startMotion(PaniMotionInfo(PIKIANIM_Walk, p), PaniMotionInfo(PIKIANIM_Walk));
    ++b.claims;
    std::printf("P2_FUEFUKI_WHISTLE_CLAIM generator=%u source_id=41 piki=%u color=%s mode_before=%d followers=%d "
                "claims=%d\n",
                b.token, pikiId(p), colorName(p->mColor), modeBefore, b.actor.follow().followerCount(), b.claims);
}

void releaseSuspend(Binding& b, std::uint32_t id)
{
    Piki* p = pikiFor(id);
    if (!p) return;
    sFollowerOwner.erase(p);
    if (!p->isAlive()) return;
    // ActTeki Success + mToEmote: EMOTE_Excitement, then the brain's ACT_Free.
    p->changeMode(PikiMode::FreeMode, p->mNavi);
    if (p->getState() == PIKISTATE_Normal) {
        p->mEmotion = PikiEmotion::Excited;
        p->mFSM->transit(p, PIKISTATE_Emotion);
    }
    sReleased[p] = Released{b.token, "beetle_airborne", false};
    std::printf("P2_FUEFUKI_FOLLOW_RELEASE generator=%u source_id=41 piki=%u reason=beetle_airborne next=free_emote\n",
                b.token, id);
}

void releasePanic(unsigned token, std::uint32_t id)
{
    Piki* p = pikiFor(id);
    if (!p) return;
    sFollowerOwner.erase(p);
    if (!p->isAlive()) return;
    // ActTeki owner-death branch: PIKISTATE_Panic with PIKIPANIC_Panic.
    sAstonish[p] = token;
    sReleased[p] = Released{token, "owner_dead", false};
    p->mFSM->transit(p, PIKISTATE_Panic);
    std::printf("P2_FUEFUKI_FOLLOW_RELEASE generator=%u source_id=41 piki=%u reason=owner_dead next=panic state=%d\n",
                token, id, p->getState());
}

// ---- world snapshot ---------------------------------------------------------
void buildWorld(BTeki* t, Binding& b, p2fuefuki::World& w)
{
    const Vector3f me = t->getPosition();
    w.x = me.x;
    w.y = me.y;
    w.z = me.z;
    w.health = t->mHealth;
    w.pressed = b.pressed;
    b.pressed = false;
    // EB_Bittered: P1 has no bitter spray and no host state to read, so this
    // stays false (the source pressCallBack / hipdropCallBack !bittered gate is
    // always open). World.water only drives the source ripple effects
    // (createDownEffect ripple / fadeRipple), which this port does not draw, so
    // it is left false with no behavioural effect. Both are documented no-ops.
    w.bittered = false;
    w.water = false;
    w.pikis.clear();
    w.navis.clear();
    std::uint32_t nid = 1;
    for (Navi* n : pc_p2_navis()) {
        if (!n) continue;
        p2fuefuki::NaviView v;
        v.id = nid++;
        v.x = n->getPosition().x;
        v.z = n->getPosition().z;
        v.alive = n->isAlive();
        w.navis.push_back(v);
    }
    if (!pikiMgr) return;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (!p) continue;
        p2fuefuki::PikiView v;
        v.id = pikiId(p);
        const Vector3f pos = p->getPosition();
        v.x = pos.x;
        v.y = pos.y;
        v.z = pos.z;
        v.alive = p->isAlive();
        v.pikmin = true;
        v.callable = pikiCallable(p);
        v.stuckToMouth = p->isStickToMouth() != 0;
        v.stuckToSelf = p->getStickObject() == t;
        auto owner = sFollowerOwner.find(p);
        v.followingOther = owner != sFollowerOwner.end() && owner->second != t;
        w.pikis.push_back(v);
    }
}

// ---- P1 target guard --------------------------------------------------------
// Source Obj::setTargetPosition rolls any point of the territory ring; the P2
// maps are authored for that. P1 maps are not: d4 (#245) put the beetle on a
// ledge ~76 u above its home, it walked back onto it and died there, and the
// carcass route to the Onion stalled on a closed waypoint (P1 TUT_Rute "path
// blocked"). A Land or Walk target is accepted only when (1) a non-water ground
// triangle lies under it, (2) its ground height is within kTargetMaxDy of home,
// and (3) its nearest route waypoint is within the placement audit's route
// coverage radius and connects to home's waypoint through open, pebble-free
// waypoints (the passability test aiTransport.cpp uses to stall carriers).
// Rejected rolls re-roll in the policy; all rejected -> home.
constexpr float kTargetMaxDy = 50.0f;
constexpr float kTargetRouteRadius = 200.0f; // pc_p2_placement_probe.cpp kRouteCoverageRadius

bool wpPassable(WayPoint* wp)
{
    return wp && wp->mIsOpen && !(wp->mFlags & WayPointFlags::Pebble);
}

int nearestWp(float x, float y, float z, float& xzDist)
{
    xzDist = -1.0f;
    if (!routeMgr || routeMgr->getNumWayPoints('test') <= 0) return -1;
    WayPoint* wp = routeMgr->findNearestWayPoint('test', Vector3f(x, y, z), false);
    if (!wp) return -1;
    const float dx = wp->mPosition.x - x, dz = wp->mPosition.z - z;
    xzDist = std::sqrt(dx * dx + dz * dz);
    return wp->mIndex;
}

bool wpConnected(int from, int to)
{
    if (from < 0 || to < 0 || !routeMgr) return false;
    if (from == to) return true;
    const int n = routeMgr->getNumWayPoints('test');
    if (from >= n || to >= n) return false;
    std::vector<char> seen(std::size_t(n), 0);
    std::vector<int> queue{from};
    seen[std::size_t(from)] = 1;
    for (std::size_t head = 0; head < queue.size(); ++head) {
        WayPoint* wp = routeMgr->getWayPoint('test', queue[head]);
        if (!wp) continue;
        for (int i = 0; i < wp->mLinkCount && i < 8; ++i) {
            const int next = wp->mLinkIndices[i];
            if (next < 0 || next >= n || seen[std::size_t(next)]) continue;
            if (!wpPassable(routeMgr->getWayPoint('test', next))) continue;
            if (next == to) return true;
            seen[std::size_t(next)] = 1;
            queue.push_back(next);
        }
    }
    return false;
}

bool targetOk(Binding& b, float x, float z)
{
    if (!mapMgr) return true;
    CollTriInfo* tri = mapMgr->getCurrTri(x, z, true);
    if (!tri) { ++b.rejNoGround; return false; }
    if (MapCode::getAttribute(tri) == ATTR_Water) { ++b.rejWater; return false; }
    const float y = mapMgr->getMinY(x, z, true);
    if (!std::isfinite(y) || std::fabs(y - b.homeY) > kTargetMaxDy) { ++b.rejDy; return false; }
    if (b.homeWp >= 0) {
        float d = -1.0f;
        const int wp = nearestWp(x, y, z, d);
        if (wp < 0 || d > kTargetRouteRadius) { ++b.rejNoRoute; return false; }
        if (!wpConnected(wp, b.homeWp)) { ++b.rejClosed; return false; }
    }
    ++b.guardAccepted;
    return true;
}

void applyCommands(BTeki* t, Binding& b, const Commands& c)
{
    if (c.transited) {
        const Vector3f p = t->getPosition();
        std::printf("P2_FUEFUKI_FSM_STATE generator=%u source_id=41 from=%s state=%s clip=%s x=%.1f z=%.1f "
                    "health=%.1f appear=%.2f whistle=%.2f squad=%d stuck=%d followers=%d\n",
                    b.token, p2fuefuki::stateName(c.from), p2fuefuki::stateName(c.to), p2fuefuki::animName(c.anim),
                    p.x, p.z, t->mHealth, b.actor.fsm().getAppearTimer(), b.actor.fsm().getWhistleTimer(),
                    b.actor.fsm().squad().squadActive() ? 1 : 0, c.stuck, b.actor.follow().followerCount());
        if (c.from == P2FuefukiFsmState::Stay && c.to == P2FuefukiFsmState::Land) {
            std::printf("P2_FUEFUKI_STAY_HIDDEN generator=%u source_id=41 stay_ticks=%d draw_calls=%d drawn=0 "
                        "host_visible_during_stay=%d\n",
                        b.token, b.stayFrames, b.stayDrawCalls, b.stayVisibleTicks);
            b.stayVisibleTicks = 0;
            b.stayFrames = b.stayDrawCalls = 0;
        }
        if (c.to == P2FuefukiFsmState::Struggle)
            std::printf("P2_FUEFUKI_STRUGGLE generator=%u source_id=41 pressed=%d stuck=%d\n", b.token,
                        c.pressAccepted ? 1 : 0, c.stuck);
        // P1 Flint Beetle / frog bank approximation (output-only, #946).
        switch (c.to) {
        case P2FuefukiFsmState::Jump: pc_p2_sfx(41, b.token, p2sfx::Event::Jump, t); break;
        case P2FuefukiFsmState::Land: pc_p2_sfx(41, b.token, p2sfx::Event::Land, t); break;
        case P2FuefukiFsmState::Whisle: pc_p2_sfx(41, b.token, p2sfx::Event::Whistle, t); break;
        case P2FuefukiFsmState::Struggle: pc_p2_sfx(41, b.token, p2sfx::Event::Flick, t); break;
        case P2FuefukiFsmState::Dead: pc_p2_sfx(41, b.token, p2sfx::Event::Dead, t); break;
        default: break;
        }
        if (c.to == P2FuefukiFsmState::Dead && !b.deadLogged) {
            b.deadLogged = true;
            std::printf("P2_FUEFUKI_DEAD generator=%u source_id=41 health=%.1f prior_health=%.1f followers_panic=%zu\n",
                        b.token, t->mHealth, b.lastPositiveHealth, c.releasedPanic.size());
        }
    }
    if (c.teleport) {
        Vector3f dest(c.tx, 0.0f, c.tz);
        dest.y = mapMgr ? mapMgr->getMinY(dest.x, dest.z, true) : t->getPosition().y;
        t->resetPosition(dest);
        t->mVelocity.set(0.0f, 0.0f, 0.0f);
        if (b.airHeld) {
            b.airX = dest.x;
            b.airZ = dest.z;
        }
        std::printf("P2_FUEFUKI_LAND_TELEPORT generator=%u source_id=41 x=%.1f y=%.1f z=%.1f face=%.3f clip=%s "
                    "home=%.1f,%.1f home_y=%.1f dy=%.1f tries=%d fallback=%d\n",
                    b.token, dest.x, dest.y, dest.z, c.faceDir, p2fuefuki::animName(c.anim), b.actor.homeX(),
                    b.actor.homeZ(), b.homeY, dest.y - b.homeY, c.targetTries, c.targetFallback ? 1 : 0);
        std::printf("P2_FUEFUKI_TARGET_GUARD generator=%u source_id=41 accepted=%d rej_noground=%d rej_water=%d "
                    "rej_dy=%d rej_noroute=%d rej_closed=%d rejected_total=%d fallbacks_total=%d home_wp=%d "
                    "max_dy=%.0f\n",
                    b.token, b.guardAccepted, b.rejNoGround, b.rejWater, b.rejDy, b.rejNoRoute, b.rejClosed,
                    b.actor.rejectedTargets(), b.actor.fallbackTargets(), b.homeWp, kTargetMaxDy);
        b.guardAccepted = b.rejNoGround = b.rejWater = b.rejDy = b.rejNoRoute = b.rejClosed = 0;
    }
    if (c.untargetableChanged) setHidden(t, b, c.untargetable);
    if (c.transited && c.to == P2FuefukiFsmState::Whisle) {
        ++b.casts;
        b.ringLogged = 0;
    }
    b.ringRadius = b.actor.fsm().getState() == P2FuefukiFsmState::Whisle ? c.whistleRadius : 0.0f;
    for (std::uint32_t id : c.claimed) claimFollower(t, b, pikiFor(id));
    for (std::uint32_t id : c.releasedSuspend) releaseSuspend(b, id);
    for (std::uint32_t id : c.releasedPanic) releasePanic(b.token, id);
    if (!c.flickStick.empty() || !c.flickPiki.empty() || !c.flickNavi.empty()) {
        int stick = 0, piki = 0, navi = 0;
        for (std::uint32_t id : c.flickStick)
            if (Piki* p = pikiFor(id))
                if (p->isAlive() && p->getStickObject() == t
                    && p->stimulate(InteractFlick(t, c.flickKnockback, c.flickDamage, c.flickStickAngle))) ++stick;
        for (std::uint32_t id : c.flickPiki)
            if (Piki* p = pikiFor(id))
                if (p->isAlive() && p->stimulate(InteractFlick(t, c.flickKnockback, c.flickDamage, c.flickNearbyAngle))) ++piki;
        std::uint32_t nid = 1;
        for (Navi* n : pc_p2_navis()) {
            const std::uint32_t id = nid++;
            if (!n || !n->isAlive()) continue;
            for (std::uint32_t want : c.flickNavi)
                if (want == id && n->stimulate(InteractFlick(t, c.flickKnockback, c.flickDamage, c.flickNearbyAngle))) ++navi;
        }
        std::printf("P2_FUEFUKI_FLICK generator=%u source_id=41 stick=%d/%zu piki=%d/%zu navi=%d/%zu\n", b.token, stick,
                    c.flickStick.size(), piki, c.flickPiki.size(), navi, c.flickNavi.size());
    }
    // Locomotion: the FSM's velocity/facing; the host integrates with its map
    // collision (doSimulation stand-in, Groink #888 pattern).
    t->setDirection(c.faceDir);
    const Vector3f drive(c.vx, 0.0f, c.vz);
    t->inputDrive(drive);
    t->mVelocity.x = drive.x;
    t->mVelocity.z = drive.z;
}

// Source StateDead::init zeroes mTargetVelocity and the dead beetle stays put
// until kill(). On the P1 host the pairwise creature separation
// (creatureCollision.cpp: impulse + mVolatileVelocity, getiMass = 1 /
// TPF_Weight) lets the attacking crowd shove the dying host: d2 drifted ~90 u
// during the dead clip. Hold the XZ where Dead began, zero the host velocity,
// and log how much push was cancelled.
void pinDead(BTeki* t, Binding& b)
{
    if (b.actor.fsm().getState() != P2FuefukiFsmState::Dead) return;
    Vector3f p = t->getPosition();
    if (!b.pinned) {
        b.pinned = true;
        b.pinX = p.x;
        b.pinZ = p.z;
        std::printf("P2_FUEFUKI_DEAD_PIN generator=%u source_id=41 x=%.1f z=%.1f\n", b.token, p.x, p.z);
    }
    const float dx = p.x - b.pinX, dz = p.z - b.pinZ;
    const float step = std::sqrt(dx * dx + dz * dz);
    b.pinCorrection += step;
    b.pinMaxStep = step > b.pinMaxStep ? step : b.pinMaxStep;
    ++b.pinTicks;
    p.x = b.pinX;
    p.z = b.pinZ;
    t->mSRT.t.set(p.x, p.y, p.z);
    t->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
    t->mVelocity.x = t->mVelocity.z = 0.0f;
    t->mVolatileVelocity.x = t->mVolatileVelocity.z = 0.0f;
}

// While untargetable (Jump after KEYEVENT_3, then Stay) the source beetle is
// off-map and nothing can touch it until Land teleports it home-relative. The
// P1 host keeps integrating (the Jump escape velocity, creature separation), so
// it drifted hundreds of units invisibly (d5) and could fall into a pit or
// water, where the host_die_external path would pelletize the corpse at that
// hidden position. Hold the XZ where the hide began (pinDead pattern) until the
// beetle is targetable again; log how much drift was cancelled.
void holdAirborne(BTeki* t, Binding& b)
{
    const bool airborne = b.hidden && b.actor.fsm().getState() != P2FuefukiFsmState::Dead;
    Vector3f p = t->getPosition();
    if (!airborne) {
        if (b.airHeld) {
            b.airHeld = false;
            std::printf("P2_FUEFUKI_AIR_HOLD_SUMMARY generator=%u source_id=41 x=%.1f z=%.1f ticks=%d "
                        "drift_cancelled=%.1f\n",
                        b.token, b.airX, b.airZ, b.airTicks, b.airCorrection);
        }
        return;
    }
    if (!b.airHeld) {
        b.airHeld = true;
        b.airX = p.x;
        b.airZ = p.z;
        b.airCorrection = 0.0f;
        b.airTicks = 0;
        std::printf("P2_FUEFUKI_AIR_HOLD generator=%u source_id=41 x=%.1f z=%.1f state=%s\n", b.token, p.x, p.z,
                    p2fuefuki::stateName(b.actor.fsm().getState()));
    }
    const float dx = p.x - b.airX, dz = p.z - b.airZ;
    b.airCorrection += std::sqrt(dx * dx + dz * dz);
    ++b.airTicks;
    t->mSRT.t.set(b.airX, p.y, b.airZ);
    t->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
    t->mVelocity.x = t->mVelocity.z = 0.0f;
    t->mVolatileVelocity.x = t->mVolatileVelocity.z = 0.0f;
}

void ownTick(BTeki* t, Binding& b, float dt)
{
    // Suppressed host strategy: drain stored Pikmin damage here so hits reach
    // mHealth and the beetle can die naturally (Groink #888 pattern).
    if (t->mStoredDamage > 0.0f) t->makeDamaged();
    if (t->mHealth < b.lastHealth && t->mHealth >= 0.0f) {
        // Attackers: Pikmin stuck on the beetle, and Pikmin in AttackMode within
        // 60 units (P1 ground attacks on a small host do not stick).
        int stuck = 0, melee = 0;
        for (Creature* c = t->mStickListHead; c; c = c->mNextSticker)
            if (c->isPiki() && c->isAlive()) ++stuck;
        if (pikiMgr) {
            const Vector3f me = t->getPosition();
            Iterator it(pikiMgr);
            CI_LOOP(it) {
                Piki* p = static_cast<Piki*>(*it);
                if (!p || !p->isAlive() || p->mMode != PikiMode::AttackMode) continue;
                const Vector3f pp = p->getPosition();
                const float dx = pp.x - me.x, dz = pp.z - me.z;
                if (dx * dx + dz * dz < 60.0f * 60.0f) ++melee;
            }
        }
        // source/src_* are the InteractAttack owners since the previous marker
        // (Pikmin hits vs captain punches); attackers/stuck/attack_mode_near
        // are proximity context only.
        const char* source = b.hitsPiki && b.hitsNavi ? "piki+navi"
                             : b.hitsPiki             ? "piki"
                             : b.hitsNavi             ? "navi"
                             : b.hitsOther            ? "other"
                                                      : "unattributed";
        if (t->mHealth > 0.0f) pc_p2_sfx(41, b.token, p2sfx::Event::Damage, t);
        std::printf("P2_FUEFUKI_DAMAGE generator=%u source_id=41 health=%.1f prior=%.1f source=%s src_piki=%d "
                    "src_piki_dmg=%.1f src_navi=%d src_navi_dmg=%.1f src_other=%d attackers=%d stuck=%d "
                    "attack_mode_near=%d state=%s\n",
                    b.token, t->mHealth, b.lastHealth, source, b.hitsPiki, b.dmgPiki, b.hitsNavi, b.dmgNavi,
                    b.hitsOther, stuck + melee, stuck, melee, p2fuefuki::stateName(b.actor.fsm().getState()));
        b.hitsPiki = b.hitsNavi = b.hitsOther = 0;
        b.dmgPiki = b.dmgNavi = b.dmgOther = 0.0f;
    }
    if (t->mHealth > 0.0f) b.lastPositiveHealth = t->mHealth;
    b.lastHealth = t->mHealth;
    b.debt += double(dt);
    int ticks = int(b.debt / double(p2fuefuki::kSourceDelta));
    if (ticks > 4) {
        ticks = 4;
        b.debt = 0.0;
    } else {
        b.debt -= double(ticks) * double(p2fuefuki::kSourceDelta);
    }
    Commands last;
    for (int k = 0; k < ticks && !b.escaped; ++k) {
        p2fuefuki::World w;
        buildWorld(t, b, w);
        last = b.actor.step(w);
        if (!last.valid) break;
        applyCommands(t, b, last);
        if (b.actor.fsm().getState() == P2FuefukiFsmState::Walk)
            pc_p2_sfx_stride(41, b.token, t, 12.0f);
        pinDead(t, b);
        holdAirborne(t, b);
        if (last.kill) {
            std::printf("P2_FUEFUKI_DEAD_PIN_SUMMARY generator=%u source_id=41 x=%.1f z=%.1f ticks=%d "
                        "push_cancelled=%.1f max_step=%.2f\n",
                        b.token, b.pinX, b.pinZ, b.pinTicks, b.pinCorrection, b.pinMaxStep);
            // Dead KEYEVENT_END -> kill(): the host death funnel (die+dieSoon)
            // births the LeaveCorpse pellet; dieSoon only runs in the
            // suppressed doAI, hence pcEscapeNow (Groink/ElecBug pattern).
            b.escaped = true;
            t->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
            t->mVelocity.x = t->mVelocity.z = 0.0f;
            std::printf("P2_FUEFUKI_ESCAPE generator=%u source_id=41 native=host_escape_now clip=%s\n", b.token,
                        p2fuefuki::animName(b.actor.anim()));
            std::fflush(stdout);
            t->pcEscapeNow();
            return;
        }
    }
    if (!b.escaped && ticks == 0) {
        // Keep the last FSM velocity/facing applied between source frames.
        t->setDirection(b.actor.faceDir());
    }
    pinDead(t, b);
    holdAirborne(t, b);
    if (b.actor.fsm().getState() == P2FuefukiFsmState::Stay) {
        ++b.stayFrames;
        if (t->getTekiOption(TEKIOPT_Visible)) ++b.stayVisibleTicks;
    }
    if (t->mHealth > 0.0f && !b.hidden) t->updateLifeGauge();
    b.logTimer += dt;
    if (b.logTimer >= 1.0f) {
        b.logTimer = 0.0f;
        const Vector3f p = t->getPosition();
        // Follower trail evidence: mean/max XZ distance of this beetle's live
        // ActTeki followers (FOLLOW_DISTANCE 100 keeps them on the trail).
        float sum = 0.0f, far = 0.0f;
        int n = 0;
        for (const auto& f : sFollowerOwner) {
            if (f.second != t || !f.first) continue;
            const Vector3f fp = const_cast<Piki*>(f.first)->getPosition();
            const float d = std::sqrt((fp.x - p.x) * (fp.x - p.x) + (fp.z - p.z) * (fp.z - p.z));
            sum += d;
            far = d > far ? d : far;
            ++n;
        }
        if (n > 0)
            std::printf("P2_FUEFUKI_FOLLOW_TRAIL generator=%u source_id=41 followers=%d mean_dist=%.1f max_dist=%.1f "
                        "state=%s\n",
                        b.token, n, sum / float(n), far, p2fuefuki::stateName(b.actor.fsm().getState()));
        std::printf("P2_FUEFUKI_POS generator=%u source_id=41 state=%s clip=%s frame=%.0f x=%.1f z=%.1f face=%.2f "
                    "target=%.1f,%.1f health=%.1f followers=%d squad=%d hidden=%d marks=%d host_ai_skipped=%lu\n",
                    b.token, p2fuefuki::stateName(b.actor.fsm().getState()), p2fuefuki::animName(b.actor.anim()),
                    b.actor.animFrame(), p.x, p.z, b.actor.faceDir(), b.actor.targetX(), b.actor.targetZ(),
                    t->mHealth, b.actor.follow().followerCount(), b.actor.fsm().squad().squadActive() ? 1 : 0,
                    b.hidden ? 1 : 0, b.actor.follow().markCount(), b.hostSkips);
    }
    std::fflush(stdout);
}

// Retail carcass weight (pelletlist_us.szs carcass_config.txt `Fuefuki`:
// min 3, max 6). The P1 corpse config is shared by every host of this type, so
// the beetle's own corpse gets a private copy instead of a shared write.
constexpr int kCarcassMin = 3;
constexpr int kCarcassMax = 6;
void carcassTick(BTeki* t, Binding& b)
{
    Pellet* pellet = t->mPellet;
    if (!pellet || !pellet->isAlive()) return;
    if (!b.carcass) {
        b.carcass = true;
        std::printf("P2_FUEFUKI_CARCASS generator=%u source_id=41 x=%.1f z=%.1f clip=carry\n", b.token,
                    pellet->mSRT.t.x, pellet->mSRT.t.z);
    }
    if (!b.weighted && pellet->mConfig) {
        b.weighted = true;
        const int hostMin = pellet->mConfig->mCarryMinPikis.mValue;
        const int hostMax = pellet->mConfig->mCarryMaxPikis.mValue;
        const bool differs = hostMin != kCarcassMin || hostMax != kCarcassMax;
        if (differs) {
            // One private copy per distinct host config, owned here and reused
            // by every later carcass (no per-carcass allocation).
            static std::map<const PelletConfig*, std::unique_ptr<PelletConfig>> sOwnConfigs;
            std::unique_ptr<PelletConfig>& own = sOwnConfigs[pellet->mConfig];
            if (!own) {
                own.reset(new PelletConfig(*pellet->mConfig));
                own->mCarryMinPikis.mValue = kCarcassMin;
                own->mCarryMaxPikis.mValue = kCarcassMax;
            }
            pellet->mConfig = own.get();
        }
        std::printf("P2_FUEFUKI_CARCASS_WEIGHT generator=%u source_id=41 retail_carry=%d..%d host_carry=%d..%d "
                    "private_copy=%d source=carcass_config_Fuefuki\n",
                    b.token, kCarcassMin, kCarcassMax, hostMin, hostMax, differs ? 1 : 0);
        std::fflush(stdout);
    }
}
// Whistle ring. Source Obj::updateWhisleEffect drives an efx::TCursor (the
// JPA whistle-cursor particle ring, createEffect init(3, 10)) at radius
// mWhistleRadiusModifier * fp22 (grows over 1 s to mAttackRadius) with angle
// speed fp23. P1 has no TCursor resource, so this is an explicit stand-in in
// the same geometry: a ground ring at the live cast radius (the exact radius
// the claim scan uses) with 10 rotating arc marks. Colour/particle look are
// not retail.
void drawRing(BTeki* t, Binding& b, Graphics& gfx)
{
    if (!gfx.mCamera) return;
    const float r = b.ringRadius;
    const Vector3f c = t->getPosition();
    const float dt = gsys ? gsys->getFrameTime() : 0.0f;
    if (dt > 0.0f && dt < 0.5f) b.ringAngle = p2fuefuki::roundAng(b.ringAngle + sRetail.attackHitAngle * p2fuefuki::kPi / 180.0f * 30.0f * dt);
    const Colour oldColour = gfx.mPrimaryColour;
    const Colour oldAux = gfx.mAuxiliaryColour;
    const int oldBlend = gfx.setCBlending(BLEND_Alpha);
    Texture* oldTexture = gfx.mActiveTexture[0];
    const bool oldLight = gfx.setLighting(false, nullptr);
    const float oldWidth = gfx.setLineWidth(3.0f);
    gfx.useMaterial(nullptr);
    gfx.useTexture(nullptr, 0);
    gfx.useMatrix(gfx.mCamera->mLookAtMtx, 0);
    const float y = c.y + 3.0f;
    constexpr int kSegs = 48;
    gfx.setColour(Colour(255, 240, 150, 150), true);
    // Core lines render 1 px on the GL backend regardless of setLineWidth, so
    // the band is built from three concentric rings on two heights.
    for (int band = 0; band < 6; ++band) {
        const float rr = r + float(band % 3 - 1) * 1.5f;
        const float yy = y + float(band / 3) * 3.0f;
        for (int i = 0; i < kSegs; ++i) {
            const float a0 = i * p2fuefuki::kTau / kSegs, a1 = (i + 1) * p2fuefuki::kTau / kSegs;
            gfx.drawLine(Vector3f(c.x + std::sin(a0) * rr, yy, c.z + std::cos(a0) * rr),
                         Vector3f(c.x + std::sin(a1) * rr, yy, c.z + std::cos(a1) * rr));
        }
    }
    gfx.setColour(Colour(255, 255, 230, 255), true);
    for (int k = 0; k < 10; ++k) {
        const float a0 = b.ringAngle + k * p2fuefuki::kTau / 10.0f;
        for (int s = 0; s < 3; ++s) {
            const float s0 = a0 + s * 0.05f, s1 = a0 + (s + 1) * 0.05f;
            gfx.drawLine(Vector3f(c.x + std::sin(s0) * r, y + 1.0f, c.z + std::cos(s0) * r),
                         Vector3f(c.x + std::sin(s1) * r, y + 1.0f, c.z + std::cos(s1) * r));
        }
    }
    gfx.setLineWidth(oldWidth);
    gfx.setColour(oldColour, true);
    gfx.mAuxiliaryColour = oldAux;
    gfx.setCBlending(oldBlend);
    gfx.useTexture(oldTexture, 0);
    gfx.setLighting(oldLight, nullptr);
    const int want = r >= sRetail.attackRadius - 0.01f ? 2 : 1;
    if (b.ringLogged < want) {
        b.ringLogged = want;
        std::printf("P2_FUEFUKI_RING_DRAW generator=%u source_id=41 cast=%d radius=%.1f full=%d attack_radius=%.1f "
                    "x=%.1f z=%.1f\n",
                    b.token, b.casts, r, want == 2 ? 1 : 0, sRetail.attackRadius, c.x, c.z);
        std::fflush(stdout);
    }
}
} // namespace

// ---------------------------------------------------------------------------
void pc_p2_fuefuki_teki_reset()
{
    const int before = int(sBound.size());
    sBound.clear();
    sTable.invalidateDomain();
    sFollowerOwner.clear();
    sAstonish.clear();
    sReleased.clear();
    sPikiId.clear();
    sIdPiki.clear();
    for (auto& c : sPoses) c = PoseClip{};
    sPosesLoaded = false;
    sPoseBank.reset();
    sPoseVis.clear();
    sReady = false;
    if (before > 0) {
        std::printf("P2_FUEFUKI_OWN_RESET bound_before=%d\n", before);
        std::fflush(stdout);
    }
}

void pc_p2_fuefuki_teki_forget(BTeki* t)
{
    auto it = sBound.find(t);
    if (it == sBound.end()) return;
    Binding& b = it->second;
    for (std::uint32_t id : b.actor.ownerDeath()) releasePanic(b.token, id);
    for (auto f = sFollowerOwner.begin(); f != sFollowerOwner.end();)
        f = f->second == t ? sFollowerOwner.erase(f) : std::next(f);
    std::printf("P2_FUEFUKI_OWN_FORGET generator=%u source_id=41 remaining=%d\n", b.token, int(sBound.size()) - 1);
    std::fflush(stdout);
    sPoseVis.forget(t);
    sBound.erase(it);
}

bool pc_p2_fuefuki_teki_is_bound(const BTeki* t) { return t && find(t) != nullptr; }
int pc_p2_fuefuki_teki_bound_count() { return int(sBound.size()); }

bool pc_p2_fuefuki_teki_casting(const BTeki* t)
{
    Binding* b = t ? find(t) : nullptr;
    return b && !b->escaped && b->actor.fsm().getState() == P2FuefukiFsmState::Whisle;
}

bool pc_p2_fuefuki_teki_suppress_ai(const BTeki* t)
{
    Binding* b = find(t);
    if (!b || b->escaped) return false;
    ++b->hostSkips; // BTeki::doAI returned before the P1 strategy act()
    return true;
}

float pc_p2_fuefuki_teki_param_f(const BTeki* t, int idx, float fallback)
{
    const Binding* b = find(t);
    if (!b || b->escaped) return fallback;
    switch (idx) {
    case TPF_Life:
        return sRetail.life;
    case TPF_VisibleRange:
    case TPF_VisibleAngle:
    case TPF_AttackableRange:
    case TPF_AttackableAngle:
    case TPF_AttackRange:
    case TPF_AttackHitRange:
    case TPF_AttackPower:
    case TPF_DangerTerritoryRange:
    case TPF_SafetyTerritoryRange:
    case TPF_LifeRecoverRate:
        return 0.0f;
    default:
        return fallback;
    }
}

namespace {
// Source Obj::pressCallBack / hipdropCallBack: with a presser, mCanStruggle and
// no EB_Bittered the beetle transits to Struggle and returns false; otherwise
// it returns true (press absorbed). The Struggle transit is latched for the
// next FSM step (the FSM re-checks the same gate). One marker per latch, so a
// landing reported by both the flying seam and InteractPress logs once.
bool pressCallBack(Binding& b, Creature* presser, const char* route)
{
    if (b.escaped) return true;
    const P2FuefukiFsmState st = b.actor.fsm().getState();
    const bool accept = p2fuefuki::pressAccepted(b.actor.fsm(), presser != nullptr, false /* no P1 bitter */);
    if (accept && !b.pressed) {
        b.pressed = true;
        std::printf("P2_FUEFUKI_PRESS_INTERACT generator=%u source_id=41 presser=%s route=%s state=%s "
                    "can_struggle=1 result=struggle\n",
                    b.token, presser->isPiki() ? "piki" : "other", route, p2fuefuki::stateName(st));
        std::fflush(stdout);
    } else if (!accept) {
        std::printf("P2_FUEFUKI_PRESS_INTERACT generator=%u source_id=41 presser=%s route=%s state=%s "
                    "can_struggle=0 result=absorbed\n",
                    b.token, presser && presser->isPiki() ? "piki" : "other", route, p2fuefuki::stateName(st));
        std::fflush(stdout);
    }
    return !accept;
}
} // namespace

bool pc_p2_fuefuki_teki_pressed(BTeki* t, Creature* presser)
{
    Binding* b = find(t);
    if (!b) return false;
    pressCallBack(*b, presser, "interact_press");
    return true; // no host squash on a bound beetle
}

bool pc_p2_fuefuki_teki_flying_press(BTeki* t, Piki* presser, bool descending)
{
    if (sBound.empty()) return false;
    Binding* b = find(t);
    if (!b || b->escaped || !t->isAlive()) return false;
    if (!descending) {
        // Source: InteractFlyCollision only (Fuefuki has no flyCollisionCallBack
        // override -> false), so the Pikmin latches as usual.
        std::printf("P2_FUEFUKI_FLY_CONTACT generator=%u source_id=41 piki=%u descending=0 result=latch state=%s\n",
                    b->token, pikiId(presser), p2fuefuki::stateName(b->actor.fsm().getState()));
        std::fflush(stdout);
        return false;
    }
    return pressCallBack(*b, presser, "flying_contact");
}

void pc_p2_fuefuki_teki_attacked(BTeki* t, Creature* owner, float damage, bool accepted)
{
    if (sBound.empty() || !accepted) return;
    Binding* b = find(t);
    if (!b || b->escaped) return;
    if (owner && owner->isPiki()) {
        ++b->hitsPiki;
        b->dmgPiki += damage;
    } else if (owner && owner->mObjType == OBJTYPE_Navi) {
        ++b->hitsNavi;
        b->dmgNavi += damage;
    } else {
        ++b->hitsOther;
        b->dmgOther += damage;
    }
}

namespace {
// Staged parms/motions/poses, loaded once per scene (setup or first late bind).
bool ensureLoaded()
{
    if (sReady) return true;
    if (!loadParms()) { pc_p2_setup_skip(true, "Fuefuki", "parms_missing"); return false; }
    if (!loadMotions()) { pc_p2_setup_skip(true, "Fuefuki", "motion_table_missing"); return false; }
    loadPoses();
    sReady = true;
    return true;
}

// Bind one seed-41 actor: the setup loop body, also the dev-console late binder (#942).
bool bindOne(BTeki* t)
{
    const unsigned token = pc_p2_campaign_token(t);
    if (t->mTekiType != TEKI_Chappy) {
        std::printf("P2_FUEFUKI_UNBOUND generator=%u type=%d reason=host_type\n", token, t->mTekiType);
        pc_p2_setup_skip(true, "Fuefuki", "actor_type_mismatch");
        return false;
    }
    if (t->getParameterI(TPI_CorpseType) != TEKICORPSE_LeaveCorpse) {
        std::printf("P2_FUEFUKI_UNBOUND generator=%u type=%d reason=no_corpse\n", token, t->mTekiType);
        return false;
    }
    Binding& b = sBound[t];
    b = Binding{};
    b.token = token;
    const Vector3f pos = t->getPosition();
    // Target guard reference: home ground height and route waypoint.
    b.homeY = mapMgr ? mapMgr->getMinY(pos.x, pos.z, true) : pos.y;
    if (!std::isfinite(b.homeY)) b.homeY = pos.y;
    {
        float d = -1.0f;
        const int wp = nearestWp(pos.x, b.homeY, pos.z, d);
        b.homeWp = wp >= 0 && d <= kTargetRouteRadius ? wp : -1;
        std::printf("P2_FUEFUKI_GUARD_HOME generator=%u source_id=41 home_y=%.1f home_wp=%d wp_dist=%.1f "
                    "max_dy=%.0f route_radius=%.0f\n",
                    token, b.homeY, b.homeWp, d, kTargetMaxDy, kTargetRouteRadius);
    }
    Binding* bp = &b;
    b.actor.setTargetProbe([bp](float x, float z) { return targetOk(*bp, x, z); });
    if (!b.actor.bind(sRetail, sMotions, sTable, ++sEpoch, token, pos.x, pos.y, pos.z, t->getDirection())) {
        sBound.erase(t);
        std::printf("P2_FUEFUKI_UNBOUND generator=%u reason=bind_rejected\n", token);
        return false;
    }
    t->mHealth = sRetail.life;
    b.lastHealth = b.lastPositiveHealth = t->mHealth;
    const float hostScale = t->mSRT.s.x;
    t->mSRT.s.set(1.0f, 1.0f, 1.0f);
    const Commands spawn = b.actor.takeSpawnCommands();
    std::printf("P2_FUEFUKI_OWN_BIND generator=%u source_id=41 host=TEKI_Chappy host_ai=suppressed fsm=p2_source "
                "health=%.1f retail_parms=%d motion_clips=%d draw=%s host_scale=%.2f epoch=%llu state=%s\n",
                token, t->mHealth, sRetail.retail ? 1 : 0, p2fuefuki::AnimCount,
                sPosesLoaded ? "p2_model" : "host", hostScale, (unsigned long long)sEpoch,
                p2fuefuki::stateName(b.actor.fsm().getState()));
    applyCommands(t, b, spawn);
    // Ordinary-delivery bridge: the carried carcass grants onion:p2:41 once.
    pc_randomizer_p2_bind_source(static_cast<PelletView*>(t), 41, token);
    std::printf("P2_FUEFUKI_DELIVERY_BIND generator=%u source_id=41\n", token);
    std::printf("P2_ENEMY_READY species=Fuefuki native_family=Chappy generator=%u x=%.3f y=%.3f z=%.3f "
                "health=%.1f max_health=%.1f behavior=native source_FSM=implemented attack=whistle_theft\n",
                token, pos.x, pos.y, pos.z, t->mHealth, sRetail.life);
    return true;
}
} // namespace

void pc_p2_fuefuki_teki_setup()
{
    pc_p2_fuefuki_teki_reset();
    if (!pc_randomizer_p2_bridge() || !tekiMgr) return;
    const std::set<unsigned> wanted = pc_p2_campaign_ids(41);
    if (wanted.empty()) return;
    if (!ensureLoaded()) return;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        BTeki* t = static_cast<BTeki*>(*it);
        if (!t || pc_p2_campaign_source(t) != 41) continue;
        bindOne(t);
    }
    std::printf("P2_FUEFUKI_SETUP wanted=%zu bound=%zu\n", wanted.size(), sBound.size());
    std::fflush(stdout);
}

bool pc_p2_fuefuki_teki_bind_dynamic(BTeki* t)
{
    if (!t || !tekiMgr || !pc_randomizer_p2_bridge() || pc_p2_campaign_source(t) != 41) return false;
    if (sBound.count(t)) return true;
    if (!ensureLoaded()) return false;
    const bool ok = bindOne(t);
    std::fflush(stdout);
    return ok;
}

void pc_p2_fuefuki_teki_tick(BTeki* t)
{
    auto it = sBound.find(t);
    if (it == sBound.end()) return;
    Binding& b = it->second;
    const float dt = gsys ? gsys->getFrameTime() : 0.0f;
    if (!(dt > 0.0f && dt < 0.5f)) return;
    // Released Pikmin that died before rejoining a captain leave the reclaim
    // table (their object may be reborn by pikiMgr).
    for (auto r = sReleased.begin(); r != sReleased.end();)
        r = r->first && !const_cast<Piki*>(r->first)->isAlive() ? sReleased.erase(r) : std::next(r);
    if (!b.escaped && t->mDeadState == 0) {
        ownTick(t, b, dt);
        return;
    }
    if (!b.escaped && t->mDeadState == 1) {
        // Something outside the FSM called die(): finish the teardown so the
        // corpse still pelletizes (dieSoon only runs in the suppressed doAI).
        b.escaped = true;
        for (std::uint32_t id : b.actor.ownerDeath()) releasePanic(b.token, id);
        std::printf("P2_FUEFUKI_ESCAPE generator=%u source_id=41 native=host_die_external\n", b.token);
        std::fflush(stdout);
        t->pcEscapeNow();
        return;
    }
    b.carcassTime += p2fbsmooth::fadeStep(dt);
    carcassTick(t, b);
}

bool pc_p2_fuefuki_teki_draw(BTeki* t, Graphics& gfx, const Matrix4f& view, bool corpse)
{
    Binding* b = find(t);
    if (!b || !sPosesLoaded || !gfx.mCamera) return false;
    const bool dead = corpse || b->escaped || t->mDeadState != 0;
    int anim = b->actor.anim();
    float frame = b->actor.animFrame();
    bool lastPose = false;
    if (dead) {
        // startCarcassMotion -> FUEFUKIANIM_Carry; the dead clip's last pose if absent.
        anim = p2fuefuki::AnimCarry;
        frame = 0.0f;
        if (sPoses[anim].shapes.empty()) {
            anim = p2fuefuki::AnimDead;
            lastPose = true;
        }
    } else if (b->actor.fsm().getState() == P2FuefukiFsmState::Stay) {
        // Stay holds landing frame 0 (authored zero scale): nothing to draw, and
        // the P1 host model must not show either. (The host is also
        // !TEKIOPT_Visible, so the engine normally never calls this; count it.)
        ++b->stayDrawCalls;
        return true;
    }
    if (anim < 0 || anim >= p2fuefuki::AnimCount || sPoses[anim].shapes.empty()) {
        anim = !sPoses[p2fuefuki::AnimWait].shapes.empty() ? int(p2fuefuki::AnimWait) : int(p2fuefuki::AnimMove);
        frame = 0.0f;
        if (sPoses[anim].shapes.empty()) return false;
    }
    const PoseClip& clip = sPoses[anim];
    std::size_t best = lastPose ? clip.shapes.size() - 1 : 0;
    if (!lastPose)
        for (std::size_t k = 1; k < clip.frames.size() && k < clip.shapes.size(); ++k)
            if (std::fabs(float(clip.frames[k]) - frame) < std::fabs(float(clip.frames[best]) - frame)) best = k;
    Shape* shape = clip.shapes[best];
    {
        // #972: lerped pose through the per-actor private Shape (150 ms crossfade on
        // clip change). The carried corpse loops its carry clip between the source
        // LOOP_START/LOOP_END markers (whole clip when absent); a corpse showing the
        // dead clip holds its last visible pose.
        float sourceFrame = std::max(0.0f, frame);
        if (dead && anim == p2fuefuki::AnimCarry) {
            const p2retail::Motion& motion = sMotions.clip[anim];
            int loopStart = 0, loopEnd = std::max(1, int(motion.duration));
            for (const auto& event : motion.events) {
                if (event.type == 0) loopStart = event.frame;
                if (event.type == 1 && event.frame > loopStart) loopEnd = event.frame;
            }
            sourceFrame = p2fbsmooth::carryLoopFrame(b->carcassTime, loopStart, loopEnd);
        } else if (lastPose) {
            sourceFrame = 1.0e6f;
        }
        if (Shape* smooth = sPoseVis.draw(t, sPoseBank, p2fuefuki::animName(anim), sourceFrame, b->token)) shape = smooth;
    }
    shape->updateAnim(gfx, view, nullptr, t);
    pc_gfx_specular_family_scope(1);
    shape->drawshape(gfx, *gfx.mCamera, nullptr);
    pc_gfx_specular_family_scope(0);
    const int bit = dead ? 2 : (1 << (anim + 2));
    if (!(b->drawLogged & bit)) {
        b->drawLogged |= bit;
        std::printf("P2_FUEFUKI_DRAW generator=%u source_id=41 corpse=%d clip=%s pose=%zu face=%.2f model=p2_fuefuki\n",
                    b->token, dead ? 1 : 0, p2fuefuki::animName(anim), best, t->getDirection());
        std::fflush(stdout);
    }
    if (!dead && b->ringRadius > 0.0f) drawRing(t, *b, gfx);
    if (std::getenv("PIKMIN_FRAME_DUMP") && ++b->screenLogCountdown >= 15) {
        // Eye-check aid (frame-dump runs only): where this actor sits on screen,
        // so the dumped frame can be cropped around it.
        b->screenLogCountdown = 0;
        Vector3f sp = t->getPosition();
        const float depth = gfx.mCamera->projectWorldPoint(gfx, sp);
        if (depth > 0.0f && gfx.mScreenWidth > 0 && gfx.mScreenHeight > 0)
            std::printf("P2_FUEFUKI_SCREEN generator=%u source_id=41 u=%.3f v=%.3f depth=%.0f state=%s clip=%s "
                        "frame=%.0f face=%.2f corpse=%d\n",
                        b->token, sp.x / float(gfx.mScreenWidth), sp.y / float(gfx.mScreenHeight), depth,
                        p2fuefuki::stateName(b->actor.fsm().getState()), p2fuefuki::animName(anim), frame,
                        t->getDirection(), dead ? 1 : 0);
    }
    return true;
}

// ---- Piki seams -------------------------------------------------------------
bool pc_p2_fuefuki_follower_controls(Piki* p)
{
    if (sFollowerOwner.empty() || !p) return false;
    auto it = sFollowerOwner.find(p);
    if (it == sFollowerOwner.end()) return false;
    Binding* b = find(it->second);
    if (!b || b->escaped) {
        sFollowerOwner.erase(it);
        return false;
    }
    const std::uint32_t id = pikiId(p);
    if (!p->isAlive()) {
        b->actor.forgetFollower(id);
        sFollowerOwner.erase(it);
        return false;
    }
    const float dt = gsys ? gsys->getFrameTime() : 0.0f;
    BTeki* t = it->second;
    const Vector3f me = p->getPosition();
    const Vector3f bp = t->getPosition();
    const Vector3f bv = t->mVelocity;
    const P2FuefukiFollowMove move =
        b->actor.follow().followerTick(id, me.x, me.z, bp.x, bp.z, bv.x, bv.z, dt > 0.0f && dt < 0.5f ? dt : 0.0f);
    if (move.hasMove) {
        if (move.stop) {
            p->mTargetVelocity.set(0.0f, 0.0f, 0.0f);
        } else {
            // ActTeki::test_0 -> Piki::setSpeed(mMoveSpeed, dirToFootprint).
            p->setSpeed(move.speed, Vector3f(move.dirX, 0.0f, move.dirZ));
        }
    }
    return true;
}

bool pc_p2_fuefuki_follower_blocks_recruit(const Piki* p)
{
    return !sFollowerOwner.empty() && p && sFollowerOwner.count(p) != 0;
}

bool pc_p2_fuefuki_panic_astonish(const Piki* p)
{
    return !sAstonish.empty() && p && sAstonish.count(p) != 0;
}

void pc_p2_fuefuki_panic_end(Piki* p, bool timedOut)
{
    auto it = sAstonish.find(p);
    if (it == sAstonish.end()) return;
    std::printf("P2_FUEFUKI_PANIC_END generator=%u source_id=41 piki=%u reason=%s state=%d\n", it->second,
                pikiId(p), timedOut ? "timeout_walk" : "state_change", p->getState());
    std::fflush(stdout);
    sAstonish.erase(it);
}

void pc_p2_fuefuki_note_whistle(Piki* p, Navi* n)
{
    (void)n;
    if (sReleased.empty() || !p) return;
    auto it = sReleased.find(p);
    if (it != sReleased.end()) it->second.whistled = true;
}

void pc_p2_fuefuki_note_formation(Piki* p, Navi* n)
{
    if (!p) return;
    if (!sFollowerOwner.empty()) {
        auto f = sFollowerOwner.find(p);
        if (f != sFollowerOwner.end()) {
            // A non-whistle path into a party (callPikis refuses followers):
            // the brain starts another action, so ActTeki::cleanup releases the
            // follow. Nothing else changes about the Pikmin.
            BTeki* owner = f->second;
            sFollowerOwner.erase(f);
            if (Binding* b = find(owner)) {
                const std::uint32_t id = pikiId(p);
                b->actor.forgetFollower(id);
                std::printf("P2_FUEFUKI_FOLLOW_RELEASE generator=%u source_id=41 piki=%u reason=formation_other "
                            "next=formation navi=%d\n",
                            b->token, id, n ? n->mNaviID : -1);
                std::fflush(stdout);
            }
            return;
        }
    }
    if (sReleased.empty()) return;
    auto it = sReleased.find(p);
    if (it == sReleased.end()) return;
    if (p->isAlive()) {
        std::printf("P2_FUEFUKI_RECLAIM generator=%u source_id=41 piki=%u navi=%d released=%s via=%s state=%d\n",
                    it->second.token, pikiId(p), n ? n->mNaviID : -1, it->second.reason,
                    it->second.whistled ? "whistle" : "other", p->getState());
        std::fflush(stdout);
    }
    sReleased.erase(it);
}
