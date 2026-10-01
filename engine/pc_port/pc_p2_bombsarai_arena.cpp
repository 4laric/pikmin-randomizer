#include "pc_p2_bombsarai_arena.h"

#include "pc_p2_bombsarai_joint.h"

#include "Camera.h"
#include "Graphics.h"

#include <cmath>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

namespace {
constexpr float kPi = 3.14159265358979323846f;
constexpr float kCoordinateLimit = 100000.0f;
constexpr float kParameterLimit = 10000.0f;
constexpr int kMaxReceivers = 8;
constexpr int kMaxEvents = 16;
constexpr int kMaxCarriers = 2;
constexpr int kMaxPathPoints = 8;
constexpr int kMaxBlastRecords = 4;
// Injected horizontal carrier speed (units/s) for the scripted x/z path. The
// source walkToTarget move speed is a consumed general parm whose retail
// value is not pinned in the lane docs; this is a labelled stand-in.
constexpr float kMoveSpeed = 60.0f;

// Pinned keyframe schedule indices (profile `timing` line order). The FSM
// owns no clip lengths; these host-fed stand-ins per state exist until the
// #128 converter supplies retail .bca durations. KEYEVENT_2 pulses at half
// the state's ticks.
enum TimingSlot {
    TWait = 0, TMove, TSupply, TBombWait, TBombMove, TRelease, TFall, TDamage,
    TTakeOff1, TTakeOff2, TFlick, kTimingSlots
};

// Tick-indexed host-event script (profile `event` lines): the seam's stand-in
// for Pikmin sticking, damage intake, bitter spray and kill, which a real
// host would derive from creature interactions.
enum EventKind { EvStuck = 0, EvHealth = 1, EvKill = 2, EvBitter = 3 };
struct ScriptEvent {
    int tick = 0;
    int kind = 0;
    float a = 0.0f, b = 0.0f;
};

struct CarrierState {
    P2BombSaraiFsm fsm;
    P2BombSaraiFsmParms fsmParms;
    P2BombSaraiHover hover;
    P2BombSaraiBomb* held = nullptr;
    P2BombSaraiVec3 carrier;          // x,z from profile + path; y = initial hover
    P2BombSaraiVec3 joint;            // body-local kamu_jnt1 stand-in offset
    float carrierYaw = 0.0f;
    float carrierY = 0.0f;            // hover-integrated height
    float carrierVy = 0.0f;           // Fall crash velocity
    float heightAboveGround = 0.0f;
    std::uint64_t carrierToken = 0;
    int stateTick = 0;
    // Scripted host state (events mutate these; FSM reads them as inputs).
    float health = 1500.0f;
    int stuckNormal = 0;
    int stuckPurple = 0;
    bool dead = false;
    bool bitter = false;              // cleared when the FSM leaves the Bomb* states
    int lastThrowKind = -1;
    int lastThrowTick = 0;
    // Scripted horizontal x/z path (injected walkToTarget stand-in).
    float pathX[kMaxPathPoints] = {};
    float pathZ[kMaxPathPoints] = {};
    int pathCount = 0;
    int pathIndex = 0;
    ScriptEvent events[kMaxEvents];
    int eventCount = 0;
};

struct ArenaState {
    P2BombSaraiBombConfig bombConfig;
    P2BombSaraiHoverParms hoverParms;
    int poolCapacity = 2; // mChildNum preallocation (enemyInfo.cpp:46)
    P2BombSaraiBombPool pool;
    P2BombSaraiReceiver receivers[kMaxReceivers];
    int receiverCount = 0;
    int timing[kTimingSlots] = { 30, 30, 10, 30, 30, 10, 10, 24, 45, 21, 20 };
    int carrierCount = 0;
    CarrierState carriers[kMaxCarriers];
    int tick = 0;
    std::uint64_t rng = 9001; // deterministic LCG for host-fed flick rolls
    P2BombSaraiBlastRecord blasts[kMaxBlastRecords];
    int blastCount = 0;
    bool blastFired = false;
    bool ready = false;
    bool drew = false;
};

ArenaState sArena;

bool finite(float value) { return std::isfinite(value); }
bool finite(P2BombSaraiVec3 value)
{
    return finite(value.x) && finite(value.y) && finite(value.z);
}
bool bounded(P2BombSaraiVec3 value)
{
    return finite(value) && std::fabs(value.x) <= kCoordinateLimit
        && std::fabs(value.y) <= kCoordinateLimit && std::fabs(value.z) <= kCoordinateLimit;
}
bool paramBound(float value, float minimum, float maximum)
{
    return finite(value) && value >= minimum && value <= maximum;
}
bool exhausted(std::istringstream& line)
{
    std::string extra;
    return !(line >> extra);
}
bool nextLine(std::ifstream& input, std::string& line)
{
    if (!std::getline(input, line)) return false;
    if (!line.empty() && line.back() == '\r') line.pop_back();
    return true;
}

int timingSlot(P2BombSaraiFsmState state)
{
    switch (state) {
    case P2BombSaraiFsmState::Wait: return TWait;
    case P2BombSaraiFsmState::Move: return TMove;
    case P2BombSaraiFsmState::Supply: return TSupply;
    case P2BombSaraiFsmState::BombWait: return TBombWait;
    case P2BombSaraiFsmState::BombMove: return TBombMove;
    case P2BombSaraiFsmState::Release: return TRelease;
    case P2BombSaraiFsmState::Fall: return TFall;
    case P2BombSaraiFsmState::Damage: return TDamage;
    case P2BombSaraiFsmState::TakeOff1: return TTakeOff1;
    case P2BombSaraiFsmState::TakeOff2: return TTakeOff2;
    case P2BombSaraiFsmState::Flick:
    case P2BombSaraiFsmState::BombFlick: return TFlick;
    case P2BombSaraiFsmState::Dead: break;
    }
    return -1; // Dead: no keyframes
}

bool parseEvent(std::istringstream& entry, ScriptEvent& event)
{
    std::string entryKey, kind;
    if (!(entry >> entryKey) || entryKey != "event") return false;
    if (!(entry >> event.tick >> kind) || event.tick < 0 || event.tick > 100000) return false;
    if (kind == "stuck") {
        event.kind = EvStuck;
        if (!(entry >> event.a >> event.b) || event.a < 0 || event.a > 99
            || event.b < 0 || event.b > 99) return false;
    } else if (kind == "health") {
        event.kind = EvHealth;
        if (!(entry >> event.a) || !paramBound(event.a, 0.0f, kParameterLimit)) return false;
    } else if (kind == "kill") {
        event.kind = EvKill;
    } else if (kind == "bitter") {
        event.kind = EvBitter;
    } else {
        return false;
    }
    return exhausted(entry);
}

bool parseEvents(std::ifstream& input, std::string& line, int slot, ArenaState& parsed,
                 const char* sectionName)
{
    std::istringstream values(line);
    std::string key;
    int count = 0;
    if (!(values >> key >> count) || count < 0 || count > kMaxEvents || !exhausted(values)
        || key != sectionName) return false;
    CarrierState& carrier = parsed.carriers[slot];
    carrier.eventCount = count;
    for (int i = 0; i < count; ++i) {
        if (!nextLine(input, line)) return false;
        std::istringstream entry(line);
        if (!parseEvent(entry, carrier.events[i])) return false;
    }
    return true;
}

// Parses `path <x0> <z0> [<x1> <z1> ...]` into a carrier's scripted waypoints.
bool parsePath(std::istringstream& values, CarrierState& carrier)
{
    int n = 0;
    while (n < kMaxPathPoints && (values >> carrier.pathX[n] >> carrier.pathZ[n])) {
        ++n;
        if (values.peek() == EOF) break;
    }
    if (n < 2 || !exhausted(values)) return false;
    for (int i = 0; i < n; ++i) {
        if (!std::isfinite(carrier.pathX[i]) || !std::isfinite(carrier.pathZ[i])
            || std::fabs(carrier.pathX[i]) > kCoordinateLimit
            || std::fabs(carrier.pathZ[i]) > kCoordinateLimit) return false;
    }
    carrier.pathCount = n;
    return true;
}

bool parseProfileFull(const char* profilePath, ArenaState& parsed)
{
    if (!profilePath || !*profilePath) return false;
    std::ifstream input(profilePath);
    if (!input) return false;
    input.seekg(0, std::ios::end);
    if (input.tellg() < 0 || input.tellg() > 8192) return false;
    input.seekg(0);

    std::string line;
    if (!nextLine(input, line) || line != "P2_BOMBSARAI_ARENA_1") return false;

    // Carrier 0 block.
    {
        if (!nextLine(input, line)) return false;
        std::istringstream values(line);
        std::string key;
        if (!(values >> key) || key != "carrier") return false;
        if (!(values >> parsed.carriers[0].carrier.x >> parsed.carriers[0].carrier.y
              >> parsed.carriers[0].carrier.z >> parsed.carriers[0].carrierYaw
              >> parsed.carriers[0].carrierToken) || !exhausted(values)) return false;
    }
    {
        // joint <body-local offset x y z> relative to the carrier body center
        // (kamu_jnt1 stand-in), rotated by carrier yaw each tick.
        if (!nextLine(input, line)) return false;
        std::istringstream values(line);
        std::string key;
        if (!(values >> key) || key != "joint") return false;
        if (!(values >> parsed.carriers[0].joint.x >> parsed.carriers[0].joint.y
              >> parsed.carriers[0].joint.z) || !exhausted(values)) return false;
    }
    {
        // hover <flightHeight> <pitchRate> <pitchAmp> <freeRise> <ladenRise>
        if (!nextLine(input, line)) return false;
        std::istringstream values(line);
        std::string key;
        if (!(values >> key) || key != "hover") return false;
        if (!(values >> parsed.hoverParms.flightHeight >> parsed.hoverParms.pitchRate
              >> parsed.hoverParms.pitchAmp >> parsed.hoverParms.freeRiseFactor
              >> parsed.hoverParms.ladenRiseFactor) || !exhausted(values)) return false;
    }
    {
        // bomb <gravityPerTick> <fuseHealth> <armLoopTicks> <bombRadius>
        //      <blastRadius> <blastHalfHeight> <tekiDamage> <naviPikiDamage>
        if (!nextLine(input, line)) return false;
        std::istringstream values(line);
        std::string key;
        if (!(values >> key) || key != "bomb") return false;
        if (!(values >> parsed.bombConfig.gravityPerTick >> parsed.bombConfig.fuseHealth
              >> parsed.bombConfig.armLoopTicks >> parsed.bombConfig.bombRadius
              >> parsed.bombConfig.blastRadius >> parsed.bombConfig.blastHalfHeight
              >> parsed.bombConfig.tekiDamage >> parsed.bombConfig.naviPikiDamage)
            || !exhausted(values)) return false;
    }
    {
        // receivers <count>, then count lines:
        // receiver <id> <kind> <x> <y> <z> <grounded> <airborneimmune>
        if (!nextLine(input, line)) return false;
        std::istringstream values(line);
        std::string key;
        if (!(values >> key >> parsed.receiverCount) || key != "receivers" || !exhausted(values)
            || parsed.receiverCount < 0 || parsed.receiverCount > kMaxReceivers) return false;
        for (int i = 0; i < parsed.receiverCount; ++i) {
            if (!nextLine(input, line)) return false;
            std::istringstream entry(line);
            std::string entryKey, kind;
            P2BombSaraiReceiver receiver;
            int immune = 0, grounded = 1;
            if (!(entry >> entryKey) || entryKey != "receiver") return false;
            if (!(entry >> receiver.id >> kind >> receiver.position.x >> receiver.position.y
                  >> receiver.position.z >> grounded >> immune) || !exhausted(entry)) return false;
            if (kind == "teki") receiver.kind = P2BombSaraiReceiverKind::Teki;
            else if (kind == "navi") receiver.kind = P2BombSaraiReceiverKind::Navi;
            else if (kind == "piki") receiver.kind = P2BombSaraiReceiverKind::Piki;
            else return false;
            receiver.grounded = grounded != 0;
            receiver.airborneBombImmune = immune != 0;
            receiver.alive = true;
            if (!bounded(receiver.position)) return false;
            parsed.receivers[i] = receiver;
        }
    }

    // Optional sections, in any order, at most one each:
    // timing, events (carrier 0), carrier2/joint2 (carrier 1),
    // path (carrier 0), path2 (carrier 1), events2 (carrier 1).
    bool seenTiming = false, seenEvents = false, seenCarrier2 = false, seenJoint2 = false,
         seenPath = false, seenPath2 = false, seenEvents2 = false, seenPool = false;
    while (nextLine(input, line)) {
        std::istringstream values(line);
        std::string key;
        if (!(values >> key)) return false;
        if (key == "timing" && !seenTiming) {
            seenTiming = true;
            for (int i = 0; i < kTimingSlots; ++i) {
                if (!(values >> parsed.timing[i]) || parsed.timing[i] < 1
                    || parsed.timing[i] > 10000) return false;
            }
            if (!exhausted(values)) return false;
        } else if (key == "events" && !seenEvents) {
            seenEvents = true;
            if (!parseEvents(input, line, 0, parsed, "events")) return false;
        } else if (key == "carrier2" && !seenCarrier2) {
            seenCarrier2 = true;
            CarrierState& c = parsed.carriers[1];
            if (!(values >> c.carrier.x >> c.carrier.y >> c.carrier.z >> c.carrierYaw
                  >> c.carrierToken) || !exhausted(values)) return false;
        } else if (key == "joint2" && !seenJoint2) {
            seenJoint2 = true;
            CarrierState& c = parsed.carriers[1];
            if (!(values >> c.joint.x >> c.joint.y >> c.joint.z) || !exhausted(values)) return false;
        } else if (key == "path" && !seenPath) {
            seenPath = true;
            if (!parsePath(values, parsed.carriers[0])) return false;
        } else if (key == "path2" && !seenPath2) {
            seenPath2 = true;
            if (!parsePath(values, parsed.carriers[1])) return false;
        } else if (key == "events2" && !seenEvents2) {
            seenEvents2 = true;
            if (!parseEvents(input, line, 1, parsed, "events2")) return false;
        } else if (key == "pool" && !seenPool) {
            // pool <capacity> — the shared bomb-pool size (mChildNum). Default 2.
            seenPool = true;
            if (!(values >> parsed.poolCapacity) || !exhausted(values)
                || parsed.poolCapacity < 1 || parsed.poolCapacity > 16) return false;
        } else {
            return false; // unknown or duplicate section
        }
    }

    // Carrier 1 is present iff both carrier2 and joint2 are present.
    if (seenCarrier2 != seenJoint2) return false;
    if (seenEvents2 && !seenCarrier2) return false;
    if (seenPath2 && !seenCarrier2) return false;
    parsed.carrierCount = seenCarrier2 ? 2 : 1;

    for (int i = 0; i < parsed.carrierCount; ++i) {
        const CarrierState& c = parsed.carriers[i];
        if (!bounded(c.carrier) || !bounded(c.joint) || !finite(c.carrierYaw)
            || std::fabs(c.carrierYaw) > 2.0f * kPi) return false;
    }
    return paramBound(parsed.hoverParms.flightHeight, 0.0f, kParameterLimit)
        && paramBound(parsed.hoverParms.pitchRate, 0.0f, kParameterLimit)
        && paramBound(parsed.hoverParms.pitchAmp, 0.0f, kParameterLimit)
        && paramBound(parsed.hoverParms.freeRiseFactor, 0.0f, kParameterLimit)
        && paramBound(parsed.hoverParms.ladenRiseFactor, 0.0f, kParameterLimit)
        && paramBound(parsed.bombConfig.gravityPerTick, 0.0f, kParameterLimit)
        && paramBound(parsed.bombConfig.fuseHealth, 0.0001f, kParameterLimit)
        && parsed.bombConfig.armLoopTicks > 0 && parsed.bombConfig.armLoopTicks <= 10000
        && paramBound(parsed.bombConfig.bombRadius, 0.0001f, kParameterLimit)
        && paramBound(parsed.bombConfig.blastRadius, 0.0001f, kParameterLimit)
        && paramBound(parsed.bombConfig.blastHalfHeight, 0.0f, kParameterLimit)
        && paramBound(parsed.bombConfig.tekiDamage, 0.0f, kParameterLimit)
        && paramBound(parsed.bombConfig.naviPikiDamage, 0.0f, kParameterLimit);
}

struct TraceBridge {
    P2BombSaraiTraceFn trace = nullptr;
    void* context = nullptr;
    bool failed = false;
};

bool requiredTrace(void* context, const P2BombSaraiVec3& position, const P2BombSaraiVec3& velocity,
                   float delta, float radius, P2BombSaraiTraceResult& result)
{
    TraceBridge& bridge = *static_cast<TraceBridge*>(context);
    if (!bridge.trace(bridge.context, position, velocity, delta, radius, result)) {
        bridge.failed = true;
        return false;
    }
    return true;
}

struct CarrierBridge {
    P2BombSaraiCarrierFn fn = nullptr;
    void* context = nullptr;
};

// Per-carrier liveness: a dead carrier fails its own token; an unknown token
// is delegated to the host callback (or treated as dead when absent), so a
// bomb never attributes to a stale/reused carrier object.
bool carrierGate(void* context, std::uint64_t token)
{
    CarrierBridge& bridge = *static_cast<CarrierBridge*>(context);
    for (int i = 0; i < sArena.carrierCount; ++i) {
        if (sArena.carriers[i].carrierToken == token) {
            return !sArena.carriers[i].dead;
        }
    }
    return bridge.fn ? bridge.fn(bridge.context, token) : false;
}

// Carrier index for a token, or -1 when no carrier owns it.
int carrierIndexOfToken(std::uint64_t token)
{
    for (int i = 0; i < sArena.carrierCount; ++i) {
        if (sArena.carriers[i].carrierToken == token) return i;
    }
    return -1;
}

// Deterministic host-fed flick roll in [0, 1) (LCG; profile-seeded).
float nextRoll()
{
    sArena.rng = sArena.rng * 6364136223846793005ull + 1442695040888963407ull;
    return (float)((sArena.rng >> 33) & 0x7FFFFFFFull) / 2147483648.0f;
}

// Joint world position from a carrier's current pose (body-local offset
// rotated by yaw, added to the hover-integrated body origin).
P2BombSaraiVec3 carrierJoint(const CarrierState& c)
{
    return P2BombSaraiJoint::compute({ c.carrier.x, c.carrierY, c.carrier.z },
                                     c.carrierYaw, c.joint);
}

// Scripted horizontal x/z motion along the carrier's waypoint ring.
void advancePath(CarrierState& c, float delta)
{
    if (c.pathCount < 2) return;
    const int next = (c.pathIndex + 1) % c.pathCount;
    const float dx = c.pathX[next] - c.carrier.x;
    const float dz = c.pathZ[next] - c.carrier.z;
    const float dist = std::sqrt(dx * dx + dz * dz);
    const float step = kMoveSpeed * delta;
    if (dist <= step || dist < 0.0001f) {
        c.carrier.x = c.pathX[next];
        c.carrier.z = c.pathZ[next];
        c.pathIndex = next;
    } else {
        c.carrier.x += dx / dist * step;
        c.carrier.z += dz / dist * step;
    }
}
}

