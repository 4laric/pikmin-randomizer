// Family-owned Long Legs native path (#312, parent #173).
//
// Registers the arena's P1 placement vehicles by generator ID from
// `p2-long-legs-actors.txt` (P2_LONG_LEGS_ACTORS_1), draws the installed static
// bind shape (`longlegs_<species>_bind_00.mod`), and advances the lane-owned
// source policy `pc_p2_long_legs_fsm` for each registered actor.
//
// The port has no IKSystemMgr, animation-event reader, foot collision or shell
// pool, so the policy is ticked from the draw path (which the engine calls every
// frame for on-camera registered actors) and the animation key edges are
// synthesized from the source animation key frames in the audit (30 fps). The
// policy only emits intents: foot crush, shake, shell request and death bursts
// are logged/observed, not applied. IK stability, real foot-press collision,
// Man-at-Legs shell objects and damage receivers remain lane work (#173/#186).
//
// Slice 2: the Houdai host now exposes a source damageable window and consumes
// lane 20's shared fired-projectile primitive (`pc_p2_cannon_stone.h`, the Stone
// policy/pool, #169) to fly a Man-at-Legs shell and route the source
// HoudaiShotGun damage (`InteractBomb` shellDamage 10) into a real Pikmin. The
// Stone's rolling/homing flight is a documented approximation of the source
// THdamaShell; the in-flight pool mirrors the source pool of 10.
#include "pc_p2_long_legs.h"
#include "pc_p2_long_legs_fsm.h"
#include "pc_p2_houdai_fsm.h"
#include "pc_p2_long_legs_ik.h"
#include "pc_p2_houdai_rig.h"
#include "pc_p2_attack_fx_host.h"
#include "pc_p2_groink_fx.h"
#include "pc_p2_groink_map_trace.h"
#include "pc_p2_long_legs_pose.h"
#include "pc_p2_pose_family.h"
#include "pc_p2_bigfoot_fsm.h"
#include "pc_p2_bigfoot_coll.h"
#include "pc_p2_bigfoot_skin.h"
#include "pc_p2_bigfoot_tables.h"
#include "Collision.h"
#include "ID32.h"
#include "MapMgr.h"
#include "EffectMgr.h"
#include "UtEffect.h"
#include "pc_p2_cannon_stone.h"
#include "pc_p2_animation.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_setup_failsafe.h"
#include "pc_randomizer.h"
#include "pc_bbft.h"
#include "teki.h"
#include "Pellet.h"
#include "Interactions.h"
#include "Generator.h"
#include "Shape.h"
#include "Joint.h"
#include "Material.h"
#include "system.h"
#include "Texture.h"
#include "Graphics.h"
#include "Camera.h"
#include "gameflow.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "pc_p2_navi_select.h"
#include "PikiState.h"
#include "PlayerState.h"
#include "SoundMgr.h"
#include "settings/pc_settings.h"
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <algorithm>
#include <cmath>
#include <fstream>
#include <map>
#include <set>
#include <string>
#include <vector>

extern Matrix4f invCamMat; // collInfo.cpp: camera inverse used by CollPart::getMatrix
// pc_port/gl/pc_gfx.cpp: never re-cache resident meshes whose vertex storage the CPU rewrites.
extern "C" void pc_gfx_mark_dynamic_vertex_range(const void* addr, size_t bytes);

namespace {
struct SpeciesDef {
    const char* name;
    const char* mod;
};
const SpeciesDef SPECIES[] = {
    {"Houdai", "longlegs_Houdai_bind_00.mod"},
    {"BigFoot", "longlegs_BigFoot_bind_00.mod"},
    {"Damagumo", "longlegs_Damagumo_bind_00.mod"},
};
constexpr size_t MeshBytes = 4 * 1024 * 1024;    // per species
constexpr size_t TotalBytes = 16 * 1024 * 1024;  // per setup
constexpr float AccumulateRadius = 60.0f;        // Pikmin "accumulating" census

struct ActorState {
    std::string species;
    unsigned generator = 0;
    P2LongLegsFsmParms parms;
    P2LongLegsFsm fsm;
    float animSeconds = 0.0f;   // time in the current state (source-key edges)
    float poseClock = 0.0f;     // presentation-only actor clock (BigFoot pose loops)
    bool key2Fired = false;
    float lastHealth = 0.0f;        // host damage edge for the Houdai shot cooldown
    float lastPositiveHealth = 0.0f; // last still-positive health, for death provenance
    P2LongLegsState lastState = P2LongLegsState::Stay;
    bool stateLogged = false;
    bool damageable = false;        // source damage window (Wait/Flick/Walk/Shot)
    bool bitterImmune = true;       // Stay/Land immunity
    float shotLoopAccum = 0.0f;     // Man-at-Legs attack-loop shell cadence
    Vector3f homePos;               // spawn position (source mHomePosition)
    Vector3f walkTarget;            // source mTargetPosition for the current Walk
    Vector3f walkStart;             // position at Walk entry (displacement measure)
    float walkDistance = 0.0f;      // accumulated body translation this Walk
    float walkSeconds = 0.0f;       // time spent in the current Walk
    bool hasWalkTarget = false;
    float lastMoveRatio = 1.0f;     // measured translation ratio fed to crushGate
    bool homeRecorded = false;
    bool deadEscapeDone = false;  // OWN death: pcEscapeNow fired once after Dead
    float deadSeconds = 0.0f;     // time in Dead before the escape finalizes
    // Man-at-Legs (66) own brain (#173): the source Houdai FSM replaces the
    // shared P2LongLegsFsm schedule for Houdai only; 56/69 keep the shared path.
    bool isHoudai = false;
    P2HoudaiFsm houdai;
    float srcAccum = 0.0f;          // 30 Hz source-tick accumulator
    float lastDamageCount = 0.0f;   // BTeki::mDamageCount at the last tick
    int pendingHits = 0;            // accepted hits since the last source tick
    bool pendingTook = false;       // accepted damage since the last source tick
    bool damageAttempt = false;     // stuck-Pikmin hit refused while dormant (wakes Stay)
    float landDrop = 0.0f;          // Land drop-in draw offset (1 = up high)
    bool drawHidden = false;        // Stay: dormant, not drawn
    int shellsFired = 0;
    int shellHits[3] = {0, 0, 0};   // piki, navi, teki
    int flicks = 0;
    int receiverAccepted = 0, receiverRejected = 0;
    bool scaleLogged = false;       // per-actor P2_HOUDAI_SCALE line
    bool stayIntangible = false;    // Stay: dormant presentation active
    int clearedOpts = 0;            // TEKIOPT bits currently withheld for the dormant body
    // #173 walk animation: source IKSystemMgr legs over the rigid skin
    // sidecar, drawn through a private copy of the bind mesh. Draw-only: it
    // reads the brain's strides and the map floor, draws no RNG and never
    // moves the host body, so gameplay and lockstep state are unchanged.
    Shape* ikShape = nullptr;
    bool ikStarted = false;
    bool ikBlend = false;           // Flick/Shot: IKSystemMgr::startBlendMotion (animation orientation hints)
    // #1012 sampled-joint rig: the clip pose drives the body, gun and collision tree.
    bool dormantShadowOff = true;   // Stay: no shadow (shadowMgr->delShadow) until Land
    p2attackfx::Emitter sightFx;    // red laser-sight glow generators (force-finished on end)
    bool sightOn = false;           // aiming and the gun ray reaches the ground
    Vector3f sightFrom, sightTo;    // muzzle and lock-on point of the last tick
    int sightTicks = 0, sightStarts = 0, sightHits = 0, sightMisses = 0;
    CollInfo* collOwn = nullptr;    // retail houdai/enemycoll.txt tree swapped in for the host's
    CollInfo* collHost = nullptr;
    std::vector<CollPart*> collParts;
    int collLogged = 0;
    unsigned poseDiag = 0;
    bool ikDrawLogged = false;
    p2ik::Mgr ik;
    int ikStrides = 0, ikLifts = 0, ikPlants = 0;
    // Raging Long Legs (69) own brain (#1018): source BigFoot FSM + source IK
    // legs, the retail enemycoll tree swapped onto the host, foot press, and
    // the stuck-Pikmin-only hurtbox. Replaces the shared P2LongLegsFsm path.
    bool isBigFoot = false;
    P2BigFootFsm bigfoot;
    CollInfo* bfOwnColl = nullptr;
    CollInfo* bfHostColl = nullptr;
    CollPart* bfParts[p2bigfoot::kCollNodeCount] = {};
    bool bfHidden = false;
    int bfHiddenOpts = 0;
    std::set<Creature*> bfPressed[p2ik::kLegCount]; // press once per leg descent per creature
    int bfStompPiki = 0, bfStompNavi = 0, bfStompTeki = 0;
    int bfAccepted = 0, bfRefused = 0, bfLatched = 0, bfBounced = 0;
    int bfBombs = 0;
    float bfHostLife = 0.0f;         // host vehicle health at bind (the old cap)
    Shape* bfSkinShape = nullptr;    // private posable mesh (IK legs)
    bool bfSkinLogged = false;
    bool bfSkinFailed = false;
    // TEST-ONLY evidence probe (PIKMIN_P2_LONGLEGS_PROBE=1).
    float probeTime = 0.0f;
    float probeNext = 0.0f;
    int probeThrows = 0;
    int probeStage = 0;
};

// BigFoot (69) sampled pose bank (animation smoothing pass, #972). Presentation
// only: four real clips (wait/landing/flick/dead), 24 baked poses each, lerped
// and crossfaded by p2posefamily. Absent bank -> the static bind draw.
p2posefamily::Bank bigfootBank("LONGLEGS");
p2posefamily::Actors bigfootVis;
std::map<std::string, p2longlegspose::ClipConfig> bigfootTiming;
std::map<std::string, std::vector<Shape*>> bigfootShapes;  // nearest-pose fallback

// Rigid skin of the Man-at-Legs bind mesh (longlegs_Houdai_skin_00.txt) and
// the skin joint index of every IK leg joint (Houdai::setupIKSystem order).
p2ik::Skin houdaiSkin;
bool houdaiSkinReady = false;
int houdaiLegJoint[p2ik::kLegCount][3];
float houdaiSkinBindError = 0.0f;
p2houdairig::Rig houdaiRig;              // sampled joint clips + retail collision tree (#1012)
bool houdaiRigReady = false;
int houdaiHeadJoint = -1, houdaiGunJoint = -1;

std::map<BTeki*, ActorState> actors;      // actor -> species + policy state
// Naturally dead Long Legs proxy corpses, keyed on the corpse Pellet* the engine
// created (PelletView::mPellet). A number-pellet stand-in corpse has no
// PelletView, so the receipt must key on the Pellet* (mirrors lane 31 Waterwraith).
std::map<Pellet*, unsigned> corpses;      // corpse pellet -> generator
std::map<std::string, Shape*> shapes;     // species -> bind shape
size_t bytesTotal = 0;
bool logged[2] = {false, false};

// Drop a registered corpse that died/vanished before it was delivered. The
// registry is keyed on the corpse Pellet*, and MonoObjectMgr recycles slots, so
// without this a future unrelated pellet at the same address could be credited as
// a Long Legs corpse. Mirrors lane 31's Waterwraith sweepCorpses()
// (pc_p2_waterwraith_register.cpp:48-58).
//
// Called from pc_p2_long_legs_corpse_count() (the fixture's observation point),
// NOT from the per-frame tick: an unconditional tick sweep dereferences the
// engine-owned corpse Pellet* every frame and stalled the stage-2 FSM in the
// merged wave (naviMgr went null). reset() clears the whole registry and
// forget() erases the forgotten actor's corpse, so the live tick does not need
// to sweep. A corpse that dies undelivered is still dropped the next time the
// registry is observed (or cleared), which is the slot-reuse protection.
void sweepCorpses() {
    for (auto it = corpses.begin(); it != corpses.end();) {
        if (!it->first->isAlive()) {
            std::printf("P2_LONG_LEGS_CORPSE_DROPPED generator=%u\n", it->second);
            std::fflush(stdout);
            it = corpses.erase(it);
        } else {
            ++it;
        }
    }
}

// Man-at-Legs shell pool (source pool of 10, HoudaiShotGun.cpp:1050) hosted on
// lane 20's shared fired-projectile policy. Consume-only: no forked projectile.
// Each shell remembers its firing actor (sourceToken) so a forget/death can kill
// only that actor's shells and two live Houdai never step each other's shells.
struct HoudaiShell {
    P2CannonStone* stone = nullptr;
    std::uint64_t sourceToken = 0;
};
P2CannonStonePool shellPool(10);
std::vector<HoudaiShell> shells;           // active shells, keyed by sourceToken
std::uint64_t shellSelfToken = 1;

[[noreturn]] void fail(const char* what) {
    std::fprintf(stderr, "P2_LONG_LEGS %s\n", what);
    std::abort();
}

const SpeciesDef* findSpecies(const std::string& name) {
    for (const SpeciesDef& species : SPECIES)
        if (name == species.name) return &species;
    return nullptr;
}

P2LongLegsSpecies speciesEnum(const std::string& name) {
    if (name == "BigFoot") return P2LongLegsSpecies::BigFoot;
    if (name == "Damagumo") return P2LongLegsSpecies::Damagumo;
    return P2LongLegsSpecies::Houdai;
}

// Source animation key frames (docs/PIKMIN2_LONG_LEGS_AUDIT.md) converted to
// seconds at 30 fps. Landing runs to the last landing key; Flick to the last
// flick key. Used only to synthesize the missing key edges in this fixture.
float landingSeconds(P2LongLegsSpecies species) {
    // Source Land (frames): Damagumo/Houdai 150, BigFoot 18.
    return species == P2LongLegsSpecies::BigFoot ? 18.0f / 30.0f : 150.0f / 30.0f;
}
float flickSeconds(P2LongLegsSpecies species) {
    // Source Flick (frames): Damagumo/Houdai 68, BigFoot 35.
    return species == P2LongLegsSpecies::BigFoot ? 35.0f / 30.0f : 68.0f / 30.0f;
}
float shotSeconds(P2LongLegsSpecies species) {
    // Houdai attack clip is 39 frames (Houdai.h); the gunless species never shoot.
    return species == P2LongLegsSpecies::Houdai ? 39.0f / 30.0f : 0.0f;
}
constexpr float kShellLoopPeriod = 5.0f / 30.0f; // one shell per attack loop (<-> frame 35)
constexpr float kShellHitRadius = 30.0f;         // shell radius 10 + contact margin over the +25 mouth y

Creature* nearestTarget(const Vector3f& pos, float radius) {
    Creature* best = nullptr;
    float bestSq = radius * radius;
    if (naviMgr) {
        for (Navi* n : pc_p2_navis()) {
            if (!n->isAlive()) continue;
            const Vector3f p = n->getPosition();
            const float dx = p.x - pos.x, dz = p.z - pos.z;
            const float d = dx * dx + dz * dz;
            if (d < bestSq) { bestSq = d; best = n; }
        }
    }
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!p || !p->isAlive()) continue;
            const Vector3f q = p->getPosition();
            const float dx = q.x - pos.x, dz = q.z - pos.z;
            const float d = dx * dx + dz * dz;
            if (d < bestSq) { bestSq = d; best = p; }
        }
    }
    return best;
}

// Source Houdai::getTargetPosition default (Houdai.cpp:313-349, via
// setTargetPattern: nearest navi or piki), consumed by StateWalk::init
// (HoudaiState.cpp:340-350, startIKMotion + getTargetPosition). The port has no
// IKSystemMgr, so the chosen target drives body translation at the source
// species speed instead of an IK motion; the target rule itself is source.
// A live target is taken as-is (source takes the Pikmin position); a missing
// target falls back to the source random territory-ring point around home
// (homeRadius + rand*(territory-homeRadius)).
Vector3f pickWalkTarget(const Vector3f& pos, const Vector3f& home,
                        const P2LongLegsFsmParms& parms)
{
    Creature* prey = nearestTarget(pos, parms.territoryRadius);
    if (prey) {
        Vector3f target = prey->getPosition();
        const float dx = target.x - home.x, dz = target.z - home.z;
        const float dist = std::sqrt(dx * dx + dz * dz);
        if (dist > parms.territoryRadius && dist > 1.0e-6f) {
            target.x = home.x + dx / dist * parms.territoryRadius;
            target.z = home.z + dz / dist * parms.territoryRadius;
        }
        return target;
    }
    const float range = parms.territoryRadius - parms.homeRadius;
    const float leg = parms.homeRadius + (range > 0.0f && gsys ? gsys->getRand(range) : 0.0f);
    const float ang = gsys ? gsys->getRand(6.2831853f) : 0.0f;
    return Vector3f(home.x + leg * std::sin(ang), home.y, home.z + leg * std::cos(ang));
}

int countPikiWithin(const Vector3f& pos, float radius) {
    int count = 0;
    if (!pikiMgr) return 0;
    const float rSq = radius * radius;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (!p || !p->isAlive()) continue;
        const Vector3f q = p->getPosition();
        const float dx = q.x - pos.x, dz = q.z - pos.z;
        if (dx * dx + dz * dz <= rSq) ++count;
    }
    return count;
}

// Man-at-Legs shell (consume lane 20 `P2CannonStone`; no forked projectile).
// Fired on the Shot loop boundary and stepped each tick; on contact with a live
// Pikmin the source HoudaiShotGun receiver (InteractBomb shellDamage) is applied.
// Documented approximations: the flight is the Stone's flat homing plan (no
// source gravity arc), contact is a flat 20-unit sphere (`kShellHitRadius`) keyed
// on the shell's elevated mouth y, and `nearestTarget` may select the Navi, which
// a shell can home on but never damages (InteractBomb is only routed to Pikmin).
void fireHoudaiShell(BTeki* actor, const Vector3f& pos) {
    Creature* target = nearestTarget(pos, 200.0f); // source shot search range
    if (!target) return;
    const Vector3f tp = target->getPosition();
    const float faceDir = std::atan2(tp.x - pos.x, tp.z - pos.z);
    P2CannonStoneConfig cfg;
    cfg.variant = P2CannonStoneVariant::Stone;
    cfg.moveSpeed = 600.0f;          // source shell speed (HoudaiShotGun.cpp:1193)
    cfg.searchRumbleSpeed = 600.0f;
    cfg.turnSpeed = 0.1f;            // homing steering fraction (approximation)
    cfg.maxTurnAngle = 180.0f;       // unrestricted homing sweep
    cfg.attackDamage = 10.0f;        // source Navi/Piki shell damage (HoudaiShotGun.cpp:227)
    cfg.sightRadius = 0.0f;
    cfg.collisionRadius = 10.0f;     // source shell trace radius
    cfg.health = 1.0f;
    P2CannonStoneVec3 mouth{ pos.x, pos.y + 25.0f, pos.z }; // source mouth offset
    P2CannonStone* s = shellPool.spawn(mouth, faceDir, true,
                                       (std::uint64_t)(std::uintptr_t)actor,
                                       shellSelfToken++, cfg);
    if (s) shells.push_back(HoudaiShell{s, (std::uint64_t)(std::uintptr_t)actor});
}

// Kill and drop every in-flight shell owned by `actor`, freeing its pool slots.
// Called on the host death path and on forget so a dead/forgotten Houdai never
// leaks shells (and a re-entered one regains the full 10-slot pool).
void killShellsOf(BTeki* actor) {
    const std::uint64_t token = (std::uint64_t)(std::uintptr_t)actor;
    for (HoudaiShell& shell : shells) {
        if (shell.sourceToken != token || !shell.stone) continue;
        shell.stone->notifyWallContact();
        shell.stone->finishDeath();
    }
    shells.erase(std::remove_if(shells.begin(), shells.end(),
                                [token](const HoudaiShell& s) { return s.sourceToken == token; }),
                 shells.end());
}

int countShellsOf(BTeki* actor) {
    const std::uint64_t token = (std::uint64_t)(std::uintptr_t)actor;
    int count = 0;
    for (const HoudaiShell& shell : shells)
        if (shell.sourceToken == token && shell.stone && shell.stone->isAlive()) ++count;
    return count;
}

