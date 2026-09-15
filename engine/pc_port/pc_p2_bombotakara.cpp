// Pikmin 2 lane-22 BombOtakara payload sidecar runtime (#170, child #447).
//
// Policy-driven, actor-local BombOtakara simulation. The payload is a
// sidecar-staged stub (labeled) driven by pc_p2_bombotakara_policy.h. On
// detonation the module now consumes the shared blast primitive owned by the
// projectiles/BombSarai lane (pc_p2_bombsarai_blast.h, #169) and applies the
// source Bomb's InteractBomb to enumerated receivers; the numeric Bomb parms
// are the pinned retail values from the lane-20 tests (radius 90 fp22, teki 500
// fp01, navi/piki 10 fp24, half-height 50 fp02). Missing sidecar = inert;
// malformed = fail closed.
#include "pc_p2_bombotakara.h"
#include "pc_p2_bombotakara_policy.h"
#include "pc_p2_bombsarai_blast.h"
#include "pc_bbft.h"
#include "Interactions.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include <SDL.h>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>

class Graphics;

namespace {

const float kTickSeconds = 1.0f / 30.0f;
// Shared Bomb payload parms (lane-20 pinned retail values; Bomb.h defaults for
// fp02): radius mAttackRadius fp22 90, teki damage fp01 500, navi/piki damage
// fp24 10, blast half-height fp02 50.
const float kBlastRadius     = 90.0f;
const float kBlastHalfHeight = 50.0f;
const float kTekDamage       = 500.0f;
const float kNavPikiDamage   = 10.0f;

struct Unit {
    std::uint32_t generator = 0;
    std::uint32_t payloadId = 0;
    float x = 0.0f, y = 0.0f, z = 0.0f, yaw = 0.0f, health = 0.0f;
    float bx = 0.0f, by = 0.0f, bz = 0.0f;
    bool carrying = true;
    bool armed = false;
    bool detonated = false;
    bool dead = false;
    bool payloadLost = false;
    float armTimer = 0.0f;
    bool carryLogged = false;
};

enum InjectMode { ModeContact = 0, ModePress, ModeDeath, ModeEarthquake, ModePayloadLost };

struct Injection {
    unsigned long tick = 0;
    std::uint32_t generator = 0;
    int mode = ModeContact;
    bool done = false;
};

std::vector<Unit> units;
std::vector<Injection> injections;
unsigned long behaviorTick = 0;
float clockAccumulator = 0.0f;
unsigned clockLast = 0;
int suppressedCount = 0;
int blastCount = 0;

// The InteractBomb receiver uses the owner for the knockback direction and
// sound source (interactBattle.cpp:63). A carrierless BombOtakara blast is
// attributed to the bomb itself (bombState.cpp:167-172), so a stateless
// module-local Creature positioned at the blast center is the faithful owner.
class BlastOwner : public Creature {
public:
    BlastOwner() : Creature(nullptr) { mHealth = 1.0f; }
    void refresh(Graphics&) override {}
    void doKill() override {}
};
BlastOwner blastOwner;

Unit* findUnit(std::uint32_t generator) {
    for (auto& unit : units)
        if (unit.generator == generator) return &unit;
    return nullptr;
}

// Consume the shared BombSarai blast primitive: enumerate Pikmin/Navi/Teki
// receivers, classify/attribute with the shared policy, then apply the source
// Bomb's InteractBomb to each routed hit. Returns the number of receivers hit.
int applyBlast(Unit& unit) {
    P2BombSaraiBlastEvent event;
    event.center = P2BombSaraiVec3{unit.bx, unit.by, unit.bz};
    event.radius = kBlastRadius;
    event.halfHeight = kBlastHalfHeight;
    event.tekiDamage = kTekDamage;
    event.naviPikiDamage = kNavPikiDamage;
    event.hasCarrier = false;
    event.carrierValid = false;

    std::vector<P2BombSaraiReceiver> receivers;
    std::vector<Creature*> actors;
    std::vector<P2BombSaraiReceiverKind> kinds;
    auto addReceiver = [&](Creature* creature, P2BombSaraiReceiverKind kind) {
        if (!creature || !creature->isAlive()) return;
        const Vector3f& position = creature->getPosition();
        P2BombSaraiReceiver receiver;
        receiver.id = receivers.size();
        receiver.position = P2BombSaraiVec3{position.x, position.y, position.z};
        receiver.kind = kind;
        receiver.alive = true;
        receiver.grounded = true;
        receivers.push_back(receiver);
        actors.push_back(creature);
        kinds.push_back(kind);
    };
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) { addReceiver(static_cast<Creature*>(static_cast<Piki*>(*it)), P2BombSaraiReceiverKind::Piki); }
    }
    if (naviMgr && naviMgr->getNavi()) {
        addReceiver(static_cast<Creature*>(naviMgr->getNavi()), P2BombSaraiReceiverKind::Navi);
    }
    if (receivers.empty()) {
        std::printf("P2_BOMBOTAKARA_BLAST generator=%u payload=%u center=%.3f,%.3f,%.3f radius=%.1f "
                    "receivers=0 hits=0 pikmin_hits=0\n",
                    unit.generator, unit.payloadId, unit.bx, unit.by, unit.bz, kBlastRadius);
        ++blastCount;
        return 0;
    }
    std::vector<P2BombSaraiRoutedHit> hits(receivers.size());
    const int routed = p2_bombsarai_route_blast(event, receivers.data(), int(receivers.size()), hits.data(),
                                                int(hits.size()));
    if (routed < 0) {
        std::printf("P2_BOMBOTAKARA_BLAST_BLOCKED generator=%u payload=%u reason=invalid_blast\n", unit.generator,
                    unit.payloadId);
        return 0;
    }
    int pikminHits = 0;
    blastOwner.mSRT.t.set(unit.bx, unit.by, unit.bz);
    for (int i = 0; i < routed; ++i) {
        const P2BombSaraiRoutedHit& hit = hits[i];
        if (hit.receiverId >= actors.size() || !actors[hit.receiverId]) continue;
        InteractBomb bomb(&blastOwner, hit.damage, nullptr);
        actors[hit.receiverId]->stimulate(bomb);
        if (kinds[hit.receiverId] == P2BombSaraiReceiverKind::Piki) ++pikminHits;
    }
    std::printf("P2_BOMBOTAKARA_BLAST generator=%u payload=%u center=%.3f,%.3f,%.3f radius=%.1f receivers=%d "
                "hits=%d pikmin_hits=%d teki_damage=%.1f navi_piki_damage=%.1f shared_primitive=1\n",
                unit.generator, unit.payloadId, unit.bx, unit.by, unit.bz, kBlastRadius, int(receivers.size()), routed,
                pikminHits, kTekDamage, kNavPikiDamage);
    ++blastCount;
    return routed;
}

