// Pikmin 2 lane-22 fixed-hazard sidecar runtime (#170, child #447).
//
// Policy-driven, actor-local Hiba/GasHiba/ElecHiba simulation. This P1 port has
// no Hiba actor or gas/electric interaction class, so the hazard runs as a
// machine-checkable FSM (pc_p2_hiba_policy.h) and applies its element only
// through receivers this engine actually owns: InteractFire for Hiba. Gas and
// denki vulnerable targets are logged APPLY_BLOCKED (no engine interaction).
// Missing sidecar = inert; malformed sidecar = fail closed.
#include "pc_p2_hiba.h"
#include "pc_p2_hiba_policy.h"
#include "pc_bbft.h"
#include "pc_p2_purple.h"
#include "GlobalGameOptions.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Interactions.h"
#include <SDL.h>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <set>
#include <string>
#include <vector>

namespace {

const float kTickSeconds = 1.0f / 30.0f;
const float kEmitRadius  = 60.0f;
const float kFireDamage  = 1.0f;

struct Hazard {
    std::uint32_t generator = 0;
    int hazardId = 0;
    float x = 0.0f, y = 0.0f, z = 0.0f, yaw = 0.0f;
    float health = 0.0f;
    float waitTime = 0.0f, activeTime = 0.0f, attackStart = 0.0f, warningTime = 0.0f;
    float separation = 0.0f;
    int link = 0;
    bool linked = false;
    int state = 0;
    float timer = 0.0f;
    bool everActivated = false, everEmitted = false;
    bool emitLogged = false, deadLogged = false, linkedLogged = false;
    std::set<const void*> handled;
};

std::vector<Hazard> hazards;
unsigned long behaviorTick = 0;
float clockAccumulator = 0.0f;
unsigned clockLast = 0;
bool hitSeen = false, immuneSeen = false;

const char* hazardName(int hazardId) {
    switch (hazardId) {
    case p2dweevil::HibaId: return "Hiba";
    case p2dweevil::GasHibaId: return "GasHiba";
    case p2dweevil::ElecHibaId: return "ElecHiba";
    default: return "Unknown";
    }
}

const char* colourName(p2dweevil::Colour colour) {
    switch (colour) {
    case p2dweevil::Red: return "Red";
    case p2dweevil::Yellow: return "Yellow";
    case p2dweevil::Blue: return "Blue";
    case p2dweevil::Purple: return "Purple";
    case p2dweevil::White: return "White";
    case p2dweevil::Bulbmin: return "Bulbmin";
    case p2dweevil::ColourCount: break;
    }
    return "Unknown";
}

p2dweevil::Colour policyColour(const Piki* piki) {
    if (pc_p2_is_purple(piki)) return p2dweevil::Purple;
    switch (piki->mColor) {
    case Blue: return p2dweevil::Blue;
    case Red: return p2dweevil::Red;
    case Yellow: return p2dweevil::Yellow;
    default: return p2dweevil::Red;
    }
}

int deadState(int hazardId) { (void)hazardId; return 0; }
int waitState(int hazardId) { (void)hazardId; return 1; }
int attackState(int hazardId) {
    return hazardId == p2dweevil::ElecHibaId ? p2hiba::ElecHibaAttack : 2;
}

void enterDead(Hazard& hazard) {
    hazard.state = deadState(hazard.hazardId);
    if (!hazard.deadLogged) {
        hazard.deadLogged = true;
        std::printf("P2_HIBA_DEAD generator=%u hazard=%s\n", hazard.generator, hazardName(hazard.hazardId));
    }
}

void setAttack(Hazard& hazard, const char* from) {
    hazard.state = attackState(hazard.hazardId);
    hazard.timer = 0.0f;
    hazard.handled.clear();
    hazard.emitLogged = false;
    hazard.everActivated = true;
    std::printf("P2_HIBA_ACTIVATE generator=%u hazard=%s from=%s to=attack\n",
                hazard.generator, hazardName(hazard.hazardId), from);
}

void setWait(Hazard& hazard, const char* from) {
    hazard.state = waitState(hazard.hazardId);
    hazard.timer = 0.0f;
    hazard.emitLogged = false;
    std::printf("P2_HIBA_DEACTIVATE generator=%u hazard=%s from=%s to=wait\n",
                hazard.generator, hazardName(hazard.hazardId), from);
}

void setSign(Hazard& hazard) {
    hazard.state = p2hiba::ElecHibaSign;
    hazard.timer = 0.0f;
    std::printf("P2_HIBA_SIGN generator=%u hazard=ElecHiba\n", hazard.generator);
}

void emitScan(Hazard& hazard) {
    const bool firstEmission = !hazard.emitLogged;
    hazard.emitLogged = true;
    hazard.everEmitted = true;
    const p2dweevil::Stimulus stimulus = p2hiba::hazardStimulus(hazard.hazardId);
    if (firstEmission) std::printf("P2_HIBA_EMIT generator=%u hazard=%s stimulus=%s\n",
                hazard.generator, hazardName(hazard.hazardId), p2dweevil::stimulusName(stimulus));
    Creature* owner = nullptr;
    if (naviMgr && naviMgr->getNavi()) owner = static_cast<Creature*>(naviMgr->getNavi());
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* piki = static_cast<Piki*>(*it);
        if (!piki || !piki->isAlive()) continue;
        const Vector3f& pos = piki->getPosition();
        const float dx = pos.x - hazard.x, dy = pos.y - hazard.y, dz = pos.z - hazard.z;
        if (dx * dx + dy * dy + dz * dz > kEmitRadius * kEmitRadius) continue;
        if (!hazard.handled.insert(static_cast<const void*>(piki)).second) continue;
        const p2dweevil::Colour colour = policyColour(piki);
        if (p2dweevil::pikminImmune(stimulus, colour, false)) {
            immuneSeen = true;
            std::printf("P2_HIBA_PASS generator=%u hazard=%s stimulus=%s colour=%s immune=1 applied=0\n",
                        hazard.generator, hazardName(hazard.hazardId), p2dweevil::stimulusName(stimulus),
                        colourName(colour));
            continue;
        }
        if (stimulus == p2dweevil::StimFire) {
            InteractFire fire(owner, kFireDamage);
            const bool applied = piki->stimulate(fire);
            if (!applied) { hazard.handled.erase(piki); continue; }
            hitSeen = true;
            std::printf("P2_HIBA_HIT generator=%u hazard=%s stimulus=InteractFire colour=%s immune=0 "
                        "applied=1 damage=%.1f\n",
                        hazard.generator, hazardName(hazard.hazardId), colourName(colour), kFireDamage);
        } else {
            std::printf("P2_HIBA_APPLY_BLOCKED generator=%u hazard=%s stimulus=%s colour=%s immune=0 "
                        "applied=0 reason=no_engine_interaction\n",
                        hazard.generator, hazardName(hazard.hazardId), p2dweevil::stimulusName(stimulus),
                        colourName(colour));
        }
    }
}