void stepHoudaiShells(BTeki* actor, const std::string& species, unsigned generator) {
    if (shells.empty() || !pikiMgr) return;
    const std::uint64_t token = (std::uint64_t)(std::uintptr_t)actor;
    int hitTotal = 0;
    for (size_t i = 0; i < shells.size();) {
        HoudaiShell& shell = shells[i];
        if (shell.sourceToken != token) { ++i; continue; }  // only step this actor's shells
        P2CannonStone* s = shell.stone;
        if (!s || !s->isAlive()) { shells.erase(shells.begin() + i); continue; }
        const P2CannonStoneVec3 sp = s->position();
        P2CannonStoneTarget tgt;
        Creature* c = nearestTarget(Vector3f(sp.x, sp.y, sp.z), 400.0f);
        if (c) {
            const Vector3f tp = c->getPosition();
            tgt.hasTarget = true;
            tgt.position = P2CannonStoneVec3{ tp.x, tp.y, tp.z };
        }
        s->update(P2CannonStone::kSourceDelta, tgt, nullptr, nullptr);
        if (s->isAlive()) {
            const P2CannonStoneVec3 now = s->position();
            Iterator it(pikiMgr);
            CI_LOOP(it) {
                Piki* p = static_cast<Piki*>(*it);
                if (!p || !p->isAlive()) continue;
                const Vector3f q = p->getPosition();
                const float dx = q.x - now.x, dy = q.y - now.y, dz = q.z - now.z;
                if (dx * dx + dy * dy + dz * dz > kShellHitRadius * kShellHitRadius) continue;
                const P2CannonStoneContactResult res = s->contact(
                    P2CannonStoneContactKind::NaviPiki, true, false,
                    (std::uint64_t)(std::uintptr_t)p);
                if (res.strikeEmitted && res.strike.damage > 0.0f) {
                    p->stimulate(InteractBomb(actor, res.strike.damage, nullptr));
                    ++hitTotal;
                }
                s->notifyWallContact(); // terminate the shell on impact
                s->finishDeath();       // free the pool slot
                break;
            }
        }
        if (!s->isAlive()) shells.erase(shells.begin() + i);
        else ++i;
    }
    if (hitTotal > 0) {
        std::printf("P2_LONG_LEGS_SHELL_HIT species=%s generator=%u pikmin=%d\n",
                    species.c_str(), generator, hitTotal);
        std::fflush(stdout);
    }
}

// Port substitution: the P1 engine has no InteractPress callback, so the
// landing key-2 "all four feet" press is applied as a single InteractFlick
// (knockback + source press damage) to grounded Pikmin within the foot radius.
// The source foot sphere radius is not in the audit; 60 units is the documented
// port value and applies only on the landing-key-2 event.
void applyFootCrush(BTeki* actor, const Vector3f& pos, const std::string& species,
                    unsigned generator, float damage, float radius) {
    if (!pikiMgr || damage <= 0.0f) return;
    int hit = 0;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (!p || !p->isAlive()) continue;
        const Vector3f q = p->getPosition();
        const float dx = q.x - pos.x, dz = q.z - pos.z;
        if (dx * dx + dz * dz >= radius * radius) continue;
        const float angle = std::atan2(q.x - pos.x, q.z - pos.z);
        p->stimulate(InteractFlick(actor, 100.0f, damage, angle));
        ++hit;
    }
    if (hit > 0) {
        std::printf("P2_LONG_LEGS_CRUSH species=%s generator=%u pikmin=%d\n",
                    species.c_str(), generator, hit);
        std::fflush(stdout);
    }
}

// OWN movement ownership: every non-Walk tick zeroes the host drive so no
// stale Chappy TAI velocity survives the suppression (mirrors frog stop()).
void stopActor(BTeki* actor) {
    actor->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
    actor->mVelocity.x = 0.0f;
    actor->mVelocity.z = 0.0f;
}

// Source StateFlick shake-off (round-2 fidelity): flick stuck Pikmin plus
// grounded Pikmin accumulated under the body. Knockback-only, like the Jigumo
// port shake; damage itself is dealt by the Walk/landing crush.
void applyFlickShake(BTeki* actor, const Vector3f& pos, const std::string& species,
                     unsigned generator) {
    if (!pikiMgr) return;
    int hit = 0;
    for (Creature* s = actor->mStickListHead; s; s = s->mNextSticker) {
        if (!s || !s->isPiki() || !s->isAlive()) continue;
        if (s->stimulate(InteractFlick(actor, 100.0f, 0.0f, FLICK_BACKWARDS_ANGLE))) ++hit;
    }
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (!p || !p->isAlive()) continue;
        const Vector3f q = p->getPosition();
        const float dx = q.x - pos.x, dz = q.z - pos.z;
        if (dx * dx + dz * dz >= AccumulateRadius * AccumulateRadius) continue;
        if (p->stimulate(InteractFlick(actor, 100.0f, 0.0f, actor->getDirection()))) ++hit;
    }
    std::printf("P2_LONG_LEGS_FLICK species=%s generator=%u hit=%d\n",
                species.c_str(), generator, hit);
    std::fflush(stdout);
}

// ---------------------------------------------------------------------------
// Man-at-Legs (Houdai, 66) own-behaviour host (#173). The engine-free brain
// P2HoudaiFsm owns every transition; this host senses the world, applies the
// requested effects and flies the source straight shells.

// HoudaiShotGunNode (HoudaiShotGun.cpp:95): straight shell, no gravity, radius
// 10 map sphere, capsule sweep of mAttackRadius against every creature, expires
// on map contact or 1500 units (1000 in y) from its Houdai. Pool of 10 per boss.
struct HoudaiStraightShell {
    BTeki* owner = nullptr;
    unsigned generator = 0;
    int id = 0;
    Vector3f pos;
    Vector3f vel;
    float flight = 0.0f;
    int age = 0;  // source ticks alive (effect cadence)
};
std::vector<HoudaiStraightShell> houdaiShells;
P2GroinkMapTrace houdaiTrace;  // shell map trace (Groink shell trace; reset with the stage)
constexpr int kHoudaiShellPool = 10;

// Shell visuals: the source THdamaShell/THdamaHit particle sets do not exist in
// P1, so the shells reuse the P1 effects the Groink shells use (#892): the
// Beatle rock-shoot halo at the muzzle, a BombLight fire-glow puff along the
// flight each tick, and the Kando BombLight burst on map impact.
void houdaiFx(int effect, const Vector3f& pos, const Vector3f* dir) {
    if (!effectMgr) return;
    zen::particleGenerator* gen =
        effectMgr->create(static_cast<EffectMgr::effTypeTable>(effect), pos, nullptr, nullptr);
    if (gen && dir) {
        gen->setEmitDir(*dir);
        gen->setOrientedNormalVector(Vector3f(0.0f, 1.0f, 0.0f));
    }
}
void houdaiImpactFx(const Vector3f& pos) {
    if (!utEffectMgr) return;
    EffectParm parm(pos);
    utEffectMgr->cast(KandoEffect::BombLight, parm);
}

int houdaiShellCount(BTeki* owner) {
    int n = 0;
    for (const HoudaiStraightShell& s : houdaiShells) n += s.owner == owner;
    return n;
}

void houdaiDropShells(BTeki* owner, const char* why) {
    for (auto it = houdaiShells.begin(); it != houdaiShells.end();) {
        if (it->owner == owner) {
            std::printf("P2_HOUDAI_SHELL_END generator=%u shell=%d reason=%s flight=%.2f\n",
                        it->generator, it->id, why, it->flight);
            it = houdaiShells.erase(it);
        } else {
            ++it;
        }
    }
}

// Capsule test of HoudaiShotGunNode::update against one creature.
bool houdaiCapsuleHit(const Vector3f& start, const Vector3f& end, float radius, const Vector3f& at) {
    const float lx = end.x - start.x, ly = end.y - start.y, lz = end.z - start.z;
    const float dist = std::sqrt(lx * lx + ly * ly + lz * lz);
    if (!(dist > 0.0f)) return false;
    const float searchRadius = dist + radius;
    const Vector3f v1(lx / dist, ly / dist, lz / dist);
    // v2 = cross(yAxis, v1), v3 = cross(v1, v2)
    Vector3f v2(v1.z, 0.0f, -v1.x);
    float n2 = std::sqrt(v2.x * v2.x + v2.z * v2.z);
    if (n2 < 1.0e-6f) { v2 = Vector3f(1.0f, 0.0f, 0.0f); n2 = 1.0f; }
    v2.x /= n2; v2.z /= n2;
    Vector3f v3(v1.y * v2.z - v1.z * v2.y, v1.z * v2.x - v1.x * v2.z, v1.x * v2.y - v1.y * v2.x);
    const float n3 = std::sqrt(v3.x * v3.x + v3.y * v3.y + v3.z * v3.z);
    if (n3 > 1.0e-6f) { v3.x /= n3; v3.y /= n3; v3.z /= n3; }
    const Vector3f sep(at.x - start.x, at.y - start.y, at.z - start.z);
    const float d2 = v2.x * sep.x + v2.y * sep.y + v2.z * sep.z;
    if (!(std::fabs(d2) < radius)) return false;
    const float d3 = v3.x * sep.x + v3.y * sep.y + v3.z * sep.z;
    if (!(std::fabs(d3) < radius)) return false;
    const float d1 = v1.x * sep.x + v1.y * sep.y + v1.z * sep.z;
    return d1 > -radius && d1 < searchRadius;
}

// HoudaiShotGunNode::update (HoudaiShotGun.cpp:218-229) blasts a hit Pikmin or
// captain with InteractBomb(owner, attackDamage, &blastDir), where blastDir is
// the sideways offset from the shell line (dot2 * vec2, flattened, normalised
// to 100) plus y 100 for Pikmin. P1's InteractBomb has no direction and flicks
// away from the owner's position, so a Pikmin under the gun flew away from the
// boss body instead of sideways off the shell line. This receiver keeps every
// P1 bomb gate and side effect (interactBattle.cpp InteractBomb::actPiki) and
// only aims the flick along the source blast direction.
struct HoudaiShellBlast : public InteractBomb {
    HoudaiShellBlast(Creature* owner, f32 damage, const Vector3f& blast)
        : InteractBomb(owner, damage, nullptr), mBlast(blast) {}
    // PikiFlickState flies at -strength * (sin, cos)(mRotationAngle), so the
    // angle that sends the Pikmin along +blast is atan2(-x, -z).
    bool actPiki(Piki* piki) immut override {
        if (pc_settings_get_piki_invincible()) return false;
        if (!piki->isAlive()) return false;
        const int st = piki->getState();
        if (st == PIKISTATE_Drown || st == PIKISTATE_Dead || st == PIKISTATE_Dying || st == PIKISTATE_Flick)
            return false;
        if (piki->aiCullable() && !playerState->mDemoFlags.isFlag(DEMOFLAG_FirstBombDeath))
            playerState->mDemoFlags.setFlagOnly(DEMOFLAG_FirstBombDeath);
        playerState->mResultFlags.setOn(zen::RESFLAG_PikminBombDeath);
        piki->playEventSound(mOwner, SE_PIKI_DAMAGED);
        piki->mHealth -= mDamage;
        piki->mLifeGauge.updValue(piki->mHealth, C_PIKI_PARM(piki, mPikiMaxHealth));
        if (mBlast.x != 0.0f || mBlast.z != 0.0f) {
            piki->mRotationAngle = std::atan2(-mBlast.x, -mBlast.z);
        } else {
            Vector3f diff = mOwner->mSRT.t - piki->mSRT.t;
            diff.normalise();
            piki->mRotationAngle = atan2f(diff.x, diff.z);
        }
        piki->mFlickIntensity = 180.0f;
        piki->mFSM->transit(piki, PIKISTATE_Flick);
        return true;
    }
    Vector3f mBlast;
};

// Source blastDir for a creature at `at` hit by the shell segment start->end.
Vector3f houdaiBlastDir(const Vector3f& start, const Vector3f& end, const Vector3f& at, bool piki) {
    const float lx = end.x - start.x, lz = end.z - start.z;
    // vec2 = cross(yAxis, vec1) flattened: (v1.z, 0, -v1.x)
    float v2x = lz, v2z = -lx;
    const float n2 = std::sqrt(v2x * v2x + v2z * v2z);
    if (n2 < 1.0e-6f) { v2x = 1.0f; v2z = 0.0f; } else { v2x /= n2; v2z /= n2; }
    const float d2 = v2x * (at.x - start.x) + v2z * (at.z - start.z);
    float bx = d2 * v2x, bz = d2 * v2z;
    const float nb = std::sqrt(bx * bx + bz * bz);
    if (nb > 1.0e-6f) { bx /= nb; bz /= nb; } else { bx = 0.0f; bz = 0.0f; }
    return Vector3f(bx * 100.0f, piki ? 100.0f : 0.0f, bz * 100.0f);
}

void houdaiStepShells(BTeki* owner, ActorState& state, float dt) {
    const Vector3f home = owner->getPosition();
    const float radius = state.houdai.parms().attackRadius;
    const float damage = state.houdai.parms().attackDamage;
    for (auto it = houdaiShells.begin(); it != houdaiShells.end();) {
        HoudaiStraightShell& s = *it;
        if (s.owner != owner) { ++it; continue; }
        const Vector3f start = s.pos;
        Vector3f next(start.x + s.vel.x * dt, start.y + s.vel.y * dt, start.z + s.vel.z * dt);
        bool expire = false;
        const char* reason = "";
        // HoudaiShotGunNode::update: mapMgr->traceMove of a radius-10 sphere (the Groink shell trace,
        // pc_p2_groink_map_trace: same source call, same radius and tick); a floor or wall contact raises the
        // shell to ground+10 when it is below ground+20, plays the hit effect at position-10 and ends it.
        // If the trace refuses (no map), fall back to the floor-height test.
        P2GroinkTraceResult traced;
        bool contact = false;
        if (P2GroinkMapTrace::trace(&houdaiTrace, P2GroinkVec3{start.x, start.y, start.z},
                                    P2GroinkVec3{s.vel.x, s.vel.y, s.vel.z}, dt, P2GroinkPolicy::kShellRadius, traced)) {
            next = Vector3f(traced.position.x, traced.position.y, traced.position.z);
            if (traced.floor || traced.wall) {
                contact = true;
                if (traced.hasGroundY && next.y - traced.groundY < 20.0f) next.y = traced.groundY + 10.0f;
                reason = traced.wall && !traced.floor ? "wall" : "floor";
            }
        } else {
            const float ground = mapMgr ? mapMgr->getMinY(next.x, next.z, true) : -1.0e9f;
            if (next.y - 10.0f <= ground) {
                if (next.y - ground < 20.0f) next.y = ground + 10.0f;
                contact = true;
                reason = "map";
            }
        }
        if (contact) {
            expire = true;
        } else if (std::fabs(home.x - next.x) > 1500.0f || std::fabs(home.y - next.y) > 1000.0f
                   || std::fabs(home.z - next.z) > 1500.0f) {
            expire = true;
            reason = "range";
        }
        s.pos = next;
        s.flight += dt;
        if (!expire) {
            // THdamaShell follows the shell: the Groink shell visuals (#892) - a trail puff every second tick,
            // the bomb glow and the floor marker every tick, all short-lived one-shots.
            if (s.age % 2 == 0) {
                P2GroinkFxCommand c;
                c.kind = P2GroinkFxKind::Trail;
                c.pos = P2GroinkVec3{next.x, next.y, next.z};
                pc_p2_groink_fx_spawn(c);
            }
            for (const P2GroinkFxKind kind : {P2GroinkFxKind::Glow, P2GroinkFxKind::Marker}) {
                P2GroinkFxCommand c;
                c.kind = kind;
                c.pos = P2GroinkVec3{next.x, next.y, next.z};
                pc_p2_groink_fx_spawn(c);
            }
        }
        ++s.age;
        const Vector3f a(start.x, start.y - 10.0f, start.z);
        const Vector3f b(next.x, next.y - 10.0f, next.z);
        auto report = [&](Creature* c, const char* kind, float dmg, bool accepted, const Vector3f& blast) {
            const Vector3f p = c->getPosition();
            std::printf("P2_HOUDAI_SHELL_HIT generator=%u shell=%d kind=%s damage=%.1f accepted=%d "
                        "at=%.1f,%.1f,%.1f flight=%.2f blast=%.0f,%.0f,%.0f\n",
                        s.generator, s.id, kind, dmg, int(accepted), p.x, p.y, p.z, s.flight,
                        blast.x, blast.y, blast.z);
        };
        if (pikiMgr) {
            Iterator pit(pikiMgr);
            CI_LOOP(pit) {
                Piki* p = static_cast<Piki*>(*pit);
                if (!p || !p->isAlive() || !houdaiCapsuleHit(a, b, radius, p->getPosition())) continue;
                const Vector3f blast = houdaiBlastDir(a, b, p->getPosition(), true);
                const bool ok = p->stimulate(HoudaiShellBlast(owner, damage, blast));
                if (ok) ++state.shellHits[0];
                report(p, "piki", damage, ok, blast);
            }
        }
        for (Navi* n : pc_p2_navis()) {
            if (!n || !n->isAlive() || !houdaiCapsuleHit(a, b, radius, n->getPosition())) continue;
            // NaviFlickState flies back along -mFaceDirection: face against
            // the source blast so the captain is thrown along it; restore the
            // facing when the bomb is refused (invincible / PikiZero).
            const Vector3f blast = houdaiBlastDir(a, b, n->getPosition(), false);
            const float face = n->mFaceDirection;
            if (blast.x != 0.0f || blast.z != 0.0f) n->mFaceDirection = std::atan2(-blast.x, -blast.z);
            const bool ok = n->stimulate(InteractBomb(owner, damage, nullptr));
            if (!ok) n->mFaceDirection = face;
            if (ok) ++state.shellHits[1];
            report(n, "navi", damage, ok, blast);
        }
        if (tekiMgr) {
            Iterator tit(tekiMgr);
            CI_LOOP(tit) {
                Teki* t = static_cast<Teki*>(*tit);
                if (!t || t == owner || !t->isAlive() || !houdaiCapsuleHit(a, b, radius, t->getPosition())) continue;
                const bool ok = t->stimulate(InteractBomb(owner, 500.0f, nullptr));
                if (ok) ++state.shellHits[2];
                report(t, "teki", 500.0f, ok, Vector3f(0.0f, 0.0f, 0.0f));
            }
        }
        if (expire && (reason[0] == 'f' || reason[0] == 'w' || reason[0] == 'm')) {
            // Map contact: the source hit effect at position-10 (THdamaHit1/2/2W; water THdamaHit3 is not
            // told apart here), as the P1 light bomb blast the Groink hit uses.
            P2GroinkFxCommand c;
            c.kind = P2GroinkFxKind::Hit;
            c.pos = P2GroinkVec3{next.x, next.y - 10.0f, next.z};
            pc_p2_groink_fx_spawn(c);
        }
        if (expire) {
            std::printf("P2_HOUDAI_SHELL_END generator=%u shell=%d reason=%s flight=%.2f at=%.1f,%.1f,%.1f\n",
                        s.generator, s.id, reason, s.flight, next.x, next.y, next.z);
            it = houdaiShells.erase(it);
        } else {
            ++it;
        }
    }
}

float angleTo(const Vector3f& from, const Vector3f& to) {
    return std::atan2(to.x - from.x, to.z - from.z);
}

float angleDiff(float a, float b) {
    float d = a - b;
    while (d > 3.14159265f) d -= 6.28318531f;
    while (d < -3.14159265f) d += 6.28318531f;
    return d;
}

// Stuck Pikmin (source Stickers of the enemy): walk the sticker list.
int houdaiStuckCount(BTeki* actor) {
    int n = 0;
    for (Creature* s = actor->mStickListHead; s; s = s->mNextSticker)
        if (s->isPiki() && s->isAlive()) ++n;
    return n;
}

// EnemyFunc::flickStickPikmin(enemy, chance, knockback, damage, FLICK_BACKWARD_ANGLE).
int houdaiFlickStuck(BTeki* actor, float chance, float knockback, float damage, int& stuck) {
    std::vector<Creature*> stickers;
    for (Creature* s = actor->mStickListHead; s; s = s->mNextSticker)
        if (s->isPiki() && s->isAlive()) stickers.push_back(s);
    stuck = int(stickers.size());
    int hit = 0;
    for (Creature* c : stickers) {
        if (!(chance > (gsys ? gsys->getRand(1.0f) : 0.0f))) continue;
        if (c->stimulate(InteractFlick(actor, knockback, damage, FLICK_BACKWARDS_ANGLE))) ++hit;
    }
    return hit;
}

