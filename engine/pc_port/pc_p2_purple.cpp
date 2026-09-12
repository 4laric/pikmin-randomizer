#include "pc_p2_purple.h"
#include "pc_p2_preview.h"
#include "pc_bbft.h"
#include "pc_randomizer.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "PikiHeadItem.h"
#include "Pellet.h"
#include "Pom.h"
#include "ItemMgr.h"
#include "NaviMgr.h"
#include "Navi.h"
#include "Shape.h"
#include "Texture.h"
#include "Camera.h"
#include "Graphics.h"
#include "gameflow.h"
#include "system.h"
#include "Stickers.h"
#include <SDL2/SDL.h>
#include <vector>
#include <string>
#include <map>
#include <fstream>
#include <cmath>
#include <cstdio>
#include <cstdlib>
namespace {
bool enabled=false;
float stats[9]={};
struct Clip {float seconds=1;std::vector<Shape*> shapes;std::vector<Matrix4f> happa;std::vector<bool> seen;};
std::map<std::string,Clip> clips;
Shape* growth[3]={};
Shape* shape(const std::string& name) {
    Shape* result=gameflow.loadShape(("courses/pikmin2room/"+name+".mod").c_str(),true);
    if(!result)std::abort();
    for(int i=0;i<result->mTexAttrCount;++i)if(result->mTexAttrList[i].mTexture)result->mTexAttrList[i].mTexture->attach();
    return result;
}
}
bool pc_p2_purples_enabled(){return pc_pikipelago_room_preview() && enabled;}
bool pc_p2_is_purple(const Piki* p){return pc_p2_purples_enabled() && p && p->mP2Purple;}
void pc_p2_make_purple(Piki* p) {
    if(!pc_p2_purples_enabled())std::abort();
    p->mP2Purple=true;p->mP2AnimationTime=0;
    p->mCurrentColour=p->mDefaultColour=p->mStartBlendColour=p->mTargetBlendColour=Colour(100,30,150,255);
    pc_p2_purple_status();
}
int pc_piki_carry_strength(const Piki* p){return pc_p2_is_purple(p)?10:pc_randomizer_carry_strength(p->mColor);}
float pc_piki_carry_power(const Piki* p){return pc_p2_is_purple(p)?stats[1]+(p->mHappa==Flower?stats[8]:p->mHappa==Bud?stats[7]:0):(1.f+0.5f*p->mHappa)*pc_randomizer_carry_strength(p->mColor);}
float pc_p2_move_multiplier(const Piki* p){return pc_p2_is_purple(p)?stats[0]:1.f;}
float pc_p2_purple_attack(){return stats[2];}
float pc_p2_purple_throw_height(){return stats[3];}
float pc_p2_transport_speed(Pellet* pellet,float fallback) {
    if(!pc_p2_purples_enabled())return fallback;
    float power=0;Stickers stickers(pellet);Iterator it(&stickers);CI_LOOP(it){Creature* p=*it;if(p && p->isPiki())power+=pc_piki_carry_power(static_cast<Piki*>(p));}
    float low=stats[4]*stats[6],high=stats[4]*stats[5];
    return low+(1+power-pellet->mConfig->mCarryMinPikis())/pellet->mConfig->mCarryMaxPikis()*(high-low);
}
void pc_p2_purple_setup() {
    enabled=false;clips.clear();
    if(!pc_pikipelago_room_preview())return;
    std::ifstream in("p2-purple.txt");if(!in)return;
    std::string word;in>>word;if(word!="P2_PURPLE_1" || !pc_p2_preview_goal())std::abort();
    if(!(in>>word) || word!="stats")std::abort();
    for(float& value:stats)if(!(in>>value) || !std::isfinite(value) || value<0 || value>1000)std::abort();
    for(const char* expected:{"wait","walk","attack1"}) {
        int count;float seconds;
        if(!(in>>word>>count>>seconds) || word!=expected || count<1 || count>32 || !std::isfinite(seconds) || seconds<=0)std::abort();
        Clip& clip=clips[word];clip.seconds=seconds;clip.happa.resize(count);clip.seen.resize(count,false);
        for(int i=0;i<count;++i){char suffix[8];std::snprintf(suffix,sizeof(suffix),"_%02d",i);clip.shapes.push_back(shape("purple_"+word+suffix));}
    }
    while(in>>word) {
        std::string name;int index;
        if(word!="happa" || !(in>>name>>index) || !clips.count(name) || index<0 || index>=int(clips[name].happa.size()))std::abort();
        if(clips[name].seen[index])std::abort();clips[name].seen[index]=true;
        Matrix4f& matrix=clips[name].happa[index];matrix.makeIdentity();
        for(int r=0;r<3;++r)for(int c=0;c<4;++c)if(!(in>>matrix.mMtx[r][c]) || !std::isfinite(matrix.mMtx[r][c]))std::abort();
    }
    for(const auto& pair:clips)for(bool seen:pair.second.seen)if(!seen)std::abort();
    for(int i=0;i<3;++i)growth[i]=shape("purple_happa_"+std::to_string(i));
    enabled=true;
    std::printf("P2_PURPLE_READY actual model; sampled source poses; weight=10 movement=%.2f carry_power=%.2f attack=%.2f throw=%.2f\n",stats[0],stats[1],stats[2],stats[3]);
}
bool pc_p2_draw_purple(Piki* p,Graphics& gfx) {
    if(!pc_p2_is_purple(p))return false;
    std::string motion=p->mMode==PikiMode::AttackMode?"attack1":(p->mVelocity.x*p->mVelocity.x+p->mVelocity.z*p->mVelocity.z>16?"walk":"wait");
    Clip& clip=clips[motion];int index=int(std::fmod(p->mP2AnimationTime,clip.seconds)/clip.seconds*clip.shapes.size());
    if(index<0 || index>=int(clip.shapes.size()))index=0;
    Matrix4f view;gfx.mCamera->mLookAtMtx.multiplyTo(p->mWorldMtx,view);
    clip.shapes[index]->updateAnim(gfx,view,nullptr,p);clip.shapes[index]->drawshape(gfx,*gfx.mCamera,nullptr);
    Matrix4f leaf;view.multiplyTo(clip.happa[index],leaf);
    Shape* top=growth[p->mHappa>=0 && p->mHappa<3?p->mHappa:0];
    top->updateAnim(gfx,leaf,nullptr,p);top->drawshape(gfx,*gfx.mCamera,nullptr);
    return true;
}
bool pc_p2_violet(const Pom* pom){
    if(!pc_pikipelago_room_preview() || !pom)return false;
    static const bool requested=[](){std::ifstream file("p2-purple.txt");return bool(file);}();
    return requested;
}
int pc_p2_convert_violet(Pom* pom, int remaining) {
    if(!pc_p2_violet(pom))return -1;
    // Allocate each replacement first: capacity failure must never eat a Pikmin.
    Stickers stickers(pom);Iterator it(&stickers);int converted=0;
    CI_LOOP(it) {
        Creature* creature=*it;if(!creature || !creature->isAlive() || !creature->isPiki())continue;
        Piki* p=static_cast<Piki*>(creature);
        if(converted>=remaining){p->endStickObject();p->mFSM->transit(p,PIKISTATE_Normal);p->changeMode(PikiMode::FreeMode,naviMgr->getNavi());it.dec();continue;}
        PikiHeadItem* sprout=static_cast<PikiHeadItem*>(itemMgr->birth(OBJTYPE_Pikihead));
        if(!sprout){p->endStickObject();p->mFSM->transit(p,PIKISTATE_Normal);p->changeMode(PikiMode::FreeMode,naviMgr->getNavi());it.dec();continue;}
        Vector3f position=pom->mSRT.t;position.y+=50;sprout->init(position);sprout->setColor(Red);sprout->mP2Purple=true;
        float angle=converted*1.256637f;sprout->mVelocity.set(120*std::sin(angle),500,120*std::cos(angle));
        sprout->startAI(0);C_SAI(sprout)->start(sprout,PikiHeadAI::PIKIHEAD_Flying);
        p->setEraseKill();p->kill(false);it.dec();++converted;
    }
    std::printf("P2_VIOLET_CONVERT count=%d\n",converted);pc_p2_purple_status();return converted;
}
void pc_p2_purple_status() {
    if(!pc_p2_purples_enabled())return;
    int purple=0,other=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p && p->isAlive()){if(pc_p2_is_purple(p))++purple;else ++other;}}
    if(SDL_Window* window=SDL_GL_GetCurrentWindow()) {
        std::string title="Pikipelago - Purple preview: "+std::to_string(purple)+" Purple, "+std::to_string(other)+" other field Pikmin | "+std::to_string(pc_p2_preview_pokos())+" Pokos";
        SDL_SetWindowTitle(window,title.c_str());
    }
}
