#include "pc_p2_pose_family.h"
#include "pc_p2_sfx.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_setup_failsafe.h"
#include "pc_p2_groink_teki.h"
#include "pc_p2_groink_teki_policy.h"
#include "pc_p2_groink_carcass.h"
#include "pc_p2_groink_clock.h"
#include "pc_p2_groink_fsm.h"
#include "pc_p2_groink_fx.h"
#include "pc_p2_groink_coll.h"
#include "pc_p2_groink_burst.h"
#include "pc_p2_groink_map_trace.h"
#include "pc_p2_animation.h"
#include "pc_p2_preview.h"
#include "pc_bbft.h"
#include "EffectMgr.h"
#include "Generator.h"
#include "MapCode.h"
#include "MapMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "pc_p2_navi_select.h"
#include "Pellet.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Route.h"
#include "Shape.h"
#include "Texture.h"
#include "Graphics.h"
#include "Collision.h"
#include "ID32.h"
#include "gameflow.h"
#include "gl/pc_gfx.h"
#include "Interactions.h"
#include "system.h"
#include "teki.h"
#include <cmath>
#include <cstddef>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <fstream>
#include <map>
#include <string>
#include <vector>

extern Matrix4f invCamMat; // collInfo.cpp: camera inverse used by CollPart::getMatrix

namespace {
// #892: retail collision tree swapped in for the P1 Frog host's (host-swap pattern of the
// Emperor Bulblax / Titan Dweevil). Only `body` is stickable; cov1..cov3 are the face cover.
struct OwnColl {
    CollInfo* own = nullptr;
    CollInfo* host = nullptr;
    CollPart* parts[p2groinkcoll::kCollNodeCount] = {};
};
struct Binding {
    unsigned generator;
    int type;
    unsigned source = 0; // bridge campaign source (78 Groink, 97 FminiHoudai pedestal); 0 = preview/staged
    P2GroinkCarcassConfig config;
    P2GroinkCarcass carcass;
    bool began = false;         // death observed -> carcass begin (doBecomeCarcass)
    bool terminal = false;      // RequestBirth emitted -> stop driving; birth pending lane 06/07
    bool gaugeShown = false;    // TEKIOPT_LifeGaugeVisible currently set
    bool pelletKilled = false;  // KillPellet emitted -> never re-dereference the recycled pellet
    int births = 0;
    bool transport = false;     // sidecar `transport` token; preview fixtures only (never campaign)
    // #888 WP5 OWN: in a campaign (bridge) session a bound 78 (NormMiniHoudai)
    // or 97 (FixMiniHoudai) is driven by the engine-free source FSM
    // (pc_p2_groink_fsm) while alive; the P1 Frog TAI is suppressed and
    // blinded. Stored damage is drained here so the host stays killable.
    bool own = false;
    p2groinkfsm::Fsm fsm;
    P2GroinkSourceClock clock;
    float lastDamageCount = 0.0f;
    int pendingHits = 0;
    float lastHealth = 0.0f;
    float lastPositiveHealth = 0.0f;
    bool deadLogged = false;
    bool escaped = false;
    bool reviveSkipLogged = false;
    float logTimer = 0.0f;
    int volleys = 0;
    P2GroinkShellFx fx;         // #892 shell visuals (one-shot P1 effects, no retained handles)
    int fxTrails = 0;
    int fxGlowMarkers = 0;
    bool haveAim = false;       // last volley target, for the draw-facing diagnostic
    Vector3f aim;
    int faceLogTick = 0;
    OwnColl coll;
    int armorBlocks = 0;        // #892 Pikmin contacts refused by the touch-only parts
    int armorHits = 0;          // #892 Pikmin latches on the stickable body
    int armorDamage = 0;        // #892 stuck-attack hits accepted
    int armorMelee = 0;         // #892 unlatched/cover Pikmin hits refused
    long sourceTicks = 0;       // #892 30 Hz source ticks driven so far
    long lastVolleyTick = -1;   // #892 tick of the previous burst (gap marker)
};
std::map<BTeki*, Binding> s;

// Staged source parameters/bank (loaded once per setup, shared by actors).
p2groinkfsm::Params sParams[2];     // [0] = 78 MiniHoudai, [1] = 97 FminiHoudai
p2groinkfsm::Bank sBank = p2groinkfsm::defaultBank();
std::vector<Shape*> sPoses[p2groinkfsm::AnimCount];
bool sPosesLoaded = false;
// #895: decoded pose vectors per clip + per-actor private geometry (lerp +
// crossfade); sPoses stays the nearest-pose fallback.
p2posefamily::Bank sPoseBank("GROINK");
p2posefamily::Actors sPoseVis;
// Heap-allocated on first campaign setup: the trace owns a Creature proxy,
// which must not be constructed during static initialisation.
P2GroinkMapTrace* sTrace = nullptr;
std::map<BTeki*, int> sDrawLogged;  // bit 1 live, bit 2 corpse

// (#198 gate 6) Lifecycle observation for the cleanup/re-entry rehearsal. The
// bound actor's generator is captured at bind time so a fixture can drive the
// real `mGenType->init()` rebirth after the natural death forget; the counters
// surface the real forget/reset seams without re-reading a torn-down binding.
Generator* sGeneratorObj = nullptr;
unsigned sForgetCount = 0;
unsigned sResetCount = 0;

// Lane 21 transport tail (mirrors the lane-27 landed recipe). After a natural
// free-mode squad kill the bound host's own corpse pellet is held at the kill
// site, the captain is parked beyond the 250u join-party range, and the
// survivors are re-ringed onto the corpse in FreeMode until a carrier latches.
// The carry itself stays natural: FreeMode grasp (Piki::graspSituation) ->
// aiTransport goal (pc_p2_preview_goal() = the Research Pod) -> pc_p2_preview
// delivery, which calls pc_p2_groink_receipt for `corpse:groink:<gen>`.
struct CarcassTail {
    bool active = false;
    bool delivered = false;
    bool captainParked = false;
    Pellet* pellet = nullptr;
    float originX = 0.0f, originZ = 0.0f;
    int probeTick = 0;
};
CarcassTail sTail;
constexpr float kPi = 3.14159265358979323846f;

void reformSurvivors() {
    if (!naviMgr || !pikiMgr || !naviMgr->getNavi()) return;
    Navi* n = naviMgr->getNavi();
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (p && p->isAlive()
            && (p->mMode == PikiMode::FreeMode || p->mMode == PikiMode::TransportMode))
            p->changeMode(PikiMode::FormationMode, n);
    }
}