// Nearest non-stuck Pikmin (and optionally captain) within `range` and the
// half-angle `viewDeg` of `face` (EnemyFunc::getNearestPikmin[OrNavi] with
// ConditionNotStickClient).
Creature* houdaiNearest(BTeki* actor, const Vector3f& pos, float face, float viewDeg, float range, bool navis) {
    Creature* best = nullptr;
    float bestSq = range * range;
    const float view = viewDeg * 3.14159265f / 180.0f;
    auto consider = [&](Creature* c) {
        const Vector3f q = c->getPosition();
        const float dx = q.x - pos.x, dz = q.z - pos.z;
        const float d = dx * dx + dz * dz;
        if (d >= bestSq) return;
        if (viewDeg < 180.0f && std::fabs(angleDiff(std::atan2(dx, dz), face)) > view) return;
        bestSq = d;
        best = c;
    };
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!p || !p->isAlive() || p->getStickObject() == actor) continue;
            consider(p);
        }
    }
    if (navis)
        for (Navi* n : pc_p2_navis())
            if (n && n->isAlive()) consider(n);
    return best;
}

bool houdaiWake(BTeki* actor, const Vector3f& pos, float radius) {
    // EnemyFunc::isThereOlimar || isTherePikmin within mPrivateRadius.
    for (Navi* n : pc_p2_navis()) {
        if (!n || !n->isAlive()) continue;
        const Vector3f q = n->getPosition();
        // EnemyFunc::isThereOlimar (enemyAction.cpp:1525): 3D squared distance below the radius.
        if ((q.x - pos.x) * (q.x - pos.x) + (q.y - pos.y) * (q.y - pos.y) + (q.z - pos.z) * (q.z - pos.z) < radius * radius)
            return true;
    }
    return houdaiNearest(actor, pos, 0.0f, 180.0f, radius, false) != nullptr;
}

P2HoudaiVec hv(const Vector3f& v) { return P2HoudaiVec{v.x, v.y, v.z}; }

// Wall-clock ms (system clock, epoch) so frame-dump file times can be matched
// to state markers during the eye check.
long long houdaiWallMs() {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
}

void houdaiLogState(const ActorState& st, P2LongLegsState from, P2LongLegsState to, BTeki* actor) {
    const Vector3f p = actor->getPosition();
    std::printf("P2_LONG_LEGS_STATE species=Houdai generator=%u from=%s state=%s x=%.1f z=%.1f health=%.1f "
                "flick_timer=%.0f burst_timer=%.1f wall_ms=%lld\n",
                st.generator, P2LongLegsFsm::stateName(from), P2LongLegsFsm::stateName(to), p.x, p.z,
                actor->mHealth, st.houdai.flickTimer(), st.houdai.burstTimer(), houdaiWallMs());
}

// Dormant (Stay) presentation. With the sampled rig the dormant body is the landing clip's frame 0 (a low
// crouched mass, legs tucked underground): visible and, like the source Stay (the collision tree updates
// every frame and Houdai::damageCallBack has no state test), still tangible. Only the joint shadow is
// withheld until StateLand::init adds it (shadowMgr->delShadow in onInit). Without the rig the legacy draw
// hides the bind mesh in Stay, so its host collision (creatureCollision.cpp:34 skips non-Atari pairs),
// shadow and life gauge go too, and come back on Land.
void houdaiSetIntangible(BTeki* actor, ActorState& state, bool on) {
    const int want = !on ? 0
        : houdaiRigReady ? int(TEKIOPT_ShadowVisible)
                         : int(TEKIOPT_Atari | TEKIOPT_ShadowVisible | TEKIOPT_LifeGaugeVisible);
    if (on == state.stayIntangible && want == state.clearedOpts) return;
    Teki* teki = static_cast<Teki*>(actor);
    if (state.clearedOpts & ~want) teki->setTekiOption(state.clearedOpts & ~want);
    if (want & ~state.clearedOpts) teki->clearTekiOption(want & ~state.clearedOpts);
    state.clearedOpts = want;
    state.stayIntangible = on;
    std::printf("P2_HOUDAI_INTANGIBLE generator=%u on=%d atari=%d rig=%d\n", state.generator, int(on),
                int(teki->isAtari()), int(houdaiRigReady));
}

// ---- #173 IK legs ---------------------------------------------------------

const p2ik::Parms& houdaiIkParms() {
    static const p2ik::Parms parms = p2ik::houdaiParms();
    return parms;
}

// Source mapMgr->getMinY for the leg IK (foot landing height).
float houdaiGround(void*, float x, float z) {
    return mapMgr ? mapMgr->getMinY(x, z, true) : 0.0f;
}

p2ik::M34 houdaiM34(const Matrix4f& m) {
    p2ik::M34 r;
    for (int row = 0; row < 3; ++row)
        for (int col = 0; col < 4; ++col) r.m[row][col] = m.mMtx[row][col];
    return r;
}

// Body world matrix at tick time: T(pos) * RotY(face) * S(scale), the same
// SRT BTeki::refresh builds mWorldMtx from (P1 facing: forward = sin, cos).
p2ik::M34 houdaiBodyMatrix(BTeki* actor) {
    const Vector3f p = actor->getPosition();
    const float face = static_cast<Teki*>(actor)->getDirection();
    const float s = (actor->mSRT.s.y > 0.05f && actor->mSRT.s.y < 20.0f) ? actor->mSRT.s.y : 1.0f;
    const float c = std::cos(face), n = std::sin(face);
    p2ik::M34 m;
    m.m[0][0] = c * s;  m.m[0][1] = 0.0f; m.m[0][2] = n * s; m.m[0][3] = p.x;
    m.m[1][0] = 0.0f;   m.m[1][1] = s;    m.m[1][2] = 0.0f;  m.m[1][3] = p.y;
    m.m[2][0] = -n * s; m.m[2][1] = 0.0f; m.m[2][2] = c * s; m.m[2][3] = p.z;
    return m;
}

void houdaiLegJoints(const p2ik::M34& world, const std::vector<p2ik::M34>& pose,
                     p2ik::M34 out[p2ik::kLegCount][3]) {
    for (int l = 0; l < p2ik::kLegCount; ++l)
        for (int j = 0; j < 3; ++j) out[l][j] = p2ik::mul(world, pose[size_t(houdaiLegJoint[l][j])]);
}

// World -> model direction for a body matrix built like houdaiBodyMatrix (yaw about +Y).
p2ik::V3 houdaiToModelDir(float face, const P2HoudaiVec& d) {
    const float c = std::cos(face), n = std::sin(face);
    return p2ik::V3(c * d.x - n * d.z, d.y, n * d.x + c * d.z);
}

// Model-space joints the body shows for the brain's current pose (#1012): the sampled clip (frame
// + `alpha` of the next source frame for draw smoothing), the gun turned toward its aim while the
// source rotation is active (HoudaiShotGunMgr::rotateLevel/rotateVertical), and - with `withIk` and
// once the legs are captured - the twelve leg joints rewritten by the ported IKSystemMgr. Without a
// rig this is the bind skeleton (the legacy draw).
void houdaiPose(BTeki* actor, ActorState& state, const p2ik::M34& world, float alpha, bool withIk,
                std::vector<p2ik::M34>& joints) {
    const P2HoudaiFsm& brain = state.houdai;
    if (houdaiRigReady) {
        houdaiRig.sample(brain.poseClip(), float(brain.poseFrame()) + alpha, joints);
        if (brain.gunRotating()) {
            const float face = static_cast<Teki*>(actor)->getDirection();
            houdaiRig.aimGun(joints, houdaiHeadJoint, houdaiGunJoint, houdaiToModelDir(face, brain.gunDirection()));
        }
    } else {
        joints = houdaiSkin.bind;
    }
    if (withIk && state.ikStarted) {
        p2ik::M34 inv;
        if (!p2ik::inverse(world, inv)) return;
        p2ik::M34 legs[p2ik::kLegCount][3];
        houdaiLegJoints(world, joints, legs);
        state.ik.makeMatrix(legs, houdaiIkParms());
        for (int l = 0; l < p2ik::kLegCount; ++l)
            for (int j = 0; j < 3; ++j) joints[size_t(houdaiLegJoint[l][j])] = p2ik::mul(inv, legs[l][j]);
    }
}

// Houdai::updateIKSystem, driven by the brain's stride choice: capture the
// planted feet once the boss has landed, start one leg cycle per brain
// stride, and advance the legs one source frame.
void houdaiIkStep(BTeki* actor, ActorState& state, const P2HoudaiOutput& out) {
    if (!state.ikShape) return;
    const P2LongLegsState now = state.houdai.state();
    const p2ik::M34 world = houdaiBodyMatrix(actor);
    std::vector<p2ik::M34> pose;
    houdaiPose(actor, state, world, 0.0f, false, pose);
    if (!state.ikStarted) {
        // StateLand::cleanup startProgramedIK: the legs are captured at the end of the landing clip.
        const bool grounded = houdaiRigReady ? (now != P2LongLegsState::Stay && now != P2LongLegsState::Land)
                                             : !(out.drawHidden || out.landDrop > 0.0f || now == P2LongLegsState::Stay
                                                 || now == P2LongLegsState::Land);
        if (!grounded) return;
        p2ik::M34 legs[p2ik::kLegCount][3];
        houdaiLegJoints(world, pose, legs);
        const Vector3f p = actor->getPosition();
        const float face = static_cast<Teki*>(actor)->getDirection();
        state.ik.init(p2ik::V3(p.x, p.y, p.z), face);
        state.ik.startProgramedIK(legs, p2ik::V3(p.x, p.y, p.z), face);
        state.ikStarted = true;
        std::printf("P2_HOUDAI_IK_START generator=%u state=%s foot_radius=%.1f leg_angles=%.2f,%.2f,%.2f,%.2f "
                    "thigh=%.1f shin=%.1f pose=%s\n",
                    state.generator, P2LongLegsFsm::stateName(now), state.ik.distanceOffset(),
                    state.ik.legAngle(0), state.ik.legAngle(1), state.ik.legAngle(2), state.ik.legAngle(3),
                    state.ik.leg(0).topToMiddle, state.ik.leg(0).middleToBottom, houdaiRigReady ? "clip" : "bind");
    }
    // Flick/Shot run with blend motion on (Flick::init/Shot::init startBlendMotion, cleanup finish).
    const bool blend = now == P2LongLegsState::Flick || now == P2LongLegsState::Shot;
    if (blend != state.ikBlend) state.ikBlend = blend;
    state.ik.setBlend(state.ikBlend);
    if (out.strideStart) {
        state.ik.startCycleTo(p2ik::V3(out.strideTo.x, 0.0f, out.strideTo.z), out.strideFace, houdaiIkParms(),
                              houdaiGround, nullptr);
        ++state.ikStrides;
        ++state.ikLifts;
        std::printf("P2_HOUDAI_IK_STRIDE generator=%u n=%d to=%.1f,%.1f face=%.3f lifts=%d plants=%d\n",
                    state.generator, state.ikStrides, out.strideTo.x, out.strideTo.z, out.strideFace,
                    state.ikLifts, state.ikPlants);
    }
    p2ik::M34 legs[p2ik::kLegCount][3];
    houdaiLegJoints(world, pose, legs);
    state.ik.update(houdaiIkParms(), P2HoudaiFsm::kDelta, houdaiGround, nullptr, legs);
    for (int l = 0; l < p2ik::kLegCount; ++l) {
        if (state.ik.liftedMask() & (1 << l)) ++state.ikLifts;
        if (state.ik.plantedMask() & (1 << l)) ++state.ikPlants;
    }
}

// Pose the private mesh: the rig's clip pose (or the bind skeleton without a rig) with the gun turned
// and the twelve leg joints taking the IK result (IKSystemMgr::makeMatrix on the world joints under
// the drawn body) mapped back to model space, then the rigid skin evaluated on it.
bool houdaiIkPose(BTeki* actor, ActorState& state, bool corpse) {
    if (!state.ikShape || !houdaiSkinReady) return false;
    if (!houdaiRigReady && !state.ikStarted) return false;  // legacy draw keeps the static bind mesh until IK runs
    const p2ik::M34 world = houdaiM34(actor->mWorldMtx);
    p2ik::M34 inv;
    if (!p2ik::inverse(world, inv)) return false;
    static std::vector<p2ik::M34> joints;
    static std::vector<p2ik::V3> pos, nrm;
    // Between two 30 Hz source ticks blend toward the next clip frame (presentation only).
    float alpha = 0.0f;
    if (houdaiRigReady && state.houdai.poseAdvancing())
        alpha = std::fmin(0.999f, std::fmax(0.0f, state.srcAccum / P2HoudaiFsm::kDelta));
    // A carried corpse moves away from the spot its legs were planted on: no IK for it (the dead clip's own legs).
    houdaiPose(actor, state, world, alpha, !corpse, joints);
    if ((++state.poseDiag % 90) == 1) {
        const p2ik::V3 k = joints[0].col(3), g = joints[size_t(houdaiGunJoint)].col(3);
        std::printf("P2_HOUDAI_POSE_DIAG generator=%u state=%s clip=%s frame=%d alpha=%.2f ik=%d kosi_model_y=%.1f gun_model_y=%.1f "
                    "world_y=%.1f actor_y=%.1f world_scale_y=%.2f corpse=%d tama_y=%.1f damage_count=%.0f flick_timer=%.0f stuck=%d\n",
                    state.generator, P2LongLegsFsm::stateName(state.houdai.state()),
                    p2houdairig::Rig::clipName(state.houdai.poseClip()), state.houdai.poseFrame(), alpha,
                    int(state.ikStarted), k.y, g.y, world.m[1][3], actor->getPosition().y, world.m[1][1], int(corpse),
                    (state.collParts.size() > 1 && state.collParts[1]) ? state.collParts[1]->mCentre.y : -9999.0f,
                    actor->mDamageCount, state.houdai.flickTimer(), houdaiStuckCount(actor));
        std::fflush(stdout);
    }
    houdaiSkin.evaluate(joints, pos, nrm);
    Shape* shape = state.ikShape;
    for (size_t i = 0; i < pos.size(); ++i) shape->mVertexList[i].set(pos[i].x, pos[i].y, pos[i].z);
    for (size_t i = 0; i < nrm.size(); ++i) shape->mNormalList[i].set(nrm[i].x, nrm[i].y, nrm[i].z);
    BoundBox bounds(shape->mVertexList[0], shape->mVertexList[0]);
    for (int i = 1; i < shape->mVertexCount; ++i) bounds.expandBound(shape->mVertexList[i]);
    // The resident-mesh cache keys on the display list: without this the first pose drawn (Stay, landing frame
    // 0, the crouch) stays on screen for the life of the level, whatever the vertices say (owner playtest
    // 2026-09-30: the boss never stood up). Same rule as p2pose::write (#897).
    pc_gfx_mark_dynamic_vertex_range(shape->mVertexList, size_t(shape->mVertexCount) * sizeof(shape->mVertexList[0]));
    pc_gfx_mark_dynamic_vertex_range(shape->mNormalList, size_t(shape->mNormalCount) * sizeof(shape->mNormalList[0]));
    shape->mCourseExtents = bounds;
    shape->mJointList[0].mBounds = bounds;
    if (!state.ikDrawLogged) {
        state.ikDrawLogged = true;
        std::printf("P2_HOUDAI_IK_DRAW generator=%u positions=%zu normals=%zu private_geometry=1 pose=%s\n",
                    state.generator, pos.size(), nrm.size(), houdaiRigReady ? "rig" : "bind");
    }
    return true;
}

// Private copy of the bind mesh for one Man-at-Legs (materials and textures
// shared with the species shape, like p2pose::privateShape).
Shape* houdaiPrivateShape(const char* rel, Shape& shared) {
    const int previousHeap = gsys->setHeap(SYSHEAP_App);
    Shape* model = gsys->getShape(rel, rel, nullptr, true);
    gsys->setHeap(previousHeap);
    if (!model || model->mJointCount != 1 || model->mVertexCount != int(houdaiSkin.posLocal.size())
            || model->mNormalCount != int(houdaiSkin.nrmLocal.size())
            || model->mMaterialCount != shared.mMaterialCount || model->mTexAttrCount != shared.mTexAttrCount
            || model->mTevInfoCount != shared.mTevInfoCount || model->mVertexList == shared.mVertexList)
        return nullptr;
    for (int j = 0; j < model->mTotalMatpolyCount; ++j) {
        auto* poly = model->mMatpolyList[j];
        if (!poly || !poly->mMaterial) continue;
        int material = -1;
        for (int m = 0; m < model->mMaterialCount; ++m)
            if (poly->mMaterial == &model->mMaterialList[m]) material = m;
        if (material < 0) return nullptr;
        poly->mMaterial = &shared.mMaterialList[material];
    }
    model->mMaterialList = shared.mMaterialList;
    model->mTexAttrList = shared.mTexAttrList;
    model->mTevInfoList = shared.mTevInfoList;
    return model;
}

