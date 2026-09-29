#include "pc_p2_campaign_actor.h"
#include "pc_p2_setup_failsafe.h"
#include "pc_p2_kurage_teki.h"
#include "pc_p2_kurage_campaign.h"
#include "pc_p2_kurage_fsm.h"
#include "pc_p2_kurage_receiver.h"
#include "pc_p2_kurage_teki_policy.h"
#include "pc_p2_kurage_visual.h"
#include "pc_p2_retail_player.h"
#include "pc_bbft.h"
#include "Camera.h"
#include "Collision.h"
#include "Generator.h"
#include "Graphics.h"
#include "Shape.h"
#include "MapMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Pellet.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "system.h"
#include "teki.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
namespace {
struct Binding {
    unsigned generator;
    int type;
    CollPart mouth;
    // Opt-in source flight-lifecycle authority.  Off by default so the
    // binding-only consumers keep the original draw + receiver behaviour.
    p2kurage::Fsm fsm;
    bool fsmEnabled = false;
    p2retail::Player attackPlayer;
    bool attackPlaying = false;
    bool sucking = false;
    p2kurage::KeyEvent pendingKey = p2kurage::KeyEvent::None;
    bool motionFinished = false;
    int motionTimer = 0;
    int autoAdmissions = 0;
    int fsmTicks = 0;
    int logTimer = 0;
    int lastLoggedState = -1;
    // Host walkToTarget (Move patrol / Chase pursuit) for the ordinary actor.
    Vector3f spawnPos;
    Vector3f patrolTarget;
    bool hasPatrol = false;
    unsigned patrolState = 0x9e3779b9u;
    float lastDistToGoal = 1e9f;
};
std::map<BTeki*, Binding> s;
// Naturally dead Kurage bodies: kept until the central forget/reset seam so the
// Pod delivery receipt can still resolve the corpse after the live binding is
// revoked (mirrors the mamuta pattern; BTeki::update keeps ticking dead bodies).
std::map<BTeki*, unsigned> corpses;
int gTickCalls = 0;
// Lane-local production showcase (env `PIKMIN_P2_KURAGE_SHOWCASE`). Opt-in so the
// default binding path is byte-identical: the bound generated actor runs the
// transcribed source flight lifecycle and one live Pikmin is seeded into its
// suction window so the real receiver can be observed. The body remains the
// generated vehicle; flight, suction and ingestion are lane-driven.
bool sShowcase = false;
bool sShowcaseBaitSpawned = false;
Piki* sShowcaseBait = nullptr;
// Natural carcass -> Research Pod carry tail (lane-27 recipe). After the bound
// generated actor really dies, the corpse Pellet is held, the captain is parked
// beyond the 250u join-party range, and the FreeMode survivors are ringed onto
// the carcass until a carrier latches (a formation squad never picks up a
// corpse; only FreeMode Pikmin do). The carry_min is forced to 1 as the same
// labelled fixture concession lane 27 used. Once the Pod credits the receipt,
// the survivors are re-formed so stray dead-Pikmin `pr01` number pellets are not
// hauled to the preview's deny-by-default cargo abort.
BTeki* sCorpseTeki = nullptr;
Pellet* sCorpsePellet = nullptr;
Vector3f sCorpseOrigin;
int sCorpseProbeTick = 0;
bool sCorpseDelivered = false;
bool sCaptainParked = false;
int sHoverProbeTick = 0;
bool sCorpseDrawLogged = false;
// Campaign (seed bridge without the room preview): the playtested path. All
// labelled fixture concessions (ground pin + seek, captain park, recruit ring,
// mode changes, carry/pellet mutations) are skipped here and kept ONLY for the
// room-preview / staged-sidecar fixtures that already test them.
inline bool kurageCampaignMode()
{
    return p2kurage_campaign::isCampaignMode(pc_randomizer_p2_bridge(),
                                             pc_pikipelago_room_preview());
}
// Injected ground-engagement seal for the production preview: a FreeMode P1
// squad rejects a flying Teki outright (piki.cpp:951; aiAttack.cpp:189/297), so
// pin the bound proxy to the floor and hold it within the squad's attack volume.
// Only the production (non-FSM) binding path uses this; the isolated runtime FSM
// scenarios keep their flight behaviour. Labelled fixture concession, mirrors
// lane 27's BombSarai grounding.
constexpr float kEngageKeepRange = 30.0f;
constexpr float kEngageSeekSpeed = 300.0f;
// p2retail::Player timers are animation frames; attack.bca is a 30 fps clip.
constexpr float kAttackFramesPerSecond = 30.0f;
// Bounded animation-END stand-in until the #431 motion-event bridge exists.
constexpr int kFsmMotionFrames = 30;
// Kurage.h mAttackRadius (asset ProperParms value not yet imported) and ip11.
constexpr float kSourceAttackRadius = 35.0f;
constexpr int kMaxAutoAdmissions = 10;
constexpr float kPatrolSpeed = 60.0f;
constexpr float kPatrolRadius = 150.0f;
// Retail Kurage attack.bca event table (enemyanimmgr.txt): 37=KEYEVENT_2 suck
// start, 60=loop, 67=KEYEVENT_1 suck end.
const p2retail::Motion kAttackMotion{
    "attack.bca", "302660c6ba9c86fee11cc6aca98bd514e201a80d8530be3a5cce867a9dc74a4e",
    120, 2, { { 37, 2 }, { 60, 0 }, { 67, 1 } }
};

void revoke(BTeki* t)
{
    auto i = s.find(t);
    if (i == s.end()) return;
    pc_p2_kurage_receiver_owner_invalidated(t);
    s.erase(i);
}

void refresh(BTeki* t, Binding& b)
{
    b.mouth.mPartType = PART_BoundSphere;
    b.mouth.mRadius = 15.0f;
    b.mouth.mCentre = t->mSRT.t;
    b.mouth.mJointMatrix.makeIdentity();
}

// getSearchedTarget approximation for the ordinary actor: first live Pikmin in
// the source vertical suction window and attack radius not already stuck here.
Piki* findSuctionTarget(BTeki* t)
{
    if (!pikiMgr || !t) return nullptr;
    ObjectMgr* manager = static_cast<ObjectMgr*>(pikiMgr);
    const float radiusSqr = kSourceAttackRadius * kSourceAttackRadius;
    for (int it = manager->getFirst(); !manager->isDone(it); it = manager->getNext(it)) {
        Piki* piki = static_cast<Piki*>(manager->getCreature(it));
        if (!piki || !piki->isAlive() || piki->getStickObject() == t || !piki->mayIstick()) continue;
        if (!p2kurage::inSuctionWindow(t->mSRT.t.y, 0.0f, piki->mSRT.t.y)) continue;
        const float dx = piki->mSRT.t.x - t->mSRT.t.x;
        const float dz = piki->mSRT.t.z - t->mSRT.t.z;
        if (dx * dx + dz * dz >= radiusSqr) continue;
        return piki;
    }
    return nullptr;
}

void pickPatrol(Binding& b)
{
    b.patrolState = b.patrolState * 1664525u + 1013904223u;
    const float u = float((b.patrolState >> 8) & 0xFFFFu) / 65535.0f;
    b.patrolState = b.patrolState * 1664525u + 1013904223u;
    const float v = float((b.patrolState >> 8) & 0xFFFFu) / 65535.0f;
    const float angle = u * 6.2831853f;
    const float dist = 40.0f + v * kPatrolRadius;
    b.patrolTarget.set(b.spawnPos.x + std::cos(angle) * dist, 0.0f,
        b.spawnPos.z + std::sin(angle) * dist);
}

void tickAttack(Binding& b, float dt)
{
    if (!b.attackPlaying) return;
    const p2retail::Update result = b.attackPlayer.advance(dt, [&b](const p2retail::Event& event) {
        if (event.type == 2) {
            b.sucking = true;
            b.pendingKey = p2kurage::KeyEvent::Key2;
        } else if (event.type == 1 || event.type == 1000) {
            b.sucking = false;
            b.attackPlaying = false;
            b.attackPlayer.cancel();
            b.pendingKey = p2kurage::KeyEvent::Key1;
            b.motionFinished = true;
        }
    });
    if (result == p2retail::Update::Inactive || result == p2retail::Update::Invalid) b.attackPlaying = false;
}

// Injected ground-engagement seal (production binding only). Clears CF_IsFlying,
// pins the proxy to the floor, and closes the gap to the nearest live Pikmin at a
// capped per-tick speed so the FreeMode squad can attack it. A large per-tick
// teleport crashes the P1 host, hence the speed cap. Labelled fixture concession.
void groundAndSeal(BTeki* t)
{
    if (!mapMgr) return;
    t->finishFlying();
    t->mSRT.t.y = mapMgr->getMinY(t->mSRT.t.x, t->mSRT.t.z, true);
    t->mVelocity.y = 0.0f;
    if (!pikiMgr) return;
    float best = 1.0e30f, dx = 0.0f, dz = 0.0f;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* piki = static_cast<Piki*>(*it);
        if (!piki || !piki->isAlive()) continue;
        const float ex = piki->mSRT.t.x - t->mSRT.t.x;
        const float ez = piki->mSRT.t.z - t->mSRT.t.z;
        const float d2 = ex * ex + ez * ez;
        if (d2 < best) { best = d2; dx = ex; dz = ez; }
    }
    if (best >= 1.0e29f) return;
    const float d = std::sqrt(best);
    if (d <= kEngageKeepRange) return;
    const float step = kEngageSeekSpeed * gsys->getFrameTime();
    const float gap = d - kEngageKeepRange;
    const float move = gap < step ? gap : step;
    t->mSRT.t.x += dx / d * move;
    t->mSRT.t.z += dz / d * move;
}

