#include "pc_p2_campaign_flush.h"
#include "Generator.h"
#include "FlowController.h"
#include "Pellet.h"
#include "PlayerState.h"
#include "gameflow.h"
#include "pc_p2_cave_campaign_cache.h"
#include "pc_p2_cave_campaign_cache_engine.h"
#include <vector>

PcP2CampaignLiveCache::PcP2CampaignLiveCache():image(pc_p2_campaign_cache_image()){
    Generator* gen;
    FOREACH_NODE_REUSE(Generator,generatorList->mGenListHead->mChild,gen)
        indices.emplace_back(gen,gen->mGeneratorListIdx);
}
void PcP2CampaignLiveCache::restore() const {
    pc_p2_campaign_cache_restore_image(image);
    for(const auto& saved:indices)saved.first->mGeneratorListIdx=saved.second;
}

bool pc_p2_campaign_flush(std::string& reason) {
    if (!flowCont.mCurrentStage || !generatorCache || !generatorList
        || !generatorList->mGenListHead || !pelletMgr || !playerState) {
        reason = "missing live generator flush context";
        return false;
    }
    const unsigned stage = flowCont.mCurrentStage->mStageIndex;
    if (stage >= STAGE_COUNT) {
        reason = "foreign native cache directory key";
        return false;
    }
    const PcP2CampaignLiveCache previous;
    unsigned expectedGenerators=0,expectedCreatures=0,expectedParts=0;
    Generator* observed;
    FOREACH_NODE_REUSE(Generator,generatorList->mGenListHead->mChild,observed){
        if(!(observed->mCarryOverFlags&GENCARRY_SaveGenerator))continue;
        if(observed->mDayLimit==-1||observed->mDayLimit>gameflow.mWorldClock.mCurrentDay)++expectedGenerators;
        if((observed->mCarryOverFlags&GENCARRY_SaveCreature)&&!observed->isExpired()
            &&observed->mLatestSpawnCreature)++expectedCreatures;
    }
    generatorCache->beginSave(stage);
    Generator* gen;
    FOREACH_NODE_REUSE(Generator, generatorList->mGenListHead->mChild, gen) {
        if (gen->mCarryOverFlags & GENCARRY_SaveGenerator)
            generatorCache->saveGenerator(gen);
    }
    FOREACH_NODE_REUSE(Generator, generatorList->mGenListHead->mChild, gen) {
        if ((gen->mCarryOverFlags & GENCARRY_SaveGenerator)
            && (gen->mCarryOverFlags & GENCARRY_SaveCreature))
            generatorCache->saveGeneratorCreature(gen);
    }
    Iterator pellets(pelletMgr);
    CI_LOOP(pellets) {
        auto* pellet = static_cast<Pellet*>(*pellets);
        if (pellet->mConfig && pellet->mConfig->mPelletType() == PELTYPE_UfoPart) {
            if(!playerState->hasUfoParts(pellet->mConfig->mModelId.mId))++expectedParts;
            generatorCache->saveUfoParts(pellet);
        }
    }
    generatorCache->endSave();
    const auto image=pc_p2_campaign_cache_image();
    auto word=[&](unsigned offset){unsigned value=0;
        for(unsigned i=0;i<4;++i)value=(value<<8)|static_cast<unsigned char>(image[offset+i]);
        return value;};
    const auto entry=8+P2CaveCacheBanks::heapSize+stage*37+1;
    if(word(entry+24)!=expectedGenerators||word(entry+28)!=expectedCreatures||word(entry+32)!=expectedParts){
        previous.restore();
        reason="native cache omitted a live record (capacity exhausted)";
        return false;
    }
    reason.clear();
    return true;
}