// Load the sampled clip rig (longlegs_Houdai_rig_00.txt, experimental/pikmin2_houdai_rig.py). It must agree
// with the skin sidecar (same joint names, order and hierarchy). Anything missing or inconsistent leaves the
// legacy bind-pose draw and is reported; it never aborts the session.
void houdaiRigLoad() {
    houdaiRigReady = false;
    houdaiHeadJoint = houdaiGunJoint = -1;
    std::ifstream file("assets/dataDir/courses/pikmin2room/longlegs_Houdai_rig_00.txt", std::ios::binary);
    if (!file) {
        std::printf("P2_HOUDAI_RIG status=absent pose=bind\n");
        return;
    }
    const std::string text((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
    std::string error;
    if (!houdaiRig.parse(text, &error)) {
        std::printf("P2_HOUDAI_RIG status=invalid error=%s pose=bind\n", error.c_str());
        return;
    }
    if (houdaiRig.jointCount() != int(houdaiSkin.names.size())) {
        std::printf("P2_HOUDAI_RIG status=joint_count_mismatch rig=%d skin=%zu pose=bind\n", houdaiRig.jointCount(),
                    houdaiSkin.names.size());
        return;
    }
    for (int j = 0; j < houdaiRig.jointCount(); ++j)
        if (houdaiRig.jointName(j) != houdaiSkin.names[size_t(j)]) {
            std::printf("P2_HOUDAI_RIG status=joint_name_mismatch joint=%d rig=%s skin=%s pose=bind\n", j,
                        houdaiRig.jointName(j).c_str(), houdaiSkin.names[size_t(j)].c_str());
            return;
        }
    houdaiHeadJoint = houdaiRig.joint("tamajnt");
    houdaiGunJoint = houdaiRig.joint("gun");
    if (houdaiHeadJoint < 0 || houdaiGunJoint < 0) {
        std::printf("P2_HOUDAI_RIG status=missing_gun_joint pose=bind\n");
        return;
    }
    // The rig's bind-time standing pose must be consistent with the skin bind (same skeleton): the wait
    // clip's kosi joint sits at the animated standing height.
    houdaiRigReady = true;
    std::printf("P2_HOUDAI_RIG status=ready joints=%d clips=5 poses=%d min_poses_per_clip=%d coll_nodes=%zu "
                "landing=%d wait=%d flick=%d attack=%d dead=%d interpolation=slerp pose=clip\n",
                houdaiRig.jointCount(), houdaiRig.totalPoses(), houdaiRig.minPoses(), houdaiRig.coll().size(),
                houdaiRig.poseCount(p2houdairig::Rig::Landing), houdaiRig.poseCount(p2houdairig::Rig::Wait),
                houdaiRig.poseCount(p2houdairig::Rig::Flick), houdaiRig.poseCount(p2houdairig::Rig::Attack),
                houdaiRig.poseCount(p2houdairig::Rig::Dead));
}

// Load the skin sidecar and give every Houdai its private posable mesh. Any
// missing or mismatched input leaves the actor on the static bind draw.
void houdaiIkSetup(const SpeciesDef& def, Shape* shared) {
    houdaiSkinReady = false;
    std::ifstream file("assets/dataDir/courses/pikmin2room/longlegs_Houdai_skin_00.txt", std::ios::binary);
    if (!file || !shared) {
        std::printf("P2_HOUDAI_IK_SKIN status=absent pose=bind\n");
        return;
    }
    const std::string text((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
    std::string error;
    if (!houdaiSkin.parse(text, &error)) {
        std::printf("P2_HOUDAI_IK_SKIN status=invalid error=%s pose=bind\n", error.c_str());
        return;
    }
    for (int l = 0; l < p2ik::kLegCount; ++l)
        for (int j = 0; j < 3; ++j) {
            houdaiLegJoint[l][j] = houdaiSkin.joint(p2ik::kHoudaiLegJoints[l][j]);
            if (houdaiLegJoint[l][j] < 0) {
                std::printf("P2_HOUDAI_IK_SKIN status=missing_joint joint=%s pose=bind\n",
                            p2ik::kHoudaiLegJoints[l][j]);
                return;
            }
        }
    if (shared->mVertexCount != int(houdaiSkin.posLocal.size())
            || shared->mNormalCount != int(houdaiSkin.nrmLocal.size())) {
        std::printf("P2_HOUDAI_IK_SKIN status=count_mismatch mod=%d/%d skin=%zu/%zu pose=bind\n",
                    shared->mVertexCount, shared->mNormalCount, houdaiSkin.posLocal.size(),
                    houdaiSkin.nrmLocal.size());
        return;
    }
    // The bind matrices must reproduce the installed bind mesh.
    std::vector<p2ik::V3> pos, nrm;
    houdaiSkin.evaluate(houdaiSkin.bind, pos, nrm);
    float worst = 0.0f;
    for (size_t i = 0; i < pos.size(); ++i) {
        const Vector3f& v = shared->mVertexList[i];
        worst = std::fmax(worst, std::fabs(v.x - pos[i].x) + std::fabs(v.y - pos[i].y) + std::fabs(v.z - pos[i].z));
    }
    houdaiSkinBindError = worst;
    if (!(worst < 0.05f)) {
        std::printf("P2_HOUDAI_IK_SKIN status=bind_mismatch max_error=%.4f pose=bind\n", worst);
        return;
    }
    houdaiSkinReady = true;
    houdaiRigLoad();
    const std::string rel = std::string("courses/pikmin2room/") + def.mod;
    for (auto& entry : actors) {
        ActorState& state = entry.second;
        if (!state.isHoudai) continue;
        state.ikShape = houdaiPrivateShape(rel.c_str(), *shared);
        std::printf("P2_HOUDAI_IK_READY generator=%u joints=%zu positions=%zu normals=%zu bind_error=%.5f "
                    "private_geometry=%d rng=0 body=brain\n",
                    state.generator, houdaiSkin.bind.size(), houdaiSkin.posLocal.size(),
                    houdaiSkin.nrmLocal.size(), worst, int(state.ikShape != nullptr));
        if (!state.ikShape && houdaiRigReady) {
            // The rig draws through the private shape; without it fall back to the legacy bind draw for all.
            houdaiRigReady = false;
            std::printf("P2_HOUDAI_RIG status=no_private_shape generator=%u pose=bind\n", state.generator);
        }
    }
    // The dormant presentation was chosen at bind time, before the rig was known: reconcile it.
    for (auto& entry : actors)
        if (entry.second.isHoudai) houdaiSetIntangible(entry.first, entry.second, entry.second.stayIntangible);
}

// ---- #1012 retail collision tree -------------------------------------------
// houdai/enemycoll.txt (US GPVE01 rev 0): root `none` r50 (code `____`, joint kosi) with one child `tama`
// r30 (code `st__`, offset 5,0,0 in the kosi frame). `tama` is the only stickable part (CollPart::isStickable
// matches the code against `s***`, collinfo.cpp:806-809): Pikmin latch onto it and Houdai::damageCallBack only
// accepts a stuck Pikmin. (Houdai::setupCollision asks for a tube tree on `rht1`, which this file does not
// contain, so the call is a no-op.) The tree replaces the P1 Swallow host's (host-swap pattern of the Groink,
// Emperor Bulblax and Titan Dweevil) and is posed through the clip every source tick like
// mCollTree->update() in doAnimationCullingOff.
unsigned houdaiFourcc(const std::string& id) {
    unsigned v = 0;
    for (int i = 0; i < 4; ++i) v = (v << 8) | unsigned(static_cast<unsigned char>(i < int(id.size()) && id[size_t(i)] ? id[size_t(i)] : '_'));
    return v;
}

void houdaiBuildColl(BTeki* t, ActorState& s) {
    if (s.collOwn || !houdaiRigReady || !t->mCollInfo || houdaiRig.coll().empty()) return;
    const std::vector<p2houdairig::CollNode>& tree = houdaiRig.coll();
    std::vector<ObjCollInfo*> nodes;
    for (const p2houdairig::CollNode& node : tree) {
        auto* n = new ObjCollInfo();
        n->mId.setID(houdaiFourcc(node.id));
        n->mCode.setID(houdaiFourcc(node.code));
        n->mRadius = node.radius;
        n->mCentrePosition.set(0.0f, 0.0f, 0.0f);
        n->mJointIndex = 0;
        nodes.push_back(n);
    }
    for (size_t i = 1; i < tree.size(); ++i) {
        if (tree[i].parent < 0) continue;
        nodes[size_t(tree[i].parent)]->add(nodes[i]);
    }
    s.collOwn = new CollInfo(int(nodes.size()) + 14);
    s.collOwn->initInfoTree(nodes[0]);
    int found = 0, stick = 0;
    s.collParts.assign(tree.size(), nullptr);
    for (size_t i = 0; i < tree.size(); ++i) {
        s.collParts[i] = s.collOwn->getSphere(houdaiFourcc(tree[i].id));
        if (s.collParts[i]) {
            ++found;
            s.collParts[i]->mIsUpdateActive = false;  // no parent shape: houdaiUpdateColl owns centre/radius
            s.collParts[i]->mJointMatrix = Matrix4f::ident;
        }
        stick += tree[i].stickable() ? 1 : 0;
    }
    s.collHost = t->mCollInfo;
    t->mCollInfo = s.collOwn;
    // The host's platforms would report contacts whose part this tree cannot resolve.
    t->mPlatMgr.release();
    std::printf("P2_HOUDAI_COLL_BIND generator=%u nodes=%zu parts_found=%d stickable=%d source=houdai/enemycoll.txt "
                "host_parts_replaced=1\n",
                s.generator, tree.size(), found, stick);
    std::fflush(stdout);
}

// Pose every node through the joints of this tick (model space) under the body matrix `world`.
void houdaiUpdateColl(BTeki* t, ActorState& s, const p2ik::M34& world, const std::vector<p2ik::M34>& joints) {
    if (!s.collOwn || t->mCollInfo != s.collOwn) return;
    const float face = static_cast<Teki*>(t)->getDirection();
    Matrix4f yaw, camRot, camYaw;
    yaw.makeSRT(Vector3f(1.0f, 1.0f, 1.0f), Vector3f(0.0f, face, 0.0f), Vector3f(0.0f, 0.0f, 0.0f));
    camRot.makeIdentity();
    for (int r = 0; r < 3; ++r)
        for (int c = 0; c < 3; ++c) camRot.mMtx[r][c] = invCamMat.mMtx[c][r];
    camRot.multiplyTo(yaw, camYaw);
    const float scale = std::sqrt(world.m[0][0] * world.m[0][0] + world.m[1][0] * world.m[1][0] + world.m[2][0] * world.m[2][0]);
    const std::vector<p2houdairig::CollNode>& tree = houdaiRig.coll();
    for (size_t i = 0; i < s.collParts.size(); ++i) {
        CollPart* part = s.collParts[i];
        if (!part) continue;
        const p2ik::V3 w = p2ik::apply(world, houdaiRig.collCentre(joints, int(i)));
        part->mCentre.set(w.x, w.y, w.z);
        part->mRadius = tree[i].radius * (scale > 0.05f ? scale : 1.0f);
        part->mJointMatrix = camYaw;
        if (s.collLogged < 3 && i == 1) {
            ++s.collLogged;
            std::printf("P2_HOUDAI_COLL_POSE generator=%u state=%s clip=%s frame=%d part=%s centre=%.1f,%.1f,%.1f "
                        "radius=%.1f stickable=%d\n",
                        s.generator, P2LongLegsFsm::stateName(s.houdai.state()),
                        p2houdairig::Rig::clipName(s.houdai.poseClip()), s.houdai.poseFrame(), tree[i].id.c_str(),
                        w.x, w.y, w.z, part->mRadius, int(tree[i].stickable()));
        }
    }
}

// Hand the host its own tree back (death funnel / forget / reset). The own tree is never freed: a stuck
// Pikmin may still hold CollPart pointers into it.
void houdaiRestoreColl(BTeki* t, ActorState& s) {
    if (!s.collOwn) return;
    if (s.collHost && t && t->mCollInfo == s.collOwn) t->mCollInfo = s.collHost;
    s.collOwn = nullptr;
    s.collHost = nullptr;
    s.collParts.clear();
}

// ---- #1012 laser sight -------------------------------------------------------
// HoudaiShotGunMgr::setShotGunLockOnPosition (HoudaiShotGun.cpp, run from doUpdate while the source
// rotation is searching): from the gun joint march the gun X axis 50 units, then up to 60 steps of 10
// units; at the first step below the floor (mapMgr->getMinY above the point) clamp to the floor and
// place efx::THdamaSight there with the reversed axis as normal; if the ray never reaches the floor the
// sight fades. PSSE_EN_HOUDAI_BEAM plays at the lock position. P1 has no THdamaSight resource, so the
// red sight is drawn as P1 effects (a red-tinted Navi light glow at the lock point and along the ray)
// and, in the actor draw, a red line from the muzzle to the lock point (houdaiDrawSight).
constexpr int kEffNaviLightGlow = 22;
static_assert(int(EffectMgr::EFF_Navi_LightGlow) == kEffNaviLightGlow, "EFF_Navi_LightGlow id");
constexpr unsigned kSightRgb = 0xFF2020;

void houdaiSightEnd(ActorState& state, const char* why) {
    if (!state.sightOn && state.sightTicks == 0) return;
    const unsigned gens = state.sightFx.stopAll();
    std::printf("P2_HOUDAI_SIGHT generator=%u event=end reason=%s ticks=%d hit=%d miss=%d generators=%u\n",
                state.generator, why, state.sightTicks, state.sightHits, state.sightMisses, gens);
    std::fflush(stdout);
    state.sightOn = false;
    state.sightTicks = 0;
}

void houdaiSightTick(BTeki* actor, ActorState& state, const p2ik::M34& world, const std::vector<p2ik::M34>& joints) {
    (void)actor;
    if (!houdaiRigReady) return;
    if (!state.houdai.gunAiming()) {
        houdaiSightEnd(state, "aim_end");
        return;
    }
    const p2ik::M34 gun = p2ik::mul(world, joints[size_t(houdaiGunJoint)]);
    const p2ik::V3 origin = gun.col(3);
    p2ik::V3 axis = gun.col(0);
    const float len = std::sqrt(axis.x * axis.x + axis.y * axis.y + axis.z * axis.z);
    if (!(len > 1.0e-6f)) return;
    axis = p2ik::V3(axis.x / len, axis.y / len, axis.z / len);
    if (state.sightTicks == 0) {
        ++state.sightStarts;
        std::printf("P2_HOUDAI_SIGHT generator=%u event=start n=%d\n", state.generator, state.sightStarts);
    }
    ++state.sightTicks;
    p2ik::V3 lock(origin.x + axis.x * 50.0f, origin.y + axis.y * 50.0f, origin.z + axis.z * 50.0f);
    bool hit = false;
    for (int i = 0; i < 60; ++i) {
        lock = p2ik::V3(lock.x + axis.x * 10.0f, lock.y + axis.y * 10.0f, lock.z + axis.z * 10.0f);
        const float minY = mapMgr ? mapMgr->getMinY(lock.x, lock.z, true) : -1.0e9f;
        if (minY > lock.y) {
            lock.y = minY;
            hit = true;
            break;
        }
    }
    state.sightFrom = Vector3f(origin.x, origin.y, origin.z);
    state.sightTo = Vector3f(lock.x, lock.y, lock.z);
    state.sightOn = hit;
    if (hit) ++state.sightHits;
    else ++state.sightMisses;
    if (state.sightTicks <= 6 || state.sightTicks % 15 == 0)
        std::printf("P2_HOUDAI_SIGHT_TRACE generator=%u tick=%d hit=%d from=%.1f,%.1f,%.1f lock=%.1f,%.1f,%.1f "
                    "axis=%.2f,%.2f,%.2f yaw=%.2f tilt=%.2f\n",
                    state.generator, state.sightTicks, int(hit), origin.x, origin.y, origin.z, lock.x, lock.y,
                    lock.z, axis.x, axis.y, axis.z, state.houdai.gunYaw(), state.houdai.gunTilt());
    if (!hit) return;
    // Red glow at the lock point plus a beam of small glows along the ray (P1 effects, owned by the
    // actor's Emitter so every generator is force-finished when the sight ends).
    const float dx = axis.x, dz = axis.z;
    const float hl = std::sqrt(dx * dx + dz * dz);
    const float ux = hl > 1.0e-4f ? dx / hl : 0.0f, uz = hl > 1.0e-4f ? dz / hl : 0.0f;
    p2attackfx::Point pts[8];
    int n = 0;
    const float total = std::sqrt((lock.x - origin.x) * (lock.x - origin.x) + (lock.y - origin.y) * (lock.y - origin.y)
                                  + (lock.z - origin.z) * (lock.z - origin.z));
    for (int i = 1; i <= 6; ++i) {
        const float t = float(i) / 7.0f;
        pts[n++] = {p2attackfx::Kind::Body, origin.x + (lock.x - origin.x) * t, origin.y + (lock.y - origin.y) * t,
                    origin.z + (lock.z - origin.z) * t, 0.35f, ux, uz};
    }
    pts[n++] = {p2attackfx::Kind::Tip, lock.x, lock.y + 1.0f, lock.z, 1.6f, ux, uz};
    (void)total;
    p2attackfx::Look look{kEffNaviLightGlow, 6, true, kSightRgb};
    state.sightFx.emitLook(look, pts, n);
}

// Red line from the muzzle to the lock-on point, drawn in the actor's draw pass (Graphics::drawLine
// renders 1 px lines on the GL backend whatever setLineWidth says, so the beam is a small bundle).
void houdaiDrawSight(Graphics& gfx, const ActorState& state) {
    if (!state.sightOn || !gfx.mCamera) return;
    const Colour oldColour = gfx.mPrimaryColour;
    const Colour oldAux = gfx.mAuxiliaryColour;
    const int oldBlend = gfx.setCBlending(BLEND_Alpha);
    Texture* oldTexture = gfx.mActiveTexture[0];
    const bool oldLight = gfx.setLighting(false, nullptr);
    const float oldWidth = gfx.setLineWidth(3.0f);
    gfx.useMaterial(nullptr);
    gfx.useTexture(nullptr, 0);
    gfx.useMatrix(gfx.mCamera->mLookAtMtx, 0);
    const Vector3f a = state.sightFrom, b = state.sightTo;
    gfx.setColour(Colour(255, 30, 30, 235), true);
    static const float offs[5][2] = {{0.0f, 0.0f}, {0.7f, 0.0f}, {-0.7f, 0.0f}, {0.0f, 0.7f}, {0.0f, -0.7f}};
    for (const auto& o : offs)
        gfx.drawLine(Vector3f(a.x + o[0], a.y + o[1], a.z), Vector3f(b.x + o[0], b.y + o[1], b.z));
    gfx.setLineWidth(oldWidth);
    gfx.setColour(oldColour, true);
    gfx.mAuxiliaryColour = oldAux;
    gfx.setCBlending(oldBlend);
    gfx.useTexture(oldTexture, 0);
    gfx.setLighting(oldLight, nullptr);
}

// One host frame for a registered Houdai. Returns after the escape.
void houdaiTick(BTeki* actor, ActorState& state, float dt) {
    if (actor->mStoredDamage > 0.0f) actor->makeDamaged();
    // Hit counter (source addDamage flickSpeed 1.0 per accepted attack):
    // TEKIOPT_DamageCountable bumps mDamageCount in interactDefault.
    if (actor->mDamageCount < state.lastDamageCount) state.lastDamageCount = actor->mDamageCount;
    const int newHits = int(actor->mDamageCount - state.lastDamageCount);
    state.lastDamageCount = actor->mDamageCount;
    if (newHits > 0) state.pendingHits += newHits;
    if (actor->mHealth < state.lastHealth) {
        state.pendingTook = true;
        if (actor->mHealth > 0.0f)
            std::printf("P2_LONG_LEGS_DAMAGE species=Houdai generator=%u health=%.2f prior=%.2f hits=%d state=%s\n",
                        state.generator, actor->mHealth, state.lastHealth, newHits,
                        P2LongLegsFsm::stateName(state.houdai.state()));
    }
    state.lastHealth = actor->mHealth;
    if (actor->mHealth > 0.0f) state.lastPositiveHealth = actor->mHealth;
    if (state.deadEscapeDone) return;

    state.srcAccum += dt;
    int steps = 0;
    while (state.srcAccum >= P2HoudaiFsm::kDelta && steps < 4) {
        state.srcAccum -= P2HoudaiFsm::kDelta;
        ++steps;
        const Vector3f pos = actor->getPosition();
        const P2HoudaiParms& parms = state.houdai.parms();
        P2HoudaiInput in;
        in.health = actor->mHealth;
        in.pos = hv(pos);
        in.faceDir = static_cast<Teki*>(actor)->getDirection();
        in.stuck = houdaiStuckCount(actor);
        in.wake = houdaiWake(actor, pos, parms.privateRadius);
        in.damageAttempt = state.damageAttempt;
        state.damageAttempt = false;
        in.hits = state.pendingHits;
        in.tookDamage = state.pendingTook;
        state.pendingHits = 0;
        state.pendingTook = false;
        if (Creature* w = houdaiNearest(actor, pos, in.faceDir, parms.viewAngleDeg, parms.sightRadius, false)) {
            in.walkPikiFound = true;
            in.walkPiki = hv(w->getPosition());
        }
        if (Creature* g = houdaiNearest(actor, pos, in.faceDir, 180.0f, parms.searchDistance, true)) {
            in.gunTargetFound = true;
            in.gunTarget = hv(g->getPosition());
        }
        for (float& r : in.roll) r = gsys ? gsys->getRand(1.0f) : 0.5f;
        if (houdaiRigReady) {
            // The gun pivot of the pose the body shows this tick (it does not move when the head turns or the
            // gun pitches): aim and muzzle both start from it, so the shells leave the drawn barrel.
            houdaiBuildColl(actor, state);
            std::vector<p2ik::M34> posed;
            const p2ik::M34 body = houdaiBodyMatrix(actor);
            houdaiPose(actor, state, body, 0.0f, false, posed);
            const p2ik::V3 g = p2ik::apply(body, posed[size_t(houdaiGunJoint)].col(3));
            in.gunPosValid = true;
            in.gunPos = P2HoudaiVec{g.x, g.y, g.z};
        }
        {
            // The bind mesh is drawn through the host mWorldMtx (host scale),
            // so the gun joint height follows the drawn scale.
            const Matrix4f& w = actor->mWorldMtx;
            const float sy = std::sqrt(w.mMtx[0][1] * w.mMtx[0][1] + w.mMtx[1][1] * w.mMtx[1][1]
                                       + w.mMtx[2][1] * w.mMtx[2][1]);
            in.modelScale = (sy > 0.05f && sy < 20.0f) ? sy : 1.0f;
            if (!state.scaleLogged) {
                state.scaleLogged = true;
                std::printf("P2_HOUDAI_SCALE generator=%u draw_scale=%.3f gun_height=%.1f\n", state.generator,
                            in.modelScale, parms.gunHeight * in.modelScale);
            }
        }

        const P2LongLegsState before = state.houdai.state();
        P2HoudaiOutput out;
        state.houdai.update(in, out);
        const P2LongLegsState after = state.houdai.state();

        if (out.entered) {
            if (before == P2LongLegsState::Walk && state.hasWalkTarget) {
                std::printf("P2_LONG_LEGS_WALK_END species=Houdai generator=%u distance=%.1f seconds=%.2f "
                            "start=%.1f,%.1f end=%.1f,%.1f next=%s\n",
                            state.generator, state.walkDistance, state.walkSeconds, state.walkStart.x,
                            state.walkStart.z, pos.x, pos.z, P2LongLegsFsm::stateName(after));
                state.hasWalkTarget = false;
            }
            houdaiLogState(state, before, after, actor);
            if (after == P2LongLegsState::Walk) {
                state.walkStart = pos;
                state.walkDistance = 0.0f;
                state.walkSeconds = 0.0f;
                state.hasWalkTarget = true;
                std::printf("P2_LONG_LEGS_WALK species=Houdai generator=%u from=%.1f,%.1f to=%.1f,%.1f "
                            "duration=%.2f piki_target=%d\n",
                            state.generator, pos.x, pos.z, out.walkTarget.x, out.walkTarget.z,
                            out.chosenSeconds, int(in.walkPikiFound));
            }
            if (after == P2LongLegsState::Dead) {
                std::printf("P2_LONG_LEGS_DEAD species=Houdai generator=%u health=%.2f prior_health=%.2f "
                            "shells=%d shell_hits=%d/%d/%d flicks=%d\n",
                            state.generator, actor->mHealth, state.lastPositiveHealth, state.shellsFired,
                            state.shellHits[0], state.shellHits[1], state.shellHits[2], state.flicks);
            }
        }
        if (out.flickStuck) {
            int stuck = 0;
            const int hit = houdaiFlickStuck(actor, out.flickChance, out.flickKnockback, out.flickDamage, stuck);
            ++state.flicks;
            if (stuck > 0 || std::string(out.flickCause) == "flick")
                std::printf("P2_LONG_LEGS_FLICK species=Houdai generator=%u cause=%s stuck=%d hit=%d "
                            "knockback=%.0f damage=%.0f\n",
                            state.generator, out.flickCause, stuck, hit, out.flickKnockback, out.flickDamage);
        }
        if (out.aimStart || out.burstOn || out.burstOff || out.aimEnd)
            std::printf("P2_HOUDAI_GUN generator=%u event=%s yaw=%.2f tilt=%.2f\n", state.generator,
                        out.aimStart ? "aim_start" : out.burstOn ? "burst_on" : out.burstOff ? "burst_off" : "aim_end",
                        state.houdai.gunYaw(), state.houdai.gunTilt());
        if (out.fireShell) {
            if (houdaiShellCount(actor) < kHoudaiShellPool) {
                HoudaiStraightShell s;
                s.owner = actor;
                s.generator = state.generator;
                s.id = ++state.shellsFired;
                s.pos = Vector3f(out.shellPos.x, out.shellPos.y, out.shellPos.z);
                s.vel = Vector3f(out.shellVel.x, out.shellVel.y, out.shellVel.z);
                houdaiShells.push_back(s);
                const Vector3f dir(s.vel.x / 600.0f, s.vel.y / 600.0f, s.vel.z / 600.0f);
                {
                    // THdamaShoot at the gun joint: the Groink muzzle burst (#892) along the barrel.
                    P2GroinkFxCommand c;
                    c.kind = P2GroinkFxKind::Shoot;
                    c.pos = P2GroinkVec3{s.pos.x, s.pos.y, s.pos.z};
                    c.dir = P2GroinkVec3{dir.x, dir.y, dir.z};
                    pc_p2_groink_fx_spawn(c);
                }
                std::printf("P2_HOUDAI_SHELL_FIRE generator=%u shell=%d pos=%.1f,%.1f,%.1f vel=%.1f,%.1f,%.1f "
                            "target_found=%d\n",
                            state.generator, s.id, s.pos.x, s.pos.y, s.pos.z, s.vel.x, s.vel.y, s.vel.z,
                            int(in.gunTargetFound));
            }
        }
        // Body: Walk strides translate; every state holds the host still.
        actor->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
        if (out.moving) {
            Vector3f next(out.bodyPos.x, pos.y, out.bodyPos.z);
            if (mapMgr) next.y = mapMgr->getMinY(next.x, next.z, true);
            const float dx = next.x - pos.x, dz = next.z - pos.z;
            const float step = std::sqrt(dx * dx + dz * dz);
            actor->resetPosition(next);
            state.walkDistance += step;
            state.walkSeconds += P2HoudaiFsm::kDelta;
            actor->mVelocity.set(dx / P2HoudaiFsm::kDelta, 0.0f, dz / P2HoudaiFsm::kDelta);
        } else {
            actor->mVelocity.x = 0.0f;
            actor->mVelocity.z = 0.0f;
        }
        static_cast<Teki*>(actor)->setDirection(out.bodyFace);
        houdaiStepShells(actor, state, P2HoudaiFsm::kDelta);
        state.drawHidden = out.drawHidden;
        houdaiSetIntangible(actor, state, out.drawHidden);
        state.landDrop = out.landDrop;
        houdaiIkStep(actor, state, out);
        if (houdaiRigReady) {
            // Collision tree and laser sight follow the pose of the tick just computed (mCollTree->update()
            // after the animation, HoudaiShotGunMgr::doUpdate in the same frame).
            std::vector<p2ik::M34> posed;
            const p2ik::M34 body = houdaiBodyMatrix(actor);
            houdaiPose(actor, state, body, 0.0f, false, posed);
            houdaiUpdateColl(actor, state, body, posed);
            houdaiSightTick(actor, state, body, posed);
        }
        state.damageable = out.damageRate > 0.0f;
        state.bitterImmune = after == P2LongLegsState::Stay || after == P2LongLegsState::Land;
        if (out.deadEnd && !state.deadEscapeDone) {
            // Source StateDead END: throwupItem + dead bomb + kill. The port
            // keeps the accepted 56/69 precedent: the host teardown births the
            // carriable corpse (owner decision pending, #173).
            state.deadEscapeDone = true;
            houdaiDropShells(actor, "owner_dead");
            houdaiSightEnd(state, "dead");
            houdaiRestoreColl(actor, state);
            {
                // StateDead END createDeadBombEffect (efx::TDamaDeadBomb per joint, THdamaDeadbomb on the body)
                // and the camera vibration: the P1 large-enemy death burst (wave, glow, smoke) at the body and
                // the belly, as the stand-in for the P2 particle sets.
                const Vector3f at = actor->getPosition();
                for (int effect : {int(EffectMgr::EFF_Teki_DeathWaveL), int(EffectMgr::EFF_Teki_DeathGlowL),
                                   int(EffectMgr::EFF_Teki_DeathSmokeL)}) {
                    houdaiFx(effect, Vector3f(at.x, at.y + 100.0f, at.z), nullptr);
                    houdaiFx(effect, Vector3f(at.x, at.y + 40.0f, at.z), nullptr);
                }
            }
            std::printf("P2_LONG_LEGS_ESCAPE species=Houdai generator=%u native=host_escape_now "
                        "dead_clip_frames=%d\n",
                        state.generator, P2HoudaiFsm::kDeadFrames);
            std::fflush(stdout);
            actor->pcEscapeNow();
            return;
        }
    }
    std::fflush(stdout);
}

// ---------------------------------------------------------------------------
// Raging Long Legs (BigFoot, 69) own-behaviour host (#1018). The engine-free
// brain P2BigFootFsm (pc_p2_bigfoot_fsm.cpp) owns every transition, the clip
// clocks, the flick counter and the source IK legs; this host senses the world,
// wears the retail collision tree, applies the foot press / flick / death and
// draws the posed mesh.

p2bigfootskin::Skin bigfootSkin;
bool bigfootSkinReady = false;
float bigfootSkinError = -1.0f;

unsigned bfFourcc(const char* id) {
    unsigned v = 0;
    for (int i = 0; i < 4; ++i) v = (v << 8) | unsigned(static_cast<unsigned char>(id[i] ? id[i] : '_'));
    return v;
}

p2ik::V3 bv(const Vector3f& v) { return p2ik::V3(v.x, v.y, v.z); }

const char* bigfootClipName(int clip) {
    switch (clip) {
    case P2BigFootFsm::ClipDead: return "dead";
    case P2BigFootFsm::ClipLanding: return "landing";
    case P2BigFootFsm::ClipFlick: return "flick";
    default: return "wait";
    }
}

// StateStay (BigFootState.cpp:80-92) enables EB_ModelHidden; StateLand::init
// disables it. The P1 host hides with the Crawbster/Mizinko set (#984) plus the
// life gauge: nothing draws, nothing collides, Pikmin do not target it.
void bigfootSetHidden(BTeki* actor, ActorState& state, bool hide) {
    if (hide == state.bfHidden) return;
    Teki* teki = static_cast<Teki*>(actor);
    static const int bits[] = {TEKIOPT_Visible, TEKIOPT_Organic, TEKIOPT_ShapeVisible, TEKIOPT_ShadowVisible,
                               TEKIOPT_Atari, TEKIOPT_LifeGaugeVisible};
    if (hide) {
        state.bfHiddenOpts = 0;
        for (int bit : bits)
            if (teki->getTekiOption(bit)) state.bfHiddenOpts |= bit;
        teki->clearTekiOption(state.bfHiddenOpts);
    } else {
        teki->setTekiOption(state.bfHiddenOpts);
    }
    state.bfHidden = hide;
    std::printf("P2_BIGFOOT_HIDDEN generator=%u hidden=%d atari=%d visible=%d\n", state.generator, int(hide),
                int(teki->isAtari()), int(teki->isVisible()));
}

// Swap the host tree for the retail bigfoot/enemycoll.txt tree (#1018), the
// same host-swap pattern as the Groink/Bloyster lanes (#892/#995).
void bigfootBuildColl(BTeki* actor, ActorState& st) {
    if (st.bfOwnColl || !actor->mCollInfo) return;
    namespace T = p2bigfoot;
    const float scale = st.bigfoot.parms().scale;
    std::vector<ObjCollInfo*> nodes;
    for (int i = 0; i < T::kCollNodeCount; ++i) {
        auto* n = new ObjCollInfo();
        n->mId.setID(bfFourcc(T::kColl[i].id));
        n->mCode.setID(bfFourcc(T::kColl[i].code));
        n->mRadius = T::kColl[i].radius * scale;
        n->mCentrePosition.set(0.0f, 0.0f, 0.0f);
        n->mJointIndex = 0;
        nodes.push_back(n);
    }
    for (int i = 1; i < T::kCollNodeCount; ++i) nodes[size_t(T::kColl[i].parent)]->add(nodes[size_t(i)]);
    CollInfo* own = new CollInfo(int(nodes.size()) + 14);
    own->initInfoTree(nodes[0]);
    int found = 0;
    for (int i = 0; i < T::kCollNodeCount; ++i) {
        st.bfParts[i] = own->getSphere(bfFourcc(T::kColl[i].id));
        if (!st.bfParts[i]) continue;
        ++found;
        st.bfParts[i]->mIsUpdateActive = false; // no parent shape: bigfootUpdateColl owns centre/radius
        st.bfParts[i]->mJointMatrix = Matrix4f::ident;
    }
    // Obj::setupCollision (BigFoot.cpp:647-656): makeTubeTree on the four leg
    // chains, i.e. x1..x3 are tubes to their child and x4 stays a sphere.
    int tubes = 0;
    for (const char* leg : {"lft1", "lht1", "rft1", "rht1"}) {
        if (own->getSphere(bfFourcc(leg))) {
            own->makeTubesChild(bfFourcc(leg), 3);
            tubes += 3;
        }
    }
    st.bfHostColl = actor->mCollInfo;
    actor->mCollInfo = own;
    st.bfOwnColl = own;
    // The host's model platforms would report contacts whose part this tree cannot resolve.
    actor->mPlatMgr.release();
    std::printf("P2_BIGFOOT_COLL_BIND generator=%u nodes=%d parts_found=%d stickable=%d (tama,lht1) tubes=%d "
                "root_radius=%.0f body_radius=%.0f host_parts_replaced=1\n",
                st.generator, T::kCollNodeCount, found, p2bigfootcoll::stickableCount(), tubes,
                double(T::kColl[0].radius * scale), double(T::kColl[p2bigfootcoll::nodeIndex("tama")].radius * scale));
}

// Pose every part from the brain's skeleton (clip body, IK legs).
void bigfootUpdateColl(BTeki* actor, ActorState& st) {
    if (!st.bfOwnColl || actor->mCollInfo != st.bfOwnColl) return;
    Matrix4f yaw, camRot, camYaw;
    yaw.makeSRT(Vector3f(1.0f, 1.0f, 1.0f), Vector3f(0.0f, st.bigfoot.face(), 0.0f), Vector3f(0.0f, 0.0f, 0.0f));
    camRot.makeIdentity();
    for (int r = 0; r < 3; ++r)
        for (int c = 0; c < 3; ++c) camRot.mMtx[r][c] = invCamMat.mMtx[c][r];
    camRot.multiplyTo(yaw, camYaw);
    const float scale = st.bigfoot.parms().scale;
    for (int i = 0; i < p2bigfoot::kCollNodeCount; ++i) {
        CollPart* part = st.bfParts[i];
        if (!part) continue;
        const p2ik::V3 c = st.bigfoot.collCentre(i);
        part->mCentre.set(c.x, c.y, c.z);
        part->mRadius = p2bigfoot::kColl[i].radius * scale;
        part->mJointMatrix = camYaw;
    }
}

// Hand the host its own tree back (death / forget). The own tree is never
// freed: a stuck Pikmin may still hold CollPart pointers into it.
void bigfootRestoreColl(BTeki* actor, ActorState& st) {
    if (!st.bfOwnColl) return;
    if (st.bfHostColl && actor && actor->mCollInfo == st.bfOwnColl) actor->mCollInfo = st.bfHostColl;
    st.bfOwnColl = nullptr;
    st.bfHostColl = nullptr;
    for (auto& part : st.bfParts) part = nullptr;
}

int bigfootNodeOf(const ActorState& st, const CollPart* part) {
    if (!part) return -1;
    for (int i = 0; i < p2bigfoot::kCollNodeCount; ++i)
        if (st.bfParts[i] == part) return i;
    return -1;
}

// Obj::collisionCallback (BigFoot.cpp:220-238): a Navi or Piki standing on the
// floor that collides with a foot sphere whose leg is lifting/descending with a
// move ratio above 1 (IKSystemMgr::isCollisionCheck) is pressed with
// mAttackDamage; another teki takes InteractAttack 500. The host test is the
// sphere contact itself; each creature is pressed once per leg descent.
void bigfootStomp(BTeki* actor, ActorState& st, const P2BigFootOutput& out) {
    const float damage = st.bigfoot.parms().attackDamage;
    const float scale = st.bigfoot.parms().scale;
    for (int leg = 0; leg < p2ik::kLegCount; ++leg) {
        if ((out.lifted >> leg) & 1) st.bfPressed[leg].clear();
        if (!st.bigfoot.footPressing(leg)) continue;
        const int node = p2bigfootcoll::nodeIndex(P2BigFootFsm::kFootNode[leg]);
        const p2ik::V3 c = st.bigfoot.collCentre(node);
        const float radius = p2bigfoot::kColl[node].radius * scale;
        int piki = 0, navi = 0, teki = 0;
        auto touching = [&](Creature* cr) {
            const Vector3f q = cr->getCentre();
            const float dx = q.x - c.x, dy = q.y - c.y, dz = q.z - c.z;
            const float r = radius + cr->getCentreSize();
            return dx * dx + dy * dy + dz * dz < r * r;
        };
        if (pikiMgr) {
            Iterator it(pikiMgr);
            CI_LOOP(it) {
                Piki* p = static_cast<Piki*>(*it);
                if (!p || !p->isAlive() || !p->mGroundTriangle || p->isStickTo() || !touching(p)) continue;
                if (!st.bfPressed[leg].insert(p).second) continue;
                p->stimulate(InteractPress(actor, damage));
                ++piki;
            }
        }
        for (Navi* n : pc_p2_navis()) {
            if (!n || !n->isAlive() || !n->mGroundTriangle || !touching(n)) continue;
            if (!st.bfPressed[leg].insert(n).second) continue;
            n->stimulate(InteractPress(actor, damage));
            ++navi;
        }
        if (tekiMgr) {
            Iterator it(tekiMgr);
            CI_LOOP(it) {
                Creature* t = static_cast<Creature*>(*it);
                if (!t || t == actor || !t->isAlive() || !t->mGroundTriangle || !touching(t)) continue;
                if (!st.bfPressed[leg].insert(t).second) continue;
                t->stimulate(InteractAttack(actor, nullptr, 500.0f, false));
                ++teki;
            }
        }
        if (piki || navi || teki) {
            st.bfStompPiki += piki;
            st.bfStompNavi += navi;
            st.bfStompTeki += teki;
            std::printf("P2_BIGFOOT_STOMP generator=%u leg=%d foot=%s state=%s enraged=%d piki=%d navi=%d teki=%d "
                        "damage=%.0f move_ratio=%.2f at=%.1f,%.1f,%.1f totals=%d/%d/%d\n",
                        st.generator, leg, P2BigFootFsm::kFootNode[leg], P2LongLegsFsm::stateName(st.bigfoot.state()),
                        int(st.bigfoot.enraged()), piki, navi, teki, damage, st.bigfoot.ik().leg(leg).moveRatio, c.x, c.y,
                        c.z, st.bfStompPiki, st.bfStompNavi, st.bfStompTeki);
        }
    }
}

// ---- TEST-ONLY evidence probe (PIKMIN_P2_LONGLEGS_PROBE=1) -----------------
// Headless runs have no player. The probe (1) walks the captain under the
// dormant boss so StateStay's own wake radius drops it in, (2) steps the
// captain back out, and (3) throws free Pikmin at the body through the REAL
// Navi::throwPiki + PikiFlyingState path every 0.5 s, so the real collision
// decides what latches, the stuck Pikmin do the damage and the real flick
// counter fills. It never touches the brain, health or any timer.
bool bigfootProbeEnabled() {
    static const bool on = [] {
        const char* e = std::getenv("PIKMIN_P2_LONGLEGS_PROBE");
        return e && *e && *e != '0';
    }();
    return on;
}

Piki* bigfootProbePiki() {
    if (!pikiMgr) return nullptr;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (!p || !p->isAlive() || p->isStickTo() || p->isBuried() || !p->isVisible() || !p->mGroundTriangle) continue;
        if (p->getState() == PIKISTATE_Flying) continue;
        return p;
    }
    return nullptr;
}

void bigfootProbe(BTeki* actor, ActorState& st, float dt) {
    if (!bigfootProbeEnabled()) return;
    static BTeki* owner = nullptr;
    if (!owner) owner = actor;
    if (owner != actor) return;
    st.probeTime += dt;
    Navi* navi = naviMgr ? naviMgr->getActiveNavi() : nullptr;
    if (!navi) return;
    const Vector3f ap = actor->getPosition();
    const P2LongLegsState s = st.bigfoot.state();
    if (st.probeStage == 0 && st.probeTime >= 1.0f) {
        // Walk the captain to 40 units from the dormant centre (private radius 70).
        const float cx = ap.x + 40.0f, cz = ap.z;
        navi->mSRT.t = Vector3f(cx, mapMgr ? mapMgr->getMinY(cx, cz, true) : ap.y, cz);
        st.probeStage = 1;
        std::printf("P2_BIGFOOT_PROBE kind=captain_wake generator=%u x=%.1f z=%.1f\n", st.generator, cx, cz);
    } else if (st.probeStage == 1 && s != P2LongLegsState::Stay && s != P2LongLegsState::Land) {
        // Landed: step the captain back out, 400 units "behind" the boss along
        // the camera's own forward axis so the whole body is in front of the lens.
        float fx = 0.0f, fz = 1.0f;
        if (Camera* cam = navi->controlCamera()) {
            fx = -cam->mLookAtMtx.mMtx[2][0];
            fz = -cam->mLookAtMtx.mMtx[2][2];
            const float len = std::sqrt(fx * fx + fz * fz);
            if (len > 1.0e-4f) { fx /= len; fz /= len; } else { fx = 0.0f; fz = 1.0f; }
        }
        const float cx = ap.x - fx * 400.0f, cz = ap.z - fz * 400.0f;
        navi->mSRT.t = Vector3f(cx, mapMgr ? mapMgr->getMinY(cx, cz, true) : ap.y, cz);
        navi->mFaceDirection = std::atan2(fx, fz);
        st.probeStage = 2;
        st.probeNext = st.probeTime + 1.0f;
        std::printf("P2_BIGFOOT_PROBE kind=captain_back generator=%u x=%.1f z=%.1f\n", st.generator, cx, cz);
    }
    if (st.probeStage < 2 || s == P2LongLegsState::Dead || st.probeTime < st.probeNext || st.probeThrows >= 400) return;
    Piki* p = bigfootProbePiki();
    const int tama = p2bigfootcoll::nodeIndex("tama");
    if (!p || tama < 0) return;
    const p2ik::V3 body = st.bigfoot.collCentre(tama);
    // A captain 150 units out from the body, on the ground there.
    const Vector3f np = navi->mSRT.t;
    float dx = np.x - body.x, dz = np.z - body.z;
    const float len = std::sqrt(dx * dx + dz * dz);
    if (len > 1.0e-3f) { dx /= len; dz /= len; } else { dx = 1.0f; dz = 0.0f; }
    const float lx = body.x + dx * 150.0f, lz = body.z + dz * 150.0f;
    const Vector3f launch(lx, mapMgr ? mapMgr->getMinY(lx, lz, true) : ap.y, lz);
    const Vector3f aim(body.x, body.y, body.z);
    const Vector3f saved = navi->mSRT.t;
    navi->mSRT.t = launch;
    p->mFSM->transit(p, PIKISTATE_Flying); // exactly as NaviThrowState key action 0
    navi->throwPiki(p, aim);
    navi->mSRT.t = saved;
    ++st.probeThrows;
    st.probeNext = st.probeTime + 0.5f;
    if (st.probeThrows <= 5 || st.probeThrows % 20 == 0)
        std::printf("P2_BIGFOOT_PROBE kind=throw generator=%u n=%d state=%s launch=%.1f,%.1f,%.1f body=%.1f,%.1f,%.1f\n",
                    st.generator, st.probeThrows, P2LongLegsFsm::stateName(s), launch.x, launch.y, launch.z, body.x,
                    body.y, body.z);
}

// One host frame for a registered BigFoot. Returns after the escape.
void bigfootTick(BTeki* actor, ActorState& state, float dt) {
    if (actor->mStoredDamage > 0.0f) actor->makeDamaged();
    // Hit counter (source addDamage flickSpeed 1.0 per accepted attack or bomb):
    // TEKIOPT_DamageCountable bumps mDamageCount in interactDefault.
    if (actor->mDamageCount < state.lastDamageCount) state.lastDamageCount = actor->mDamageCount;
    const int newHits = int(actor->mDamageCount - state.lastDamageCount);
    state.lastDamageCount = actor->mDamageCount;
    if (newHits > 0) state.pendingHits += newHits;
    if (actor->mHealth < state.lastHealth && actor->mHealth > 0.0f) {
        static int damageLogs = 0;
        if (++damageLogs <= 40 || damageLogs % 50 == 0)
            std::printf("P2_LONG_LEGS_DAMAGE species=BigFoot generator=%u health=%.2f prior=%.2f hits=%d state=%s "
                        "flick_timer=%.0f\n",
                        state.generator, actor->mHealth, state.lastHealth, newHits,
                        P2LongLegsFsm::stateName(state.bigfoot.state()), state.bigfoot.flickTimer());
    }
    state.lastHealth = actor->mHealth;
    if (actor->mHealth > 0.0f) state.lastPositiveHealth = actor->mHealth;
    if (state.deadEscapeDone) return;
    bigfootBuildColl(actor, state);
    bigfootProbe(actor, state, dt);

    state.srcAccum += dt;
    int steps = 0;
    while (state.srcAccum >= P2BigFootFsm::kDelta && steps < 4) {
        state.srcAccum -= P2BigFootFsm::kDelta;
        ++steps;
        const P2BigFootParms& parms = state.bigfoot.parms();
        const Vector3f pos = actor->getPosition();
        P2BigFootInput in;
        in.health = actor->mHealth;
        in.hits = state.pendingHits;
        state.pendingHits = 0;
        in.stuck = houdaiStuckCount(actor);
        in.wake = houdaiWake(actor, pos, parms.privateRadius);
        if (Creature* w = houdaiNearest(actor, pos, state.bigfoot.face(), parms.viewAngleDeg, parms.sightRadius, false)) {
            in.walkPikiFound = true;
            in.walkPiki = bv(w->getPosition());
        }
        for (float& r : in.roll) r = gsys ? gsys->getRand(1.0f) : 0.5f;
        in.ground = houdaiGround;

        const P2LongLegsState before = state.bigfoot.state();
        P2BigFootOutput out;
        state.bigfoot.update(in, out);
        const P2LongLegsState after = state.bigfoot.state();

        if (out.entered) {
            const p2ik::V3 c = state.bigfoot.position();
            if (before == P2LongLegsState::Walk && state.hasWalkTarget) {
                std::printf("P2_LONG_LEGS_WALK_END species=BigFoot generator=%u distance=%.1f seconds=%.2f "
                            "start=%.1f,%.1f end=%.1f,%.1f next=%s cycles=%d\n",
                            state.generator, state.walkDistance, state.walkSeconds, state.walkStart.x,
                            state.walkStart.z, c.x, c.z, P2LongLegsFsm::stateName(after), state.bigfoot.ik().cycles());
                state.hasWalkTarget = false;
            }
            std::printf("P2_LONG_LEGS_STATE species=BigFoot generator=%u from=%s state=%s x=%.1f z=%.1f health=%.1f "
                        "flick_timer=%.0f stuck=%d enraged=%d walk_max=%.2f wall_ms=%lld\n",
                        state.generator, P2LongLegsFsm::stateName(out.from), P2LongLegsFsm::stateName(after), c.x, c.z,
                        actor->mHealth, state.bigfoot.flickTimer(), in.stuck, int(state.bigfoot.enraged()),
                        state.bigfoot.walkTimeMax(), houdaiWallMs());
            if (after == P2LongLegsState::Walk) {
                state.walkStart = Vector3f(c.x, c.y, c.z);
                state.walkDistance = 0.0f;
                state.walkSeconds = 0.0f;
                state.hasWalkTarget = true;
                const p2ik::V3 t = state.bigfoot.target();
                std::printf("P2_LONG_LEGS_WALK species=BigFoot generator=%u from=%.1f,%.1f to=%.1f,%.1f duration=%.2f "
                            "enraged=%d piki_target=%d\n",
                            state.generator, c.x, c.z, t.x, t.z, out.chosenSeconds, int(out.enraged),
                            int(in.walkPikiFound));
            }
            if (after == P2LongLegsState::Dead)
                std::printf("P2_LONG_LEGS_DEAD species=BigFoot generator=%u health=%.2f prior_health=%.2f "
                            "stomps=%d/%d/%d accepted=%d refused=%d\n",
                            state.generator, actor->mHealth, state.lastPositiveHealth, state.bfStompPiki,
                            state.bfStompNavi, state.bfStompTeki, state.bfAccepted, state.bfRefused);
        }
        if (out.hidden != state.bfHidden) bigfootSetHidden(actor, state, out.hidden);
        if (out.landKey2)
            std::printf("P2_BIGFOOT_LAND generator=%u key=2 bitter_immune=0 feet=4\n", state.generator);
        if (out.flickStuck) {
            int stuck = 0;
            const int hit = houdaiFlickStuck(actor, out.flickChance, out.flickKnockback, out.flickDamage, stuck);
            ++state.flicks;
            std::printf("P2_LONG_LEGS_FLICK species=BigFoot generator=%u cause=flick stuck=%d hit=%d knockback=%.0f "
                        "damage=%.0f health=%.1f\n",
                        state.generator, stuck, hit, out.flickKnockback, out.flickDamage, actor->mHealth);
        }
        // Body: mPosition is the IK centre (Obj::updateIKSystem).
        const p2ik::V3 c = state.bigfoot.position();
        Vector3f next(c.x, c.y, c.z);
        const float mx = next.x - pos.x, mz = next.z - pos.z;
        const float step = std::sqrt(mx * mx + mz * mz);
        actor->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
        actor->resetPosition(next);
        actor->mVelocity.set(mx / P2BigFootFsm::kDelta, 0.0f, mz / P2BigFootFsm::kDelta);
        static_cast<Teki*>(actor)->setDirection(state.bigfoot.face());
        if (after == P2LongLegsState::Walk) {
            state.walkDistance += step;
            state.walkSeconds += P2BigFootFsm::kDelta;
        }
        bigfootStomp(actor, state, out);
        state.damageable = after != P2LongLegsState::Stay && after != P2LongLegsState::Dead;
        state.bitterImmune = out.bitterImmune;
        if (out.deadKey2) {
            // StateDead key 2: throwupItem + createItemAndEnemy (30 Mitites when
            // no treasure). Children are lane objects: logged, not spawned.
            std::printf("P2_LONG_LEGS_BIRTH species=BigFoot generator=%u count=30\n", state.generator);
        }
        if (out.deadEnd && !state.deadEscapeDone) {
            // StateDead END: kill. The port keeps the accepted 56/69 precedent: the
            // host teardown births the carriable corpse for the ordinary delivery.
            state.deadEscapeDone = true;
            bigfootRestoreColl(actor, state);
            std::printf("P2_LONG_LEGS_ESCAPE species=BigFoot generator=%u native=host_escape_now dead_clip_frames=%d\n",
                        state.generator, P2BigFootFsm::clipFrames(P2BigFootFsm::ClipDead));
            std::fflush(stdout);
            actor->pcEscapeNow();
            return;
        }
    }
    bigfootUpdateColl(actor, state);
    std::fflush(stdout);
}

// Private posable copy of the bank mesh for one BigFoot; the skin writes the
// clip body with the IK legs into it (the source joint callback's result).
Shape* bigfootSkinShape(BTeki* actor, ActorState& st) {
    if (!bigfootSkinReady || st.bfSkinFailed || !bigfootBank.ready()) return nullptr;
    if (!st.bfSkinShape) {
        const p2pose::Pose* base = bigfootBank.basePose();
        if (!base || !bigfootBank.owner()) { st.bfSkinFailed = true; return nullptr; }
        const int previousHeap = gsys->setHeap(SYSHEAP_App);
        st.bfSkinShape = p2pose::privateShape(bigfootBank.basePath().c_str(), *bigfootBank.owner(), *base);
        gsys->setHeap(previousHeap);
        if (!st.bfSkinShape) {
            st.bfSkinFailed = true;
            std::printf("P2_BIGFOOT_SKIN_DRAW generator=%u status=private_shape_failed pose=bank\n", st.generator);
            return nullptr;
        }
    }
    p2ik::M34 joints[P2BigFootFsm::kJoints];
    st.bigfoot.jointsModel(joints);
    static std::vector<p2ik::V3> pos, nrm;
    bigfootSkin.evaluate(joints, pos, nrm);
    static p2pose::Pose pose;
    pose.positions.resize(pos.size());
    pose.normals.resize(nrm.size());
    for (size_t i = 0; i < pos.size(); ++i) pose.positions[i] = p2pose::Vec{pos[i].x, pos[i].y, pos[i].z};
    for (size_t i = 0; i < nrm.size(); ++i) pose.normals[i] = p2pose::Vec{nrm[i].x, nrm[i].y, nrm[i].z};
    if (!p2pose::write(*st.bfSkinShape, pose)) {
        st.bfSkinFailed = true;
        return nullptr;
    }
    if (!st.bfSkinLogged) {
        st.bfSkinLogged = true;
        std::printf("P2_BIGFOOT_SKIN_DRAW generator=%u status=ready positions=%zu normals=%zu ik_legs=%d "
                    "private_geometry=1 gameplay_clock=P1\n",
                    st.generator, pos.size(), nrm.size(), int(st.bigfoot.ikActive()));
    }
    return st.bfSkinShape;
}

bool parseActors(const std::string& path, std::map<unsigned, std::string>& out) {
    std::ifstream in(path);
    if (!in) return false;  // absent config -> P1 fallback
    std::string header, species, word;
    int count = 0;
    if (!(in >> header >> count) || header.size() < 11
            || header.compare(0, 3, "P2_") != 0
            || header.compare(header.size() - 9, 9, "_ACTORS_1") != 0
            || count < 1 || count > 100) fail("invalid actor config");
    for (int i = 0; i < count; ++i) {
        unsigned long long generator = 0;
        if (!(in >> generator >> species) || generator > 0xffffffffULL
                || !findSpecies(species)
                || !out.emplace(unsigned(generator), species).second) fail("invalid actor row");
    }
    if (in >> word) fail("trailing actor config data");
    return true;
}

Shape* loadBind(const SpeciesDef& species) {
    std::vector<unsigned char> data;
    {
        std::ifstream file(std::string("assets/dataDir/courses/pikmin2room/") + species.mod,
                           std::ios::binary | std::ios::ate);
        if (!file) fail("missing bind mesh");
        const auto size = file.tellg();
        if (size <= 0 || size_t(size) > MeshBytes) fail("bind mesh exceeds per-species budget");
        bytesTotal += size_t(size);
        if (bytesTotal > TotalBytes) fail("bind mesh exceeds total budget");
        file.seekg(0);
        data.assign(size_t(size), 0);
        if (!file.read(reinterpret_cast<char*>(data.data()), size)) fail("unreadable bind mesh");
    }
    std::vector<unsigned char> resources;
    if (!p2animation::resources(data, resources)) fail("invalid bind resources");
    Shape* shape = gameflow.loadShape(
        (std::string("courses/pikmin2room/") + species.mod).c_str(), true);
    if (!shape) fail("bind mesh load failed");
    for (int i = 0; i < shape->mTexAttrCount; ++i)
        if (shape->mTexAttrList[i].mTexture) shape->mTexAttrList[i].mTexture->attach();
    return shape;
}

// Load the optional BigFoot pose bank through the compact p2posefamily loader.
// A missing config leaves the static bind draw; a config that does not load
// (missing/mismatched files, budget) is reported and also keeps the bind draw.
void bigfootBankSetup(size_t& total) {
    bigfootBank.reset();
    bigfootVis.clear();
    bigfootTiming.clear();
    bigfootShapes.clear();
    std::ifstream config("assets/dataDir/courses/pikmin2room/p2-long-legs-animation.txt");
    if (!config) {
        std::printf("P2_LONGLEGS_BANK status=absent pose=bind\n");
        return;
    }
    std::vector<p2longlegspose::ClipConfig> clips;
    if (!p2longlegspose::parse(config, clips)) {
        std::printf("P2_LONGLEGS_BANK status=invalid_config pose=bind\n");
        return;
    }
    p2poseload::Shared shared;
    size_t loaded = 0;
    for (const p2longlegspose::ClipConfig& clip : clips) {
        std::string error;
        std::vector<Shape*> poses;
        if (!p2posefamily::loadFamilyClip(bigfootBank, clip.name, "longlegs_BigFoot_" + clip.name, clip.count,
                                          clip.duration, clip.frames, shared, loaded, poses, error)) {
            std::printf("P2_LONGLEGS_BANK status=load_failed clip=%s reason=%s pose=bind\n", clip.name.c_str(),
                        error.c_str());
            bigfootBank.reset();
            bigfootTiming.clear();
            bigfootShapes.clear();
            return;
        }
        bigfootTiming[clip.name] = clip;
        bigfootShapes[clip.name] = poses;
    }
    total += loaded;
    std::printf("P2_LONGLEGS_BANK status=ready clips=%zu resident_bytes=%zu gameplay=P1_unchanged\n",
                bigfootTiming.size(), loaded);
    // #1018: the J3D skin of the same vertex order lets the draw pose the legs
    // from the source IK. It must reproduce the baked wait pose 0 from the
    // tables' wait frame 0; otherwise the pose-bank draw stays.
    bigfootSkinReady = false;
    bigfootSkinError = -1.0f;
    std::ifstream skinFile("assets/dataDir/courses/pikmin2room/longlegs_BigFoot_skin_00.txt", std::ios::binary);
    if (!skinFile) {
        std::printf("P2_BIGFOOT_SKIN status=absent draw=pose_bank\n");
        return;
    }
    const std::string text((std::istreambuf_iterator<char>(skinFile)), std::istreambuf_iterator<char>());
    std::string error;
    if (!bigfootSkin.parse(text, &error) || bigfootSkin.jointCount != P2BigFootFsm::kJoints) {
        std::printf("P2_BIGFOOT_SKIN status=invalid error=%s draw=pose_bank\n", error.c_str());
        return;
    }
    const p2posefamily::Clip* wait = bigfootBank.clip("wait");
    if (!wait || wait->poses.empty() || wait->frames.empty() || wait->frames.front() != 0) {
        std::printf("P2_BIGFOOT_SKIN status=no_wait_pose draw=pose_bank\n");
        return;
    }
    p2ik::M34 joints[P2BigFootFsm::kJoints];
    P2BigFootFsm::clipJoints(P2BigFootFsm::ClipWait, 0.0f, joints);
    std::vector<p2ik::V3> pos, nrm;
    bigfootSkin.evaluate(joints, pos, nrm);
    const p2pose::Pose& ref = wait->poses.front();
    if (pos.size() != ref.positions.size() || nrm.size() != ref.normals.size()) {
        std::printf("P2_BIGFOOT_SKIN status=count_mismatch skin=%zu/%zu bank=%zu/%zu draw=pose_bank\n", pos.size(),
                    nrm.size(), ref.positions.size(), ref.normals.size());
        return;
    }
    float worst = 0.0f;
    for (size_t i = 0; i < pos.size(); ++i)
        worst = std::fmax(worst, std::fabs(pos[i].x - ref.positions[i].x) + std::fabs(pos[i].y - ref.positions[i].y)
                                     + std::fabs(pos[i].z - ref.positions[i].z));
    bigfootSkinError = worst;
    bigfootSkinReady = worst < 0.5f;
    std::printf("P2_BIGFOOT_SKIN status=%s positions=%zu normals=%zu draws=%zu max_error=%.4f draw=%s\n",
                bigfootSkinReady ? "ready" : "mismatch", pos.size(), nrm.size(), bigfootSkin.draws.size(), worst,
                bigfootSkinReady ? "skin_ik" : "pose_bank");
}

// The shape to draw for a BigFoot this frame, or nullptr for the bind mesh.
Shape* bigfootPoseShape(BTeki* actor, const ActorState& state, bool corpse) {
    if (!bigfootBank.ready() || bigfootTiming.size() != 4) return nullptr;
    const auto dur = [](const char* name) { return bigfootTiming.at(name).duration; };
    p2longlegspose::Choice pick;
    if (state.isBigFoot) {
        // #1018 own brain: the clip and source frame the brain is playing.
        pick.clip = bigfootClipName(corpse ? P2BigFootFsm::ClipDead : state.bigfoot.clip());
        const int frames = dur(pick.clip);
        const int f = corpse ? frames - 1 : state.bigfoot.frame();
        pick.frame = float(f < 0 ? 0 : (f >= frames ? frames - 1 : f));
    } else {
        pick = p2longlegspose::choose(state.fsm.state(), state.animSeconds, state.deadSeconds, state.poseClock, corpse,
                                      dur("wait"), dur("landing"), dur("flick"), dur("dead"));
    }
    const unsigned token = state.generator;
    if (Shape* smooth = bigfootVis.draw(actor, bigfootBank, pick.clip, pick.frame, token)) return smooth;
    const auto poses = bigfootShapes.find(pick.clip);  // nearest pose (PIKMIN_P2_INTERPOLATION=0 / failure)
    if (poses == bigfootShapes.end() || poses->second.empty()) return nullptr;
    const p2longlegspose::ClipConfig& timing = bigfootTiming.at(pick.clip);
    const size_t index = size_t(p2longlegspose::nearestPose(timing.frames, pick.frame));
    return index < poses->second.size() ? poses->second[index] : poses->second.back();
}
}

void pc_p2_long_legs_reset() {
    bigfootBank.reset();
    bigfootVis.clear();
    bigfootTiming.clear();
    bigfootShapes.clear();
    bigfootSkinReady = false;
    for (auto& entry : actors)
        if (entry.second.isBigFoot) bigfootRestoreColl(entry.first, entry.second); // stage boundary / rebind
    for (HoudaiShell& shell : shells) {
        if (shell.stone) { shell.stone->notifyWallContact(); shell.stone->finishDeath(); }
    }
    actors.clear();
    corpses.clear();
    shapes.clear();
    shells.clear();
    houdaiShells.clear();
    bytesTotal = 0;
    logged[0] = logged[1] = false;
    houdaiSkinReady = false;
    houdaiRigReady = false;
    houdaiTrace.reset(mapMgr);
}

void pc_p2_long_legs_forget(BTeki* actor) {
    bigfootVis.forget(actor);
    {
        auto it = actors.find(actor);
        if (it != actors.end() && it->second.isBigFoot) bigfootRestoreColl(actor, it->second);
    }
    killShellsOf(actor);
    houdaiDropShells(actor, "forget");
    {
        auto known = actors.find(actor);
        if (known != actors.end() && known->second.isHoudai) {
            houdaiSightEnd(known->second, "forget");
            houdaiRestoreColl(actor, known->second);
        }
    }
    // Lane 06 single-use binding: drop the ordinary-delivery source so a
    // recycled actor address can never inherit it (mirrors Sokkuri/ElecBug).
    pc_randomizer_p2_forget_source(static_cast<PelletView*>(actor));
    actors.erase(actor);
    // The actor's corpse registration is keyed on its Pellet*, so a plain
    // actors.erase leaves it behind; clear it with the actor (review fix 3b).
    if (actor && actor->mPellet) corpses.erase(actor->mPellet);
}

static unsigned sourceForSpecies(const std::string& species) {
    if (species == "Damagumo") return 56;
    if (species == "BigFoot") return 69;
    return 66; // Houdai
}

void pc_p2_long_legs_setup() {
    pc_p2_long_legs_reset();
    if (!tekiMgr) return;
    const bool bridge = pc_randomizer_p2_bridge() && !pc_pikipelago_room_preview();
    const bool preview = pc_pikipelago_room_preview();
    if (!preview && !bridge) return;
    std::map<unsigned, std::string> wanted;
    if (!parseActors("p2-long-legs-actors.txt", wanted)) {
        if (bridge) {
            // No sidecar: fall through to the seed-bridge identity below.
        } else return;
    }
    if (bridge) {
        // Generated campaign sessions bind by the seed's source id per actor
        // (like Sokkuri/Kurage), not by the arena sidecar's generator ids.
        // The sidecar's filed generators are placeholders there.
        wanted.clear();
        for (unsigned id : pc_p2_campaign_ids(56)) wanted[id] = "Damagumo";
        for (unsigned id : pc_p2_campaign_ids(69)) wanted[id] = "BigFoot";
        for (unsigned id : pc_p2_campaign_ids(66)) wanted[id] = "Houdai";
        if (wanted.empty()) return;
    }

    std::set<unsigned> found;
    std::set<std::string> speciesUsed;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        Teki* teki = static_cast<Teki*>(*it);
        if (!teki || !teki->mGenerator) continue;
        const unsigned generator = bridge ? pc_p2_campaign_token(teki) : teki->mGenerator->_70;
        auto match = wanted.find(generator);
        if (match == wanted.end()) continue;
        if (bridge) {
            // Campaign vehicle for 66 is TEKI_Swallow (policy hostType 66->4);
            // the preview fixture uses TEKI_Chappy. Accept either in bridge
            // so the vehicle check cannot strand the boss as a host-driven
            // PROXY; fail closed only on a non-legged vehicle.
            if (teki->mTekiType != TEKI_Chappy && teki->mTekiType != TEKI_Swallow) {
                std::printf("P2_LONG_LEGS_ERROR native_type generator=%u\n", generator);
                std::fflush(stdout);
                if (pc_p2_setup_skip(true, "LongLegs", "actor_type_mismatch")) return;
                fail("native type mismatch");
            }
        } else if (teki->mTekiType != TEKI_Chappy) {
            fail("native type mismatch");
        }
        if (!found.insert(generator).second) {
            if (bridge) {
                if (pc_p2_setup_skip(true, "LongLegs", "duplicate_generator")) return;
            }
            fail("duplicate generator in scene");
        }
        ActorState& state = actors[teki];
        state.species = match->second;
        state.generator = generator;
        state.parms = p2LongLegsParmsFor(speciesEnum(match->second));
        state.fsm.reset(state.parms);
        state.homePos = teki->getPosition(); // source mHomePosition: spawn point
        state.homeRecorded = true;
        // Source health per identity (audit: Damagumo 1300 disc; BigFoot/Houdai
        // from the FSM parms retail). The host vehicle spawns with P1 health,
        // so take the source value here like Jigumo/Sokkuri do.
        const float hostHealth = teki->mHealth;
        teki->mHealth = state.parms.maxHealth > 0.0f ? state.parms.maxHealth : teki->mHealth;
        state.lastHealth = teki->mHealth;
        state.lastPositiveHealth = teki->mHealth;
        if (match->second == "Houdai") {
            // #173 own brain: source Houdai FSM (disc parms), hit counter via
            // TEKIOPT_DamageCountable (interactDefault bumps mDamageCount).
            state.isHoudai = true;
            state.houdai.reset(P2HoudaiParms(), P2HoudaiVec{state.homePos.x, state.homePos.y, state.homePos.z},
                               teki->getDirection());
            teki->setTekiOption(TEKIOPT_DamageCountable);
            state.lastDamageCount = teki->mDamageCount;
            state.drawHidden = true;
            houdaiSetIntangible(teki, state, true);
            std::printf("P2_HOUDAI_OWN_BIND generator=%u health=%.0f home=%.1f,%.1f,%.1f brain=P2HoudaiFsm "
                        "parms=disc private=%.0f territory=%.0f search_height=%.0f search_angle=%.0f\n",
                        generator, teki->mHealth, state.homePos.x, state.homePos.y, state.homePos.z,
                        state.houdai.parms().privateRadius, state.houdai.parms().territoryRadius,
                        state.houdai.parms().burstCooldown, state.houdai.parms().maxAimSeconds);
        }
        if (match->second == "BigFoot") {
            // #1018 own brain: source BigFoot FSM + IK (disc parms), hit counter
            // via TEKIOPT_DamageCountable, retail collision tree on first tick,
            // hidden until the drop-in (StateStay EB_ModelHidden).
            state.isBigFoot = true;
            P2BigFootParms bp;
            state.bigfoot.reset(bp, p2ik::V3(state.homePos.x, state.homePos.y, state.homePos.z), teki->getDirection());
            teki->mHealth = bp.maxHealth;
            state.lastHealth = teki->mHealth;
            state.lastPositiveHealth = teki->mHealth;
            state.bfHostLife = hostHealth;
            teki->setTekiOption(TEKIOPT_DamageCountable);
            state.lastDamageCount = teki->mDamageCount;
            bigfootSetHidden(teki, state, true);
            std::printf("P2_BIGFOOT_OWN_BIND generator=%u health=%.0f host_health=%.0f max_life=%.0f "
                        "home=%.1f,%.1f,%.1f brain=P2BigFootFsm parms=disc private=%.0f territory=%.0f sight=%.0f "
                        "flick_tiers=%d/%d,%d/%d,%d/%d,%d host_scale=%.3f draw_scale=%.3f\n",
                        generator, teki->mHealth, hostHealth, bp.maxHealth, state.homePos.x, state.homePos.y,
                        state.homePos.z, bp.privateRadius, bp.territoryRadius, bp.sightRadius, bp.shakeOffBlowA,
                        bp.shakeOffSticking1, bp.shakeOffBlowB, bp.shakeOffSticking2, bp.shakeOffBlowC,
                        bp.shakeOffSticking3, bp.shakeOffBlowD, teki->mSRT.s.y, bp.scale);
        }
        speciesUsed.insert(match->second);
        // Ordinary-delivery bridge (lane 06 contract): bind the source so
        // GoalItem::suckMe grants onion:p2:<id> exactly once through
        // pc_randomizer_p2_corpse_delivered. Single-use: consumed on delivery.
        if (bridge) {
            const unsigned source = sourceForSpecies(match->second);
            pc_randomizer_p2_bind_source(static_cast<PelletView*>(teki), source, generator);
            std::printf("P2_LONG_LEGS_DELIVERY_BIND generator=%u source_id=%u\n",
                        generator, source);
            std::fflush(stdout);
        }
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_LONG_LEGS_ERROR missing_actor wanted=%zu found=%zu\n",
                    wanted.size(), found.size());
        if (pc_p2_setup_skip(bridge, "LongLegs", "actor_roster_incomplete")) return;
        fail("arena actor not present in scene");
    }
    for (const std::string& species : speciesUsed) {
        if (shapes.count(species)) continue;
        const SpeciesDef* def = findSpecies(species);
        if (!def) {
            if (pc_p2_setup_skip(bridge, "LongLegs", "unknown_species")) return;
            fail("unknown species in actor config");
        }
        if (bridge) {
            std::ifstream probe(std::string("assets/dataDir/courses/pikmin2room/") + def->mod,
                                std::ios::binary);
            if (!probe) {
                std::printf("P2_SETUP_SKIP LongLegs clip_file_missing species=%s\n",
                            species.c_str());
                std::fflush(stdout);
                for (auto ait = actors.begin(); ait != actors.end();) {
                    if (ait->second.species == species) ait = actors.erase(ait);
                    else ++ait;
                }
                continue;
            }
        }
        shapes[species] = loadBind(*def);
        if (species == "Houdai") houdaiIkSetup(*def, shapes[species]);
        if (species == "BigFoot") bigfootBankSetup(bytesTotal);
    }
    for (const auto& entry : actors)
        std::printf("P2_LONG_LEGS_BIND generator=%u species=%s pose=bind visual_only=0 "
                    "native_fsm=implemented\n",
                    entry.second.generator,
                    entry.second.species.c_str());
    std::printf("P2_LONG_LEGS_BANK total_mod_bytes=%zu species=%zu pose_bank=0\n",
                bytesTotal, shapes.size());
}

