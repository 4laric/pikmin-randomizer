// Muse lane l66 (#506) adversarial identity-contract checker.
//
// Standalone, engine-independent log checker: audits one native run log for
// the four generated candidates (41 Fuefuki, 57 Kurage, 58 BombSarai,
// 78 MiniHoudai) across the adversarial classes owned by this lane —
// swapped source ids, generator/slot mismatch, unsupported terrain, unmapped
// slots, missing route evidence and injected-birth taint. Prints one verdict
// line per candidate plus a global verdict, and exits 0 only when at least
// one candidate fully correlates (resolve + placement + family binding agree
// on one slot/generator, terrain legal, mapped slot, route evidence) with no
// conflicting leg on that same slot/generator and no injected taint on the
// correlated markers; exits 1 otherwise. Markers for other identities on
// other slots/generators (mixed scene) do not fail the verdict. Never emits
// markers itself, so it cannot fabricate acceptance.
//
// Expected until muse-placement (l52) and muse-packaging (l53) land their
// reviewed candidates: exit 1 with absent markers (BLOCKED).
//
// Build (standalone, no engine headers):
//   g++ -std=c++17 -Wall -Wextra -Werror tools/p2_muse_identityqa_fixture.cpp -o p2_muse_identityqa_fixture
// Run:
//   ./p2_muse_identityqa_fixture <run.log>

#include <cstdio>
#include <fstream>
#include <string>
#include <vector>

namespace {

struct Candidate {
    int sourceId;
    const char* family;
    const char* bindA; // primary binding token (upper-case match)
    const char* bindB; // secondary binding token (upper-case match)
    bool mixedOk;      // Kurage57 frog-cohort slot allows mixed shore
};

const Candidate kCandidates[] = {
    {41, "Fuefuki", "P2_FUEFUKI_TEKI_", "FAMILY=FUEFUKI", false},
    {57, "Kurage", "P2_KURAGE_TEKI_READY", "P2_KURAGE_CORPSE_READY", true},
    {58, "BombSarai", "P2_BOMBSARAI_", "FAMILY=BOMBSARAI", false},
    {78, "MiniHoudai", "P2_GROINK_", "P2_MINIHOUDAI_", false},
};

const int kNumCandidates = 4;

bool hasToken(const std::string& line, const char* token)
{
    return line.find(token) != std::string::npos;
}

bool hasTokenUpper(const std::string& upper, const char* token)
{
    return upper.find(token) != std::string::npos;
}

// Extract `key=<unsigned>` from a line; returns false when absent/malformed.
bool fieldValue(const std::string& line, const char* key, unsigned& out)
{
    const std::string needle = std::string(key) + "=";
    std::string::size_type pos = line.find(needle);
    if (pos == std::string::npos) return false;
    pos += needle.size();
    std::string::size_type end = pos;
    while (end < line.size() && line[end] >= '0' && line[end] <= '9') ++end;
    if (end == pos) return false;
    out = static_cast<unsigned>(std::stoul(line.substr(pos, end - pos)));
    return true;
}

bool fieldText(const std::string& line, const char* key, const char* want)
{
    const std::string needle = std::string(key) + "=" + want;
    std::string::size_type pos = line.find(needle);
    if (pos == std::string::npos) return false;
    const std::string::size_type end = pos + needle.size();
    return end >= line.size() || line[end] == ' ' || line[end] == '\t';
}

std::string toUpper(std::string text)
{
    for (char& ch : text) {
        if (ch >= 'a' && ch <= 'z') ch = static_cast<char>(ch - 'a' + 'A');
    }
    return text;
}

bool isTainted(const std::string& upper)
{
    return hasToken(upper, "INJECTED") || hasToken(upper, "HEALTH_ZERO");
}

struct ResolveLeg {
    int sourceId;
    unsigned target;
};

struct BindingLeg {
    int candidateIdx; // -1 when family unknown
    unsigned generator;
};

struct Placement {
    unsigned generator;
    unsigned slot;
    bool terrainOk;
    bool routeOk;
};

} // namespace