void pc_p2_bombsarai_arena_reset()
{
    sArena = ArenaState{};
}

bool pc_p2_bombsarai_arena_setup(const char* profilePath)
{
    pc_p2_bombsarai_arena_reset();
    ArenaState parsed;
    if (!parseProfileFull(profilePath, parsed)) {
        std::fputs("P2_BOMBSARAI_ARENA invalid profile\n", stderr);
        return false;
    }
    int totalEvents = 0;
    for (int i = 0; i < parsed.carrierCount; ++i) {
        CarrierState& c = parsed.carriers[i];
        c.carrierY = c.carrier.y;
        c.health = c.fsmParms.maxHealth;
        c.hover.reset(parsed.hoverParms);
        c.fsm.reset(c.fsmParms);
        totalEvents += c.eventCount;
    }
    parsed.pool = P2BombSaraiBombPool(parsed.poolCapacity);
    parsed.ready = true;
    sArena = parsed;
    std::printf("P2_BOMBSARAI_ARENA_READY pinned=1 fsm=1 no_ai=1 no_visual_assets=1 "
                "joint_follow=1 carriers=%d receivers=%d pool=%d events=%d\n",
                sArena.carrierCount, sArena.receiverCount, sArena.pool.capacity(), totalEvents);
    return true;
}

