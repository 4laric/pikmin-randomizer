// Campaign Onion GoalItem lifecycle test (#836).
//
// Engine-free. Section A unit-checks the probe header helpers (color names,
// census line format/parse round-trip, malformed rejection, first-tick vs
// playable-state classification truth table). Section B validates captured
// runtime census logs with the same classifier: each vector below is a
// hand-made SYNTHETIC self-test of the validator, NOT natural evidence, and
// is labelled as such. Real classification runs against a captured engine
// log via argv[1] (one census line per line; other lines ignored).
//
// Exit 0 only if every check passes; any failure prints FAIL and exits 1.
#include "pc_p2_campaign_goal_probe.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

namespace {

int failures = 0;

#define CHECK(cond, name) do { \
    if (cond) { std::printf("PASS %s\n", name); } \
    else { std::printf("FAIL %s\n", name); ++failures; } \
} while (0)

P2CampaignGoalCensus makeCensus(int red, int blue, int yellow, int melt, int direct,
    int hr, int hb, int hy)
{
    P2CampaignGoalCensus census;
    census.container[P2_GOAL_RED] = red;
    census.container[P2_GOAL_BLUE] = blue;
    census.container[P2_GOAL_YELLOW] = yellow;
    census.melt_total = melt;
    census.itemmgr_direct = direct;
    census.discovered[P2_GOAL_RED] = hr;
    census.discovered[P2_GOAL_BLUE] = hb;
    census.discovered[P2_GOAL_YELLOW] = hy;
    return census;
}

// Validator input: parsed census rows in tick order.
struct Series {
    std::vector<int> ticks;
    std::vector<P2CampaignGoalCensus> rows;
};

const char* classifySeries(const Series& series)
{
    if (series.rows.empty()) return "no-census";
    bool first = series.rows[0].melt_total > 0;
    bool later = false;
    for (size_t i = 1; i < series.rows.size(); ++i) {
        if (series.rows[i].melt_total > 0) {
            later = true;
            break;
        }
    }
    return p2_campaign_goal_classify(first, later);
}

void sectionA()
{
    CHECK(std::strcmp(p2_campaign_goal_color_name(P2_GOAL_BLUE), "blue") == 0, "A/color-blue");
    CHECK(std::strcmp(p2_campaign_goal_color_name(P2_GOAL_RED), "red") == 0, "A/color-red");
    CHECK(std::strcmp(p2_campaign_goal_color_name(P2_GOAL_YELLOW), "yellow") == 0, "A/color-yellow");
    CHECK(std::strcmp(p2_campaign_goal_color_name(7), "unknown") == 0, "A/color-unknown");
    CHECK(P2_GOAL_BLUE == 0 && P2_GOAL_RED == 1 && P2_GOAL_YELLOW == 2, "A/color-indices-match-engine");

    P2CampaignGoalCensus census = makeCensus(1, 0, 0, 1, 0, 1, 0, 0);
    char line[256];
    CHECK(p2_campaign_goal_format(line, sizeof(line), "P2_CAMPAIGN_GOAL_CENSUS", 90, &census) > 0, "A/format-ok");
    CHECK(std::strstr(line, "tick=90") != nullptr, "A/format-tick");
    CHECK(std::strstr(line, "red=1") != nullptr, "A/format-red");
    CHECK(std::strstr(line, "melt_total=1") != nullptr, "A/format-melt");
    CHECK(std::strstr(line, "itemmgr_direct=0") != nullptr, "A/format-direct");
    CHECK(p2_campaign_goal_format(line, 10, "P2_CAMPAIGN_GOAL_CENSUS", 90, &census) < 0, "A/format-small-buffer");
    CHECK(p2_campaign_goal_format(nullptr, sizeof(line), "P2_CAMPAIGN_GOAL_CENSUS", 90, &census) < 0, "A/format-null-out");
    CHECK(p2_campaign_goal_format(line, sizeof(line), "P2_CAMPAIGN_GOAL_CENSUS", 90, nullptr) < 0, "A/format-null-census");

    char tag[64];
    int tick = -1;
    P2CampaignGoalCensus parsed = makeCensus(0, 0, 0, 0, 0, 0, 0, 0);
    const char* sample = "P2_CAMPAIGN_GOAL_CENSUS tick=90 red=1 blue=0 yellow=0 "
        "melt_total=1 itemmgr_direct=0 have_r=1 have_b=0 have_y=0";
    CHECK(p2_campaign_goal_parse(sample, tag, sizeof(tag), &tick, &parsed) == 0, "A/parse-ok");
    CHECK(std::strcmp(tag, "P2_CAMPAIGN_GOAL_CENSUS") == 0, "A/parse-tag");
    CHECK(tick == 90, "A/parse-tick");
    CHECK(parsed.container[P2_GOAL_RED] == 1 && parsed.melt_total == 1, "A/parse-values");
    CHECK(parsed.itemmgr_direct == 0 && parsed.discovered[P2_GOAL_RED] == 1, "A/parse-methodology-split");
    CHECK(p2_campaign_goal_parse("garbage line", tag, sizeof(tag), &tick, &parsed) != 0, "A/parse-rejects-garbage");
    CHECK(p2_campaign_goal_parse(nullptr, tag, sizeof(tag), &tick, &parsed) != 0, "A/parse-rejects-null");
    CHECK(p2_campaign_goal_parse(sample, nullptr, 0, &tick, &parsed) == 0, "A/parse-null-tag-ok");

    CHECK(std::strcmp(p2_campaign_goal_classify(true, true), "present-throughout") == 0, "A/classify-present");
    CHECK(std::strcmp(p2_campaign_goal_classify(false, true), "late-population") == 0, "A/classify-late");
    CHECK(std::strcmp(p2_campaign_goal_classify(true, false), "early-loss") == 0, "A/classify-early-loss");
    CHECK(std::strcmp(p2_campaign_goal_classify(false, false), "absent-through-playable-state") == 0, "A/classify-absent");
}