// Per-frame source-FSM tick. Called from BTeki::update() (tekibteki.cpp) so the
// schedule runs for every registered actor regardless of camera visibility; the
// previous draw-tick only advanced on-camera actors.
void pc_p2_long_legs_update(BTeki* actor) {
    auto entry = actors.find(actor);
    if (entry == actors.end()) return;
    ActorState& state = entry->second;
    // OWN damage path (mirrors frog): the P1 TAI damaging reaction is
    // suppressed with doAI, so the source FSM applies pending attack damage
    // itself. Bitter-immune Stay/Land attacks never reach storage: the shared
    // tekiinteraction hook rejects them before interactDefault stores damage.
    if (actor->mStoredDamage > 0.0f) actor->makeDamaged();
    // Once the host teardown runs, capture the corpse Pellet* the engine created
    // (PelletView::mPellet) so the ordinary Pod receipt can resolve a view-less
    // stand-in corpse (mirrors lane 31). Runs each tick until the corpse is
    // delivered (the receipt consumes it one-shot) or swept as dead, and is also
    // cleared by forget (per-actor) and reset (whole registry).
    if (!actor->isAlive() && actor->mPellet && !corpses.count(actor->mPellet)) {
        corpses[actor->mPellet] = state.generator;
        std::printf("P2_LONG_LEGS_CORPSE_REGISTER generator=%u species=%s\n",
                    state.generator, state.species.c_str());
        std::fflush(stdout);
    }
    const float dt = gsys ? gsys->getFrameTime() : 0.0f;
    if (!(dt > 0.0f && dt < 0.5f)) return;
    state.poseClock += dt;  // presentation clock only; never read by gameplay
    if (state.isHoudai) {
        houdaiTick(actor, state, dt);
        return;
    }
    if (state.isBigFoot) {
        bigfootTick(actor, state, dt);
        return;
    }

    // OWN death (mirrors frog/kochappy): doAI is suppressed, so dieSoon() never
    // runs there. The P2 Dead state finalizes the host teardown itself via
    // pcEscapeNow() (= die() + dieSoon(), teki.h) after a 1 s dead beat, which
    // births the real carriable Chappy-pellet corpse the receipt then resolves.
    // The bind-pose family ships no dead clip, so the beat is wall-clock.
    if (state.fsm.state() == P2LongLegsState::Dead) {
        stopActor(actor);
        state.deadSeconds += dt;
        if (!state.deadEscapeDone && state.deadSeconds >= 1.0f) {
            state.deadEscapeDone = true;
            std::printf("P2_LONG_LEGS_ESCAPE species=%s generator=%u native=host_escape_now\n",
                        state.species.c_str(), state.generator);
            std::fflush(stdout);
            actor->pcEscapeNow();
        }
        return;
    }

    const Vector3f pos = actor->getPosition();
    const P2LongLegsSpecies species = speciesEnum(state.species);

    // P2 kill signal is the drained health itself: with doAI suppressed the
    // host never sets mDeadState, so isAlive() stays true at 0 HP. One
    // terminal tick lets the policy emit its source death output: the held
    // treasure drop, or the no-treasure child burst. The dropped treasure and
    // children are lane 06/14/15/20 objects, so the intents are logged, not
    // spawned here. The escape above finalizes on the following ticks.
    if (actor->mHealth <= 0.0f || !actor->isAlive()) {
        killShellsOf(actor);  // free the actor's in-flight shells on death
        P2LongLegsFsmInput kill;
        kill.health = actor->mHealth;
        kill.killed = true;
        P2LongLegsFsmOutput dead;
        state.fsm.update(kill, dead);
        // prior_health distinguishes a naturally-fought death (small, drained
        // to zero by incremental combat damage) from a fixture-injected large
        // jump to zero. Reported from the last still-positive health, since the
        // engine death tick already sees health == 0.
        std::printf("P2_LONG_LEGS_DEAD species=%s generator=%u health=0 prior_health=%.2f\n",
                    state.species.c_str(), state.generator, state.lastPositiveHealth);
        if (dead.dropTreasure)
            std::printf("P2_LONG_LEGS_DROP species=%s generator=%u\n",
                        state.species.c_str(), state.generator);
        if (dead.birthChildren > 0)
            std::printf("P2_LONG_LEGS_BIRTH species=%s generator=%u count=%d\n",
                        state.species.c_str(), state.generator, dead.birthChildren);
        std::printf("P2_LONG_LEGS_STATE species=%s generator=%u state=%s\n",
                    state.species.c_str(), state.generator,
                    P2LongLegsFsm::stateName(state.fsm.state()));
        std::fflush(stdout);
        state.deadSeconds = 0.0f;
        state.damageable = false;
        state.bitterImmune = false;
        stopActor(actor);
        return;
    }

    const float land = landingSeconds(species);
    const float flick = flickSeconds(species);
    const float shot = shotSeconds(species);
    const P2LongLegsState before = state.fsm.state();

    P2LongLegsFsmInput in;
    in.health = actor->mHealth;
    // Round-2 crush gate (review: "Walk crush stays closed"): the source foot
    // presses while descending/planting with a move ratio above 1
    // (IKSystemMgr::isCollisionCheck). The port has no leg joints, but it DOES
    // own body translation in Walk, so a Walk tick with a live target implies
    // the planting stride: synthesize footDescendingOrPlanting=true and a 1.5
    // stride ratio while in Walk. Landing key 2 still fires all four feet via
    // the FSM Land path. Houdai never presses (pressDamage 0 gates in policy).
    in.footDescendingOrPlanting = (before == P2LongLegsState::Walk);
    in.ikMoveRatio = (before == P2LongLegsState::Walk) ? 1.5f : state.lastMoveRatio;
    // A health decrease this tick is the source damage edge; it postpones the
    // Houdai gun by resetting the shot cooldown (Houdai.cpp).
    if (actor->mHealth > 0.0f && actor->mHealth < state.lastHealth) {
        // Natural combat observability: an incremental, still-positive health
        // decrease is live Pikmin attack damage, distinguishable from a single
        // fixture-injected jump to zero (which shows up only in P2_LONG_LEGS_DEAD).
        std::printf("P2_LONG_LEGS_DAMAGE species=%s generator=%u health=%.2f prior=%.2f\n",
                    state.species.c_str(), state.generator, actor->mHealth, state.lastHealth);
        std::fflush(stdout);
    }
    in.damageTaken = actor->mHealth < state.lastHealth;
    state.lastHealth = actor->mHealth;
    if (actor->mHealth > 0.0f) state.lastPositiveHealth = actor->mHealth;
    in.roll = gsys->getRand(1.0f);
    in.wakeTargetNearby = nearestTarget(pos, state.parms.privateRadius) != nullptr;
    in.pikminAccumulating = countPikiWithin(pos, AccumulateRadius) > 0;
    in.landingKey2 = before == P2LongLegsState::Land && !state.key2Fired
        && state.animSeconds >= land * 0.5f;
    in.flickKey2 = before == P2LongLegsState::Flick && !state.key2Fired
        && state.animSeconds >= flick * 0.5f;
    in.animEnd = (before == P2LongLegsState::Land && state.animSeconds >= land)
        || (before == P2LongLegsState::Flick && state.animSeconds >= flick)
        || (before == P2LongLegsState::Shot && shot > 0.0f && state.animSeconds >= shot);
    // Man-at-Legs attack loop: one shell every ~5 source frames while the burst
    // is on, bounded by the lane-20 in-flight pool occupancy.
    if (before == P2LongLegsState::Shot) {
        state.shotLoopAccum += dt;
        in.shotLoop = state.shotLoopAccum >= kShellLoopPeriod;
        if (in.shotLoop) state.shotLoopAccum = 0.0f;
    } else {
        state.shotLoopAccum = 0.0f;
    }
    in.shellsInFlight = countShellsOf(actor);
    if (in.landingKey2 || in.flickKey2) state.key2Fired = true;

    P2LongLegsFsmOutput out;
    state.fsm.update(in, out);
    const P2LongLegsState after = state.fsm.state();
    // Source StateWalk (HoudaiState.cpp:340-375, BigFoot/Damagumo equivalents):
    // startIKMotion toward getTargetPosition for mStateDuration, with no walk
    // animation (family-wide). The port has no IKSystemMgr and no leg joints, so
    // the source target rule + species speed drive BODY translation here while
    // the legs stay bind-pose (documented approximation). Translation runs only
    // in FSM Walk; every other state leaves the actor where it stands.
    if (after == P2LongLegsState::Walk && before != P2LongLegsState::Walk) {
        if (!state.homeRecorded) { state.homePos = pos; state.homeRecorded = true; }
        state.walkTarget = pickWalkTarget(pos, state.homePos, state.parms);
        state.walkStart = pos;
        state.walkDistance = 0.0f;
        state.walkSeconds = 0.0f;
        state.hasWalkTarget = true;
        std::printf("P2_LONG_LEGS_WALK species=%s generator=%u from=%.1f,%.1f to=%.1f,%.1f speed=%.1f\n",
                    state.species.c_str(), state.generator, pos.x, pos.z,
                    state.walkTarget.x, state.walkTarget.z, state.parms.speed);
        std::fflush(stdout);
    }
    if (after == P2LongLegsState::Walk && state.hasWalkTarget) {
        const float dx = state.walkTarget.x - pos.x, dz = state.walkTarget.z - pos.z;
        const float dist = std::sqrt(dx * dx + dz * dz);
        const float maxStep = state.parms.speed * dt;
        const float step = dist < maxStep ? dist : maxStep;
        state.lastMoveRatio = maxStep > 1.0e-6f ? step / maxStep : 1.0f;
        state.walkSeconds += dt;
        if (step > 1.0e-6f && dist > 1.0e-6f) {
            const Vector3f next(pos.x + dx / dist * step, pos.y, pos.z + dz / dist * step);
            actor->resetPosition(next);
            // Registered actors are TEKI_Chappy placement vehicles (setup fails
            // otherwise), so the Teki facing control is available.
            static_cast<Teki*>(actor)->setDirection(std::atan2(dx, dz));
            state.walkDistance += step;
            // Last-word drive (inst3-misc OWN): P2 FSM decides movement each
            // tick; host Swallow/Chappy TAI is suppressed (doAI) and blinded
            // (param_f), and this overwrite is the movement verdict.
            const float heading = std::atan2(dx, dz);
            const Vector3f drive(std::sin(heading) * state.parms.speed, 0.0f,
                                 std::cos(heading) * state.parms.speed);
            actor->inputDrive(drive);
            actor->mVelocity.set(drive);
        } else {
            actor->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
            actor->mVelocity.x = 0.0f;
            actor->mVelocity.z = 0.0f;
        }
    } else {
        // Non-Walk states: P2 holds the actor (last-word zero drive).
        actor->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
        actor->mVelocity.x = 0.0f;
        actor->mVelocity.z = 0.0f;
        state.lastMoveRatio = 1.0f;
        stopActor(actor);
        if (before == P2LongLegsState::Walk && state.hasWalkTarget) {
            std::printf("P2_LONG_LEGS_WALK_END species=%s generator=%u distance=%.1f seconds=%.2f start=%.1f,%.1f end=%.1f,%.1f\n",
                        state.species.c_str(), state.generator,
                        state.walkDistance, state.walkSeconds,
                        state.walkStart.x, state.walkStart.z, pos.x, pos.z);
            std::fflush(stdout);
            state.hasWalkTarget = false;
        }
    }
    if (state.fsm.state() != before) {
        state.animSeconds = 0.0f;
        state.key2Fired = false;
        state.lastState = state.fsm.state();
    } else {
        state.animSeconds += dt;
    }
    state.damageable = out.damageable;
    state.bitterImmune = out.bitterImmune;
    if (out.footCrush) {
        std::printf("P2_LONG_LEGS_FOOT species=%s generator=%u\n", state.species.c_str(),
                    state.generator);
        std::fflush(stdout);
        applyFootCrush(actor, pos, state.species, state.generator,
                       state.parms.pressDamage, 60.0f);
    }
    // Round-2 Flick shake (review: Flick key-2 shake never applied): the FSM
    // emits shake on the flick key-2 edge; resolve it here as the source
    // shake-off of accumulated/stuck Pikmin.
    if (out.shake) {
        applyFlickShake(actor, pos, state.species, state.generator);
    }
    if (out.fireShell) {
        std::printf("P2_LONG_LEGS_SHELL species=%s generator=%u\n", state.species.c_str(),
                    state.generator);
        std::fflush(stdout);
        if (state.species == "Houdai") fireHoudaiShell(actor, pos);
    }
    if (state.species == "Houdai") stepHoudaiShells(actor, state.species, state.generator);
    if (!state.stateLogged || out.entered) {
        state.stateLogged = true;
        std::printf("P2_LONG_LEGS_STATE species=%s generator=%u state=%s\n",
                    state.species.c_str(), state.generator,
                    P2LongLegsFsm::stateName(state.fsm.state()));
        std::fflush(stdout);
    }
}

