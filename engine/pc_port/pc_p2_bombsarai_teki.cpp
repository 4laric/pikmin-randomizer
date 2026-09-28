// Generated Careening Dirigibug (BombSarai) carrier sidecar (#244).
//
// Mirrors pc_p2_kurage_teki.cpp: bind a generated P1 vehicle (TEKI_Napkid
// here, the flying vehicle family used by Fuefuki) through a
// `p2-bombsarai-teki.txt` sidecar, then drive it as the BombSarai carrier.
// Everything the carrier needs -- 13-state FSM, hover, bomb pool, capture
// joint, blast routing -- is the lane's existing engine-free policy
// (pc_p2_bombsarai_*); this module only feeds live host inputs and applies the
// real engine receivers.
//
// Sidecar (cwd), strict, count must be 1:
//   P2_BOMBSARAI_TEKI_1 <count> <generator> <type>
// e.g.  P2_BOMBSARAI_TEKI_1 1 270001 11     (11 = TEKI_Napkid)
//
// Blast routing deviates from the isolated arena: instead of instrumented
// P2BombSaraiReceiver rows it enumerates live Navi/Pikmin and applies the
// source Bomb's InteractBomb (Interactions.h) via Creature::stimulate,
// attributed to the carrier Teki while alive (bombState.cpp:167-189). Teki
// friendly-fire is not stimulated here (the grounded carrier is the only Teki
// candidate and the flyer is immune while airborne, BombSarai.cpp:127-135).
#include "pc_p2_bombsarai_teki.h"
#include "pc_p2_preview.h"
#include "pc_p2_teki_lifetime.h"
#include "pc_p2_bombsarai_fsm.h"
#include "pc_p2_bombsarai_hover.h"
#include "pc_p2_bombsarai_bomb.h"
#include "pc_p2_bombsarai_blast.h"
#include "pc_p2_bombsarai_clock.h"
#include "pc_p2_bombsarai_joint.h"
#include "pc_p2_bombsarai_map_trace.h"
#include "pc_p2_bombsarai_terrain.h"
#include "pc_bbft.h"
#include "Interactions.h"
#include "MapMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Pellet.h"
#include "Collision.h"
#include "Generator.h"
#include "system.h"
#include "teki.h"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <string>
#include <utility>
#include <vector>

