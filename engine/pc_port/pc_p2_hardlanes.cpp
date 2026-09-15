// Hard-lane shared registration seam (#244, #245, #246).
//
// Batch 2: wire the isolated hard-lane policy/arena modules into the shared game
// target with live host adapters.
//
// * BombSarai (#244): the carrier arena is bound to the live P1 static map
//   through the lane's P2BombSaraiMapBinding terrain adapter and advanced on the
//   authoritative frame delta via the lane's source clock. Runs only inside the
//   private room preview and only when the opt-in `p2-bombsarai-arena.txt`
//   profile is present.
// * Fuefuki (#245): the lane-owned P2FuefukiBinding is bound to a live host
//   adapter over the real squad, with the beetle vehicle anchored on a staged
//   TEKI_Napkid proxy actor. Whistle-theft/reclaim policy runs against real
//   Pikmin. The ActTeki follow-locomotion policy (pc_p2_fuefuki_follow.h)
//   drives each held Pikmin: the faithful Piki::setSpeed drive plus a labeled
//   volatile-velocity approximation, because P1 has no follow-teki action and
//   ActFree overwrites mTargetVelocity before moveVelocity each frame. Runs
//   only inside the private room preview when a Napkid vehicle exists, so
//   ordinary P1 play is unaffected.
//
// No shared semantics are changed: this module owns no saves, rewards, generic
// damage or actor lifetime. It is a debug/arena registration for runtime
// evidence. BigTreasure host glue lands in a following slice.
#include "pc_p2_hardlanes.h"
#include "pc_p2_bombsarai_arena.h"
#include "pc_p2_bombsarai_bomb.h"
#include "pc_p2_bombsarai_clock.h"
#include "pc_p2_bombsarai_map_trace.h"
#include "pc_p2_bombsarai_terrain.h"
#include "pc_p2_fuefuki_binding.h"
#include "pc_p2_fuefuki_motion.h"
#include "pc_p2_fuefuki_visual.h"
#include "pc_p2_retail_player.h"
#include "pc_p2_bigtreasure_host.h"
#include "pc_p2_bigtreasure_ordinary.h"
#include "pc_p2_bigtreasure_animclock.h"
#include "pc_p2_bigtreasure_elements.h"
#include "pc_p2_bigtreasure_receiver_host.h"
#include "pc_p2_bigtreasure_map_trace.h"
#include "pc_p2_bigtreasure_visual.h"
#include "pc_p2_waterwraith_register.h"
#include "Matrix4f.h"
#include "pc_bbft.h"
#include "gameflow.h"
#include "MoviePlayer.h"
#include "Graphics.h"
#include "MapMgr.h"
#include "system.h"
#include "Generator.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "Creature.h"
#include "teki.h"
#include <cstdint>
#include <cstdio>
#include <cmath>
#include <map>
#include <set>
#include <string>

namespace {
// ---------------------------------------------------------------------------
// BombSarai (#244)
P2BombSaraiMapBinding* sBinding = nullptr;
P2BombSaraiTerrainAdapter* sAdapter = nullptr;
P2BombSaraiSourceClock* sClock = nullptr;
bool sBombSaraiReady = false;

bool sCarrierAlive(void*, std::uint64_t) { return true; }

// ---------------------------------------------------------------------------
// Fuefuki (#245)
constexpr float kFuefukiSourceDelta = 1.0f / 30.0f;
P2FuefukiBinding* sFuefuki = nullptr;
Teki* sFuefukiVehicle = nullptr;
std::map<Piki*, std::uint32_t> sFuefukiId;
std::map<std::uint32_t, Piki*> sFuefukiPiki;
std::map<std::uint32_t, bool> sFuefukiHeld;
std::uint32_t sFuefukiNextId = 1;
double sFuefukiDebt = 0.0;
bool sFuefukiPressed = false;      // #245 natural combat: press/hipdrop latch
unsigned long sFuefukiPressCount = 0;
bool sFuefukiVisualReady = false;
double sFuefukiVisualDebt = 0.0;
int sFuefukiLastState = -1;
P2FuefukiMotionBank sFuefukiMotions;
p2retail::Player sFuefukiMotionPlayer;
bool sFuefukiMotionReady = false;
int sFuefukiMotionState = -1;

std::uint32_t fuefukiId(Piki* piki)
{
    auto it = sFuefukiId.find(piki);
    if (it != sFuefukiId.end()) return it->second;
    const std::uint32_t id = sFuefukiNextId++;
    sFuefukiId[piki] = id;
    sFuefukiPiki[id] = piki;
    sFuefukiHeld[id] = false;
    return id;
}

float fuefukiXzSq(const Vector3f& a, const Vector3f& b)
{
    const float dx = a.x - b.x, dz = a.z - b.z;
    return dx * dx + dz * dz;
}

void fuefukiProbe(void*, P2FuefukiProbeResult& out)
{
    out.arriveTarget = false;
    out.water = false;
    out.intruder = false;
    out.x = out.z = 0.0f;
    if (!sFuefukiVehicle) { out.valid = false; return; }
    const Vector3f anchor = sFuefukiVehicle->getPosition();
    out.x = anchor.x;
    out.z = anchor.z;
    const Vector3f velocity = sFuefukiVehicle->getVelocity();
    out.vx = velocity.x;
    out.vz = velocity.z;
    Navi* navi = naviMgr ? naviMgr->getNavi() : nullptr;
    if (navi && fuefukiXzSq(navi->mSRT.t, anchor) < 3600.0f) out.intruder = true;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* piki = static_cast<Piki*>(*it);
        if (!piki) continue;
        const std::uint32_t id = fuefukiId(piki);
        if (piki->isAlive() && !sFuefukiHeld[id]
            && fuefukiXzSq(piki->mSRT.t, anchor) < 3600.0f) out.intruder = true;
    }
    out.valid = true;
}

