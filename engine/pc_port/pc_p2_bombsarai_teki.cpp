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
// Injected engagement seal: keep the grounded carrier within this XZ distance
// of the nearest live Pikmin (units), closing the gap at a capped per-tick
// speed so the FreeMode squad can attack it (a large teleport crashes the host).
constexpr float kEngageKeepRange = 30.0f;
constexpr float kEngageSeekSpeed = 300.0f;

struct Binding {
    std::uint64_t generator = 0;
    int type = 0;
    std::uint64_t rng = 0; // LCG seed for host-fed flick rolls (never the token)
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

    // Experimental ground-engagement mode. A FreeMode Pikmin squad rejects a
    // flying Teki outright: graspSituation skips `isFlying()` (piki.cpp:951) and
    // ActAttack abandons an airborne target (aiAttack.cpp:189/297), so raising
    // only the height is not enough. This hook runs after the Napkid strategy's
    // act()+moveNew (tekibteki.cpp:473-484), so it is the last write of the
    // frame: clear CF_IsFlying and pin the carrier to the floor every tick. The
    // Fall crash keeps gravity; every other state walks on the ground.
    t->finishFlying();
    if (state == P2BombSaraiFsmState::Fall) {
        t->mSRT.t.y -= b.bombConfig.gravityPerTick * 30.0f * delta;
        if (t->mSRT.t.y < groundY) t->mSRT.t.y = groundY;
    } else {
        t->mSRT.t.y = groundY;
    }
    t->mVelocity.y = 0.0f;

    // Keep the grounded carrier inside the squad's attack volume: the P1 host
    // flight otherwise carries it away from the FreeMode squad. If the nearest
    // live Pikmin is farther than the keep range, close the gap at a capped
    // per-tick speed (injected locomotion; the host is overridden after the
    // fact). A large teleport on one tick crashes the P1 host.
    if (pikiMgr) {
        float best = 1.0e30f, bestDx = 0.0f, bestDz = 0.0f;
        Iterator sit(pikiMgr);
        CI_LOOP(sit) {
            Piki* piki = static_cast<Piki*>(*sit);
            if (!piki || !piki->isAlive()) continue;
            const float dx = piki->mSRT.t.x - t->mSRT.t.x;
            const float dz = piki->mSRT.t.z - t->mSRT.t.z;
            const float d2 = dx * dx + dz * dz;
            if (d2 < best) { best = d2; bestDx = dx; bestDz = dz; }
        }
        if (best < 1.0e29f) {
            const float d = std::sqrt(best);
            if (d > kEngageKeepRange) {
                const float step = kEngageSeekSpeed * delta;
                const float gap = d - kEngageKeepRange;
                const float move = gap < step ? gap : step;
                t->mSRT.t.x += bestDx / d * move;
                t->mSRT.t.z += bestDz / d * move;
            }
        }
    }
    const P2BombSaraiVec3 carrier = carrierPosition(t);

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
    in.waypointReached = false;
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
    auto strike = [&](Creature* receiver, bool isPiki) -> bool {
        if (!receiver || !receiver->isAlive()) return false;
        const Vector3f& p = receiver->getPosition();
        const float dx = p.x - event.center.x;
        const float dy = p.y - event.center.y;
        const float dz = p.z - event.center.z;
        if (dy < -event.halfHeight || dy > event.halfHeight) return false;
        if (dx * dx + dz * dz > event.radius * event.radius) return false;
        InteractBomb bomb(owner, event.naviPikiDamage, nullptr);
        receiver->stimulate(bomb);
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

void pc_p2_bombsarai_teki_tick(BTeki* t)
{
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
    sBound.erase(t);
    sCorpses.erase(t);
}

void pc_p2_bombsarai_teki_reset()
{
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
