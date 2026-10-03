#include "pc_p2_cave_campaign_party_engine.h"
#include "pc_p2_species.h"
#include "pc_p2_original_piki_origin.h"
#include "pc_p2_source_body.h"
#if __has_include("pc_p2_original_sprout_native.h")
#include "pc_p2_original_sprout_native.h"
#define PC_P2_PARTY_SOURCE_SPROUT_PROVIDER 1
#endif
#include "pc_p2_purple.h"
#include "pc_p2_white.h"
#include "pc_p2_captain.h"
#include "pc_randomizer.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiHeadItem.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "GoalItem.h"
#include "ItemMgr.h"
#include "PikiState.h"
#include "SimpleAI.h"
#include "AIConstant.h"
#include "GameStat.h"
#include <cstdio>
#include <cstdlib>
#include <set>
#include <unordered_map>

namespace {
std::unordered_map<Piki*,P2CavePartyBody> provenance;
std::unordered_map<Piki*,P2CavePartyBody> birthOrigins;
P2CavePartyPoint point(const Vector3f& p){return {p.x,p.y,p.z};}
Vector3f vector(const P2CavePartyPoint& p){return Vector3f(p.x,p.y,p.z);}
bool near(const Vector3f& p,const P2CavePartyPoint& q){return std::fabs(p.x-q.x)<.05f
    &&std::fabs(p.y-q.y)<.05f&&std::fabs(p.z-q.z)<.05f;}
[[noreturn]] void invalid(const char* why){std::fprintf(stderr,"Invalid native cave party: %s\n",why);std::abort();}
bool assets(int species){return (species!=3||pc_p2_purples_enabled())&&(species!=4||pc_p2_whites_enabled());}
bool sameSource(const P2CavePartyBody& a,const P2CavePartyBody& b){
    return !a.sourceKey.empty()&&a.sourceKey==b.sourceKey&&a.catalogFingerprint==b.catalogFingerprint&&a.sourceRecord==b.sourceRecord
        &&a.sourceAttempt==b.sourceAttempt&&a.sourceActivation==b.sourceActivation;}
}
bool pc_p2_cave_campaign_party_capture(P2CaveCampaignParty& party,bool inside){
    auto held=[](const char* why){std::printf("P2_CAMPAIGN_PARTY_CAPTURE_HELD reason=%s\n",why);return false;};
    if(!pikiMgr||!naviMgr||!itemMgr||!itemMgr->getPikiHeadMgr())return held("missing_managers");
    auto captured=party;captured.present=true;captured.inside=inside;
    captured.resumeLiving=true;
    captured.landing=false;
    auto nextProvenance=provenance;
    // A caller may inspect a capture without adopting its party. Existing live
    // identities still own their keys; allocate beyond them on the next capture.
    for(const auto& entry:nextProvenance)
        if(entry.second.key>=captured.nextKey)captured.nextKey=entry.second.key+1;
    captured.captains.clear();captured.bodies.clear();
    Navi* active=naviMgr->getActiveNavi();if(!active)return held("missing_active_captain");
    if(!active->getCurrState()||active->getCurrState()->getID()!=NAVISTATE_Walk)return held("captain_not_walking");
    captured.active=active->getNaviIndex();
    for(int slot=0;slot<naviMgr->getNaviCount();++slot){Navi* n=naviMgr->getNavi(slot);
        if(!n||!n->isAlive())return held("unavailable_captain");
        // Native Navi/Piki initialise current HP from their own parameters;
        // the inherited Creature::mMaxHealth is not initialised for either.
        captured.captains.push_back({slot,n->mHealth,C_NAVI_PARM(n,mHealth),n->mFaceDirection,point(n->mSRT.t)});
        if(!captured.captains.back().valid()){
            std::printf("P2_CAMPAIGN_CAPTAIN_CAPTURE slot=%d health=%.9g parameter_max=%.9g state=%d\n",slot,n->mHealth,float(C_NAVI_PARM(n,mHealth)),n->getCurrState()?n->getCurrState()->getID():-1);
            return held("invalid_captain_fields");}}
    Iterator bodies(pikiMgr);CI_LOOP(bodies){Piki* p=static_cast<Piki*>(*bodies);
        if(!p->isAlive())continue;
        PcP2SourceBody typed;
        const auto kind=pc_p2_source_body_query(p,typed);
        // Party3 cannot represent conversion/Onyon ancestry or an expired
        // labelled root. Retain the tag and refuse before allocating keys or
        // publishing capture; Party4's complete graph owns those families.
        if(kind==PcP2SourceBodyKind::BudConversion||kind==PcP2SourceBodyKind::OnyonEmission
           ||kind==PcP2SourceBodyKind::Unavailable)return held("typed_source_body_requires_graph");
        if(!p->getCurrState()||p->getCurrState()->getID()!=PIKISTATE_Normal||p->isStickTo())return held("unsettled_body");
        P2CavePartyBody b;
        const auto prior=nextProvenance.find(p);
        if(prior!=nextProvenance.end())b=prior->second;
        else {b.key=captured.nextKey++;b.originRealm=int(inside);b.originPosition=point(p->mSRT.t);
            const auto association=birthOrigins.find(p);
            if(association!=birthOrigins.end()){
                b.sourceKey=association->second.sourceKey;b.sourceRecord=association->second.sourceRecord;
                b.catalogFingerprint=association->second.catalogFingerprint;
                b.sourceAttempt=association->second.sourceAttempt;b.sourceActivation=association->second.sourceActivation;}
            if(p->mGenerator){b.originGenerator=pc_randomizer_generator_id(p->mGenerator);
                if(!b.originGenerator)return held("unresolved_generator_id");}}
        b.species=pc_p2_species(p);b.growth=p->mHappa;
        OriginalPikiBody canonical;
        if(pc_p2_original_piki_body_query(p,canonical)){
            const auto& o=canonical.origin;
            if(canonical.state.species!=b.species)return held("source_species_disagreement");
            if(!b.sourceKey.empty()&&(b.sourceKey!=o.sourceKey||b.sourceRecord!=o.recordUid
                ||b.sourceAttempt!=o.attempt||b.sourceActivation!=o.activation
                ||b.catalogFingerprint!=o.catalogFingerprint))return held("source_body_identity_disagreement");
            b.sourceKey=o.sourceKey;b.sourceRecord=o.recordUid;b.sourceAttempt=o.attempt;
            b.sourceActivation=o.activation;b.catalogFingerprint=o.catalogFingerprint;
            b.wild=canonical.state.wild;b.wasWild=canonical.state.wasWild;
        }else if(!b.sourceKey.empty())return held("source_body_authority_missing");
        b.owner=p->mNavi?p->mNavi->getNaviIndex():-1;b.player=p->mPlayerId;b.mode=p->mMode;
        b.generator=p->mGenerator?pc_randomizer_generator_id(p->mGenerator):0;
        b.health=p->mHealth;b.maxHealth=pikiMgr->mPikiParms->mPikiParms.mPikiMaxHealth();b.face=p->mFaceDirection;b.position=point(p->mSRT.t);
        if(!b.valid()||!assets(b.species)){
            std::printf("P2_CAMPAIGN_BODY_CAPTURE species=%d growth=%d owner=%d player=%d mode=%d health=%.9g max=%.9g assets=%d\n",b.species,b.growth,b.owner,b.player,b.mode,b.health,b.maxHealth,int(assets(b.species)));
            return held("invalid_body_fields");}
        if(!captured.retainOrigin(b))return held("conflicting_body_origin");
        nextProvenance[p]=b;
        captured.bodies.push_back(b);}
    auto& heads=inside?captured.floorHeads:captured.surfaceHeads;heads.clear();
    Iterator sprouts(itemMgr->getPikiHeadMgr());CI_LOOP(sprouts){auto* h=static_cast<PikiHeadItem*>(*sprouts);
#if defined(PC_P2_PARTY_SOURCE_SPROUT_PROVIDER)
        // The retained tag survives an unavailable full lineage read. Party3
        // cannot encode the source Onion family, including pending and stock.
        if(pc_p2_original_sprout_head_tag(h))return held("typed_source_head_requires_graph");
#endif
        p2budorigin::Record converted;
        if(p2budorigin::registry().head(h,converted))return held("typed_source_head_requires_graph");
        if(!h->canPullout()||!h->getCurrState()||h->getCurrState()->getID()!=PikiHeadAI::PIKIHEAD_Wait)return held("unsettled_head");
        P2CavePartyHead s;s.species=pc_p2_species(h);s.growth=h->mFlowerStage;s.owner=h->mPcOwner;
        s.parent=h->mParentOnion?int(h->mParentOnion->mOnionColour):-1;s.state=h->getCurrState()->getID();
        s.counter=h->mSAICtx.mCounter;s.timer=h->mSAICtx.mCurrentItemHealth;
        s.motion=h->mItemAnimator.mMotionIdx;s.key=h->mItemAnimator.mCurrentKeyIndex;
        s.previousKey=int(h->mItemAnimator.mPreviousKeyIndex);s.playState=h->mItemAnimator.mPlayState;
        s.frame=h->mItemAnimator.mAnimationCounter;s.speed=h->mMotionSpeed;s.position=point(h->mSRT.t);
        if(!s.valid()||!assets(s.species))return held("invalid_head_fields");heads.push_back(s);}
    if(!captured.valid())return held("invalid_party_relationships");
    party=std::move(captured);provenance=std::move(nextProvenance);return true;
}
void pc_p2_cave_campaign_party_forget(Piki* body){provenance.erase(body);birthOrigins.erase(body);pc_p2_original_piki_origin_forget(body);}
void pc_p2_cave_campaign_party_scene_exit(){for(const auto& entry:provenance)pc_p2_original_piki_origin_forget(entry.first);
    for(const auto& entry:birthOrigins)pc_p2_original_piki_origin_forget(entry.first);
    provenance.clear();birthOrigins.clear();}