// Corpse -> Pod carry tail, run from every teki tick (including after the live
// binding is revoked) before the binding lookup. Bookkeeping itself runs once
// per frame on the corpse actor's own tick: the caller invokes this once per
// TEKI per frame, so an unguarded counter would advance N times per frame and
// the "every 60 calls" recruit would fire several times a second. Returns true
// when a corpse is active.
bool corpseTail(BTeki* t)
{
    if (sCorpseTeki && t != sCorpseTeki) return true;
    if (sCorpseTeki && sCorpseDelivered) {
        // Campaign: no forced mode changes; just end the tail.
        if (!kurageCampaignMode() && naviMgr && pikiMgr && naviMgr->getNavi()) {
            Navi* n = naviMgr->getNavi();
            Iterator fp(pikiMgr);
            CI_LOOP(fp) {
                Piki* p = static_cast<Piki*>(*fp);
                if (p && p->isAlive()
                    && (p->mMode == PikiMode::FreeMode || p->mMode == PikiMode::TransportMode))
                    p->changeMode(PikiMode::FormationMode, n);
            }
        }
        std::printf("P2_KURAGE_TEKI_CORPSE_DELIVERED\n");
        std::fflush(stdout);
        sCorpseTeki = nullptr;
        sCorpsePellet = nullptr;
        sCorpseProbeTick = 0;
        sCaptainParked = false;
    }
    if (!sCorpseTeki) return false;
    if (!sCorpsePellet) {
        sCorpsePellet = sCorpseTeki->mPellet;
        if (sCorpsePellet) {
            // Death-drop-to-ground (flyer): a Kurage killed mid-air spawns its
            // corpse Pellet at altitude. FreeMode Pikmin only grasp grounded
            // corpses, so settle the fresh Pellet onto the floor before the
            // carry can latch. Natural gravity settle, one marker.
            if (mapMgr) {
                const float groundY = mapMgr->getMinY(sCorpsePellet->mSRT.t.x,
                    sCorpsePellet->mSRT.t.z, true);
                if (std::isfinite(groundY) && sCorpsePellet->mSRT.t.y > groundY + 1.0f) {
                    std::printf("P2_KURAGE_CORPSE_DROP from_y=%.3f ground_y=%.3f\n",
                        sCorpsePellet->mSRT.t.y, groundY);
                    std::fflush(stdout);
                    sCorpsePellet->mSRT.t.y = groundY;
                    sCorpsePellet->mVelocity.set(0.0f, 0.0f, 0.0f);
                    sCorpsePellet->mTargetVelocity.set(0.0f, 0.0f, 0.0f);
                }
            }
        }
        if (sCorpsePellet && sCorpsePellet->mConfig) {
            std::printf("P2_KURAGE_TEKI_CORPSE_CONFIG carry_min=%d carry_max=%d min_free_slot=%d alive=%d\n",
                        sCorpsePellet->mConfig->mCarryMinPikis.mValue,
                        sCorpsePellet->mConfig->mCarryMaxPikis.mValue,
                        sCorpsePellet->getMinFreeSlotIndex(),
                        sCorpsePellet->isAlive() ? 1 : 0);
            std::fflush(stdout);
        }
    }
    if (!sCorpsePellet) return true;
    // Fixture-only holds and mutations (mirrors lane 27): the campaign carries
    // the corpse naturally with untouched physics and config.
    if (!kurageCampaignMode()) {
    // Hold the freshly spawned corpse at the kill site until a carrier latches;
    // its spawn velocity otherwise flings it clear of the ringed squad.
    if (sCorpsePellet->getMinFreeSlotIndex() != -1) sCorpsePellet->mVelocity.set(0.0f, 0.0f, 0.0f);
    if (sCorpsePellet->mConfig) {
        if (sCorpsePellet->mConfig->mCarryMaxPikis.mValue < 1) sCorpsePellet->mConfig->mCarryMaxPikis.mValue = 6;
        // Fixture concession (mirrors lane 27): allow a single survivor to
        // haul the carcass; the carry itself stays natural (FreeMode grasp ->
        // route -> Pod credit).
        sCorpsePellet->mConfig->mCarryMinPikis.mValue = 1;
    }
    } // !campaign: velocity hold + carry mutations
    // Suppress stray Red number pellets (pr01) while the carcass is being hauled:
    // the proxy's death (and any Pikmin it killed) drops `pr01` number pellets,
    // and a FreeMode Pikmin carrying one to the Pod hits the preview's
    // deny-by-default cargo abort before the carcass receipt lands. Lane 27
    // re-formed survivors only *after* the receipt; this closes the pre-receipt
    // race. Only free (uncarried) pellets are touched so an in-flight carrier is
    // never disrupted. Labelled fixture concession.
    if (!kurageCampaignMode() && pelletMgr) {
        Iterator pit(pelletMgr);
        CI_LOOP(pit) {
            Pellet* pel = static_cast<Pellet*>(*pit);
            if (!pel || pel == sCorpsePellet || !pel->isAlive() || !pel->mConfig) continue;
            if (pel->mConfig->mModelId.mId != 'pr01') continue;
            if (pel->getMinFreeSlotIndex() == -1) continue;
            pel->mConfig->mCarryMinPikis.mValue = 0;
            pel->mConfig->mCarryMaxPikis.mValue = 0;
        }
    }
    // Fixture-only recruit (labelled concession): park the captain beyond the
    // 250u join-party range and ring the survivors onto the carcass in FreeMode
    // until a carrier latches. Never in campaign (no captain/Pikmin teleports,
    // no forced mode changes).
    if (!kurageCampaignMode() && naviMgr && pikiMgr && naviMgr->getNavi()) {
        Navi* n = naviMgr->getNavi();
        int carriers = 0, squad = 0;
        Iterator pc(pikiMgr);
        CI_LOOP(pc) {
            Piki* p = static_cast<Piki*>(*pc);
            if (!p || !p->isAlive()) continue;
            ++squad;
            if (p->mMode == PikiMode::TransportMode) ++carriers;
        }
        if (carriers == 0 && sCorpseProbeTick % 60 == 0) {
            Vector3f park(sCorpseOrigin.x, 0.0f, sCorpseOrigin.z + 300.0f);
            park.y = mapMgr ? mapMgr->getMinY(park.x, park.z, true) : 0.0f;
            n->resetPosition(park);
            n->mVelocity.set(0.0f, 0.0f, 0.0f);
            if (!sCaptainParked) {
                sCaptainParked = true;
                std::printf("P2_KURAGE_TEKI_CAPTAIN_PARK x=%.3f z=%.3f\n", park.x, park.z);
                std::fflush(stdout);
            }
            int ring = 0;
            Iterator sq(pikiMgr);
            CI_LOOP(sq) {
                Piki* p = static_cast<Piki*>(*sq);
                if (!p || !p->isAlive()) continue;
                const float a = float(ring) * 2.0f * 3.14159265358979323846f / float(squad > 0 ? squad : 1);
                Vector3f pt(sCorpseOrigin.x + 16.0f * std::sin(a), 0.0f,
                            sCorpseOrigin.z + 16.0f * std::cos(a));
                pt.y = mapMgr ? mapMgr->getMinY(pt.x, pt.z, true) : 0.0f;
                p->resetPosition(pt);
                p->changeMode(PikiMode::FreeMode, n);
                ++ring;
            }
            std::printf("P2_KURAGE_TEKI_FREE_RECRUIT count=%d carriers=%d squad=%d\n", ring, carriers, squad);
            std::fflush(stdout);
        }
    }
    // Natural carry only -- no injected delivery fallback. The FreeMode release
    // latches Transport onto the corpse (carriers > 0) and the receipt lands
    // through pc_p2_preview_deliver -> pc_p2_kurage_receipt. Rate-limited to
    // about once per second now that the tail runs once per frame, and silent
    // once delivered/forgotten (the tail clears itself there).
    if (p2kurage_campaign::corpseProbeDue(++sCorpseProbeTick)) {
        const Vector3f& cp = sCorpsePellet->mSRT.t;
        const float dx = cp.x - sCorpseOrigin.x, dz = cp.z - sCorpseOrigin.z;
        int transport = 0;
        if (pikiMgr) {
            Iterator tp(pikiMgr);
            CI_LOOP(tp) {
                Piki* p = static_cast<Piki*>(*tp);
                if (p && p->isAlive() && p->mMode == PikiMode::TransportMode) ++transport;
            }
        }
        std::printf("P2_KURAGE_TEKI_CORPSE tick=%d x=%.3f z=%.3f moved=%.3f carriers=%d\n",
                    sCorpseProbeTick, cp.x, cp.z, std::sqrt(dx * dx + dz * dz), transport);
        std::fflush(stdout);
    }
    return true;
}
} // namespace

