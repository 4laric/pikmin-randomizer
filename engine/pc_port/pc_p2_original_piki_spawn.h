#pragma once
#include <array>
#include <cstdint>
#include <string>
namespace p2original {
struct PikiSpawnRecord {
    // Opaque admitted record key; zero is not a no-record sentinel. The actual
    // catalog/provider validates source identity, not this placement helper.
    std::uint32_t uid=0, count=0;
    int species=0, wildParameter=0;
    std::array<float,3> position{}, offset{};
};
// Independent P2 PlayData authority, not an AP Onion-unlock mask.
struct PikiSpawnProgress {
    std::uint8_t met=0, boot=0;
    bool allowDebug=false;
};
enum class PikiBirthResult { Born, CapacitySkipped, Failed };
struct PikiSpawnProvider {
    virtual ~PikiSpawnProvider()=default;
    // Validate immutable source/catalog/resources and reserve bookkeeping before
    // any draw/birth. Own any partially constructed body until cleaned up.
    virtual bool prepare(const PikiSpawnRecord&, std::string& error)=0;
    virtual float randomUnit()=0;
    virtual PikiBirthResult birth(std::uint32_t attempt,
        const std::array<float,3>& position, bool wild, std::string& error)=0;
};
struct PikiSpawnResult {std::uint32_t attempts=0, policySkipped=0, capacitySkipped=0, born=0;};
// Source order is two draws then one birth, repeated. A failure after drawing
// cannot roll back RNG or successful earlier bodies; output reports that exact
// prefix and the provider retains cleanup ownership. Never floor-corrects Y.
bool spawnOriginalPiki(const PikiSpawnRecord&,const PikiSpawnProgress&,
    PikiSpawnProvider&,PikiSpawnResult& out,std::string& error);
}
