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
// Consumer lane #572 adds an opt-in generated-triple check behind the
// --generated second argument: P2_SEED_RESOLVE source_id=99,
// P2_GENERATED_PLACEMENT source_id=99 ... bound=1 (reviewed l52 grammar;
// no engine build emits the case-99 arm yet), and the family BIRTH above
// must agree on one target/generator with no injected-birth taint. Default
// invocation is byte-identical to the l63 contract. In --generated mode
// exit 0 additionally requires generated_ok=1.
//
// Build (standalone, no engine headers):
//   g++ -std=c++17 -Wall -Wextra -Werror tools/p2_muse_waterwraith_fixture.cpp -o p2_muse_waterwraith_fixture
// Run:
//   ./p2_muse_waterwraith_fixture <run.log> [--generated]

#include <cctype>
#include <cstdio>
#include <fstream>
#include <string>
#include <vector>

namespace {

bool hasToken(const std::string& line, const char* token)
{
    return line.find(token) != std::string::npos;
}

// Extract key=<text> bounded by whitespace; true when present.
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

const char* kAcceptedSlot = "568677317";

bool tainted(const std::string& line)
{
    std::string lower(line);
    for (char& c : lower) c = (char)std::tolower((unsigned char)c);
    return lower.find("injected") != std::string::npos ||
           lower.find("health_zero") != std::string::npos;
}

struct GeneratedVerdict {
    bool resolve = false;
    bool placement = false;
    bool birth = false;
    bool taint = false;
    std::string target;
    std::string generator;
    std::string reason;
    bool ok() const { return resolve && placement && birth && !taint; }
};

GeneratedVerdict checkGenerated(const std::vector<std::string>& lines)
{
    GeneratedVerdict verdict;
    verdict.reason = "undecided";
    std::string resolveTarget;
    std::string placeTarget;
    std::string placeGenerator;
    bool placeGeneratorSeen = false;
    bool birthSeen = false;
    std::vector<std::string> bindGens;
    std::vector<std::string> bindSlots;
    std::vector<std::size_t> bindLines;
    std::vector<std::string> forgetGens;
    std::vector<std::size_t> forgetLines;
    for (std::vector<std::string>::size_type li = 0; li < lines.size(); ++li) {
        const std::string& line = lines[li];
        std::string source, target, bound, id, helper, phase, attached;
        std::string bindGen, bindSlot, bindSource, forgetGen;
        if (hasToken(line, "P2_SEED_RESOLVE") && fieldText(line, "source_id", source)) {
            if (tainted(line)) { verdict.taint = true; continue; }
            if (source == "99" && fieldText(line, "target", target)) {
                verdict.resolve = true;
                resolveTarget = target;
            }
        }
        if (hasToken(line, "P2_GENERATED_PLACEMENT") && fieldText(line, "source_id", source)) {
            if (tainted(line)) { verdict.taint = true; continue; }
            if (source == "99" && fieldText(line, "target", target)
                && fieldText(line, "bound", bound) && bound == "1") {
                verdict.placement = true;
                placeTarget = target;
                if (fieldText(line, "generator", placeGenerator)) {
                    placeGeneratorSeen = true;
                }
            }
        }
        if (hasToken(line, "P2_WATERWRAITH_BIRTH") && fieldText(line, "id", id)) {
            if (tainted(line)) { verdict.taint = true; continue; }
            if (id == "99" && fieldText(line, "helper", helper) && helper == "98"
                && fieldText(line, "phase", phase) && phase == "fall"
                && fieldText(line, "attached", attached) && attached == "1") {
                birthSeen = true;
            }
        }
        if (hasToken(line, "P2_WATERWRAITH_GENERATED_BIND") && fieldText(line, "generator", bindGen)) {
            if (tainted(line)) { verdict.taint = true; continue; }
            if (fieldText(line, "slot", bindSlot) && fieldText(line, "source", bindSource)
                && bindSource == "99") {
                bindLines.push_back(li);
                bindGens.push_back(bindGen);
                bindSlots.push_back(bindSlot);
            }
        }
        if (hasToken(line, "P2_WATERWRAITH_GENERATED_FORGET") && fieldText(line, "generator", forgetGen)) {
            if (tainted(line)) { verdict.taint = true; continue; }
            forgetLines.push_back(li);
            forgetGens.push_back(forgetGen);
        }
    }
    if (verdict.taint) { verdict.reason = "injected-birth taint"; return verdict; }
    if (!verdict.resolve) {
        verdict.reason = "missing P2_SEED_RESOLVE source_id=99 (fixed-encounter birth is not generated)";
        return verdict;
    }
    if (!verdict.placement) {
        verdict.reason = "missing P2_GENERATED_PLACEMENT source_id=99 bound=1 (placement99 unpublished)";
        return verdict;
    }
    if (resolveTarget != placeTarget) {
        verdict.reason = "resolve/placement target disagreement";
        return verdict;
    }
    if (!birthSeen) {
        verdict.reason = "missing P2_WATERWRAITH_BIRTH id=99 helper=98";
        return verdict;
    }
    verdict.birth = true;
    verdict.target = resolveTarget;
    if (verdict.target != kAcceptedSlot) {
        verdict.birth = false;
        verdict.reason = "slot-not-accepted";
        return verdict;
    }
    if (!placeGeneratorSeen) {
        verdict.birth = false;
        verdict.reason = "placement marker lacks a generator field";
        return verdict;
    }
    std::size_t lastBind = bindLines.size();
    for (std::size_t i = 0; i < bindLines.size(); ++i) {
        if (bindGens[i] == placeGenerator && bindSlots[i] == resolveTarget) {
            lastBind = i;
        }
    }
    if (lastBind == bindLines.size()) {
        verdict.birth = false;
        verdict.reason = "family generated-claim missing: no P2_WATERWRAITH_GENERATED_BIND for this generator and slot";
        return verdict;
    }
    for (std::size_t i = 0; i < forgetLines.size(); ++i) {
        if (forgetLines[i] > bindLines[lastBind] && forgetGens[i] == placeGenerator) {
            verdict.birth = false;
            verdict.reason = "family claim lost after bind";
            return verdict;
        }
    }
    verdict.generator = placeGenerator;
    verdict.reason = "resolve+placement+register-claim agree (live family bind)";
    return verdict;
}

} // namespace