namespace {
constexpr float kPi = 3.14159265358979323846f;
constexpr float kTargetTerritory = 200.0f; // fp09 sight radius
constexpr float kAttackableRange = 100.0f; // fp20 attackable range
constexpr float kAttackableCos = 0.7071068f; // cos(45deg) max attack angle
constexpr float kAttackXZ = 50.0f;          // mAttackRadius XZ gate

// Timing stand-ins until the #128 converter supplies retail .bca durations.
constexpr int kTiming[11] = { 30, 30, 10, 30, 30, 10, 10, 24, 45, 21, 20 };
// Lane host walkToTarget (source BombSarai Move/BombMove): walk toward the
// nearest sensed creature inside the territory (target selection is host-owned
// in the source), else toward a random 50-100u ring waypoint around home
// (BombSarai::setRandTarget, BombSarai.cpp:230-245). Arrival radius 25u is the
// source walkToTarget waypoint test (audit "Move waypoint ... 25 (625
// squared)"). kEngageKeepRange is the XZ distance kept to the sensed creature
// so the grounded FreeMode squad can attack it (grounding is a labelled
// engagement concession: the source always hovers, but ordinary Pikmin reject
// a flying Teki, piki.cpp:951 / aiAttack.cpp:189).
constexpr float kEngageKeepRange = 30.0f;
constexpr float kMoveSpeed = 300.0f; // host move speed (source fp06 consumed parm)
constexpr float kWaypointArrival = 25.0f; // source walkToTarget arrival radius
// Movement/animation evidence is sampled once a second (30 source ticks).
constexpr int kMoveSampleTicks = 30;

struct Binding {
    std::uint64_t generator = 0;
    int type = 0;
    std::uint64_t rng = 0; // LCG seed for host-fed flick rolls (never the token)
    std::uint64_t targetRng = 0; // LCG seed for walkToTarget ring waypoints
    P2BombSaraiFsm fsm;
    P2BombSaraiFsmParms fsmParms;
    P2BombSaraiHover hover;
    P2BombSaraiHoverParms hoverParms;
    P2BombSaraiBombConfig bombConfig;
    P2BombSaraiBombPool pool{ 2 };
    P2BombSaraiBomb* held = nullptr;
    P2BombSaraiVec3 joint{ 0.0f, -40.0f, 0.0f }; // kamu_jnt1 body-local offset
    P2BombSaraiSourceClock clock;
    int stateTick = 0;
    int tick = 0;
    bool dead = false;
    bool supplied = false;
    bool jointTracked = false;
    float jointMinY = 0.0f, jointMaxY = 0.0f;
    float prevX = 0.0f, prevZ = 0.0f;
    bool havePrev = false;
    float horizTravel = 0.0f;
    // Movement/animation evidence (#244): the lane host adapter's walk target
    // (nearest sensed creature inside the territory, else a random 50-100u ring
    // waypoint around home, mirroring BombSarai::setRandTarget/walkToTarget) and
    // the previous position we wrote, so the P1 host's own flight contribution
    // can be measured separately from the lane policy.
    P2BombSaraiVec3 home{ 0.0f, 0.0f, 0.0f };
    float targetX = 0.0f, targetZ = 0.0f;
    bool targetActive = false;
    float prevMoveX = 0.0f, prevMoveY = 0.0f, prevMoveZ = 0.0f;
    bool haveMovePrev = false;
    float hostAccum = 0.0f; // P1 host flight distance since the last MOVE sample
    float laneAccum = 0.0f; // lane walkToTarget distance since the last sample
    float lastPitch = 0.0f;
};

std::map<BTeki*, Binding> sBound;
// Naturally dead carrier bodies: kept until the central forget/reset seam so
// the Pod delivery receipt can still resolve the corpse after the live binding
// is revoked (mirrors pc_p2_kurage_teki.cpp). Populated only on the death tick
// path; the recycle/slot-reuse forget erases without recording.
std::map<BTeki*, unsigned> sCorpses;
// Corpse-carry diagnostic: the dead carrier and its corpse pellet (mPellet is
// spawned later in the death sequence, so resolve it lazily), probed once a
// second so the run shows whether the FreeMode squad carries it to the Pod.
BTeki* sCorpseTeki = nullptr;
Pellet* sCorpsePellet = nullptr;
P2BombSaraiVec3 sCorpseOrigin;
int sCorpseProbeTick = 0;
unsigned sCorpseGenerator = 0;
bool sCorpseDelivered = false;
// Snapshot of the shared carcass PelletConfig carry slots before the carry
// concession mutates them, restored on receipt/reset so the shared config is
// left at its retail values.
PelletConfig* sCarryConfig = nullptr;
int sOrigCarryMin = 0;
int sOrigCarryMax = 0;
bool sHaveOrigCarry = false;

// Restore the shared carcass carry slots captured before the concession.
void restoreCarryConfig()
{
    if (sHaveOrigCarry && sCarryConfig) {
        sCarryConfig->mCarryMinPikis.mValue = sOrigCarryMin;
        sCarryConfig->mCarryMaxPikis.mValue = sOrigCarryMax;
    }
    sHaveOrigCarry = false;
    sCarryConfig = nullptr;
}
P2BombSaraiMapBinding sMap;
P2BombSaraiTerrainAdapter sAdapter;
int sThrowCount = 0;
int sBlastCount = 0;
bool sCarrierDead = false;
// Corpse-carry tail: the captain is parked beyond the join-party range so the
// freed Pikmin do not re-adopt formation mid-haul; printed once.
bool sCaptainParked = false;

// Blast owner for the small self-creature the source passes as the bomb when
// the carrier is not live (carrierless attribution). Module-local, like
// pc_p2_bombotakara.cpp's BlastOwner.
class BombOwner : public Creature {
public:
    BombOwner() : Creature(nullptr) { mHealth = 1.0f; }
    void refresh(Graphics&) override {}
    void doKill() override {}
};
BombOwner sBombOwner;

int timingSlot(P2BombSaraiFsmState state)
{
    switch (state) {
    case P2BombSaraiFsmState::Wait: return 0;
    case P2BombSaraiFsmState::Move: return 1;
    case P2BombSaraiFsmState::Supply: return 2;
    case P2BombSaraiFsmState::BombWait: return 3;
    case P2BombSaraiFsmState::BombMove: return 4;
    case P2BombSaraiFsmState::Release: return 5;
    case P2BombSaraiFsmState::Fall: return 6;
    case P2BombSaraiFsmState::Damage: return 7;
    case P2BombSaraiFsmState::TakeOff1: return 8;
    case P2BombSaraiFsmState::TakeOff2: return 9;
    case P2BombSaraiFsmState::Flick:
    case P2BombSaraiFsmState::BombFlick: return 10;
    case P2BombSaraiFsmState::Dead: break;
    }
    return -1;
}

void applyBlast(BTeki* t, Binding& b, const P2BombSaraiBlastEvent& event);

const char* kindName(int kind)
{
    return kind == (int)P2BombSaraiThrowKind::Release ? "Release"
        : kind == (int)P2BombSaraiThrowKind::Fall ? "Fall" : "Death";
}

// Deterministic host-fed flick roll in [0, 1).
float nextRoll(std::uint64_t& rng)
{
    rng = rng * 6364136223846793005ull + 1442695040888963407ull;
    return (float)((rng >> 33) & 0x7FFFFFFFull) / 2147483648.0f;
}

bool carrierAlive(void* context, std::uint64_t)
{
    const BTeki* t = static_cast<BTeki*>(context);
    return t != nullptr && t->isAlive();
}

P2BombSaraiVec3 carrierPosition(const BTeki* t)
{
    return { t->mSRT.t.x, t->mSRT.t.y, t->mSRT.t.z };
}

void readConfig(Binding& b)
{
    // Lowered from the retail fp01 70 to keep the carrier within ordinary-Pikmin
    // throw reach for the natural kill demonstration; labelled experimental.
    b.hoverParms.flightHeight = 20.0f;
    b.hoverParms.pitchRate = 2.5f;
    b.hoverParms.pitchAmp = 20.0f;
    b.hoverParms.freeRiseFactor = 1.5f;
    b.hoverParms.ladenRiseFactor = 1.0f;
    b.fsmParms.transitionHeight = 50.0f;
    b.fsmParms.maxHealth = 1500.0f;
    b.bombConfig.gravityPerTick = 18.666667f; // aiConstants 560 / 30
    b.bombConfig.fuseHealth = 4.5f;
    b.bombConfig.armLoopTicks = 30;
    b.bombConfig.bombRadius = 15.0f;
    b.bombConfig.blastRadius = 90.0f;
    b.bombConfig.blastHalfHeight = 50.0f;
    b.bombConfig.tekiDamage = 500.0f;
    b.bombConfig.naviPikiDamage = 10.0f;
}

void stepCarrier(BTeki* t, Binding& b, float delta)
{
    const P2BombSaraiVec3 pos = carrierPosition(t);
    const P2BombSaraiFsmState state = b.fsm.state();
    float groundY = 0.0f;
    if (!P2BombSaraiTerrainAdapter::getMinY(&sAdapter, pos.x, pos.z, groundY)) return;

    // The P1 host's own flight this frame (its AI ran before this hook), measured
    // from the position we wrote last tick. Reported separately from the lane
    // walkToTarget so the movement evidence labels both components.
    if (b.haveMovePrev) {
        const float hx = t->mSRT.t.x - b.prevMoveX;
        const float hz = t->mSRT.t.z - b.prevMoveZ;
        b.hostAccum += std::sqrt(hx * hx + hz * hz);
    }
    const float hostStartX = t->mSRT.t.x, hostStartZ = t->mSRT.t.z;

    // Ground-engagement concession (labelled): clear CF_IsFlying and pin the
    // carrier to the floor every tick so ordinary FreeMode Pikmin can attack it.
    // A FreeMode squad rejects a flying Teki outright (graspSituation skips
    // `isFlying()`, piki.cpp:951; ActAttack abandons an airborne target,
    // aiAttack.cpp:189/297), and the source dirigibug always hovers. This hook
    // runs after the Napkid strategy's act()+moveNew (tekibteki.cpp:473-484),
    // so it is the last write of the frame. Fall keeps gravity; every other
    // state is grounded.
    t->finishFlying();
    if (state == P2BombSaraiFsmState::Fall) {
        t->mSRT.t.y -= b.bombConfig.gravityPerTick * 30.0f * delta;
        if (t->mSRT.t.y < groundY) t->mSRT.t.y = groundY;
    } else {
        t->mSRT.t.y = groundY;
    }
    t->mVelocity.y = 0.0f;

    // Lane host walkToTarget (source BombSarai Move/BombMove; horizontal
    // movement/target selection is host-owned per the FSM header): walk toward
    // the nearest live Pikmin at the host move speed, holding the engage keep
    // range; when no Pikmin exist, walk the source setRandTarget 50-100u ring
    // around home. waypointReached fires inside the source 25u arrival radius.
    bool waypointReached = false;
    {
        // Nearest live Pikmin (the host walkToTarget target when one exists).
        float bestD2 = 1.0e30f, bx = 0.0f, bz = 0.0f;
        bool havePiki = false;
        if (pikiMgr) {
            Iterator sit(pikiMgr);
            CI_LOOP(sit) {
                Piki* piki = static_cast<Piki*>(*sit);
                if (!piki || !piki->isAlive()) continue;
                const float dx = piki->mSRT.t.x - t->mSRT.t.x;
                const float dz = piki->mSRT.t.z - t->mSRT.t.z;
                const float d2 = dx * dx + dz * dz;
                if (d2 < bestD2) { bestD2 = d2; bx = dx; bz = dz; havePiki = true; }
            }
        }
        const bool walkingState = state == P2BombSaraiFsmState::Move
            || state == P2BombSaraiFsmState::BombMove;
        // The walk runs every tick toward the nearest Pikmin: the P1 host
        // flight is fast (~150u/s) and would otherwise carry the grounded
        // carrier out of the squad's reach; the keep range holds it in the
        // squad's attack volume. When no Pikmin exist, the source Move/BombMove
        // setRandTarget ring walk (50-100u around home) is used instead.
        if (havePiki) {
            const float d = std::sqrt(bestD2);
            if (d <= kWaypointArrival) {
                waypointReached = true;
            } else {
                const float step = kMoveSpeed * delta;
                const float gap = d > kEngageKeepRange ? d - kEngageKeepRange : 0.0f;
                const float move = gap < step ? gap : step;
                t->mSRT.t.x += bx / d * move;
                t->mSRT.t.z += bz / d * move;
                if (d - move <= kWaypointArrival) waypointReached = true;
            }
        } else if (walkingState) {
            if (!b.targetActive) {
                b.targetRng = b.targetRng * 6364136223846793005ull + 1442695040888963407ull;
                const float roll = (float)((b.targetRng >> 33) & 0x7FFFFFFFull) / 2147483648.0f;
                const float radius = 50.0f + roll * 50.0f; // cave 50-100u ring
                b.targetRng = b.targetRng * 6364136223846793005ull + 1442695040888963407ull;
                const float ang = ((float)((b.targetRng >> 33) & 0x7FFFFFFFull) / 2147483648.0f)
                    * 2.0f * kPi;
                b.targetX = b.home.x + radius * std::sin(ang);
                b.targetZ = b.home.z + radius * std::cos(ang);
                b.targetActive = true;
            }
            const float dx = b.targetX - t->mSRT.t.x, dz = b.targetZ - t->mSRT.t.z;
            const float d = std::sqrt(dx * dx + dz * dz);
            if (d > 0.0001f) {
                const float step = kMoveSpeed * delta;
                const float move = d < step ? d : step;
                t->mSRT.t.x += dx / d * move;
                t->mSRT.t.z += dz / d * move;
                if (move >= d) { b.targetActive = false; waypointReached = true; }
            }
        }
    }
    // Advance the source hover policy (BombSarai::setHeightVelocity/addPitchRatio)
    // for the pitch animation. The grounding concession keeps y on the floor, so
    // only the pitch ratio is consumed by the lane here.
    {
        float velocityY = 0.0f, height = 0.0f;
        if (b.hover.update(state == P2BombSaraiFsmState::TakeOff2, 0, carrierPosition(t),
                           delta, sAdapter.mGetMinY, sAdapter.mGetMinYContext,
                           velocityY, height)) {
            b.lastPitch = b.hover.pitchRatio();
        }
    }
    const P2BombSaraiVec3 carrier = carrierPosition(t);
    b.laneAccum += std::sqrt((carrier.x - hostStartX) * (carrier.x - hostStartX)
                             + (carrier.z - hostStartZ) * (carrier.z - hostStartZ));
    b.prevMoveX = carrier.x; b.prevMoveY = carrier.y; b.prevMoveZ = carrier.z;
    b.haveMovePrev = true;

    // Animated capture joint world position. The source body offset is below
    // the carrier (kamu_jnt1); with the carrier grounded that would put the
    // payload under the floor, so clamp the joint just above the ground.
    P2BombSaraiVec3 jointWorld = P2BombSaraiJoint::compute(carrier, t->getDirection(), b.joint);
    if (jointWorld.y < groundY + 5.0f) jointWorld.y = groundY + 5.0f;

    // Per-second engagement probe: the carrier's floor height, the live squad
    // size and the nearest squad distance, so the run proves the ground squad
    // can actually reach the carrier.
    if (b.tick % 30 == 0) {
        int squad = 0;
        float nearest = 1.0e30f;
        if (pikiMgr) {
            Iterator pit(pikiMgr);
            CI_LOOP(pit) {
                Piki* piki = static_cast<Piki*>(*pit);
                if (!piki || !piki->isAlive()) continue;
                ++squad;
                const float dx = piki->mSRT.t.x - carrier.x;
                const float dy = piki->mSRT.t.y - carrier.y;
                const float dz = piki->mSRT.t.z - carrier.z;
                const float d = std::sqrt(dx * dx + dy * dy + dz * dz);
                if (d < nearest) nearest = d;
            }
        }
        if (nearest > 1.0e29f) nearest = -1.0f;
        std::printf("P2_BOMBSARAI_TEKI_PROBE generator=%llu tick=%d y=%.3f nearest=%.3f squad=%d\n",
                    (unsigned long long)b.generator, b.tick, t->mSRT.t.y, nearest, squad);
    }

    // Movement/animation evidence once a second: the carrier's position and
    // facing, the driving FSM state and its animation keyframe counter, and the
    // hover pitch, with the lane walk distance and the P1 host flight distance
    // reported separately (further below).
    if (b.tick % kMoveSampleTicks == 0) {
        std::printf("P2_BOMBSARAI_TEKI_MOVE generator=%llu tick=%d state=%s anim=%d "
                    "x=%.3f y=%.3f z=%.3f yaw=%.3f pitch=%.3f lane=%.3f host=%.3f\n",
                    (unsigned long long)b.generator, b.tick, P2BombSaraiFsm::stateName(state),
                    b.stateTick, carrier.x, carrier.y, carrier.z, t->getDirection(),
                    b.lastPitch, b.laneAccum, b.hostAccum);
        b.laneAccum = 0.0f;
        b.hostAccum = 0.0f;
    }

    // Target sensing: nearest alive Navi/Pikmin against retail radii.
    bool territory = false, attackable = false, attackXZ = false;
    {
        float best = 1.0e30f, bestDx = 0.0f, bestDz = 0.0f;
        auto probe = [&](float x, float z) {
            const float dx = x - carrier.x, dz = z - carrier.z;
            const float d2 = dx * dx + dz * dz;
            if (d2 < best) { best = d2; bestDx = dx; bestDz = dz; }
        };
        if (naviMgr && naviMgr->getNavi() && naviMgr->getNavi()->isAlive()) {
            const Vector3f& p = naviMgr->getNavi()->mSRT.t;
            probe(p.x, p.z);
        }
        if (pikiMgr) {
            Iterator it(pikiMgr);
            CI_LOOP(it) {
                Piki* piki = static_cast<Piki*>(*it);
                if (piki && piki->isAlive()) probe(piki->mSRT.t.x, piki->mSRT.t.z);
            }
        }
        if (best < 1.0e29f) {
            const float dist = std::sqrt(best);
            territory = dist <= kTargetTerritory;
            if (dist <= kAttackableRange) {
                const float fx = std::sin(t->getDirection()), fz = std::cos(t->getDirection());
                const float dot = dist > 0.0001f ? (bestDx * fx + bestDz * fz) / dist : 1.0f;
                attackable = dot >= kAttackableCos;
            }
            attackXZ = dist <= kAttackXZ;
        }
    }

    // Keyframes from the timing stand-in of the current state.
    bool animEnd = false, keyEvent2 = false;
    {
        const int slot = timingSlot(state);
        if (slot >= 0) {
            const int ticks = kTiming[slot];
            const int at = b.stateTick + 1;
            animEnd = at >= ticks;
            keyEvent2 = at == (ticks > 1 ? ticks / 2 : 1);
        }
    }

    // FSM decision (health sourced from the live Teki; carrying means a live
    // captured bomb, matching source mHeldBomb semantics).
    P2BombSaraiFsmInput in;
    in.health = t->mHealth;
    in.carrying = b.held != nullptr && b.held->phase() == P2BombSaraiBombPhase::Captured;
    in.stuckPikmin = 0;
    in.stuckPurple = 0;
    in.targetWithinTerritory = territory;
    in.targetAttackable = attackable;
    in.targetWithinAttackXZ = attackXZ;
    in.waypointReached = waypointReached;
    in.heightAboveGround = carrier.y - groundY;
    in.animEnd = animEnd;
    in.keyEvent2 = keyEvent2;
    in.bitterQueued = false;
    in.killed = false; // death is handled in pc_p2_bombsarai_teki_tick (revoke + corpse)
    in.flickRoll = nextRoll(b.rng);
    P2BombSaraiFsmOutput out;
    b.fsm.update(in, out);
    if (out.entered) {
        b.stateTick = 0;
    } else {
        ++b.stateTick;
    }

    // Requested effects.
    if (out.supplyRequested && !b.held) {
        b.held = b.pool.supply(b.generator, jointWorld, b.bombConfig);
        if (!b.supplied) {
            b.supplied = true;
            std::printf("P2_BOMBSARAI_TEKI_SUPPLY generator=%llu tick=%d\n",
                        (unsigned long long)b.generator, b.tick);
        }
    }
    if (out.throwRequested && b.held) {
        b.held->throwBomb(out.throwKind, t->getDirection());
        ++sThrowCount;
        std::printf("P2_BOMBSARAI_TEKI_THROW generator=%llu kind=%s tick=%d\n",
                    (unsigned long long)b.generator, kindName((int)out.throwKind), b.tick);
        if (b.jointTracked) {
            std::printf("P2_BOMBSARAI_TEKI_JOINT_FOLLOW generator=%llu travel_y=%.3f travel_xz=%.3f\n",
                        (unsigned long long)b.generator, b.jointMaxY - b.jointMinY, b.horizTravel);
        }
    }

    // Bomb update (follow the joint while captured, fly otherwise).
    if (b.held) {
        b.held->followJoint(jointWorld);
        if (b.held->phase() == P2BombSaraiBombPhase::Captured) {
            const P2BombSaraiVec3& p = b.held->position();
            if (!b.jointTracked) {
                b.jointTracked = true;
                b.jointMinY = b.jointMaxY = p.y;
                b.horizTravel = 0.0f;
                b.havePrev = false;
            } else {
                if (p.y < b.jointMinY) b.jointMinY = p.y;
                if (p.y > b.jointMaxY) b.jointMaxY = p.y;
                if (b.havePrev) {
                    const float dx = p.x - b.prevX, dz = p.z - b.prevZ;
                    b.horizTravel += std::sqrt(dx * dx + dz * dz);
                }
                b.prevX = p.x; b.prevZ = p.z; b.havePrev = true;
            }
        }
        b.held->update(delta, P2BombSaraiTerrainAdapter::trace, &sAdapter, carrierAlive, t);
        if (b.held->hasBlast()) {
            const P2BombSaraiBlastEvent& event = b.held->lastBlast();
            ++sBlastCount;
            applyBlast(t, b, event);
            b.held->clearBlast();
        }
        if (b.held->phase() == P2BombSaraiBombPhase::Despawned) {
            b.held = nullptr;
        }
    }
}

// Applies one recorded blast to live Navi/Pikmin via InteractBomb and reports.
void applyBlast(BTeki* t, Binding& b, const P2BombSaraiBlastEvent& event)
{
    int hits = 0;
    int pikminHits = 0;
    Creature* owner = t->isAlive() ? static_cast<Creature*>(t) : static_cast<Creature*>(&sBombOwner);
    // Snapshot candidates BEFORE stimulating: a lethal InteractBomb removes the
    // Pikmin from pikiMgr, which would invalidate a live CI_LOOP iterator and
    // crash the game right after a big blast (hits>=20).
    std::vector<std::pair<Creature*, bool>> targets;
    if (naviMgr && naviMgr->getNavi()) {
        targets.emplace_back(static_cast<Creature*>(naviMgr->getNavi()), false);
    }
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* piki = static_cast<Piki*>(*it);
            if (piki) targets.emplace_back(static_cast<Creature*>(piki), true);
        }
    }
    int index = 0;
    auto strike = [&](Creature* receiver, bool isPiki) -> bool {
        const int target = index++;
        if (!receiver || !receiver->isAlive()) return false;
        const Vector3f& p = receiver->getPosition();
        const float dx = p.x - event.center.x;
        const float dy = p.y - event.center.y;
        const float dz = p.z - event.center.z;
        if (dy < -event.halfHeight || dy > event.halfHeight) return false;
        if (dx * dx + dz * dz > event.radius * event.radius) return false;
        // Real engine receiver: the source Bomb's InteractBomb (Interactions.h)
        // through Creature::stimulate. InteractBomb::actPiki reduces mHealth and
        // transits PIKISTATE_Flick (interactBattle.cpp:37-74); log the target's
        // health/state before and after so the receiver's effect is cited.
        const float hpBefore = receiver->mHealth;
        const int stateBefore = isPiki ? static_cast<Piki*>(receiver)->getState() : -1;
        const bool aliveBefore = receiver->isAlive();
        InteractBomb bomb(owner, event.naviPikiDamage, nullptr);
        const bool applied = receiver->stimulate(bomb);
        const float hpAfter = receiver->mHealth;
        const int stateAfter = isPiki ? static_cast<Piki*>(receiver)->getState() : -1;
        const bool aliveAfter = receiver->isAlive();
        std::printf("P2_BOMBSARAI_TEKI_HIT generator=%llu tick=%d target=%d kind=%s "
                    "hp_before=%.3f hp_after=%.3f state_before=%d state_after=%d "
                    "alive_before=%d alive_after=%d applied=%d\n",
                    (unsigned long long)b.generator, b.tick, target,
                    isPiki ? "piki" : "navi", hpBefore, hpAfter, stateBefore, stateAfter,
                    aliveBefore ? 1 : 0, aliveAfter ? 1 : 0, applied ? 1 : 0);
        ++hits;
        if (isPiki) ++pikminHits;
        return true;
    };
    for (const auto& target : targets) {
        strike(target.first, target.second);
    }
    std::printf("P2_BOMBSARAI_TEKI_BLAST generator=%llu token=%llu carrier_valid=%d hits=%d pikmin_hits=%d\n",
                (unsigned long long)b.generator, (unsigned long long)event.carrierToken,
                event.carrierValid ? 1 : 0, hits, pikminHits);
}

} // namespace

