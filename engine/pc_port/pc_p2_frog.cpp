#include "pc_p2_frog.h"
#include "pc_p2_frog_policy.h"
#include "Material.h"
#include "pc_bbft.h"
#include "teki.h"
#include "Generator.h"
#include "Shape.h"
#include "Texture.h"
#include "Graphics.h"
#include "Camera.h"
#include "gameflow.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include <fstream>
#include <set>
#include <cstdlib>
#include <cstdio>
namespace {
std::map<PelletView*,int> actors;
const char* ids[]={"Frog","MaroFrog"};
std::map<std::string,std::vector<Shape*>> animated[2];
std::map<std::string,p2animation::Clip> timing[2];
std::set<PelletView*> pressing,bitteredFrogs;
// Family-local instrumentation only: records the P1-proxy Attack motion of a
// registered frog; it does not assert the source landing press.
bool logPress(BTeki* actor,int kind){
    auto* view=static_cast<PelletView*>(actor);
    bool active=actor->mTekiAnimator&&actor->mTekiAnimator->getCurrentMotionIndex()==TekiMotion::Attack;
    if(active){if(pressing.insert(view).second){std::printf("P2_FROG_PRESS species=%s attack=1 behavior=P1_proxy\n",ids[kind]);return true;}return false;}
    pressing.erase(view);return false;
}
bool isBittered(PelletView* view){return bitteredFrogs.count(view)!=0;}
// Family-local landing-press attribution (#167/#201). Edge-triggered from the
// P1-proxy Attack motion, the host's landing/attack key. It counts grounded
// Pikmin/Navi inside the source head radius and reports only: it never presses,
// damages or moves any actor, so unregistered controls are untouched and press
// behavior is unchanged (the P1 host already presses). The source not-bittered
// precondition is honoured through pc_p2_frog_set_bittered; no P1 bitter
// provider exists yet, so native always reports the not-bittered case.
void logLand(BTeki* actor,int kind){
    if(isBittered(static_cast<PelletView*>(actor)))return;
    const float radius=p2frog::headRadius(kind);const Vector3f& at=actor->getPosition();
    const float r2=radius*radius;int pikmin=0,navi=0;
    if(pikiMgr){Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);
        if(!p||!p->isAlive()||p->isFlying())continue;const Vector3f& pos=p->getPosition();
        const float dx=pos.x-at.x,dz=pos.z-at.z;if(dx*dx+dz*dz<=r2)++pikmin;}}
    if(naviMgr){Iterator it(naviMgr);CI_LOOP(it){Navi* n=static_cast<Navi*>(*it);
        if(!n||!n->isAlive()||n->isFlying())continue;const Vector3f& pos=n->getPosition();
        const float dx=pos.x-at.x,dz=pos.z-at.z;if(dx*dx+dz*dz<=r2)++navi;}}
    if(pikmin+navi<=0)return;
    std::printf("P2_FROG_LAND species=%s radius=%.1f bittered=0 pikmin=%d navi=%d behavior=P1_proxy\n",ids[kind],radius,pikmin,navi);
}
void loadAnimation(std::vector<p2animation::Clip> (&banks)[2]){
    size_t total=0;
    for(int kind=0;kind<2;++kind){std::vector<unsigned char> reference;
        for(const auto& clip:banks[kind]){size_t clipBytes=0;
            for(int i=0;i<clip.count;++i){char path[192];std::snprintf(path,sizeof(path),"assets/dataDir/courses/pikmin2room/frog_%s_%s_%02d.mod",ids[kind],clip.name.c_str(),i);
                std::ifstream file(path,std::ios::binary|std::ios::ate);if(!file)std::abort();auto size=file.tellg();
                if(size<=0||size>512*1024)std::abort();clipBytes+=size_t(size);total+=size_t(size);
                if(clipBytes>512*1024||total>10*1024*1024)std::abort();file.seekg(0);
                std::vector<unsigned char> bytes(size_t(size),0),resources;
                if(!file.read(reinterpret_cast<char*>(bytes.data()),size)||!p2animation::resources(bytes,resources))std::abort();
                if(!reference.empty()&&reference!=resources)std::abort();reference=resources;
            }
        }
    }
    for(int kind=0;kind<2;++kind){Shape* shared=nullptr;
        for(const auto& clip:banks[kind]){timing[kind][clip.name]=clip;
            for(int i=0;i<clip.count;++i){char path[160];std::snprintf(path,sizeof(path),"courses/pikmin2room/frog_%s_%s_%02d.mod",ids[kind],clip.name.c_str(),i);
                Shape* shape=gameflow.loadShape(path,true);if(!shape)std::abort();
                if(!shared){shared=shape;for(int t=0;t<shape->mTexAttrCount;++t)if(shape->mTexAttrList[t].mTexture)shape->mTexAttrList[t].mTexture->attach();}
                else{
                    if(shape->mMaterialCount!=shared->mMaterialCount||shape->mTexAttrCount!=shared->mTexAttrCount||shape->mTevInfoCount!=shared->mTevInfoCount)std::abort();
                    for(int j=0;j<shape->mTotalMatpolyCount;++j){auto* poly=shape->mMatpolyList[j];if(!poly||!poly->mMaterial)continue;int material=-1;
                        for(int m=0;m<shape->mMaterialCount;++m)if(poly->mMaterial==&shape->mMaterialList[m])material=m;
                        if(material<0)std::abort();poly->mMaterial=&shared->mMaterialList[material];}
                    shape->mMaterialList=shared->mMaterialList;shape->mTexAttrList=shared->mTexAttrList;shape->mTevInfoList=shared->mTevInfoList;
                }
                animated[kind][clip.name].push_back(shape);
            }
        }
    }
    std::printf("P2_FROG_BANK_READY mod_bytes=%zu gameplay=P1_unchanged\n",total);
}
}
void pc_p2_frog_reset(){actors.clear();pressing.clear();bitteredFrogs.clear();for(auto& b:animated)b.clear();for(auto& b:timing)b.clear();}
void pc_p2_frog_forget(BTeki* actor){actors.erase(static_cast<PelletView*>(actor));pressing.erase(static_cast<PelletView*>(actor));bitteredFrogs.erase(static_cast<PelletView*>(actor));}
void pc_p2_frog_set_bittered(BTeki* actor,bool bittered){auto* view=static_cast<PelletView*>(actor);if(!actors.count(view))return;if(bittered)bitteredFrogs.insert(view);else bitteredFrogs.erase(view);}
const char* pc_p2_frog_name(PelletView* view){auto i=actors.find(view);return i==actors.end()?nullptr:ids[i->second];}
// Source parameters replace the shared P1 host values for registered frogs only;
// unregistered controls keep native values. Reads stay non-mutating.
float pc_p2_frog_param_f(const BTeki* actor,int idx,float fallback){
    auto i=actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));if(i==actors.end())return fallback;
    const p2frog::Params& p=p2frog::params(i->second);
    switch(idx){
    case TPF_Life:return p.health;
    case TPF_VisibleRange:return p.sight;
    case TPF_AttackableRange:return p.attackRange;
    case TPF_AttackPower:return p.attackDamage;
    default:return fallback;
    }
}
void pc_p2_frog_setup(){
    pc_p2_frog_reset();if(!pc_pikipelago_room_preview())return;
    std::ifstream input("p2-frog.txt");if(!input)return;
    std::map<unsigned,int> wanted;std::vector<p2animation::Clip> banks[2];
    if(!p2frog::parse(input,wanted,banks))std::abort();
    std::set<unsigned> seen;
    Iterator it(tekiMgr);CI_LOOP(it){Teki* teki=static_cast<Teki*>(*it);if(!teki||!teki->mGenerator)continue;
        auto found=wanted.find(teki->mGenerator->_70);if(found==wanted.end())continue;
        int kind=found->second;if(!seen.insert(found->first).second)std::abort();if(teki->mTekiType!=(kind?TEKI_Frow:TEKI_Frog))std::abort();
        actors[static_cast<PelletView*>(teki)]=kind;
        teki->mHealth=p2frog::params(kind).health;
        std::printf("P2_FROG_READY species=%s generator=%u health=%.1f max_health=%.1f behavior=P1_proxy rewards=P1_unchanged\n",ids[kind],found->first,teki->mHealth,teki->getParameterF(TPF_Life));
    }
    if(seen.size()!=wanted.size())std::abort();loadAnimation(banks);
}
bool pc_p2_frog_draw(BTeki* actor,Graphics& gfx,const Matrix4f& matrix,bool corpse){
    auto it=actors.find(static_cast<PelletView*>(actor));if(it==actors.end())return false;
    int kind=it->second;if(!corpse&&logPress(actor,kind))logLand(actor,kind);int motion=actor->mTekiAnimator->getCurrentMotionIndex();
    const char* name=corpse?"dead":p2frog::motionClip(motion);
    Shape* shape=animated[kind].at("wait1").front();
    if(name){int frames=actor->mTekiAnimator->getFrameCount();float phase=frames>1?actor->mTekiAnimator->getCounter()/(frames-1):0;
        shape=animated[kind].at(name).at(timing[kind].at(name).index(phase,corpse));}
    shape->updateAnim(gfx,matrix,nullptr,actor);shape->drawshape(gfx,*gfx.mCamera,nullptr);return true;
}