bool pc_p2_long_legs_draw(BTeki* actor, Graphics& gfx, const Matrix4f& matrix, bool corpse) {
    auto entry = actors.find(actor);
    if (entry == actors.end() || !gfx.mCamera) return false;
    ActorState& state = entry->second;
    auto shapeIt = shapes.find(state.species);
    if (shapeIt == shapes.end() || !shapeIt->second) return false;
    Shape* shape = shapeIt->second;

    if (!logged[corpse ? 1 : 0]) {
        std::printf("P2_LONG_LEGS_DRAW corpse=%d species=%s pose=bind generator=%u\n",
                    int(corpse), state.species.c_str(), state.generator);
        std::printf("P2_%s_DRAW corpse=%d species=%s generator=%u\n",
                    state.species == "Damagumo" ? "DAMAGUMO"
                    : state.species == "BigFoot" ? "BIGFOOT" : "HOUDAI",
                    int(corpse), state.species.c_str(), state.generator);
        logged[corpse ? 1 : 0] = true;
    }
    if (state.isHoudai && houdaiRigReady && state.ikShape) {
        // Sampled rig (#1012): the landing clip raises the dormant crouch into the standing body, wait/flick/
        // attack/dead play from the bank, the gun turns to its aim, the legs take the IK. A carried corpse
        // shows the dead clip's last visible pose.
        if (houdaiIkPose(actor, state, corpse)) {
            state.ikShape->updateAnim(gfx, matrix, nullptr, actor);
            state.ikShape->drawshape(gfx, *gfx.mCamera, nullptr);
            if (!corpse) houdaiDrawSight(gfx, state);
            return true;
        }
    }
    if (state.isHoudai && !corpse && !houdaiRigReady) {
        // Legacy bind-pose draw (no rig sidecar staged). Source Stay keeps the dormant boss out of view
        // until Land drops it in; without clip playback Land lowers the bind mesh from kHoudaiDropHeight to
        // the ground by landing key 4 (frame 100).
        if (state.drawHidden) return true;
        if (state.landDrop > 0.0f) {
            constexpr float kHoudaiDropHeight = 300.0f;
            Matrix4f dropped = matrix;
            const float dy = state.landDrop * kHoudaiDropHeight;
            for (int r = 0; r < 3; ++r) dropped.mMtx[r][3] += dropped.mMtx[r][1] * dy;
            shape->updateAnim(gfx, dropped, nullptr, actor);
            shape->drawshape(gfx, *gfx.mCamera, nullptr);
            return true;
        }
        if (houdaiIkPose(actor, state, false)) {
            state.ikShape->updateAnim(gfx, matrix, nullptr, actor);
            state.ikShape->drawshape(gfx, *gfx.mCamera, nullptr);
            return true;
        }
    }
    if (state.isBigFoot) {
        // #1018: hidden until the drop-in; the live body is drawn where the
        // brain puts it (T(trace) * RotY(face) * S(P2 scale 1), the source base
        // matrix), with the legs from the source IK once it has landed.
        if (!corpse && state.bfHidden) return true;
        Matrix4f onCam = matrix;
        if (!corpse) {
            const p2ik::M34 body = state.bigfoot.bodyMatrix();
            Matrix4f world;
            world.makeIdentity();
            for (int r = 0; r < 3; ++r)
                for (int c = 0; c < 4; ++c) world.mMtx[r][c] = body.m[r][c];
            gfx.mCamera->mLookAtMtx.multiplyTo(world, onCam);
            const P2LongLegsState s = state.bigfoot.state();
            if (s == P2LongLegsState::Wait || s == P2LongLegsState::Flick || s == P2LongLegsState::Walk) {
                if (Shape* skinned = bigfootSkinShape(actor, state)) {
                    skinned->updateAnim(gfx, onCam, nullptr, actor);
                    skinned->drawshape(gfx, *gfx.mCamera, nullptr);
                    return true;
                }
            }
        }
        if (Shape* posed = bigfootPoseShape(actor, state, corpse)) shape = posed;
        shape->updateAnim(gfx, onCam, nullptr, actor);
        shape->drawshape(gfx, *gfx.mCamera, nullptr);
        return true;
    }
    if (state.species == "BigFoot")
        if (Shape* posed = bigfootPoseShape(actor, state, corpse)) shape = posed;
    shape->updateAnim(gfx, matrix, nullptr, actor);
    shape->drawshape(gfx, *gfx.mCamera, nullptr);
    return true;
}

