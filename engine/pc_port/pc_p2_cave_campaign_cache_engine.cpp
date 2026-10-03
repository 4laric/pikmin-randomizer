#include "pc_p2_cave_campaign_cache_engine.h"
#include "pc_p2_cave_campaign_cache.h"
#include "pc_randomizer.h"
#include "Generator.h"
#include "Stream.h"
#include <cstdio>
#include <cstdlib>

namespace {
[[noreturn]] void invalid(const char* reason) {
    std::fprintf(stderr,"Invalid generated campaign cache: %s\n",reason);std::abort();
}
std::string capture() {
    if(!generatorCache)invalid("missing native cache");
    static_assert(GENCACHE_HEAP_SIZE==P2CaveCacheBanks::heapSize);
    static_assert(STAGE_START==0 && STAGE_COUNT==5);
    std::string bytes(P2CaveCacheBanks::imageSize,'\0');
    RamStream stream(&bytes[0],int(bytes.size()));
    generatorCache->saveCard(stream);
    if(stream.getPosition()!=int(bytes.size())||!P2CaveCacheBanks::imageValid(bytes))
        invalid("native snapshot layout");
    return bytes;
}
void restore(std::string bytes) {
    if(!generatorCache||!P2CaveCacheBanks::imageValid(bytes))invalid("invalid restore image");
    RamStream stream(&bytes[0],int(bytes.size()));
    generatorCache->loadCard(stream);
    if(stream.getPosition()!=int(bytes.size()))invalid("native restore length");
}
}
void pc_p2_cave_campaign_cache_enter(int surfaceStage) {
    if(surfaceStage!=STAGE_Forest)invalid("foreign entry surface");
    auto banks=pc_randomizer_generated_cave_cache();
    if(!banks.enter(capture()))invalid("duplicate or invalid entry");
    pc_randomizer_generated_cave_cache_set(banks);
    generatorCache->initGame();
    if(!banks.floor.empty())restore(banks.floor);
}
void pc_p2_cave_campaign_cache_return() {
    auto banks=pc_randomizer_generated_cave_cache();
    const auto surface=banks.surface;
    if(!banks.leave(capture()))invalid("return outside cave");
    pc_randomizer_generated_cave_cache_set(banks);
    restore(surface);
}
void pc_p2_cave_campaign_cache_capture() {
    if(!pc_randomizer_generated_cave())return;
    auto banks=pc_randomizer_generated_cave_cache();
    if(!banks.inside)return;
    if(!banks.captureFloor(capture()))invalid("floor save snapshot");
    pc_randomizer_generated_cave_cache_set(banks);
}
void pc_p2_cave_campaign_cache_restore_floor() {
    const auto& banks=pc_randomizer_generated_cave_cache();
    if(!banks.inside)invalid("floor restore outside cave");
    if(!generatorCache)invalid("missing native cache");
    generatorCache->initGame();
    if(!banks.floor.empty())restore(banks.floor);
}