void stepCarcassTransport(BTeki* t) {
    if (!sTail.active) return;
    // Once the Pod credited the carcass, stop the free roam so leftover
    // dead-Pikmin `pr01` number pellets are not carried to the Pod (the preview
    // denies unregistered cargo and would abort after the receipt landed).
    if (sTail.delivered) {
        reformSurvivors();
        std::printf("P2_GROINK_CARCASS_CORPSE_DELIVERED\n");
        std::fflush(stdout);
        sTail.active = false;
        sTail.pellet = nullptr;
        return;
    }
    if (!sTail.pellet) {
        sTail.pellet = t->mPellet;
        if (sTail.pellet && sTail.pellet->mConfig) {
            std::printf("P2_GROINK_CARCASS_CORPSE_CONFIG carry_min=%d carry_max=%d min_free_slot=%d alive=%d\n",
                        sTail.pellet->mConfig->mCarryMinPikis.mValue,
                        sTail.pellet->mConfig->mCarryMaxPikis.mValue,
                        sTail.pellet->getMinFreeSlotIndex(),
                        sTail.pellet->isAlive() ? 1 : 0);
        }
    }
    if (!sTail.pellet) return;
    // Hold the freshly spawned corpse at the kill site until a carrier latches:
    // its spawn velocity otherwise flings it clear of the ringed squad.
    if (sTail.pellet->getMinFreeSlotIndex() != -1) sTail.pellet->mVelocity.set(0.0f, 0.0f, 0.0f);
    if (sTail.pellet->mConfig) {
        if (sTail.pellet->mConfig->mCarryMaxPikis.mValue < 1) sTail.pellet->mConfig->mCarryMaxPikis.mValue = 6;
        // Fixture concession: the host's own area attack decimates the squad
        // (retail corpse carry_min is higher), so allow a single survivor to
        // haul. The carry itself stays natural (grasp -> route -> Pod credit).
        sTail.pellet->mConfig->mCarryMinPikis.mValue = 1;
    }
    if (naviMgr && pikiMgr && naviMgr->getNavi()) {
        Navi* n = naviMgr->getNavi();
        int carriers = 0, squad = 0;
        Iterator pc(pikiMgr);
        CI_LOOP(pc) {
            Piki* p = static_cast<Piki*>(*pc);
            if (!p || !p->isAlive()) continue;
            ++squad;
            if (p->mMode == PikiMode::TransportMode) ++carriers;
        }
        if (carriers == 0 && sTail.probeTick % 60 == 0) {
            Vector3f park(sTail.originX, 0.0f, sTail.originZ + 300.0f);
            park.y = mapMgr ? mapMgr->getMinY(park.x, park.z, true) : 0.0f;
            n->resetPosition(park);
            n->mVelocity.set(0.0f, 0.0f, 0.0f);
            if (!sTail.captainParked) {
                sTail.captainParked = true;
                std::printf("P2_GROINK_CARCASS_CAPTAIN_PARK x=%.3f z=%.3f\n", park.x, park.z);
            }
            int ring = 0;
            Iterator sq(pikiMgr);
            CI_LOOP(sq) {
                Piki* p = static_cast<Piki*>(*sq);
                if (!p || !p->isAlive()) continue;
                const float a = float(ring) * 2.0f * kPi / float(squad > 0 ? squad : 1);
                Vector3f pt(sTail.originX + 16.0f * std::sin(a), 0.0f,
                            sTail.originZ + 16.0f * std::cos(a));
                pt.y = mapMgr ? mapMgr->getMinY(pt.x, pt.z, true) : 0.0f;
                p->resetPosition(pt);
                p->changeMode(PikiMode::FreeMode, n);
                ++ring;
            }
            std::printf("P2_GROINK_CARCASS_FREE_RECRUIT count=%d carriers=%d squad=%d\n",
                        ring, carriers, squad);
        }
    }
    if (++sTail.probeTick % 30 == 0) {
        const Vector3f& cp = sTail.pellet->mSRT.t;
        const float dx = cp.x - sTail.originX, dz = cp.z - sTail.originZ;
        int transport = 0;
        if (pikiMgr) {
            Iterator tp(pikiMgr);
            CI_LOOP(tp) {
                Piki* p = static_cast<Piki*>(*tp);
                if (p && p->isAlive() && p->mMode == PikiMode::TransportMode) ++transport;
            }
        }
        std::printf("P2_GROINK_CARCASS_CORPSE tick=%d x=%.3f z=%.3f moved=%.3f carriers=%d\n",
                    sTail.probeTick, cp.x, cp.z, std::sqrt(dx * dx + dz * dz), transport);
    }
    std::fflush(stdout);
}

const Binding* find(const BTeki* t) {
    auto i = s.find(const_cast<BTeki*>(t));
    return i == s.end() ? nullptr : &i->second;
}
// Preview-only bound-host max-life cap (see the header note).
constexpr float kHostLifeClamp = 120.0f;
// ---------------------------------------------------------------------------
// #888 WP5: source-FSM ownership of a campaign Gatling Groink.

// P1 carry-route graph ('test' handle) as the source WayPoint graph
// (MiniHoudai.cpp:383-441 walks mapMgr->mRouteMgr in P2).
struct P1Route : p2groinkfsm::Route {
    int nearest(const P2GroinkVec3& p) const override {
        if (!routeMgr || routeMgr->getNumWayPoints('test') <= 0) return -1;
        WayPoint* wp = routeMgr->findNearestWayPoint('test', Vector3f(p.x, p.y, p.z), false);
        return wp ? wp->mIndex : -1;
    }
    bool get(int index, p2groinkfsm::WayPointInfo& out) const override {
        if (!routeMgr || index < 0 || index >= routeMgr->getNumWayPoints('test')) return false;
        WayPoint* wp = routeMgr->getWayPoint('test', index);
        if (!wp) return false;
        out = p2groinkfsm::WayPointInfo{};
        out.index = wp->mIndex;
        out.pos = {wp->mPosition.x, wp->mPosition.y, wp->mPosition.z};
        out.radius = wp->mRadius;
        out.open = wp->mIsOpen;
        out.linkCount = 0;
        for (int l = 0; l < wp->mLinkCount && l < 8; ++l)
            if (wp->mLinkIndices[l] >= 0) out.links[out.linkCount++] = wp->mLinkIndices[l];
        return true;
    }
};
P1Route sRoute;

unsigned sourceOf(const Binding& b) { return b.source == 97 ? 97u : 78u; }

// Retail parms are the verbatim `minihoudai/enemyparm.txt` (78) and
// `fminihoudai/enemyparm.txt` (97) the MiniHoudai extractor already copies
// out of the disc; the family adapter stages them under these names.
void loadParams() {
    static const char* files[2] = {"p2-groink-parms.txt", "p2-groink-fixed-parms.txt"};
    for (int k = 0; k < 2; ++k) {
        sParams[k] = p2groinkfsm::Params{};
        std::ifstream in(files[k]);
        std::string error;
        if (in && !p2groinkfsm::parseEnemyParm(in, sParams[k], error)) {
            std::printf("P2_GROINK_PARMS_INVALID file=%s reason=%s fallback=source_defaults\n", files[k], error.c_str());
            sParams[k] = p2groinkfsm::Params{};
        }
        std::printf("P2_GROINK_PARMS source_id=%u retail=%d health=%.1f move=%.1f sight=%.1f search=%.1f "
                    "attack_radius=%.1f hit_angle=%.1f damage=%.1f territory=%.1f\n",
                    k ? 97u : 78u, sParams[k].retail ? 1 : 0, sParams[k].health, sParams[k].moveSpeed,
                    sParams[k].sightRadius, sParams[k].searchDistance, sParams[k].attackRadius,
                    sParams[k].attackHitAngle, sParams[k].attackDamage, sParams[k].territoryRadius);
    }
}

void loadBank() {
    sBank = p2groinkfsm::defaultBank();
    for (auto& v : sPoses) v.clear();
    sPosesLoaded = false;
    std::ifstream in("p2-groink-bank.txt");
    std::string error;
    if (in && !p2groinkfsm::parseBank(in, sBank, error)) {
        std::printf("P2_GROINK_BANK_INVALID reason=%s fallback=builtin_timing draw=host\n", error.c_str());
        sBank = p2groinkfsm::defaultBank();
    }
    int staged = 0;
    for (const auto& c : sBank.clip) staged += c.staged ? 1 : 0;
    // Poses: minihoudai_<clip>_<ii>.mod (pikmin2_minihoudai_assets.pose_name),
    // through the compact loader (#895: a few Shapes per clip plus decoded
    // vectors; the Shapes stay the nearest-pose fallback).
    sPoseBank.reset();
    sPoseVis.clear();
    p2poseload::Shared shared;
    std::size_t total = 0, poses = 0;
    bool ok = staged > 0;
    for (int a = 0; ok && a < p2groinkfsm::AnimCount; ++a) {
        const auto& clip = sBank.clip[a];
        if (!clip.staged || clip.poses.empty()) continue;
        std::string error;
        if (!p2posefamily::loadFamilyClip(sPoseBank, clip.name, "minihoudai_" + clip.name, int(clip.poses.size()),
                                          clip.frames, clip.poses, shared, total, sPoses[a], error)) {
            std::printf("P2_GROINK_POSE_LOAD_FAILED clip=%s reason=%s\n", clip.name.c_str(), error.c_str());
            ok = false;
            break;
        }
        poses += clip.poses.size();
    }
    if (!ok) for (auto& v : sPoses) v.clear();
    sPosesLoaded = ok && poses > 0;
    std::printf("P2_GROINK_BANK staged_clips=%d muzzle_staged=%d poses=%zu bytes=%zu draw=%s\n", staged,
                sBank.muzzleStaged ? 1 : 0, sPosesLoaded ? poses : std::size_t(0), total,
                sPosesLoaded ? "p2_model" : "host");
}