void pc_p2_kurage_teki_reset()
{
    for (auto& x : s) pc_p2_kurage_receiver_owner_invalidated(x.first);
    const int boundBefore = int(s.size());
    const int corpseBefore = int(corpses.size());
    s.clear();
    corpses.clear();
    sCorpseTeki = nullptr;
    sCorpsePellet = nullptr;
    sCorpseProbeTick = 0;
    sCorpseDelivered = false;
    sCaptainParked = false;
    sHoverProbeTick = 0;
    sCorpseDrawLogged = false;
    sShowcase = false;
    sShowcaseBaitSpawned = false;
    sShowcaseBait = nullptr;
    if (boundBefore || corpseBefore) {
        std::printf("P2_KURAGE_TEKI_RESET bound_before=%d corpse_before=%d bound_after=%d corpse_after=%d\n",
                    boundBefore, corpseBefore, int(s.size()), int(corpses.size()));
        std::fflush(stdout);
    }
}
void pc_p2_kurage_teki_forget(BTeki* t)
{
    if (!t) return;
    const bool wasBound = s.count(t) != 0;
    const bool wasCorpse = corpses.count(t) != 0;
    revoke(t);
    corpses.erase(t);
    if (t == sCorpseTeki) {
        // The forget seam recycles the slot: stop the tail so the probe line
        // cannot outlive the corpse (delivered already stops the same way).
        sCorpseTeki = nullptr;
        sCorpsePellet = nullptr;
        sCorpseProbeTick = 0;
        sCorpseDelivered = false;
        sCaptainParked = false;
    }
    if (wasBound || wasCorpse) {
        std::printf("P2_KURAGE_TEKI_FORGET bound=%d corpse=%d remaining=%d\n",
                    int(wasBound), int(wasCorpse), int(s.size() + corpses.size()));
        std::fflush(stdout);
    }
}
bool pc_p2_kurage_teki_is_bound(const BTeki* t) { return t && s.count(const_cast<BTeki*>(t)); }

