// #529 combined-candidate Queen QA observer (isolated, no engine link).
//
// Pure-C++ re-derivation of the Queen30 transport chain from a GL log file:
// READY health 5000.0 -> FLICK -> CORPSE health 0.0 -> corpse pellet ->
// carrier latch (transport>0) -> Pod receipt corpse:queen:230010 value=2
// new=1 -> PASS line, with staging-marker rejection. Must agree with
// experimental/pikmin2_queen_combined_qa.py on the same log.
//
// Build (MinGW, single translation unit, no engine objects):
//   g++ -std=gnu++17 -O2 -Wall -Wextra -Werror p2_queen_combined_qa_fixture.cpp
//       -o queen_qa_observe.exe
// Run:
//   queen_qa_observe.exe <native.log>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

namespace {

bool contains(const std::string& text, const std::string& needle) {
    return text.find(needle) != std::string::npos;
}

int countOccurrences(const std::string& text, const std::string& needle) {
    int count = 0;
    std::string::size_type pos = 0;
    while ((pos = text.find(needle, pos)) != std::string::npos) {
        ++count;
        pos += needle.size();
    }
    return count;
}

bool hasLatchedCarry(const std::string& text) {
    std::istringstream lines(text);
    std::string line;
    while (std::getline(lines, line)) {
        std::string::size_type pos = line.find("P2_QUEEN_CREATURE_CARRY");
        if (pos == std::string::npos) continue;
        std::string::size_type tpos = line.find("transport=", pos);
        if (tpos == std::string::npos) continue;
        int transport = 0;
        if (std::sscanf(line.c_str() + tpos, "transport=%d", &transport) == 1
            && transport > 0) {
            return true;
        }
    }
    return false;
}

const char* kStaging[] = {
    "NAVI_HEAL", "REPIN", "NAVI_SUSTAIN", "GUARD_PIKMIN",
    "P2_QUEEN_INJECT", "P2_KING_INJECT",
    "P2_QUEEN_TEKI_FORCED_TRANSPORT", "P2_QUEEN_TEKI_TRANSPORT_INJECT",
    "P2_KING_TEKI_FORCED_TRANSPORT", "P2_POD_CAPTAIN_RETURN",
    "FORCED_TRANSPORT",
};

}  // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::fprintf(stderr, "usage: %s <native.log>\n", argv[0]);
        return 2;
    }
    std::ifstream input(argv[1], std::ios::binary);
    if (!input) {
        std::fprintf(stderr, "cannot open %s\n", argv[1]);
        return 2;
    }
    std::ostringstream buffer;
    buffer << input.rdbuf();
    const std::string text = buffer.str();

    int failures = 0;
    auto check = [&](const char* name, bool ok) {
        std::printf("%-16s %s\n", name, ok ? "ok" : "FAIL");
        if (!ok) ++failures;
    };

    check("ready_hp",
          contains(text, "P2_QUEEN_TEKI_READY generator=230010")
              && contains(text, "health=5000.0"));
    check("attached",
          contains(text, "P2_QUEEN_TEKI_ATTACHED generator=230010"));
    check("flick",
          countOccurrences(text, "P2_QUEEN_TEKI_FLICK generator=230010") >= 1);
    check("natural_death",
          contains(text,
                   "P2_QUEEN_TEKI_CORPSE generator=230010 health=0.0"));
    check("corpse_pellet",
          contains(text, "P2_QUEEN_CREATURE_CORPSE_PELLET found=1"));
    check("carrier_latch", hasLatchedCarry(text));
    check("pod_receipt",
          contains(text,
                   "P2_POD_RECEIPT id=corpse:queen:230010 value=2 new=1"));
    check("completion",
          contains(text, "PASS P2_QUEEN_CREATURE_RUNTIME"));
    std::string stagingHits;
    for (const char* marker : kStaging) {
        if (contains(text, marker)) {
            if (!stagingHits.empty()) stagingHits += ",";
            stagingHits += marker;
        }
    }
    check("no_staging", stagingHits.empty());
    if (!stagingHits.empty()) {
        std::printf("staging_hits=%s\n", stagingHits.c_str());
    }
    std::printf("result=%s\n", failures == 0 ? "PASS" : "FAIL");
    return failures == 0 ? 0 : 1;
}