// Host snapshot in source manager order: captains (pc_p2_navis(), naviMgr index order, so
// co-op captains are all candidates), Piki, then nearby enemies (shells only).
struct Snapshot {
    std::vector<p2groinkfsm::Candidate> c;
    std::vector<Creature*> who;
    int stuck = 0;
};
void buildSnapshot(BTeki* self, Snapshot& snap) {
    snap.c.clear();
    snap.who.clear();
    snap.stuck = 0;
    const Vector3f me = self->getPosition();
    auto add = [&](Creature* cr, p2groinkfsm::Candidate cand) {
        const Vector3f p = cr->getPosition();
        cand.id = static_cast<std::uint64_t>(snap.who.size() + 1);
        cand.pos = {p.x, p.y, p.z};
        cand.alive = cr->isAlive();
        snap.c.push_back(cand);
        snap.who.push_back(cr);
    };
    if (naviMgr) {
        for (Navi* n : pc_p2_navis()) {
            if (!n) continue;
            p2groinkfsm::Candidate cand;
            cand.navi = true;
            add(n, cand);
        }
    }
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!p) continue;
            p2groinkfsm::Candidate cand;
            cand.pikmin = true;
            cand.stuckToSelf = p->getStickObject() == self;
            cand.stuckToMouth = p->isStickToMouth() != 0;
            // Piki::isSearchable: alive, above ground, not held in a mouth.
            cand.searchable = p->isAlive() && !p->isBuried() && !cand.stuckToMouth;
            if (cand.stuckToSelf && p->isAlive()) ++snap.stuck;
            add(p, cand);
        }
    }
    if (tekiMgr) {
        Iterator it(tekiMgr);
        CI_LOOP(it) {
            BTeki* t = static_cast<BTeki*>(*it);
            if (!t || t == self || !t->isAlive()) continue;
            const Vector3f p = t->getPosition();
            const float dx = p.x - me.x, dz = p.z - me.z;
            if (dx * dx + dz * dz > 1200.0f * 1200.0f) continue; // shell range bound (1000 recycle)
            p2groinkfsm::Candidate cand;
            cand.teki = true;
            cand.cellRadius = t->getCentreSize();
            add(t, cand);
        }
    }
}

Creature* creatureFor(const Snapshot& snap, std::uint64_t id) {
    return id >= 1 && id <= snap.who.size() ? snap.who[std::size_t(id - 1)] : nullptr;
}

void logState(const Binding& b, p2groinkfsm::State from, p2groinkfsm::State to, BTeki* t) {
    const Vector3f p = t->getPosition();
    std::printf("P2_GROINK_FSM_STATE generator=%u source_id=%u from=%s state=%s x=%.1f z=%.1f health=%.1f\n",
                b.generator, sourceOf(b), p2groinkfsm::stateName(from), p2groinkfsm::stateName(to), p.x, p.z,
                t->mHealth);
}

void applyOutput(BTeki* t, Binding& b, const Snapshot& snap, const p2groinkfsm::TickOutput& o,
                 p2groinkfsm::State& shown) {
    for (p2groinkfsm::State e : o.entered) {
        logState(b, shown, e, t);
        shown = e;
        // P1 Blowhog / Cannon Beetle bank approximation (output-only, #946).
        if (e == p2groinkfsm::State::Dead) pc_p2_sfx(sourceOf(b), b.generator, p2sfx::Event::Dead, t);
        if (e == p2groinkfsm::State::Flick) pc_p2_sfx(sourceOf(b), b.generator, p2sfx::Event::Flick, t);
        if (e == p2groinkfsm::State::Dead && !b.deadLogged) {
            b.deadLogged = true;
            std::printf("P2_GROINK_DEAD generator=%u source_id=%u health=%.1f prior_health=%.1f\n", b.generator,
                        sourceOf(b), t->mHealth, b.lastPositiveHealth);
        }
    }
    if (o.flick) {
        int stick = 0, piki = 0, navi = 0;
        for (auto id : o.flickStick)
            if (Creature* c = creatureFor(snap, id))
                if (c->isAlive() && c->getStickObject() == t && !c->isStickToMouth()
                    && c->stimulate(InteractFlick(t, o.flickKnockback, o.flickDamage, o.flickStickAngle))) ++stick;
        for (auto id : o.flickPiki)
            if (Creature* c = creatureFor(snap, id))
                if (c->isAlive() && c->stimulate(InteractFlick(t, o.flickKnockback, o.flickDamage, o.flickNearbyAngle))) ++piki;
        for (auto id : o.flickNavi)
            if (Creature* c = creatureFor(snap, id))
                if (c->isAlive() && c->stimulate(InteractFlick(t, o.flickKnockback, o.flickDamage, o.flickNearbyAngle))) ++navi;
        std::printf("P2_GROINK_FLICK generator=%u source_id=%u stick=%d/%zu piki=%d/%zu navi=%d/%zu\n", b.generator,
                    sourceOf(b), stick, o.flickStick.size(), piki, o.flickPiki.size(), navi, o.flickNavi.size());
    }
    if (o.volley) {
        ++b.volleys;
        pc_p2_sfx(sourceOf(b), b.generator, p2sfx::Event::Shot, t);
        b.haveAim = true;
        b.aim = Vector3f(o.volleyTarget.x, o.volleyTarget.y, o.volleyTarget.z);
        std::printf("P2_GROINK_VOLLEY generator=%u source_id=%u shells=%d speed=%.1f angle=%.3f target=%.1f,%.1f,%.1f n=%d\n",
                    b.generator, sourceOf(b), o.volley, o.volleySpeed, o.volleyAngle, o.volleyTarget.x,
                    o.volleyTarget.y, o.volleyTarget.z, b.volleys);
        // #892 burst evidence: one emitShotGun call spawns three shells in the same source
        // tick (MiniHoudaiShotGun.cpp:1345-1384); interval is the source-tick stagger (0).
        const long gap = b.lastVolleyTick < 0 ? -1L : b.sourceTicks - b.lastVolleyTick;
        b.lastVolleyTick = b.sourceTicks;
        std::printf("P2_GROINK_BURST generator=%u source_id=%u shots=%d interval=%d same_tick=%d spread_deg=%.1f "
                    "primary_first=%d gap_ticks=%ld n=%d\n",
                    b.generator, sourceOf(b), o.burst.shots, o.burst.intervalTicks, o.burst.sameTick ? 1 : 0,
                    double(o.burst.maxSpreadDeg), o.burst.primaryFirst ? 1 : 0, gap, b.volleys);
    }
    // Shell receivers (MiniHoudaiShotGun.cpp:201-245): InteractBomb with the
    // source damage for captains/Pikmin (100 for other enemies), InteractWind
    // with the splash impulse. The P1 receivers own the outcome (flicked or
    // flown Piki refuse repeats, a flicking captain is invincible).
    for (const auto& h : o.hits) {
        Creature* c = creatureFor(snap, h.id);
        if (!c || !c->isAlive()) continue;
        bool accepted = false;
        if (h.hit.kind == P2GroinkHitKind::Bomb) {
            accepted = c->stimulate(InteractBomb(t, h.hit.damage, nullptr));
        } else if (h.hit.kind == P2GroinkHitKind::Wind) {
            accepted = c->stimulate(InteractWind(t, Vector3f(h.hit.impulse.x, h.hit.impulse.y, h.hit.impulse.z), 0.0f, nullptr));
        }
        if (accepted)
            std::printf("P2_GROINK_SHELL_HIT generator=%u source_id=%u kind=%s target=%s damage=%.1f primary=%d\n",
                        b.generator, sourceOf(b), h.hit.kind == P2GroinkHitKind::Bomb ? "bomb" : "wind",
                        c->isPiki() ? "piki" : (c->mObjType == OBJTYPE_Navi ? "navi" : "teki"), h.hit.damage,
                        h.primary ? 1 : 0);
    }
}

// #892: P1 water floor at an impact point (source mapMgr->findWater ->
// THdamaHit3); P1 marks water on the floor triangle (itemAI.cpp:189).
bool waterAt(void*, const P2GroinkVec3& at) {
    if (!mapMgr) return false;
    CollTriInfo* tri = mapMgr->getCurrTri(at.x, at.z, true);
    return tri && MapCode::getAttribute(tri) == ATTR_Water;
}

const char* fxName(P2GroinkFxKind k) {
    switch (k) {
    case P2GroinkFxKind::Shoot: return "shoot";
    case P2GroinkFxKind::Trail: return "trail";
    case P2GroinkFxKind::Hit: return "hit";
    case P2GroinkFxKind::WaterHit: return "water";
    case P2GroinkFxKind::Glow: return "glow";
    case P2GroinkFxKind::Marker: return "marker";
    }
    return "?";
}


