// Muse lane l63 (#503) fixed-encounter log checker for Waterwraith (99/98).
//
// Standalone, engine-independent: reads one native run log and verifies the
// birth triple (P2_WATERWRAITH_BIRTH phase=fall attached=1 id=99 helper=98,
// P2_WATERWRAITH_REGISTER_PROFILE with placement=, P2_WATERWRAITH_VISUAL_READY
// species=2) and the autonomous chase leg (a P2_WATERWRAITH_STEER mode=chase
// line with motion=walk|run, travel>=1.0 and escape=2). Prints a verdict line
// and exits 0 only when both gates hold; exits 1 otherwise. Never emits
// markers itself, so it cannot fabricate acceptance. Scope honesty: this
// checks the FIXED natural encounter; generated admission stays open with
// muse-placement (l52).
//
// Build (standalone, no engine headers):
//   g++ -std=c++17 -Wall -Wextra -Werror tools/p2_muse_waterwraith_fixture.cpp -o p2_muse_waterwraith_fixture
// Run:
//   ./p2_muse_waterwraith_fixture <run.log>

#include <cstdio>
#include <fstream>
#include <string>

namespace {

bool hasToken(const std::string& line, const char* token)
{
    return line.find(token) != std::string::npos;
}

// Extract `key=<text>` bounded by whitespace; true when present.
bool fieldText(const std::string& line, const char* key, std::string& out)
{
    const std::string needle = std::string(key) + "=";
    const std::string::size_type pos = line.find(needle);
    if (pos == std::string::npos) {
        return false;
    }
    const std::string::size_type start = pos + needle.size();
    std::string::size_type end = start;
    while (end < line.size() && line[end] != ' ' && line[end] != '\t'
           && line[end] != '\r' && line[end] != '\n') {
        ++end;
    }
    out = line.substr(start, end - start);
    return true;
}

bool fieldDouble(const std::string& line, const char* key, double& out)
{
    std::string text;
    if (!fieldText(line, key, text)) {
        return false;
    }
    try {
        std::size_t used = 0;
        out = std::stod(text, &used);
        return used > 0;
    } catch (...) {
        return false;
    }
}

} // namespace

int main(int argc, char** argv)
{
    if (argc != 2) {
        std::fprintf(stderr, "usage: %s <run.log>\n",
                     argc > 0 ? argv[0] : "p2_muse_waterwraith_fixture");
        return 2;
    }
    std::ifstream log(argv[1]);
    if (!log) {
        std::fprintf(stderr, "cannot open %s\n", argv[1]);
        return 2;
    }

    bool birthOk = false;
    bool profileSeen = false;
    bool visualSeen = false;
    bool escape2 = false;
    bool chaseLocomotion = false;
    double chaseTravelMax = 0.0;

    std::string line;
    while (std::getline(log, line)) {
        if (hasToken(line, "P2_WATERWRAITH_BIRTH")) {
            std::string phase, attached, id, helper;
            if (fieldText(line, "phase", phase) && fieldText(line, "attached", attached)
                && fieldText(line, "id", id) && fieldText(line, "helper", helper)
                && phase == "fall" && attached == "1" && id == "99" && helper == "98") {
                birthOk = true;
            }
        }
        if (hasToken(line, "P2_WATERWRAITH_REGISTER_PROFILE") && hasToken(line, "placement=")) {
            profileSeen = true;
        }
        if (hasToken(line, "P2_WATERWRAITH_VISUAL_READY")) {
            std::string species;
            if (fieldText(line, "species", species) && species == "2") {
                visualSeen = true;
            }
        }
        if (hasToken(line, "P2_WATERWRAITH_STEER")) {
            std::string mode, motion, escape;
            double travel = 0.0;
            fieldText(line, "mode", mode);
            fieldText(line, "motion", motion);
            fieldText(line, "escape", escape);
            fieldDouble(line, "travel", travel);
            if (escape == "2") {
                escape2 = true;
            }
            if (mode == "chase") {
                if (motion == "walk" || motion == "run") {
                    chaseLocomotion = true;
                }
                if (travel > chaseTravelMax) {
                    chaseTravelMax = travel;
                }
            }
        }
    }

    const bool gate1Ok = birthOk && profileSeen && visualSeen;
    const bool gate2Ok = chaseLocomotion && chaseTravelMax >= 1.0 && escape2;
    std::printf("P2_MUSE_WATERWRAITH birth=%d profile=%d visual=%d chase=%d travel=%.1f "
                "escape2=%d gate1_ok=%d gate2_ok=%d\n",
                birthOk ? 1 : 0, profileSeen ? 1 : 0, visualSeen ? 1 : 0,
                chaseLocomotion ? 1 : 0, chaseTravelMax, escape2 ? 1 : 0,
                gate1Ok ? 1 : 0, gate2Ok ? 1 : 0);
    return (gate1Ok && gate2Ok) ? 0 : 1;
}