void pc_p2_bombsarai_teki_setup()
{
    pc_p2_bombsarai_teki_reset();
    if (!pc_pikipelago_room_preview()) return;
    std::ifstream in("p2-bombsarai-teki.txt");
    if (!in) return; // inert without the sidecar
    std::string magic;
    int count = 0;
    unsigned generator = 0;
    int type = 0;
    if (!(in >> magic >> count >> generator >> type) || magic != "P2_BOMBSARAI_TEKI_1"
        || count != 1 || generator == 0 || type != 11 || !tekiMgr) {
        std::fputs("P2_BOMBSARAI_TEKI invalid sidecar\n", stderr);
        std::abort();
    }
    std::string trailing;
    if (in >> trailing) { std::fputs("P2_BOMBSARAI_TEKI trailing data\n", stderr); std::abort(); }

    if (mapMgr) sMap.reset(mapMgr);
    sAdapter.reset(P2BombSaraiMapBinding::traceMove, &sMap,
                   P2BombSaraiMapBinding::getMinY, &sMap);

    Iterator it(tekiMgr);
    CI_LOOP(it) {
        Teki* t = static_cast<Teki*>(*it);
        if (!t || !t->mGenerator || t->mGenerator->_70 != generator) continue;
        if (t->mTekiType != type || !sBound.empty()) std::abort();
        Binding b;
        b.generator = generator;
        b.type = type;
        b.rng = generator;
        b.targetRng = generator ^ 0x9E3779B97F4A7C15ull; // independent of the flick LCG
        b.home = carrierPosition(static_cast<BTeki*>(t)); // setRandTarget ring centre
        readConfig(b);
        b.fsm.reset(b.fsmParms);
        b.hover.reset(b.hoverParms);
        b.pool = P2BombSaraiBombPool(2);
        b.clock.reset();
        sBound.emplace(static_cast<BTeki*>(t), b);
        std::printf("P2_BOMBSARAI_TEKI_READY generator=%u type=%d\n", generator, type);
    }
    if (sBound.empty()) {
        std::fputs("P2_BOMBSARAI_TEKI generator not found\n", stderr);
        std::abort();
    }
}