int fuefukiEnumerate(void*, float x, float z, float radius, P2FuefukiSquadEntry* out, int capacity)
{
    int count = 0;
    const float radiusSq = radius * radius;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* piki = static_cast<Piki*>(*it);
        if (!piki || count >= capacity) continue;
        const float dx = piki->mSRT.t.x - x, dz = piki->mSRT.t.z - z;
        if (dx * dx + dz * dz > radiusSq) continue;
        P2FuefukiSquadEntry& entry = out[count++];
        entry.id = fuefukiId(piki);
        entry.living = piki->isAlive();
        entry.callable = piki->getState() == PIKISTATE_Normal;
        entry.stuckToMouth = false;  // no P1 mouth-stuck Pikmin staged
        entry.alreadyTeki = false;   // no P1 follow-teki action exists
    }
    return count;
}

bool fuefukiFollowStart(void*, std::uint32_t id)
{
    auto it = sFuefukiPiki.find(id);
    if (it == sFuefukiPiki.end() || !it->second->isAlive()) return false;
    sFuefukiHeld[id] = true;
    return true;
}

void fuefukiFollowEnd(void*, std::uint32_t id, int) { sFuefukiHeld[id] = false; }

int fuefukiPingCollect(void*, std::uint32_t* out, int capacity)
{
    int count = 0;
    for (const auto& held : sFuefukiHeld) {
        if (!held.second || count >= capacity) continue;
        auto it = sFuefukiPiki.find(held.first);
        if (it != sFuefukiPiki.end() && it->second->isAlive()) out[count++] = held.first;
    }
    return count;
}

// The lane's single captain-ownership write for an accepted Panic reclaim:
// clear the follow action, hand the Pikmin to the whistling captain and set
// LookAt, matching the source InteractFue receiver.
void fuefukiOwnershipWrite(void*, std::uint32_t id, std::uint32_t)
{
    auto it = sFuefukiPiki.find(id);
    Navi* navi = naviMgr ? naviMgr->getNavi() : nullptr;
    if (it == sFuefukiPiki.end() || !navi || !it->second->isAlive()) return;
    Piki* piki = it->second;
    piki->mNavi = navi;
    piki->mFSM->transit(piki, PIKISTATE_LookAt);
}

// No P1 Beetle actor exists yet, so kill delivery is recorded only.
void fuefukiKill(void*, bool) {}

// (g) ActTeki follow locomotion host side. The sample returns the real P1
// Pikmin position; the drive applies the policy command to the real actor.
bool fuefukiFollowerSample(void*, std::uint32_t id, float& x, float& z)
{
    auto it = sFuefukiPiki.find(id);
    if (it == sFuefukiPiki.end() || !it->second->isAlive()) return false;
    x = it->second->mSRT.t.x;
    z = it->second->mSRT.t.z;
    return true;
}

void fuefukiFollowDrive(void*, std::uint32_t id, const P2FuefukiFollowMove& move)
{
    auto it = sFuefukiPiki.find(id);
    if (it == sFuefukiPiki.end() || !it->second->isAlive()) return;
    Piki* piki = it->second;
    if (move.stop) {
        piki->mTargetVelocity.set(0.0f, 0.0f, 0.0f);
        piki->mVolatileVelocity.set(0.0f, 0.0f, 0.0f);
        return;
    }
    // Faithful source drive (ActTeki::test_0 -> Piki::setSpeed).
    Vector3f dir(move.dirX, 0.0f, move.dirZ);
    piki->setSpeed(move.speed, dir);
    // Labeled approximation: P1 has no follow-teki action, so the Pikmin's
    // ActFree overwrites mTargetVelocity before Creature::moveVelocity each
    // frame. Seed the volatile impulse channel (already used by flicks) so
    // the follow motion is actually realized until a real follow action lands
    // (provider lane 12). Remove once that action exists.
    piki->mVolatileVelocity.set(move.dirX * piki->mMoveSpeed, 0.0f, move.dirZ * piki->mMoveSpeed);
}

