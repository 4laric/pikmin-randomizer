#include "pc_p2_bombsarai_arena.h"

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

struct ArenaState {
    P2BombSaraiFsm fsm;
    P2BombSaraiFsmParms fsmParms;
    P2BombSaraiHover hover;
    P2BombSaraiHoverParms hoverParms;
    P2BombSaraiBombConfig bombConfig;
    P2BombSaraiBombPool pool{ 2 }; // mChildNum preallocation (enemyInfo.cpp:46)
    P2BombSaraiBomb* held = nullptr;
    P2BombSaraiVec3 carrier;
    P2BombSaraiVec3 joint; // pinned capture joint (kamu_jnt1 stand-in, #128 pending)
    float carrierYaw = 0.0f;
    float carrierY = 0.0f;   // current hover height, integrated by the seam
    float carrierVy = 0.0f;  // Fall crash velocity
    float heightAboveGround = 0.0f;
    std::uint64_t carrierToken = 0;
    P2BombSaraiReceiver receivers[kMaxReceivers];
    int receiverCount = 0;
    P2BombSaraiRoutedHit hits[kMaxReceivers];
    int hitCount = 0;
    P2BombSaraiVec3 lastBlastCenter;
    int timing[kTimingSlots] = { 30, 30, 10, 30, 30, 10, 10, 24, 45, 21, 20 };
    ScriptEvent events[kMaxEvents];
    int eventCount = 0;
    int tick = 0;
    int stateTick = 0;
    // Scripted host state (events mutate these; FSM reads them as inputs).
    float health = 1500.0f;
    int stuckNormal = 0;
    int stuckPurple = 0;
    bool dead = false;
    bool bitter = false; // level, cleared when the FSM leaves the Bomb* states
    std::uint64_t rng = 9001; // deterministic LCG for host-fed flick rolls
    int lastThrowKind = -1;
    int lastThrowTick = 0;
    bool blastMarker = false;
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

    {
        if (!nextLine(input, line)) return false;
        std::istringstream values(line);
        std::string key;
        if (!(values >> key) || key != "carrier") return false;
        if (!(values >> parsed.carrier.x >> parsed.carrier.y >> parsed.carrier.z
              >> parsed.carrierYaw >> parsed.carrierToken) || !exhausted(values)) return false;
    }
    {
        if (!nextLine(input, line)) return false;
        std::istringstream values(line);
        std::string key;
        if (!(values >> key) || key != "joint") return false;
        if (!(values >> parsed.joint.x >> parsed.joint.y >> parsed.joint.z) || !exhausted(values)) {
            return false;
        }
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
    // Optional sections, in any order, at most one each: timing, events.
    bool seenTiming = false, seenEvents = false;
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
            continue;
        }
        if (key == "events" && !seenEvents) {
            seenEvents = true;
            if (!(values >> parsed.eventCount) || parsed.eventCount < 0
                || parsed.eventCount > kMaxEvents || !exhausted(values)) return false;
            for (int i = 0; i < parsed.eventCount; ++i) {
                if (!nextLine(input, line)) return false;
                std::istringstream entry(line);
                std::string entryKey, kind;
                ScriptEvent event;
                if (!(entry >> entryKey) || entryKey != "event") return false;
                if (!(entry >> event.tick >> kind) || event.tick < 0 || event.tick > 100000) {
                    return false;
                }
                if (kind == "stuck") {
                    event.kind = EvStuck;
                    if (!(entry >> event.a >> event.b) || event.a < 0 || event.a > 99
                        || event.b < 0 || event.b > 99) return false;
                } else if (kind == "health") {
                    event.kind = EvHealth;
                    if (!(entry >> event.a) || !paramBound(event.a, 0.0f, kParameterLimit)) {
                        return false;
                    }
                } else if (kind == "kill") {
                    event.kind = EvKill;
                } else if (kind == "bitter") {
                    event.kind = EvBitter;
                } else {
                    return false;
                }
                if (!exhausted(entry)) return false;
                parsed.events[i] = event;
            }
            continue;
        }
        return false; // unknown or duplicate section
    }

    return bounded(parsed.carrier) && bounded(parsed.joint) && finite(parsed.carrierYaw)
        && std::fabs(parsed.carrierYaw) <= 2.0f * kPi
        && paramBound(parsed.hoverParms.flightHeight, 0.0f, kParameterLimit)
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

