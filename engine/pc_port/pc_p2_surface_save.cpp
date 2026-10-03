#include "pc_p2_surface_save.h"
#include "pc_p2_campaign_flush.h"
#include "pc_p2_cave_survivor_permit.h"
#include "WorkObject.h"
#include <set>
#include "pc_p2_cave_campaign_cache_engine.h"
#include "pc_p2_cave_campaign_party_engine.h"
#include "pc_p2_original_actor.h"
#include "pc_randomizer.h"
#include "FlowController.h"
#include "Generator.h"
#include "OnePlayerSection.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PlayerState.h"
#include "MoviePlayer.h"
#include "ItemMgr.h"
#include "Pellet.h"
#include "Boss.h"
#include "teki.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "PikiHeadItem.h"
#include "gameflow.h"
#include "zen/ogFileChkSel.h"
#include "Controller.h"
#include <SDL.h>
#include <array>
#include <cstdio>
#include <cstdlib>

namespace {
zen::ogScrFileChkSelMgr* choice=nullptr;
bool choosing=false, requested=false, restoring=false, restored=false, bindingParty=false;
std::uint64_t selectedGeneration=0;
std::array<std::uint8_t,32> selectedSha{};
[[noreturn]] void invalid(const char* why){std::fprintf(stderr,"Invalid living surface SAVE: %s\n",why);std::abort();}
bool proof(){
    selectedSha.fill(0);selectedGeneration=0;
    if(!pc_randomizer_checkpoint_info(&selectedGeneration,selectedSha.data())||!selectedGeneration
        ||selectedGeneration!=pc_randomizer_active_campaign_generation())return false;
    for(auto byte:selectedSha)if(byte)return true;
    return false;
}
bool sameProof(){
    std::uint64_t generation=0;std::array<std::uint8_t,32> digest{};
    return selectedGeneration&&selectedGeneration==pc_randomizer_active_campaign_generation()
        &&pc_randomizer_checkpoint_info(&generation,digest.data())
        &&generation==selectedGeneration&&digest==selectedSha;
}
bool held(const char* why){std::printf("P2_SURFACE_SAVE_HELD reason=%s\n",why);return false;}
bool settled(){
    if(pc_randomizer_original_session())return held("original_graph_restore_pending");
    if(!pc_randomizer_ready()||pc_randomizer_netplay_agreed_saves()||pc_randomizer_generated_cave()
        ||!playerState||playerState->isChallengeMode()||!flowCont.mCurrentStage
        ||gameflow.mPauseAll||gameflow.mIsUIOverlayActive||gameflow.mIsDayEndActive
        ||gameflow.mIsDayEndTriggered||!gameflow.mMoviePlayer||gameflow.mMoviePlayer->mIsActive)
        return held("scene_not_available");
    // The current native card cache does not preserve live enemy FSMs, loose
    // cargo or original group saved-creature payloads. Never qualify their
    // regeneration as an exact mid-day resume.
    if(!p2original::originalActors().rows().empty())return held("original_group_restore_pending");
    if(!tekiMgr||!bossMgr||!pelletMgr||!pikiMgr||!itemMgr)return held("missing_managers");
    if(!generatorList||!generatorList->mGenListHead)return held("missing_generator_authority");
    std::set<Generator*> savedSources;
    Generator* source;
    FOREACH_NODE_REUSE(Generator,generatorList->mGenListHead->mChild,source){
        if(source->isExpired())continue;
        // Native SaveCreature retains only mLatestSpawnCreature. Its exact
        // properties cannot stand in for a grouped source's other actors.
        if(source->mAliveCount<0||source->mAliveCount>1
            ||(source->mAliveCount==1&&(!source->mLatestSpawnCreature||!source->mLatestSpawnCreature->isAlive()))
            ||(source->mAliveCount==0&&source->mLatestSpawnCreature))
            return held("source_actor_cardinality_restore_pending");
        if(source->mCarryOverFlags>15||source->mDayLimit<-1||source->mDayLimit>32767
            ||!source->mGenObject||!source->mGenArea||!source->mGenType)
            return held("unsupported_source_record");
        savedSources.insert(source);
    }
    auto serializedActor=[&](Creature* actor){
        auto* gen=actor->mGenerator;
        return gen&&savedSources.count(gen)&&gen->mLatestSpawnCreature==actor
            &&gen->mAliveCount==1;
    };
    for(ObjectMgr* manager:{static_cast<ObjectMgr*>(tekiMgr),static_cast<ObjectMgr*>(bossMgr),static_cast<ObjectMgr*>(pelletMgr)}){
        Iterator actors(manager);CI_LOOP(actors){auto* actor=static_cast<Creature*>(*actors);
            if(actor)return held("live_enemy_or_cargo_restore_pending");}}
    if(itemMgr->getContainerExitCount())return held("onion_transfer_in_progress");
    if(!naviMgr)return held("missing_captain_manager");
    for(int i=0;i<naviMgr->getNaviCount();++i){auto* n=naviMgr->getNavi(i);
        if(!n||!n->getCurrState()||n->getCurrState()->getID()!=NAVISTATE_Walk)
            return held("unsettled_captain");}
    Iterator bodies(pikiMgr);CI_LOOP(bodies){auto* body=static_cast<Piki*>(*bodies);
        // Party3 authenticates original-source flags, but the physical source
        // factory/cache restore composition is still unqualified here.
        OriginalPikiBody originalBody;
        if(body->isAlive()&&(body->mGenerator||pc_p2_original_piki_body_query(body,originalBody)
            ||body->mP2Bulbmin||body->mMode>1||body->isHolding()))
            return held("unsupported_body_state");}
    if(!itemMgr->getPikiHeadMgr())return held("missing_head_manager");
    Iterator heads(itemMgr->getPikiHeadMgr());CI_LOOP(heads){auto* h=static_cast<PikiHeadItem*>(*heads);
        if(h->mGenerator)return held("source_head_restore_pending");}
    Iterator items(itemMgr);CI_LOOP(items){auto* item=static_cast<Creature*>(*items);
        if(!item)continue;
        if(item->mObjType!=OBJTYPE_Pikihead&&!serializedActor(item))
            return held("world_item_source_authority_missing");
        switch(item->mObjType){
        case OBJTYPE_Goal:case OBJTYPE_Ufo:case OBJTYPE_Pikihead:
        case OBJTYPE_SluiceSoft:case OBJTYPE_SluiceHard:case OBJTYPE_SluiceBomb:case OBJTYPE_SluiceBombHard:
        break;
        default:return held("world_item_restore_pending");
        }
    }
    if(!workObjectMgr)return held("missing_work_object_manager");
    Iterator works(workObjectMgr);CI_LOOP(works){auto* work=static_cast<WorkObject*>(*works);
        if(!work)continue;
        if(!serializedActor(work))return held("work_object_source_authority_missing");
        if(!work->isBridge()&&!work->isHinderRock())return held("work_object_codec_unsupported");
        if(work->isHinderRock()){
            const auto* rock=static_cast<HinderRock*>(work);
            if(rock->mState==1||rock->mPushingPikmin||rock->mPushMoveTimer!=0)
                return held("work_object_transition_in_progress");
        }
    }
    return true;
}
// The mid-day card needs a full exact source snapshot even when authored
// carry flags intentionally discard it at sunset. These transient flags never
// become gameplay policy: the authenticated descriptor keeps the authored
// values and both live continuation and cold restoration restore them.
class SurfaceSourceSerialization {
    struct Live {Generator* gen;unsigned flags;int dayLimit;};
    std::vector<Live> originals;
public:
    explicit SurfaceSourceSerialization(P2SurfaceSession& session){
        session.sources.clear();
        Generator* gen;
        FOREACH_NODE_REUSE(Generator,generatorList->mGenListHead->mChild,gen){
            if(gen->isExpired())continue;
            originals.push_back({gen,gen->mCarryOverFlags,gen->mDayLimit});
            session.sources.push_back({gen->mCarryOverFlags,gen->mDayLimit,gen->mAliveCount,
                gen->mLatestSpawnDay,gen->mRespawnInterval,
                {gen->mGenPosition.x,gen->mGenPosition.y,gen->mGenPosition.z},
                {gen->mGenOffset.x,gen->mGenOffset.y,gen->mGenOffset.z}});
            gen->mCarryOverFlags=GENCARRY_SaveGenerator|GENCARRY_SaveSpawnCount
                |GENCARRY_SaveCreature|GENCARRY_SaveProperties;
            if(gen->mDayLimit==gameflow.mWorldClock.mCurrentDay)++gen->mDayLimit;
        }
    }
    ~SurfaceSourceSerialization(){for(const auto& live:originals){
        live.gen->mCarryOverFlags=live.flags;live.gen->mDayLimit=live.dayLimit;}}
};
void restoreSourcePolicy(const P2SurfaceSession& saved,bool afterLoad){
    if(saved.sources.empty())return; // Legacy restricted version1 descriptor.
    std::vector<bool> seen(saved.sources.size(),false);
    Generator* gen;
    FOREACH_NODE_REUSE(Generator,generatorList->mGenListHead->mChild,gen){
        const int index=gen->mGeneratorListIdx;
        if(index<0||std::size_t(index)>=saved.sources.size()||seen[index]
            ||!gen->readFromRam()||gen->mCarryOverFlags!=15)invalid("cold source policy identity mismatch");
        if(afterLoad&&(gen->mAliveCount!=saved.sources[index].aliveCount
            ||(gen->mAliveCount==1&&(!gen->mLatestSpawnCreature||!gen->mLatestSpawnCreature->isAlive()))
            ||(gen->mAliveCount==0&&gen->mLatestSpawnCreature)))invalid("cold source actor restoration failed");
        seen[index]=true;
        const auto& source=saved.sources[index];
        gen->mGenPosition.set(source.position.x,source.position.y,source.position.z);
        gen->mGenOffset.set(source.offset.x,source.offset.y,source.offset.z);
        gen->mLatestSpawnDay=source.latestSpawnDay;gen->mRespawnInterval=source.respawnInterval;
        if(afterLoad){gen->mCarryOverFlags=source.flags;gen->mDayLimit=source.dayLimit;}
    }
    for(bool found:seen)if(!found)invalid("cold source policy record absent");
}
bool commit(){
    if(!settled())return false;
    const auto oldSession=pc_randomizer_surface_session();
    P2SurfaceSession next;next.present=true;
    auto* stage=flowCont.mCurrentStage;
    next.stage=stage->mStageID;next.index=stage->mStageIndex;
    next.day=gameflow.mWorldClock.mCurrentDay;
    if(!stage->mFileName)return held("missing_surface_file");next.file=stage->mFileName;
    next.party=oldSession.party;
    next.party.surfaceTime=gameflow.mWorldClock.mTimeOfDay;
    if(!pc_p2_cave_campaign_party_capture(next.party,false)||!next.valid())return held("unsettled_party");
    if(gameflow.mGamePrefs.mSpareMemCardSaveIndex<1||gameflow.mGamePrefs.mSpareMemCardSaveIndex>4)
        return held("no_selected_native_slot");
    // Preserve the PRE-flush image. A failed physical card write must not
    // replace a prior scene cache while gameplay continues.
    const PcP2CampaignLiveCache oldCache;
    const auto oldPlayState=gameflow.mPlayState;
    SurfaceSourceSerialization serialization(next);
    if(!next.valid())return held("invalid_authored_source_policy");
    std::string reason;
    if(!pc_p2_campaign_flush(reason))return held(reason.c_str());
    pc_randomizer_surface_session_set(next);
    const auto before=pc_randomizer_active_campaign_generation();
    gameflow.mMemoryCard.saveCurrentGame();
    if(pc_randomizer_active_campaign_generation()<=before){
        oldCache.restore();
        pc_randomizer_surface_session_set(oldSession);
        gameflow.mPlayState=oldPlayState;
        return held("native_card_failed_rolled_back");
    }
    if(!proof())invalid("committed checkpoint proof unavailable");
    // endSave makes the serialized stage ALIVE; live gameplay's next normal
    // day end/second F11 expects its consumed DEAD entry. Preserve that actual
    // lifecycle without reloading/spawning the scene on top of itself.
    oldCache.restore();
    std::printf("P2_SURFACE_SAVED generation=%llu day=%d time=%.9g stage=%d bodies=%zu heads=%zu options_failed=%d\n",
        static_cast<unsigned long long>(selectedGeneration),next.day,next.party.surfaceTime,next.stage,
        next.party.bodies.size(),next.party.surfaceHeads.size(),int(gameflow.mMemoryCard.didSaveFail()));
    return true;
}
}
bool pc_p2_surface_save_resume_scene(){
    const auto& saved=pc_randomizer_surface_session();
    if(!saved.present)return false;
    if(!pc_randomizer_resumed()||!saved.valid()||!proof()||pc_randomizer_generated_cave()
        ||pc_randomizer_netplay_agreed_saves()
        ||gameflow.mWorldClock.mCurrentDay!=saved.day)invalid("unauthenticated or inconsistent surface descriptor");
    StageInfo* match=nullptr;
    FOREACH_NODE(StageInfo,flowCont.mStageList.mChild,stage){
        if(stage->mStageID==saved.stage&&stage->mStageIndex==saved.index
            &&stage->mFileName&&saved.file==stage->mFileName){if(match)invalid("ambiguous resume scene");match=stage;}}
    if(!match)invalid("saved scene absent from installed source");
    flowCont.mCurrentStage=match;gameflow.mCurrentStageID=saved.stage;
    std::snprintf(flowCont.mCurrStageFilePath,sizeof(flowCont.mCurrStageFilePath),"%s",match->mFileName);
    std::snprintf(flowCont.mDoorStageFilePath,sizeof(flowCont.mDoorStageFilePath),"%s",match->mFileName);
    gameflow.mWorldClock.setTime(saved.party.surfaceTime);restoring=true;
    return true;
}
bool pc_p2_surface_save_owns_heads(){return restoring&&pc_randomizer_surface_session().present;}
bool pc_p2_surface_save_living_scene(){return restoring||restored;}
void pc_p2_surface_save_sources_preinit(){
    if(!restoring)return;
    if(!sameProof())invalid("selected checkpoint changed before source init");
    restoreSourcePolicy(pc_randomizer_surface_session(),false);
}
void pc_p2_surface_save_sources_loaded(){
    if(!restoring)return;
    if(!sameProof())invalid("selected checkpoint changed during source restore");
    restoreSourcePolicy(pc_randomizer_surface_session(),true);
}
void pc_p2_surface_save_scene_setup(){
    choosing=false;requested=false;choice=nullptr;
    if(restoring){
        if(!sameProof())invalid("selected checkpoint changed before cold restore");
        const auto& saved=pc_randomizer_surface_session();
        if(!flowCont.mCurrentStage||flowCont.mCurrentStage->mStageID!=saved.stage)invalid("restore scene mismatch");
        gameflow.mWorldClock.setTime(saved.party.surfaceTime);
        bindingParty=true;
        pc_p2_cave_campaign_party_restore(saved.party);
        bindingParty=false;
        // Cold setup runs the native landing FSM. A living checkpoint resumes
        // its settled Walk state rather than walking these restored positions
        // back to the ship on the next tick.
        for(const auto& captain:saved.party.captains){auto* n=naviMgr->getNavi(captain.slot);
            n->mStateMachine->transit(n,NAVISTATE_Walk);}
        restoring=false;restored=true;
        std::printf("P2_SURFACE_RESUMED generation=%llu day=%d time=%.9g bodies=%zu heads=%zu\n",
            static_cast<unsigned long long>(selectedGeneration),saved.day,saved.party.surfaceTime,
            saved.party.bodies.size(),saved.party.surfaceHeads.size());
    }
    const char* enabled=std::getenv("PIKMIN_P2_SURFACE_SAVE");
    if(enabled&&std::string(enabled)=="1"&&pc_randomizer_enabled()&&!pc_randomizer_generated_cave()){
        choice=new zen::ogScrFileChkSelMgr();
        std::puts("P2_SURFACE_SAVE_READY key=F11 settled_surface_only=1");
    }
}
void pc_p2_surface_save_scene_exit(){
    if(choosing)gameflow.mIsUIOverlayActive=FALSE;
    choosing=false;choice=nullptr;restoring=false;restored=false;bindingParty=false;
    pc_p2_cave_campaign_party_scene_exit();
    // A saved checkpoint remains on disk; ordinary unsaved travel must not
    // carry a stale living descriptor into a future day-boundary card.
    if(pc_randomizer_enabled())pc_randomizer_surface_session_set(P2SurfaceSession{});
}
void pc_p2_surface_save_before_day_cleanup(){
    if(pc_randomizer_enabled())pc_randomizer_surface_session_set(P2SurfaceSession{});
}
void pc_p2_surface_save_request(){if(choice&&!choosing)requested=true;}
bool pc_p2_surface_save_update(Controller* input){
    const bool pressed=requested;requested=false;
    if(!choice)return false;
    if(!choosing){
        if(!pressed||!settled())return false;
        choice->startSave();choosing=true;gameflow.mIsUIOverlayActive=TRUE;
        std::puts("P2_SURFACE_SAVE_CHOICE_STARTED native_file_menu=1");return true;
    }
    if(!input)invalid("native selection without controller");
    CardQuickInfo selection;const auto state=choice->update(input,selection);
    if(state==zen::ogScrFileChkSelMgr::SelectionA||state==zen::ogScrFileChkSelMgr::SelectionB
        ||state==zen::ogScrFileChkSelMgr::SelectionC){
        // This is the exact physical backup and logical file returned by the
        // native menu, including an existing file's overwrite selection.
        gameflow.mPlayState.mSaveSlot=selection.mGameSaveSlot;
        gameflow.mGamePrefs.mSpareMemCardSaveIndex=selection.mMemCardSaveIndex+1;
        choosing=false;gameflow.mIsUIOverlayActive=FALSE;commit();
    }else if(state==zen::ogScrFileChkSelMgr::ErrorOrCompleted||state==zen::ogScrFileChkSelMgr::ForceExit){
        choosing=false;gameflow.mIsUIOverlayActive=FALSE;std::puts("P2_SURFACE_SAVE_CANCELLED");
    }
    return true;
}
void pc_p2_surface_save_draw(Graphics& gfx){if(choosing&&choice)choice->draw(gfx);}

