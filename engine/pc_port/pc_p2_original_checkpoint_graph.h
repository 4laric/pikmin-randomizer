#pragma once
#include <array>
#include <cstdint>
#include <string>
#include <vector>

namespace p2originalcheckpoint {
// Family payloads retain their own complete typed incarnation/source identities.
// A section must never replace those identities with its ordinal in this vector.
struct Section {
    std::string role;
    unsigned version = 0;
    std::string bytes;
};
struct Graph {
    std::string campaign, session;
    std::vector<Section> sections;
};
// Issued by the selected native checkpoint reader, outside the graph payload.
// Including the card's own final hash in its payload would be self-referential.
struct Proof {
    std::uint64_t generation = 0;
    std::array<std::uint8_t,32> sha{};
    bool valid() const {
        if (!generation) return false;
        for (auto byte : sha) if (byte) return true;
        return false;
    }
    bool operator==(const Proof& other) const {
        return generation == other.generation && sha == other.sha;
    }
};
inline bool digest(const std::string& value) {
    return value.size() == 64 && value.find_first_not_of("0123456789abcdef") == std::string::npos;
}
inline bool bounded(const Graph& graph) {
    if (!digest(graph.campaign) || !digest(graph.session)
        || graph.sections.empty() || graph.sections.size() > 64) return false;
    std::size_t total = 0;
    std::string previous;
    for (const auto& section : graph.sections) {
        if (section.role.empty() || section.role.size() > 64
            || section.role.find_first_not_of("abcdefghijklmnopqrstuvwxyz0123456789_-") != std::string::npos
            || (!previous.empty() && section.role <= previous)
            || !section.version || section.version > 65535
            || section.bytes.empty() || section.bytes.size() > 1024*1024) return false;
        total += section.bytes.size();
        if (total > 8*1024*1024) return false;
        previous = section.role;
    }
    return true;
}
class ProofSource {
public:
    virtual ~ProofSource() = default;
    virtual bool selected(Proof&, std::string&) const = 0;
};
// Separate from ordinary GroupProvider. No ordinary birth/initialize, placement
// draw, generation activation, death/drop, stock credit or gameplay callback.
// The owner keeps the scene unpublished and its clock stopped for this call.
class Provider {
public:
    virtual ~Provider() = default;
    // Decode ALL sections and verify actual selected source/resource/scene and
    // complete family census. Missing actors, terminal histories, graph links,
    // optional receiver states and required providers must fail here.
    virtual bool preflight(const Graph&, std::string&) = 0;
    // Reserve aggregate physical capacity, including captured/released children.
    virtual bool reserve(const Graph&, std::string&) = 0;
    // Allocate hidden native actors without source init/RNG and bind only into
    // provisional registries. Saved full identities/frontiers remain unchanged.
    // A retry must not inherit Catalog.mUsed entries from a failed attempt.
    virtual bool allocateNoInit(const Graph&, std::string&) = 0;
    // Resolve the whole prospective graph, then apply validated snapshots.
    // Dead visible bodies, absent terminal children and pending FSMs follow
    // their typed family codecs; enum names alone never imply source death.
    virtual bool resolveAndApply(const Graph&, std::string&) = 0;
    // All potentially failing work precedes publication. This adopts the whole
    // provisional ownership context, never individual global registry entries.
    virtual void publish() noexcept = 0;
    // Release only this attempt's hidden allocations/reservations/registries.
    // Do not retire successful identities or mutate the previous live graph.
    virtual void abort() noexcept = 0;
};
inline bool restore(const Graph& graph, const Proof& proof,
                    const std::string& campaign, const std::string& session,
                    const ProofSource& authority, Provider& provider, std::string& error) {
    if (!bounded(graph) || graph.campaign != campaign || graph.session != session || !proof.valid()) {
        error = "original checkpoint graph selection invalid";
        return false;
    }
    auto selected = [&]() {
        Proof current;
        if (!authority.selected(current,error) || !current.valid() || !(current == proof)) {
            error = "original checkpoint graph selected card changed";
            return false;
        }
        return true;
    };
    if (!selected()) return false;
    struct Rollback {
        Provider& owner;
        bool committed = false;
        ~Rollback() { if (!committed) owner.abort(); }
    } rollback{provider};
    if (!provider.preflight(graph,error) || !provider.reserve(graph,error) || !selected()
        || !provider.allocateNoInit(graph,error) || !selected()
        || !provider.resolveAndApply(graph,error) || !selected()) return false;
    provider.publish();
    rollback.committed = true;
    error.clear();
    return true;
}
} // namespace p2originalcheckpoint