bool pc_p2_bombsarai_arena_update(float sourceDelta,
                                  P2BombSaraiTraceFn trace, void* traceContext,
                                  P2BombSaraiCarrierFn carrier, void* carrierContext)
{
    if (!sArena.ready || !trace || !finite(sourceDelta)
        || std::fabs(sourceDelta - P2BombSaraiBomb::kSourceDelta) > 0.000001f) return false;
    P2BombSaraiTerrainAdapter* adapter = static_cast<P2BombSaraiTerrainAdapter*>(traceContext);
    ++sArena.tick;

    // Phase A: per-carrier events, motion, FSM decision and requested effects.
    for (int c = 0; c < sArena.carrierCount; ++c) {
        CarrierState& k = sArena.carriers[c];

        // 1. Scripted host events for this tick.
        bool killed = false;
        for (int i = 0; i < k.eventCount; ++i) {
            const ScriptEvent& event = k.events[i];
            if (event.tick != sArena.tick) continue;
            switch (event.kind) {
            case EvStuck:
                k.stuckNormal = (int)event.a;
                k.stuckPurple = (int)event.b;
                break;
            case EvHealth:
                k.health = event.a;
                break;
            case EvKill:
                k.health = 0.0f;
                killed = true;
                break;
            case EvBitter:
                k.bitter = true;
                break;
            }
        }

        // 2. Horizontal motion (scripted path) before the vertical step.
        const P2BombSaraiFsmState state = k.fsm.state();
        // Skip the walk in Fall/Damage/Dead: the carrier is crashing or
        // grounded there and must not advance its waypoint (source advancePath
        // runs only in the walking states).
        if (state != P2BombSaraiFsmState::Fall && state != P2BombSaraiFsmState::Damage
            && state != P2BombSaraiFsmState::Dead) {
            advancePath(k, sourceDelta);
        }

        // 3. Vertical motion: hover in the flying states, crash integration in
        // Fall, grounded in Damage/Dead (bomb-immunity semantics depend on the
        // floor contact, bombCallBack BombSarai.cpp:127-135).
        float groundY = 0.0f;
        if (!P2BombSaraiTerrainAdapter::getMinY(adapter, k.carrier.x, k.carrier.z, groundY)) {
            return false;
        }
        const bool fastTakeOff = state == P2BombSaraiFsmState::TakeOff2;
        if (state == P2BombSaraiFsmState::Fall) {
            k.carrierVy -= sArena.bombConfig.gravityPerTick * 30.0f * sourceDelta;
            k.carrierY += k.carrierVy * sourceDelta;
            if (k.carrierY < groundY) k.carrierY = groundY;
        } else if (state == P2BombSaraiFsmState::Damage || state == P2BombSaraiFsmState::Dead) {
            k.carrierVy = 0.0f;
            k.carrierY = groundY;
        } else {
            k.carrierVy = 0.0f;
            float velocityY = 0.0f, height = 0.0f;
            if (!k.hover.update(fastTakeOff, k.stuckNormal + k.stuckPurple,
                                { k.carrier.x, k.carrierY, k.carrier.z },
                                sourceDelta, adapter->mGetMinY, adapter->mGetMinYContext,
                                velocityY, height)) {
                return false;
            }
            k.carrierY += velocityY * sourceDelta;
        }
        if (!finite(k.carrierY)) return false;
        k.heightAboveGround = k.carrierY - groundY;

        const P2BombSaraiVec3 jointWorld = carrierJoint(k);
        if (!finite(jointWorld)) return false;

        // 4. Target sensing from the pinned receiver list (nearest alive
        // Navi/Pikmin). Retail radii: territory 200 (fp09), attackable 100/45deg
        // (fp20/fp21), attack XZ 50 (fp22 mAttackRadius). The angle gate uses the
        // profile yaw (the scripted path does not steer the carrier).
        bool targetTerritory = false, targetAttackable = false, targetXZ = false;
        {
            float best = 1.0e30f, bestDx = 0.0f, bestDz = 0.0f;
            for (int i = 0; i < sArena.receiverCount; ++i) {
                const P2BombSaraiReceiver& r = sArena.receivers[i];
                if (!r.alive || r.kind == P2BombSaraiReceiverKind::Teki) continue;
                const float dx = r.position.x - k.carrier.x;
                const float dz = r.position.z - k.carrier.z;
                const float d2 = dx * dx + dz * dz;
                if (d2 < best) { best = d2; bestDx = dx; bestDz = dz; }
            }
            if (best < 1.0e29f) {
                const float dist = std::sqrt(best);
                targetTerritory = dist <= 200.0f;
                if (dist <= 100.0f) {
                    const float fx = std::sin(k.carrierYaw), fz = std::cos(k.carrierYaw);
                    const float dot = dist > 0.0001f ? (bestDx * fx + bestDz * fz) / dist : 1.0f;
                    targetAttackable = dot >= std::cos(45.0f * kPi / 180.0f);
                }
                targetXZ = dist <= 50.0f;
            }
        }

        // 5. Keyframe pulses from the profile timing of the current state.
        bool animEnd = false, keyEvent2 = false;
        {
            const int slot = timingSlot(k.fsm.state());
            if (slot >= 0) {
                const int ticks = sArena.timing[slot];
                const int at = k.stateTick + 1;
                animEnd = at >= ticks;
                keyEvent2 = at == (ticks > 1 ? ticks / 2 : 1);
            }
        }

        // 6. FSM decision.
        P2BombSaraiFsmInput in;
        in.health = k.health;
        in.carrying = k.held != nullptr; // mHeldBomb: Captured only (cleared on throw)
        in.stuckPikmin = k.stuckNormal + k.stuckPurple;
        in.stuckPurple = k.stuckPurple;
        in.targetWithinTerritory = targetTerritory;
        in.targetAttackable = targetAttackable;
        in.targetWithinAttackXZ = targetXZ;
        in.waypointReached = false; // scripted path is not a source walkToTarget arrival
        in.heightAboveGround = k.heightAboveGround;
        in.animEnd = animEnd;
        in.keyEvent2 = keyEvent2;
        in.bitterQueued = k.bitter;
        in.killed = killed;
        in.flickRoll = nextRoll();
        P2BombSaraiFsmOutput out;
        k.fsm.update(in, out);
        if (out.entered) {
            k.stateTick = 0;
            if (out.state == P2BombSaraiFsmState::Fall) k.carrierVy = 0.0f;
            if (out.state == P2BombSaraiFsmState::Fall
                || out.state == P2BombSaraiFsmState::Release) k.bitter = false;
        } else {
            ++k.stateTick;
        }
        if (out.state != P2BombSaraiFsmState::BombWait
            && out.state != P2BombSaraiFsmState::BombMove
            && out.state != P2BombSaraiFsmState::BombFlick) k.bitter = false;

        // 7. Requested effects for this carrier.
        if (out.supplyRequested && !k.held) {
            k.held = sArena.pool.supply(k.carrierToken, jointWorld, sArena.bombConfig);
            // Exhaustion is tolerated silently (source behavior); the FSM
            // proceeds through the Bomb* states with no payload.
        }
        if (out.throwRequested && k.held) {
            k.held->throwBomb(out.throwKind, k.carrierYaw);
            k.lastThrowKind = (int)out.throwKind;
            k.lastThrowTick = sArena.tick;
            k.held = nullptr; // mHeldBomb cleared in flight (BombSarai.cpp:285-294)
        }
        if (killed) {
            k.dead = true;
        }
    }

    // Phase B: glue each carrier's captured payload to its joint, then advance
    // every live bomb in the shared pool. Captured bombs are constrained (their
    // update is a no-op); in-flight/armed/burning bombs fly through the trace
    // and may detonate. Iterating the pool means an in-flight bomb keeps
    // advancing after its carrier has cleared its held pointer (and possibly
    // supplied a second bomb — see Finding #2).
    for (int c = 0; c < sArena.carrierCount; ++c) {
        if (sArena.carriers[c].held) {
            sArena.carriers[c].held->followJoint(carrierJoint(sArena.carriers[c]));
        }
    }
    TraceBridge bridge{ trace, traceContext };
    const int poolSlots = sArena.pool.slotCount();
    for (int slot = 0; slot < poolSlots; ++slot) {
        if (!sArena.pool.slotLive(slot)) continue;
        P2BombSaraiBomb* bomb = sArena.pool.bombAt(slot);
        CarrierBridge carrierBridge{ carrier, carrierContext };
        bomb->update(sourceDelta, requiredTrace, &bridge, carrierGate, &carrierBridge);
        if (bridge.failed) return false;
        if (bomb->hasBlast()) {
            const P2BombSaraiBlastEvent& event = bomb->lastBlast();
            if (sArena.blastCount >= kMaxBlastRecords) {
                std::fputs("P2_BOMBSARAI_BLAST_OVERFLOW record capacity exceeded\n", stderr);
                return false; // never silently drop a detonation
            }
            P2BombSaraiBlastRecord& record = sArena.blasts[sArena.blastCount++];
            record.carrier = carrierIndexOfToken(event.carrierToken);
            record.carrierToken = event.carrierToken;
            record.carrierValid = event.carrierValid;
            record.center = event.center;
            record.tick = sArena.tick;
            record.hitCount = p2_bombsarai_route_blast(event, sArena.receivers,
                                                        sArena.receiverCount,
                                                        record.hits, kMaxReceivers);
            if (record.hitCount < 0) return false;
            sArena.blastFired = true;
            bomb->clearBlast();
        }
    }
    return true;
}

