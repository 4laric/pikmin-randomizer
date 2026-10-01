// Muse lane l57 (#497) gate-1 log observer for Fuefuki (source 41).
//
// Standalone, engine-independent checker: reads one native run log and
// verifies the SAME generated spawn correlates across the three marker legs
// required for identity_spawn —
//   P2_PLACEMENT_SLOT generator=<file-id> slot=<seed-uid> ... terrain=ground route=1
//   P2_SEED_RESOLVE source_id=41 target=<seed-uid>
//   P2_HARDLANES_READY family=Fuefuki ... gen=<file-id>
//     (or any P2_FUEFUKI_TEKI_* ... generator=<file-id>).
// Prints a verdict line and exits 0 only on a fully correlated triple with a
// mapped slot (slot != 0), ground terrain and route evidence; exits 1
// otherwise. Never emits markers itself, so it cannot fabricate acceptance.
// This is the acceptance contract the muse-placement (l52) and muse-packaging
// (l53) candidates must satisfy; until their reviewed commits land, any real
// generated run is expected to exit 1 (BLOCKED on those dependencies).
//
// Build (standalone, no engine headers):
//   g++ -std=c++17 -Wall -Wextra -Werror tools/p2_muse_fuefuki_fixture.cpp -o p2_muse_fuefuki_fixture
// Run:
//   ./p2_muse_fuefuki_fixture <run.log>

#include <cstdio>
#include <fstream>
#include <string>
#include <vector>

namespace {

bool hasToken(const std::string& line, const char* token)
{
    return line.find(token) != std::string::npos;
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
        std::fprintf(stderr, "usage: %s <run.log>\n", argc > 0 ? argv[0] : "p2_muse_fuefuki_fixture");
        return 2;
    }
    std::ifstream log(argv[1]);
    if (!log) {
        std::fprintf(stderr, "cannot open %s\n", argv[1]);
        return 2;
    }

    std::vector<Placement> placements;
    std::vector<unsigned> seedTargets41;
    std::vector<unsigned> bindings;

    std::string line;
    while (std::getline(log, line)) {
        if (hasToken(line, "P2_PLACEMENT_SLOT")) {
            Placement placement = {0, 0, false, false};
            unsigned generator = 0, slot = 0;
            if (fieldValue(line, "generator", generator) && fieldValue(line, "slot", slot)) {
                placement.generator = generator;
                placement.slot = slot;
                placement.terrainOk = fieldText(line, "terrain", "ground") && fieldText(line, "xyz", "1");
                placement.routeOk = fieldText(line, "route", "1");
                placements.push_back(placement);
            }
        }
        if (hasToken(line, "P2_SEED_RESOLVE") && fieldText(line, "source_id", "41")) {
            unsigned target = 0;
            if (fieldValue(line, "target", target) || fieldValue(line, "target_id", target)) {
                seedTargets41.push_back(target);
            }
        }
        const bool tekiMarker = line.find("P2_FUEFUKI_TEKI_") != std::string::npos;
        const bool readyMarker =
            hasToken(line, "P2_HARDLANES_READY") && hasToken(line, "family=Fuefuki");
        if (tekiMarker || readyMarker) {
            unsigned fileId = 0;
            if (fieldValue(line, "generator", fileId) || fieldValue(line, "gen", fileId) ||
                fieldValue(line, "generator_id", fileId)) {
                bindings.push_back(fileId);
            }
        }
    }

    bool gate1Ok = false;
    unsigned matchGenerator = 0, matchUid = 0;
    for (const Placement& placement : placements) {
        if (placement.slot == 0) continue; // unmapped slot: fail closed
        if (!placement.terrainOk || !placement.routeOk) continue;
        bool seedHit = false;
        for (unsigned target : seedTargets41) {
            if (target == placement.slot) {
                seedHit = true;
                break;
            }
        }
        if (!seedHit) continue;
        bool bindHit = false;
        for (unsigned fileId : bindings) {
            if (fileId == placement.generator) {
                bindHit = true;
                break;
            }
        }
        if (!bindHit) continue;
        gate1Ok = true;
        matchGenerator = placement.generator;
        matchUid = placement.slot;
        break;
    }

    std::printf("P2_MUSE_FUEFUKI_GATE1 placements=%u seed41=%u bindings=%u gate1_ok=%d generator=%u seed_uid=%u\n",
                static_cast<unsigned>(placements.size()), static_cast<unsigned>(seedTargets41.size()),
                static_cast<unsigned>(bindings.size()), gate1Ok ? 1 : 0, matchGenerator, matchUid);
    return gate1Ok ? 0 : 1;
}