// Fixture observability (#397): behavior-neutral read-only accessors so the
// lifecycle fixture can prove pc_p2_long_legs_forget() clears a registration.
unsigned long pc_p2_long_legs_count() {
    return (unsigned long)actors.size();
}

bool pc_p2_long_legs_registered(BTeki* actor) {
    return actors.count(actor) != 0;
}

bool pc_p2_long_legs_suppress_ai(const BTeki* actor) {
    if (!actor) return false;
    return actors.count(const_cast<BTeki*>(actor)) != 0;
}

float pc_p2_long_legs_param_f(const BTeki* actor, int idx, float fallback) {
    if (!actor || !actors.count(const_cast<BTeki*>(actor))) return fallback;
    // Catfish pattern: blind the P1 host strategy so it cannot acquire or
    // attack while the P2 FSM drives. Life stays host-owned (damage funnel).
    switch (idx) {
    case TPF_VisibleRange:
    case TPF_VisibleAngle:
    case TPF_AttackableRange:
    case TPF_AttackableAngle:
    case TPF_AttackRange:
    case TPF_AttackHitRange:
    case TPF_AttackPower:
    case TPF_DangerTerritoryRange:
    case TPF_SafetyTerritoryRange:
        return 0.0f;
    case TPF_LifeRecoverRate:
        return 0.0f;
    case TPF_Life: {
        // #173/#1018: BTeki::update clamps mHealth to getMaxLife() every frame,
        // so the host vehicle life (Chappy 130, Swallow 1100) silently capped
        // the source value set at bind. Every Long Legs reports its disc max
        // life: Houdai 2800 (own brain), BigFoot 10000 (own brain, fp00),
        // Damagumo 1300 (P2LongLegsFsmParms). This is native PR #7's fix,
        // which was merged into claude/p2-port-66-houdai and never reached main.
        const ActorState& st = actors.find(const_cast<BTeki*>(actor))->second;
        const float srcMax = st.isHoudai ? st.houdai.parms().maxHealth
            : st.isBigFoot ? st.bigfoot.parms().maxHealth : st.parms.maxHealth;
        return srcMax > 0.0f ? srcMax : fallback;
    }
    case TPF_BombDamageRate: {
        // EnemyBase::bombCallBack (enemyBase.cpp:2908-2912) adds the bomb's
        // damage unscaled; BigFoot does not override it.
        const ActorState& st = actors.find(const_cast<BTeki*>(actor))->second;
        return st.isBigFoot ? 1.0f : fallback;
    }
    default:
        return fallback;
    }
}