int main(int argc, char** argv)
{
    if (argc < 2 || argc > 3) {
        std::fprintf(stderr, "usage: %s <run.log> [--generated]\n",
                     argc > 0 ? argv[0] : "p2_muse_waterwraith_fixture");
        return 2;
    }
    const bool generatedMode = argc == 3 && std::string(argv[2]) == "--generated";
    if (argc == 3 && !generatedMode) {
        std::fprintf(stderr, "usage: %s <run.log> [--generated]\n", argv[0]);
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

    std::vector<std::string> lines;
    std::string line;
    while (std::getline(log, line)) {
        lines.push_back(line);
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
    if (!generatedMode) {
        return (gate1Ok && gate2Ok) ? 0 : 1;
    }
    const GeneratedVerdict generated = checkGenerated(lines);
    std::printf("P2_MUSE_WATERWRAITH_GENERATED resolve=%d placement=%d birth=%d taint=%d "
                "target=%s generator=%s generated_ok=%d reason=%s\n",
                generated.resolve ? 1 : 0, generated.placement ? 1 : 0,
                generated.birth ? 1 : 0, generated.taint ? 1 : 0,
                generated.target.empty() ? "-" : generated.target.c_str(),
                generated.generator.empty() ? "-" : generated.generator.c_str(),
                generated.ok() ? 1 : 0, generated.reason.c_str());
    return (gate1Ok && gate2Ok && generated.ok()) ? 0 : 1;
}
