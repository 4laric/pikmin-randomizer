#include "pc_p2_dwarf_orange.h"
#include "pc_p2_dwarf_orange_policy.h"
#include "pc_p2_kochappy_stun.h"
#include "pc_p2_enemy.h"
#include "pc_p2_sheargrub.h"
#include "teki.h"
#include "Generator.h"
#include "Shape.h"
#include "Texture.h"
#include "Material.h"
#include "gameflow.h"
#include "Graphics.h"
#include "Camera.h"
#include <map>
#include <fstream>
#include <chrono>
#include <cstdio>
#include <cstdlib>
namespace {
std::map<std::string,std::vector<Shape*>> clips;
std::map<std::string,p2animation::Clip> timing;
std::set<PelletView*> actors;
p2dwarforange::Health health;
bool logged[2]={false,false};
// Source BlueKochappy purple-pikmin stun: fp38 = 5 s (KochappyBase flick/press).
constexpr float PurpleFitDuration = 5.0f;
}
void pc_p2_dwarf_orange_reset(){clips.clear();timing.clear();actors.clear();health.reset();logged[0]=logged[1]=false;}
void pc_p2_dwarf_orange_forget(BTeki* actor){
    const bool wasRegistered=actors.erase(static_cast<PelletView*>(actor))!=0;
    // The generator is already detached by dieSoon(), so identity is not
    // available here; the registration transition is the cleanup signal.
    if(wasRegistered)std::printf("P2_DWARF_ORANGE_FORGET registered=1\n");
    health.forget(actor);pc_p2_kochappy_stun_forget(actor);
}
float pc_p2_dwarf_orange_max_health(const BTeki* actor,float fallback){return health.life(actor,fallback);}
const char* pc_p2_dwarf_orange_name(PelletView* actor){return actors.count(actor)?"Dwarf Orange Bulborb":nullptr;}
bool pc_p2_dwarf_orange_registered(const BTeki* actor){return actors.count(const_cast<BTeki*>(actor))!=0;}
void pc_p2_dwarf_orange_setup(){
    pc_p2_dwarf_orange_reset();
    std::ifstream profile("p2-dwarf-orange-profile.txt"),bank("p2-dwarf-orange-bank.txt"),bindings("p2-dwarf-orange-actors.txt");
    if(!profile && !bank && !bindings)return;
    std::vector<p2animation::Clip> manifest;std::set<std::uint32_t> wanted;
    if(!profile || !bank || !bindings || !tekiMgr || !health.read(profile) || !p2dwarforange::bank(bank,manifest) || !p2dwarforange::bindings(bindings,wanted))std::abort();
    // Reject identity overlap and unresolved/duplicate generator IDs before loading.
    std::vector<Teki*> selected;std::set<std::uint32_t> seen;
    Iterator it(tekiMgr);CI_LOOP(it){
        Teki* actor=static_cast<Teki*>(*it);
        if(!actor || !actor->mGenerator || !wanted.count(actor->mGenerator->_70))continue;
        if(!seen.insert(actor->mGenerator->_70).second || actor->mTekiType!=TEKI_Chappy || pc_p2_enemy_name(actor) || pc_p2_sheargrub_name(actor) || pc_p2_kochappy_name(actor))std::abort();
        selected.push_back(actor);
    }
    if(seen!=wanted)std::abort();
    size_t total=0,poses=0;std::vector<unsigned char> reference;
    for(const auto& clip:manifest){
        size_t clipBytes=0;
        for(int i=0;i<clip.count;++i){
            char path[160];std::snprintf(path,sizeof(path),"assets/dataDir/courses/pikmin2room/dwarf_orange_%s_%02d.mod",clip.name.c_str(),i);
            std::ifstream file(path,std::ios::binary|std::ios::ate);if(!file)std::abort();auto bytes=file.tellg();
            if(bytes<=0 || size_t(bytes)>p2animation::ClipBytes-clipBytes || size_t(bytes)>p2animation::TotalBytes-total)std::abort();
            clipBytes+=size_t(bytes);total+=size_t(bytes);file.seekg(0);
            std::vector<unsigned char> data(size_t(bytes),0),resources;
            if(!file.read(reinterpret_cast<char*>(data.data()),bytes) || !p2animation::resources(data,resources))std::abort();
            if(!reference.empty() && reference!=resources)std::abort();reference=resources;
        }
    }
    const auto started=std::chrono::steady_clock::now();Shape* shared=nullptr;int attachments=0;
    for(const auto& clip:manifest){
        timing[clip.name]=clip;
        for(int i=0;i<clip.count;++i){
            char path[128];std::snprintf(path,sizeof(path),"courses/pikmin2room/dwarf_orange_%s_%02d.mod",clip.name.c_str(),i);
            Shape* shape=gameflow.loadShape(path,true);if(!shape)std::abort();
            if(!shared){shared=shape;for(int t=0;t<shape->mTexAttrCount;++t)if(shape->mTexAttrList[t].mTexture){shape->mTexAttrList[t].mTexture->attach();++attachments;}}
            else{
                if(shape->mMaterialCount!=shared->mMaterialCount || shape->mTexAttrCount!=shared->mTexAttrCount || shape->mTevInfoCount!=shared->mTevInfoCount)std::abort();
                for(int j=0;j<shape->mTotalMatpolyCount;++j){auto* poly=shape->mMatpolyList[j];if(!poly || !poly->mMaterial)continue;int material=-1;
                    for(int m=0;m<shape->mMaterialCount;++m)if(poly->mMaterial==&shape->mMaterialList[m])material=m;
                    if(material<0)std::abort();poly->mMaterial=&shared->mMaterialList[material];}
                shape->mMaterialList=shared->mMaterialList;shape->mTexAttrList=shared->mTexAttrList;shape->mTevInfoList=shared->mTevInfoList;
            }
            clips[clip.name].push_back(shape);++poses;
        }
    }
    for(Teki* actor:selected){
        if(!health.bind(static_cast<BTeki*>(actor)))std::abort();actors.insert(actor);actor->mHealth=actor->getParameterF(TPF_Life);
        const auto& pos=actor->getPosition();
        pc_p2_kochappy_stun_register(actor,PurpleFitDuration);
        std::printf("P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=%u x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=P1 purple_stun=bluekochappy_5s\n",actor->mGenerator->_70,pos.x,pos.y,pos.z,actor->mHealth,actor->getParameterF(TPF_Life));
    }
    std::printf("P2_DWARF_ORANGE_BANK poses=%zu mod_bytes=%zu texture_attach_calls=%d load_seconds=%.3f\n",poses,total,attachments,std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count());
}
bool pc_p2_dwarf_orange_draw(BTeki* actor,Graphics& gfx,const Matrix4f& matrix,bool corpse){
    if(!actors.count(static_cast<PelletView*>(actor)))return false;
    if(!logged[corpse?1:0]){std::printf("P2_DWARF_ORANGE_DRAW corpse=%d\n",int(corpse));logged[corpse?1:0]=true;}
    int motion=actor->mTekiAnimator->getCurrentMotionIndex();
    const char* name=corpse || motion==TekiMotion::Dead?"dead":motion==TekiMotion::Attack?"attack":motion==TekiMotion::Flick?"flick":
        (actor->mVelocity.x*actor->mVelocity.x+actor->mVelocity.z*actor->mVelocity.z>1?"move1":"wait1");
    int frames=actor->mTekiAnimator->getFrameCount();float phase=frames>1?actor->mTekiAnimator->getCounter()/(frames-1):0;
    Shape* shape=clips.at(name).at(timing.at(name).index(phase,corpse));shape->updateAnim(gfx,matrix,nullptr,actor);shape->drawshape(gfx,*gfx.mCamera,nullptr);return true;
}
