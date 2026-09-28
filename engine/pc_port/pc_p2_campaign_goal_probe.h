#ifndef PC_P2_CAMPAIGN_GOAL_PROBE_H
#define PC_P2_CAMPAIGN_GOAL_PROBE_H
// Campaign Onion GoalItem lifecycle probe (rd-p2-campaign-goal-lifecycle, #836).
//
// Read-only observer over the REAL production goal path. It never births a
// GoalItem, never mutates discovery/save state, never grants a reward, never
// edits species behavior or pools, and never touches the user's game.
//
// Background (#830 gen-4): the Sarai campaign harness counted Onion goals
// with `Iterator git(itemMgr)` filtering `OBJTYPE_Goal` and saw zero at its
// first gameplay tick despite a retail red-goal generator record in
// stage1/default.gen. GoalItems are birthed into ItemMgr::mMeltingPotMgr
// (see ItemMgr::birth in src/plugPikiKando/itemMgr.cpp, which forwards
// OBJTYPE_Goal to MeltingPotMgr::birth), NOT into ItemMgr's own
// PolyObjectMgr pool. `Iterator(itemMgr)` only walks the latter, so that
// census always reads zero even with live Onions. Production code reads
// goals through ItemMgr::getContainer(color), which walks mMeltingPotMgr
// (src/plugPikiKando/itemMgr.cpp); ItemMgr::refresh2d iterates BOTH pools,
// proving they are distinct. This probe emits both counts side by side so a
// zero-direct/positive-container split is visible instead of silent.
//
// Engine colors: Blue=0, Red=1, Yellow=2 (include/GlobalGameOptions.h).
// This header is engine-free includable: it declares the engine-linked
// census and provides inline format/parse helpers tested without an engine.

#include <cstdio>
#include <cstring>

enum P2CampaignGoalColor {
    P2_GOAL_BLUE = 0,
    P2_GOAL_RED = 1,
    P2_GOAL_YELLOW = 2,
    P2_GOAL_COLOR_COUNT = 3
};

inline const char* p2_campaign_goal_color_name(int color)
{
    switch (color) {
    case P2_GOAL_BLUE: return "blue";
    case P2_GOAL_RED: return "red";
    case P2_GOAL_YELLOW: return "yellow";
    default: return "unknown";
    }
}

// One read-only census row. `container[c]` mirrors
// ItemMgr::getContainer(c) != nullptr (the production lookup the delivery
// path uses in aiTransport/aiPut/demoEvent/gameCoreSection). `melt_total`
// counts OBJTYPE_Goal actors visible through getMeltingPotMgr().
// `itemmgr_direct` repeats the legacy Iterator(itemMgr) count that #830
// used; it is expected to stay zero while Onions live (methodology gap,
// not absence). `discovered[c]` mirrors playerState->hasContainer(c).
struct P2CampaignGoalCensus {
    int container[P2_GOAL_COLOR_COUNT];
    int discovered[P2_GOAL_COLOR_COUNT];
    int melt_total;
    int itemmgr_direct;
};

// Engine-linked: implemented in pc_p2_campaign_goal_probe.cpp against the
// live itemMgr/playerState singletons. Read-only.
P2CampaignGoalCensus pc_p2_campaign_goal_census();
int pc_p2_campaign_goal_itemmgr_direct();
void pc_p2_campaign_goal_log(const char* tag, int tick);

// Engine-free line format shared by the runtime emitter and the log
// validator compiled into tools/p2_campaign_goal_lifecycle_test.cpp.
// Returns the byte count (excluding NUL) or -1 when the buffer is too small.
inline int p2_campaign_goal_format(char* out, int cap, const char* tag, int tick,
    const P2CampaignGoalCensus* census)
{
    if (!out || cap <= 0 || !tag || !census) return -1;
    int n = std::snprintf(out, cap,
        "%s tick=%d red=%d blue=%d yellow=%d melt_total=%d itemmgr_direct=%d "
        "have_r=%d have_b=%d have_y=%d",
        tag, tick,
        census->container[P2_GOAL_RED], census->container[P2_GOAL_BLUE],
        census->container[P2_GOAL_YELLOW],
        census->melt_total, census->itemmgr_direct,
        census->discovered[P2_GOAL_RED], census->discovered[P2_GOAL_BLUE],
        census->discovered[P2_GOAL_YELLOW]);
    if (n < 0 || n >= cap) return -1;
    return n;
}

// Engine-free parse of one formatted line back into a census. Returns 0 on
// success, -1 on malformed input. `tag_out` may be null.
inline int p2_campaign_goal_parse(const char* line, char* tag_out, int tag_cap,
    int* tick_out, P2CampaignGoalCensus* census)
{
    if (!line || !tick_out || !census) return -1;
    char tag[64];
    int tick, red, blue, yellow, melt, direct, hr, hb, hy;
    int matched = std::sscanf(line,
        "%63s tick=%d red=%d blue=%d yellow=%d melt_total=%d itemmgr_direct=%d "
        "have_r=%d have_b=%d have_y=%d",
        tag, &tick, &red, &blue, &yellow, &melt, &direct, &hr, &hb, &hy);
    if (matched != 10) return -1;
    if (tag_out && tag_cap > 0) {
        std::snprintf(tag_out, tag_cap, "%s", tag);
    }
    tick_out[0] = tick;
    census->container[P2_GOAL_RED] = red;
    census->container[P2_GOAL_BLUE] = blue;
    census->container[P2_GOAL_YELLOW] = yellow;
    census->melt_total = melt;
    census->itemmgr_direct = direct;
    census->discovered[P2_GOAL_RED] = hr;
    census->discovered[P2_GOAL_BLUE] = hb;
    census->discovered[P2_GOAL_YELLOW] = hy;
    return 0;
}

// Classification of a time series of censuses: the exact distinction #836
// requires. `first_tick_present` covers the #830 observation point;
// `later_present` covers any census after the first (playable state).
// Returns one of the static strings below (never null).
inline const char* p2_campaign_goal_classify(bool first_tick_present, bool later_present)
{
    if (first_tick_present && later_present) return "present-throughout";
    if (!first_tick_present && later_present) return "late-population";
    if (first_tick_present && !later_present) return "early-loss";
    return "absent-through-playable-state";
}

#endif