int pc_p2_bombsarai_arena_carrier_count()
{
    return sArena.carrierCount;
}

int pc_p2_bombsarai_arena_state(int carrier)
{
    if (carrier < 0 || carrier >= sArena.carrierCount) return -1;
    return (int)sArena.carriers[carrier].fsm.state();
}

const char* pc_p2_bombsarai_arena_state_name(int carrier)
{
    if (carrier < 0 || carrier >= sArena.carrierCount) return "?";
    return P2BombSaraiFsm::stateName(sArena.carriers[carrier].fsm.state());
}

bool pc_p2_bombsarai_arena_carrier_dead(int carrier)
{
    if (carrier < 0 || carrier >= sArena.carrierCount) return true;
    return sArena.carriers[carrier].dead;
}

bool pc_p2_bombsarai_arena_carrying(int carrier)
{
    if (carrier < 0 || carrier >= sArena.carrierCount) return false;
    P2BombSaraiBomb* held = sArena.carriers[carrier].held;
    return held != nullptr && held->phase() == P2BombSaraiBombPhase::Captured;
}

bool pc_p2_bombsarai_arena_captured_position(int carrier, P2BombSaraiVec3& out)
{
    if (carrier < 0 || carrier >= sArena.carrierCount) return false;
    P2BombSaraiBomb* held = sArena.carriers[carrier].held;
    if (!held || held->phase() != P2BombSaraiBombPhase::Captured) return false;
    out = held->position();
    return true;
}