P2FuefukiFollowParms fuefukiFollowParms()
{
    P2FuefukiFollowParms p;
    p.followDistance = 100.0f; // source FOLLOW_DISTANCE
    return p;
}

P2FuefukiFsmParms fuefukiParms()
{
    P2FuefukiFsmParms p;
    p.maxGroundTime = 20.0f;         // fp01 retail
    p.minGroundTime = 10.0f;         // fp02 retail
    p.maxWhistleTimeNoSquad = 3.0f;  // fp12 retail re-cast interval
    p.struggleTime = 2.5f;           // fp21 retail
    p.attackRadius = 130.0f;         // retail whistle ring radius
    return p;
}

// (#245) Count live Pikmin currently stuck to the vehicle (source stuck-attacker
// count: Struggle exits to Jump when no stuck Pikmin remain after 3.0 s, and the
// whistle cadence uses "stuck attackers present" to pick the fp12 interval).
// Walks the engine sticker list and counts only living Piki.
int fuefukiStuckPikmin(Teki* vehicle)
{
    int count = 0;
    if (!vehicle) return 0;
    for (Creature* stuck = vehicle->mStickListHead; stuck; stuck = stuck->mNextSticker) {
        if (stuck->isPiki() && stuck->isAlive()) ++count;
    }
    return count;
}

// ---------------------------------------------------------------------------
// BigTreasure (#246)
constexpr float kBigTreasureSourceDelta = 1.0f / 30.0f;
constexpr float kBigTreasureAttackDamage = kBigTreasureDefaultAttackDamage;
P2BigTreasureHostSeam sBigTreasure;
P2BigTreasureOrdinary sBigTreasureOrdinary;
P2BigTreasureAnimClock sBigTreasureClock;
P2BigTreasureElementRuntime sBigTreasureElements;
P2BigTreasureMapTrace sBigTreasureTrace;
// Per-attack handled set of live targets (Navi/Piki pointers). Mirrors lane 22's
// per-Piki handled set (pc_p2_hiba.cpp:47,142): a target is stimulated at most
// once per attack so a creature standing inside the running element is not
// re-stimulated (and SEF_PIKI_FIRED re-emitted) every frame. Cleared on attack
// start and on full reset.
std::set<const void*> sBigTreasureHandled;
bool sBigTreasureAttackLogged = false;
bool sBigTreasureReady = false;
bool sBigTreasureVisualReady = false;
bool sBigTreasureVisualDriven = true;
float sBigTreasureGround = 0.0f;
double sBigTreasureDebt = 0.0;
float sWaterwraithGround = 0.0f;
P2BigTreasurePhase sBigTreasurePhase = P2BT_Dead;

const char* bigTreasureWeaponName(int weapon)
{
    switch (weapon) {
    case P2BTWEAPON_Elec: return "elec";
    case P2BTWEAPON_Fire: return "fire";
    case P2BTWEAPON_Gas: return "gas";
    case P2BTWEAPON_Water: return "water";
    default: return "?";
    }
}

// Source isAttackLimitTime box test: a live Navi/Pikmin inside the 225-unit XZ
// box around the fixed placement. The ordinary FSM drive consumes the result
// as `targetInBox`; the policy's pacer owns the timer accrual and threshold.
bool bigTreasureTargetInBox()
{
    if (!sBigTreasure.active) return false;
    const float bx = sBigTreasure.placement.owner.x;
    const float bz = sBigTreasure.placement.owner.z;
    const float box = P2BigTreasureAttackPacer::kBoxHalfExtent;
    auto inside = [&](float x, float z) {
        return std::fabs(x - bx) <= box && std::fabs(z - bz) <= box;
    };
    Navi* navi = naviMgr ? naviMgr->getNavi() : nullptr;
    if (navi && inside(navi->mSRT.t.x, navi->mSRT.t.z)) return true;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* piki = static_cast<Piki*>(*it);
        if (piki && piki->isAlive() && inside(piki->mSRT.t.x, piki->mSRT.t.z)) return true;
    }
    return false;
}
}

void pc_p2_hardlanes_set_bigtreasure_visual_driven(bool driven)
{
    sBigTreasureVisualDriven = driven;
}