void sectionB()
{
    // Synthetic validator self-test vectors (NOT natural evidence).
    {
        Series present;
        present.ticks.push_back(1);
        present.rows.push_back(makeCensus(1, 0, 0, 1, 0, 1, 0, 0));
        present.ticks.push_back(91);
        present.rows.push_back(makeCensus(1, 0, 0, 1, 0, 1, 0, 0));
        CHECK(std::strcmp(classifySeries(present), "present-throughout") == 0, "B/synthetic-present");
    }
    {
        // The #830 shape: first-tick zero, later population.
        Series late;
        late.ticks.push_back(1);
        late.rows.push_back(makeCensus(0, 0, 0, 0, 0, 1, 0, 0));
        late.ticks.push_back(91);
        late.rows.push_back(makeCensus(1, 0, 0, 1, 0, 1, 0, 0));
        CHECK(std::strcmp(classifySeries(late), "late-population") == 0, "B/synthetic-late");
    }
    {
        // The methodology-gap shape: direct count zero while the
        // production container lookup is live through every row.
        Series gap;
        gap.ticks.push_back(1);
        gap.rows.push_back(makeCensus(1, 0, 0, 1, 0, 1, 0, 0));
        gap.ticks.push_back(91);
        gap.rows.push_back(makeCensus(1, 0, 0, 2, 0, 1, 0, 0));
        CHECK(std::strcmp(classifySeries(gap), "present-throughout") == 0, "B/synthetic-methodology-gap-present");
        CHECK(gap.rows[0].itemmgr_direct == 0 && gap.rows[0].container[P2_GOAL_RED] == 1, "B/synthetic-gap-split-visible");
    }
    {
        Series absent;
        absent.ticks.push_back(1);
        absent.rows.push_back(makeCensus(0, 0, 0, 0, 0, 1, 0, 0));
        absent.ticks.push_back(91);
        absent.rows.push_back(makeCensus(0, 0, 0, 0, 0, 1, 0, 0));
        CHECK(std::strcmp(classifySeries(absent), "absent-through-playable-state") == 0, "B/synthetic-absent");
    }
    {
        Series empty;
        CHECK(std::strcmp(classifySeries(empty), "no-census") == 0, "B/synthetic-empty");
    }
}

// Optional log mode: argv[1] is a captured engine log. Every
// P2_CAMPAIGN_GOAL_CENSUS line is parsed in order and classified; other
// lines are ignored. Prints the verdict and exits 0 on a well-formed
// series (any classification), 1 when no census line exists.
int logMode(const char* path)
{
    std::ifstream in(path);
    if (!in) {
        std::printf("FAIL log-open path=%s\n", path);
        return 1;
    }
    Series series;
    std::string line;
    int malformed = 0;
    while (std::getline(in, line)) {
        if (line.find("P2_CAMPAIGN_GOAL_CENSUS") == std::string::npos) continue;
        int tick = -1;
        P2CampaignGoalCensus census = makeCensus(0, 0, 0, 0, 0, 0, 0, 0);
        if (p2_campaign_goal_parse(line.c_str(), nullptr, 0, &tick, &census) != 0) {
            ++malformed;
            continue;
        }
        series.ticks.push_back(tick);
        series.rows.push_back(census);
    }
    if (series.rows.empty()) {
        std::printf("FAIL log-nocensus malformed=%d path=%s\n", malformed, path);
        return 1;
    }
    const P2CampaignGoalCensus& first = series.rows[0];
    const P2CampaignGoalCensus& last = series.rows.back();
    std::printf("P2_GOAL_LIFECYCLE_VERDICT rows=%d malformed=%d first_tick=%d "
        "first_red=%d first_melt=%d first_direct=%d last_tick=%d last_red=%d "
        "last_melt=%d classification=%s\n",
        int(series.rows.size()), malformed, series.ticks[0],
        first.container[P2_GOAL_RED], first.melt_total, first.itemmgr_direct,
        series.ticks.back(), last.container[P2_GOAL_RED], last.melt_total,
        classifySeries(series));
    std::fflush(stdout);
    return 0;
}

} // namespace

int main(int argc, char** argv)
{
    if (argc > 1) {
        return logMode(argv[1]);
    }
    sectionA();
    sectionB();
    if (failures) {
        std::printf("FAIL p2_campaign_goal_lifecycle_test failures=%d\n", failures);
        return 1;
    }
    std::printf("PASS p2_campaign_goal_lifecycle_test\n");
    return 0;
}
