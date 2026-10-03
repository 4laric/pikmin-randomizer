#pragma once
#include "pc_p2_egg_hazard.h"
#include <cstdint>
#include <map>
#include <string>
#include <vector>
#include <utility>

namespace p2originalresource {
// Original generator identity, never an AP pool identity. Epoch/activation
// distinguish a genuine source respawn from scene teardown/re-entry.
struct SourceIdentity {
    std::string fingerprint;
    std::uint32_t uid = 0, ordinal = 0;
    std::uint64_t epoch = 0, activation = 0;
    bool operator<(const SourceIdentity&) const;
    bool operator==(const SourceIdentity&) const;
};
enum class EmitterKind : unsigned { EggMitite = 68, PlantSpectralid = 77 };
struct EmissionIdentity {
    EmitterKind kind = EmitterKind::PlantSpectralid;
    std::uint64_t emissionOrdinal = 0;
    unsigned member = 0;
    bool operator<(const EmissionIdentity&) const;
    bool operator==(const EmissionIdentity&) const;
};
struct ChildIdentity {
    SourceIdentity source;
    unsigned slot = 0; // group=0; Mitite fallback=1; double nectar=0,1
    // Empty for direct Egg children. A typed emitted-member step retains the real
    // parent incarnation and authored member index instead of inventing a UID
    // or borrowing an unrelated source generator ordinal.
    std::vector<EmissionIdentity> ancestry;
    ChildIdentity() = default;
    ChildIdentity(SourceIdentity root,unsigned childSlot,std::vector<EmissionIdentity> path={})
      :source(std::move(root)),slot(childSlot),ancestry(std::move(path)){}
    bool operator<(const ChildIdentity&) const;
    bool operator==(const ChildIdentity&) const;
};
bool validChildIdentity(const ChildIdentity&);
enum class HoneyKind { Nectar, Spicy, Bitter };
enum class ChildKind { PelletOne, PelletFive, Nectar, Spicy, Bitter, MititeGroup };
struct ChildOutcome {
    ChildIdentity identity;
    ChildKind kind = ChildKind::Nectar;
    P2EggVec3 position, velocity;
    int pelletColor = 0, mititeCount = 0;
    float facing = 0;
    bool attempted = false, born = false, consumed = false;
};
struct ContentsRecord {
    SourceIdentity source;
    P2EggDropType type = P2EggDropType::SingleNectar;
    bool complete = false;
    std::vector<ChildOutcome> children;
};
// Preflight the union of physically reachable outcomes from the verified
// source parameters. Live spray-made flags may change after admission, so both
// the spray and its nectar gate fallback remain required. Pellet types are
// reachable only through the literal forced-type source control.
struct ContentsRequirements {
    bool pelletOne=false,pelletFive=false,nectar=false,spicy=false,bitter=false,mitites=false;
};
bool requirements(const P2EggConfig&,ContentsRequirements&,std::string& error);
// Birth callbacks perform the real manager birth/init/position/velocity path.
// In particular, SUCCESSFUL birthHoney must execute ItemHoney::init(nullptr),
// whose onInit draws from the same source randFloat before the caller overwrites
// mHoneyType. Do not substitute a typed init arg or skip that draw. Failed
// manager births do not init and consume no such draw. This preserves RNG
// interleaving across the two DoubleNectar births (itemHoney.cpp 0x801D3758).
// They must bind the supplied child identity to the live native object. A group
// callback must execute real TamagoMushi createGroup(10), not a proxy or nectar
// substitution. False means actual source birth failure, recorded permanently.
class Engine {
public:
    virtual ~Engine() = default;
    virtual float randFloat() noexcept = 0;
    virtual int randInt(int count) noexcept = 0;
    virtual bool sprayMade(HoneyKind) noexcept = 0;
    virtual bool mititeManagerAvailable() noexcept = 0;
    virtual bool birthPellet(const ChildOutcome&) noexcept = 0;
    virtual bool birthHoney(HoneyKind, const ChildOutcome&) noexcept = 0;
    virtual bool birthMititeGroup(const ChildOutcome&) noexcept = 0;
};
class EggContents {
public:
    // Call only on actual Egg StateWait destruction. Source genItem rolls even
    // with a forced type. Duplicate/re-entry calls never reroll or retry births.
    // A reentrant call before completion returns false with a pending error.
    bool generate(const SourceIdentity&, const P2EggConfig&, const P2EggVec3&,
                  Engine&, ContentsRecord&, std::string& error);
    // Read-only actual producer record for synchronous scoped consumers. Pending
    // birth has attempted=true/born=false; completion follows the callback.
    // Never retain this pointer across restore or owner destruction.
    const ContentsRecord* find(const SourceIdentity&) const;
    std::vector<ContentsRecord> snapshot() const;
    bool restore(const std::vector<ContentsRecord>&, std::string& error);
    // Actual accepted resource absorption/death owner marks its child. No
    // treasure receipt, generic reward, or fabricated consumption is implied.
    bool consume(const ChildIdentity&, std::string& error);
private:
    std::map<SourceIdentity, ContentsRecord> mRecords;
};
}