void pc_p2_hardlanes_reset()
{
    pc_p2_bombsarai_arena_reset();
    if (sClock) sClock->reset();
    sBombSaraiReady = false;
    sFuefukiVehicle = nullptr;
    sFuefukiDebt = 0.0;
    sFuefukiPressed = false;
    sFuefukiPressCount = 0;
    sFuefukiId.clear();
    sFuefukiPiki.clear();
    sFuefukiHeld.clear();
    sFuefukiNextId = 1;
    if (sFuefuki) sFuefuki->follow().reset();
    pc_p2_fuefuki_visual_reset();
    sFuefukiVisualReady = false;
    sFuefukiVisualDebt = 0.0;
    sFuefukiLastState = -1;
    sFuefukiMotions = P2FuefukiMotionBank();
    sFuefukiMotionReady = false;
    sFuefukiMotionState = -1;
    p2_bigtreasure_host_reset(sBigTreasure);
    sBigTreasureOrdinary.reset(P2BigTreasureFsmParms());
    sBigTreasureClock.reset();
    sBigTreasureElements.defeat();
    sBigTreasureHandled.clear();
    sBigTreasureAttackLogged = false;
    pc_p2_bigtreasure_visual_reset();
    sBigTreasureReady = false;
    sBigTreasureVisualReady = false;
    sBigTreasureVisualDriven = true;
    sBigTreasureGround = 0.0f;
    sBigTreasureDebt = 0.0;
    // Waterwraith (#443 / #175) - lane 31 additive hook.
    pc_p2_waterwraith_register_reset();
    sWaterwraithGround = 0.0f;
    sBigTreasurePhase = P2BT_Dead;
}

bool pc_p2_hardlanes_bigtreasure_hit(int weapon, float damage, bool bittered)
{
    P2BigTreasureOrdinaryHit hit;
    hit.weapon = weapon;
    hit.damage = damage;
    hit.bittered = bittered;
    return sBigTreasureOrdinary.postHit(hit);
}

bool pc_p2_hardlanes_bigtreasure_ready()
{
    return sBigTreasureReady && sBigTreasure.active;
}

int pc_p2_hardlanes_bigtreasure_weapon_count()
{
    return sBigTreasureReady ? sBigTreasure.ownership.weaponCount() : 0;
}

int pc_p2_hardlanes_bigtreasure_recv_probe(int weapon, Piki* piki)
{
    if (!sBigTreasureReady || !sBigTreasure.active || !piki || !piki->isAlive()) {
        return 0;
    }
    // Reuse the ordinary loop's per-attack handled set: a target is stimulated
    // at most once per attack, so a second probe of the same Piki returns 0.
    // The probe removes its transient entry when it observes that dedup so it
    // never leaves a target permanently handled. This demonstrates set-dedupe
    // only; per-attack re-arm is the ordinary loop's attack-start clear
    // (pc_p2_hardlanes_update, startAttack), which a probe cannot exercise
    // without a real attack.
    const void* key = static_cast<const void*>(piki);
    if (!sBigTreasureHandled.insert(key).second) {
        sBigTreasureHandled.erase(key);
        return 0;
    }
    const P2BigTreasureVec3 origin{ sBigTreasure.placement.owner.x,
                                    sBigTreasureGround,
                                    sBigTreasure.placement.owner.z };
    const bool accepted = pc_p2_bigtreasure_stimulate_piki(weapon, origin,
                                                           kBigTreasureAttackDamage, piki);
    return accepted ? 1 : -1;
}