// Carrier-liveness wrapper: after a scripted kill the token must fail
// validation so later blasts attribute Navi/Pikmin damage to the bomb
// (source mCarrier==nullptr fallback, bombState.cpp:167-172).
struct CarrierBridge {
    P2BombSaraiCarrierFn fn = nullptr;
    void* context = nullptr;
};

bool carrierGate(void* context, std::uint64_t token)
{
    CarrierBridge& bridge = *static_cast<CarrierBridge*>(context);
    if (sArena.dead) return false;
    return bridge.fn ? bridge.fn(bridge.context, token) : false;
}

// Deterministic host-fed flick roll in [0, 1) (LCG; profile-seeded).
float nextRoll()
{
    sArena.rng = sArena.rng * 6364136223846793005ull + 1442695040888963407ull;
    return (float)((sArena.rng >> 33) & 0x7FFFFFFFull) / 2147483648.0f;
}
}

void pc_p2_bombsarai_arena_reset()
{
    const P2BombSaraiBombConfig config = sArena.bombConfig;
    const P2BombSaraiHoverParms hover = sArena.hoverParms;
    sArena = ArenaState{};
    sArena.bombConfig = config;
    sArena.hoverParms = hover;
}

bool pc_p2_bombsarai_arena_setup(const char* profilePath)
{
    pc_p2_bombsarai_arena_reset();
    ArenaState parsed;
    if (!parseProfileFull(profilePath, parsed)) {
        std::fputs("P2_BOMBSARAI_ARENA invalid profile\n", stderr);
        return false;
    }
    parsed.carrierY = parsed.carrier.y;
    parsed.health = parsed.fsmParms.maxHealth;
    parsed.hover.reset(parsed.hoverParms);
    parsed.fsm.reset(parsed.fsmParms);
    parsed.ready = true;
    sArena = parsed;
    std::printf("P2_BOMBSARAI_ARENA_READY pinned=1 fsm=1 no_ai=1 no_visual_assets=1 "
                "receivers=%d pool=%d events=%d\n", sArena.receiverCount,
                sArena.pool.capacity(), sArena.eventCount);
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

    // 1. Scripted host events for this tick.
    bool killed = false;
    for (int i = 0; i < sArena.eventCount; ++i) {
        const ScriptEvent& event = sArena.events[i];
        if (event.tick != sArena.tick) continue;
        switch (event.kind) {
        case EvStuck:
            sArena.stuckNormal = (int)event.a;
            sArena.stuckPurple = (int)event.b;
            break;
        case EvHealth:
            sArena.health = event.a;
            break;
        case EvKill:
            sArena.health = 0.0f;
            killed = true;
            break;
        case EvBitter:
            sArena.bitter = true;
            break;
        }
    }

    // 2. Vertical motion: hover control in the flying states, crash
    // integration in Fall, grounded in Damage/Dead (bomb-immunity semantics
    // depend on the floor contact, bombCallBack BombSarai.cpp:127-135).
    const P2BombSaraiFsmState state = sArena.fsm.state();
    float groundY = 0.0f;
    if (!P2BombSaraiTerrainAdapter::getMinY(adapter, sArena.carrier.x, sArena.carrier.z, groundY)) {
        return false;
    }
    const bool fastTakeOff = state == P2BombSaraiFsmState::TakeOff2;
    if (state == P2BombSaraiFsmState::Fall) {
        sArena.carrierVy -= sArena.bombConfig.gravityPerTick * 30.0f * sourceDelta;
        sArena.carrierY += sArena.carrierVy * sourceDelta;
        if (sArena.carrierY < groundY) sArena.carrierY = groundY;
    } else if (state == P2BombSaraiFsmState::Damage || state == P2BombSaraiFsmState::Dead) {
        sArena.carrierVy = 0.0f;
        sArena.carrierY = groundY;
    } else {
        sArena.carrierVy = 0.0f;
        float velocityY = 0.0f, height = 0.0f;
        if (!sArena.hover.update(fastTakeOff, sArena.stuckNormal + sArena.stuckPurple,
                                 { sArena.carrier.x, sArena.carrierY, sArena.carrier.z },
                                 sourceDelta, adapter->mGetMinY, adapter->mGetMinYContext,
                                 velocityY, height)) {
            return false;
        }
        sArena.carrierY += velocityY * sourceDelta;
    }
    if (!finite(sArena.carrierY)) return false;
    sArena.heightAboveGround = sArena.carrierY - groundY;

    // 3. Target sensing from the pinned receiver list (nearest alive
    // Navi/Pikmin). Retail radii: territory 200 (fp09), attackable 100/45deg
    // (fp20/fp21), attack XZ 50 (fp22 mAttackRadius). The pinned carrier
    // never turns, so the attackable angle gate uses the profile yaw.
    bool targetTerritory = false, targetAttackable = false, targetXZ = false;
    {
        float best = 1.0e30f, bestDx = 0.0f, bestDz = 0.0f;
        for (int i = 0; i < sArena.receiverCount; ++i) {
            const P2BombSaraiReceiver& r = sArena.receivers[i];
            if (!r.alive || r.kind == P2BombSaraiReceiverKind::Teki) continue;
            const float dx = r.position.x - sArena.carrier.x;
            const float dz = r.position.z - sArena.carrier.z;
            const float d2 = dx * dx + dz * dz;
            if (d2 < best) { best = d2; bestDx = dx; bestDz = dz; }
        }
        if (best < 1.0e29f) {
            const float dist = std::sqrt(best);
            targetTerritory = dist <= 200.0f;
            if (dist <= 100.0f) {
                const float fx = std::sin(sArena.carrierYaw), fz = std::cos(sArena.carrierYaw);
                const float dot = dist > 0.0001f ? (bestDx * fx + bestDz * fz) / dist : 1.0f;
                targetAttackable = dot >= std::cos(45.0f * kPi / 180.0f);
            }
            targetXZ = dist <= 50.0f;
        }
    }

    // 4. Keyframe pulses from the profile timing of the current state.
    bool animEnd = false, keyEvent2 = false;
    {
        const int slot = timingSlot(sArena.fsm.state());
        if (slot >= 0) {
            const int ticks = sArena.timing[slot];
            const int at = sArena.stateTick + 1;
            animEnd = at >= ticks;
            keyEvent2 = at == (ticks > 1 ? ticks / 2 : 1);
        }
    }

    // 5. FSM decision.
    P2BombSaraiFsmInput in;
    in.health = sArena.health;
    in.carrying = sArena.held != nullptr;
    in.stuckPikmin = sArena.stuckNormal + sArena.stuckPurple;
    in.stuckPurple = sArena.stuckPurple;
    in.targetWithinTerritory = targetTerritory;
    in.targetAttackable = targetAttackable;
    in.targetWithinAttackXZ = targetXZ;
    in.waypointReached = false; // pinned carrier: walkToTarget never arrives
    in.heightAboveGround = sArena.heightAboveGround;
    in.animEnd = animEnd;
    in.keyEvent2 = keyEvent2;
    in.bitterQueued = sArena.bitter;
    in.killed = killed;
    in.flickRoll = nextRoll();
    P2BombSaraiFsmOutput out;
    sArena.fsm.update(in, out);
    if (out.entered) {
        sArena.stateTick = 0;
        if (out.state == P2BombSaraiFsmState::Fall) sArena.carrierVy = 0.0f;
        // Bitter is consumed once the FSM reacts (leaves the Bomb* states).
        if (out.state == P2BombSaraiFsmState::Fall
            || out.state == P2BombSaraiFsmState::Release) sArena.bitter = false;
    } else {
        ++sArena.stateTick;
    }
    if (out.state != P2BombSaraiFsmState::BombWait
        && out.state != P2BombSaraiFsmState::BombMove
        && out.state != P2BombSaraiFsmState::BombFlick) sArena.bitter = false;

    // 6. Requested effects.
    if (out.supplyRequested && !sArena.held) {
        sArena.held = sArena.pool.supply(sArena.carrierToken, sArena.joint, sArena.bombConfig);
        // Exhaustion is tolerated silently (source behavior); the FSM
        // proceeds through the Bomb* states with no payload.
    }
    if (out.throwRequested && sArena.held) {
        sArena.held->throwBomb(out.throwKind, sArena.carrierYaw);
        sArena.lastThrowKind = (int)out.throwKind;
        sArena.lastThrowTick = sArena.tick;
    }
    if (killed) {
        sArena.dead = true;
    }

    // 7. Bomb update + blast routing.
    TraceBridge bridge{ trace, traceContext };
    if (sArena.held) {
        CarrierBridge carrierBridge{ carrier, carrierContext };
        P2BombSaraiBomb* held = sArena.held;
        held->update(sourceDelta, requiredTrace, &bridge, carrierGate, &carrierBridge);
        if (bridge.failed) return false;
        if (held->hasBlast()) {
            sArena.lastBlastCenter = held->lastBlast().center;
            sArena.hitCount = p2_bombsarai_route_blast(held->lastBlast(), sArena.receivers,
                                                       sArena.receiverCount, sArena.hits,
                                                       kMaxReceivers);
            if (sArena.hitCount < 0) return false;
            sArena.blastMarker = true;
            sArena.blastFired = true;
            held->clearBlast();
        }
        if (!sArena.held) { // unreachable, guards pool pointer reuse
            return false;
        }
        if (sArena.held->phase() == P2BombSaraiBombPhase::Despawned) {
            sArena.held = nullptr;
        }
    }
    return true;
}

