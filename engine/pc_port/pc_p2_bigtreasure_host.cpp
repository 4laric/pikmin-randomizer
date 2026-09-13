#include "pc_p2_bigtreasure_host.h"

#include <cmath>
#include <fstream>
#include <sstream>
#include <string>

namespace {
constexpr float kCoordinateLimit = 100000.0f;
constexpr std::size_t kMaxProfileBytes = 4096;

bool finiteBounded(float value)
{
    return std::isfinite(value) && std::fabs(value) <= kCoordinateLimit;
}

bool finiteBounded(const P2BigTreasureVec3& value)
{
    return finiteBounded(value.x) && finiteBounded(value.y) && finiteBounded(value.z);
}

bool exhausted(std::istringstream& line)
{
    std::string extra;
    return !(line >> extra);
}

bool nextLine(std::ifstream& input, std::string& line)
{
    if (!std::getline(input, line)) {
        return false;
    }
    if (!line.empty() && line.back() == '\r') {
        line.pop_back();
    }
    return true;
}
} // namespace

bool p2_bigtreasure_host_parse(const char* profilePath, P2BigTreasureHostPlacement& out)
{
    if (!profilePath || !*profilePath) {
        return false;
    }
    std::ifstream input(profilePath);
    if (!input) {
        return false;
    }
    input.seekg(0, std::ios::end);
    if (input.tellg() < 0 || input.tellg() > static_cast<std::streamoff>(kMaxProfileBytes)) {
        return false;
    }
    input.seekg(0);

    P2BigTreasureHostPlacement parsed;
    std::string line;
    if (!nextLine(input, line) || line != "P2_BIGTREASURE_HOST_1") {
        return false;
    }
    {
        if (!nextLine(input, line)) {
            return false;
        }
        std::istringstream values(line);
        std::string key;
        if (!(values >> key >> parsed.owner.x >> parsed.owner.y >> parsed.owner.z
              >> parsed.ownerYaw) || key != "placement" || !exhausted(values)
            || !finiteBounded(parsed.owner) || !std::isfinite(parsed.ownerYaw)) {
            return false;
        }
    }
    {
        if (!nextLine(input, line)) {
            return false;
        }
        std::istringstream values(line);
        std::string key;
        if (!(values >> key >> parsed.target.x >> parsed.target.y >> parsed.target.z)
            || key != "target" || !exhausted(values) || !finiteBounded(parsed.target)) {
            return false;
        }
    }
    {
        if (!nextLine(input, line)) {
            return false;
        }
        std::istringstream values(line);
        std::string key;
        if (!(values >> key >> parsed.initialTimer) || key != "timer" || !exhausted(values)
            || !std::isfinite(parsed.initialTimer) || parsed.initialTimer < 0.0f
            || parsed.initialTimer > 2.0f) {
            return false;
        }
    }
    {
        if (!nextLine(input, line)) {
            return false;
        }
        std::istringstream values(line);
        std::string key;
        if (!(values >> key >> parsed.maxDischarge) || key != "discharge" || !exhausted(values)
            || parsed.maxDischarge < 0
            || parsed.maxDischarge > P2BigTreasureAttackPools::kElecCapacity - 1) {
            return false;
        }
    }
    out = parsed;
    return true;
}

bool p2_bigtreasure_host_setup(const char* profilePath, P2BigTreasureHostSeam& seam)
{
    p2_bigtreasure_host_reset(seam);
    P2BigTreasureHostPlacement placement;
    if (!p2_bigtreasure_host_parse(profilePath, placement)) {
        return false;
    }
    seam.placement = placement;
    // Full retail loadout: 4 weapon pellets + Louie captured on the
    // otakara_* joints at full health (5 captured pellets).
    for (int weapon = 0; weapon < P2BTWEAPON_Count; ++weapon) {
        seam.ownership.attachWeapon(weapon);
    }
    seam.ownership.attachLouie();
    seam.director.pacer.reset(placement.initialTimer);
    if (!seam.director.pools.setElecMaxDischarge(placement.maxDischarge)) {
        p2_bigtreasure_host_reset(seam);
        return false;
    }
    seam.active = true;
    return true;
}

int p2_bigtreasure_host_tick_entry(P2BigTreasureHostSeam& seam, float delta,
                                   bool unstuckOutsiderNearby, float pickThreshold)
{
    if (!seam.active || !std::isfinite(delta) || delta <= 0.0f) {
        return -1;
    }
    ++seam.ticks;
    const float dx = seam.placement.target.x - seam.placement.owner.x;
    const float dz = seam.placement.target.z - seam.placement.owner.z;
    const float box = P2BigTreasureAttackPacer::kBoxHalfExtent;
    const bool targetInBox = std::fabs(dx) <= box && std::fabs(dz) <= box;
    const int started = seam.director.tickEntry(seam.ownership, delta, targetInBox,
                                                unstuckOutsiderNearby, pickThreshold);
    if (started >= 0) {
        ++seam.attacksStarted;
    }
    return started;
}

std::size_t p2_bigtreasure_host_defeat(P2BigTreasureHostSeam& seam,
                                       P2BigTreasureDropEvent* outDrops, std::size_t maxDrops)
{
    if (!seam.active) {
        return 0;
    }
    // Deterministic order: pooled attack nodes (including in-flight water
    // bubbles, no hit events) recycle before any captured pellet releases.
    seam.director.defeat();
    P2BigTreasureDropEvent local[P2BTWEAPON_Count + 1];
    P2BigTreasureDropEvent* sink = outDrops ? outDrops : local;
    const std::size_t capacity = outDrops ? maxDrops : (P2BTWEAPON_Count + 1);
    const std::size_t events = seam.ownership.defeat(sink, capacity);
    seam.defeatEvents += events;
    seam.active = false;
    return events;
}

void p2_bigtreasure_host_reset(P2BigTreasureHostSeam& seam)
{
    p2_bigtreasure_host_defeat(seam, nullptr, 0);
    seam.ownership  = P2BigTreasureOwnership();
    seam.director   = P2BigTreasureAttackDirector();
    seam.placement  = P2BigTreasureHostPlacement();
    seam.ticks          = 0;
    seam.attacksStarted = 0;
    seam.defeatEvents   = 0;
    seam.active         = false;
}