void pc_p2_hardlanes_setup()
{
    pc_p2_hardlanes_reset();
    if (!pc_pikipelago_room_preview() || !mapMgr) return;

    // BombSarai (#244): opt-in arena profile.
    if (!sBinding) sBinding = new P2BombSaraiMapBinding();
    if (!sAdapter) sAdapter = new P2BombSaraiTerrainAdapter();
    if (!sClock) sClock = new P2BombSaraiSourceClock();
    if (pc_p2_bombsarai_arena_setup("p2-bombsarai-arena.txt")) {
        sBinding->reset(mapMgr);
        sAdapter->reset(P2BombSaraiMapBinding::traceMove, sBinding,
                        P2BombSaraiMapBinding::getMinY, sBinding);
        sBombSaraiReady = true;
        std::printf("P2_HARDLANES_READY family=BombSarai arena=1\n");
    }

    // Fuefuki (#245): bind to a staged placement vehicle. An optional
    // `p2-fuefuki-teki.txt` scopes the binding to one generator (private
    // adapter pattern, Kurage/Onikurage); absent, the first Napkid is used.
    unsigned wantedGenerator = 0;
    int wantedType = TEKI_Napkid;
    if (FILE* config = std::fopen("p2-fuefuki-teki.txt", "r")) {
        char version[32];
        unsigned generator = 0;
        int type = 0;
        const bool valid = std::fscanf(config, "%31s %u %d", version, &generator, &type) == 3;
        std::fclose(config);
        if (!valid || std::string(version) != "P2_FUEFUKI_TEKI_1") {
            std::printf("P2_HARDLANES_ERROR family=Fuefuki invalid p2-fuefuki-teki.txt\n");
            return;
        }
        wantedGenerator = generator;
        wantedType = type;
    }
    if (tekiMgr) {
        Iterator it(tekiMgr);
        CI_LOOP(it) {
            Teki* teki = static_cast<Teki*>(*it);
            if (!teki || teki->mTekiType != wantedType) continue;
            if (wantedGenerator && (!teki->mGenerator || teki->mGenerator->_70 != wantedGenerator)) continue;
            sFuefukiVehicle = teki;
            break;
        }
    }
    if (wantedGenerator && !sFuefukiVehicle) {
        std::printf("P2_HARDLANES_ERROR family=Fuefuki generator=%u type=%d not found\n",
                    wantedGenerator, wantedType);
    }
    if (sFuefukiVehicle) {
        if (!sFuefuki) sFuefuki = new P2FuefukiBinding();
        P2FuefukiHost host;
        host.context = nullptr;
        host.probe = fuefukiProbe;
        host.enumerate = fuefukiEnumerate;
        host.followStart = fuefukiFollowStart;
        host.followEnd = fuefukiFollowEnd;
        host.pingCollect = fuefukiPingCollect;
        host.ownershipWrite = fuefukiOwnershipWrite;
        host.kill = fuefukiKill;
        host.followerSample = fuefukiFollowerSample;
        host.followDrive = fuefukiFollowDrive;
        host.randFloat = nullptr; // deterministic lane LCG fallback
        if (sFuefuki->bind(host, fuefukiParms(), nullptr, fuefukiFollowParms())) {
            sFuefuki->spawn(1);
            const unsigned generator = sFuefukiVehicle->mGenerator ? sFuefukiVehicle->mGenerator->_70 : 0u;
            std::printf("P2_HARDLANES_READY family=Fuefuki vehicle=Napkid gen=%u type=%d follow_locomotion=actteki_volatile_approx\n",
                        generator, static_cast<int>(sFuefukiVehicle->mTekiType));
        }
    }

    // Fuefuki (#245): opt-in converted visual bank (#128 pose import).
    if (pc_p2_fuefuki_visual_setup("p2-fuefuki-visual.txt")) {
        sFuefukiVisualReady = true;
        pc_p2_fuefuki_visual_clip("wait");
        if (sFuefukiVehicle) {
            const Vector3f anchor = sFuefukiVehicle->getPosition();
            pc_p2_fuefuki_visual_set_position(anchor.x, anchor.y, anchor.z);
        } else {
            const float ground = mapMgr->getMinY(0.0f, 0.0f, false);
            pc_p2_fuefuki_visual_set_position(0.0f, ground, 0.0f);
        }
        std::printf("P2_HARDLANES_READY family=Fuefuki visual=1 clips=%d\n",
                    pc_p2_fuefuki_visual_clip_count());
    }

    // Fuefuki (#245): opt-in converted motion event table for the lane FSM.
    if (p2_fuefuki_motion_load("p2-fuefuki-motion.txt", sFuefukiMotions)) {
        sFuefukiMotionReady = true;
        std::printf("P2_HARDLANES_READY family=Fuefuki motion=1 clips=%d\n",
                    static_cast<int>(sFuefukiMotions.table.motions.size()));
    }

    // BigTreasure (#246): fixed-placement host seam + sampled visual bank.
    if (p2_bigtreasure_host_setup("p2-bigtreasure-host.txt", sBigTreasure)) {
        sBigTreasureReady = true;
        sBigTreasureOrdinary.reset(P2BigTreasureFsmParms());
        // Animation keyframe source: the lane's own motion-table player, so the
        // policy can leave Land even when the shared visual bank only stages a
        // subset. Absent table leaves the clock inactive (policy parks in Land).
        if (sBigTreasureClock.load("p2_bigtreasure_events.txt")) {
            std::printf("P2_HARDLANES_READY family=BigTreasure keyframes=1\n");
        }
        sBigTreasureTrace.reset(mapMgr);
        sBigTreasureGround = mapMgr->getMinY(0.0f, 0.0f, false);
        std::printf("P2_HARDLANES_READY family=BigTreasure host=1 captures=5\n");
    }
    if (pc_p2_bigtreasure_visual_setup("p2-bigtreasure-visual.txt")) {
        sBigTreasureVisualReady = true;
        pc_p2_bigtreasure_visual_clip("wait1");
        std::printf("P2_HARDLANES_READY family=BigTreasure visual=1 clips=%d debug=%d\n",
                    pc_p2_bigtreasure_visual_pellet_count(),
                    pc_p2_bigtreasure_visual_debug_count());
    }

    // Waterwraith (#443 / #175) - lane 31 additive hook. Opt-in: the caller is
    // already inside the experimental room preview, and setup is a no-op unless
    // `p2-waterwraith-actor.txt` is present. Fixed placement first.
    if (pc_p2_waterwraith_register_setup("p2-waterwraith-actor.txt")) {
        sWaterwraithGround = mapMgr->getMinY(0.0f, 0.0f, false);
        std::printf("P2_HARDLANES_READY family=Waterwraith register=1 placement=fixed\n");
    }
}