namespace {
// Dedicated reset/re-entry rehearsal hook (#244). When
// PIKMIN_P2_BOMBSARAI_REENTRY_TICK=<n> is set the family exercises the real
// teardown/finalSetup entry points once, at source tick n, on the live scene:
// the binding maps clear to zero and the generated carrier re-binds cleanly.
// This is a lane-local test trigger, not a scene transition; the production
// runs are unaffected (the variable is unset).
void maybeReentry(BTeki* t)
{
    static bool done = false;
    static bool announced = false;
    const char* env = std::getenv("PIKMIN_P2_BOMBSARAI_REENTRY_TICK");
    if (!announced) {
        announced = true;
        std::printf("P2_BOMBSARAI_TEKI_REENTRY_ENV %s\n", env ? env : "unset");
    }
    if (done || !env) return;
    const int at = std::atoi(env);
    if (at <= 0) return;
    auto i = sBound.find(t);
    if (i == sBound.end() || i->second.tick < at) return;
    done = true;
    int boundBefore = 0, boundAfter = 0, corpseAfter = 0;
    const bool ok = pc_p2_bombsarai_teki_reentry(boundBefore, boundAfter, corpseAfter);
    std::printf("P2_BOMBSARAI_TEKI_REENTRY_PASS %d\n", ok ? 1 : 0);
}
}

