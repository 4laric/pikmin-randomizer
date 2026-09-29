// Kurage57 campaign contract (#871): engine-free pins for the campaign fixes.
//
//   * campaign mode = seed bridge WITHOUT the room preview. Only there are
//     the fixture concessions (captain park, recruit ring, forced modes,
//     carry/pellet mutations, ground pin + seek) skipped.
//   * fixture mode = room preview or any non-bridge run; concessions stay.
//   * hover height floats low (30-60u) while the host body stays grounded.
//   * corpse probe fires about once per second (every 60 frames) and never on
//     tick 0, so the tail cannot flood the probe log.
//
// Exit 0 only if every check passes; any failure prints FAIL and exits 1.
#include "pc_p2_kurage_campaign.h"

#include <cstdio>
#include <fstream>
#include <string>
#include <vector>

namespace {

int failures = 0;

#define CHECK(cond, name) do { \
    if (cond) { std::printf("PASS %s\n", name); } \
    else { std::printf("FAIL %s\n", name); ++failures; } \
} while (0)

// Production-source audit (fixround Major-1): the header contract above is
// vacuous unless the production call sites actually honour it. A later edit
// deleting one !kurageCampaignMode() guard (e.g. around the captain park or
// the recruit ring) or re-enabling groundAndSeal in campaign must turn this
// test red. The audit scans the committed production source text, so it runs
// engine-free like the rest of this test.
std::string dirOf(const std::string& path)
{
    const size_t slash = path.find_last_of("/\\");
    return slash == std::string::npos ? std::string(".") : path.substr(0, slash);
}

bool readLines(const std::string& path, std::vector<std::string>& out)
{
    std::ifstream in(path);
    if (!in) return false;
    std::string line;
    while (std::getline(in, line)) out.push_back(line);
    return true;
}

std::string findProductionSource(const char* leaf)
{
    // __FILE__-derived first (robust to worktree location), then the known
    // absolute worktree path, then build-dir relatives (ctest runs from the
    // build dir: ../../wt/native-kurage == worktree).
    const std::string here = dirOf(__FILE__);
    const std::string candidates[] = {
        here + "/../pc_port/pc_p2_kurage_teki.cpp",
        here + "/" + leaf,
        std::string("C:/Users/alari/pikmin-randomizer/output/claude-orch/wt/native-kurage/") + leaf,
        std::string("pc_port/pc_p2_kurage_teki.cpp"),
        std::string("../wt/native-kurage/") + leaf,
        std::string("../../wt/native-kurage/") + leaf,
    };
    // leaf selects which file we want; the first candidate is always the teki
    // source, so rewrite it for the tekibteki hook lookup.
    for (const std::string& c : candidates) {
        std::string p = c;
        if (std::string(leaf) != "pc_port/pc_p2_kurage_teki.cpp") {
            const size_t pos = p.find("pc_port/pc_p2_kurage_teki.cpp");
            if (pos != std::string::npos) p = p.substr(0, pos) + leaf;
            else continue;
        }
        std::ifstream in(p);
        if (in) return p;
    }
    return std::string();
}

bool lineHas(const std::string& line, const char* needle)
{
    return line.find(needle) != std::string::npos;
}

} // namespace