int pc_p2_bombsarai_arena_state()
{
    return (int)sArena.fsm.state();
}

const char* pc_p2_bombsarai_arena_state_name()
{
    return P2BombSaraiFsm::stateName(sArena.fsm.state());
}

bool pc_p2_bombsarai_arena_carrier_dead()
{
    return sArena.dead;
}

bool pc_p2_bombsarai_arena_carrying()
{
    return sArena.held != nullptr
        && sArena.held->phase() == P2BombSaraiBombPhase::Captured;
}

int pc_p2_bombsarai_arena_last_throw_kind()
{
    return sArena.lastThrowKind;
}

int pc_p2_bombsarai_arena_last_throw_tick()
{
    return sArena.lastThrowTick;
}

bool pc_p2_bombsarai_arena_blast_fired()
{
    return sArena.blastFired;
}

int pc_p2_bombsarai_arena_blast_count()
{
    return sArena.hitCount;
}

const P2BombSaraiRoutedHit* pc_p2_bombsarai_arena_blast_hits()
{
    return sArena.hits;
}

void pc_p2_bombsarai_arena_draw(Graphics& gfx)
{
    if (!sArena.ready || !gfx.mCamera) return;
    gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx, gfx.mCamera->mFov,
                       gfx.mCamera->mAspectRatio, gfx.mCamera->mNear, gfx.mCamera->mFar, 1.0f);
    gfx.useMaterial(nullptr);
    gfx.setDepth(true);
    const Vector3f carrierPos(sArena.carrier.x, sArena.carrierY, sArena.carrier.z);
    gfx.drawSphere(carrierPos, 10.0f, gfx.mCamera->mLookAtMtx);
    if (sArena.held) {
        const P2BombSaraiVec3& p = sArena.held->position();
        const Vector3f bombPos(p.x, p.y, p.z);
        gfx.drawSphere(bombPos, sArena.bombConfig.bombRadius, gfx.mCamera->mLookAtMtx);
    }
    if (sArena.blastMarker) {
        const Vector3f blastPos(sArena.lastBlastCenter.x, sArena.lastBlastCenter.y,
                                sArena.lastBlastCenter.z);
        gfx.drawSphere(blastPos, sArena.bombConfig.blastRadius, gfx.mCamera->mLookAtMtx);
    }
    if (!sArena.drew) {
        std::puts("P2_BOMBSARAI_ARENA_DRAW debug_markers_only no_visual_assets=1");
        sArena.drew = true;
    }
}