// #892 TEST-ONLY visual harness (PIKMIN_P2_GROINK_FX_DEMO=1): a Groink shell
// volley cannot be waited for under the autoplay bot on a smoke seed, so the
// first bound Groink also throws a synthetic four-shell volley around the
// captain every 150 source ticks. It only feeds the same fx spawn path with the
// same per-tick cadence the live policy uses (trail every kTrailInterval,
// glow/marker every tick, Hit at landing); no sim state is touched.
struct DemoShell { float x, y, z, vx, vy, vz; int age; bool live; };
void fxDemoTick(unsigned generator) {
    static const bool enabled = [] { const char* v = std::getenv("PIKMIN_P2_GROINK_FX_DEMO"); return v && v[0] == '1'; }();
    static unsigned owner = 0;
    static int tick = 0;
    static DemoShell shells[4];
    if (!enabled || !naviMgr || !naviMgr->getNavi() || !mapMgr) return;
    if (!owner) owner = generator;
    if (generator != owner) return;
    const Vector3f c = naviMgr->getNavi()->getPosition();
    if (tick % 150 == 30) {
        for (int i = 0; i < 4; ++i) {
            const float a = 1.5707963f * float(i) + 0.4f;
            const float r0 = 260.0f, r1 = 70.0f + 25.0f * float(i);
            DemoShell& d = shells[i];
            d.x = c.x + std::cos(a) * r0; d.z = c.z + std::sin(a) * r0; d.y = c.y + 45.0f;
            const float tx = c.x + std::cos(a + 0.5f) * r1, tz = c.z + std::sin(a + 0.5f) * r1;
            const float flight = 48.0f;
            d.vx = (tx - d.x) / flight; d.vz = (tz - d.z) / flight;
            d.vy = 0.0f; d.age = 0; d.live = true;
        }
    }
    unsigned liveCount = 0;
    for (DemoShell& d : shells) {
        if (!d.live) continue;
        ++liveCount;
        d.x += d.vx; d.z += d.vz; d.vy -= 0.9f; d.y += d.vy;
        const float floorY = mapMgr->getMinY(d.x, d.z, true);
        P2GroinkFxCommand cmd;
        cmd.pos = {d.x, d.y, d.z};
        if (d.y <= floorY + 10.0f || d.age > 120) {
            d.live = false;
            cmd.pos.y = floorY;
            cmd.kind = P2GroinkFxKind::Hit;
            pc_p2_groink_fx_spawn(cmd);
            continue;
        }
        if (d.age % P2GroinkShellFx::kTrailInterval == 0) { cmd.kind = P2GroinkFxKind::Trail; pc_p2_groink_fx_spawn(cmd); }
        if (d.age % P2GroinkShellFx::kGlowInterval == 0) { cmd.kind = P2GroinkFxKind::Glow; pc_p2_groink_fx_spawn(cmd); }
        if (d.age % P2GroinkShellFx::kMarkerInterval == 0) { cmd.kind = P2GroinkFxKind::Marker; pc_p2_groink_fx_spawn(cmd); }
        ++d.age;
    }
    if (tick % 30 == 0 && effectMgr)
        std::printf("P2_GROINK_FX_DEMO tick=%d live_shells=%u gens=%u\n", tick, liveCount, unsigned(effectMgr->getLiveGeneratorCount()));
    ++tick;
}

void applyEffects(Binding& b, const p2groinkfsm::TickOutput& o) {
    fxDemoTick(b.generator);
    P2GroinkFxTick tick;
    tick.volley = o.shotFired;
    tick.volleyMuzzle = o.volleyMuzzle;
    tick.deadBomb = o.deadBomb;
    tick.deadMuzzle = o.deadMuzzle;
    tick.terminals = o.terminals;
    tick.shells = &b.fsm.shells();
    // #892 leak check: live particle generators over time; after the last shell
    // lands this must fall back to the level before the volley.
    if (effectMgr) {
        static int sampleTick = 0;
        static unsigned lastLive = ~0u;
        if (++sampleTick % 6 == 0) {
            const unsigned live = effectMgr->getLiveGeneratorCount();
            if (live != lastLive) {
                lastLive = live;
                int liveShells = 0;
                for (std::size_t s = 0; s < P2GroinkVolley::kCapacity; ++s) liveShells += b.fx.live(s) ? 1 : 0;
                std::printf("P2_GROINK_FX_LIVE generator=%u gens=%u shells=%d\n", b.generator, live, liveShells);
            }
        }
    }
    for (const P2GroinkFxCommand& c : b.fx.onTick(tick, waterAt, nullptr)) {
        pc_p2_groink_fx_spawn(c);
        if (c.kind == P2GroinkFxKind::Trail) {
            ++b.fxTrails;
            continue;
        }
        if (c.kind == P2GroinkFxKind::Glow || c.kind == P2GroinkFxKind::Marker) {
            // Per-shell cadence effects (#892): log only the first of each kind.
            if (++b.fxGlowMarkers <= 2)
                std::printf("P2_GROINK_FX generator=%u source_id=%u kind=%s slot=%zu pos=%.1f,%.1f,%.1f\n",
                            b.generator, sourceOf(b), fxName(c.kind), c.slot, c.pos.x, c.pos.y, c.pos.z);
            continue;
        }
        std::printf("P2_GROINK_FX generator=%u source_id=%u kind=%s slot=%zu pos=%.1f,%.1f,%.1f dir=%.2f,%.2f,%.2f "
                    "trails=%d\n",
                    b.generator, sourceOf(b), fxName(c.kind), c.slot, c.pos.x, c.pos.y, c.pos.z, c.dir.x, c.dir.y,
                    c.dir.z, b.fxTrails);
    }
}

// ---- #892 retail collision tree (front armour cover) ----------------------------------
unsigned fourcc(const char* id) {
    unsigned v = 0;
    for (int i = 0; i < 4; ++i) v = (v << 8) | unsigned(static_cast<unsigned char>(id[i] ? id[i] : '_'));
    return v;
}

void buildColl(BTeki* t, Binding& b) {
    if (b.coll.own || b.began || !t->mCollInfo) return;
    namespace C = p2groinkcoll;
    std::vector<ObjCollInfo*> nodes;
    for (int i = 0; i < C::kCollNodeCount; ++i) {
        auto* n = new ObjCollInfo();
        n->mId.setID(fourcc(C::kCollNodes[i].id));
        n->mCode.setID(fourcc(C::kCollNodes[i].code));
        n->mRadius = C::kCollNodes[i].radius;
        n->mCentrePosition.set(0.0f, 0.0f, 0.0f);
        n->mJointIndex = 0;
        nodes.push_back(n);
    }
    for (int i = 1; i < C::kCollNodeCount; ++i) nodes[size_t(C::kCollNodes[i].parent)]->add(nodes[size_t(i)]);
    b.coll.own = new CollInfo(int(nodes.size()) + 14);
    b.coll.own->initInfoTree(nodes[0]);
    int found = 0;
    for (int i = 0; i < C::kCollNodeCount; ++i) {
        b.coll.parts[i] = b.coll.own->getSphere(fourcc(C::kCollNodes[i].id));
        if (b.coll.parts[i]) {
            ++found;
            b.coll.parts[i]->mIsUpdateActive = false; // no parent shape: updateColl owns centre/radius
            b.coll.parts[i]->mJointMatrix = Matrix4f::ident;
        }
    }
    b.coll.host = t->mCollInfo;
    t->mCollInfo = b.coll.own;
    // The host's platforms would report contacts whose part this tree cannot resolve.
    t->mPlatMgr.release();
    int stick = 0;
    for (int i = 0; i < C::kCollNodeCount; ++i) stick += C::stickable(i) ? 1 : 0;
    std::printf("P2_GROINK_COLL_BIND generator=%u source_id=%u nodes=%zu parts_found=%d stickable=%d cover=cov1,cov2,cov3 "
                "host_parts_replaced=1\n",
                b.generator, sourceOf(b), nodes.size(), found, stick);
    std::fflush(stdout);
}

// Pose every part through the FSM's current clip frame at the actor's position and heading.
void updateColl(BTeki* t, Binding& b) {
    if (!b.coll.own || t->mCollInfo != b.coll.own) return;
    namespace C = p2groinkcoll;
    Matrix4f yaw, camRot, camYaw;
    yaw.makeSRT(Vector3f(1.0f, 1.0f, 1.0f), Vector3f(0.0f, t->getDirection(), 0.0f), Vector3f(0.0f, 0.0f, 0.0f));
    camRot.makeIdentity();
    for (int r = 0; r < 3; ++r)
        for (int c = 0; c < 3; ++c) camRot.mMtx[r][c] = invCamMat.mMtx[c][r];
    camRot.multiplyTo(yaw, camYaw);
    const int clip = C::clipForAnim(b.fsm.animator().anim());
    const float frame = b.fsm.animator().frame();
    const Vector3f p = t->getPosition();
    const float pos[3] = {p.x, p.y, p.z};
    for (int i = 0; i < C::kCollNodeCount; ++i) {
        CollPart* part = b.coll.parts[i];
        if (!part) continue;
        float local[3] = {0.0f, 36.0f, 0.0f}, w[3];
        C::centre(clip, frame, i, local);
        C::toWorld(pos, t->getDirection(), local, w);
        part->mCentre.set(w[0], w[1], w[2]);
        part->mRadius = C::kCollNodes[i].radius;
        part->mJointMatrix = camYaw;
    }
}