void pc_p2_kurage_teki_setup()
{
    pc_p2_kurage_teki_reset();
    std::ifstream in("p2-kurage-teki.txt");
    if (!in) return;
    p2kurage::Binding cfg{};
    if (!p2kurage::read(in, cfg) || !tekiMgr) { if (pc_p2_setup_skip(pc_randomizer_p2_bridge(), "Kurage", "staged_config_invalid")) return; }
    unsigned gen = cfg.generator;
    int type = cfg.type;
    Iterator it(tekiMgr);
    CI_LOOP(it)
    {
        auto* t = static_cast<Teki*>(*it);
        if (!t || !t->mGenerator) continue;
        if (pc_randomizer_p2_bridge()) {
            if (pc_p2_campaign_source(t) != 57) continue;
            gen = pc_p2_campaign_token(t);
        } else if (pc_p2_campaign_token(t) != gen) continue;
        if (t->mTekiType != type || (!pc_randomizer_p2_bridge() && s.size())) { if (pc_p2_setup_skip(pc_randomizer_p2_bridge(), "Kurage", "actor_type_mismatch")) return; }
        // Optional visual poses: the corpse/receipt path must not require the
        // converted kurage_*.mod files. When they are absent the P1 host body
        // draws instead (pc_p2_kurage_visual_draw returns false).
        if (!pc_p2_kurage_visual_setup())
            std::printf("P2_KURAGE_VISUAL_MISSING generator=%u (host body draw)\n", gen);
        auto inserted = s.emplace(static_cast<BTeki*>(t), Binding{ gen, type, {} });
        Binding& b = inserted.first->second;
        b.spawnPos = t->mSRT.t;
        refresh(t, b);
        if (!pc_p2_kurage_receiver_setup(t, &b.mouth)) { if (pc_p2_setup_skip(pc_randomizer_p2_bridge(), "Kurage", "receiver_setup_failed")) return; }
        std::printf("P2_KURAGE_TEKI_READY generator=%u type=%d binding=private_adapter\n", gen, type);
        std::printf("P2_KURAGE_CORPSE_READY generator=%u drop=BDT_Normal ledger=onion receipt=corpse:kurage:%u\n", gen, gen);
        // bot-deliver (#871): lane-06 ordinary-delivery source bind so
        // GoalItem::suckMe grants onion:p2:57 instead of the P1 bestiary
        // CHECK (Yellow Wollywog). Mirrors Sokkuri/Sarai/ElecBug and proxy
        // batch2. Single-use: consumed on delivery, cleared on forget.
        // Additive: hover/draw/corpseTail campaign gates untouched.
        pc_randomizer_p2_bind_source(static_cast<PelletView*>(t), 57, gen);
        std::printf("P2_KURAGE_DELIVERY_BIND generator=%u source_id=57\n", gen);
        std::fflush(stdout);
        if (std::getenv("PIKMIN_P2_KURAGE_SHOWCASE")) {
            b.fsmEnabled = true;
            b.fsm = p2kurage::Fsm();
            b.fsm.spawn();
            sShowcase = true;
            std::printf("P2_KURAGE_SHOWCASE_ARMED generator=%u fsm=1 bait=1\n", gen);
            std::fflush(stdout);
        }
    }
}

