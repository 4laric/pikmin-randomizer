#pragma once
#include <array>
#include <cstdint>
#include <string>
#include <vector>

namespace pc_midday {
using Bytes = std::vector<uint8_t>;
using Digest = std::array<uint8_t, 32>;
constexpr uint32_t FormatVersion = 1;
constexpr size_t MaxBytes = 16 * 1024 * 1024;
constexpr uint32_t MaxActors = 65536;
// IDs belong to one checkpoint world epoch, never a pointer or a recycled slot.
// Capture assigns monotonic nonzero incarnations; references name that incarnation.
struct Capability { uint32_t family = 0, version = 0; };
struct Binding { Digest seed{}, session{}, content{}, schema{}; };
struct Actor {
    uint64_t id = 0;
    Capability adapter;
    Bytes state; // adapter-owned explicit scalar wire format, never native memory
    std::vector<uint64_t> references; // zero means an absent optional reference
};
struct Section { Capability adapter; Bytes state; };
struct Snapshot {
    Binding binding;
    uint64_t generation = 0, frame = 0, dayEndGeneration = 0;
    std::vector<Actor> actors;
    std::vector<Section> sections;
};
// Exact adapter versions, required global sections, and complete observed actor
// inventory form the capture contract. Empty inventories cannot prove a real world.
struct Coverage {
    std::vector<Capability> supported;
    std::vector<Capability> requiredSections;
    std::vector<uint64_t> observedActorIds;
};
bool validate(const Snapshot&, const Coverage&, std::string& error);
bool encode(const Snapshot&, const Coverage&, Bytes&, std::string& error);
// Output is replaced only after all integrity, binding and graph checks succeed.
bool decode(const Bytes&, const Binding&, const Coverage&, Snapshot&, std::string& error);
Digest digest(const Bytes&);
}
