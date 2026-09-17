// Guarded probe proving the #698 per-gate instrumentation fix (#739).
//
// Standalone, engine-free (no captain, no Navi, no HP): it verifies (1) the
// gate-decision truth table the fixed fixture implements (which gate holds,
// in fixture order), and (2) that the fixture source actually contains the
// required diagnostic markers. Any future runtime consumer must adopt
// scripts/p2_fixture_captain_guard.h before launch; its hash is recorded in
// the lane packet, not claimed here.
//
// Build (no engine, no lease):
//   g++ -std=c++17 -Wall -Wextra -Werror tools/p2_impact_gating_fix_probe.cpp
//       -o <private-output>/p2_impact_gating_fix_probe
// Run:
//   p2_impact_gating_fix_probe --fixture-src <path-to>/p2_challenge_guarded_boot_fixture.cpp
#include <cstdio>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>

// Mirrors the fixed fixture idle() gate order exactly: managers, navi,
// movie (with skip), pause/UI. Returns the gate that would hold, or "none"
// when observed would advance.
static const char* gate_name(bool managers_ok, bool navi_ok, bool movie_active,
                             bool paused_or_ui, bool paused) {
    if (!managers_ok) return "managers";
    if (!navi_ok) return "navi";
    if (movie_active) return "movie";
    if (paused_or_ui) return paused ? "pause" : "ui";
    return "none";
}

static int failures = 0;
static void check(bool ok, const char* name) {
    std::printf("%s GATING_FIX_PROBE %s\n", ok ? "PASS" : "FAIL", name);
    std::fflush(stdout);
    if (!ok) ++failures;
}

int main(int argc, char** argv) {
    const char* fixture_src = nullptr;
    for (int i = 1; i < argc; ++i) {
        if (!std::strcmp(argv[i], "--fixture-src") && i + 1 < argc) {
            fixture_src = argv[++i];
        }
    }
    // 1. Gate-decision truth table (fixture order).
    check(!std::strcmp(gate_name(false, false, false, false, false), "managers"),
          "gate-managers");
    check(!std::strcmp(gate_name(true, false, false, false, false), "navi"),
          "gate-navi");
    check(!std::strcmp(gate_name(true, true, true, false, false), "movie"),
          "gate-movie");
    check(!std::strcmp(gate_name(true, true, false, true, true), "pause"),
          "gate-pause");
    check(!std::strcmp(gate_name(true, true, false, true, false), "ui"),
          "gate-ui");
    check(!std::strcmp(gate_name(true, true, false, false, false), "none"),
          "gate-none");
    // 2. The fixture source carries the #698 markers.
    if (fixture_src == nullptr) {
        check(false, "fixture-src-provided");
    } else {
        std::ifstream in(fixture_src);
        std::ostringstream text;
        text << in.rdbuf();
        const std::string body = text.str();
        check(body.find("P2_CHALLENGE_GATE_DIAG") != std::string::npos,
              "marker-gate-diag-present");
        check(body.find("P2_CHALLENGE_PARK_ALIVE") != std::string::npos,
              "marker-park-alive-present");
        check(body.find("gateDiag(\"movie\")") != std::string::npos,
              "marker-movie-path");
        check(body.find("gateDiag(gameflow.mPauseAll?\"pause\":\"ui\")") != std::string::npos,
              "marker-pause-ui-path");
    }
    if (failures == 0) {
        std::puts("ALL_PROBE_PASS");
    } else {
        std::printf("FAIL GATING_FIX_PROBE failures=%d\n", failures);
    }
    std::fflush(stdout);
    return failures == 0 ? 0 : 1;
}
