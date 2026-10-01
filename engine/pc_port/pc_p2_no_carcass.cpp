#include "pc_p2_no_carcass.h"
#include "pc_p2_no_carcass_policy.h"
#include "pc_p2_campaign_actor.h"
#include "pc_randomizer.h"
#include "FlowController.h"
#include "MoviePlayer.h"
#include "gameflow.h"
#include "teki.h"
#include <cstdio>

int pc_p2_no_carcass_corpse_type(BTeki* actor, int value)
{
    if (!actor || (value != TEKICORPSE_LeaveCorpse && value != TEKICORPSE_NoCorpse)) return value;
    unsigned source = pc_randomizer_p2_source_for(static_cast<PelletView*>(actor));
    if (!source) source = pc_p2_campaign_source(actor);
    const int type = p2nocarcass::corpseType(source, value);
    if (p2nocarcass::leavesNoCarcass(source)) {
        static bool logged[102] = {};
        if (source < 102 && !logged[source]) {
            logged[source] = true;
            std::printf("P2_NO_CARCASS source_id=%u corpse=none source_carcass=0\n", source);
            std::fflush(stdout);
        }
    }
    return type;
}

void pc_p2_no_carcass_forget(BTeki* actor)
{
    if (!actor) return;
    const auto view = static_cast<PelletView*>(actor);
    const unsigned source = pc_randomizer_p2_source_for(view);
    // Combat availability (#1064) also becomes false during a death clip.
    // Only dieSoon's host flag distinguishes a completed kill from teardown.
    if (!p2nocarcass::killEarnsReceipt(source, actor->getTekiOption(TEKIOPT_Alive))) return;
    const unsigned generator = pc_randomizer_p2_generator_for(view);
    const int stage = flowCont.mCurrentStage ? flowCont.mCurrentStage->mStageID : -1;
    // Same gameplay gate as the Onion corpse receipt (GoalItem::suckMe).
    const bool gameplay = !gameflow.mIsChallengeMode && !gameflow.mPauseAll && !gameflow.mIsUIOverlayActive
        && !gameflow.mMoviePlayer->mIsActive;
    const bool handled = stage >= 0 && pc_randomizer_p2_killed(view, actor->mTekiType, stage, gameplay);
    std::printf("P2_NO_CARCASS_KILL source_id=%u generator=%u stage=%d gameplay=%d receipt=%d\n", source, generator,
                stage, int(gameplay), int(handled));
    std::fflush(stdout);
}