void pc_p2_kurage_teki_tick(BTeki* t)
{
    ++gTickCalls;
    // Corpse -> Pod carry tail runs even after the live binding is revoked, so it
    // must precede the binding lookup. Keyed to the corpse actor's own tick so
    // the bookkeeping runs once per frame, not once per teki per frame.
    corpseTail(t);
    auto i = s.find(t);
    if (i == s.end()) return;
    if (!t->isAlive()) {
        corpses[t] = i->second.generator;
        sCorpseTeki = t;
        sCorpsePellet = nullptr;
        // Death-drop-to-ground (flyer): an FSM-driven Kurage can die at
        // altitude. Pin the dead body to the floor so the corpse Pellet spawns
        // where FreeMode Pikmin can grasp it. Natural settle, one marker.
        if (mapMgr) {
            const float groundY = mapMgr->getMinY(t->mSRT.t.x, t->mSRT.t.z, true);
            if (std::isfinite(groundY) && t->mSRT.t.y > groundY + 1.0f) {
                std::printf("P2_KURAGE_DEATH_DROP generator=%u from_y=%.3f ground_y=%.3f\n",
                    i->second.generator, t->mSRT.t.y, groundY);
                std::fflush(stdout);
                t->finishFlying();
                t->mSRT.t.y = groundY;
                t->mVelocity.set(0.0f, 0.0f, 0.0f);
            }
        }
        sCorpseOrigin = t->mSRT.t;
        sCorpseProbeTick = 0;
        sCorpseDelivered = false;
        std::printf("P2_KURAGE_TEKI_DEAD generator=%u\n", i->second.generator);
        std::fflush(stdout);
        revoke(t);
        return;
    }
    Binding& b = i->second;
    const float dt = gsys->getFrameTime();
    if (!b.fsmEnabled) {
        if (kurageCampaignMode()) {
            // Campaign hover: the P1 Frog host keeps its natural locomotion
            // (no finishFlying, no y-pin, no seek toward Pikmin), so its
            // collision stays sane and the body stays killable on the ground.
            // The Jellyfloat floats as a visual-only offset in the draw path.
            // The ported FSM float/descend was rejected here: its 90u cruise
            // plus patrol wander would put the bell out of Pikmin melee reach
            // and fight the host's jump/land each tick (unkillable risk).
            if (mapMgr && ++sHoverProbeTick % 60 == 0) {
                const float groundY = mapMgr->getMinY(t->mSRT.t.x, t->mSRT.t.z, true);
                std::printf("P2_KURAGE_HOVER tick=%d y=%.3f ground_y=%.3f above=%.3f visual_above=%.3f\n",
                            sHoverProbeTick, t->mSRT.t.y, groundY,
                            t->mSRT.t.y - groundY,
                            t->mSRT.t.y + p2kurage_campaign::kHoverHeight - groundY);
                std::fflush(stdout);
            }
        } else {
            // Injected engagement seal: make the P1 proxy reachable and killable by
            // the ordinary FreeMode squad (fixture concession, see groundAndSeal).
            groundAndSeal(t);
        }
        refresh(t, b);
        pc_p2_kurage_receiver_update(dt, true, t->mHealth > 0.0f, false);
        return;
    }

    // Showcase target: after the actor has demonstrated its autonomous patrol,
    // seed one live Pikmin into its suction window so the source Attack state's
    // real receiver can be observed. FreeMode keeps the candidate from biting the
    // body before the suction owns it; it is repositioned until the receiver
    // takes control, exactly like a Pikmin walking under the body.
    if (sShowcase && !sShowcaseBaitSpawned && b.fsmTicks > 300
        && pikiMgr && naviMgr && naviMgr->getNavi()) {
        Piki* bait = static_cast<Piki*>(pikiMgr->birth());
        if (bait) {
            bait->init(naviMgr->getNavi());
            bait->initColor(Red);
            bait->setFlower(Leaf);
            bait->changeMode(PikiMode::FreeMode, naviMgr->getNavi());
            bait->resetPosition(Vector3f(t->mSRT.t.x, t->mSRT.t.y - 30.0f, t->mSRT.t.z));
            sShowcaseBait = bait;
            sShowcaseBaitSpawned = true;
            std::printf("P2_KURAGE_SHOWCASE_BAIT spawned=1 x=%.3f y=%.3f z=%.3f\n",
                        bait->mSRT.t.x, bait->mSRT.t.y, bait->mSRT.t.z);
            std::fflush(stdout);
        }
    }
    if (sShowcaseBait && sShowcaseBait->isAlive()
        && !pc_p2_kurage_receiver_controls(sShowcaseBait))
        sShowcaseBait->resetPosition(Vector3f(t->mSRT.t.x, t->mSRT.t.y - 30.0f, t->mSRT.t.z));

    // Source flight lifecycle authority for the ordinary generated actor.
    p2kurage::In in;
    in.deltaTime = dt;
    in.health = t->mHealth;
    // Mouth-travel Pikmin are not body-stuck; only stomach-attached ones count
    // toward the source fall/flick threshold.
    in.stuckPikminCount = pc_p2_kurage_receiver_stomach_count();
    in.isFlying = true;
    in.mapY = mapMgr ? mapMgr->getMinY(t->mSRT.t.x, t->mSRT.t.z, false) : 0.0f;
    in.positionY = t->mSRT.t.y;
    in.distToTargetXZ = b.lastDistToGoal;
    in.targetFound = findSuctionTarget(t) != nullptr || pc_p2_kurage_receiver_count() > 0;
    in.suckTarget = in.targetFound;
    in.suckAny = in.targetFound;
    in.motionFrame = b.attackPlaying ? b.attackPlayer.frame() : 0.0f;
    bool motionEnd = false;
    if (!b.attackPlaying && ++b.motionTimer >= kFsmMotionFrames) { b.motionTimer = 0; motionEnd = true; }
    in.motionFinished = b.motionFinished || motionEnd;
    in.keyEvent = b.pendingKey;
    b.pendingKey = p2kurage::KeyEvent::None;
    b.motionFinished = false;

    const p2kurage::Out out = b.fsm.tick(in);
    ++b.fsmTicks;
    t->mSRT.t.y += out.heightVelocity * dt;
    // Host walkToTarget: the ordinary actor flies Move patrol / Chase pursuit.
    {
        Vector3f goal;
        bool haveGoal = false;
        if (out.state == p2kurage::State::Move) {
            if (!b.hasPatrol) { pickPatrol(b); b.hasPatrol = true; }
            goal = b.patrolTarget;
            haveGoal = true;
        } else if (out.state == p2kurage::State::Chase) {
            Piki* chase = findSuctionTarget(t);
            if (chase) { goal = chase->mSRT.t; haveGoal = true; }
        } else {
            b.hasPatrol = false;
        }
        if (haveGoal) {
            const float dx = goal.x - t->mSRT.t.x;
            const float dz = goal.z - t->mSRT.t.z;
            const float dist = std::sqrt(dx * dx + dz * dz);
            b.lastDistToGoal = dist;
            if (dist > 1.0f && std::isfinite(dt) && dt > 0.0f) {
                float step = kPatrolSpeed * dt;
                if (step > dist) step = dist;
                t->mSRT.t.x += dx / dist * step;
                t->mSRT.t.z += dz / dist * step;
            }
        } else {
            b.lastDistToGoal = 1e9f;
        }
    }
    if (out.state == p2kurage::State::Attack && out.motionChanged && !b.attackPlaying) {
        if (b.attackPlayer.start(kAttackMotion)) {
            b.attackPlaying = true;
            b.autoAdmissions = 0;
            b.motionTimer = 0;
        }
    }
    tickAttack(b, dt * kAttackFramesPerSecond);
    refresh(t, b);
    if (++b.logTimer >= 30) {
        b.logTimer = 0;
        std::printf("P2_KURAGE_MOVE tick=%d x=%.3f y=%.3f z=%.3f state=%d motion=%d anim=%.2f\n",
                    b.fsmTicks, t->mSRT.t.x, t->mSRT.t.y, t->mSRT.t.z,
                    (int)out.state, (int)out.motion,
                    b.attackPlaying ? b.attackPlayer.frame() : 0.0f);
        std::fflush(stdout);
    }
    if ((int)out.state != b.lastLoggedState) {
        b.lastLoggedState = (int)out.state;
        std::printf("P2_KURAGE_STATE tick=%d state=%d motion=%d altitude=%.3f\n",
                    b.fsmTicks, (int)out.state, (int)out.motion, out.altitude);
        std::fflush(stdout);
    }
    if ((out.isSucking || b.sucking)
        && pc_p2_kurage_receiver_scan_admit(0.0f, kSourceAttackRadius, kMaxAutoAdmissions, true) > 0)
        ++b.autoAdmissions;
    pc_p2_kurage_receiver_update(dt, true, t->mHealth > 0.0f, false);
}