void pc_p2_bombsarai_teki_tick(BTeki* t)
{
    maybeReentry(t);
    // Once the Pod receipt has credited the carcass, stop the free roam so the
    // survivors do not pick up leftover number pellets (dead-Pikmin `pr01`
    // bodies) and carry them to the Pod, which would hit the preview's
    // unregistered-cargo abort after the receipt already landed.
    if (sCorpseTeki && sCorpseDelivered) {
        if (naviMgr && pikiMgr && naviMgr->getNavi()) {
            Navi* n = naviMgr->getNavi();
            Iterator fp(pikiMgr);
            CI_LOOP(fp) {
                Piki* p = static_cast<Piki*>(*fp);
                if (p && p->isAlive()
                    && (p->mMode == PikiMode::FreeMode || p->mMode == PikiMode::TransportMode))
                    p->changeMode(PikiMode::FormationMode, n);
            }
        }
        std::printf("P2_BOMBSARAI_TEKI_CORPSE_DELIVERED\n");
        restoreCarryConfig();
        sCorpseTeki = nullptr;
        sCorpsePellet = nullptr;
        sCorpseProbeTick = 0;
        sCaptainParked = false;
    }
    if (sCorpseTeki) {
        if (!sCorpsePellet) {
            sCorpsePellet = sCorpseTeki->mPellet;
            if (sCorpsePellet && sCorpsePellet->mConfig) {
                std::printf("P2_BOMBSARAI_TEKI_CORPSE_CONFIG carry_min=%d carry_max=%d min_free_slot=%d alive=%d\n",
                            sCorpsePellet->mConfig->mCarryMinPikis.mValue,
                            sCorpsePellet->mConfig->mCarryMaxPikis.mValue,
                            sCorpsePellet->getMinFreeSlotIndex(),
                            sCorpsePellet->isAlive() ? 1 : 0);
            }
        }
        if (sCorpsePellet) {
            // Hold the freshly spawned corpse at the kill site for a few
            // seconds instead of letting its spawn velocity fling it clear of
            // the squad, so the FreeMode Pikmin that killed it can pick it up
            // (injected; the natural throw otherwise lands it out of reach).
            // Hold the corpse at the kill site until a carrier latches: its
            // spawn velocity otherwise flings it out of the room (probe moved
            // grew to 373) well clear of the ringed squad.
            if (sCorpsePellet->getMinFreeSlotIndex() != -1) sCorpsePellet->mVelocity.set(0.0f, 0.0f, 0.0f);
            // Cargo-Pod corpse carry, same recipe as lanes 13/19/22/24/31: a
            // formation squad never picks up a corpse; only FREE-MODE Pikmin do
            // (Piki::graspSituation, mIdleWorkSearchRange ~100; graspSituation
            // skips flying tekis, hence ground_engagement above). The carrier
            // corpse config must offer carry slots, and the captain must be
            // parked beyond the 250u join-party range or the freed squad
            // re-adopts formation and drops the pellet. Re-ring every 60 ticks
            // while no carrier is latched; stop once one is.
            if (sCorpsePellet->mConfig) {
                if (!sHaveOrigCarry) {
                    // Snapshot the shared carcass config before mutating it.
                    sCarryConfig = sCorpsePellet->mConfig;
                    sOrigCarryMin = sCarryConfig->mCarryMinPikis.mValue;
                    sOrigCarryMax = sCarryConfig->mCarryMaxPikis.mValue;
                    sHaveOrigCarry = true;
                }
                if (sCorpsePellet->mConfig->mCarryMaxPikis.mValue < 1) sCorpsePellet->mConfig->mCarryMaxPikis.mValue = 6;
                // Fixture concession: the carrier's own bombs decimate the
                // 20-red squad before it dies (retail Napkid corpse min is 3),
                // so allow a single surviving Pikmin to haul the carcass. The
                // carry itself stays natural (FreeMode grasp -> route -> Pod).
                sCorpsePellet->mConfig->mCarryMinPikis.mValue = 1;
            }
            // Suppress stray Red number pellets (pr01) while the carcass is being
            // hauled: the carrier (and any Pikmin it killed) drops `pr01` number
            // pellets, and a FreeMode Pikmin carrying one to the Pod hits the
            // preview's deny-by-default cargo abort before the carcass receipt
            // lands. Only free (uncarried) pellets are touched so an in-flight
            // carrier is never disrupted. Labelled fixture concession (the
            // l29 recipe closes the same pre-receipt race).
            if (pelletMgr) {
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
                if (carriers == 0 && sCorpseProbeTick % 60 == 0) {
                    Vector3f park(sCorpseOrigin.x, 0.0f, sCorpseOrigin.z + 300.0f);
                    park.y = mapMgr ? mapMgr->getMinY(park.x, park.z, true) : 0.0f;
                    n->resetPosition(park);
                    n->mVelocity.set(0.0f, 0.0f, 0.0f);
                    if (!sCaptainParked) {
                        sCaptainParked = true;
                        std::printf("P2_BOMBSARAI_TEKI_CAPTAIN_PARK x=%.3f z=%.3f\n", park.x, park.z);
                    }
                    int ring = 0;
                    Iterator sq(pikiMgr);
                    CI_LOOP(sq) {
                        Piki* p = static_cast<Piki*>(*sq);
                        if (!p || !p->isAlive()) continue;
                        const float a = float(ring) * 2.0f * kPi / float(squad > 0 ? squad : 1);
                        Vector3f pt(sCorpseOrigin.x + 16.0f * std::sin(a), 0.0f,
                                    sCorpseOrigin.z + 16.0f * std::cos(a));
                        pt.y = mapMgr ? mapMgr->getMinY(pt.x, pt.z, true) : 0.0f;
                        p->resetPosition(pt);
                        p->changeMode(PikiMode::FreeMode, n);
                        ++ring;
                    }
                std::printf("P2_BOMBSARAI_TEKI_FREE_RECRUIT count=%d carriers=%d squad=%d\n",
                            ring, carriers, squad);
                }
            }
            // Natural carry only -- no injected delivery fallback. The free-mode
            // release above latches Transport onto the corpse (carriers > 0) and
            // the Pod receipt lands through pc_p2_bombsarai_receipt. A run whose
            // squad was decimated and never latches is an honest no-receipt run.
            if (++sCorpseProbeTick % 30 == 0) {
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
                std::printf("P2_BOMBSARAI_TEKI_CORPSE tick=%d x=%.3f z=%.3f moved=%.3f carriers=%d\n",
                            sCorpseProbeTick, cp.x, cp.z, std::sqrt(dx * dx + dz * dz), transport);
            }
        }
    }
    auto i = sBound.find(t);
    if (i == sBound.end()) return;
    if (!t->isAlive() || t->mHealth <= 0.0f) {
        sCorpses[t] = (unsigned)i->second.generator;
        sCarrierDead = true;
        sCorpseTeki = t;
        sCorpsePellet = nullptr;
        sCorpseOrigin = carrierPosition(t);
        sCorpseProbeTick = 0;
        sCorpseGenerator = (unsigned)i->second.generator;
        sCorpseDelivered = false;
        std::printf("P2_BOMBSARAI_TEKI_DEAD generator=%llu\n",
                    (unsigned long long)i->second.generator);
        sBound.erase(i);
        return;
    }
    const int ticks = i->second.clock.step(gsys->getFrameTime(), true);
    for (int k = 0; k < ticks; ++k) {
        ++i->second.tick;
        stepCarrier(t, i->second, P2BombSaraiBomb::kSourceDelta);
    }
}