void pc_p2_hardlanes_update()
{
    if (!gsys) return;
    const bool active = !gameflow.mPauseAll && !gameflow.mIsUIOverlayActive
        && !(gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive);
    if (!active) return;

    if (sBombSaraiReady) {
        const int ticks = sClock->step(gsys->getFrameTime(), true);
        for (int i = 0; i < ticks; ++i)
            pc_p2_bombsarai_arena_update(P2BombSaraiBomb::kSourceDelta,
                                         P2BombSaraiTerrainAdapter::trace, sAdapter,
                                         sCarrierAlive, nullptr);
    }

    if (sFuefuki && sFuefukiVehicle) {
        const Vector3f anchor = sFuefukiVehicle->getPosition();
        pc_p2_fuefuki_visual_set_position(anchor.x, anchor.y, anchor.z);
        sFuefukiDebt += gsys->getFrameTime();
        int ticks = static_cast<int>(sFuefukiDebt / kFuefukiSourceDelta);
        if (ticks > 4) ticks = 4;
        sFuefukiDebt -= ticks * static_cast<double>(kFuefukiSourceDelta);
        for (int i = 0; i < ticks; ++i) {
            P2FuefukiBindTick tick;
            tick.delta = kFuefukiSourceDelta;
            tick.health = sFuefukiVehicle->mHealth;
            tick.turnComplete = true;
            tick.pressed = sFuefukiPressed; // #245 natural combat: consume the latch
            sFuefukiPressed = false;
            tick.stuckPikmin = fuefukiStuckPikmin(sFuefukiVehicle);
            tick.bittered = false; // no P1 bittering bridge; host admits via parm
            if (sFuefukiMotionReady) {
                // Drive the FSM from the converted clip bank: start the clip
                // for the current state and feed its KEYEVENT_2/3 and END.
                const int state = static_cast<int>(sFuefuki->getFsm().getState());
                if (state != sFuefukiMotionState) {
                    sFuefukiMotionState = state;
                    const p2retail::Motion* motion = p2_fuefuki_motion_find(
                        sFuefukiMotions, p2_fuefuki_motion_clip_for_state(state));
                    if (motion) sFuefukiMotionPlayer.start(*motion);
                }
                int key = 0;
                sFuefukiMotionPlayer.advance(1.0f, [&key](const p2retail::Event& event) {
                    if (event.type == 2) key = 2;
                    else if (event.type == 3) key = 3;
                    else if (event.type >= 1000) key = 4;
                });
                tick.animPlaying = true;
                tick.keyEvent = key;
                tick.motionFinished = sFuefukiMotionPlayer.completed();
            } else {
                tick.animPlaying = true; // no source Beetle animation bank yet (#128)
                tick.keyEvent = 0;
                tick.motionFinished = false;
            }
            P2FuefukiBindOut out = sFuefuki->tick(tick);
            if (sFuefukiMotionReady && out.fsm.requestFinishMotion) {
                // The transition waits for the finish motion's END; let the
                // active (possibly looping) clip run to completion.
                sFuefukiMotionPlayer.finishMotion(true);
            }
        }
    }

    if (sFuefukiVisualReady) {
        sFuefukiVisualDebt += gsys->getFrameTime();
        int ticks = static_cast<int>(sFuefukiVisualDebt / kFuefukiSourceDelta);
        if (ticks > 4) ticks = 4;
        sFuefukiVisualDebt -= ticks * static_cast<double>(kFuefukiSourceDelta);
        for (int i = 0; i < ticks; ++i) {
            if (sFuefuki) {
                const int state = static_cast<int>(sFuefuki->getFsm().getState());
                if (state != sFuefukiLastState) {
                    sFuefukiLastState = state;
                    const char* clip = pc_p2_fuefuki_visual_clip_for_state(state);
                    pc_p2_fuefuki_visual_clip(clip);
                    std::printf("P2_FUEFUKI_FSM state=%d clip=%s\n", state, clip);
                }
            }
            pc_p2_fuefuki_visual_update(1.0f);
        }
    }

    if (sBigTreasureReady || sBigTreasureVisualReady) {
        sBigTreasureDebt += gsys->getFrameTime();
        int ticks = static_cast<int>(sBigTreasureDebt / kBigTreasureSourceDelta);
        if (ticks > 4) ticks = 4;
        sBigTreasureDebt -= ticks * static_cast<double>(kBigTreasureSourceDelta);
        for (int i = 0; i < ticks; ++i) {
            if (sBigTreasureReady) {
                // Ordinary update: step the 12-state policy (not the injected
                // attack shortcut). The animation keyframe source runs the
                // mapped source clip through the lane's own motion player, so
                // the policy advances Land -> ItemWalk -> ... -> Attack as the
                // clips dispatch their authored events. Natural hits enter via
                // pc_p2_hardlanes_bigtreasure_hit.
                P2BigTreasureAnimPulses pulses;
                sBigTreasureClock.tick(sBigTreasureOrdinary.phase(),
                                       sBigTreasureOrdinary.chosenWeapon(), pulses);
                P2BigTreasureOrdinaryFacts facts;
                facts.delta = kBigTreasureSourceDelta;
                facts.targetInBox = bigTreasureTargetInBox();
                facts.hasTarget = facts.targetInBox;
                facts.animEnd = pulses.animEnd;
                facts.keyEvent2 = pulses.keyEvent2;
                facts.keyEvent100 = pulses.keyEvent100;
                // No IK-system bridge yet: treat the IK motion as finished so
                // the walk gates resolve, mirroring the fixture inputs.
                facts.finishIKMotion = true;
                P2BigTreasureFsmHostOutput fsmOut;
                sBigTreasureOrdinary.tick(sBigTreasure, facts, fsmOut);
                const P2BigTreasurePhase phase = sBigTreasureOrdinary.phase();
                if (phase != sBigTreasurePhase) {
                    sBigTreasurePhase = phase;
                    char clip[40] = "-";
                    p2_bigtreasure_anim_clip(phase, sBigTreasureOrdinary.chosenWeapon(),
                                             clip, sizeof(clip));
                    std::printf("P2_BIGTREASURE_FSM phase=%s weapons=%d clip=%s\n",
                                P2BigTreasureFsm::stateName(phase),
                                sBigTreasure.ownership.weaponCount(), clip);
                }
                // Element runtime: start the source controller the FSM just
                // started through the pools, and step it against the lane map
                // trace so a live attack actually emits/moves and its emitted
                // nodes apply real elemental damage to live targets below.
                if (fsmOut.fsm.startAttack) {
                    const int weapon = sBigTreasureOrdinary.chosenWeapon();
                    const P2BigTreasureVec3 origin{ sBigTreasure.placement.owner.x,
                                                    sBigTreasureGround,
                                                    sBigTreasure.placement.owner.z };
                    if (sBigTreasureElements.start(
                            weapon, origin, sBigTreasureGround,
                            sBigTreasure.ownership.weaponHealth(weapon), 0.25f, 0.25f)) {
                        sBigTreasureHandled.clear();
                        sBigTreasureAttackLogged = false;
                        std::printf("P2_BIGTREASURE_ATTACK_START weapon=%s\n",
                                    bigTreasureWeaponName(weapon));
                    }
                }
                if (fsmOut.fsm.finishAttack) {
                    sBigTreasureElements.finish();
                }
                if (sBigTreasureElements.active()) {
                    P2BigTreasureElementHost elementHost;
                    elementHost.context = &sBigTreasureTrace;
                    elementHost.trace = P2BigTreasureMapTrace::trace;
                    elementHost.ground = P2BigTreasureMapTrace::ground;
                    P2BigTreasureElementStats elementStats;
                    sBigTreasureElements.tick(kBigTreasureSourceDelta, elementHost, elementStats);
                    if (!sBigTreasureAttackLogged && elementStats.nodes > 0) {
                        sBigTreasureAttackLogged = true;
                        std::printf("P2_BIGTREASURE_ATTACK_EMIT weapon=%s nodes=%d\n",
                                    bigTreasureWeaponName(sBigTreasureElements.activeWeapon()),
                                    elementStats.nodes);
                    }
                    // Real elemental receiver (#246): apply each emitted node's
                    // source stimulus to every live Navi/Pikmin intersecting it,
                    // through the shared P2 receivers (InteractFire/InteractGas/
                    // InteractBubble/InteractDenki). This closes the
                    // "detection-only" gap: a hit now mutates the target. The
                    // per-attack handled set targets once per attack, so a
                    // creature standing in the running element is not
                    // re-stimulated (and SEF_PIKI_FIRED re-emitted) every frame.
                    if (elementStats.nodes > 0) {
                        const int recvWeapon = sBigTreasureElements.activeWeapon();
                        const P2BigTreasureVec3 origin{ sBigTreasure.placement.owner.x,
                                                        sBigTreasureGround,
                                                        sBigTreasure.placement.owner.z };
                        Navi* liveNavi = naviMgr ? naviMgr->getNavi() : nullptr;
                        if (liveNavi) {
                            const P2BigTreasureVec3 target{ liveNavi->mSRT.t.x,
                                                            liveNavi->mSRT.t.y,
                                                            liveNavi->mSRT.t.z };
                            if (sBigTreasureElements.queryHit(target)
                                && sBigTreasureHandled.insert(
                                       static_cast<const void*>(liveNavi)).second) {
                                pc_p2_bigtreasure_stimulate_navi(recvWeapon, origin,
                                                                 kBigTreasureAttackDamage,
                                                                 liveNavi);
                            }
                        }
                        Iterator pikiIt(pikiMgr);
                        CI_LOOP(pikiIt) {
                            Piki* piki = static_cast<Piki*>(*pikiIt);
                            if (!piki || !piki->isAlive()) continue;
                            const P2BigTreasureVec3 target{ piki->mSRT.t.x,
                                                            piki->mSRT.t.y,
                                                            piki->mSRT.t.z };
                            if (sBigTreasureElements.queryHit(target)
                                && sBigTreasureHandled.insert(
                                       static_cast<const void*>(piki)).second) {
                                pc_p2_bigtreasure_stimulate_piki(recvWeapon, origin,
                                                                 kBigTreasureAttackDamage,
                                                                 piki);
                            }
                        }
                    }
                }
            }
            if (sBigTreasureVisualReady && sBigTreasureVisualDriven) {
                if (pc_p2_bigtreasure_visual_completed()) pc_p2_bigtreasure_visual_clip("wait1");
                pc_p2_bigtreasure_visual_update(1.0f);
            }
        }
    }

    // Waterwraith (#443 / #175) - lane 31 additive hook. Source-clocks the
    // registered actor on the authoritative frame delta.
    if (pc_p2_waterwraith_register_ready()) {
        pc_p2_waterwraith_register_tick(gsys->getFrameTime());
    }
}

