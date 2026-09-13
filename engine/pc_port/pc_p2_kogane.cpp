#include "pc_p2_kogane.h"
#include "pc_p2_kogane_policy.h"
#include "pc_p2_enemy.h"
#include "pc_p2_kochappy.h"
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
std::map<PelletView*,int> actors;int karada=-1;

bool logged[2]={false,false};
}
void pc_p2_kogane_reset(){clips.clear();timing.clear();actors.clear();karada=-1;logged[0]=logged[1]=false;}
void pc_p2_kogane_forget(BTeki* actor){actors.erase(static_cast<PelletView*>(actor));}
int pc_p2_kogane_source_id(PelletView* a){auto i=actors.find(a);return i==actors.end()?-1:i->second;}
const char* pc_p2_kogane_name(PelletView* a){int id=pc_p2_kogane_source_id(a);return id==9?"Iridescent Flint Beetle":id==10?"Iridescent Glint Beetle":id==11?"Doodlebug":nullptr;}
void pc_p2_kogane_setup(){
    pc_p2_kogane_reset();
    std::ifstream sidecar("p2-kogane-native.txt");if(!sidecar)return;
    p2kogane::Config config;if(!tekiMgr||!p2kogane::read(sidecar,config))std::abort();
    auto manifest=config.clips;std::set<std::uint32_t> wanted;for(auto row:config.ids)wanted.insert(row.first);karada=config.karada;
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
            char path[160];std::snprintf(path,sizeof(path),"assets/dataDir/courses/pikmin2room/kogane_%s_%02d.mod",clip.name.c_str(),i);
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
            char path[128];std::snprintf(path,sizeof(path),"courses/pikmin2room/kogane_%s_%02d.mod",clip.name.c_str(),i);
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
        actors[actor]=config.ids.at(actor->mGenerator->_70);
        std::printf("P2_KOGANE_BIND generator=%u source_id=%d karada_k0=%d visual_only=1\n",actor->mGenerator->_70,actors[actor],p2kogane::karada(actors[actor]));
        const auto& pos=actor->getPosition();
        std::printf("P2_ENEMY_READY species=Kogane_family native_family=Chappy generator=%u x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=P1 source_FSM=unimplemented\n",actor->mGenerator->_70,pos.x,pos.y,pos.z,actor->mHealth,actor->getParameterF(TPF_Life));
    }
    std::printf("P2_KOGANE_BANK poses=%zu mod_bytes=%zu texture_attach_calls=%d load_seconds=%.3f\n",poses,total,attachments,std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count());
}
bool pc_p2_kogane_draw(BTeki* actor,Graphics& gfx,const Matrix4f& matrix,bool corpse){
    if(!actors.count(static_cast<PelletView*>(actor)))return false;
    if(!logged[corpse?1:0]){std::printf("P2_KOGANE_DRAW corpse=%d\n",int(corpse));logged[corpse?1:0]=true;}
    if(corpse)return false;
    int motion=actor->mTekiAnimator->getCurrentMotionIndex();
    const char* name=motion==TekiMotion::Damage?"damage":actor->mVelocity.x*actor->mVelocity.x+actor->mVelocity.z*actor->mVelocity.z>1?"move":"wait";
    int frames=actor->mTekiAnimator->getFrameCount();float phase=frames>1?actor->mTekiAnimator->getCounter()/(frames-1):0;
    Shape* shape=clips.at(name).at(timing.at(name).index(phase,corpse));
    if(karada>=shape->mMaterialCount)std::abort();auto* tev=shape->mMaterialList[karada].mTevInfo;if(!tev)std::abort();
    Colour saved=tev->mKonstColors[0];int colour=p2kogane::karada(actors.at(actor));tev->mKonstColors[0].set(colour,colour,colour,255);
    shape->updateAnim(gfx,matrix,nullptr,actor);shape->drawshape(gfx,*gfx.mCamera,nullptr);tev->mKonstColors[0]=saved;return true;
}