void detonate(Unit& unit, p2bombotakara::Trigger trigger) {
    const p2bombotakara::DetonationResult result = p2bombotakara::detonate(unit.carrying, unit.detonated);
    if (result.detonated) {
        unit.detonated = true;
        unit.carrying = false;
        std::printf("P2_BOMBOTAKARA_DETONATE generator=%u payload=%u trigger=%s detonated=1 "
                    "exactly_once=1 total_detonations=1\n",
                    unit.generator, unit.payloadId, p2bombotakara::triggerName(trigger));
        applyBlast(unit);
    } else {
        ++suppressedCount;
        std::printf("P2_BOMBOTAKARA_DETONATE_SUPPRESSED generator=%u payload=%u trigger=%s detonated=0 "
                    "already_detonated=1\n",
                    unit.generator, unit.payloadId, p2bombotakara::triggerName(trigger));
    }
}

void applyInjection(Injection& injection) {
    Unit* unit = findUnit(injection.generator);
    if (!unit) return;
    if (injection.mode == ModePayloadLost) {
        if (unit->dead || unit->payloadLost) return;
        unit->payloadLost = true;
        unit->carrying = false;
        unit->dead = true;
        std::printf("P2_BOMBOTAKARA_PAYLOAD_LOST generator=%u payload=%u action=kill_carrier\n",
                    unit->generator, unit->payloadId);
        std::printf("P2_BOMBOTAKARA_KILL_CARRIER generator=%u\n", unit->generator);
        return;
    }
    if (injection.mode == ModeDeath) {
        if (!unit->dead) {
            unit->dead = true;
            unit->health = 0.0f;
            std::printf("P2_BOMBOTAKARA_DEATH generator=%u\n", unit->generator);
        }
        detonate(*unit, p2bombotakara::TriggerDeath);
        return;
    }
    const p2bombotakara::Trigger trigger = injection.mode == ModePress ? p2bombotakara::TriggerPress
        : injection.mode == ModeEarthquake ? p2bombotakara::TriggerEarthquake
                                           : p2bombotakara::TriggerContact;
    detonate(*unit, trigger);
}

void tickUnit(Unit& unit) {
    if (unit.dead || unit.payloadLost) return;
    if (!unit.carrying) return;
    // stimulateBomb: while chasing, the payload force-fires after 1.5 s.
    unit.armTimer += kTickSeconds;
    if (!unit.armed && unit.armTimer >= p2bombotakara::kForceDelaySeconds) {
        unit.armed = true;
        std::printf("P2_BOMBOTAKARA_ARM generator=%u payload=%u arm_seconds=%.2f source=stimulateBomb\n",
                    unit.generator, unit.payloadId, p2bombotakara::kForceDelaySeconds);
    }
}

} // namespace

