#include "pc_p2_white.h"
#include "pc_p2_white_policy.h"
#include "pc_p2_species.h"
#include "pc_p2_preview.h"
#include "pc_bbft.h"
#include "Piki.h"
#include "PikiHeadItem.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "Pom.h"
#include "ItemMgr.h"
#include "NaviMgr.h"
#include "Navi.h"
#include "Shape.h"
#include "Texture.h"
#include "Camera.h"
#include "Graphics.h"
#include "Generator.h"
#include "gameflow.h"
#include "system.h"
#include "Stickers.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <set>
#include <string>
#include <vector>

namespace {
bool enabled = false;
P2WhiteStats stats;
struct Clip { float seconds=1; std::vector<Shape*> shapes; std::vector<Matrix4f> happa; std::vector<bool> seen; };
std::map<std::string, Clip> clips;
Shape* growth[3] = {};
std::set<unsigned> ivoryGenerators;
Shape* loadShape(const std::string& name) {
    Shape* result=gameflow.loadShape(("courses/pikmin2room/"+name+".mod").c_str(),true);
    if(!result)std::abort();
    for(int i=0;i<result->mTexAttrCount;++i)if(result->mTexAttrList[i].mTexture)result->mTexAttrList[i].mTexture->attach();
    return result;
}
}

bool pc_p2_whites_enabled(){return pc_pikipelago_room_preview() && enabled;}
bool pc_p2_is_white(const Piki* piki){return pc_p2_whites_enabled() && pc_p2_species(piki)==P2SpeciesWhite;}
void pc_p2_make_white(Piki* piki){
    if(!pc_p2_whites_enabled() || !pc_p2_set_species(piki,P2SpeciesWhite))std::abort();
    piki->mP2AnimationTime=0;
    piki->mCurrentColour=piki->mDefaultColour=piki->mStartBlendColour=piki->mTargetBlendColour=Colour(230,230,220,255);
}
float pc_p2_white_move_multiplier(){return stats.movement;}
float pc_p2_white_attack(){return stats.attack;}
float pc_p2_white_carry_power(int maturity){return stats.carryPower+(maturity==Flower?stats.flowerBonus:(maturity==Bud?stats.budBonus:0));}
float pc_p2_white_carry_min_factor(){return stats.baseRunSpeed*stats.carryMinFactor;}
float pc_p2_white_carry_max_factor(){return stats.baseRunSpeed*stats.carryMaxFactor;}

void pc_p2_white_setup(){
    enabled=false;clips.clear();ivoryGenerators.clear();
    if(!pc_pikipelago_room_preview())return;
    std::ifstream in("p2-white.txt");if(!in)return;
    std::string word;if(!(in>>word) || word!="P2_WHITE_1" || !pc_p2_preview_goal())std::abort();
    if(!(in>>word>>stats.movement>>stats.attack>>stats.scale>>stats.carryPower>>stats.budBonus>>stats.flowerBonus>>stats.carryMaxFactor>>stats.carryMinFactor>>stats.baseRunSpeed) || word!="stats" || !p2_white_stats_valid(stats))std::abort();
    int generatorCount=0;if(!(in>>word>>generatorCount)||word!="ivory_generators"||generatorCount<1||generatorCount>32)std::abort();
    for(int i=0;i<generatorCount;++i){unsigned id;if(!(in>>id)||!ivoryGenerators.insert(id).second)std::abort();}
    for(const char* expected:{"wait","walk","attack1"}){
        int count;float seconds;if(!(in>>word>>count>>seconds)||word!=expected||count<1||count>32||!std::isfinite(seconds)||seconds<=0)std::abort();
        Clip& clip=clips[word];clip.seconds=seconds;clip.happa.resize(count);clip.seen.resize(count,false);
        for(int i=0;i<count;++i){char suffix[8];std::snprintf(suffix,sizeof(suffix),"_%02d",i);clip.shapes.push_back(loadShape("white_"+word+suffix));}
    }
    while(in>>word){std::string name;int index;if(word!="happa"||!(in>>name>>index)||!clips.count(name)||index<0||index>=int(clips[name].happa.size())||clips[name].seen[index])std::abort();
        clips[name].seen[index]=true;Matrix4f& matrix=clips[name].happa[index];matrix.makeIdentity();
        for(int r=0;r<3;++r)for(int c=0;c<4;++c)if(!(in>>matrix.mMtx[r][c])||!std::isfinite(matrix.mMtx[r][c]))std::abort();}
    for(const auto& pair:clips)for(bool seen:pair.second.seen)if(!seen)std::abort();
    for(int i=0;i<3;++i)growth[i]=loadShape("white_happa_"+std::to_string(i));
    enabled=true;
    std::printf("P2_WHITE_READY actual model; sampled source poses; movement_adaptation=%.3f attack=%.3f model_scale=1.0 p008_unused=%.3f carry_power=%.3f\n",stats.movement,stats.attack,stats.scale,stats.carryPower);
}