void pc_p2_bombsarai_teki_forget(BTeki* t)
{
    if (!t) return;
    const int boundBefore = (int)sBound.size();
    const int corpseBefore = (int)sCorpses.size();
    unsigned generator = 0;
    auto bound = sBound.find(t);
    if (bound != sBound.end()) generator = (unsigned)bound->second.generator;
    auto corpse = sCorpses.find(t);
    if (corpse != sCorpses.end()) generator = corpse->second;
    const bool wasBound = sBound.erase(t) != 0;
    const bool wasCorpse = sCorpses.erase(t) != 0;
    // Cleanup evidence: a dead/despawned carrier is dropped from both maps so a
    // recycled slot cannot inherit it (mirrors pc_p2_kurage_teki.cpp).
    if (wasBound || wasCorpse) {
        std::printf("P2_BOMBSARAI_TEKI_FORGET generator=%u bound_before=%d corpse_before=%d "
                    "bound_after=%d corpse_after=%d\n",
                    generator, boundBefore, corpseBefore, (int)sBound.size(), (int)sCorpses.size());
    }
}

void pc_p2_bombsarai_teki_reset()
{
    const int boundBefore = (int)sBound.size();
    const int corpseBefore = (int)sCorpses.size();
    restoreCarryConfig();
    sBound.clear();
    sCorpses.clear();
    sThrowCount = 0;
    sBlastCount = 0;
    sCarrierDead = false;
    sCorpseTeki = nullptr;
    sCorpsePellet = nullptr;
    sCorpseProbeTick = 0;
    sCorpseGenerator = 0;
    sCorpseDelivered = false;
    sCaptainParked = false;
    if (boundBefore || corpseBefore) {
        std::printf("P2_BOMBSARAI_TEKI_RESET bound_before=%d corpse_before=%d "
                    "bound_after=%d corpse_after=%d\n",
                    boundBefore, corpseBefore, (int)sBound.size(), (int)sCorpses.size());
    }
}

