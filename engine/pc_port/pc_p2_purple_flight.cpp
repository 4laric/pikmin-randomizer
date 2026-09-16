#include "pc_p2_purple_flight.h"
#include "pc_p2_purple_feedback.h"
#include "pc_p2_purple_impact.h"
#include "pc_p2_purple.h"
#include "Piki.h"
#include "teki.h"
#include <cmath>
#include <cstdlib>
#include <cstdio>
#include <filesystem>
#include <string>
#include <unordered_map>
#include <vector>

namespace {
struct FlightState {
    PcP2PurpleFlightPhase phase = PcP2PurpleFlightPhase::None;
    float elapsed = 0.0f;
    float motionElapsed = 0.0f;
    bool hadIgnoreGravity = false;
    bool hadPriorityFaceDirection = false;
};

bool enabled = false;
std::unordered_map<Piki*, FlightState> states;

void beginDescent(Piki* piki, float gravity)
{
    auto found = states.find(piki);
    if (found != states.end() && !found->second.hadIgnoreGravity) {
        piki->resetCreatureFlag(CF_IgnoreGravity);
    }
    piki->setCreatureFlag(CF_UsePriorityFaceDir);
    piki->mVelocity.set(0.0f, -gravity * 0.5f, 0.0f);
    BTeki* closest = nullptr;
    float closestDistance = 12800.0f;
    Iterator enemies(tekiMgr);
    CI_LOOP(enemies) {
        BTeki* enemy = static_cast<BTeki*>(*enemies);
        // Native has no P2 isLivingThing predicate. Organic is the bounded adapter
        // that excludes bombs, vents, rocks, and other nonliving Teki props.
        if (!enemy || !enemy->isAlive() || !enemy->isOrganic()) continue;
        const Vector3f separation = enemy->mSRT.t - piki->mSRT.t;
        const float distance = separation.length();
        if (!std::isfinite(enemy->mCollisionRadius) || enemy->mCollisionRadius < 0.0f) continue;
        const float searchRadius = 50.0f + enemy->mCollisionRadius;
        if (distance <= searchRadius && distance < closestDistance) {
            closest = enemy;
            closestDistance = distance;
        }
    }
    if (closest) {
        Vector3f direction = closest->mSRT.t - piki->mSRT.t;
        const float horizontalDistance = std::sqrt(direction.x * direction.x + direction.z * direction.z);
        if (horizontalDistance > 0.0f) {
            piki->mVelocity.x = direction.x * 120.0f / horizontalDistance;
            piki->mVelocity.z = direction.z * 120.0f / horizontalDistance;
        }
    }
    piki->mTargetVelocity = piki->mVelocity;
}
}

void pc_p2_purple_flight_reset()
{
    std::vector<Piki*> active;
    active.reserve(states.size());
    for (const auto& entry : states) active.push_back(entry.first);
    for (Piki* piki : active) pc_p2_purple_flight_cancel(piki);
    pc_p2_purple_feedback_reset();
    enabled = false;
}

void pc_p2_purple_flight_setup()
{
    pc_p2_purple_flight_reset();
    if (!std::filesystem::exists("p2-purple-flight.txt")) return;
    FILE* file = std::fopen("p2-purple-flight.txt", "r");
    char version[32] = {};
    char trailing = 0;
    const bool valid = file && std::fscanf(file, "%31s", version) == 1
        && std::fscanf(file, " %c", &trailing) != 1;
    if (file) std::fclose(file);
    if (!valid || std::string(version) != "P2_PURPLE_FLIGHT_1") {
        std::fprintf(stderr, "Invalid P2 Purple flight config\n");
        std::abort();
    }
    if (!pc_p2_purple_impact_enabled()) {
        std::fprintf(stderr, "P2 Purple flight requires enabled impact profile\n");
        std::abort();
    }
    enabled = pc_p2_purples_enabled();
    std::printf("P2_PURPLE_FLIGHT_SETUP enabled=%d pause=0.25 recovery=0.30 homing=120 radius=50\n", enabled ? 1 : 0);
}

bool pc_p2_purple_flight_enabled() { return enabled; }