bool pc_p2_cave_campaign_party_associate_birth(Piki* body,const char* sourceKey,
    std::uint32_t recordUid,std::uint32_t attempt,std::uint64_t activation,const char* catalogFingerprint){
    // Original source births also notify this optional consumer in ordinary
    // courses. An inactive cave consumer accepts without retaining identity.
    if(!pc_randomizer_generated_cave())return true;
    if(!body||!sourceKey||!sourceKey[0])return false;
    P2CavePartyBody origin;origin.sourceKey=sourceKey;origin.sourceRecord=recordUid;
    if(catalogFingerprint)origin.catalogFingerprint=catalogFingerprint;
    origin.sourceAttempt=attempt;origin.sourceActivation=activation;
    if(!origin.sourceValid()||birthOrigins.count(body)||provenance.count(body))return false;
    birthOrigins.emplace(body,std::move(origin));return true;
}
void pc_p2_cave_campaign_party_restore(const P2CaveCampaignParty& party){
    if(!party.present||!party.valid()||!pikiMgr||!naviMgr||!itemMgr)invalid("missing validated state/managers");
    if(naviMgr->getNaviCount()!=int(party.captains.size()))invalid("captain population changed");
    for(const auto& c:party.captains)if(!naviMgr->getNavi(c.slot))invalid("missing captain slot");
    for(const auto& c:party.captains)if(c.maxHealth!=float(C_NAVI_PARM(naviMgr->getNavi(c.slot),mHealth)))invalid("captain health parameter changed");
    for(const auto& b:party.bodies)if(b.maxHealth!=pikiMgr->mPikiParms->mPikiParms.mPikiMaxHealth())invalid("body health parameter changed");
    for(const auto& b:party.bodies)if(!assets(b.species))invalid("body species assets unavailable");
    const auto& savedHeads=party.inside?party.floorHeads:party.surfaceHeads;
    for(const auto& h:savedHeads)if(!assets(h.species))invalid("head species assets unavailable");
    std::vector<Piki*> live;Iterator adults(pikiMgr);CI_LOOP(adults){auto* p=static_cast<Piki*>(*adults);if(p->isAlive())live.push_back(p);}
    std::vector<Piki*> matched(party.bodies.size(),nullptr);std::set<Piki*> used;
    std::vector<Piki*> lost;
    for(std::size_t i=0;i<party.bodies.size();++i){const auto& b=party.bodies[i];
        for(auto* p:live){const auto uid=p->mGenerator?pc_randomizer_generator_id(p->mGenerator):0;
            const auto& matchPosition=b.generator?b.originPosition:b.position;
            const auto source=birthOrigins.find(p);
            const bool identity=!b.sourceKey.empty()?b.originRealm==int(party.inside)
                &&source!=birthOrigins.end()&&sameSource(b,source->second):uid==b.generator&&near(p->mSRT.t,matchPosition);
            if(!used.count(p)&&identity){
                if(matched[i])invalid("ambiguous cache body identity");matched[i]=p;}}
        if(matched[i])used.insert(matched[i]);}
    for(auto* p:live){if(used.count(p))continue;
        const auto uid=p->mGenerator?pc_randomizer_generator_id(p->mGenerator):0;
        const auto source=birthOrigins.find(p);
        const P2CavePartyBody* origin=nullptr;
        for(const auto& candidate:party.origins)if(candidate.originRealm==int(party.inside)
            &&(!candidate.sourceKey.empty()?source!=birthOrigins.end()&&sameSource(candidate,source->second):
                candidate.originGenerator==uid&&near(p->mSRT.t,candidate.originPosition))){
                if(origin)invalid("ambiguous lost source member");origin=&candidate;}
        if(!origin)invalid("foreign cache body");
        for(const auto& survivor:party.bodies)if(survivor.key==origin->key)invalid("live member absent from source cache");
        if(!p->removable())invalid("lost source member still referenced");
        lost.push_back(p);}
    for(std::size_t i=0;i<party.bodies.size();++i)
        if(!matched[i]&&(party.bodies[i].generator
            ||(!party.bodies[i].sourceKey.empty()&&party.bodies[i].originRealm==int(party.inside))))
            invalid("missing source-bound cache body");
    if(party.bodies.size()>std::size_t(pikiMgr->getMax()))invalid("body manager capacity");
    const auto bodyNeeded=party.bodies.size()-used.size();
    if(bodyNeeded>std::size_t(pikiMgr->getMax()-pikiMgr->getSize())+lost.size())invalid("body pool reservation");
    // PikiMgr::birth also gates the native population counter. Refuse before
    // deleting/rebinding actors if that gate cannot admit every missing body.
    const int currentField=GameStat::mapPikis;
    if(currentField<0||std::size_t(currentField)+bodyNeeded>std::size_t(AICONST.mMaxPikisOnField()))
        invalid("native body birth population gate");
    std::vector<PikiHeadItem*> existing;Iterator heads(itemMgr->getPikiHeadMgr());CI_LOOP(heads){existing.push_back(static_cast<PikiHeadItem*>(*heads));}
    std::vector<PikiHeadItem*> headMatches(savedHeads.size(),nullptr);std::set<PikiHeadItem*> usedHeads;
    for(std::size_t i=0;i<savedHeads.size();++i){for(auto* h:existing)if(!usedHeads.count(h)&&near(h->mSRT.t,savedHeads[i].position)){
        if(headMatches[i])invalid("ambiguous cache head identity");headMatches[i]=h;}
        if(headMatches[i])usedHeads.insert(headMatches[i]);}
    if(usedHeads.size()!=existing.size())invalid("foreign cache head");
    if(savedHeads.size()>std::size_t(itemMgr->getPikiHeadMgr()->getMax()))invalid("head manager capacity");
    if(savedHeads.size()-usedHeads.size()>std::size_t(itemMgr->getPikiHeadMgr()->getMax()-itemMgr->getPikiHeadMgr()->getSize()))
        invalid("head pool reservation");
    if(party.bodies.size()+savedHeads.size()>std::size_t(AICONST.mMaxPikisOnField())
        ||itemMgr->getContainerExitCount()!=0)invalid("native aggregate field capacity");
    for(const auto& h:savedHeads)if(h.parent>=0&&!itemMgr->getContainer(h.parent))invalid("head parent unavailable");
    for(const auto& h:savedHeads){
        auto* table=itemMgr->mItemMotionTable;auto* shape=itemMgr->mItemShapes[3];
        if(!table||!shape||!shape->mAnimMgr||h.motion>=table->mMotionCount)invalid("head motion unavailable");
        auto* motion=table->getMotion(h.motion);auto* info=motion?shape->mAnimMgr->findAnim(motion->mAnimID):nullptr;
        if(!info||!info->mData||h.key>info->countIKeys()||h.previousKey>info->countIKeys()
            ||h.frame>float(info->mData->mTotalFrameCount))invalid("head animation bounds");}
    for(auto* p:lost){
        const auto source=birthOrigins.find(p);
        std::printf("P2_CAMPAIGN_SOURCE_LOSS uid=%u source=%s record=%u attempt=%u activation=%llu\n",
            p->mGenerator?pc_randomizer_generator_id(p->mGenerator):0,
            source!=birthOrigins.end()?source->second.sourceKey.c_str():"-",
            source!=birthOrigins.end()?source->second.sourceRecord:0,
            source!=birthOrigins.end()?source->second.sourceAttempt:0,
            static_cast<unsigned long long>(source!=birthOrigins.end()?source->second.sourceActivation:0));
        p->kill(false);}
    for(const auto& c:party.captains){Navi* n=naviMgr->getNavi(c.slot);if(!n)invalid("missing captain slot");
        n->mHealth=c.health;n->mSRT.t=vector(c.position);n->mFaceDirection=c.face;}
    for(std::size_t i=0;i<party.bodies.size();++i){const auto& b=party.bodies[i];Piki* p=matched[i];
        if(!p){p=static_cast<Piki*>(pikiMgr->birth());if(!p)invalid("body birth capacity");
            // Native generator/Onion births register work before the action
            // moves that population into formation/free mode. Register each
            // newly born restored body once, using its actual base colour.
            GameStat::workPikis.inc(b.species<=2?b.species:Red);GameStat::update();
            p->init(b.owner>=0?naviMgr->getNavi(b.owner):naviMgr->getNavi());p->resetPosition(vector(b.position));}
        if(!b.sourceKey.empty()){
            OriginalPikiBody saved{{b.sourceKey,b.sourceRecord,b.sourceAttempt,b.sourceActivation,b.catalogFingerprint},
                {std::uint8_t(b.species),b.wild,b.wasWild}};
            OriginalPikiBody existing;
            if(pc_p2_original_piki_body_query(p,existing)){
                const auto& o=existing.origin;
                if(o.sourceKey!=b.sourceKey||o.recordUid!=b.sourceRecord||o.attempt!=b.sourceAttempt
                    ||o.activation!=b.sourceActivation||o.catalogFingerprint!=b.catalogFingerprint)
                    invalid("foreign canonical cache body");
                // Rebind the authentic selected state, including recruitment,
                // through the source owner's restore API rather than overwrite
                // live flags or authorize an unrelated pointer.
                pc_p2_cave_campaign_party_forget(p);
            }
            if(!pc_p2_original_piki_body_restore_saved(p,saved))invalid("authenticated source body bind");
            PcOriginalPikiSavedColorScope color(p);
            if(!color.valid()||!pc_p2_set_species(p,b.species))invalid("source saved colour authority");
        }else if(!pc_p2_set_species(p,b.species))invalid("body species");
        if(pc_p2_species(p)!=b.species)invalid("physical restored species disagreement");
        if(b.species==3)pc_p2_make_purple(p);if(b.species==4)pc_p2_make_white(p);
        p->mHappa=b.growth;p->mPlayerId=b.player;p->mHealth=b.health;
        p->mSRT.t=vector(b.position);p->mFaceDirection=b.face;
        p->changeMode(b.mode,b.owner>=0?naviMgr->getNavi(b.owner):nullptr);
        if(!b.sourceKey.empty()&&!birthOrigins.count(p)){
            if(!pc_p2_cave_campaign_party_associate_birth(p,b.sourceKey.c_str(),b.sourceRecord,b.sourceAttempt,b.sourceActivation,b.catalogFingerprint.c_str()))
                invalid("captured source origin bind");}
        provenance[p]=b;
        std::printf("P2_CAMPAIGN_BODY_RESTORE key=%llu species=%d growth=%d owner=%d runtime_uid=%u origin_uid=%u\n",
            static_cast<unsigned long long>(b.key),b.species,b.growth,b.owner,
            p->mGenerator?pc_randomizer_generator_id(p->mGenerator):0,b.originGenerator);}
    for(std::size_t i=0;i<savedHeads.size();++i){const auto& s=savedHeads[i];auto* h=headMatches[i];
        if(!h){h=static_cast<PikiHeadItem*>(itemMgr->birth(OBJTYPE_Pikihead));if(!h)invalid("head birth capacity");h->init(vector(s.position));h->setColor(s.species<=2?s.species:Red);h->startAI(0);}
        if(!pc_p2_set_species(h,s.species))invalid("head species");h->mFlowerStage=s.growth;h->mPcOwner=s.owner;
        h->mParentOnion=s.parent>=0?itemMgr->getContainer(s.parent):nullptr;
        if(s.parent>=0&&!h->mParentOnion)invalid("head parent unavailable");
        h->mSAICtx.mStateMachine->transit(h,s.state);
        h->startMotion(s.motion);h->mItemAnimator.mAnimationCounter=s.frame;
        h->mItemAnimator.mCurrentKeyIndex=s.key;h->mItemAnimator.mPreviousKeyIndex=s.previousKey;
        h->mItemAnimator.mPlayState=s.playState;h->mMotionSpeed=s.speed;
        h->mSAICtx.mCounter=s.counter;h->mSAICtx.mCurrentItemHealth=s.timer;
        std::printf("P2_CAMPAIGN_HEAD_RESTORE species=%d growth=%d state=%d timer=%.9g\n",s.species,s.growth,s.state,s.timer);}
    naviMgr->setActiveNavi(naviMgr->getNavi(party.active));
    pc_p2_captain::teardown();if(!pc_p2_captain::setup_from_navi_mgr())invalid("captain ownership rebind");
}