void pc_p2_hardlanes_draw(Graphics& gfx)
{
    if (sBombSaraiReady) pc_p2_bombsarai_arena_draw(gfx);
    if (sFuefukiVisualReady) pc_p2_fuefuki_visual_draw(gfx);
    if (sBigTreasureVisualReady) {
        Matrix4f owner;
        owner.makeSRT(Vector3f(1.0f, 1.0f, 1.0f), Vector3f(0.0f, 0.0f, 0.0f),
                      Vector3f(0.0f, sBigTreasureGround, 0.0f));
        pc_p2_bigtreasure_visual_draw(gfx, owner);
    }
    // Waterwraith (#443 / #175) - lane 31 additive hook.
    if (pc_p2_waterwraith_register_ready()) {
        Matrix4f owner;
        owner.makeSRT(Vector3f(1.0f, 1.0f, 1.0f), Vector3f(0.0f, 0.0f, 0.0f),
                      Vector3f(0.0f, sWaterwraithGround, 0.0f));
        pc_p2_waterwraith_register_draw(gfx, owner);
    }
}

bool pc_p2_hardlanes_fuefuki_ready()
{
    return sFuefuki != nullptr && sFuefukiVehicle != nullptr;
}

int pc_p2_hardlanes_fuefuki_state()
{
    return sFuefuki ? static_cast<int>(sFuefuki->getFsm().getState()) : -1;
}