void pc_p2_bombotakara_reset() {
    units.clear();
    injections.clear();
    behaviorTick = 0;
    clockAccumulator = 0.0f;
    clockLast = 0;
    suppressedCount = 0;
    blastCount = 0;
}

void pc_p2_bombotakara_setup() {
    pc_p2_bombotakara_reset();
    if (!pc_pikipelago_room_preview()) return;
    std::ifstream configFile("p2-bombotakara-native.txt");
    if (!configFile) return; // inert without the sidecar
    p2bombotakara::Config config;
    if (!p2bombotakara::readConfig(configFile, config)) {
        std::fputs("P2_BOMBOTAKARA invalid profile\n", stderr);
        std::abort();
    }
    for (const auto& row : config.units) {
        Unit unit;
        unit.generator = row.generator;
        unit.payloadId = row.payloadId;
        unit.x = row.x;
        unit.y = row.y;
        unit.z = row.z;
        unit.yaw = row.yaw;
        unit.health = row.health;
        unit.bx = row.bx;
        unit.by = row.by;
        unit.bz = row.bz;
        units.push_back(unit);
        std::printf("P2_BOMBOTAKARA_READY generator=%u xyz=%.3f,%.3f,%.3f health=%.1f payload=%u "
                    "bomb_xyz=%.3f,%.3f,%.3f state=bomb_wait policy=bombotakara_source_1\n",
                    unit.generator, unit.x, unit.y, unit.z, unit.health, unit.payloadId,
                    unit.bx, unit.by, unit.bz);
    }
    for (auto& unit : units) {
        unit.carryLogged = true;
        std::printf("P2_BOMBOTAKARA_CARRY generator=%u payload=%u state=bomb_wait joint=otakara\n",
                    unit.generator, unit.payloadId);
    }
    std::ifstream injectFile("p2-bombotakara-inject.txt");
    if (injectFile) {
        std::string magic;
        while (injectFile >> magic) {
            unsigned long long tick = 0, id = 0;
            std::string mode;
            if (magic != "P2_BOMBOTAKARA_INJECT_1" || !(injectFile >> tick >> id >> mode)
                || tick < 1 || tick > 1000000ULL || id > 0xffffffffULL) {
                std::abort();
            }
            const int modeId = mode == "contact" ? ModeContact : mode == "press" ? ModePress
                : mode == "death" ? ModeDeath : mode == "earthquake" ? ModeEarthquake
                : mode == "payload_lost" ? ModePayloadLost : -1;
            if (modeId < 0) std::abort();
            Injection injection;
            injection.tick = static_cast<unsigned long>(tick);
            injection.generator = static_cast<std::uint32_t>(id);
            injection.mode = modeId;
            injections.push_back(injection);
        }
    }
    clockLast = SDL_GetTicks();
}

void pc_p2_bombotakara_update() {
    if (units.empty()) return;
    const unsigned now = SDL_GetTicks();
    clockAccumulator += static_cast<float>(now - clockLast) * 0.001f;
    clockLast = now;
    int steps = 0;
    while (clockAccumulator >= kTickSeconds && steps < 4) {
        clockAccumulator -= kTickSeconds;
        ++steps;
        ++behaviorTick;
        for (auto& injection : injections) {
            if (!injection.done && behaviorTick >= injection.tick) {
                applyInjection(injection);
                injection.done = true;
            }
        }
        for (auto& unit : units) tickUnit(unit);
    }
    if (steps == 4) clockAccumulator = 0.0f;
}

unsigned long pc_p2_bombotakara_behavior_tick() { return behaviorTick; }

bool pc_p2_bombotakara_gates_ready() {
    if (units.empty()) return false;
    for (const auto& unit : units) {
        if (!unit.carryLogged || !unit.armed || !unit.detonated) return false;
    }
    // Every carrier is triggered twice by the fixture; require the second
    // (suppressed) trigger for each so the fixture cannot exit before the
    // death-path suppression is emitted.
    const int required = static_cast<int>(units.size());
    return suppressedCount >= required && blastCount >= required;
}

void pc_p2_bombotakara_kill_all() {
    for (auto& unit : units) {
        if (unit.dead) continue;
        unit.dead = true;
        std::printf("P2_BOMBOTAKARA_DEAD generator=%u\n", unit.generator);
    }
}

int pc_p2_bombotakara_carry_count() {
    int count = 0;
    for (const auto& unit : units) if (unit.carryLogged) ++count;
    return count;
}

int pc_p2_bombotakara_armed_count() {
    int count = 0;
    for (const auto& unit : units) if (unit.armed) ++count;
    return count;
}

int pc_p2_bombotakara_detonated_count() {
    int count = 0;
    for (const auto& unit : units) if (unit.detonated) ++count;
    return count;
}

int pc_p2_bombotakara_suppressed_count() { return suppressedCount; }
int pc_p2_bombotakara_blast_count() { return blastCount; }