// Hand the host its own tree back (death funnel / stage teardown / forget). The own tree
// is never freed: a stuck Pikmin may still hold CollPart pointers into it.
void restoreColl(BTeki* t, Binding& b) {
    if (!b.coll.own) return;
    if (b.coll.host && t && t->mCollInfo == b.coll.own) t->mCollInfo = b.coll.host;
    b.coll.own = nullptr;
    b.coll.host = nullptr;
    for (auto& part : b.coll.parts) part = nullptr;
}

// Live tick for an OWN-bound Groink. Returns true once the host teardown ran
// (pcEscapeNow); the caller must not touch the binding again that frame.
bool ownTick(BTeki* t, Binding& b, float dt) {
    buildColl(t, b);
    updateColl(t, b);
    // The suppressed P1 strategy normally applies stored damage through its
    // damage reaction; drain it here so Pikmin hits reach mHealth (natural
    // death). Every InteractAttack also bumps mDamageCount
    // (TEKIOPT_DamageCountable, tekibteki.cpp interactDefault), which feeds
    // the source addDamage count (flick timer, EB_TakingDamage caution).
    if (t->mStoredDamage > 0.0f) t->makeDamaged();
    if (t->mDamageCount < b.lastDamageCount) b.lastDamageCount = t->mDamageCount;
    b.pendingHits += int(t->mDamageCount - b.lastDamageCount);
    b.lastDamageCount = t->mDamageCount;
    if (t->mHealth < b.lastHealth && t->mHealth > 0.0f) pc_p2_sfx(sourceOf(b), b.generator, p2sfx::Event::Damage, t);
    if (t->mHealth < b.lastHealth && t->mHealth > 0.0f)
        std::printf("P2_GROINK_DAMAGE generator=%u source_id=%u health=%.1f prior=%.1f hits=%d\n", b.generator,
                    sourceOf(b), t->mHealth, b.lastHealth, b.pendingHits);
    if (t->mHealth > 0.0f) b.lastPositiveHealth = t->mHealth;
    b.lastHealth = t->mHealth;
    const int ticks = b.clock.step(double(dt), true);
    if (ticks <= 0) return false;
    Snapshot snap;
    buildSnapshot(t, snap);
    p2groinkfsm::State shown = b.fsm.state();
    p2groinkfsm::TickOutput last;
    bool kill = false;
    for (int k = 0; k < ticks && !kill; ++k) {
        p2groinkfsm::TickInput in;
        const Vector3f pos = t->getPosition();
        in.position = {pos.x, pos.y, pos.z};
        in.health = t->mHealth;
        in.damageHits = k == 0 ? b.pendingHits : 0;
        in.stuckPikmin = snap.stuck;
        in.candidates = snap.c.data();
        in.count = snap.c.size();
        in.route = &sRoute;
        in.trace = sTrace ? &P2GroinkMapTrace::trace : nullptr;
        in.traceContext = sTrace;
        ++b.sourceTicks;
        last = b.fsm.tick(in);
        if (!last.valid) break;
        applyOutput(t, b, snap, last, shown);
        applyEffects(b, last);
        kill = last.killRequest;
    }
    b.pendingHits = 0;
    if (last.valid) {
        // Movement/facing are the FSM's (doSimulationGround + updateFaceDir);
        // the P1 host only integrates them with its own map collision.
        t->setDirection(last.faceDir);
        const Vector3f drive(last.velocity.x, 0.0f, last.velocity.z);
        t->inputDrive(drive);
        t->mVelocity.x = drive.x;
        t->mVelocity.z = drive.z;
        if (shown == p2groinkfsm::State::Walk || shown == p2groinkfsm::State::WalkHome
            || shown == p2groinkfsm::State::WalkPath)
            pc_p2_sfx_stride(sourceOf(b), b.generator, t, 28.0f);
    }
    if (t->mHealth > 0.0f) t->updateLifeGauge();
    b.logTimer += dt;
    if (b.logTimer >= 1.0f) {
        b.logTimer = 0.0f;
        const Vector3f p = t->getPosition();
        const auto& home = b.fsm.home();
        std::printf("P2_GROINK_FSM_POS generator=%u source_id=%u state=%s anim=%d frame=%.0f x=%.1f z=%.1f "
                    "home=%.1f,%.1f health=%.1f shells=%zu searched=%d\n",
                    b.generator, sourceOf(b), p2groinkfsm::stateName(b.fsm.state()), b.fsm.animator().anim(),
                    b.fsm.animator().frame(), p.x, p.z, home.x, home.z, t->mHealth, b.fsm.shells().activeCount(),
                    b.fsm.lastSearched() ? 1 : 0);
    }
    std::fflush(stdout);
    if (kill && !b.escaped) {
        // Dead KEYEVENT_END -> kill(): onKill drops the shells, then the host
        // death funnel (die + dieSoon) births the LeaveCorpse pellet the
        // carcass/receipt path below owns. dieSoon only runs inside the
        // suppressed doAI, hence pcEscapeNow (long-legs/chappy pattern).
        b.escaped = true;
        restoreColl(t, b);
        b.fsm.forceFinishShotGun();
        b.fx.reset(); // source onKill fades every TChibiShell; one-shot puffs need no stop
        t->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
        t->mVelocity.x = t->mVelocity.z = 0.0f;
        std::printf("P2_GROINK_ESCAPE generator=%u source_id=%u native=host_escape_now\n", b.generator, sourceOf(b));
        std::fflush(stdout);
        t->pcEscapeNow();
        return true;
    }
    return false;
}

// #892 facing diagnostic: screen compass of a world XZ direction (0 = up the
// screen, 90 = right), from the camera look-at rotation (view x right, y up).
float screenDeg(const Matrix4f& look, float dx, float dz) {
    const float vx = look.mMtx[0][0] * dx + look.mMtx[0][2] * dz;
    const float vy = look.mMtx[1][0] * dx + look.mMtx[1][2] * dz;
    return std::atan2(vx, vy) * 57.2957795f;
}
} // namespace

void pc_p2_groink_teki_reset()
{
    const int boundBefore = int(s.size());
    for (auto& e : s) restoreColl(e.first, e.second);
    s.clear();
    sTail = CarcassTail{};
    sGeneratorObj = nullptr;
    sDrawLogged.clear();
    sPoseVis.clear();
    sPoseBank.reset();
    // Stage teardown frees the pose shapes with the stage heap.
    for (auto& poses : sPoses) poses.clear();
    sPosesLoaded = false;
    ++sResetCount;
    if (boundBefore > 0) {
        std::printf("P2_GROINK_TEKI_RESET bound_before=%d bound_after=%d count=%u\n",
                    boundBefore, int(s.size()), sResetCount);
        std::fflush(stdout);
    }
}

void pc_p2_groink_teki_forget(BTeki* t)
{
    if (!t) return;
    { auto known = s.find(t); if (known != s.end()) restoreColl(t, known->second); }
    const bool wasBound = s.erase(t) > 0;
    sDrawLogged.erase(t);
    sPoseVis.forget(t);
    if (wasBound) {
        ++sForgetCount;
        std::printf("P2_GROINK_TEKI_FORGET bound=1 remaining=%d count=%u\n",
                    int(s.size()), sForgetCount);
        std::fflush(stdout);
    }
}

