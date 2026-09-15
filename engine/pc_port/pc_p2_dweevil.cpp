// Pikmin 2 lane-22 dweevil family sidecar runtime (#170, child #447).
//
// Policy-driven, actor-local treasure capture/carry/drop for the four
// elemental dweevils. There is no P2 dweevil actor in this P1 engine and this
// slice deliberately does not bind an engine TEKI_Chappy vehicle or mutate
// Pellet ownership: it consumes the delivered Python policy semantics over a
// sidecar-staged treasure set, runs the shared OtakaraBase state subset on a
// bounded 30 Hz clock, and proves the death/interruption drop fires exactly
// once. Missing sidecar = inert; malformed sidecar = fail closed.
#include "pc_p2_dweevil.h"
#include "pc_p2_dweevil_policy.h"
#include "pc_bbft.h"
#include <SDL.h>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>

namespace {

const float kTickSeconds       = 1.0f / 30.0f;
const float kTerritoryRadius   = 200.0f; // fp09 home territory
const float kPickRadius        = 30.0f;  // lane approximation of the capture reach
const float kCarryStepPerTick  = 0.5f;   // lane approximation of item-move speed

enum InjectMode { ModeKill = 0, ModeInterrupt = 1, ModeReplay = 2 };

struct Unit {
    std::uint32_t generator = 0;
    int species             = 0;
    float x = 0.0f, y = 0.0f, z = 0.0f, yaw = 0.0f;
    float homeX = 0.0f, homeZ = 0.0f;
    float otakaraLife = 0.0f;
    float treasureHealth = 0.0f;
    std::uint32_t carriedId = 0;
    int state = p2dweevil::Wait;
    bool carrying = false;
    bool droppedThisCapture = false;
    bool carryLogged = false;
    int drops = 0;
};

struct Treasure {
    std::uint32_t id = 0;
    float x = 0.0f, y = 0.0f, z = 0.0f;
    bool alive = false;
    bool pickable = false;
    bool captured = false;
};

struct Injection {
    unsigned long tick = 0;
    std::uint32_t generator = 0;
    int mode = ModeKill;
    bool done = false;
};

std::vector<Unit> units;
std::vector<Treasure> treasures;
std::vector<Injection> injections;
unsigned long behaviorTick = 0;
float clockAccumulator = 0.0f;
unsigned clockLast = 0;

Treasure* findTreasure(std::uint32_t id) {
    for (auto& treasure : treasures)
        if (treasure.id == id) return &treasure;
    return nullptr;
}

float horizontalDistance(const Unit& unit, const Treasure& treasure) {
    const float dx = treasure.x - unit.x;
    const float dz = treasure.z - unit.z;
    return std::sqrt(dx * dx + dz * dz);
}

void doDrop(Unit& unit, p2dweevil::DropReason reason) {
    const p2dweevil::DropResult result = p2dweevil::drop(unit.carrying, unit.droppedThisCapture, reason);
    if (result.dropped) {
        Treasure* treasure = findTreasure(unit.carriedId);
        if (treasure) {
            treasure->captured = false;
            treasure->x        = unit.x;
            treasure->y        = unit.y;
            treasure->z        = unit.z;
        }
        unit.carrying            = false;
        unit.droppedThisCapture  = true;
        unit.state               = p2dweevil::ItemDrop;
        ++unit.drops;
        std::printf("P2_DWEEVIL_DROP generator=%u treasure=%u reason=%s dropped=1 exactly_once=1 total_drops=%d\n",
                    unit.generator, unit.carriedId,
                    reason == p2dweevil::DropInterruption ? "interruption" : reason == p2dweevil::DropStone
                        ? "stone" : reason == p2dweevil::DropEarthquake ? "earthquake" : "death",
                    unit.drops);
    } else if (unit.droppedThisCapture) {
        std::printf("P2_DWEEVIL_DROP_SUPPRESSED generator=%u treasure=%u reason=%s dropped=0 already_dropped=1\n",
                    unit.generator, unit.carriedId,
                    reason == p2dweevil::DropInterruption ? "interruption" : reason == p2dweevil::DropStone
                        ? "stone" : reason == p2dweevil::DropEarthquake ? "earthquake" : "death");
    }
}

void applyInjection(Injection& injection) {
    for (auto& unit : units) {
        if (injection.generator && unit.generator != injection.generator) continue;
        if (injection.mode == ModeKill) {
            if (unit.state == p2dweevil::Dead) break;
            unit.state = p2dweevil::Dead;
            std::printf("P2_DWEEVIL_DEATH generator=%u tick=%lu fixture=1\n", unit.generator, behaviorTick);
            doDrop(unit, p2dweevil::DropDeath);
        } else if (injection.mode == ModeInterrupt) {
            if (unit.state == p2dweevil::Dead) break;
            std::printf("P2_DWEEVIL_INTERRUPT generator=%u tick=%lu fixture=1\n", unit.generator, behaviorTick);
            doDrop(unit, p2dweevil::DropInterruption);
        } else {
            std::printf("P2_DWEEVIL_REPLAY generator=%u tick=%lu fixture=1\n", unit.generator, behaviorTick);
            doDrop(unit, p2dweevil::DropDeath);
        }
        break;
    }
}

void tickUnit(Unit& unit) {
    if (unit.state == p2dweevil::Dead) {
        if (unit.carrying) doDrop(unit, p2dweevil::DropDeath);
        return;
    }
    if (unit.carrying) {
        Treasure* treasure = findTreasure(unit.carriedId);
        if (!treasure || !treasure->alive || !treasure->pickable) {
            doDrop(unit, p2dweevil::DropInterruption);
            return;
        }
        // Carry/follow: the captured treasure tracks the dweevil homeward.
        const float dx = unit.homeX - unit.x;
        const float dz = unit.homeZ - unit.z;
        const float distance = std::sqrt(dx * dx + dz * dz);
        if (distance > kCarryStepPerTick) {
            unit.x += dx / distance * kCarryStepPerTick;
            unit.z += dz / distance * kCarryStepPerTick;
        }
        treasure->x = unit.x;
        treasure->y = unit.y;
        treasure->z = unit.z;
        if (!unit.carryLogged) {
            unit.carryLogged = true;
            std::printf("P2_DWEEVIL_CARRY generator=%u treasure=%u state=item_move otakara_health=%.1f\n",
                        unit.generator, unit.carriedId, unit.treasureHealth);
        }
        return;
    }
    Treasure* best = nullptr;
    float bestDistance = 0.0f;
    for (auto& treasure : treasures) {
        const float distance = horizontalDistance(unit, treasure);
        const bool withinTerritory = distance <= kTerritoryRadius;
        if (!p2dweevil::theftDecision(treasure.alive, treasure.pickable, treasure.captured,
                                      withinTerritory, false)) {
            continue;
        }
        if (!best || distance < bestDistance) {
            best         = &treasure;
            bestDistance = distance;
        }
    }
    if (!best || bestDistance > kPickRadius) return;
    unit.carriedId          = best->id;
    unit.carrying           = true;
    unit.droppedThisCapture = false;
    unit.carryLogged        = false;
    unit.treasureHealth     = p2dweevil::captureHealth(unit.otakaraLife);
    unit.state              = p2dweevil::ItemWait;
    best->captured          = true;
    std::printf("P2_DWEEVIL_CAPTURE generator=%u species=%s treasure=%u otakara_life=%.1f health=%.1f\n",
                unit.generator, p2dweevil::speciesName(unit.species), best->id, unit.otakaraLife,
                unit.treasureHealth);
}

} // namespace

