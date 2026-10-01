// TEST-ONLY day-cycle driver (#246). See pc_p2_test_day_cycle.h.
#include "pc_p2_test_day_cycle.h"

#include "FlowController.h"
#include "gameflow.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#include "pc_p2_teki_lifetime.h"

namespace {
struct Step {
    std::string kind;
    float seconds = 0.0f;
};

bool sParsed = false;
std::vector<Step> sSteps;
unsigned long sGeneration = 0;
bool sHaveGeneration = false;
int sStep = 0;
float sSinceBegin = 0.0f;
float sHurtAt = -1.0f;
float sDeliveredAt = -1.0f;
bool sFired = false;
bool sAdvancing = false;
bool sMapPending = false;
int sStageId = -1;
float sDoneTimer = 0.0f;
bool sDone = false;

void parse()
{
    if (sParsed) return;
    sParsed = true;
    const char* env = std::getenv("PIKMIN_P2_TEST_DAY_CYCLE");
    if (!env || !*env) return;
    std::string spec(env);
    std::size_t at = 0;
    while (at <= spec.size()) {
        std::size_t end = spec.find(',', at);
        if (end == std::string::npos) end = spec.size();
        const std::string item = spec.substr(at, end - at);
        const std::size_t colon = item.find(':');
        if (colon != std::string::npos) {
            Step s;
            s.kind = item.substr(0, colon);
            s.seconds = float(std::atof(item.c_str() + colon + 1));
            if (s.kind == "hurt" || s.kind == "receipt" || s.kind == "time") sSteps.push_back(s);
        }
        at = end + 1;
    }
    std::printf("TEST_ONLY P2_TEST_DAY_CYCLE spec=%s steps=%zu\n", env, sSteps.size());
    std::fflush(stdout);
}
} // namespace

bool pc_p2_test_day_cycle_active()
{
    parse();
    return !sSteps.empty();
}

bool pc_p2_test_day_cycle_due(float dt)
{
    if (!pc_p2_test_day_cycle_active()) return false;
    const unsigned long gen = pc_p2_scene_generation();
    if (!sHaveGeneration || gen != sGeneration) {
        if (sHaveGeneration && sAdvancing) ++sStep;
        sHaveGeneration = true;
        sGeneration = gen;
        sSinceBegin = 0.0f;
        sHurtAt = sDeliveredAt = -1.0f;
        sFired = sAdvancing = sMapPending = false;
        sDoneTimer = 0.0f;
        sStageId = flowCont.mCurrentStage ? flowCont.mCurrentStage->mStageID : -1;
        std::printf("TEST_ONLY P2_TEST_DAY_CYCLE_STAGE step=%d day=%d stage=%d scene=%lu\n", sStep,
                    gameflow.mWorldClock.mCurrentDay, sStageId, gen);
        std::fflush(stdout);
    }
    if (dt > 0.0f && dt < 0.5f) sSinceBegin += dt;
    if (sStep >= int(sSteps.size())) {
        sDoneTimer += dt > 0.0f && dt < 0.5f ? dt : 0.0f;
        if (!sDone && sDoneTimer >= 60.0f) {
            sDone = true;
            std::printf("TEST_ONLY P2_TEST_DAY_CYCLE_DONE day=%d stage=%d\n", gameflow.mWorldClock.mCurrentDay,
                        sStageId);
            std::fflush(stdout);
        }
        return false;
    }
    if (sFired) return false;
    const Step& s = sSteps[std::size_t(sStep)];
    float anchor = -1.0f;
    if (s.kind == "time") anchor = 0.0f;
    else if (s.kind == "hurt") anchor = sHurtAt;
    else if (s.kind == "receipt") anchor = sDeliveredAt;
    if (anchor < 0.0f || sSinceBegin - anchor < s.seconds) return false;
    sFired = sAdvancing = sMapPending = true;
    std::printf("TEST_ONLY P2_TEST_DAY_CYCLE_SUNSET step=%d reason=%s day=%d stage=%d t=%.1f\n", sStep, s.kind.c_str(),
                gameflow.mWorldClock.mCurrentDay, sStageId, sSinceBegin);
    std::fflush(stdout);
    return true;
}

bool pc_p2_test_day_cycle_advancing()
{
    return pc_p2_test_day_cycle_active() && sAdvancing;
}

bool pc_p2_test_day_cycle_mapselect(int* stageId)
{
    if (!pc_p2_test_day_cycle_active() || !sMapPending || sStageId < 0) return false;
    sMapPending = false;
    if (stageId) *stageId = sStageId;
    std::printf("TEST_ONLY P2_TEST_DAY_CYCLE_MAPSELECT stage=%d day=%d\n", sStageId, gameflow.mWorldClock.mCurrentDay);
    std::fflush(stdout);
    return true;
}

void pc_p2_test_day_cycle_note(const char* event)
{
    if (!pc_p2_test_day_cycle_active() || !event) return;
    if (!std::strcmp(event, "hurt") && sHurtAt < 0.0f) sHurtAt = sSinceBegin;
    if (!std::strcmp(event, "delivered") && sDeliveredAt < 0.0f) sDeliveredAt = sSinceBegin;
}