bool pc_p2_groink_teki_is_bound(const BTeki* t) { return t && find(t) != nullptr; }
float pc_p2_groink_teki_timer(const BTeki* t) {
    const Binding* b = find(t);
    return b ? b->carcass.timer() : 0.0f;
}
float pc_p2_groink_teki_health(const BTeki* t) {
    const Binding* b = find(t);
    return b ? b->carcass.health() : 0.0f;
}
int pc_p2_groink_teki_births(const BTeki* t) {
    const Binding* b = find(t);
    return b ? b->births : 0;
}
int pc_p2_groink_teki_total_births() { return p2_groink_carcass_total_births(); }
unsigned pc_p2_groink_teki_forget_count() { return sForgetCount; }
unsigned pc_p2_groink_teki_reset_count() { return sResetCount; }
int pc_p2_groink_teki_bound_count() { return int(s.size()); }
Generator* pc_p2_groink_teki_generator_object() { return sGeneratorObj; }
bool pc_p2_groink_receipt(PelletView* view, unsigned& generator) {
    if (!view) return false;
    const Binding* b = find(static_cast<BTeki*>(view));
    if (!b) return false;
    generator = b->generator;
    // The preview calls this from pc_p2_preview_deliver when the carried
    // carcass reaches the Pod; record it so the transport tail re-forms the
    // survivors on the next tick and stops the free roam.
    if (sTail.active) sTail.delivered = true;
    return true;
}
float pc_p2_groink_teki_param_f(const BTeki* teki, int idx, float fallback) {
    const Binding* b = find(teki);
    if (!b) return fallback;
    // OWN (78/97 campaign, #888): the P2 FSM decides; blind the suppressed
    // Frog host and give it the source life so gauge/death use P2 health.
    // The carcass (began) keeps the host corpse parameters.
    if (b->own && !b->began) {
        switch (idx) {
        case TPF_Life:
            return b->fsm.params().health;
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
            break;
        }
    }
    if (idx != TPF_Life || !pc_pikipelago_room_preview()) return fallback;
    return fallback < kHostLifeClamp ? fallback : kHostLifeClamp;
}

bool pc_p2_groink_teki_suppress_ai(const BTeki* teki) {
    const Binding* b = find(teki);
    // OWN actors (campaign 78 + 97) are driven by the P2 FSM while alive and
    // through the dead clip; the corpse (began) is left to the host.
    return b && b->own && !b->began && !b->terminal;
}

namespace {
// Bind one host actor (setup loop body; also the dev-console late binder, #942).
bool bindOne(Teki* t, unsigned gen, int type, unsigned srcForBind, bool bridge, const p2groink::Binding& cfg) {
    // A host that leaves no corpse dies through dieSoon -> kill -> doKill,
    // which runs pc_p2_forget_teki on the death frame and erases this binding
    // before RequestBirth can ever fire (tekibteki.cpp:681-721, 742-749).
    // Only a LeaveCorpse host survives death as a revivable carcass pellet.
    if (t->getParameterI(TPI_CorpseType) != TEKICORPSE_LeaveCorpse) {
        std::printf("P2_GROINK_CARCASS_UNBOUND generator=%u type=%d reason=no_corpse\n", gen, type);
        return false;
    }
    Binding bind;
    bind.generator = gen;
    bind.type = type;
    bind.source = srcForBind;
    bind.config = cfg.carcass;
    // The lane-21 transport tail (teleports the captain, re-rings the
    // squad, forces carry_min=1) is a room-preview fixture recipe. It can
    // never run in a campaign session, whatever the sidecar says.
    bind.transport = cfg.transport && !bridge && pc_pikipelago_room_preview();
    bind.own = bridge;
    auto placed = s.emplace(static_cast<BTeki*>(t), bind);
    Binding& b = placed.first->second;
    if (b.own) {
        const bool fixed = srcForBind == 97;
        const p2groinkfsm::Params& parms = sParams[fixed ? 1 : 0];
        // Campaign carcass timeline uses the source parms (fp11/fp12).
        b.config.gaugeDelay = parms.healthGaugeTimer;
        b.config.recoverySeconds = parms.respawnRate;
        b.config.maxHealth = parms.health;
        const Vector3f pos = t->getPosition();
        b.fsm.init(parms, sBank, fixed, {pos.x, pos.y, pos.z}, t->getDirection(), (gen * 2654435761u) | 1u, &sRoute);
        t->mHealth = parms.health;
        b.lastHealth = b.lastPositiveHealth = t->mHealth;
        t->setTekiOption(TEKIOPT_DamageCountable);
        b.lastDamageCount = t->mDamageCount;
        std::printf("P2_GROINK_OWN_BIND generator=%u source_id=%u variant=%s health=%.1f retail_parms=%d "
                    "staged_clips=%d draw=%s route=%d state=%s\n",
                    gen, srcForBind, fixed ? "FixMiniHoudai" : "NormMiniHoudai", t->mHealth, parms.retail ? 1 : 0,
                    [] { int n = 0; for (const auto& c : sBank.clip) n += c.staged ? 1 : 0; return n; }(),
                    sPosesLoaded ? "p2_model" : "host", b.fsm.nearestWayPoint(),
                    p2groinkfsm::stateName(b.fsm.state()));
    }
    sGeneratorObj = t->mGenerator; // (#198 gate 6 rebirth probe)
    std::printf("P2_GROINK_CARCASS_READY generator=%u type=%d source=%u gauge_delay=%.3f recovery=%.3f max_health=%.3f\n",
                gen, type, srcForBind, b.config.gaugeDelay, b.config.recoverySeconds, b.config.maxHealth);
    if (bridge) {
        // Ordinary-delivery bridge (lane 06 contract, mirrors Catfish 26):
        // bind the seed source so GoalItem::suckMe grants onion:p2:78 or
        // onion:p2:97 exactly once for the delivered corpse.
        pc_randomizer_p2_bind_source(static_cast<PelletView*>(t), srcForBind, gen);
        std::printf("P2_GROINK_DELIVERY_BIND generator=%u source_id=%u\n", gen, srcForBind);
    }
    std::fflush(stdout);
    return true;
}
} // namespace

void pc_p2_groink_teki_setup() {
    pc_p2_groink_teki_reset();
    const bool bridge = pc_randomizer_p2_bridge();
    std::ifstream in("p2-groink-teki.txt");
    // Campaign actors come from the seed, so the preview sidecar is optional
    // in bridge mode (its gauge/recovery profile is a fixture profile and is
    // not used for campaign carcasses; see the carcass note in the tick).
    if (!in && !bridge) return;
    if (!tekiMgr) return;
    p2groink::Binding cfg{};
    if (in) {
        if (!p2groink::read(in, cfg)) { if (pc_p2_setup_skip(bridge, "Groink", "staged_config_invalid")) return; }
        // Fail closed on an unusable carcass config before any actor is bound.
        { P2GroinkCarcass probe; if (!probe.become(cfg.carcass)) { if (pc_p2_setup_skip(bridge, "Groink", "carcass_config_invalid")) return; } }
    }
    if (bridge) {
        loadParams();
        loadBank();
        if (!sTrace) sTrace = new P2GroinkMapTrace;
        sTrace->reset(mapMgr);
    }
    unsigned gen = cfg.generator;
    int type = cfg.type;
    unsigned srcForBind = 0;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        auto* t = static_cast<Teki*>(*it);
        if (!t || !t->mGenerator) continue;
        if (bridge) {
            const unsigned src = pc_p2_campaign_source(t);
            if (src != 78 && src != 97) continue;
            gen = pc_p2_campaign_token(t);
            // In bridge the staged single-type config no longer describes the
            // actor: 78 (NormMiniHoudai) and 97 (FixMiniHoudai pedestal) ride
            // the same Frog vehicle and are both driven by the source FSM.
            type = t->mTekiType;
            srcForBind = src;
        } else if (pc_p2_campaign_token(t) != gen) continue;
        if (t->mTekiType != type) {
            // #948: wrong vehicle for this actor only; keep sweeping the rest.
            if (pc_p2_setup_skip(bridge, "Groink", "actor_type_mismatch")) {
                std::printf("P2_GROINK_UNBOUND generator=%u source_id=%u type=%d reason=host_type_mismatch\n", gen, srcForBind, int(t->mTekiType));
                std::fflush(stdout);
                continue;
            }
        }
        if (!bridge && s.size()) { if (pc_p2_setup_skip(bridge, "Groink", "actor_type_mismatch")) return; }
        if (!bindOne(t, gen, type, srcForBind, bridge, cfg)) continue;
    }
}

bool pc_p2_groink_teki_bind_dynamic(BTeki* t) {
    if (!t || !tekiMgr || !t->mGenerator || !pc_randomizer_p2_bridge()) return false;
    const unsigned src = pc_p2_campaign_source(t);
    if (src != 78 && src != 97) return false;
    if (s.count(t)) return true;
    if (!sPosesLoaded) {
        // Setup did not run in this scene (or the bank failed): load the
        // staged source parms/bank now, exactly as the campaign setup does.
        loadParams();
        loadBank();
        if (!sTrace) sTrace = new P2GroinkMapTrace;
        sTrace->reset(mapMgr);
    }
    const p2groink::Binding cfg{};
    const bool ok = bindOne(static_cast<Teki*>(t), pc_p2_campaign_token(t), t->mTekiType, src, true, cfg);
    std::fflush(stdout);
    return ok;
}