bool pc_p2_kurage_teki_draw(BTeki* t, Graphics& gfx, const Matrix4f& matrix, bool corpse)
{
    if (corpse) {
        // The live binding is revoked at death, so a corpse resolves through
        // the corpses map. Draw the Kurage dead pose when the converted clips
        // exist (dead1/dead2 ship: optional_loaded=8/8), else the last/idle
        // pose -- never the stock P1 Frog body the fallthrough would draw.
        // The corpse Pellet itself stays naturally carriable (grasp -> carry
        // to Onion -> pc_p2_kurage_receipt); only the drawn model changes.
        if (corpses.count(t) == 0) return false;
        Shape* dead = pc_p2_kurage_visual_shape("dead1");
        const char* pose = "dead1";
        if (!dead) { dead = pc_p2_kurage_visual_shape("dead2"); pose = "dead2"; }
        if (!dead) return pc_p2_kurage_visual_draw(t, gfx, matrix, true);
        dead->updateAnim(gfx, matrix, nullptr, t);
        dead->drawshape(gfx, *gfx.mCamera, nullptr);
        if (!sCorpseDrawLogged) {
            sCorpseDrawLogged = true;
            std::printf("P2_KURAGE_CORPSE_DRAW corpse=1 pose=%s\n", pose);
            std::fflush(stdout);
        }
        return true;
    }
    auto i = s.find(t);
    if (i == s.end()) return false;
    if (i->second.fsmEnabled) {
        Shape* shape = pc_p2_kurage_visual_shape(
            pc_p2_kurage_visual_motion_for_state((int)i->second.fsm.state()));
        if (shape) {
            shape->updateAnim(gfx, matrix, nullptr, t);
            shape->drawshape(gfx, *gfx.mCamera, nullptr);
            return true;
        }
    }
    if (kurageCampaignMode()) {
        // Campaign hover, visual half: the actor stays grounded (see the tick
        // path) and only the drawn bell floats. Camera-space +Y reads as up
        // on screen; on-screen look stays owner-verified.
        Matrix4f floatMat;
        floatMat.set(matrix);
        floatMat.mMtx[1][3] += p2kurage_campaign::kHoverHeight;
        return pc_p2_kurage_visual_draw(t, gfx, floatMat, false);
    }
    return pc_p2_kurage_visual_draw(t, gfx, matrix, corpse);
}