void tickHazard(Hazard& hazard) {
    if (hazard.state == deadState(hazard.hazardId)) return;
    if (hazard.health <= 0.0f) {
        enterDead(hazard);
        return;
    }
    if (hazard.linked) {
        if (!hazard.linkedLogged) {
            hazard.linkedLogged = true;
            std::printf("P2_HIBA_LINKED generator=%u hazard=GasHiba owner=%s living=0\n",
                        hazard.generator,
                        p2hiba::linkOwnerName(static_cast<p2hiba::LinkOwner>(hazard.link)));
        }
        return;
    }
    hazard.timer += kTickSeconds;
    if (hazard.hazardId == p2dweevil::ElecHibaId) {
        const p2hiba::ElecStep step
            = p2hiba::elechibaAdvance(static_cast<p2hiba::ElecHibaState>(hazard.state), hazard.health,
                                      hazard.timer, hazard.waitTime, hazard.warningTime, hazard.activeTime, false);
        if (step.next == p2hiba::ElecHibaDead) {
            enterDead(hazard);
            return;
        }
        if (step.emits) {
            if (hazard.state != p2hiba::ElecHibaAttack) setAttack(hazard, "sign");
            emitScan(hazard);
        } else if (step.next == p2hiba::ElecHibaWait && hazard.state == p2hiba::ElecHibaAttack) {
            setWait(hazard, "attack");
        } else if (step.next == p2hiba::ElecHibaSign && hazard.state == p2hiba::ElecHibaWait) {
            setSign(hazard);
        }
        return;
    }
    if (hazard.state == waitState(hazard.hazardId)) {
        const p2dweevil::HazardAction action
            = p2dweevil::hazardActivate(hazard.hazardId, hazard.health, hazard.timer, hazard.waitTime);
        if (action == p2dweevil::HazardDead) {
            enterDead(hazard);
        } else if (action == p2dweevil::HazardAttack) {
            setAttack(hazard, "wait");
        }
        return;
    }
    // Attack.
    if (hazard.hazardId == p2dweevil::HibaId) {
        if (p2hiba::hibaEmit(p2hiba::HibaAttack, hazard.health, hazard.timer, hazard.activeTime)) {
            emitScan(hazard);
        } else {
            setWait(hazard, "attack");
        }
        return;
    }
    // GasHiba: the attack-start gate delays emission; the finish condition only
    // fires with a positive wait time (retail disc wait is 0, so it never
    // self-finishes and is torn down by the fixture).
    if (hazard.timer < hazard.attackStart) return;
    if (p2hiba::gashibaEmit(p2hiba::GasHibaAttack, hazard.timer, hazard.timer, hazard.attackStart,
                            hazard.activeTime, hazard.waitTime)) {
        emitScan(hazard);
    } else {
        setWait(hazard, "attack");
    }
}

} // namespace