void pc_p2_purple_flight_arm(Piki* piki)
{
    if (!enabled || !piki || !piki->isAlive() || !pc_p2_is_purple(piki)) return;
    pc_p2_purple_flight_cancel(piki);
    states[piki] = { PcP2PurpleFlightPhase::Ascent, 0.0f, 0.0f,
        piki->isCreatureFlag(CF_IgnoreGravity), piki->isCreatureFlag(CF_UsePriorityFaceDir) };
}

bool pc_p2_purple_flight_update(Piki* piki, float deltaTime, float gravity)
{
    auto found = states.find(piki);
    if (found == states.end()) return false;
    if (!std::isfinite(deltaTime) || deltaTime <= 0.0f || !std::isfinite(gravity) || gravity <= 0.0f) return false;
    FlightState& state = found->second;
    state.elapsed += deltaTime;
    state.motionElapsed += deltaTime;
    pc_p2_purple_feedback_update(piki, deltaTime);
    if (state.phase == PcP2PurpleFlightPhase::Ascent && piki->mVelocity.y <= 0.0f) {
        state.phase = PcP2PurpleFlightPhase::EntryPause;
        state.elapsed = 0.0f;
        piki->mVelocity.set(0.0f, 0.0f, 0.0f);
        piki->mTargetVelocity = piki->mVelocity;
        piki->setCreatureFlag(CF_IgnoreGravity);
        pc_p2_purple_feedback_entry(piki);
    } else if (state.phase == PcP2PurpleFlightPhase::EntryPause) {
        piki->mVelocity.set(0.0f, 0.0f, 0.0f);
        piki->mTargetVelocity = piki->mVelocity;
        if (state.elapsed >= 0.25f) {
            const bool hadIgnoreGravity = state.hadIgnoreGravity;
            const bool hadPriorityFaceDirection = state.hadPriorityFaceDirection;
            state = { PcP2PurpleFlightPhase::Descent, 0.0f, 0.0f,
                hadIgnoreGravity, hadPriorityFaceDirection };
            beginDescent(piki, gravity);
        }
    } else if (state.phase == PcP2PurpleFlightPhase::Descent) {
        piki->mFaceDirection = roundAng(piki->mFaceDirection + deltaTime * PI / 0.2f);
    } else if (state.phase == PcP2PurpleFlightPhase::Recovery) {
        piki->mTargetVelocity.set(0.0f, 0.0f, 0.0f);
        if (state.elapsed >= 0.3f) return true;
    }
    return false;
}

bool pc_p2_purple_flight_land(Piki* piki, bool enemyContact)
{
    auto found = states.find(piki);
    if (found == states.end()
        || (found->second.phase != PcP2PurpleFlightPhase::EntryPause
            && found->second.phase != PcP2PurpleFlightPhase::Descent)) return false;
    found->second.phase = PcP2PurpleFlightPhase::Recovery;
    found->second.elapsed = 0.0f;
    piki->mTargetVelocity.set(0.0f, 0.0f, 0.0f);
    pc_p2_purple_feedback_land(piki, enemyContact);
    return true;
}

void pc_p2_purple_flight_contact(Piki* piki, bool enemyContact)
{
    if (pc_p2_purple_flight_active(piki)) pc_p2_purple_feedback_land(piki, enemyContact);
}

void pc_p2_purple_flight_cancel(Piki* piki)
{
    if (!piki) return;
    auto found = states.find(piki);
    if (found == states.end()) return;
    if (!found->second.hadIgnoreGravity) piki->resetCreatureFlag(CF_IgnoreGravity);
    if (!found->second.hadPriorityFaceDirection) piki->resetCreatureFlag(CF_UsePriorityFaceDir);
    states.erase(found);
    pc_p2_purple_feedback_cancel(piki);
}

bool pc_p2_purple_flight_active(const Piki* piki) { return states.count(const_cast<Piki*>(piki)) != 0; }

PcP2PurpleFlightSample pc_p2_purple_flight_sample(const Piki* piki)
{
    auto found = states.find(const_cast<Piki*>(piki));
    return found == states.end() ? PcP2PurpleFlightSample{}
                                 : PcP2PurpleFlightSample{ found->second.phase, found->second.elapsed, found->second.motionElapsed };
}