bool pc_p2_draw_white(Piki* piki,Graphics& gfx){
    if(!pc_p2_is_white(piki))return false;
    std::string motion=piki->mMode==PikiMode::AttackMode?"attack1":(piki->mVelocity.x*piki->mVelocity.x+piki->mVelocity.z*piki->mVelocity.z>16?"walk":"wait");
    Clip& clip=clips[motion];int index=int(std::fmod(piki->mP2AnimationTime,clip.seconds)/clip.seconds*clip.shapes.size());if(index<0||index>=int(clip.shapes.size()))index=0;
    // Source p008 is unused by the audited retail implementation. Keep the
    // imported model at authored scale until a live use site is established.
    Matrix4f world,view;world.makeSRT(Vector3f(1,1,1),piki->mSRT.r,piki->mSRT.t);
    gfx.mCamera->mLookAtMtx.multiplyTo(world,view);clip.shapes[index]->updateAnim(gfx,view,nullptr,piki);clip.shapes[index]->drawshape(gfx,*gfx.mCamera,nullptr);
    Matrix4f leaf;view.multiplyTo(clip.happa[index],leaf);Shape* top=growth[piki->mHappa>=0&&piki->mHappa<3?piki->mHappa:0];top->updateAnim(gfx,leaf,nullptr,piki);top->drawshape(gfx,*gfx.mCamera,nullptr);return true;
}

bool pc_p2_ivory(const Pom* pom){
    return pom && pc_p2_whites_enabled() && pom->mGenerator && ivoryGenerators.count(pom->mGenerator->_70);
}

int pc_p2_convert_ivory(Pom* pom,int remaining){
    if(!pc_p2_ivory(pom))return -1;
    Stickers stickers(pom);Iterator it(&stickers);int converted=0;
    CI_LOOP(it){Creature* creature=*it;if(!creature||!creature->isAlive()||!creature->isPiki())continue;Piki* p=static_cast<Piki*>(creature);
        if(converted>=remaining){p->endStickObject();p->mFSM->transit(p,PIKISTATE_Normal);p->changeMode(PikiMode::FreeMode,naviMgr->getNavi());it.dec();continue;}
        PikiHeadItem* sprout=static_cast<PikiHeadItem*>(itemMgr->birth(OBJTYPE_Pikihead));
        if(!sprout){p->endStickObject();p->mFSM->transit(p,PIKISTATE_Normal);p->changeMode(PikiMode::FreeMode,naviMgr->getNavi());it.dec();continue;}
        Vector3f position=pom->mSRT.t;position.y+=50;sprout->init(position);pc_p2_set_species(sprout,P2SpeciesWhite);
        float angle=converted*1.256637f;sprout->mVelocity.set(120*std::sin(angle),500,120*std::cos(angle));sprout->startAI(0);C_SAI(sprout)->start(sprout,PikiHeadAI::PIKIHEAD_Flying);
        p->setEraseKill();p->kill(false);it.dec();++converted;}
    std::printf("P2_IVORY_CONVERT count=%d\n",converted);return converted;
}