int pc_p2_hardlanes_fuefuki_held_count()
{
    int count = 0;
    for (const auto& entry : sFuefukiHeld) {
        if (entry.second) ++count;
    }
    return count;
}

Piki* pc_p2_hardlanes_fuefuki_held(int index)
{
    if (index < 0) return nullptr;
    int seen = 0;
    for (const auto& entry : sFuefukiHeld) {
        if (!entry.second) continue;
        if (seen++ == index) {
            auto it = sFuefukiPiki.find(entry.first);
            return it == sFuefukiPiki.end() ? nullptr : it->second;
        }
    }
    return nullptr;
}

bool pc_p2_hardlanes_fuefuki_vehicle_position(float& x, float& y, float& z)
{
    if (!sFuefukiVehicle) return false;
    const Vector3f position = sFuefukiVehicle->getPosition();
    x = position.x;
    y = position.y;
    z = position.z;
    return true;
}

// (#245) Source pressCallBack/hipdropCallBack (Fuefuki.cpp:163-185): latch the
// press stimulus on the bound vehicle. Admission (mCanStruggle && !bittered) and
// the Struggle transit are decided by the FSM on the next source tick, matching
// the source's immediate-presence check rather than a spatial radius. A no-op
// (returns false) for any unregistered Tei or when the seam is not bound.
bool pc_p2_hardlanes_fuefuki_pressed(Teki* teki, Creature*)
{
    if (!teki || !sFuefukiVehicle || teki != sFuefukiVehicle) return false;
    sFuefukiPressed     = true;
    sFuefukiPressCount += 1;
    std::printf("P2_FUEFUKI_PRESS press=%u state=%d\n",
                pc_p2_hardlanes_fuefuki_press_count(),
                pc_p2_hardlanes_fuefuki_state());
    std::fflush(stdout);
    return true;
}

unsigned pc_p2_hardlanes_fuefuki_press_count()
{
    return static_cast<unsigned>(sFuefukiPressCount);
}

// (#397/#245) Lifecycle seam: drop the bound vehicle pointer before the TekiMgr
// reuses its slot. pc_p2_hardlanes_update gates its sticker walk on sFuefukiVehicle,
// and pc_p2_hardlanes_fuefuki_pressed compares against the same pointer, so a
// forgotten actor must never leave either running on a despawned/reused Napkid.
void pc_p2_hardlanes_forget(BTeki* actor)
{
    if (!actor || !sFuefukiVehicle || static_cast<BTeki*>(sFuefukiVehicle) != actor) return;
    sFuefukiVehicle = nullptr;
    sFuefukiPressed = false;
}