int main()
{
    using namespace p2kurage_campaign;

    // Campaign gate: bridge without preview is campaign; everything else keeps
    // the labelled fixture concessions the room fixtures depend on.
    CHECK(isCampaignMode(true, false), "campaign-bridge-no-preview");
    CHECK(!isCampaignMode(true, true), "fixture-bridge-plus-preview");
    CHECK(!isCampaignMode(false, false), "fixture-no-bridge");
    CHECK(!isCampaignMode(false, true), "fixture-preview-only");
    CHECK(!fixtureConcessionsAllowed(true, false), "campaign-skips-concessions");
    CHECK(fixtureConcessionsAllowed(true, true), "preview-keeps-concessions");
    CHECK(fixtureConcessionsAllowed(false, false), "plain-keeps-concessions");

    // Hover: Jellyfloat-low, inside the 30-60u band, so the drawn bell floats
    // while the grounded host body stays in Pikmin reach.
    CHECK(kHoverHeight >= kHoverMin && kHoverHeight <= kHoverMax, "hover-in-band");
    CHECK(kHoverHeight == 40.0f, "hover-is-40");

    // Corpse probe: about once per second at 60fps, never on tick 0, never
    // mid-interval (the old per-30-call line flooded ~1260 lines / 100 s when
    // the tail ran once per teki per frame).
    CHECK(corpseProbeDue(60), "probe-due-60");
    CHECK(corpseProbeDue(120), "probe-due-120");
    CHECK(!corpseProbeDue(0), "probe-silent-0");
    CHECK(!corpseProbeDue(30), "probe-silent-30");
    CHECK(!corpseProbeDue(59), "probe-silent-59");
    CHECK(!corpseProbeDue(61), "probe-silent-61");
    CHECK(kCorpseProbeIntervalFrames == 60, "probe-interval-60");

    // Production gating audit: every resetPosition / ->changeMode site in the
    // production teki source must sit under a !kurageCampaignMode() guard
    // (campaign concessions skipped) or under the sShowcase opt-in path
    // (unreachable in campaign behind the !fsmEnabled early return).
    {
        const std::string tekiPath = findProductionSource("pc_port/pc_p2_kurage_teki.cpp");
        std::vector<std::string> lines;
        CHECK(!tekiPath.empty(), "production-source-found");
        CHECK(readLines(tekiPath, lines) && !lines.empty(), "production-source-readable");
        if (!lines.empty()) {
            int negGuards = 0, posGuards = 0, hoverUses = 0, probeUses = 0;
            int sealCalls = 0, sealCallLine = -1;
            for (size_t i = 0; i < lines.size(); ++i) {
                if (lineHas(lines[i], "kurageCampaignMode()")) ++posGuards;
                if (lineHas(lines[i], "!kurageCampaignMode()")) ++negGuards;
                if (lineHas(lines[i], "kHoverHeight")) ++hoverUses;
                if (lineHas(lines[i], "corpseProbeDue(")) ++probeUses;
                if (lineHas(lines[i], "groundAndSeal(t);")) { ++sealCalls; sealCallLine = int(i); }
            }
            CHECK(negGuards >= 4, "production-gating-guard-count");
            CHECK(posGuards >= 3, "production-campaign-branch-count");
            CHECK(sealCalls == 1, "production-seal-single-fixture-call");
            if (sealCallLine >= 0) {
                bool gated = false;
                for (int j = sealCallLine - 20; j < sealCallLine; ++j) {
                    if (j < 0) continue;
                    if (lineHas(lines[size_t(j)], "kurageCampaignMode()")
                        || lineHas(lines[size_t(j)], "} else {")) { gated = true; break; }
                }
                CHECK(gated, "production-seal-fixture-gated");
            } else {
                CHECK(false, "production-seal-fixture-gated");
            }
            CHECK(probeUses >= 1, "production-tail-rate-limited");
            CHECK(hoverUses >= 2, "production-hover-offset");

            int gatedSites = 0, ungatedSites = 0;
            for (size_t i = 0; i < lines.size(); ++i) {
                if (!lineHas(lines[i], "resetPosition") && !lineHas(lines[i], "->changeMode"))
                    continue;
                bool gated = false;
                for (int j = int(i) - 50; j < int(i); ++j) {
                    if (j < 0) continue;
                    if (lineHas(lines[size_t(j)], "!kurageCampaignMode()")
                        || lineHas(lines[size_t(j)], "sShowcase")) { gated = true; break; }
                }
                if (gated) ++gatedSites;
                else {
                    ++ungatedSites;
                    std::printf("UNCOVERED production line %d: %s\n", int(i) + 1, lines[i].c_str());
                }
            }
            CHECK(gatedSites >= 5, "production-gating-sites-seen");
            CHECK(ungatedSites == 0, "production-gating-no-ungated-reset-or-mode");
        }
        const std::string hookPath = findProductionSource("src/plugPikiNakata/tekibteki.cpp");
        std::vector<std::string> hookLines;
        CHECK(!hookPath.empty(), "production-corpse-hook-source-found");
        if (readLines(hookPath, hookLines) && !hookLines.empty()) {
            bool hook = false;
            for (const std::string& l : hookLines) {
                if (lineHas(l, "pc_p2_kurage_teki_draw") && (lineHas(l, "corpse") || lineHas(l, ", true)"))) { hook = true; break; }
            }
            CHECK(hook, "production-corpse-hook");
        } else {
            CHECK(false, "production-corpse-hook");
        }
    }

    if (failures == 0)
        std::printf("PASS P2_KURAGE_CAMPAIGN campaign_gated=1 hover=%.1f probe=1Hz\n",
                    double(kHoverHeight));
    else
        std::printf("P2_KURAGE_CAMPAIGN pass=0 failures=%d\n", failures);
    return failures == 0 ? 0 : 1;
}
