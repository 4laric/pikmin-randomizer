// Campaign Onion GoalItem lifecycle probe (rd-p2-campaign-goal-lifecycle, #836).
//
// Engine-linked census implementation. Strictly read-only: const iteration
// over the live managers, no birth/kill/mutation, no save I/O, no reward
// grant. See the header for the methodology note (MeltingPotMgr vs the
// ItemMgr pool) and exact production callsites.
#include "pc_p2_campaign_goal_probe.h"

#include "Creature.h"
#include "GoalItem.h"
#include "ItemMgr.h"
#include "ObjType.h"
#include "PlayerState.h"
#include "Traversable.h"

namespace {

int countGoals(Traversable* trav)
{
    if (!trav) return 0;
    int total = 0;
    Iterator it(trav);
    CI_LOOP(it)
    {
        Creature* creature = *it;
        if (creature && creature->mObjType == OBJTYPE_Goal) {
            ++total;
        }
    }
    return total;
}

} // namespace

P2CampaignGoalCensus pc_p2_campaign_goal_census()
{
    P2CampaignGoalCensus census;
    for (int color = 0; color < P2_GOAL_COLOR_COUNT; ++color) {
        census.container[color] = 0;
        census.discovered[color] = 0;
    }
    census.melt_total = 0;
    census.itemmgr_direct = 0;
    if (!itemMgr) {
        return census;
    }
    // Production lookup path (aiTransport.cpp, aiPut.cpp, demoEvent.cpp,
    // gameCoreSection.cpp, demoInvoker.cpp): per-color container through
    // the MeltingPotMgr pool.
    for (int color = 0; color < P2_GOAL_COLOR_COUNT; ++color) {
        census.container[color] = itemMgr->getContainer(color) != nullptr ? 1 : 0;
    }
    census.melt_total = countGoals(itemMgr->getMeltingPotMgr());
    // Legacy #830 census for side-by-side methodology comparison.
    census.itemmgr_direct = countGoals(itemMgr);
    if (playerState) {
        for (int color = 0; color < P2_GOAL_COLOR_COUNT; ++color) {
            census.discovered[color] = playerState->hasContainer(color) ? 1 : 0;
        }
    }
    return census;
}

int pc_p2_campaign_goal_itemmgr_direct()
{
    if (!itemMgr) return 0;
    return countGoals(itemMgr);
}

void pc_p2_campaign_goal_log(const char* tag, int tick)
{
    P2CampaignGoalCensus census = pc_p2_campaign_goal_census();
    char line[256];
    if (p2_campaign_goal_format(line, sizeof(line), tag ? tag : "P2_CAMPAIGN_GOAL_CENSUS",
            tick, &census) < 0) {
        std::printf("%s tick=%d FORMAT_ERROR\n", tag ? tag : "P2_CAMPAIGN_GOAL_CENSUS", tick);
    } else {
        std::printf("%s\n", line);
    }
    std::fflush(stdout);
}