bool pc_p2_surface_save_survivor_permit(const std::string& sourceKey,std::uint32_t recordUid,
    std::uint32_t attempt,std::uint64_t activation,const std::string& catalogFingerprint,
    std::uint64_t* generation,std::uint8_t sha[32]){
    if(!bindingParty||!restoring||pc_randomizer_generated_cave()||!sameProof())return false;
    return p2CaveSurvivorPermit(pc_randomizer_surface_session().party,true,
        selectedGeneration,pc_randomizer_active_campaign_generation(),selectedSha,
        sourceKey,recordUid,attempt,activation,catalogFingerprint,generation,sha);
}
bool pc_p2_surface_save_survivor_body(const std::string& sourceKey,std::uint32_t recordUid,
    std::uint32_t attempt,std::uint64_t activation,const std::string& catalogFingerprint,
    OriginalPikiBodyState& state,std::uint64_t* generation,std::uint8_t sha[32]){
    if(!bindingParty||!restoring||pc_randomizer_generated_cave()||!sameProof())return false;
    return p2CaveSurvivorBody(pc_randomizer_surface_session().party,true,
        selectedGeneration,pc_randomizer_active_campaign_generation(),selectedSha,
        sourceKey,recordUid,attempt,activation,catalogFingerprint,state,generation,sha);
}
// Current base has no cave campaign provider. A composed cave build supplies
// these global dispatchers and forwards its outside-cave case to the surface
// callbacks above; explicit provider ownership prevents duplicate definitions.
#if !defined(PIKMIN_P2_CAVE_CAMPAIGN_PROVIDER)
bool pc_p2_cave_campaign_survivor_permit(const std::string& key,std::uint32_t record,
    std::uint32_t attempt,std::uint64_t activation,const std::string& fingerprint,
    std::uint64_t* generation,std::uint8_t sha[32]){
    return pc_p2_surface_save_survivor_permit(key,record,attempt,activation,fingerprint,generation,sha);
}
bool pc_p2_cave_campaign_survivor_body(const std::string& key,std::uint32_t record,
    std::uint32_t attempt,std::uint64_t activation,const std::string& fingerprint,
    OriginalPikiBodyState& state,std::uint64_t* generation,std::uint8_t sha[32]){
    return pc_p2_surface_save_survivor_body(key,record,attempt,activation,fingerprint,state,generation,sha);
}
#endif