void pc_p2_dweevil_reset() {
    units.clear();
    treasures.clear();
    injections.clear();
    behaviorTick     = 0;
    clockAccumulator = 0.0f;
    clockLast        = 0;
}

void pc_p2_dweevil_setup() {
    pc_p2_dweevil_reset();
    if (!pc_pikipelago_room_preview()) return;
    std::ifstream configFile("p2-dweevil-native.txt");
    if (!configFile) return; // inert without the sidecar
    p2dweevil::Config config;
    if (!p2dweevil::readConfig(configFile, config)) {
        std::fputs("P2_DWEEVIL invalid profile\n", stderr);
        std::abort();
    }
    for (const auto& row : config.units) {
        Unit unit;
        unit.generator   = row.generator;
        unit.species     = row.species;
        unit.x           = row.x;
        unit.y           = row.y;
        unit.z           = row.z;
        unit.yaw         = row.yaw;
        unit.homeX       = row.x;
        unit.homeZ       = row.z;
        unit.otakaraLife = row.otakaraLife;
        units.push_back(unit);
    }
    for (const auto& row : config.treasures) {
        Treasure treasure;
        treasure.id       = row.id;
        treasure.x        = row.x;
        treasure.y        = row.y;
        treasure.z        = row.z;
        treasure.alive    = row.alive;
        treasure.pickable = row.pickable;
        treasure.captured = row.captured;
        treasures.push_back(treasure);
    }
    std::ifstream injectFile("p2-dweevil-inject.txt");
    if (injectFile) {
        std::string magic;
        while (injectFile >> magic) {
            unsigned long long tick = 0, id = 0;
            std::string mode;
            if (magic != "P2_DWEEVIL_INJECT_1" || !(injectFile >> tick >> id >> mode)
                || tick < 1 || tick > 1000000ULL || id > 0xffffffffULL) {
                std::abort();
            }
            const int modeId = mode == "kill" ? ModeKill : mode == "interrupt" ? ModeInterrupt
                : mode == "replay" ? ModeReplay : -1;
            if (modeId < 0) std::abort();
            Injection injection;
            injection.tick      = static_cast<unsigned long>(tick);
            injection.generator = static_cast<std::uint32_t>(id);
            injection.mode      = modeId;
            injections.push_back(injection);
        }
    }
    for (const auto& unit : units) {
        std::printf("P2_DWEEVIL_READY generator=%u species=%s xyz=%.3f,%.3f,%.3f yaw=%.3f "
                    "otakara_life=%.1f policy=dweevil_source_1\n",
                    unit.generator, p2dweevil::speciesName(unit.species), unit.x, unit.y, unit.z, unit.yaw,
                    unit.otakaraLife);
    }
    for (const auto& treasure : treasures) {
        std::printf("P2_DWEEVIL_TREASURE id=%u xyz=%.3f,%.3f,%.3f alive=%d pickable=%d captured=%d\n",
                    treasure.id, treasure.x, treasure.y, treasure.z, int(treasure.alive),
                    int(treasure.pickable), int(treasure.captured));
    }
    clockLast = SDL_GetTicks();
}

void pc_p2_dweevil_update() {
    if (units.empty() && treasures.empty()) return;
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

unsigned long pc_p2_dweevil_behavior_tick() { return behaviorTick; }