int main(int argc, char** argv)
{
    if (argc != 2) {
        std::fprintf(stderr, "usage: %s <run.log>\n",
                     argc > 0 ? argv[0] : "p2_muse_identityqa_fixture");
        return 2;
    }
    std::ifstream log(argv[1]);
    if (!log) {
        std::fprintf(stderr, "cannot open %s\n", argv[1]);
        return 2;
    }

    std::vector<std::string> lines;
    std::string line;
    while (std::getline(log, line)) lines.push_back(line);

    // Global legs: every resolve/placement/binding in the log, whatever
    // family, so conflicts can be scoped to the correlated slot/generator.
    std::vector<ResolveLeg> resolveLegs;
    std::vector<ResolveLeg> placementLegs; // bound=1 only
    std::vector<ResolveLeg> placementRefusals; // bound=0 vetoes the target
    std::vector<BindingLeg> bindingLegs;
    bool taintedBirth = false;
    std::vector<std::string> taintedLines;

    for (const std::string& raw : lines) {
        const std::string upper = toUpper(raw);
        const bool birthMarker = hasToken(raw, "P2_SEED_RESOLVE") ||
            hasToken(raw, "P2_GENERATED_PLACEMENT") ||
            hasToken(raw, "P2_PLACEMENT_SLOT");
        int familyIdx = -1;
        for (int i = 0; i < kNumCandidates; ++i) {
            if (hasTokenUpper(upper, kCandidates[i].bindA) ||
                hasTokenUpper(upper, kCandidates[i].bindB)) {
                familyIdx = i;
                break;
            }
        }
        if (isTainted(upper) && (birthMarker || familyIdx >= 0)) {
            taintedBirth = true;
            taintedLines.push_back(raw);
        }
        if (hasToken(raw, "P2_SEED_RESOLVE")) {
            unsigned source = 0, target = 0;
            if (fieldValue(raw, "source_id", source) &&
                (fieldValue(raw, "target", target) ||
                 fieldValue(raw, "target_id", target))) {
                resolveLegs.push_back({static_cast<int>(source), target});
            }
        }
        if (hasToken(raw, "P2_GENERATED_PLACEMENT")) {
            unsigned source = 0, target = 0;
            if (fieldValue(raw, "source_id", source) &&
                fieldValue(raw, "target", target)) {
                if (fieldText(raw, "bound", "1")) {
                    placementLegs.push_back(
                        {static_cast<int>(source), target});
                } else if (fieldText(raw, "bound", "0")) {
                    // A native refusal for this exact target vetoes any
                    // otherwise-consistent triple on it.
                    placementRefusals.push_back(
                        {static_cast<int>(source), target});
                }
            }
        }
        if (familyIdx >= 0) {
            unsigned fileId = 0;
            if (fieldValue(raw, "generator", fileId) ||
                fieldValue(raw, "gen", fileId) ||
                fieldValue(raw, "generator_id", fileId)) {
                bindingLegs.push_back({familyIdx, fileId});
            }
        }
    }

    int passCount = 0;
    bool conflictOnMatch = false;
    bool taintOnMatch = false;

    for (int c = 0; c < kNumCandidates; ++c) {
        const Candidate& cand = kCandidates[c];
        char want[16];
        std::snprintf(want, sizeof(want), "%d", cand.sourceId);
        std::vector<unsigned> resolveTargets;
        std::vector<unsigned> placementTargets;
        std::vector<unsigned> refusedTargets;
        std::vector<Placement> slots;
        std::vector<unsigned> bindings;

        for (const ResolveLeg& leg : resolveLegs) {
            char have[16];
            std::snprintf(have, sizeof(have), "%d", leg.sourceId);
            if (std::string(have) == want) resolveTargets.push_back(leg.target);
        }
        for (const ResolveLeg& leg : placementLegs) {
            char have[16];
            std::snprintf(have, sizeof(have), "%d", leg.sourceId);
            if (std::string(have) == want) placementTargets.push_back(leg.target);
        }
        for (const ResolveLeg& leg : placementRefusals) {
            char have[16];
            std::snprintf(have, sizeof(have), "%d", leg.sourceId);
            if (std::string(have) == want) refusedTargets.push_back(leg.target);
        }
        for (const BindingLeg& leg : bindingLegs) {
            if (leg.candidateIdx == c) bindings.push_back(leg.generator);
        }
        for (const std::string& raw : lines) {
            if (!hasToken(raw, "P2_PLACEMENT_SLOT")) continue;
            Placement placement = {0, 0, false, false};
            unsigned generator = 0, slot = 0;
            if (!(fieldValue(raw, "generator", generator) &&
                  fieldValue(raw, "slot", slot))) {
                continue;
            }
            placement.generator = generator;
            placement.slot = slot;
            const bool ground = fieldText(raw, "terrain", "ground");
            const bool mixed =
                cand.mixedOk && fieldText(raw, "terrain", "mixed");
            placement.terrainOk =
                (ground || mixed) && fieldText(raw, "xyz", "1");
            placement.routeOk = fieldText(raw, "route", "1");
            slots.push_back(placement);
        }

        bool ok = false;
        unsigned matchGen = 0, matchUid = 0;
        for (const Placement& placement : slots) {
            if (placement.slot == 0) continue; // unmapped: fail closed
            if (!placement.terrainOk || !placement.routeOk) continue;
            bool refused = false;
            for (unsigned target : refusedTargets) {
                if (target == placement.slot) {
                    refused = true;
                    break;
                }
            }
            if (refused) continue; // native bound=0 vetoes this target
            bool seedHit = false;
            for (unsigned target : resolveTargets) {
                if (target == placement.slot) {
                    seedHit = true;
                    break;
                }
            }
            if (!seedHit) continue;
            if (!placementTargets.empty()) {
                bool placeHit = false;
                for (unsigned target : placementTargets) {
                    if (target == placement.slot) {
                        placeHit = true;
                        break;
                    }
                }
                if (!placeHit) continue;
            }
            bool bindHit = false;
            for (unsigned fileId : bindings) {
                if (fileId == placement.generator) {
                    bindHit = true;
                    break;
                }
            }
            if (!bindHit) continue;
            ok = true;
            matchGen = placement.generator;
            matchUid = placement.slot;
            break;
        }

        if (ok) {
            ++passCount;
            // Scope conflicts to THIS slot/generator: a foreign leg on the
            // same slot, a foreign binding on the same generator, or taint
            // touching either, disqualifies this correlation.
            for (const ResolveLeg& leg : resolveLegs) {
                if (leg.sourceId != cand.sourceId &&
                    leg.target == matchUid) {
                    conflictOnMatch = true;
                }
            }
            for (const ResolveLeg& leg : placementLegs) {
                if (leg.sourceId != cand.sourceId &&
                    leg.target == matchUid) {
                    conflictOnMatch = true;
                }
            }
            for (const BindingLeg& leg : bindingLegs) {
                if (leg.candidateIdx != c && leg.generator == matchGen) {
                    conflictOnMatch = true;
                }
            }
            char uidText[16], genText[16];
            std::snprintf(uidText, sizeof(uidText), "%u", matchUid);
            std::snprintf(genText, sizeof(genText), "%u", matchGen);
            for (const std::string& raw : taintedLines) {
                if (raw.find(uidText) != std::string::npos ||
                    raw.find(genText) != std::string::npos ||
                    raw.find("P2_SEED_RESOLVE") != std::string::npos ||
                    raw.find("P2_GENERATED_PLACEMENT") != std::string::npos ||
                    raw.find("P2_PLACEMENT_SLOT") != std::string::npos) {
                    taintOnMatch = true;
                }
            }
        }
        std::printf("P2_MUSE_IDENTITYQA source_id=%d family=%s gate1_ok=%d "
                    "generator=%u seed_uid=%u resolve=%u placement=%u "
                    "bindings=%u\n",
                    cand.sourceId, cand.family, ok ? 1 : 0, matchGen, matchUid,
                    static_cast<unsigned>(resolveTargets.size()),
                    static_cast<unsigned>(placementTargets.size()),
                    static_cast<unsigned>(bindings.size()));
    }

    const bool pass =
        passCount > 0 && !conflictOnMatch && !taintOnMatch && !taintedBirth;
    std::printf("P2_MUSE_IDENTITYQA verdict=%s pass_ids=%d conflict=%d "
                "tainted=%d\n",
                pass ? "PASS" : "FAIL", passCount,
                conflictOnMatch ? 1 : 0,
                (taintOnMatch || taintedBirth) ? 1 : 0);
    return pass ? 0 : 1;
}