void pc_p2_groink_teki_tick(BTeki* t) {
    auto i = s.find(t);
    if (i == s.end()) return;
    Binding& b = i->second;
    if (b.terminal) return;
    const float dt = gsys ? gsys->getFrameTime() : 0.0f;
    // OWN live phase (#888): the source FSM drives the living Groink and its
    // dead clip; the carcass starts when the host death funnel produced the
    // corpse pellet (doBecomeCarcass), below.
    if (b.own && !b.began && t->mDeadState == 0) {
        if (!(dt > 0.0f && dt < 0.5f)) return;
        ownTick(t, b, dt); // may run the host teardown; never touch b after it
        return;
    }
    if (b.own && !b.began && t->mDeadState == 1 && !b.escaped) {
        // Something outside the FSM called die() (e.g. a host hazard). dieSoon
        // only runs in the suppressed doAI, so finish the teardown here or the
        // corpse would never pelletize (the Tamago carry_no_grab lesson).
        b.escaped = true;
        restoreColl(t, b);
        b.fsm.forceFinishShotGun();
        std::printf("P2_GROINK_ESCAPE generator=%u source_id=%u native=host_die_external\n", b.generator, sourceOf(b));
        std::fflush(stdout);
        t->pcEscapeNow();
        return;
    }
    // A carcass begins the moment the live actor drops to death (mHealth <= 0),
    // mirroring doBecomeCarcass.  The regrowth timeline is then read from the
    // actor's own update cadence and pellet presence, not injected.
    if (!b.began) {
        if (t->mHealth > 0.0f) return; // still alive: no carcass yet
        if (!b.carcass.become(b.config)) {
            std::fputs("P2_GROINK_CARCASS invalid config\n", stderr);
            std::abort();
        }
        b.began = true;
        if (b.transport) {
            sTail.active = true;
            sTail.delivered = false;
            sTail.captainParked = false;
            sTail.pellet = nullptr;
            sTail.originX = t->mSRT.t.x;
            sTail.originZ = t->mSRT.t.z;
            sTail.probeTick = 0;
        }
        std::printf("P2_GROINK_CARCASS_BECOME generator=%u pos=%.3f,%.3f,%.3f face_dir=%.3f\n",
                    b.generator, t->mSRT.t.x, t->mSRT.t.y, t->mSRT.t.z, t->getDirection());
    }
    // Natural carcass -> Pod carry (transport profile only).
    if (b.transport) stepCarcassTransport(t);
    // The carcass "pellet" is the actor's own corpse pellet (PelletView::mPellet).
    // Once KillPellet has fired the pellet slot may be recycled by pelletMgr, so
    // it is never re-dereferenced after that (defensive; see the kill note below).
    const bool pelletAlive = !b.pelletKilled && t->mPellet != nullptr && t->mPellet->isAlive();
    // gaugeManager is bound to the P1 life-gauge manager. ActivateGauge only
    // toggles TEKIOPT_LifeGaugeVisible; BTeki::update runs updateLifeGauge only
    // while mDeadState == 0, so on a corpse the toggle is inert (not updated),
    // and the regrowth amount is surfaced via pc_p2_groink_teki_health()/markers,
    // not the on-screen ring (a real health regrowth is a lane 06/07 concern).
    const P2GroinkCarcassStep step = b.carcass.step(dt, pelletAlive, /*gaugeManager=*/true, /*activeTick=*/true);
    if (!step.valid) return;
    // Snapshot and log every command BEFORE the pellet is killed. Killing the
    // pellet runs Pellet::doKill -> viewKill -> BTeki::doKill ->
    // pc_p2_forget_teki, which erases this binding (and clears the actor), so no
    // field of `t` or `b` may be read after the kill. The kill is done last.
    bool killPellet = false;
    for (std::size_t k = 0; k < step.count; ++k) {
        switch (step.commands[k]) {
        case P2GroinkCarcassCommand::ActivateGauge:
            if (!b.gaugeShown) { t->setTekiOption(TEKIOPT_LifeGaugeVisible); b.gaugeShown = true; }
            std::printf("P2_GROINK_CARCASS_GAUGE_ACTIVE generator=%u timer=%.3f\n", b.generator, b.carcass.timer());
            break;
        case P2GroinkCarcassCommand::DeactivateGauge:
            if (b.gaugeShown) { t->clearTekiOption(TEKIOPT_LifeGaugeVisible); b.gaugeShown = false; }
            std::printf("P2_GROINK_CARCASS_GAUGE_INACTIVE generator=%u\n", b.generator);
            break;
        case P2GroinkCarcassCommand::KillPellet:
            if (b.own) {
                // Campaign: the port cannot birth the revived Groink
                // (generalEnemyMgr->birth + Rebirth, MiniHoudai.cpp:304-317),
                // and killing the corpse without that birth would delete the
                // enemy and its onion:p2 check. The carcass stays carriable.
                if (!b.reviveSkipLogged) {
                    b.reviveSkipLogged = true;
                    std::printf("P2_GROINK_CARCASS_REVIVE_SKIPPED generator=%u source_id=%u reason=no_native_birth health=%.3f\n",
                                b.generator, sourceOf(b), b.carcass.health());
                }
                break;
            }
            killPellet = true;
            std::printf("P2_GROINK_CARCASS_KILL_PELLET generator=%u health=%.3f\n", b.generator, b.carcass.health());
            break;
        case P2GroinkCarcassCommand::RequestBirth: {
            if (b.own) break; // see KillPellet: no campaign revival birth
            P2GroinkCarcassBirth born;
            born.position = { t->mSRT.t.x, t->mSRT.t.y, t->mSRT.t.z };
            born.faceDir = t->getDirection();
            // EnemyBirthArg existence duration / Piklopedia flag belong to the
            // lane 06/07 manager birth; the sidecar records the surviving host
            // identity but leaves that birth to the shared actor hook.
            born.existenceLength = -1.0f;
            born.inPiklopedia = false;
            ++b.births;
            p2_groink_carcass_note_birth();
            std::printf("P2_GROINK_CARCASS_BIRTH generator=%u pos=%.3f,%.3f,%.3f face_dir=%.3f existence_length=%.3f in_piklopedia=%d health=%.3f\n",
                        b.generator, born.position.x, born.position.y, born.position.z,
                        born.faceDir, born.existenceLength, born.inPiklopedia ? 1 : 0,
                        b.carcass.health());
            // Records the descriptor and stops driving. On a P1 host the pellet
            // kill below also tears down the actor + pellet, so the binding is
            // erased and "stop ticking" is moot; the replacement birth itself is
            // pending lane 06/07.
            b.terminal = true;
            break;
        }
        }
    }
    // Kill the pellet last, after every marker is recorded and every field read;
    // never touch `t` or `b` again (the kill erases the binding on a P1 host).
    if (killPellet) {
        b.pelletKilled = true; // still valid here; the kill below erases the binding on a P1 host
        if (t->mPellet) t->mPellet->kill(false);
    }
}