void pc_p2_kurage_teki_fsm_enable(bool enable)
{
    for (auto& x : s) {
        x.second.fsmEnabled = enable;
        if (enable) { x.second.fsm = p2kurage::Fsm(); x.second.fsm.spawn(); }
    }
}
bool pc_p2_kurage_teki_fsm_enabled(const BTeki* t)
{
    auto i = s.find(const_cast<BTeki*>(t));
    return i != s.end() && i->second.fsmEnabled;
}
int pc_p2_kurage_teki_fsm_state(const BTeki* t)
{
    auto i = s.find(const_cast<BTeki*>(t));
    return i == s.end() ? -1 : (int)i->second.fsm.state();
}
int pc_p2_kurage_teki_auto_admissions(const BTeki* t)
{
    auto i = s.find(const_cast<BTeki*>(t));
    return i == s.end() ? 0 : i->second.autoAdmissions;
}
int pc_p2_kurage_teki_fsm_ticks(const BTeki* t)
{
    auto i = s.find(const_cast<BTeki*>(t));
    return i == s.end() ? -1 : i->second.fsmTicks;
}
int pc_p2_kurage_teki_tick_calls()
{
    return gTickCalls;
}

bool pc_p2_kurage_receipt(PelletView* view, unsigned& generator)
{
    if (!view) return false;
    BTeki* t = static_cast<BTeki*>(view);
    auto i = s.find(t);
    if (i != s.end()) { generator = i->second.generator; return true; }
    auto c = corpses.find(t);
    if (c == corpses.end()) return false;
    generator = c->second;
    // Natural Pod delivery of the carcass: the preview calls this during
    // pc_p2_preview_deliver, so record it to end the free-roam cleanly.
    sCorpseDelivered = true;
    return true;
}

int pc_p2_kurage_bound_count()
{
    return int(s.size() + corpses.size());
}