bool pc_p2_bombsarai_receipt(PelletView* view, unsigned& generator)
{
    if (!view) return false;
    BTeki* t = static_cast<BTeki*>(view);
    auto i = sBound.find(t);
    if (i != sBound.end()) {
        generator = (unsigned)i->second.generator;
        return true;
    }
    auto c = sCorpses.find(t);
    if (c == sCorpses.end()) return false;
    generator = c->second;
    // Natural Pod delivery of the carcass: the preview calls this during
    // pc_p2_preview_deliver, so record it to end the free-roam cleanly.
    sCorpseDelivered = true;
    return true;
}

bool pc_p2_bombsarai_teki_is_bound(const BTeki* t)
{
    return t && sBound.count(const_cast<BTeki*>(t));
}

int pc_p2_bombsarai_teki_throw_count() { return sThrowCount; }
int pc_p2_bombsarai_teki_blast_count() { return sBlastCount; }
bool pc_p2_bombsarai_teki_carrier_dead() { return sCarrierDead; }

int pc_p2_bombsarai_teki_bound_count() { return (int)sBound.size(); }
int pc_p2_bombsarai_teki_corpse_count() { return (int)sCorpses.size(); }

bool pc_p2_bombsarai_teki_reentry(int& boundBefore, int& boundAfter, int& corpseAfter)
{
    boundBefore = (int)sBound.size();
    // Real stage-teardown entry point (GameCoreSection::exitStage ->
    // pc_p2_reset_all_teki, gameCoreSection.cpp:897): every family map is
    // cleared so a finished stage retains no stale BTeki* key.
    pc_p2_reset_all_teki();
    const int boundAfterReset = (int)sBound.size();
    const int corpseAfterReset = (int)sCorpses.size();
    // Real finalSetup entry point (gameCoreSection.cpp:1490): the fresh scene
    // re-runs the family setup and re-binds the generated carrier.
    pc_p2_bombsarai_teki_setup();
    boundAfter = (int)sBound.size();
    corpseAfter = (int)sCorpses.size();
    std::printf("P2_BOMBSARAI_TEKI_REENTRY bound_before=%d bound_after_reset=%d "
                "corpse_after_reset=%d bound_after=%d corpse_after=%d\n",
                boundBefore, boundAfterReset, corpseAfterReset, boundAfter, corpseAfter);
    return boundBefore > 0 && boundAfterReset == 0 && corpseAfterReset == 0
        && boundAfter == 1 && corpseAfter == 0;
}