// #888 WP5 draw: a bound campaign Groink renders the staged P2 MiniHoudai
// pose bank, chosen by the FSM's own animation (clip = AnimID, pose = the
// staged frame nearest the source animator frame). The corpse uses the
// carcass clip (startCarcassMotion -> type5), else the dead clip's last pose.
// Without a staged bank this returns false and the host model draws.
bool pc_p2_groink_teki_draw(BTeki* t, Graphics& gfx, const Matrix4f& view, bool corpse) {
    auto i = s.find(t);
    if (i == s.end() || !sPosesLoaded || !i->second.own || !gfx.mCamera) return false;
    Binding& b = i->second;
    const bool dead = corpse || b.began || t->mDeadState != 0;
    int anim = b.fsm.animator().anim();
    float frame = b.fsm.animator().frame();
    bool last = false;
    if (dead) {
        anim = p2groinkfsm::AnimCarry;
        frame = 0.0f;
        if (sPoses[anim].empty()) { anim = p2groinkfsm::AnimDead; last = true; }
    }
    if (anim < 0 || anim >= p2groinkfsm::AnimCount || sPoses[anim].empty()) {
        // Unstaged clip: hold the nearest staged stand-in (walk, then attack).
        anim = !sPoses[p2groinkfsm::AnimWalk].empty() ? int(p2groinkfsm::AnimWalk) : int(p2groinkfsm::AnimAttack);
        frame = 0.0f;
        if (sPoses[anim].empty()) return false;
    }
    const auto& poses = sBank.clip[anim].poses;
    std::size_t best = last ? sPoses[anim].size() - 1 : 0;
    if (!last)
        for (std::size_t k = 1; k < poses.size() && k < sPoses[anim].size(); ++k)
            if (std::fabs(float(poses[k]) - frame) < std::fabs(float(poses[best]) - frame)) best = k;
    Shape* shape = sPoses[anim][best];
    {   // #895: lerp + crossfade into a private Shape; nearest pose stays the fallback.
        const auto& clip = sBank.clip[anim];
        const float duration = float(clip.frames > 1 ? clip.frames : 2);
        const float drawFrame = last ? duration - 1.0f
                                     : (std::isfinite(frame) ? std::max(0.0f, std::min(duration - 1.0f, frame)) : 0.0f);
        if (Shape* smooth = sPoseVis.draw(t, sPoseBank, clip.name, drawFrame, b.generator)) shape = smooth;
    }
    shape->updateAnim(gfx, view, nullptr, t);
    pc_gfx_specular_family_scope(1);
    shape->drawshape(gfx, *gfx.mCamera, nullptr);
    pc_gfx_specular_family_scope(0);
    if (!dead && ++b.faceLogTick % 30 == 1) {
        const Matrix4f& look = gfx.mCamera->mLookAtMtx;
        const float face = t->getDirection();
        const Vector3f p = t->getPosition();
        float aimDeg = 0.0f, velDeg = 0.0f;
        const float vx = t->mVelocity.x, vz = t->mVelocity.z;
        if (b.haveAim) aimDeg = screenDeg(look, b.aim.x - p.x, b.aim.z - p.z);
        if (vx * vx + vz * vz > 1.0f) velDeg = screenDeg(look, vx, vz);
        std::printf("P2_GROINK_FACE generator=%u state=%s face_deg=%.1f screen_fwd_deg=%.1f screen_aim_deg=%s%.1f "
                    "screen_vel_deg=%s%.1f clip=%s\n",
                    b.generator, p2groinkfsm::stateName(b.fsm.state()), face * 57.2957795f,
                    screenDeg(look, std::sin(face), std::cos(face)), b.haveAim ? "" : "na:", aimDeg,
                    (vx * vx + vz * vz > 1.0f) ? "" : "na:", velDeg, sBank.clip[anim].name.c_str());
        std::fflush(stdout);
    }
    int& logged = sDrawLogged[t];
    const int bit = dead ? 2 : 1;
    if (!(logged & bit)) {
        logged |= bit;
        std::printf("P2_GROINK_DRAW generator=%u source_id=%u corpse=%d clip=%s pose=%zu model=p2_minihoudai\n",
                    b.generator, sourceOf(b), dead ? 1 : 0, sBank.clip[anim].name.c_str(), best);
        std::fflush(stdout);
    }
    return true;
}

// #892 armour cover observer (declared in pc_p2_groink_teki.h). The engine's own
// CollPart::isStickable decides the latch; this reports the verdict and cross-checks it
// against the retail table (only `body` may take a Pikmin).
void pc_p2_groink_teki_piki_contact(BTeki* t, Piki* piki, CollPart* part, const char* site) {
    auto i = s.find(t);
    if (i == s.end() || !piki) return;
    Binding& b = i->second;
    static int diag = 0;
    if (!part || !b.own || !b.coll.own || t->mCollInfo != b.coll.own) {
        if (diag++ < 6)
            std::printf("P2_GROINK_ARMOR_SKIP site=%s part=%d own=%d coll=%d swapped=%d\n", site, part ? 1 : 0, b.own ? 1 : 0,
                        b.coll.own ? 1 : 0, (b.coll.own && t->mCollInfo == b.coll.own) ? 1 : 0);
        return;
    }
    namespace C = p2groinkcoll;
    // ID32::mStringID is the raw bytes of mId (little-endian: reversed), so resolve the part
    // by identity against the tree built in buildColl, never by string.
    int node = -1;
    for (int k = 0; k < C::kCollNodeCount; ++k)
        if (b.coll.parts[k] == part) node = k;
    if (node < 0) {
        if (diag++ < 6) std::printf("P2_GROINK_ARMOR_UNRESOLVED site=%s part=%s\n", site, part->getID().mStringID);
        return;
    }
    struct { const char* mStringID; } id = {C::kCollNodes[node].id};
    const bool engineLatch = part->isStickable();
    // Latches are reported from Creature::startStick (site "stick"); the thrown/jump sites only
    // report refusals, so a latch is never counted twice.
    const bool fromStick = !std::strcmp(site, "stick");
    if (engineLatch != fromStick) return;
    const bool policyLatch = C::contact(node) == C::Contact::Latch;
    const bool cover = C::frontCover(node);
    int& counter = engineLatch ? b.armorHits : b.armorBlocks;
    ++counter;
    const bool log = counter <= 12 || counter % 25 == 0;
    if (engineLatch != policyLatch)
        std::printf("P2_GROINK_ARMOR_MISMATCH generator=%u source_id=%u part=%s engine_latch=%d policy_latch=%d\n",
                    b.generator, sourceOf(b), id.mStringID, engineLatch ? 1 : 0, policyLatch ? 1 : 0);
    if (log)
        std::printf("P2_GROINK_ARMOR_%s generator=%u source_id=%u part=%s cover=%d site=%s damage=%s health=%.1f "
                    "blocks=%d hits=%d\n",
                    engineLatch ? "HIT" : "BLOCK", b.generator, sourceOf(b), id.mStringID, cover ? 1 : 0, site,
                    engineLatch ? "accepted" : "refused", t->mHealth, b.armorBlocks, b.armorHits);
    std::fflush(stdout);
}

void pc_p2_groink_teki_armor_counts(const BTeki* t, int& blocks, int& hits) {
    const Binding* b = find(t);
    blocks = b ? b->armorBlocks : 0;
    hits = b ? b->armorHits : 0;
}

// #892 armour cover, damage side (declared in pc_p2_groink_teki.h; hooked from
// InteractAttack::actTeki). P2's only Pikmin-origin InteractAttack is ActStickAttack, which
// sends the part the Pikmin is stuck to (aiPrimitives.cpp:3920); Pikmin never hit without
// latching. P1 also has a ground melee that sends no part (aiAttack.cpp:695), which P2 does
// not have, so it is refused for a bound Groink. Only `body` is stickable, so the face cover
// can never pass a Pikmin hit. The captain's punch always carries the touched part in the
// source (naviState.cpp:1626) and is full damage. Returns -1 for an unregistered actor or
// an attacker this rule does not cover.
float pc_p2_groink_teki_damage_rate(BTeki* t, Creature* owner, CollPart* part) {
    auto i = s.find(t);
    if (i == s.end() || !owner) return -1.0f;
    Binding& b = i->second;
    if (!b.own || b.began || !b.coll.own || t->mCollInfo != b.coll.own) return -1.0f;
    if (owner->mObjType == OBJTYPE_Navi) return 1.0f;
    if (!owner->isPiki()) return -1.0f;
    namespace C = p2groinkcoll;
    const bool stuck = owner->getStickObject() == static_cast<Creature*>(t);
    CollPart* stickPart = stuck ? owner->getStickPart() : nullptr;
    int node = -1;
    for (int k = 0; k < C::kCollNodeCount; ++k)
        if (b.coll.parts[k] == stickPart) node = k;
    const bool accept = C::pikminHit(stuck, node) == C::PikminHit::Accept;
    int& counter = accept ? b.armorDamage : b.armorMelee;
    ++counter;
    if (counter <= 12 || counter % 25 == 0) {
        if (accept)
            std::printf("P2_GROINK_ARMOR_DAMAGE generator=%u source_id=%u part=%s site=stuck_attack damage=accepted health=%.1f "
                        "accepted=%d\n", b.generator, sourceOf(b), C::kCollNodes[node].id, t->mHealth, b.armorDamage);
        else
            std::printf("P2_GROINK_ARMOR_BLOCK generator=%u source_id=%u part=%s cover=%d site=melee damage=refused "
                        "reason=%s health=%.1f refused=%d\n", b.generator, sourceOf(b),
                        node >= 0 ? C::kCollNodes[node].id : "none", (node >= 0 && C::frontCover(node)) ? 1 : 0,
                        stuck ? "not_stickable_part" : "not_latched", t->mHealth, b.armorMelee);
        std::fflush(stdout);
    }
    (void)part;
    return accept ? C::damageScale(true) : 0.0f;
}