int pc_p2_bombsarai_arena_last_throw_kind(int carrier)
{
    if (carrier < 0 || carrier >= sArena.carrierCount) return -1;
    return sArena.carriers[carrier].lastThrowKind;
}

int pc_p2_bombsarai_arena_last_throw_tick(int carrier)
{
    if (carrier < 0 || carrier >= sArena.carrierCount) return -1;
    return sArena.carriers[carrier].lastThrowTick;
}

bool pc_p2_bombsarai_arena_blast_fired()
{
    return sArena.blastFired;
}

int pc_p2_bombsarai_arena_blast_record_count()
{
    return sArena.blastCount;
}

const P2BombSaraiBlastRecord* pc_p2_bombsarai_arena_blast_records()
{
    return sArena.blasts;
}

void pc_p2_bombsarai_arena_draw(Graphics& gfx)
{
    if (!sArena.ready || !gfx.mCamera) return;
    gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx, gfx.mCamera->mFov,
                       gfx.mCamera->mAspectRatio, gfx.mCamera->mNear, gfx.mCamera->mFar, 1.0f);
    gfx.useMaterial(nullptr);
    gfx.setDepth(true);
    for (int c = 0; c < sArena.carrierCount; ++c) {
        const CarrierState& k = sArena.carriers[c];
        const Vector3f carrierPos(k.carrier.x, k.carrierY, k.carrier.z);
        gfx.drawSphere(carrierPos, 10.0f, gfx.mCamera->mLookAtMtx);
        if (k.held) {
            const P2BombSaraiVec3& p = k.held->position();
            const Vector3f bombPos(p.x, p.y, p.z);
            gfx.drawSphere(bombPos, sArena.bombConfig.bombRadius, gfx.mCamera->mLookAtMtx);
        }
    }
    for (int b = 0; b < sArena.blastCount; ++b) {
        const P2BombSaraiBlastRecord& record = sArena.blasts[b];
        const Vector3f blastPos(record.center.x, record.center.y, record.center.z);
        gfx.drawSphere(blastPos, sArena.bombConfig.blastRadius, gfx.mCamera->mLookAtMtx);
    }
    if (!sArena.drew) {
        std::puts("P2_BOMBSARAI_ARENA_DRAW debug_markers_only no_visual_assets=1");
        sArena.drew = true;
    }
}