bool pc_p2_long_legs_damageable(const BTeki* actor) {
    auto entry = actors.find(const_cast<BTeki*>(actor));
    if (entry == actors.end()) return false;
    return entry->second.damageable;
}

const char* pc_p2_long_legs_state_name(const BTeki* actor) {
    auto entry = actors.find(const_cast<BTeki*>(actor));
    if (entry == actors.end()) return "unregistered";
    if (entry->second.isBigFoot) return P2LongLegsFsm::stateName(entry->second.bigfoot.state());
    if (entry->second.isHoudai) return P2LongLegsFsm::stateName(entry->second.houdai.state());
    return P2LongLegsFsm::stateName(entry->second.fsm.state());
}

bool pc_p2_long_legs_receiver_rejects(Teki* teki, const InteractAttack* /*attack*/) {
    // Source damageCallBack + EB_BitterImmune: a registered Long Legs rejects
    // every attack while it is still bitter-immune (Stay or Land). Once damageable
    // (Wait/Flick/Walk/Shot) the P1 proxy accepts ordinary Pikmin attack damage.
    // Unregistered actors are never rejected, keeping the shared hook a no-op.
    if (!actors.count(teki)) return false;
    if (actors[teki].isHoudai) return false; // Houdai: pc_p2_long_legs_damage_rate
    if (actors[teki].isBigFoot) return false; // BigFoot: pc_p2_long_legs_damage_rate / _bomb_rate
    return !actors[teki].damageable;
}

float pc_p2_long_legs_damage_rate(Teki* teki, Creature* attacker) {
    // Source Houdai::damageCallBack (Houdai.cpp:223-236, US build): only a
    // Pikmin stuck to the boss damages it through this path (captain punches
    // and loose Pikmin do nothing); Land takes 0.25x. Bombs do not come here:
    // they use EnemyBase::bombCallBack (full damage, any state, #1012). A stuck hit while dormant wakes Stay into
    // Land (StateStay::exec EB_TakingDamage) but is refused here.
    auto it = actors.find(teki);
    if (it != actors.end() && it->second.isBigFoot) {
        // #1018 Raging Long Legs, BigFoot::damageCallBack (BigFoot.cpp:202-214,
        // US): only a Pikmin stuck to the boss, through the part it is stuck to.
        // The retail tree makes that the body sphere `tama` (plus the retail
        // `st__` lht1 thigh tube); feet and legs are touch-only, so a thrown
        // Pikmin bounces off them, and the captain punch and P1's partless
        // ground melee take nothing (P2 has no such hit).
        ActorState& st = it->second;
        const bool fromPiki = attacker && attacker->isPiki();
        const bool stuck = fromPiki && attacker->getStickObject() == static_cast<Creature*>(teki);
        const int node = stuck ? bigfootNodeOf(st, attacker->getStickPart()) : -1;
        const float rate = p2bigfootcoll::attackRate(fromPiki, stuck, node);
        int& counter = rate > 0.0f ? st.bfAccepted : st.bfRefused;
        ++counter;
        if (counter <= 12 || counter % 100 == 0)
            std::printf("P2_BIGFOOT_HURTBOX generator=%u verdict=%s attacker=%s stuck=%d part=%s health=%.1f "
                        "accepted=%d refused=%d state=%s\n",
                        st.generator, rate > 0.0f ? "accept" : "refuse",
                        fromPiki ? "piki" : (attacker && attacker->mObjType == OBJTYPE_Navi ? "navi" : "other"),
                        int(stuck), node >= 0 ? p2bigfoot::kColl[node].id : "none", teki->mHealth, st.bfAccepted,
                        st.bfRefused, P2LongLegsFsm::stateName(st.bigfoot.state()));
        return rate;
    }
    if (it == actors.end() || !it->second.isHoudai) return -1.0f;
    ActorState& st = it->second;
    const bool stuckPiki = attacker && attacker->isPiki() && attacker->getStickObject() == teki;
    const P2LongLegsState s = st.houdai.state();
    // The part the Pikmin is stuck to (retail tree swapped in): only `tama` (st__) is stickable, so a
    // latch anywhere else cannot damage (defence in depth; the engine already refuses the latch).
    int node = -1;
    if (stuckPiki && st.collOwn) {
        CollPart* stuckPart = attacker->getStickPart();
        for (size_t i = 0; i < st.collParts.size(); ++i)
            if (st.collParts[i] == stuckPart) node = int(i);
    }
    const bool partOk = !st.collOwn || node < 0 || houdaiRig.coll()[size_t(node)].stickable();
    float rate = 0.0f;
    if (stuckPiki && partOk) {
        // US damageCallBack applies the hit in Stay too; StateStay::exec then
        // sees EB_TakingDamage and transits to Land.
        rate = P2HoudaiFsm::damageRateFor(s);
        if (s == P2LongLegsState::Stay) st.damageAttempt = true;
    }
    if (rate > 0.0f) ++st.receiverAccepted;
    else ++st.receiverRejected;
    const int total = st.receiverAccepted + st.receiverRejected;
    if (total == 1 || total % 200 == 0) {
        std::printf("P2_HOUDAI_RECEIVER generator=%u accepted=%d rejected=%d last_rate=%.2f stuck_piki=%d state=%s "
                    "part=%s\n",
                    st.generator, st.receiverAccepted, st.receiverRejected, rate, int(stuckPiki),
                    P2LongLegsFsm::stateName(s), node >= 0 ? houdaiRig.coll()[size_t(node)].id.c_str() : "none");
        std::fflush(stdout);
    }
    return rate;
}

float pc_p2_long_legs_bomb_rate(Teki* teki) {
    // #1018: InteractBomb -> EnemyBase::bombCallBack for a registered BigFoot
    // (full damage, BigFoot.h has no override). -1 leaves every other actor on
    // its existing bomb rule.
    auto it = actors.find(teki);
    // #1012: Man-at-Legs also takes the base bombCallBack (Houdai.h overrides only damageCallBack): full
    // damage in every state, so no refusal rule applies to it.
    if (it != actors.end() && it->second.isHoudai) return 1.0f;
    if (it == actors.end() || !it->second.isBigFoot) return -1.0f;
    ActorState& st = it->second;
    ++st.bfBombs;
    std::printf("P2_BIGFOOT_BOMB generator=%u rate=%.1f health=%.1f bombs=%d state=%s\n", st.generator,
                p2bigfootcoll::bombRate(), teki->mHealth, st.bfBombs, P2LongLegsFsm::stateName(st.bigfoot.state()));
    return p2bigfootcoll::bombRate();
}

void pc_p2_long_legs_piki_contact(BTeki* teki, Piki* piki, CollPart* part, const char* site) {
    // #1018 observer: where a thrown/jumping Pikmin touched the retail tree and
    // whether it latched (the engine's CollPart::isStickable decides).
    auto it = actors.find(teki);
    if (it == actors.end() || !it->second.isBigFoot || !piki) return;
    ActorState& st = it->second;
    const int node = bigfootNodeOf(st, part);
    if (node < 0) return;
    const bool fromStick = !std::strcmp(site, "stick");
    const bool latch = part->isStickable();
    if (latch != fromStick) return; // latches are reported once, from Creature::startStick
    int& counter = latch ? st.bfLatched : st.bfBounced;
    ++counter;
    if (counter <= 20 || counter % 50 == 0)
        std::printf("P2_BIGFOOT_CONTACT generator=%u site=%s part=%s latch=%d body=%d policy_stickable=%d "
                    "latched=%d bounced=%d state=%s\n",
                    st.generator, site, p2bigfoot::kColl[node].id, int(latch), int(p2bigfootcoll::body(node)),
                    int(p2bigfootcoll::stickable(node)), st.bfLatched, st.bfBounced,
                    P2LongLegsFsm::stateName(st.bigfoot.state()));
}

bool pc_p2_long_legs_cull_bounds(BTeki* actor, float centre[3], float* radius) {
    // #1018: P2 culls BigFoot by its LOD radius (enemyparm fp32 225) around the
    // body, not by the small P1 host sphere at the feet.
    auto it = actors.find(actor);
    if (it == actors.end() || !it->second.isBigFoot) return false;
    const p2ik::V3 t = it->second.bigfoot.trace();
    centre[0] = t.x;
    centre[1] = t.y + 100.0f; // root sphere offset (enemycoll `none` -100 under kosi ~180)
    centre[2] = t.z;
    *radius = 225.0f;
    return true;
}

bool pc_p2_long_legs_receipt(Pellet* pellet, unsigned& generator) {
    // Ordinary corpse receipt (mirrors lane 31's pc_p2_waterwraith_receipt and
    // kurage/otakara). Primary key is the corpse Pellet* captured at death, which
    // resolves even a view-less stand-in corpse; the PelletView backlink is a
    // fallback for a live-binding corpse. Returns false for any unowned pellet.
    // One-shot: the resolved registration is consumed so MonoObjectMgr slot reuse
    // cannot re-credit a future unrelated pellet at the same address (lane 31).
    if (!pellet) return false;
    auto corpse = corpses.find(pellet);
    if (corpse != corpses.end()) {
        generator = corpse->second;
        corpses.erase(corpse);
        return true;
    }
    PelletView* view = pellet->mPelletView;
    if (!view) return false;
    auto it = actors.find(static_cast<BTeki*>(view));
    if (it == actors.end()) return false;
    generator = it->second.generator;
    return true;
}

bool pc_p2_long_legs_shot(const BTeki* actor) {
    auto it = actors.find(const_cast<BTeki*>(actor));
    return it != actors.end() && it->second.fsm.state() == P2LongLegsState::Shot;
}

void pc_p2_long_legs_update_all() {
    // Sweeping is done from the guarded per-actor tick (pc_p2_long_legs_update),
    // not here: an unconditional per-frame sweep stalled the stage-2 FSM.
    if (actors.empty()) return;
    // Tick in generator-token order, not pointer order (std::map<BTeki*> sorts
    // by address, which differs between netplay peers and would reorder the
    // per-actor gsys->getRand draws). Snapshot first: a tick can reach the
    // host teardown, and forget() erases from `actors`.
    std::vector<std::pair<unsigned, BTeki*>> order;
    order.reserve(actors.size());
    for (const auto& entry : actors) order.emplace_back(entry.second.generator, entry.first);
    std::sort(order.begin(), order.end(),
              [](const std::pair<unsigned, BTeki*>& x, const std::pair<unsigned, BTeki*>& y) {
                  return x.first < y.first;
              });
    for (const auto& entry : order)
        if (actors.count(entry.second)) pc_p2_long_legs_update(entry.second);
}

unsigned long pc_p2_long_legs_corpse_count() {
    // Fixture observability (review fix 3b): sweeps dead/undelivered corpses and
    // reports the surviving registrations, so a non-one-shot receipt is visible.
    sweepCorpses();
    return static_cast<unsigned long>(corpses.size());
}