void pc_p2_hiba_reset() {
    hazards.clear();
    behaviorTick = 0;
    clockAccumulator = 0.0f;
    clockLast = 0;
    hitSeen = false;
    immuneSeen = false;
}

void pc_p2_hiba_setup() {
    pc_p2_hiba_reset();
    if (!pc_pikipelago_room_preview()) return;
    std::ifstream configFile("p2-hiba-native.txt");
    if (!configFile) return; // inert without the sidecar
    p2hiba::Config config;
    if (!p2hiba::readConfig(configFile, config)) {
        std::fputs("P2_HIBA invalid profile\n", stderr);
        std::abort();
    }
    for (const auto& row : config.hazards) {
        Hazard hazard;
        hazard.generator  = row.generator;
        hazard.hazardId   = row.hazardId;
        hazard.x          = row.x;
        hazard.y          = row.y;
        hazard.z          = row.z;
        hazard.yaw        = row.yaw;
        hazard.health     = row.health;
        const p2hiba::HazardTiming disc = p2hiba::discTiming(row.hazardId);
        hazard.waitTime     = row.waitOverride >= 0.0f ? row.waitOverride : disc.wait;
        hazard.activeTime   = disc.active;
        hazard.attackStart  = disc.attackStart;
        hazard.warningTime  = disc.warning;
        hazard.separation   = row.separation;
        hazard.link         = row.link;
        hazard.state        = waitState(row.hazardId);
        hazard.linked       = row.hazardId == p2dweevil::GasHibaId && row.link != 0;
        if (row.hazardId == p2dweevil::ElecHibaId && row.separation > 0.0f) {
            const std::pair<float, float> nodes = p2hiba::elechibaNodePositions(row.x, row.separation);
            std::printf("P2_HIBA_NODES generator=%u hazard=ElecHiba center=%.3f negative=%.3f positive=%.3f\n",
                        row.generator, row.x, nodes.first, nodes.second);
        }
        hazards.push_back(hazard);
        std::printf("P2_HIBA_READY generator=%u hazard=%s xyz=%.3f,%.3f,%.3f wait=%.2f active=%.2f "
                    "separation=%.2f link=%s policy=hiba_source_1\n",
                    hazard.generator, hazardName(hazard.hazardId), hazard.x, hazard.y, hazard.z,
                    hazard.waitTime, hazard.activeTime, hazard.separation,
                    p2hiba::linkOwnerName(static_cast<p2hiba::LinkOwner>(hazard.link)));
    }
    clockLast = SDL_GetTicks();
}

void pc_p2_hiba_update() {
    if (hazards.empty()) return;
    const unsigned now = SDL_GetTicks();
    clockAccumulator += static_cast<float>(now - clockLast) * 0.001f;
    clockLast = now;
    int steps = 0;
    while (clockAccumulator >= kTickSeconds && steps < 4) {
        clockAccumulator -= kTickSeconds;
        ++steps;
        ++behaviorTick;
        for (auto& hazard : hazards) tickHazard(hazard);
    }
    if (steps == 4) clockAccumulator = 0.0f;
}

unsigned long pc_p2_hiba_behavior_tick() { return behaviorTick; }

bool pc_p2_hiba_gates_ready() {
    if (hazards.empty() || !hitSeen || !immuneSeen) return false;
    for (const auto& hazard : hazards) {
        if (!hazard.everActivated || !hazard.everEmitted) return false;
    }
    return true;
}

void pc_p2_hiba_kill_all() {
    for (auto& hazard : hazards) {
        if (hazard.state == deadState(hazard.hazardId)) continue;
        hazard.health = 0.0f;
        enterDead(hazard);
    }
}

int pc_p2_hiba_activated() {
    int count = 0;
    for (const auto& hazard : hazards) if (hazard.everActivated) ++count;
    return count;
}

int pc_p2_hiba_emitted() {
    int count = 0;
    for (const auto& hazard : hazards) if (hazard.everEmitted) ++count;
    return count;
}

bool pc_p2_hiba_hit_seen() { return hitSeen; }
bool pc_p2_hiba_immune_seen() { return immuneSeen; }
